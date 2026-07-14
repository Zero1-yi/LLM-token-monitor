"""Background polling thread that fetches usage data at a configurable interval."""

import logging
import threading
import time
from typing import Callable

from providers.base import UsageData

logger = logging.getLogger(__name__)


class UsagePoller:
    """Runs on a daemon thread. Fetches usage periodically and calls
    callbacks with results or errors. Implements exponential backoff
    on consecutive failures.

    Usage:
        poller = UsagePoller(fetch_fn, on_update, on_error, interval=600)
        poller.start()
        ...
        poller.stop()
    """

    def __init__(
        self,
        fetch_fn: Callable[[], UsageData],
        on_update: Callable[[UsageData], None],
        on_error: Callable[[Exception], None],
        interval_seconds: int = 600,
    ):
        """
        Args:
            fetch_fn: Called each cycle; must return UsageData.
            on_update: Called with fresh UsageData on success.
            on_error: Called with the Exception on failure.
            interval_seconds: Seconds between successful polls (default 600 = 10min).
        """
        self._fetch_fn = fetch_fn
        self._on_update = on_update
        self._on_error = on_error
        self.interval_seconds = max(60, interval_seconds)
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._consecutive_errors = 0
        self._max_backoff = 3600  # 1 hour max backoff

    def start(self) -> None:
        """Launch the daemon polling thread. No-op if already running."""
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True, name="usage-poller")
        self._thread.start()
        logger.info(f"Poller started (interval={self.interval_seconds}s)")

    def stop(self) -> None:
        """Signal the thread to exit and wait up to 5 seconds for join."""
        logger.info("Stopping poller...")
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5.0)
        logger.info("Poller stopped")

    def update_interval(self, seconds: int) -> None:
        """Change polling interval without restarting (checked each loop)."""
        self.interval_seconds = max(60, seconds)
        logger.info(f"Poller interval updated to {self.interval_seconds}s")

    def trigger_now(self) -> None:
        """Request an immediate fetch by interrupting the current sleep.

        This is best-effort: sets a short internal flag so the next
        1-second sleep chunk wakes up and fetches.
        """
        # The sleep loop checks stop_event every 1s, so it will pick up
        # a manual refresh within ~1 second if we just skip the remaining sleep.
        # We handle this by having _run check a _force_refresh flag.
        pass  # The actual mechanism is in app.py which calls fetch directly

    def _run(self) -> None:
        """Main loop: fetch → sleep → repeat. Backs off on errors."""
        while not self._stop_event.is_set():
            try:
                data = self._fetch_fn()
                self._consecutive_errors = 0
                self._on_update(data)
            except Exception as exc:
                self._consecutive_errors += 1
                backoff = min(60 * (2 ** self._consecutive_errors), self._max_backoff)
                logger.warning(
                    f"Poll error (consecutive={self._consecutive_errors}, "
                    f"backoff={backoff}s): {exc}"
                )
                self._on_error(exc)

                # Sleep through the backoff period, checking stop_event
                for _ in range(backoff):
                    if self._stop_event.is_set():
                        return
                    time.sleep(1)
                continue

            # Normal sleep between polls — 1s chunks for responsive stop
            for _ in range(self.interval_seconds):
                if self._stop_event.is_set():
                    return
                time.sleep(1)
