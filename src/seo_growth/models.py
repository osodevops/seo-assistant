from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from typing import Any


@dataclass(frozen=True)
class PageMetric:
    date: date
    page: str
    users: int
    sessions: int
    conversions: int = 0

    def as_dict(self) -> dict[str, Any]:
        return {**asdict(self), "date": self.date.isoformat()}


@dataclass(frozen=True)
class SearchMetric:
    date: date
    page: str
    query: str
    clicks: int
    impressions: int
    ctr: float
    position: float

    def as_dict(self) -> dict[str, Any]:
        return {**asdict(self), "date": self.date.isoformat()}


@dataclass(frozen=True)
class Opportunity:
    page: str
    query: str
    score: float
    clicks: int
    impressions: int
    ctr: float
    position: float
    reason: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SeoChange:
    page: str
    field: str
    old_value: str
    new_value: str
    reason: str


@dataclass(frozen=True)
class Experiment:
    page: str
    query: str
    change_id: int
    baseline_clicks: int
    baseline_impressions: int
    baseline_ctr: float
    started_on: date
    review_on: date
