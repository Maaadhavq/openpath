from __future__ import annotations

import io
import struct
import wave

import pytest
from fastapi.testclient import TestClient

from server.config import Settings
from server.main import create_app

PASSCODE = "135790"
SARVAM = "https://api.sarvam.ai"


def make_wav(seconds: float = 1.5, rate: int = 16000) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(struct.pack("<h", 0) * int(seconds * rate))
    return buf.getvalue()


def settings(**kw) -> Settings:
    base = dict(sarvam_api_key="test-key", demo_passcode=PASSCODE, fake_sarvam=False, log_level="info")
    base.update(kw)
    return Settings(**base)


@pytest.fixture()
def client():
    # The teacher endpoints need the class code; it falls back to the demo passcode.
    with TestClient(create_app(settings()), headers={"X-Teacher-Code": PASSCODE}) as c:
        yield c


@pytest.fixture()
def fake_client():
    with TestClient(create_app(settings(fake_sarvam=True, sarvam_api_key=""))) as c:
        yield c


def talk(c: TestClient, question_id: str = "home", audio: bytes | None = None, passcode: str = PASSCODE, extra: dict | None = None, headers: dict | None = None):
    data = {"question_id": question_id, **(extra or {})}
    h = {"X-Demo-Passcode": passcode, **(headers or {})}
    return c.post("/api/talk", data=data, files={"audio": ("a.wav", audio if audio is not None else make_wav(), "audio/wav")}, headers=h)
