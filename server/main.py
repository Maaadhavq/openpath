"""OpenPath server: the student app at /, the teacher dashboard at /teacher, and the API under /api. One origin."""
from __future__ import annotations

import logging
import mimetypes

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .config import APP_DIR, TEACHER_DIR, VERSION, Settings, load_settings

# Windows can map .js to text/plain, which breaks module scripts. Set the types we serve explicitly.
for ext, mime in {".js": "text/javascript", ".mjs": "text/javascript", ".css": "text/css", ".json": "application/json",
                  ".webmanifest": "application/manifest+json", ".mp3": "audio/mpeg", ".png": "image/png", ".svg": "image/svg+xml"}.items():
    mimetypes.add_type(mime, ext)

log = logging.getLogger("openpath")


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()
    logging.basicConfig(level=settings.log_level.upper(), format="%(asctime)s %(levelname)s %(name)s %(message)s")
    app = FastAPI(title="OpenPath", version=VERSION, docs_url=None, redoc_url=None, openapi_url=None)
    app.state.settings = settings

    @app.get("/api/health")
    def health():
        return {"ok": True, "version": VERSION, "fake": settings.fake_sarvam,
                "models": {"stt": settings.stt_model, "llm": settings.llm_model, "tts": settings.tts_model}}

    app.mount("/teacher", StaticFiles(directory=TEACHER_DIR, html=True), name="teacher")
    app.mount("/", StaticFiles(directory=APP_DIR, html=True), name="app")
    return app


app = create_app()
