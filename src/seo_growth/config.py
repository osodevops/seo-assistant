from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path

from dotenv import load_dotenv


def _boolean(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    site_url: str
    site_directory: Path
    database_path: Path
    ga4_property_id: str | None
    search_console_site_url: str
    google_credentials_path: Path | None
    openai_api_key: str | None
    openai_model: str
    auto_apply: bool

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv()
        credentials = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
        return cls(
            site_url=os.getenv("SEO_SITE_URL", "https://www.kafka-streamyard.com").rstrip("/"),
            site_directory=Path(os.getenv("SEO_SITE_DIRECTORY", "../kafka-streamyard-website")).resolve(),
            database_path=Path(os.getenv("SEO_DATABASE_PATH", "./seo-growth.db")).resolve(),
            ga4_property_id=os.getenv("SEO_GA4_PROPERTY_ID", "").strip() or None,
            search_console_site_url=os.getenv(
                "SEO_SEARCH_CONSOLE_SITE_URL", "https://www.kafka-streamyard.com/"
            ).strip(),
            google_credentials_path=Path(credentials).resolve() if credentials else None,
            openai_api_key=os.getenv("OPENAI_API_KEY", "").strip() or None,
            openai_model=os.getenv("SEO_OPENAI_MODEL", "gpt-4.1-mini").strip(),
            auto_apply=_boolean(os.getenv("SEO_AUTO_APPLY")),
        )

    @property
    def google_ready(self) -> bool:
        return bool(
            self.ga4_property_id
            and self.google_credentials_path
            and self.google_credentials_path.is_file()
        )

    @property
    def search_console_ready(self) -> bool:
        return bool(self.google_credentials_path and self.google_credentials_path.is_file())

    @property
    def openai_ready(self) -> bool:
        return self.openai_api_key is not None
