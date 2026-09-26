from __future__ import annotations

from datetime import date
from pathlib import Path

from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import DateRange, Dimension, Metric, RunReportRequest
from google.oauth2 import service_account
from googleapiclient.discovery import build

from seo_growth.models import PageMetric, SearchMetric


class GoogleAnalyticsReader:
    def __init__(self, property_id: str, credentials_path: Path) -> None:
        credentials = service_account.Credentials.from_service_account_file(str(credentials_path))
        self._client = BetaAnalyticsDataClient(credentials=credentials)
        self._property_id = property_id.removeprefix("properties/")

    def read(self, start_date: date, end_date: date) -> list[PageMetric]:
        response = self._client.run_report(
            RunReportRequest(
                property=f"properties/{self._property_id}",
                dimensions=[Dimension(name="date"), Dimension(name="pagePath")],
                metrics=[
                    Metric(name="activeUsers"),
                    Metric(name="sessions"),
                    Metric(name="keyEvents"),
                ],
                date_ranges=[DateRange(start_date=start_date.isoformat(), end_date=end_date.isoformat())],
                limit=10000,
            )
        )
        return [
            PageMetric(
                date=date.fromisoformat(f"{row.dimension_values[0].value[:4]}-{row.dimension_values[0].value[4:6]}-{row.dimension_values[0].value[6:8]}"),
                page=row.dimension_values[1].value,
                users=int(float(row.metric_values[0].value or 0)),
                sessions=int(float(row.metric_values[1].value or 0)),
                conversions=int(float(row.metric_values[2].value or 0)),
            )
            for row in response.rows
        ]


class SearchConsoleReader:
    _SCOPES = ["https://www.googleapis.com/auth/webmasters.readonly"]

    def __init__(self, site_url: str, credentials_path: Path) -> None:
        credentials = service_account.Credentials.from_service_account_file(
            str(credentials_path), scopes=self._SCOPES
        )
        self._service = build("searchconsole", "v1", credentials=credentials, cache_discovery=False)
        self._site_url = site_url

    def read(self, start_date: date, end_date: date) -> list[SearchMetric]:
        response = (
            self._service.searchanalytics()
            .query(
                siteUrl=self._site_url,
                body={
                    "startDate": start_date.isoformat(),
                    "endDate": end_date.isoformat(),
                    "dimensions": ["date", "page", "query"],
                    "rowLimit": 25000,
                    "dataState": "final",
                },
            )
            .execute()
        )
        return [
            SearchMetric(
                date=date.fromisoformat(row["keys"][0]),
                page=row["keys"][1],
                query=row["keys"][2],
                clicks=int(row.get("clicks", 0)),
                impressions=int(row.get("impressions", 0)),
                ctr=float(row.get("ctr", 0)),
                position=float(row.get("position", 0)),
            )
            for row in response.get("rows", [])
        ]
