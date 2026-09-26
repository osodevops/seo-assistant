from __future__ import annotations

from dataclasses import dataclass
from html import unescape
from pathlib import Path
import re
import tempfile
from urllib.parse import urlparse

from seo_growth.models import SeoChange


_TITLE_PATTERN = re.compile(r"<title>(?P<value>.*?)</title>", re.IGNORECASE | re.DOTALL)
_DESCRIPTION_PATTERN = re.compile(
    r'(<meta\s+name=["\']description["\']\s+content=["\'])(?P<value>.*?)(["\']\s*/?>)',
    re.IGNORECASE | re.DOTALL,
)
_TAG_PATTERN = re.compile(r"<[^>]+>")


@dataclass(frozen=True)
class PageMetadata:
    file_path: Path
    title: str
    description: str
    visible_text: str


class HtmlSiteEditor:
    def __init__(self, site_directory: Path, site_url: str) -> None:
        self._site_directory = site_directory.resolve()
        self._site_url = site_url.rstrip("/")

    def read_page(self, page: str) -> PageMetadata:
        file_path = self._resolve_page(page)
        html = file_path.read_text(encoding="utf-8")
        title_match = _TITLE_PATTERN.search(html)
        description_match = _DESCRIPTION_PATTERN.search(html)
        if not title_match or not description_match:
            raise ValueError(f"Page must contain a title and meta description: {file_path.name}")
        visible_text = " ".join(unescape(_TAG_PATTERN.sub(" ", html)).split())
        return PageMetadata(
            file_path=file_path,
            title=unescape(title_match.group("value").strip()),
            description=unescape(description_match.group("value").strip()),
            visible_text=visible_text,
        )

    def apply(self, change: SeoChange) -> Path:
        metadata = self.read_page(change.page)
        html = metadata.file_path.read_text(encoding="utf-8")
        pattern = _TITLE_PATTERN if change.field == "title" else _DESCRIPTION_PATTERN
        match = pattern.search(html)
        if match is None or unescape(match.group("value").strip()) != change.old_value:
            raise ValueError("The page changed after this proposal was created; refusing to overwrite it")
        escaped_value = self._escape_attribute(change.new_value) if change.field == "description" else self._escape_text(change.new_value)
        start, end = match.span("value")
        updated = f"{html[:start]}{escaped_value}{html[end:]}"
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=metadata.file_path.parent, delete=False
        ) as temporary:
            temporary.write(updated)
            temporary_path = Path(temporary.name)
        temporary_path.replace(metadata.file_path)
        return metadata.file_path

    def _resolve_page(self, page: str) -> Path:
        parsed = urlparse(page)
        path = parsed.path if parsed.scheme else page
        relative = path.strip("/") or "index.html"
        if not Path(relative).suffix:
            relative = f"{relative}.html"
        candidate = (self._site_directory / relative).resolve()
        if not candidate.is_relative_to(self._site_directory):
            raise ValueError("Page path falls outside the configured website directory")
        if not candidate.is_file():
            raise FileNotFoundError(candidate)
        return candidate

    @staticmethod
    def _escape_text(value: str) -> str:
        return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    @classmethod
    def _escape_attribute(cls, value: str) -> str:
        return cls._escape_text(value).replace('"', "&quot;").replace("'", "&#x27;")
