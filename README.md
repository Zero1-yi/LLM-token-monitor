# LLM Token Monitor

Lightweight Windows system-tray application for monitoring LLM API token usage and billing.

## Features

- **System tray only** — no main window, lives in the notification area
- **Color-coded status** — Green (<50%) / Yellow (50-80%) / Red (>80%) circle icon
- **Hover tooltip** — Model name, token usage, remaining balance at a glance
- **Multi-provider** — Supports OpenAI (Dashboard Billing API) and DeepSeek (Balance API)
- **Auto-refresh** — Polls every 10 minutes (configurable 1–60 min)
- **Secure storage** — API keys encrypted via Windows DPAPI + Fernet
- **Lightweight** — ~15 MB packaged, minimal CPU/memory footprint

## Supported Providers

| Provider | API Endpoint | Key Type |
|----------|-------------|----------|
| OpenAI | Dashboard Billing API (`/dashboard/billing/subscription`, `/dashboard/billing/usage`) | Standard API key |
| DeepSeek | Balance API (`/user/balance`) | Standard API key |

## Installation

### Option 1: Run from source

```bash
# Clone or download the project
cd deepseek

# Install dependencies
pip install -r requirements.txt

# Run
python main.py
```

### Option 2: Build standalone .exe

```bash
pip install pyinstaller
pyinstaller build.spec --clean --noconfirm
# Output: dist/LLMTokenMonitor.exe
```

## Usage

1. **First launch** — Settings window opens automatically
2. Select your **Provider** (OpenAI or DeepSeek)
3. Select a **Model**
4. Enter your **API Key**
5. Click **Test Connection** to verify
6. Set your **Monthly Budget** and **Poll Interval**
7. Click **Save**

The app will minimize to the system tray and begin monitoring.

### Tray Icon Colors

- 🟢 **Green**: Less than 50% of budget used — all good
- 🟡 **Yellow**: 50–80% of budget used — approaching limit
- 🔴 **Red**: Over 80% of budget used — critical
- ⚫ **Gray**: No data / disconnected / error

### Right-Click Menu

- **Settings** (or double-click icon) — Open configuration
- **Refresh Now** — Force an immediate fetch
- **Quit** — Exit the application

## Configuration

Configuration is stored encrypted at:
```
%APPDATA%/LLMTokenMonitor/
├── .keyfile    (DPAPI-encrypted Fernet key)
└── config.enc  (Fernet-encrypted JSON settings)
```

## Project Structure

```
deepseek/
├── main.py                  # Entry point
├── app.py                   # Core TrayApp orchestrator
├── config.py                # Configuration manager
├── models.py                # Data models
├── secure_store.py          # DPAPI + Fernet encryption
├── poller.py                # Background polling thread
├── icons.py                 # Dynamic icon generation
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

## Adding a New Provider

1. Create a new file in `providers/` (e.g., `gemini_provider.py`)
2. Subclass `BaseProvider` and implement all abstract methods
3. Register in `providers/__init__.py`:

```python
from providers.gemini_provider import GeminiProvider
_PROVIDER_MAP["gemini"] = GeminiProvider
```

## License

MIT
