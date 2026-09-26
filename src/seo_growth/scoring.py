from __future__ import annotations

from collections.abc import Iterable
from datetime import date

from seo_growth.models import Opportunity, SearchMetric


class OpportunityScorer:
    _EXPECTED_CTR = {
        1: 0.28,
        2: 0.15,
        3: 0.11,
        4: 0.08,
        5: 0.07,
        6: 0.05,
        7: 0.04,
        8: 0.035,
        9: 0.03,
        10: 0.025,
    }

    def __init__(self, minimum_impressions: int = 20) -> None:
        self.minimum_impressions = minimum_impressions

    def score(self, metrics: Iterable[SearchMetric]) -> list[Opportunity]:
        opportunities = [self._score_metric(metric) for metric in self._aggregate(metrics)]
        return sorted(
            (item for item in opportunities if item is not None),
            key=lambda item: item.score,
            reverse=True,
        )

    @staticmethod
    def _aggregate(metrics: Iterable[SearchMetric]) -> list[SearchMetric]:
        totals: dict[tuple[str, str], dict[str, float | int | date]] = {}
        for metric in metrics:
            key = (metric.page, metric.query)
            total = totals.setdefault(
                key,
                {"date": metric.date, "clicks": 0, "impressions": 0, "weighted_position": 0.0},
            )
            total["date"] = max(total["date"], metric.date)
            total["clicks"] += metric.clicks
            total["impressions"] += metric.impressions
            total["weighted_position"] += metric.position * metric.impressions
        aggregated = []
        for (page, query), total in totals.items():
            impressions = int(total["impressions"])
            if impressions == 0:
                continue
            clicks = int(total["clicks"])
            aggregated.append(
                SearchMetric(
                    date=total["date"],
                    page=page,
                    query=query,
                    clicks=clicks,
                    impressions=impressions,
                    ctr=clicks / impressions,
                    position=float(total["weighted_position"]) / impressions,
                )
            )
        return aggregated

    def _score_metric(self, metric: SearchMetric) -> Opportunity | None:
        if metric.impressions < self.minimum_impressions or metric.position > 30:
            return None
        rank = max(1, min(10, round(metric.position)))
        expected_ctr = self._EXPECTED_CTR[rank] if metric.position <= 10 else 0.02
        missing_clicks = max(0.0, (expected_ctr - metric.ctr) * metric.impressions)
        near_page_one = max(0.0, 15.0 - abs(metric.position - 8.0))
        if metric.position <= 10:
            score = round(missing_clicks, 2)
        else:
            score = round(near_page_one * (metric.impressions ** 0.5) / 4, 2)
        if score <= 0:
            return None
        if metric.position <= 10 and metric.ctr < expected_ctr:
            reason = "High visibility but fewer clicks than expected; improve title and description."
        else:
            reason = "Ranks near page one; strengthen the page's relevance and internal links."
        return Opportunity(
            page=metric.page,
            query=metric.query,
            score=score,
            clicks=metric.clicks,
            impressions=metric.impressions,
            ctr=metric.ctr,
            position=metric.position,
            reason=reason,
        )
