"""LLM Token Usage Monitor — Windows system tray application.

Monitors token usage and billing for OpenAI and DeepSeek APIs.
Lives in the system tray with color-coded status indicators.

Usage:
    python main.py          # Run normally
    pythonw main.py         # Run without console window (Windows)
"""

import logging
import os
import sys
from pathlib import Path

# Fix SSL certificate issues on Anaconda Python (missing cert.pem)
# Must run BEFORE any httpx/requests imports
try:
    import certifi
    os.environ.setdefault("SSL_CERT_FILE", certifi.where())
except ImportError:
    pass


def setup_logging() -> None:
    """Configure file + console logging."""
    log_dir = Path(__file__).parent / "logs"
    log_dir.mkdir(exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(
                log_dir / "monitor.log", encoding="utf-8", mode="a"
            ),
        ],
    )

    # Also log to stdout if not running via pythonw (no console)
    if sys.stdout and hasattr(sys.stdout, "fileno"):
        try:
            logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))
        except Exception:
            pass


def main() -> None:
    """Application entry point."""
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("=" * 50)
    logger.info("LLM Token Monitor starting...")

    try:
        from app import TrayApp

        app = TrayApp()
        app.run()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    except Exception:
        logger.exception("Fatal error — application terminated")
        raise
    finally:
        logger.info("LLM Token Monitor shutdown complete")


if __name__ == "__main__":
    main()
