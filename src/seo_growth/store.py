from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from typing import Iterator

from seo_growth.models import Experiment, PageMetric, SearchMetric, SeoChange


class GrowthStore:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def initialize(self) -> None:
        with self._connection() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS metric_snapshots (
                    id INTEGER PRIMARY KEY,
                    source TEXT NOT NULL,
                    metric_date TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    imported_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS seo_changes (
                    id INTEGER PRIMARY KEY,
                    page TEXT NOT NULL,
                    field TEXT NOT NULL,
                    old_value TEXT NOT NULL,
                    new_value TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    applied_at TEXT
                );
                CREATE TABLE IF NOT EXISTS experiments (
                    id INTEGER PRIMARY KEY,
                    page TEXT NOT NULL,
                    query TEXT NOT NULL,
                    change_id INTEGER NOT NULL REFERENCES seo_changes(id),
                    baseline_clicks INTEGER NOT NULL,
                    baseline_impressions INTEGER NOT NULL,
                    baseline_ctr REAL NOT NULL,
                    started_on TEXT NOT NULL,
                    review_on TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'running'
                );
                """
            )

    def save_page_metrics(self, metrics: list[PageMetric]) -> None:
        self._save_metrics("ga4", [(metric.date.isoformat(), metric.as_dict()) for metric in metrics])

    def save_search_metrics(self, metrics: list[SearchMetric]) -> None:
        self._save_metrics("search_console", [(metric.date.isoformat(), metric.as_dict()) for metric in metrics])

    def _save_metrics(self, source: str, metrics: list[tuple[str, dict]]) -> None:
        imported_at = datetime.now(timezone.utc).isoformat()
        with self._connection() as connection:
            connection.executemany(
                "INSERT INTO metric_snapshots(source, metric_date, payload, imported_at) VALUES (?, ?, ?, ?)",
                [(source, metric_date, json.dumps(payload), imported_at) for metric_date, payload in metrics],
            )

    def latest_search_metrics(self, limit: int = 500) -> list[SearchMetric]:
        with self._connection() as connection:
            rows = connection.execute(
                """SELECT payload FROM metric_snapshots
                WHERE source = 'search_console'
                  AND imported_at = (SELECT MAX(imported_at) FROM metric_snapshots WHERE source = 'search_console')
                ORDER BY id DESC LIMIT ?""",
                (limit,),
            ).fetchall()
        return [SearchMetric(**self._decode_metric(row["payload"])) for row in rows]

    def propose_change(self, change: SeoChange) -> int:
        with self._connection() as connection:
            cursor = connection.execute(
                """INSERT INTO seo_changes(page, field, old_value, new_value, reason, status, created_at)
                VALUES (?, ?, ?, ?, ?, 'proposed', ?)""",
                (
                    change.page,
                    change.field,
                    change.old_value,
                    change.new_value,
                    change.reason,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            return int(cursor.lastrowid)

    def mark_change_applied(self, change_id: int) -> None:
        with self._connection() as connection:
            connection.execute(
                "UPDATE seo_changes SET status = 'applied', applied_at = ? WHERE id = ?",
                (datetime.now(timezone.utc).isoformat(), change_id),
            )

    def list_changes(self) -> list[dict]:
        with self._connection() as connection:
            rows = connection.execute("SELECT * FROM seo_changes ORDER BY id DESC").fetchall()
        return [dict(row) for row in rows]

    def get_change(self, change_id: int) -> dict | None:
        with self._connection() as connection:
            row = connection.execute("SELECT * FROM seo_changes WHERE id = ?", (change_id,)).fetchone()
        return dict(row) if row else None

    def start_experiment(self, experiment: Experiment) -> int:
        with self._connection() as connection:
            cursor = connection.execute(
                """INSERT INTO experiments(
                    page, query, change_id, baseline_clicks, baseline_impressions,
                    baseline_ctr, started_on, review_on
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    experiment.page,
                    experiment.query,
                    experiment.change_id,
                    experiment.baseline_clicks,
                    experiment.baseline_impressions,
                    experiment.baseline_ctr,
                    experiment.started_on.isoformat(),
                    experiment.review_on.isoformat(),
                ),
            )
            return int(cursor.lastrowid)

    def list_experiments(self) -> list[dict]:
        with self._connection() as connection:
            rows = connection.execute("SELECT * FROM experiments ORDER BY id DESC").fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def _decode_metric(payload: str) -> dict:
        data = json.loads(payload)
        from datetime import date

        data["date"] = date.fromisoformat(data["date"])
        return data
