"""OpenPath server: the student app at /, the teacher dashboard at /teacher, and the API under /api. One origin."""
from __future__ import annotations

import hmac
import logging
import mimetypes
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.datastructures import UploadFile
from starlette.formparsers import MultiPartParser

from . import ask, talk
from .config import APP_DIR, TEACHER_DIR, VERSION, Settings, load_settings
from .schemas import AskBody, SyncBody
from .store import ClassStore

# Windows can map .js to text/plain, which breaks module scripts. Set the types we serve explicitly.
for ext, mime in {".js": "text/javascript", ".mjs": "text/javascript", ".css": "text/css", ".json": "application/json",
                  ".webmanifest": "application/manifest+json", ".mp3": "audio/mpeg", ".png": "image/png", ".svg": "image/svg+xml"}.items():
    mimetypes.add_type(mime, ext)

# Uploaded audio stays in memory: by default Starlette spools uploads over 1 MB to a temporary file on disk.
MultiPartParser.spool_max_size = 2 * 1024 * 1024
MAX_TALK_BODY = 1_600_000       # the WAV (1.5 MB at most) plus the form overhead

log = logging.getLogger("openpath")


class RateLimiter:
    """In-memory sliding window: at most `limit` requests per `window` seconds per key."""

    def __init__(self, limit: int, window: float = 60.0):
        self.limit, self.window = limit, window
        self.hits: dict[str, deque] = defaultdict(deque)

    def allow(self, key: str) -> bool:
        now, q = time.monotonic(), self.hits[key]
        while q and now - q[0] > self.window:
            q.popleft()
        if len(q) >= self.limit:
            return False
        q.append(now)
        return True


