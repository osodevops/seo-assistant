from datetime import date

from seo_growth.models import SearchMetric
from seo_growth.scoring import OpportunityScorer


def test_scores_low_ctr_query_with_meaningful_impressions_first():
    metrics = [
        SearchMetric(date.today(), "/strong", "strong query", 28, 100, 0.28, 1),
        SearchMetric(date.today(), "/weak", "weak query", 2, 200, 0.01, 7),
        SearchMetric(date.today(), "/small", "small query", 0, 10, 0, 8),
    ]

    opportunities = OpportunityScorer().score(metrics)

    assert [item.query for item in opportunities] == ["weak query"]
    assert opportunities[0].score > 0
    assert "title and description" in opportunities[0].reason


def test_aggregates_daily_rows_before_scoring():
    metrics = [
        SearchMetric(date(2026, 9, 1), "/docs", "kafka filter", 1, 40, 0.025, 12),
        SearchMetric(date(2026, 9, 2), "/docs", "kafka filter", 2, 60, 0.033, 10),
    ]

    opportunity = OpportunityScorer().score(metrics)[0]

    assert opportunity.clicks == 3
    assert opportunity.impressions == 100
    assert opportunity.ctr == 0.03
    assert opportunity.position == 10.8


def test_scores_near_page_one_content_opportunity():
    metric = SearchMetric(date.today(), "/docs", "kafka filter", 1, 100, 0.01, 12)

    opportunity = OpportunityScorer().score([metric])[0]

    assert opportunity.page == "/docs"
    assert "page one" in opportunity.reason
