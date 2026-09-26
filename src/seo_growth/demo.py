from __future__ import annotations

from datetime import date, timedelta

from seo_growth.models import PageMetric, SearchMetric


def demo_metrics() -> tuple[list[PageMetric], list[SearchMetric]]:
    today = date.today() - timedelta(days=3)
    pages = [
        PageMetric(today, "/", users=42, sessions=49, conversions=2),
        PageMetric(today, "/features.html", users=23, sessions=26, conversions=1),
        PageMetric(today, "/docs.html", users=61, sessions=68, conversions=0),
    ]
    searches = [
        SearchMetric(today, "https://www.kafka-streamyard.com/", "kafka desktop app", 4, 240, 0.0167, 7.2),
        SearchMetric(today, "https://www.kafka-streamyard.com/features.html", "kafka testing tool", 2, 180, 0.0111, 9.4),
        SearchMetric(today, "https://www.kafka-streamyard.com/docs.html", "kafka message filter", 1, 95, 0.0105, 12.1),
    ]
    return pages, searches
