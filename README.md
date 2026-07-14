# LLM Token Monitor / LLM 用量监控

[English](#english) | [中文](#中文)

---

## 中文

一款轻量级的 Windows 系统托盘应用，用于监控大模型 API 的 token 用量和账单余额。

### 功能

- **系统托盘常驻** — 无主窗口，安静运行在通知区域
- **颜色编码** — 🟢 绿色 (<50%) / 🟡 黄色 (50-80%) / 🔴 红色 (>80%) 圆形图标
- **悬停提示** — 鼠标悬停显示余额、用量和 per-model token 明细
- **多平台** — 支持 OpenAI（账单 API）和 DeepSeek（余额 API）
- **自动刷新** — 每 10 分钟拉取一次（可配置 1-60 分钟）
- **安全存储** — API Key 使用 Windows DPAPI + Fernet 双层加密
- **中英文切换** — 设置中可选择中文或英文界面
- **轻量** — 打包后 ~24 MB，资源占用极低

### 支持平台

| 平台 | API | 密钥类型 | Per-Model 用量 |
|------|-----|----------|---------------|
| OpenAI | Dashboard Billing API | 标准 API Key | 支持 |
| DeepSeek | Balance API (`/user/balance`) | 标准 API Key | 不支持（公开 API 无此端点） |

### 快速开始

**方式一：下载 .exe（推荐）**

从 [Releases](https://github.com/Zero1-yi/llm-token-monitor/releases) 下载 `LLMTokenMonitor.exe`，双击运行。

**方式二：从源码运行**

```bash
git clone https://github.com/Zero1-yi/llm-token-monitor.git
cd llm-token-monitor
pip install -r requirements.txt
python main.py
```

**方式三：自行打包**

```bash
pip install pyinstaller
pyinstaller build.spec --clean --noconfirm
# 输出: dist/LLMTokenMonitor.exe
```

### 使用说明

1. 首次运行自动弹出设置窗口
2. 选择平台（OpenAI / DeepSeek）
3. 输入 API Key，点击「测试连接」
4. 设置月度预算 / 告警阈值
5. 点击保存，应用缩入托盘开始监控

### 托盘图标

| 颜色 | 含义 |
|------|------|
| 🟢 绿色 | 用量 < 50%，正常 |
| 🟡 黄色 | 用量 50-80%，注意 |
| 🔴 红色 | 用量 > 80% 或余额低于阈值 |
| ⚫ 灰色 | 无数据 / 断连 / 错误 |

### 配置存储

加密存储于 `%APPDATA%/LLMTokenMonitor/`，仅当前 Windows 用户可解密。

---

## English

A lightweight Windows system-tray app for monitoring LLM API token usage and billing.

### Features

- **System tray only** — no main window, lives in the notification area
- **Color-coded status** — 🟢 Green (<50%) / 🟡 Yellow (50-80%) / 🔴 Red (>80%)
- **Hover tooltip** — balance, usage, and per-model token breakdown
- **Multi-provider** — OpenAI (Dashboard Billing API) and DeepSeek (Balance API)
- **Auto-refresh** — polls every 10 minutes (configurable 1–60 min)
- **Secure storage** — API keys encrypted via Windows DPAPI + Fernet
- **i18n** — Chinese and English UI
- **Lightweight** — ~24 MB packaged

### Supported Providers

| Provider | API | Key Type | Per-Model |
|----------|-----|----------|-----------|
| OpenAI | Dashboard Billing API | Standard API key | Yes |
| DeepSeek | Balance API (`/user/balance`) | Standard API key | No (no public endpoint) |

### Quick Start

**Option 1: Download .exe**

Grab `LLMTokenMonitor.exe` from [Releases](https://github.com/Zero1-yi/llm-token-monitor/releases), double-click to run.

**Option 2: Run from source**

```bash
git clone https://github.com/Zero1-yi/llm-token-monitor.git
cd llm-token-monitor
pip install -r requirements.txt
python main.py
```

**Option 3: Build from source**

```bash
pip install pyinstaller
pyinstaller build.spec --clean --noconfirm
# Output: dist/LLMTokenMonitor.exe
```

### Project Structure

```
deepseek/
├── main.py                  # Entry point
├── app.py                   # Core TrayApp orchestrator
├── config.py                # Configuration manager
├── models.py                # Data models
├── secure_store.py          # DPAPI + Fernet encryption
├── poller.py                # Background polling thread
├── icons.py                 # Dynamic icon generation
├── i18n.py                  # Chinese/English translations
├── settings_ui.py           # tkinter settings window
├── providers/
│   ├── __init__.py          # Provider registry
│   ├── base.py              # Abstract base provider
│   ├── openai_provider.py   # OpenAI implementation
│   └── deepseek_provider.py # DeepSeek implementation
├── requirements.txt
├── build.spec               # PyInstaller spec
└── README.md
```

### Adding a New Provider

1. Create a new file in `providers/` and subclass `BaseProvider`
2. Register in `providers/__init__.py`:

```python
from providers.gemini_provider import GeminiProvider
_PROVIDER_MAP["gemini"] = GeminiProvider
```

### License

MIT
