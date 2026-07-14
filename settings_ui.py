"""Settings window — tkinter-based configuration dialog launched from tray menu."""

import logging
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable, Optional

from models import AppSettings
from providers import list_providers
from providers.base import UsageData
from i18n import T

logger = logging.getLogger(__name__)


class SettingsWindow:
    """Modal settings dialog for configuring the LLM Token Monitor.

    Launched as a standalone tkinter window.
    Uses a tabbed interface: Provider, Budget, General.
    """

    def __init__(
        self,
        settings: AppSettings,
        on_save: Callable[[AppSettings], None],
        last_usage: Optional[UsageData] = None,
    ):
        self._settings = settings
        self._on_save_callback = on_save
        self._last_usage = last_usage
        self._test_result: Optional[str] = None
        self._current_lang = T.lang
        self._original_lang = T.lang  # snapshot to revert on Cancel

        # Create the window
        self._root = tk.Tk()
        self._root.title(T.t("sw_title"))
        self._root.resizable(False, False)
        self._root.protocol("WM_DELETE_WINDOW", self._on_cancel)

        # Center the window
        self._root.geometry("480x420")
        self._root.update_idletasks()
        w = self._root.winfo_width()
        h = self._root.winfo_height()
        x = (self._root.winfo_screenwidth() // 2) - (w // 2)
        y = (self._root.winfo_screenheight() // 2) - (h // 2)
        self._root.geometry(f"{w}x{h}+{x}+{y}")

        self._build_ui()
        self._load_current_settings()

        self._root.lift()
        self._root.focus_force()
        self._root.mainloop()

    def _build_ui(self) -> None:
        """Construct the tabbed settings interface."""
        notebook = ttk.Notebook(self._root)
        notebook.pack(fill="both", expand=True, padx=10, pady=(10, 0))

        # === Tab 1: Provider ===
        self._provider_frame = ttk.Frame(notebook, padding=10)
        notebook.add(self._provider_frame, text=T.t("sw_provider_tab"))

        # Provider dropdown
        ttk.Label(self._provider_frame, text=T.t("sw_platform")).grid(
            row=0, column=0, sticky="w", pady=(5, 2)
        )
        self._provider_var = tk.StringVar()
        self._provider_combo = ttk.Combobox(
            self._provider_frame,
            textvariable=self._provider_var,
            state="readonly",
            width=30,
        )
        providers = list_providers()
        self._provider_combo["values"] = list(providers.values())
        self._provider_combo.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 10))

        # API Key
        ttk.Label(self._provider_frame, text=T.t("sw_api_key")).grid(
            row=2, column=0, sticky="w", pady=(5, 2)
        )
        self._api_key_var = tk.StringVar()
        self._api_key_entry = ttk.Entry(
            self._provider_frame,
            textvariable=self._api_key_var,
            show="*",
            width=35,
        )
        self._api_key_entry.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(0, 5))

        # Show/Hide key toggle
        self._show_key_var = tk.BooleanVar(value=False)
        self._show_key_cb = ttk.Checkbutton(
            self._provider_frame,
            text=T.t("sw_show_key"),
            variable=self._show_key_var,
            command=self._toggle_key_visibility,
        )
        self._show_key_cb.grid(row=4, column=0, sticky="w", pady=(0, 10))

        # Test Connection button
        self._test_btn = ttk.Button(
            self._provider_frame,
            text=T.t("sw_test_btn"),
            command=self._test_connection,
        )
        self._test_btn.grid(row=5, column=0, sticky="w", pady=(5, 5))

        self._test_label = ttk.Label(self._provider_frame, text="", foreground="gray")
        self._test_label.grid(row=6, column=0, columnspan=2, sticky="w")

        # === Tab 2: Budget ===
        self._budget_frame = ttk.Frame(notebook, padding=10)
        notebook.add(self._budget_frame, text=T.t("sw_budget_tab"))

        # Provider-specific budget fields
        self._budget_labels: dict[str, list] = {}  # provider -> [label_widgets]

        # -- OpenAI budget --
        self._openai_budget_frame = ttk.Frame(self._budget_frame)
        ttk.Label(self._openai_budget_frame, text=T.t("sw_monthly_budget")).grid(
            row=0, column=0, sticky="w", pady=(10, 2)
        )
        self._budget_var = tk.DoubleVar(value=50.0)
        self._budget_spin = ttk.Spinbox(
            self._openai_budget_frame,
            textvariable=self._budget_var,
            from_=1.0,
            to=10000.0,
            increment=5.0,
            width=15,
        )
        self._budget_spin.grid(row=1, column=0, sticky="w", pady=(0, 10))

        # -- DeepSeek threshold --
        self._ds_frame = ttk.Frame(self._budget_frame)
        self._ds_currency_var = tk.StringVar(value="CNY")
        self._ds_threshold_var = tk.DoubleVar(value=10.0)

        ttk.Label(self._ds_frame, text=T.t("sw_alert_threshold", cur="CNY")).grid(
            row=0, column=0, sticky="w", pady=(10, 2)
        )
        self._ds_threshold_label = ttk.Label(
            self._ds_frame, text=T.t("sw_alert_threshold", cur="CNY")
        )
        self._ds_threshold_label.grid(row=0, column=0, sticky="w", pady=(10, 2))

        self._ds_threshold_spin = ttk.Spinbox(
            self._ds_frame,
            textvariable=self._ds_threshold_var,
            from_=0.1,
            to=100000.0,
            increment=10.0,
            width=15,
        )
        self._ds_threshold_spin.grid(row=1, column=0, sticky="w", pady=(0, 2))
        ttk.Label(
            self._ds_frame,
            text=T.t("sw_threshold_hint"),
            foreground="gray",
        ).grid(row=2, column=0, sticky="w", pady=(0, 10))

        # Poll interval (shared)
        ttk.Label(self._budget_frame, text=T.t("sw_poll_interval")).grid(
            row=10, column=0, sticky="w", pady=(10, 2)
        )
        self._poll_var = tk.IntVar(value=10)
        self._poll_spin = ttk.Spinbox(
            self._budget_frame,
            textvariable=self._poll_var,
            from_=1,
            to=60,
            increment=1,
            width=15,
        )
        self._poll_spin.grid(row=11, column=0, sticky="w", pady=(0, 10))

        # Current usage display
        ttk.Label(self._budget_frame, text=T.t("sw_current_usage")).grid(
            row=12, column=0, sticky="w", pady=(15, 2)
        )
        self._usage_text = tk.Text(
            self._budget_frame,
            height=5,
            width=45,
            state="disabled",
            relief="sunken",
            bg="#f5f5f5",
        )
        self._usage_text.grid(row=13, column=0, columnspan=2, sticky="ew", pady=(0, 10))

        # Show/hide budget sections based on provider
        self._provider_combo.bind("<<ComboboxSelected>>", self._on_provider_changed)

        # === Tab 3: General ===
        self._general_frame = ttk.Frame(notebook, padding=10)
        notebook.add(self._general_frame, text=T.t("sw_general_tab"))

        # Launch at startup
        self._startup_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            self._general_frame,
            text=T.t("sw_launch_startup"),
            variable=self._startup_var,
        ).grid(row=0, column=0, sticky="w", pady=(10, 5))

        ttk.Label(
            self._general_frame,
            text=T.t("sw_startup_hint"),
            foreground="gray",
        ).grid(row=1, column=0, sticky="w", pady=(0, 15))

        # Language selector
        ttk.Label(self._general_frame, text=T.t("sw_language")).grid(
            row=2, column=0, sticky="w", pady=(5, 2)
        )
        self._lang_var = tk.StringVar(value="English" if self._settings.language == "en" else "中文")
        self._lang_combo = ttk.Combobox(
            self._general_frame,
            textvariable=self._lang_var,
            values=["English", "中文"],
            state="readonly",
            width=15,
        )
        self._lang_combo.grid(row=3, column=0, sticky="w", pady=(0, 5))
        self._lang_combo.bind("<<ComboboxSelected>>", self._on_language_changed)

        # About info
        ttk.Separator(self._general_frame, orient="horizontal").grid(
            row=4, column=0, sticky="ew", pady=(10, 10)
        )
        ttk.Label(
            self._general_frame,
            text=T.t("sw_about"),
            foreground="gray",
        ).grid(row=5, column=0, sticky="w", pady=(5, 5))

        # --- Bottom buttons ---
        btn_frame = ttk.Frame(self._root)
        btn_frame.pack(fill="x", padx=10, pady=(5, 10))

        ttk.Button(btn_frame, text=T.t("save"), command=self._on_save).pack(
            side="right", padx=5
        )
        ttk.Button(btn_frame, text=T.t("cancel"), command=self._on_cancel).pack(
            side="right", padx=5
        )

    # ── Event handlers ────────────────────────────────────────────

    def _load_current_settings(self) -> None:
        """Populate UI fields from current AppSettings."""
        # Provider
        provider_key = self._settings.provider.provider
        if provider_key:
            providers = list_providers()
            provider_display = providers.get(provider_key, "")
            for i, val in enumerate(self._provider_combo["values"]):
                if val == provider_display:
                    self._provider_combo.current(i)
                    break
        else:
            if self._provider_combo["values"]:
                self._provider_combo.current(0)

        self._api_key_var.set(self._settings.provider.api_key)

        # Budget
        self._budget_var.set(self._settings.budget_usd)
        self._poll_var.set(self._settings.poll_interval_minutes)
        self._ds_threshold_var.set(self._settings.deepseek_alert_threshold)

        # General
        self._startup_var.set(self._settings.launch_at_startup)
        self._lang_var.set("English" if self._settings.language == "en" else "中文")

        # Show correct budget section
        self._on_provider_changed(None)
        self._update_usage_display()

    def _on_provider_changed(self, event) -> None:
        """Show/hide budget fields based on selected provider."""
        provider_display = self._provider_var.get()
        providers = list_providers()
        provider_key = None
        for k, v in providers.items():
            if v == provider_display:
                provider_key = k
                break

        # Show/hide OpenAI budget section
        if provider_key == "openai":
            self._openai_budget_frame.grid(row=0, column=0, columnspan=2, sticky="ew")
            self._ds_frame.grid_forget()
        elif provider_key == "deepseek":
            self._openai_budget_frame.grid_forget()
            cur = self._settings.deepseek_currency
            self._ds_threshold_label.config(text=T.t("sw_alert_threshold", cur=cur))
            self._ds_frame.grid(row=0, column=0, columnspan=2, sticky="ew")
        else:
            self._openai_budget_frame.grid(row=0, column=0, columnspan=2, sticky="ew")
            self._ds_frame.grid_forget()

    def _on_language_changed(self, event) -> None:
        """Handle language dropdown change."""
        lang_choice = self._lang_var.get()
        new_lang = "en" if lang_choice == "English" else "zh"

        if new_lang == self._current_lang:
            return

        self._current_lang = new_lang
        T.set_lang(new_lang)

        # Refresh the entire window
        self._root.destroy()
        self.__init__(self._settings, self._on_save_callback, self._last_usage)

    def _toggle_key_visibility(self) -> None:
        if self._show_key_var.get():
            self._api_key_entry.config(show="")
        else:
            self._api_key_entry.config(show="*")

    def _get_selected_provider_key(self) -> str:
        provider_display = self._provider_var.get()
        providers = list_providers()
        for k, v in providers.items():
            if v == provider_display:
                return k
        return ""

    def _test_connection(self) -> None:
        """Test the API connection in a background thread."""
        self._test_btn.config(state="disabled", text=T.t("sw_testing"))
        self._test_label.config(text=T.t("sw_connecting"), foreground="gray")
        self._test_result = None

        provider_key = self._get_selected_provider_key()
        api_key = self._api_key_var.get().strip()

        if not api_key:
            self._test_label.config(text=T.t("sw_test_enter_key"), foreground="red")
            self._test_btn.config(state="normal", text=T.t("sw_test_btn"))
            return

        def _run_test():
            try:
                if provider_key == "openai":
                    import certifi
                    import httpx
                    resp = httpx.Client(timeout=15.0, verify=certifi.where(), trust_env=False).get(
                        "https://api.openai.com/dashboard/billing/subscription",
                        headers={"Authorization": f"Bearer {api_key}"},
                    )
                    if resp.status_code in (401, 403):
                        self._test_result = T.t("sw_test_fail_key")
                    elif resp.is_success:
                        sub = resp.json()
                        limit = sub.get("hard_limit_usd", "?")
                        self._test_result = T.t("sw_test_ok_openai", limit=limit)
                    else:
                        self._test_result = T.t("sw_test_fail_http", code=resp.status_code)
                elif provider_key == "deepseek":
                    from providers.deepseek_provider import DeepSeekProvider
                    provider = DeepSeekProvider()
                    data = provider.fetch_raw_balance(api_key)
                    balance_infos = data.get("balance_infos", [])
                    if balance_infos:
                        bal = balance_infos[0]
                        total = bal.get("total_balance", "?")
                        currency = bal.get("currency", "")
                        self._test_result = T.t("sw_test_ok_ds", bal=total, cur=currency)
                    else:
                        self._test_result = T.t("sw_test_ok_nobal")
                else:
                    self._test_result = T.t("sw_test_fail_unk")
            except Exception as e:
                self._test_result = T.t("sw_test_fail_err", err=str(e))

            self._root.after(0, self._on_test_complete)

        thread = threading.Thread(target=_run_test, daemon=True)
        thread.start()

    def _on_test_complete(self) -> None:
        """Update UI after test connection completes."""
        self._test_btn.config(state="normal", text=T.t("sw_test_btn"))
        if self._test_result:
            is_ok = self._test_result.startswith("OK") or self._test_result.startswith("连接成功")
            self._test_label.config(
                text=self._test_result,
                foreground="green" if is_ok else "red",
            )

    def _update_usage_display(self) -> None:
        """Show current usage data in the budget tab."""
        self._usage_text.config(state="normal")
        self._usage_text.delete("1.0", "end")

        if self._last_usage:
            u = self._last_usage
            if u.provider_name == "deepseek":
                text = (
                    f"Provider:  {u.provider_name.upper()}\n"
                    f"Balance:   {u.balance_remaining:.2f} {u.currency}\n"
                    f"Threshold: {self._settings.deepseek_alert_threshold:.2f} {u.currency}\n"
                    f"Status:    {'OK' if u.balance_remaining > self._settings.deepseek_alert_threshold else 'LOW'}"
                )
            else:
                text = (
                    f"Provider:  {u.provider_name.upper()}\n"
                    f"Used:      ${u.cost_incurred_usd:.2f} / ${u.hard_limit_usd:.2f}\n"
                    f"Usage:     {u.usage_pct:.1f}%\n"
                    f"Remain:    ${u.balance_remaining:.2f}\n"
                    f"Period:    {u.period_start} → {u.period_end}"
                )
                # Per-model breakdown
                if u.model_breakdown:
                    text += "\n\n── Token Usage ──\n"
                    for m in u.model_breakdown[:8]:
                        total = m["input_tokens"] + m["output_tokens"]
                        text += f"{m['model']}: {m['input_tokens']:,} + {m['output_tokens']:,} = {total:,}\n"
            self._usage_text.insert("1.0", text)
        else:
            self._usage_text.insert("1.0", T.t("sw_no_data"))

        self._usage_text.config(state="disabled")

    def _on_save(self) -> None:
        """Validate inputs, build updated AppSettings, and call on_save."""
        provider_key = self._get_selected_provider_key()
        if not provider_key:
            messagebox.showwarning(
                T.t("val_missing_provider"),
                T.t("val_select_provider"),
            )
            return

        api_key = self._api_key_var.get().strip()
        if not api_key:
            messagebox.showwarning(
                T.t("val_missing_key"),
                T.t("val_enter_key"),
            )
            return

        budget = self._budget_var.get()
        if budget <= 0:
            messagebox.showwarning(
                T.t("val_invalid_budget"),
                T.t("val_budget_positive"),
            )
            return

        # Update settings object
        self._settings.provider.provider = provider_key
        self._settings.provider.api_key = api_key
        self._settings.budget_usd = budget
        self._settings.poll_interval_minutes = self._poll_var.get()
        self._settings.launch_at_startup = self._startup_var.get()
        self._settings.first_run = False
        self._settings.language = "en" if self._lang_var.get() == "English" else "zh"
        self._settings.deepseek_alert_threshold = self._ds_threshold_var.get()

        T.set_lang(self._settings.language)

        self._on_save_callback(self._settings)
        self._root.destroy()

    def _on_cancel(self) -> None:
        """Close without saving — revert any language change."""
        T.set_lang(self._original_lang)
        self._root.destroy()
