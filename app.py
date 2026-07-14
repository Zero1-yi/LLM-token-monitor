"""Tray Application — core orchestrator for the LLM Token Monitor.

Owns the pystray Icon, UsagePoller, ConfigManager, and wires together
all components. This is the heart of the application.
"""

import logging
import queue
import threading
from typing import Optional

import pystray

from config import ConfigManager
from i18n import T
from icons import IconGenerator, TrayColor
from models import AppSettings
from poller import UsagePoller
from providers import get_provider, list_providers
from providers.base import (
    UsageData,
    ProviderAuthError,
    ProviderRateLimitError,
    ProviderConnectionError,
    ProviderError,
)
from secure_store import SecureStore

logger = logging.getLogger(__name__)

# How often the main thread checks for queued updates (ms)
_UI_POLL_INTERVAL_MS = 500


class TrayApp:
    """Central application class.

    Creates the system tray icon, manages the background poller,
    and coordinates all UI updates in a thread-safe manner.
    """

    def __init__(self):
        # ── Core components ──
        self._store = SecureStore()
        self._config = ConfigManager(store=self._store)
        self._settings = self._config.load()
        self._icon_gen = IconGenerator()

        # Apply persisted language
        T.set_lang(self._settings.language)

        # ── State ──
        self.icon: Optional[pystray.Icon] = None
        self.poller: Optional[UsagePoller] = None
        self._last_usage: Optional[UsageData] = None
        self._last_error: Optional[str] = None
        self._current_color: TrayColor = TrayColor.GRAY

        # ── Thread safety ──
        self._update_queue: queue.Queue = queue.Queue()
        self._settings_window_open = False
        self._quit_requested = False

    # ═══════════════════════════════════════════════════════════════
    # Public API
    # ═══════════════════════════════════════════════════════════════

    def run(self) -> None:
        """Start the tray application. Blocks until quit."""
        logger.info("Starting LLM Token Monitor...")

        # First run? Show settings immediately
        if self._settings.first_run or not self._settings.provider.api_key:
            logger.info("First run detected — opening settings")
            self._open_settings()

        # Build the tray icon
        self.icon = pystray.Icon(
            "llm_token_monitor",
            self._icon_gen.generate(TrayColor.GRAY),
            T.t("app_title"),
            menu=self._build_menu(),
        )

        # Start the poller if we have credentials
        self._start_poller_if_configured()

        # Schedule the UI update checker
        self._schedule_ui_check()

        # Enter the pystray event loop (blocks until icon.stop())
        self.icon.run()

    def stop(self) -> None:
        """Shut down gracefully: stop poller, save config, remove icon."""
        logger.info("Shutting down...")
        self._quit_requested = True

        if self.poller:
            self.poller.stop()
            self.poller = None

        if self.icon:
            self.icon.stop()

    # ═══════════════════════════════════════════════════════════════
    # Menu
    # ═══════════════════════════════════════════════════════════════

    def _build_menu(self) -> pystray.Menu:
        """Build the right-click context menu with dynamic status line."""
        usage_text = self._get_status_line()

        return pystray.Menu(
            pystray.MenuItem(
                T.t("settings"),
                self._on_settings_click,
                default=True,
            ),
            pystray.MenuItem(
                T.t("refresh_now"),
                self._on_refresh_click,
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                usage_text,
                self._noop,
                enabled=False,
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                T.t("quit"),
                self._on_quit_click,
            ),
        )

    def _get_status_line(self) -> str:
        """Build the status line text for the menu."""
        if self._last_error:
            return T.t("status_error", msg=self._last_error[:40])
        if self._last_usage:
            u = self._last_usage
            if u.provider_name == "deepseek":
                return T.t("status_line", pct=u.usage_pct, used=u.balance_remaining, limit=u.hard_limit_usd)
            return T.t("status_line", pct=u.usage_pct, used=u.cost_incurred_usd, limit=u.hard_limit_usd)
        return T.t("status_waiting")

    @staticmethod
    def _noop() -> None:
        pass

    # ═══════════════════════════════════════════════════════════════
    # Tooltip
    # ═══════════════════════════════════════════════════════════════

    def _build_tooltip(self) -> str:
        """Build the hover tooltip text."""
        if self._last_error:
            return T.t("app_title") + "\n" + T.t("tt_error_prefix", msg=self._last_error)

        if self._last_usage is None:
            return T.t("app_title") + "\n" + T.t("tt_waiting")

        u = self._last_usage

        if u.provider_name == "deepseek":
            return self._build_deepseek_tooltip(u)
        else:
            return self._build_openai_tooltip(u)

    def _build_openai_tooltip(self, u: UsageData) -> str:
        """Tooltip for OpenAI (billing-based)."""
        lines = [
            T.t("tt_account_openai"),
            T.t("tt_used", used=u.cost_incurred_usd, limit=u.hard_limit_usd),
            T.t("tt_usage", pct=u.usage_pct),
            T.t("tt_remain", remain=u.balance_remaining),
            T.t("tt_period", start=u.period_start, end=u.period_end),
        ]

        # Per-model token breakdown
        if u.model_breakdown:
            lines.append("")
            lines.append(T.t("tt_model_header"))
            for m in u.model_breakdown[:10]:
                total = m["input_tokens"] + m["output_tokens"]
                lines.append(
                    T.t("tt_model_row",
                        model=m["model"],
                        input=m["input_tokens"],
                        output=m["output_tokens"],
                        total=total)
                )
        else:
            lines.append("")
            lines.append(T.t("tt_model_na"))

        return "\n".join(lines)

    def _build_deepseek_tooltip(self, u: UsageData) -> str:
        """Tooltip for DeepSeek (balance-based)."""
        threshold = self._settings.deepseek_alert_threshold
        cur = u.currency

        if u.balance_remaining <= threshold:
            status = T.t("tt_ds_warn")
        else:
            status = T.t("tt_ds_ok")

        lines = [
            T.t("tt_account_ds"),
            T.t("tt_ds_balance", bal=f"{u.balance_remaining:.2f}", cur=cur),
            T.t("tt_ds_threshold", thresh=f"{threshold:.2f}", cur=cur),
            status,
        ]

        # Per-model not available for DeepSeek
        if u.model_breakdown:
            lines.append("")
            lines.append(T.t("tt_model_header"))
            for m in u.model_breakdown:
                total = m["input_tokens"] + m["output_tokens"]
                lines.append(
                    T.t("tt_model_row",
                        model=m["model"],
                        input=m["input_tokens"],
                        output=m["output_tokens"],
                        total=total)
                )
        else:
            lines.append("")
            lines.append(T.t("tt_model_na"))

        return "\n".join(lines)

    # ═══════════════════════════════════════════════════════════════
    # Menu actions
    # ═══════════════════════════════════════════════════════════════

    def _on_settings_click(self) -> None:
        self._open_settings()

    def _on_refresh_click(self) -> None:
        """Trigger an immediate manual refresh."""
        logger.info("Manual refresh requested")
        if self._settings.provider.api_key:
            threading.Thread(
                target=self._fetch_and_update,
                daemon=True,
                name="manual-refresh",
            ).start()
        else:
            self._last_error = T.t("err_no_key")
            self._current_color = TrayColor.GRAY
            self._update_tray_display()

    def _on_quit_click(self) -> None:
        self.stop()

    # ═══════════════════════════════════════════════════════════════
    # Settings window
    # ═══════════════════════════════════════════════════════════════

    def _open_settings(self) -> None:
        """Launch the settings window (modal)."""
        if self._settings_window_open:
            return

        self._settings_window_open = True

        def on_save(updated: AppSettings) -> None:
            """Called when user clicks Save in settings."""
            logger.info(
                f"Settings saved: provider={updated.provider.provider}"
            )
            self._settings = updated
            self._config.update_provider(
                updated.provider.provider,
                updated.provider.api_key,
            )
            self._config.update_budget(updated.budget_usd)
            self._config.update_poll_interval(updated.poll_interval_minutes)
            self._config.set_launch_at_startup(updated.launch_at_startup)
            self._config.update_language(updated.language)
            self._config.update_deepseek_threshold(
                updated.deepseek_alert_threshold,
                updated.deepseek_currency,
            )

            # Apply language change immediately
            T.set_lang(updated.language)

            self._last_error = None

            # Restart poller with new settings
            self._start_poller_if_configured()

            # Refresh menu / tooltip language
            self._update_tray_display()

        try:
            from settings_ui import SettingsWindow
            SettingsWindow(self._settings, on_save, self._last_usage)
        except Exception as e:
            logger.exception("Failed to open settings window")
            self._last_error = T.t("err_settings", msg=str(e))
            self._current_color = TrayColor.GRAY
            self._update_tray_display()
        finally:
            self._settings_window_open = False

    # ═══════════════════════════════════════════════════════════════
    # Poller management
    # ═══════════════════════════════════════════════════════════════

    def _start_poller_if_configured(self) -> None:
        """Start or restart the poller if provider is configured."""
        if not self._settings.provider.api_key:
            logger.info("No API key configured — poller not started")
            return

        # Stop existing poller
        if self.poller:
            self.poller.stop()

        def fetch_fn() -> UsageData:
            return self._fetch_usage()

        interval = self._settings.poll_interval_minutes * 60
        self.poller = UsagePoller(
            fetch_fn=fetch_fn,
            on_update=self._on_poll_success,
            on_error=self._on_poll_error,
            interval_seconds=interval,
        )
        self.poller.start()

        # Also do an immediate first fetch
        threading.Thread(
            target=self._fetch_and_update,
            daemon=True,
            name="initial-fetch",
        ).start()

    def _fetch_and_update(self) -> None:
        """Fetch usage once and update UI (used for manual refresh)."""
        try:
            data = self._fetch_usage()
            self._on_poll_success(data)
        except Exception as exc:
            self._on_poll_error(exc)

    def _fetch_usage(self) -> UsageData:
        """Perform a single usage fetch using the configured provider."""
        provider_key = self._settings.provider.provider
        api_key = self._settings.provider.api_key

        if not provider_key or not api_key:
            raise ProviderError(T.t("err_not_configured"))

        provider = get_provider(provider_key)

        if provider_key == "deepseek":
            return provider.fetch_usage(
                api_key=api_key,
                alert_threshold=self._settings.deepseek_alert_threshold,
            )
        else:
            return provider.fetch_usage(
                api_key=api_key,
                budget_usd=self._settings.budget_usd,
            )

    # ═══════════════════════════════════════════════════════════════
    # Poll callbacks (called from poller thread)
    # ═══════════════════════════════════════════════════════════════

    def _on_poll_success(self, data: UsageData) -> None:
        """Called when a poll succeeds. Thread-safe."""
        self._last_usage = data
        self._last_error = None
        self._current_color = IconGenerator.color_for_usage(data.usage_pct)

        # Persist DeepSeek currency so threshold labels stay consistent
        if data.provider_name == "deepseek" and data.currency:
            self._config.update_deepseek_threshold(
                self._settings.deepseek_alert_threshold,
                data.currency,
            )
            self._settings = self._config.settings

        self._update_queue.put(("update", None))

    def _on_poll_error(self, exc: Exception) -> None:
        """Called when a poll fails. Thread-safe."""
        logger.warning(f"Poll error: {exc}")

        if isinstance(exc, ProviderAuthError):
            self._last_error = T.t("err_auth")
            self._current_color = TrayColor.GRAY
        elif isinstance(exc, ProviderRateLimitError):
            self._last_error = T.t("err_rate_limit")
            self._current_color = TrayColor.YELLOW
        elif isinstance(exc, ProviderConnectionError):
            self._last_error = T.t("err_connection")
            self._current_color = TrayColor.GRAY
        else:
            self._last_error = str(exc)[:80]
            self._current_color = TrayColor.GRAY

        self._update_queue.put(("update", None))

    # ═══════════════════════════════════════════════════════════════
    # UI update (runs on main thread via tkinter .after)
    # ═══════════════════════════════════════════════════════════════

    def _schedule_ui_check(self) -> None:
        """Schedule periodic check of the update queue on the GUI thread."""
        if self._quit_requested:
            return

        self._drain_update_queue()

        if self.icon and self.icon.visible:
            self.icon.after(_UI_POLL_INTERVAL_MS, self._schedule_ui_check)

    def _drain_update_queue(self) -> None:
        """Process all pending updates from the poller thread."""
        had_update = False

        while True:
            try:
                msg_type, _ = self._update_queue.get_nowait()
                had_update = True
            except queue.Empty:
                break

        if had_update:
            self._update_tray_display()

    def _update_tray_display(self) -> None:
        """Update icon, tooltip, and menu on the main thread."""
        if self.icon is None:
            return

        self.icon.icon = self._icon_gen.generate(self._current_color)
        self.icon.title = self._build_tooltip()
        self.icon.menu = self._build_menu()