def client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def error(status: int, code: str, **extra) -> JSONResponse:
    return JSONResponse({"error": code, **extra}, status_code=status)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()
    logging.basicConfig(level=settings.log_level.upper(), format="%(asctime)s %(levelname)s %(name)s %(message)s")
    if not settings.demo_passcode:
        log.warning("DEMO_PASSCODE is not set: /api/talk and /api/reset will refuse every request")
    if not settings.fake_sarvam and not settings.sarvam_api_key:
        log.warning("SARVAM_API_KEY is not set and FAKE_SARVAM is off: voice answers will fail and the app falls back to taps")

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.http = httpx.AsyncClient()       # one client, so the TLS connection to Sarvam is reused
        yield
        await app.state.http.aclose()

    app = FastAPI(title="OpenPath", version=VERSION, docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)
    app.state.settings = settings
    limiter = RateLimiter(settings.talk_per_minute)
    ask_limiter = RateLimiter(30)
    sync_limiter = RateLimiter(settings.sync_per_minute)
    wrong_codes = RateLimiter(20)              # at most 20 wrong teacher codes a minute per address
    store = ClassStore()
    app.state.store = store
    teacher_code = settings.teacher_code or settings.demo_passcode

    def passcode_ok(request: Request) -> bool:
        given = request.headers.get("x-demo-passcode", "")
        return bool(settings.demo_passcode) and hmac.compare_digest(given.encode(), settings.demo_passcode.encode())

    def teacher_ok(request: Request) -> bool:
        given = request.headers.get("x-teacher-code", "")
        return bool(teacher_code) and hmac.compare_digest(given.encode(), teacher_code.encode())

    def teacher_guard(request: Request) -> JSONResponse | None:
        """The teacher pages show student names, so they need the class code."""
        if not teacher_code:
            return error(503, "teacher_code_not_set", detail="Set TEACHER_CODE (or DEMO_PASSCODE) on the server.")
        if teacher_ok(request):
            return None
        if not wrong_codes.allow(client_ip(request)):
            return error(429, "rate_limited")
        return error(401, "bad_teacher_code")

    @app.get("/api/health")
    def health():
        return {"ok": True, "version": VERSION, "fake": settings.fake_sarvam,
                "passcode_set": bool(settings.demo_passcode), "teacher_code_set": bool(teacher_code),
                "models": {"stt": settings.stt_model, "llm": settings.llm_model, "tts": settings.tts_model}}

    @app.post("/api/talk")
    async def api_talk(request: Request):
        if not limiter.allow(client_ip(request)):
            return error(429, "rate_limited")
        if not passcode_ok(request):
            return error(401, "bad_passcode")
        try:
            if int(request.headers.get("content-length") or 0) > MAX_TALK_BODY:
                return error(413, "too_large")
        except ValueError:
            return error(422, "bad_input")
        try:
            form = await request.form(max_files=1, max_fields=2, max_part_size=64 * 1024)
        except Exception:
            return error(422, "bad_input", detail="send multipart/form-data with audio and question_id only")
        if set(form.keys()) != {"audio", "question_id"}:
            return error(422, "bad_fields", allowed=["audio", "question_id"])
        audio, qid = form.get("audio"), form.get("question_id")
        if not isinstance(audio, UploadFile) or not isinstance(qid, str) or qid not in talk.questions():
            return error(422, "bad_input")
        wav = await audio.read()
        await form.close()
        if len(wav) > talk.MAX_AUDIO_BYTES:
            return error(413, "too_large")
        try:
            seconds = talk.wav_seconds(wav)
        except talk.BadAudio:
            return error(422, "bad_audio", detail="audio must be a WAV file")
        if seconds > talk.MAX_AUDIO_SECONDS:
            return error(413, "too_long")

        if settings.fake_sarvam:
            log.info("talk fake q=%s bytes=%d seconds=%.1f", qid, len(wav), seconds)
            return talk.fake_result(settings, qid)
        if not settings.sarvam_api_key:
            log.error("talk failed q=%s: no SARVAM_API_KEY", qid)
            return error(502, "stt_failed", fallback="tap")
        client = getattr(request.app.state, "http", None)
        own = client is None
        if own:
            client = httpx.AsyncClient()
        try:
            res = await talk.run_talk(client, settings, wav, qid, use_keyterms=settings.stt_keyterms)
        except talk.STTFailed as e:
            log.warning("talk stt_failed q=%s bytes=%d seconds=%.1f kind=%s", qid, len(wav), seconds, e.kind)
            return error(502, "stt_failed", fallback="tap")
        finally:
            if own:
                await client.aclose()
            del wav
        usage, llm_error = res.pop("_usage"), res.pop("_llm_error")
        sug = res["suggestion"]
        log.info("talk ok q=%s seconds=%.1f stt_ms=%d llm_ms=%d total_ms=%d source=%s llm_error=%s",
                 qid, seconds, res["timings_ms"]["stt"], res["timings_ms"]["llm"], res["timings_ms"]["total"],
                 sug["source"] if sug else "none", llm_error or "-")
        if request.headers.get("x-debug") == "1":
            res["usage"] = {"audio_seconds": round(seconds, 2), "llm": usage, "llm_error": llm_error}
        return res

    @app.post("/api/sync")
    async def api_sync(body: SyncBody, request: Request):
        if not sync_limiter.allow(client_ip(request)):
            return error(429, "rate_limited")        # the phone keeps the events and retries
        accepted, duplicates = store.apply(body.events)
        log.info("sync accepted=%d duplicates=%d", len(accepted), len(duplicates))
        return {"accepted": accepted, "duplicates": duplicates}

    @app.get("/api/class")
    async def api_class(request: Request):
        if (denied := teacher_guard(request)) is not None:
            return denied
        snap = store.snapshot()
        snap["suggestions"] = ask.SUGGESTIONS
        return JSONResponse(snap, headers={"Cache-Control": "no-store"})

    @app.get("/api/student/{roll}")
    async def api_student(roll: str, request: Request):
        if (denied := teacher_guard(request)) is not None:
            return denied
        d = store.detail(roll)
        if d is None:
            return error(404, "unknown_student")
        return JSONResponse(d, headers={"Cache-Control": "no-store"})

    @app.post("/api/ask")
    async def api_ask(body: AskBody, request: Request):
        if (denied := teacher_guard(request)) is not None:
            return denied
        if not ask_limiter.allow(client_ip(request)):
            return error(429, "rate_limited")
        students = store.students()
        return await ask.answer(getattr(request.app.state, "http", None), settings, body.question, body.lang, students, store.summary(students))

    @app.post("/api/reset")
    async def api_reset(request: Request):
        if not (passcode_ok(request) or teacher_ok(request)):
            return error(401, "bad_passcode")
        store.reset()
        log.info("reset: class store re-seeded")
        return {"ok": True}

    app.mount("/teacher", StaticFiles(directory=TEACHER_DIR, html=True), name="teacher")
    app.mount("/", StaticFiles(directory=APP_DIR, html=True), name="app")
    return app


app = create_app()
