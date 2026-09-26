from datetime import date, timedelta

from seo_growth.models import Experiment, SearchMetric, SeoChange
from seo_growth.store import GrowthStore


def test_store_persists_metrics_changes_and_experiments(tmp_path):
    store = GrowthStore(tmp_path / "growth.db")
    store.initialize()
    metric = SearchMetric(date.today(), "/", "kafka app", 1, 50, 0.02, 8.0)
    store.save_search_metrics([metric])

    change_id = store.propose_change(SeoChange("/", "title", "Old", "New", "Low CTR"))
    experiment_id = store.start_experiment(
        Experiment("/", "kafka app", change_id, 1, 50, 0.02, date.today(), date.today() + timedelta(days=28))
    )

    assert store.latest_search_metrics() == [metric]
    assert store.get_change(change_id)["status"] == "proposed"
    assert store.list_experiments()[0]["id"] == experiment_id


def test_latest_search_metrics_returns_only_latest_import(tmp_path):
    store = GrowthStore(tmp_path / "growth.db")
    store.initialize()
    first = SearchMetric(date.today(), "/first", "first", 1, 50, 0.02, 8.0)
    second = SearchMetric(date.today(), "/second", "second", 2, 60, 0.03, 7.0)
    store.save_search_metrics([first])
    store.save_search_metrics([second])

    assert store.latest_search_metrics() == [second]


def test_mark_change_applied_updates_status(tmp_path):
    store = GrowthStore(tmp_path / "growth.db")
    store.initialize()
    change_id = store.propose_change(SeoChange("/", "title", "Old", "New", "Test"))

    store.mark_change_applied(change_id)

    change = store.get_change(change_id)
    assert change["status"] == "applied"
    assert change["applied_at"] is not None
