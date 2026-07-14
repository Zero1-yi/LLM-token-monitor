"""DeepSeek provider — uses Balance API (standard API key)."""

import logging
import os

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

# DeepSeek balance endpoint
BALANCE_URL = "https://api.deepseek.com/user/balance"

# NOTE: DeepSeek does not publicly expose a per-model usage API.
# The web console (platform.deepseek.com) uses internal APIs with
# browser session auth, not API keys. All known api.deepseek.com
# usage endpoints return 404. Per-model data is not available.


class DeepSeekProvider(BaseProvider):
    """Fetches DeepSeek balance via the /user/balance endpoint.

    DeepSeek does not provide a time-bucketed usage/history API.
    This provider shows the current account balance directly
    (matching what you see on platform.deepseek.com).
    A user-configurable alert threshold determines the color:
      - Green:  balance > threshold × 2
      - Yellow: balance in (threshold, threshold × 2]
      - Red:    balance <= threshold
    """

    def __init__(self):
        pass

    @staticmethod
    def provider_name() -> str:
        return "deepseek"

    @staticmethod
    def display_name() -> str:
        return "DeepSeek"

    def fetch_usage(
        self,
        api_key: str,
        alert_threshold: float = 10.0,
        **kwargs,
    ) -> UsageData:
        """Fetch current DeepSeek balance and evaluate against threshold.

        Args:
            api_key: DeepSeek API key.
            alert_threshold: Balance below this triggers red icon.
        """
        client = httpx.Client(timeout=30.0, verify=certifi.where(), trust_env=False)

        try:
            resp = client.get(
                BALANCE_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Accept": "application/json",
                },
            )
        except httpx.ConnectError as e:
            raise ProviderConnectionError(f"Cannot connect to DeepSeek: {e}") from e
        except httpx.TimeoutException as e:
            raise ProviderConnectionError(f"DeepSeek request timed out: {e}") from e

        self._check_response(resp)
        data = resp.json()

        if not data.get("is_available", True):
            raise ProviderError("DeepSeek account is not available for API calls")

        # Parse balance — keep original currency
        balance_info = self._parse_balance(data)

        if balance_info is None:
            raise ProviderError("Could not parse DeepSeek balance response")

        current_balance = balance_info["total"]
        currency = balance_info["currency"]

        # --- Per-model token breakdown (best-effort) ---
        model_breakdown = self._fetch_model_breakdown(client, api_key)

        # Color threshold calculation
        if alert_threshold > 0:
            if current_balance <= alert_threshold:
                usage_pct = 90.0  # Red zone
            elif current_balance <= alert_threshold * 2:
                usage_pct = 60.0  # Yellow zone
            else:
                usage_pct = 25.0  # Green zone
        else:
            usage_pct = 0.0

        # cost/hard_limit are not meaningful for DeepSeek balance model,
        # but we provide them for UI consistency
        hard_limit = max(alert_threshold * 3, current_balance)

        from datetime import datetime, timedelta, timezone

        now = datetime.now(timezone.utc)
        month_start = now.replace(day=1).strftime("%Y-%m-%d")
        if now.month == 12:
            month_end = now.replace(year=now.year + 1, month=1, day=1)
        else:
            month_end = now.replace(month=now.month + 1, day=1)
        month_end = (month_end - timedelta(days=1)).strftime("%Y-%m-%d")

        return UsageData(
            provider_name="deepseek",
            tokens_used=0,  # Not available from balance endpoint
            cost_incurred_usd=0.0,  # Not tracked in this model
            hard_limit_usd=hard_limit,
            balance_remaining=current_balance,
            usage_pct=round(usage_pct, 1),
            period_start=month_start,
            period_end=month_end,
            currency=currency,
            model_breakdown=model_breakdown,
            raw_response=data,
        )

    def _parse_balance(self, data: dict) -> dict | None:
        """Extract total balance and currency from API response.

        Returns dict with 'total' (float) and 'currency' (str), or None.
        """
        balance_infos = data.get("balance_infos", [])
        if not balance_infos:
            return None

        # Prefer CNY, fallback to USD
        for info in balance_infos:
            if info.get("currency") == "CNY":
                return {
                    "total": float(info.get("total_balance", "0")),
                    "currency": "CNY",
                }
        for info in balance_infos:
            if info.get("currency") == "USD":
                return {
                    "total": float(info.get("total_balance", "0")),
                    "currency": "USD",
                }

        # Last resort
        info = balance_infos[0]
        return {
            "total": float(info.get("total_balance", "0")),
            "currency": info.get("currency", "CNY"),
        }

    def fetch_raw_balance(self, api_key: str) -> dict:
        """Fetch raw balance data (used by settings UI for 'Test Connection')."""
        client = httpx.Client(timeout=30.0, verify=certifi.where(), trust_env=False)

        resp = client.get(
            BALANCE_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Accept": "application/json",
            },
        )
        self._check_response(resp)
        return resp.json()

    def _fetch_model_breakdown(self, client: httpx.Client, api_key: str) -> list[dict]:
        """DeepSeek has no public per-model usage API. Returns empty list."""
        return []

    def _check_response(self, response: httpx.Response) -> None:
        """Check HTTP response and raise appropriate errors."""
        if response.status_code in (401, 403):
            raise ProviderAuthError(
                f"DeepSeek API key is invalid or expired (HTTP {response.status_code})"
            )
        if response.status_code == 429:
            raise ProviderRateLimitError(
                "DeepSeek rate limit exceeded — backing off"
            )
        if response.status_code >= 500:
            raise ProviderConnectionError(
                f"DeepSeek server error (HTTP {response.status_code})"
            )
        if not response.is_success:
            raise ProviderError(
                f"DeepSeek API error (HTTP {response.status_code}): {response.text[:200]}"
            )
