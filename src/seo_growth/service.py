from __future__ import annotations

from datetime import date, timedelta

from seo_growth.adapters.google import GoogleAnalyticsReader, SearchConsoleReader
from seo_growth.adapters.openai_recommender import OpenAiMetadataRecommender
from seo_growth.adapters.site_editor import HtmlSiteEditor
from seo_growth.config import Settings
from seo_growth.demo import demo_metrics
from seo_growth.models import Opportunity, SeoChange
from seo_growth.scoring import OpportunityScorer
from seo_growth.store import GrowthStore


class GrowthService:
    def __init__(self, settings: Settings, store: GrowthStore) -> None:
        self.settings = settings
        self.store = store
        self.scorer = OpportunityScorer()
        self.editor = HtmlSiteEditor(settings.site_directory, settings.site_url)

    def status(self) -> dict:
        return {
            "site": self.settings.site_url,
            "site_directory_ready": self.settings.site_directory.is_dir(),
            "google_analytics_ready": self.settings.google_ready,
            "search_console_ready": self.settings.search_console_ready,
            "openai_ready": self.settings.openai_ready,
            "auto_apply": self.settings.auto_apply,
        }

    def import_demo(self) -> dict:
        pages, searches = demo_metrics()
        self.store.save_page_metrics(pages)
        self.store.save_search_metrics(searches)
        return {"page_metrics": len(pages), "search_metrics": len(searches)}

    def sync_google(self, days: int = 28) -> dict:
        if not self.settings.google_credentials_path or not self.settings.google_credentials_path.is_file():
            raise ValueError("Google credentials have not been configured")
        end_date = date.today() - timedelta(days=3)
        start_date = end_date - timedelta(days=days - 1)
        page_metrics = []
        if self.settings.ga4_property_id:
            page_metrics = GoogleAnalyticsReader(
                self.settings.ga4_property_id, self.settings.google_credentials_path
            ).read(start_date, end_date)
            self.store.save_page_metrics(page_metrics)
        search_metrics = SearchConsoleReader(
            self.settings.search_console_site_url, self.settings.google_credentials_path
        ).read(start_date, end_date)
        self.store.save_search_metrics(search_metrics)
        return {"page_metrics": len(page_metrics), "search_metrics": len(search_metrics)}

    def opportunities(self) -> list[Opportunity]:
        return self.scorer.score(self.store.latest_search_metrics())

    def draft_metadata(self, opportunity_index: int) -> list[dict]:
        opportunities = self.opportunities()
        if opportunity_index < 0 or opportunity_index >= len(opportunities):
            raise IndexError("Opportunity does not exist")
        if not self.settings.openai_api_key:
            raise ValueError("OpenAI has not been configured")
        opportunity = opportunities[opportunity_index]
        metadata = self.editor.read_page(opportunity.page)
        draft = OpenAiMetadataRecommender(
            self.settings.openai_api_key, self.settings.openai_model
        ).draft(opportunity, metadata.title, metadata.description, metadata.visible_text)
        reason = f"Target '{opportunity.query}': {draft.rationale}"
        changes = [
            SeoChange(opportunity.page, "title", metadata.title, draft.title, reason),
            SeoChange(
                opportunity.page,
                "description",
                metadata.description,
                draft.description,
                reason,
            ),
        ]
        proposals = []
        for change in changes:
            change_id = self.store.propose_change(change)
            proposal = {"id": change_id, **change.__dict__, "status": "proposed"}
            if self.settings.auto_apply:
                self.apply_change(change_id)
                proposal["status"] = "applied"
            proposals.append(proposal)
        return proposals

    def apply_change(self, change_id: int) -> dict:
        record = self.store.get_change(change_id)
        if record is None:
            raise LookupError("Change does not exist")
        if record["status"] != "proposed":
            raise ValueError("Only proposed changes can be applied")
        change = SeoChange(
            page=record["page"],
            field=record["field"],
            old_value=record["old_value"],
            new_value=record["new_value"],
            reason=record["reason"],
        )
        path = self.editor.apply(change)
        self.store.mark_change_applied(change_id)
        return {"id": change_id, "file": str(path), "status": "applied"}
