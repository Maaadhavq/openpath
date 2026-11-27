"""Speech to an answer option: Saaras v4 transcript -> Sarvam-105B picks one option -> validate -> keyword fallback.

The model only maps speech to one of the fixed options. It never sees a profile, and it never decides eligibility.
Audio and transcripts stay in memory: nothing here writes them to disk or to the logs.
"""
from __future__ import annotations

import json
import re
import struct
import time
import unicodedata
from functools import lru_cache

import httpx

from . import sarvam
from .config import DATA_DIR, Settings
from .prompts import build_messages

MAX_AUDIO_BYTES = 1_500_000
MAX_AUDIO_SECONDS = 25.0
TOTAL_BUDGET_S = 14.0           # the phone gives up after 15 s, so answer before that


@lru_cache(maxsize=1)
def questions() -> dict[str, dict]:
    data = json.loads((DATA_DIR / "questions.json").read_text(encoding="utf-8"))
    return {q["id"]: q for q in data}


class BadAudio(ValueError):
    pass


def wav_seconds(data: bytes) -> float:
    """Duration of a RIFF/WAV file from its fmt and data chunks. Raises BadAudio if it is not a WAV."""
    if len(data) < 44 or data[:4] != b"RIFF" or data[8:12] != b"WAVE":
        raise BadAudio("not a WAV file")
    pos, byte_rate, data_size = 12, None, None
    while pos + 8 <= len(data):
        cid, size = data[pos:pos + 4], struct.unpack("<I", data[pos + 4:pos + 8])[0]
        if cid == b"fmt " and size >= 16:
            byte_rate = struct.unpack("<I", data[pos + 16:pos + 20])[0]
        elif cid == b"data":
            data_size = min(size, len(data) - pos - 8)
            break
        pos += 8 + size + (size & 1)
    if not byte_rate or data_size is None:
        raise BadAudio("WAV without fmt or data chunk")
    return data_size / byte_rate


def normalise(text: str) -> str:
    """Unicode NFC, lower case, no punctuation, single spaces."""
    text = unicodedata.normalize("NFC", text or "").lower()
    text = "".join(" " if unicodedata.category(ch).startswith("P") else ch for ch in text)
    return re.sub(r"\s+", " ", text).strip()


def keyword_suggestion(question: dict, transcript: str) -> dict | None:
    """The prototype's listen() matching: one option's keyword in the transcript -> that option, else nothing."""
    said = normalise(transcript)
    hits = []
    for o in question["opts"]:
        kw = next((k for k in o["kw"] if normalise(k) and normalise(k) in said), None)
        if kw:
            hits.append((o["id"], kw))
    if len(hits) != 1:
        return None
    return {"option_id": hits[0][0], "confidence": 0.6, "evidence": hits[0][1], "source": "keywords"}


class InvalidReply(ValueError):
    pass


def parse_reply(content: str, question: dict) -> dict | None:
    """Validates the model's JSON. Returns a suggestion, None for 'nothing matches', or raises InvalidReply."""
    text = re.sub(r"<think>.*?</think>", "", content or "", flags=re.S).strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.I).strip()
    m = re.search(r"\{.*\}", text, flags=re.S)
    if not m:
        raise InvalidReply("no JSON object")
    try:
        obj = json.loads(m.group(0))
    except json.JSONDecodeError as e:
        raise InvalidReply("bad JSON") from e
    if not isinstance(obj, dict) or "option_id" not in obj:
        raise InvalidReply("no option_id")
    oid = obj.get("option_id")
    if oid in ("", "null", "none"):
        oid = None
    if oid is not None and oid not in {o["id"] for o in question["opts"]}:
        raise InvalidReply("unknown option id")
    try:
        conf = float(obj.get("confidence", 0))
    except (TypeError, ValueError):
        conf = 0.0
    conf = min(1.0, max(0.0, conf))
    if oid is None:
        return None
    evidence = obj.get("evidence") if isinstance(obj.get("evidence"), str) else ""
    return {"option_id": oid, "confidence": round(conf, 3), "evidence": evidence[:120], "source": "llm"}


def keyterms_for(question: dict) -> list[str]:
    terms = []
    for o in question["opts"]:
        for t in [o["label"]["ta"], *o["kw"]]:
            if t not in terms and len(t) <= 64:
                terms.append(t)
    return terms[:50]


FAKE = {
    "home": ("நான் எங்க கடையில கணக்கு எழுதுவேன்", "accounts", "கடையில கணக்கு"),
    "school": ("எனக்கு அறிவியல் ரொம்ப பிடிக்கும்", "science", "அறிவியல்"),
    "style": ("மத்தவங்களுக்கு உதவி செய்யப் பிடிக்கும்", "help", "உதவி செய்ய"),
}


def fake_result(settings: Settings, question_id: str) -> dict:
    said, oid, ev = FAKE[question_id]
    return {"transcript": said, "language_code": "ta-IN",
            "suggestion": {"option_id": oid, "confidence": 0.9, "evidence": ev, "source": "fake"},
            "timings_ms": {"stt": 0, "llm": 0, "total": 0},
            "models": {"stt": settings.stt_model, "llm": settings.llm_model}, "fake": True}


class STTFailed(Exception):
    def __init__(self, kind: str):
        super().__init__(kind)
        self.kind = kind


async def run_talk(client: httpx.AsyncClient, settings: Settings, wav: bytes, question_id: str, use_keyterms: bool = False) -> dict:
    q = questions()[question_id]
    t0 = time.perf_counter()
    try:
        stt = await sarvam.transcribe(client, settings, wav, keyterms_for(q) if use_keyterms else None)
    except sarvam.SarvamError as e:
        raise STTFailed(e.kind) from e
    t1 = time.perf_counter()
    transcript = stt["transcript"]
    usage, llm_error, suggestion = {}, None, None
    if transcript:
        budget = max(2.0, min(sarvam.CHAT_TIMEOUT, TOTAL_BUDGET_S - (t1 - t0)))
        try:
            content, usage = await sarvam.chat(client, settings, build_messages(questions(), question_id, transcript), timeout=budget)
            suggestion = parse_reply(content, q)
        except (sarvam.SarvamError, InvalidReply) as e:
            llm_error = getattr(e, "kind", None) or type(e).__name__
            suggestion = keyword_suggestion(q, transcript)
    t2 = time.perf_counter()
    return {"transcript": transcript, "language_code": stt.get("language_code") or "ta-IN", "suggestion": suggestion,
            "timings_ms": {"stt": round((t1 - t0) * 1000), "llm": round((t2 - t1) * 1000), "total": round((t2 - t0) * 1000)},
            "models": {"stt": settings.stt_model, "llm": settings.llm_model}, "fake": False,
            "_usage": usage, "_llm_error": llm_error}
