"""Settings from environment variables. Locally, a git-ignored .env file in the repo root is read too."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP_DIR = ROOT / "app"
TEACHER_DIR = ROOT / "teacher"
DATA_DIR = APP_DIR / "data"
VERSION = "2026-11-28"


def _load_dotenv(path: Path) -> None:
    """Minimal .env reader (KEY=value lines). Real environment variables win."""
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


@dataclass
class Settings:
    sarvam_api_key: str = ""
    demo_passcode: str = ""
    fake_sarvam: bool = False
    stt_model: str = "saaras:v4"
    stt_mode: str = "transcribe"
    stt_keyterms: bool = False
    llm_model: str = "sarvam-105b"
    tts_model: str = "bulbul:v4-flash"
    tts_speaker: str = ""
    log_level: str = "info"
    sarvam_base: str = "https://api.sarvam.ai"
    talk_per_minute: int = 20


def load_settings() -> Settings:
    if os.environ.get("OPENPATH_NO_DOTENV") != "1":
        _load_dotenv(ROOT / ".env")
    env = os.environ.get
    return Settings(
        sarvam_api_key=env("SARVAM_API_KEY", ""),
        demo_passcode=env("DEMO_PASSCODE", ""),
        fake_sarvam=env("FAKE_SARVAM", "0").strip() in ("1", "true", "yes"),
        stt_model=env("STT_MODEL", "saaras:v4"),
        stt_mode=env("STT_MODE", "transcribe"),
        stt_keyterms=env("STT_KEYTERMS", "0").strip() in ("1", "true", "yes"),
        llm_model=env("LLM_MODEL", "sarvam-105b"),
        tts_model=env("TTS_MODEL", "bulbul:v4-flash"),
        tts_speaker=env("TTS_SPEAKER", ""),
        log_level=env("LOG_LEVEL", "info"),
        sarvam_base=env("SARVAM_BASE", "https://api.sarvam.ai").rstrip("/"),
        talk_per_minute=int(env("TALK_PER_MINUTE", "20")),
    )
