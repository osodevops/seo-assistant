from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

from seo_growth.config import Settings
from seo_growth.service import GrowthService
from seo_growth.store import GrowthStore


STATIC_DIRECTORY = Path(__file__).parent / "static"


def create_app(settings: Settings | None = None) -> FastAPI:
    app_settings = settings or Settings.from_env()
    store = GrowthStore(app_settings.database_path)
    service = GrowthService(app_settings, store)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        store.initialize()
        yield

    app = FastAPI(title="SEO Growth Assistant", lifespan=lifespan)
    app.mount("/static", StaticFiles(directory=STATIC_DIRECTORY), name="static")

    @app.get("/", include_in_schema=False)
    def dashboard():
        return FileResponse(STATIC_DIRECTORY / "index.html")

    @app.get("/healthz", include_in_schema=False)
    def health():
        return {"status": "ok"}

    @app.get("/api/status")
    def status():
        return service.status()

    @app.get("/api/opportunities")
    def opportunities():
        return [item.as_dict() for item in service.opportunities()]

    @app.get("/api/changes")
    def changes():
        return store.list_changes()

    @app.post("/api/import/demo")
    def import_demo():
        return service.import_demo()

    @app.post("/api/sync/google")
    def sync_google():
        try:
            return service.sync_google()
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error

    @app.post("/api/opportunities/{opportunity_index}/draft")
    def draft(opportunity_index: int):
        try:
            return service.draft_metadata(opportunity_index)
        except (IndexError, ValueError, FileNotFoundError) as error:
            raise HTTPException(status_code=400, detail=str(error)) from error

    @app.post("/api/changes/{change_id}/apply")
    def apply(change_id: int):
        try:
            return service.apply_change(change_id)
        except LookupError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except (ValueError, FileNotFoundError) as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    return app


app = create_app()


def run() -> None:
    uvicorn.run("seo_growth.main:app", host="127.0.0.1", port=8765, reload=False)
