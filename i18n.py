"""Internationalization module for LLM Token Monitor.

Provides a simple dict-based i18n system with Chinese and English support.
Usage:
    from i18n import T
    label = T.t("settings")  # -> "Settings" or "设置"
    label = T.t("usage_pct", pct=65)  # -> "65% used" or "已用 65%"
"""

from typing import Optional


STRINGS: dict[str, dict[str, str]] = {
    # ── Tray Menu ──
    "settings":           {"en": "Settings",              "zh": "设置"},
    "refresh_now":        {"en": "Refresh Now",           "zh": "立即刷新"},
    "quit":               {"en": "Quit",                  "zh": "退出"},
    "app_title":          {"en": "LLM Token Monitor",     "zh": "LLM 用量监控"},

    # ── Status line (menu) ──
    "status_waiting":     {"en": "Waiting for data...",   "zh": "等待数据中..."},
    "status_error":       {"en": "Error: {msg}",          "zh": "错误: {msg}"},
    "status_line":        {"en": "{pct:.0f}% — ${used:.2f} / ${limit:.2f}",
                           "zh": "{pct:.0f}% — ${used:.2f} / ${limit:.2f}"},

    # ── Tooltip ──
    "tt_account_openai":  {"en": "OpenAI Account",        "zh": "OpenAI 账户"},
    "tt_account_ds":      {"en": "DeepSeek Account",      "zh": "DeepSeek 账户"},
    "tt_used":            {"en": "Used:   ${used:.2f} / ${limit:.2f}",
                           "zh": "已用:   ${used:.2f} / ${limit:.2f}"},
    "tt_usage":           {"en": "Usage:  {pct:.1f}%",    "zh": "用量:  {pct:.1f}%"},
    "tt_remain":          {"en": "Remain: ${remain:.2f}", "zh": "剩余:  ${remain:.2f}"},
    "tt_period":          {"en": "Period: {start} → {end}",
                           "zh": "周期: {start} → {end}"},
    "tt_ds_balance":      {"en": "Balance: {bal} {cur}",  "zh": "余额: {bal} {cur}"},
    "tt_ds_threshold":    {"en": "Alert Threshold: {thresh} {cur}",
                           "zh": "告警阈值: {thresh} {cur}"},
    "tt_ds_ok":           {"en": "Status: OK",            "zh": "状态: 正常"},
    "tt_ds_warn":         {"en": "Status: LOW BALANCE",   "zh": "状态: 余额偏低"},
    "tt_waiting":         {"en": "Waiting for first data...",
                           "zh": "等待首次数据..."},
    "tt_model_header":    {"en": "── Token Usage ──",     "zh": "── Token 用量 ──"},
    "tt_model_row":       {"en": "  {model}: {input:,} in + {output:,} out ({total:,} total)",
                           "zh": "  {model}: {input:,} 输入 + {output:,} 输出 (共 {total:,})"},
    "tt_model_na":        {"en": "(per-model data unavailable)", "zh": "(无单模型数据)"},
    "tt_error_prefix":    {"en": "Error: {msg}",          "zh": "错误: {msg}"},

    # ── Error messages (tray) ──
    "err_no_key":         {"en": "No API key configured",           "zh": "未配置 API Key"},
    "err_auth":           {"en": "Invalid API key — update Settings", "zh": "API Key 无效 — 请更新设置"},
    "err_rate_limit":     {"en": "Rate limited — backing off...",    "zh": "频率限制 — 等待中..."},
    "err_connection":     {"en": "Connection error — will retry",    "zh": "连接错误 — 将重试"},
    "err_settings":       {"en": "Settings error: {msg}",           "zh": "设置错误: {msg}"},
    "err_not_configured": {"en": "Provider not configured",         "zh": "未配置提供商"},

    # ── Settings window ──
    "sw_title":           {"en": "LLM Token Monitor — Settings",
                           "zh": "LLM 用量监控 — 设置"},
    "sw_provider_tab":    {"en": "Provider",              "zh": "提供商"},
    "sw_budget_tab":      {"en": "Budget",                "zh": "预算"},
    "sw_general_tab":     {"en": "General",               "zh": "通用"},

    # Provider tab
    "sw_platform":        {"en": "Platform:",             "zh": "平台:"},
    "sw_api_key":         {"en": "API Key:",              "zh": "API Key:"},
    "sw_show_key":        {"en": "Show key",              "zh": "显示密钥"},
    "sw_test_btn":        {"en": "Test Connection",       "zh": "测试连接"},
    "sw_testing":         {"en": "Testing...",            "zh": "测试中..."},
    "sw_connecting":      {"en": "Connecting...",         "zh": "连接中..."},
    "sw_test_enter_key":  {"en": "Please enter an API key", "zh": "请输入 API Key"},
    "sw_test_ok_openai":  {"en": "OK — Monthly limit: ${limit}",
                           "zh": "连接成功 — 月度限额: ${limit}"},
    "sw_test_ok_ds":      {"en": "OK — Balance: {bal} {cur}",
                           "zh": "连接成功 — 余额: {bal} {cur}"},
    "sw_test_ok_nobal":   {"en": "OK — Connected (no balance info)",
                           "zh": "连接成功 (无余额信息)"},
    "sw_test_fail_key":   {"en": "FAILED: Invalid API key", "zh": "失败: API Key 无效"},
    "sw_test_fail_http":  {"en": "FAILED: HTTP {code}",    "zh": "失败: HTTP {code}"},
    "sw_test_fail_unk":   {"en": "FAILED: Unknown provider", "zh": "失败: 未知提供商"},
    "sw_test_fail_err":   {"en": "FAILED: {err}",          "zh": "失败: {err}"},

    # Budget tab
    "sw_monthly_budget":  {"en": "Monthly Budget (USD):",  "zh": "月度预算 (USD):"},
    "sw_poll_interval":   {"en": "Poll Interval (min):",   "zh": "刷新间隔 (分钟):"},
    "sw_current_usage":   {"en": "Current Usage:",         "zh": "当前用量:"},
    "sw_no_data":         {"en": "No data yet — waiting for first poll...",
                           "zh": "暂无数据 — 等待首次刷新..."},

    # General tab
    "sw_launch_startup":  {"en": "Launch at Windows startup",
                           "zh": "开机自启动"},
    "sw_startup_hint":    {"en": "When enabled, LLM Token Monitor will start automatically\nwhen you log into Windows.",
                           "zh": "启用后，登录 Windows 时自动启动 LLM Token Monitor。"},
    "sw_language":        {"en": "Language:",              "zh": "语言:"},
    "sw_about":           {"en": "LLM Token Monitor v1.1.0\nMonitors token usage for OpenAI and DeepSeek APIs.\nConfiguration is encrypted and stored in %APPDATA%.",
                           "zh": "LLM Token Monitor v1.1.0\n监控 OpenAI 和 DeepSeek API 的用量。\n配置已加密存储于 %APPDATA%。"},

    # Buttons
    "save":               {"en": "Save",                  "zh": "保存"},
    "cancel":             {"en": "Cancel",                 "zh": "取消"},

    # Validation dialogs
    "val_missing_provider":   {"en": "Missing Provider",                "zh": "缺少提供商"},
    "val_select_provider":    {"en": "Please select a provider platform.", "zh": "请选择提供商平台。"},
    "val_missing_key":        {"en": "Missing API Key",                 "zh": "缺少 API Key"},
    "val_enter_key":          {"en": "Please enter your API key.",      "zh": "请输入 API Key。"},
    "val_invalid_budget":     {"en": "Invalid Budget",                  "zh": "无效预算"},
    "val_budget_positive":    {"en": "Monthly budget must be greater than $0.", "zh": "月度预算必须大于 $0。"},

    # DeepSeek alert threshold
    "sw_alert_threshold": {"en": "Alert Threshold ({cur}):",
                           "zh": "告警阈值 ({cur}):"},
    "sw_threshold_hint":  {"en": "Icon turns red when balance drops below this amount.",
                           "zh": "余额低于此值时图标变红。"},
}


class _I18n:
    """Singleton i18n manager."""

    _instance: Optional["_I18n"] = None

    def __new__(cls) -> "_I18n":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._lang = "en"
        return cls._instance

    @property
    def lang(self) -> str:
        return self._lang

    def set_lang(self, lang: str) -> None:
        """Switch language. 'en' or 'zh'."""
        if lang in ("en", "zh"):
            self._lang = lang

    def t(self, key: str, **kwargs) -> str:
        """Translate a key with optional format arguments.

        Args:
            key: Translation key from the STRINGS dict.
            **kwargs: Values to format into the translated string.

        Returns:
            Translated and formatted string, or the key itself if missing.
        """
        entry = STRINGS.get(key, {})
        text = entry.get(self._lang) or entry.get("en", key)
        if kwargs:
            try:
                return text.format(**kwargs)
            except (KeyError, ValueError):
                return text
        return text


# Global singleton
T = _I18n()
