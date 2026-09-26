from pathlib import Path

import pytest

from seo_growth.adapters.site_editor import HtmlSiteEditor
from seo_growth.models import SeoChange


HTML = """<!doctype html>
<html><head>
<title>Old title</title>
<meta name="description" content="Old description" />
</head><body><h1>Visible heading</h1></body></html>
"""


def make_editor(tmp_path: Path) -> HtmlSiteEditor:
    (tmp_path / "index.html").write_text(HTML, encoding="utf-8")
    return HtmlSiteEditor(tmp_path, "https://example.com")


def test_reads_root_url_as_index(tmp_path):
    metadata = make_editor(tmp_path).read_page("https://example.com/")

    assert metadata.title == "Old title"
    assert metadata.description == "Old description"
    assert "Visible heading" in metadata.visible_text


def test_applies_only_requested_metadata(tmp_path):
    editor = make_editor(tmp_path)

    path = editor.apply(SeoChange("/", "title", "Old title", "New & better", "Test"))

    updated = path.read_text(encoding="utf-8")
    assert "<title>New &amp; better</title>" in updated
    assert 'content="Old description"' in updated


def test_refuses_stale_change(tmp_path):
    editor = make_editor(tmp_path)

    with pytest.raises(ValueError, match="changed"):
        editor.apply(SeoChange("/", "title", "Different old title", "New", "Test"))


def test_refuses_path_outside_site(tmp_path):
    editor = make_editor(tmp_path)

    with pytest.raises(ValueError, match="outside"):
        editor.read_page("../secret.html")
