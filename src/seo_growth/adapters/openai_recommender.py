from __future__ import annotations

from dataclasses import dataclass
import json

from openai import OpenAI

from seo_growth.models import Opportunity


@dataclass(frozen=True)
class MetadataDraft:
    title: str
    description: str
    rationale: str


class OpenAiMetadataRecommender:
    def __init__(self, api_key: str, model: str) -> None:
        self._client = OpenAI(api_key=api_key)
        self._model = model

    def draft(
        self,
        opportunity: Opportunity,
        current_title: str,
        current_description: str,
        page_text: str,
    ) -> MetadataDraft:
        response = self._client.chat.completions.create(
            model=self._model,
            response_format={"type": "json_object"},
            temperature=0.2,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You improve search snippets for Kafka Streamyard, a professional Kafka desktop app. "
                        "Return JSON with title, description, and rationale. Stay factual. Never invent features. "
                        "Keep title at most 60 characters and description at most 155 characters."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "target_query": opportunity.query,
                            "page": opportunity.page,
                            "current_title": current_title,
                            "current_description": current_description,
                            "visible_page_text": page_text[:6000],
                        }
                    ),
                },
            ],
        )
        payload = json.loads(response.choices[0].message.content or "{}")
        title = str(payload.get("title", "")).strip()
        description = str(payload.get("description", "")).strip()
        rationale = str(payload.get("rationale", "")).strip()
        if not title or not description:
            raise ValueError("OpenAI did not return a title and description")
        if len(title) > 60 or len(description) > 155:
            raise ValueError("OpenAI metadata exceeded the configured length limits")
        return MetadataDraft(title=title, description=description, rationale=rationale)
