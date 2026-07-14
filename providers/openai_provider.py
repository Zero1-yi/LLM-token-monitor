"""OpenAI provider — uses Dashboard Billing API (standard API key)."""

import logging
import os
from datetime import datetime, timedelta, timezone

import certifi
import httpx

from providers.base import (
    BaseProvider,
    UsageData,
    ProviderAuthError,
    ProviderRateLimitError,
    ProviderConnectionError,
    ProviderError,
)

logger = logging.getLogger(__name__)

# OpenAI Dashboard Billing endpoints (work with standard API keys)
SUBSCRIPTION_URL = "https://api.openai.com/dashboard/billing/subscription"
USAGE_URL = "https://api.openai.com/dashboard/billing/usage"

# Admin organization usage — per-model token breakdown
# Works with some standard keys; fails silently with 403 otherwise
USAGE_COMPLETIONS_URL = "https://api.openai.com/v1/organization/usage/completions"


class OpenAIProvider(BaseProvider):
    """Fetches OpenAI usage via the public Dashboard Billing API.

    Uses two endpoints:
    1. /dashboard/billing/subscription → hard_limit_usd (billing cap)
    2. /dashboard/billing/usage?start_date=...&end_date=... → total_usage in cents

    Both work with standard API keys (sk-...).
    """

    def __init__(self):
        pass

    @staticmethod
    def provider_name() -> str:
        return "openai"

    @staticmethod
    def display_name() -> str:
        return "OpenAI"

    def fetch_usage(self, api_key: str, **kwargs) -> UsageData:
        """Fetch current-month billing usage from OpenAI.

        Returns account-level (not per-model) usage data directly
        from the Dashboard Billing API to match what you see on
        platform.openai.com.
        """
        client = httpx.Client(timeout=30.0, verify=certifi.where(), trust_env=False)

        # --- 1. Get subscription / hard limit ---
        try:
            sub_resp = client.get(
                SUBSCRIPTION_URL,
                headers={"Authorization": f"Bearer {api_key}"},
            )
        except httpx.ConnectError as e:
            raise ProviderConnectionError(f"Cannot connect to OpenAI: {e}") from e
        except httpx.TimeoutException as e:
            raise ProviderConnectionError(f"OpenAI request timed out: {e}") from e

        self._check_response(sub_resp)
        sub_data = sub_resp.json()
        hard_limit_usd = float(sub_data.get("hard_limit_usd", 0))

        # --- 2. Get current-month usage ---
        now = datetime.now(timezone.utc)
        start_date = now.replace(day=1).strftime("%Y-%m-%d")
        end_date = now.strftime("%Y-%m-%d")

        try:
            usage_resp = client.get(
                USAGE_URL,
                params={"start_date": start_date, "end_date": end_date},
                headers={"Authorization": f"Bearer {api_key}"},
            )
        except httpx.ConnectError as e:
            raise ProviderConnectionError(f"Cannot connect to OpenAI: {e}") from e
        except httpx.TimeoutException as e:
            raise ProviderConnectionError(f"OpenAI request timed out: {e}") from e

        self._check_response(usage_resp)
        usage_data = usage_resp.json()

        # total_usage is in cents — convert to dollars
        total_usage_cents = float(usage_data.get("total_usage", 0))
        cost_incurred_usd = total_usage_cents / 100.0

        # Remaining = hard_limit - spent (matches OpenAI billing page)
        balance_remaining = hard_limit_usd - cost_incurred_usd

        # Usage percentage against hard limit
        if hard_limit_usd > 0:
            usage_pct = (cost_incurred_usd / hard_limit_usd) * 100
        else:
            usage_pct = 0.0

        # Token estimation: ~$0.01 per 1K tokens blended (rough guide only)
        tokens_used = int(cost_incurred_usd * 100_000) if cost_incurred_usd > 0 else 0

        # --- 3. Get per-model token breakdown (best-effort) ---
        model_breakdown = self._fetch_model_breakdown(client, api_key, now)
        if model_breakdown:
            # Use actual token count from the breakdown instead of estimate
            tokens_used = sum(m["input_tokens"] + m["output_tokens"] for m in model_breakdown)

        # Period dates
        month_start = now.replace(day=1).strftime("%Y-%m-%d")
        if now.month == 12:
            month_end = now.replace(year=now.year + 1, month=1, day=1)
        else:
            month_end = now.replace(month=now.month + 1, day=1)
        month_end = (month_end - timedelta(days=1)).strftime("%Y-%m-%d")

        return UsageData(
            provider_name="openai",
            tokens_used=tokens_used,
            cost_incurred_usd=round(cost_incurred_usd, 2),
            hard_limit_usd=hard_limit_usd,
            balance_remaining=round(balance_remaining, 2),
            usage_pct=round(usage_pct, 1),
            period_start=month_start,
            period_end=month_end,
            currency="USD",
            model_breakdown=model_breakdown,
            raw_response={
                "subscription": sub_data,
                "usage": usage_data,
            },
        )

    def _fetch_model_breakdown(
        self, client: httpx.Client, api_key: str, now: datetime
    ) -> list[dict]:
        """Fetch per-model token breakdown from the organization usage API.

        Silently returns [] if the API key lacks admin permissions (403)
        or if the endpoint is unreachable. This is best-effort only.
        """
        try:
            start_time = int(now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).timestamp())
            end_time = int(now.timestamp())

            resp = client.get(
                USAGE_COMPLETIONS_URL,
                params={
                    "start_time": start_time,
                    "end_time": end_time,
                    "group_by": "model",
                    "limit": 100,
                },
                headers={"Authorization": f"Bearer {api_key}"},
            )
        except Exception:
            logger.debug("Per-model usage fetch failed (network)", exc_info=True)
            return []

        if resp.status_code in (401, 403, 404):
            logger.debug(f"Per-model usage not available (HTTP {resp.status_code})")
            return []

        if not resp.is_success:
            logger.debug(f"Per-model usage fetch failed (HTTP {resp.status_code})")
            return []

        try:
            data = resp.json()
        except Exception:
            return []

        # Parse bucket → results → per-model totals
        breakdown: dict[str, dict[str, int]] = {}
        for bucket in data.get("data", []):
            for result in bucket.get("results", []):
                model = result.get("model", "unknown")
                if model not in breakdown:
                    breakdown[model] = {"input_tokens": 0, "output_tokens": 0}
                breakdown[model]["input_tokens"] += result.get("input_tokens", 0)
                breakdown[model]["output_tokens"] += result.get("output_tokens", 0)

        # Sort by total tokens desc
        sorted_models = sorted(
            breakdown.items(),
            key=lambda kv: kv[1]["input_tokens"] + kv[1]["output_tokens"],
            reverse=True,
        )

        return [
            {"model": model, "input_tokens": tokens["input_tokens"], "output_tokens": tokens["output_tokens"]}
            for model, tokens in sorted_models
        ]

    def _check_response(self, response: httpx.Response) -> None:
        """Check HTTP response and raise appropriate errors."""
        if response.status_code in (401, 403):
            raise ProviderAuthError(
                f"OpenAI API key is invalid or expired (HTTP {response.status_code})"
            )
        if response.status_code == 429:
            raise ProviderRateLimitError(
                "OpenAI rate limit exceeded — backing off"
            )
        if response.status_code >= 500:
            raise ProviderConnectionError(
                f"OpenAI server error (HTTP {response.status_code})"
            )
        if not response.is_success:
            raise ProviderError(
                f"OpenAI API error (HTTP {response.status_code}): {response.text[:200]}"
            )
