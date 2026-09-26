from fastapi.testclient import TestClient

from seo_growth.config import Settings
from seo_growth.main import create_app


def settings(tmp_path):
    site = tmp_path / "site"
    site.mkdir()
    (site / "index.html").write_text(
        '<html><head><title>Title</title><meta name="description" content="Description"></head><body>Page</body></html>',
        encoding="utf-8",
    )
    return Settings(
        site_url="https://example.com",
        site_directory=site,
        database_path=tmp_path / "growth.db",
        ga4_property_id=None,
        search_console_site_url="https://example.com/",
        google_credentials_path=None,
        openai_api_key=None,
        openai_model="gpt-4.1-mini",
        auto_apply=False,
    )


def test_dashboard_and_demo_flow(tmp_path):
    with TestClient(create_app(settings(tmp_path))) as client:
        assert client.get("/").status_code == 200
        assert client.get("/healthz").json() == {"status": "ok"}
        status = client.get("/api/status").json()
        assert status["site_directory_ready"] is True
        assert status["google_analytics_ready"] is False

        imported = client.post("/api/import/demo").json()
        opportunities = client.get("/api/opportunities").json()

    assert imported == {"page_metrics": 3, "search_metrics": 3}
    assert len(opportunities) == 3


def test_google_sync_explains_missing_setup(tmp_path):
    with TestClient(create_app(settings(tmp_path))) as client:
        response = client.post("/api/sync/google")

    assert response.status_code == 400
    assert response.json()["detail"] == "Google credentials have not been configured"
