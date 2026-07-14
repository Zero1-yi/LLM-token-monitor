"""Provider registry — maps provider names to their implementation classes."""

from providers.base import BaseProvider
from providers.openai_provider import OpenAIProvider
from providers.deepseek_provider import DeepSeekProvider

_PROVIDER_MAP: dict[str, type[BaseProvider]] = {
    "openai": OpenAIProvider,
    "deepseek": DeepSeekProvider,
}


def get_provider(name: str) -> BaseProvider:
    """Factory: return a provider instance by name.

    Args:
        name: Provider key, e.g. "openai", "deepseek".

    Returns:
        A concrete BaseProvider instance.

    Raises:
        ValueError: If the provider name is not registered.
    """
    cls = _PROVIDER_MAP.get(name)
    if cls is None:
        available = ", ".join(_PROVIDER_MAP.keys())
        raise ValueError(f"Unknown provider: '{name}'. Available: {available}")
    return cls()


def list_providers() -> dict[str, str]:
    """Return {provider_key: display_name} for all registered providers."""
    return {k: v.display_name() for k, v in _PROVIDER_MAP.items()}


def register_provider(name: str, cls: type[BaseProvider]) -> None:
    """Register a new provider at runtime (for extensibility)."""
    _PROVIDER_MAP[name] = cls
