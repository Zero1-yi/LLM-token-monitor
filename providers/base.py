"""Abstract base provider and shared types for LLM usage monitoring."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


class ProviderError(Exception):
    """Base exception for all provider errors."""


class ProviderAuthError(ProviderError):
    """401/403 — bad or expired API key."""


class ProviderRateLimitError(ProviderError):
    """429 — rate limited, should back off."""


class ProviderConnectionError(ProviderError):
    """Network failure, DNS, timeout."""


@dataclass
class UsageData:
    """Normalized usage snapshot returned by any provider."""

    provider_name: str  # "openai", "deepseek"
    tokens_used: int  # Tokens consumed in current billing period
    cost_incurred_usd: float  # Dollar-equivalent amount spent this period
    hard_limit_usd: float  # Monthly hard limit / budget ceiling
    balance_remaining: float  # Remaining balance
    usage_pct: float  # Derived: (cost_incurred / hard_limit) * 100
    period_start: str  # ISO date string, billing period start
    period_end: str  # ISO date string, billing period end
    currency: str = "USD"  # Currency code (USD, CNY, etc.)
    model_breakdown: list = field(default_factory=list)
    # [{"model": "gpt-4o", "input_tokens": 50000, "output_tokens": 12000}, ...]
    raw_response: dict = field(default_factory=dict, repr=False)


class BaseProvider(ABC):
    """Interface that every LLM provider must implement."""

    @abstractmethod
    def fetch_usage(self, api_key: str, **kwargs) -> UsageData:
        """Fetch current billing-period usage from the provider's API.

        Args:
            api_key: The provider API key.
            **kwargs: Provider-specific options (budget_usd, thresholds, etc.).

        Returns:
            UsageData with normalized fields populated.

        Raises:
            ProviderAuthError: 401/403 — bad or expired key.
            ProviderRateLimitError: 429 — back off.
            ProviderConnectionError: Network failure, DNS, timeout.
            ProviderError: Any other API error.
        """
        ...

    @staticmethod
    @abstractmethod
    def provider_name() -> str:
        """Short identifier: 'openai', 'deepseek', etc."""
        ...

    @staticmethod
    @abstractmethod
    def display_name() -> str:
        """Human-readable: 'OpenAI', 'DeepSeek', etc."""
        ...
