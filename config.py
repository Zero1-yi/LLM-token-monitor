"""Configuration manager — loads, validates, saves, and exposes AppSettings."""

import logging
from typing import Optional

from models import AppSettings, ProviderSettings
from secure_store import SecureStore

logger = logging.getLogger(__name__)


class ConfigManager:
    """Singleton-friendly manager for application configuration.

    Uses SecureStore for encrypted persistence of sensitive data (API keys).
    """

    def __init__(self, store: Optional[SecureStore] = None):
        self._store = store or SecureStore()
        self._settings: Optional[AppSettings] = None

    def load(self) -> AppSettings:
        """Load settings from encrypted store, with fallback to defaults."""
        raw = self._store.load()

        try:
            provider_raw = raw.get("provider", {})
            if isinstance(provider_raw, str):
                provider_raw = {"provider": provider_raw, "api_key": ""}
            provider = ProviderSettings(
                provider=provider_raw.get("provider", ""),
                api_key=provider_raw.get("api_key", ""),
            )

            self._settings = AppSettings(
                provider=provider,
                budget_usd=float(raw.get("budget_usd", 50.0)),
                poll_interval_minutes=int(raw.get("poll_interval_minutes", 10)),
                launch_at_startup=bool(raw.get("launch_at_startup", False)),
                first_run=bool(raw.get("first_run", True)),
                language=raw.get("language", "en"),
                deepseek_alert_threshold=float(raw.get("deepseek_alert_threshold", 10.0)),
                deepseek_currency=raw.get("deepseek_currency", "CNY"),
            )
        except Exception:
            logger.warning("Failed to parse config, using defaults", exc_info=True)
            self._settings = AppSettings()

        return self._settings

    def save(self) -> None:
        """Persist current settings to encrypted store."""
        if self._settings is None:
            return

        raw = {
            "provider": {
                "provider": self._settings.provider.provider,
                "api_key": self._settings.provider.api_key,
            },
            "budget_usd": self._settings.budget_usd,
            "poll_interval_minutes": self._settings.poll_interval_minutes,
            "launch_at_startup": self._settings.launch_at_startup,
            "first_run": self._settings.first_run,
            "language": self._settings.language,
            "deepseek_alert_threshold": self._settings.deepseek_alert_threshold,
            "deepseek_currency": self._settings.deepseek_currency,
        }
        self._store.save(raw)

    @property
    def settings(self) -> AppSettings:
        """Get current settings, loading from disk if needed."""
        if self._settings is None:
            self.load()
        assert self._settings is not None
        return self._settings

    def update_provider(self, provider: str, api_key: str) -> None:
        """Update provider settings and persist."""
        self.settings.provider.provider = provider
        self.settings.provider.api_key = api_key
        self.settings.first_run = False
        self.save()

    def update_budget(self, budget_usd: float) -> None:
        """Update monthly budget and persist."""
        self.settings.budget_usd = budget_usd
        self.save()

    def update_poll_interval(self, minutes: int) -> None:
        """Update polling interval and persist."""
        self.settings.poll_interval_minutes = max(1, min(60, minutes))
        self.save()

    def update_language(self, lang: str) -> None:
        """Update UI language and persist."""
        self.settings.language = lang
        self.save()

    def update_deepseek_threshold(self, threshold: float, currency: str) -> None:
        """Update DeepSeek alert threshold and persist."""
        self.settings.deepseek_alert_threshold = threshold
        self.settings.deepseek_currency = currency
        self.save()

    def set_launch_at_startup(self, enabled: bool) -> None:
        """Toggle Windows startup registry entry."""
        import winreg

        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        app_name = "LLMTokenMonitor"

        try:
            if enabled:
                import sys
                exe_path = sys.executable
                if not exe_path.endswith(".exe"):
                    exe_path = sys.executable
                with winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE
                ) as key:
                    winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, exe_path)
            else:
                with winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE
                ) as key:
                    try:
                        winreg.DeleteValue(key, app_name)
                    except FileNotFoundError:
                        pass
        except OSError as e:
            logger.warning(f"Failed to update startup registry: {e}")

        self.settings.launch_at_startup = enabled
        self.save()

    def reset(self) -> None:
        """Delete all stored config and reset to defaults."""
        self._store.delete_config()
        self._settings = AppSettings()
