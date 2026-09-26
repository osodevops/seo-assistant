from threading import Event

import pytest

from seo_growth.scheduler import SyncScheduler


def test_scheduler_syncs_immediately_and_stops_cleanly():
    stop_event = Event()
    calls = []

    def sync():
        calls.append("sync")
        stop_event.set()
        return {"page_metrics": 3, "search_metrics": 5}

    SyncScheduler(sync, interval_seconds=3600, stop_event=stop_event).run_forever()

    assert calls == ["sync"]


def test_scheduler_reports_missing_setup_without_traceback(caplog):
    stop_event = Event()

    def missing_setup():
        stop_event.set()
        raise ValueError("Google credentials have not been configured")

    SyncScheduler(missing_setup, interval_seconds=3600, stop_event=stop_event).run_forever()

    assert "Google sync skipped" in caplog.text
    assert "Traceback" not in caplog.text


def test_scheduler_survives_sync_failure(caplog):
    stop_event = Event()

    def failing_sync():
        stop_event.set()
        raise RuntimeError("temporary failure")

    SyncScheduler(failing_sync, interval_seconds=3600, stop_event=stop_event).run_forever()

    assert "scheduler will retry" in caplog.text


def test_scheduler_rejects_non_positive_interval():
    with pytest.raises(ValueError, match="greater than zero"):
        SyncScheduler(lambda: {}, interval_seconds=0)
