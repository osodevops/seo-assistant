from __future__ import annotations

from collections.abc import Callable
import logging
import os
from threading import Event

from seo_growth.config import Settings
from seo_growth.service import GrowthService
from seo_growth.store import GrowthStore


logger = logging.getLogger(__name__)


class SyncScheduler:
    def __init__(
        self,
        sync: Callable[[], dict],
        interval_seconds: float,
        stop_event: Event | None = None,
    ) -> None:
        if interval_seconds <= 0:
            raise ValueError("Sync interval must be greater than zero")
        self._sync = sync
        self._interval_seconds = interval_seconds
        self._stop_event = stop_event or Event()

    def run_forever(self) -> None:
        while not self._stop_event.is_set():
            try:
                result = self._sync()
                logger.info(
                    "Google sync completed: page_metrics=%s search_metrics=%s",
                    result["page_metrics"],
                    result["search_metrics"],
                )
            except ValueError as error:
                logger.warning("Google sync skipped: %s; the scheduler will retry", error)
            except Exception:
                logger.exception("Google sync failed; the scheduler will retry")
            self._stop_event.wait(self._interval_seconds)


def run() -> None:
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO").upper())
    settings = Settings.from_env()
    store = GrowthStore(settings.database_path)
    store.initialize()
    interval_hours = float(os.getenv("SEO_SYNC_INTERVAL_HOURS", "24"))
    SyncScheduler(
        GrowthService(settings, store).sync_google,
        interval_seconds=interval_hours * 60 * 60,
    ).run_forever()


if __name__ == "__main__":
    run()
