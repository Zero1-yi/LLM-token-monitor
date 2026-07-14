"""Data models for LLM Token Monitor — configuration and usage data."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class UsageData:
    """Normalized usage snapshot returned by any provider."""

    provider_name: str  # "openai", "deepseek"
    tokens_used: int  # Tokens consumed in current billing period (0 if N/A)
    cost_incurred_usd: float  # Dollar-equivalent amount spent this period
    hard_limit_usd: float  # Monthly hard limit (billing cap or user-set budget)
    balance_remaining: float  # Remaining balance in account currency
    usage_pct: float  # Derived: (cost_incurred / hard_limit) * 100
    period_start: str  # ISO date string, billing period start
    period_end: str  # ISO date string, billing period end
    currency: str = "USD"  # Currency code
    raw_response: dict = field(default_factory=dict, repr=False)


@dataclass
class ProviderSettings:
    """Per-provider configuration."""

    provider: str = ""  # key into provider registry, e.g. "openai"
    api_key: str = ""  # encrypted at rest, plaintext only in memory


@dataclass
class AppSettings:
    """Top-level application configuration."""

    provider: ProviderSettings = field(default_factory=ProviderSettings)
    budget_usd: float = 50.0  # Monthly budget ceiling in USD (or threshold for DeepSeek)
    poll_interval_minutes: int = 10  # How often to poll (1–60)
    launch_at_startup: bool = False  # Windows startup registry key
    first_run: bool = True  # Triggers settings dialog on first launch
    language: str = "en"  # "en" or "zh"
    # DeepSeek-specific: alert threshold in account currency
    deepseek_alert_threshold: float = 10.0
    deepseek_currency: str = "CNY"
