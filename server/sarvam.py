"""Plain HTTP calls to the Sarvam API with httpx (async). The API key is sent only in the request header.

Checked against docs.sarvam.ai on 28 Nov 2026: speech-to-text (saaras:v4), chat completions (sarvam-105b,
reasoning returned separately in reasoning_content) and text-to-speech (bulbul:v4-flash).
"""
from __future__ import annotations

import asyncio
import base64
import json
import logging

import httpx

from .config import Settings

log = logging.getLogger("openpath.sarvam")

STT_TIMEOUT = 10.0
CHAT_TIMEOUT = 12.0
TTS_TIMEOUT = 10.0
RETRY_STATUSES = (429, 503)

# If the API ever rejects response_format or reasoning_effort, we drop them and rely on the prompt and the parser.
_chat_extras_ok = True


class SarvamError(Exception):
    def __init__(self, kind: str, status: int | None = None):
        super().__init__(f"{kind} ({status})" if status else kind)
        self.kind = kind
        self.status = status


async def _post(client: httpx.AsyncClient, settings: Settings, path: str, timeout: float, **kwargs) -> httpx.Response:
    headers = {"api-subscription-key": settings.sarvam_api_key}
    for attempt in (1, 2):
        try:
            r = await client.post(settings.sarvam_base + path, headers=headers, timeout=timeout, **kwargs)
        except httpx.TimeoutException as e:
            raise SarvamError("timeout") from e
        except httpx.HTTPError as e:
            raise SarvamError("network") from e
        if r.status_code in RETRY_STATUSES and attempt == 1:
            await asyncio.sleep(0.5)
            continue
        return r
    return r


async def transcribe(client: httpx.AsyncClient, settings: Settings, wav: bytes, keyterms: list[str] | None = None,
                     language_code: str = "ta-IN") -> dict:
    data = {"model": settings.stt_model, "mode": settings.stt_mode, "language_code": language_code}
    if keyterms:
        data["keyterms"] = json.dumps(keyterms[:50], ensure_ascii=False)
    r = await _post(client, settings, "/speech-to-text", STT_TIMEOUT, data=data, files={"file": ("answer.wav", wav, "audio/wav")})
    if r.status_code != 200:
        raise SarvamError("stt_http", r.status_code)
    body = r.json()
    return {"transcript": (body.get("transcript") or "").strip(), "language_code": body.get("language_code"), "request_id": body.get("request_id")}


async def chat(client: httpx.AsyncClient, settings: Settings, messages: list[dict], max_tokens: int = 300,
               timeout: float = CHAT_TIMEOUT, json_mode: bool = True) -> tuple[str, dict]:
    global _chat_extras_ok
    body = {"model": settings.llm_model, "messages": messages, "temperature": 0.2, "max_tokens": max_tokens}
    if _chat_extras_ok:
        if json_mode:
            body["response_format"] = {"type": "json_object"}
        body["reasoning_effort"] = None          # sarvam-105b reasons by default; None turns it off for speed
    r = await _post(client, settings, "/v1/chat/completions", timeout, json=body)
    if r.status_code in (400, 422) and _chat_extras_ok and ("response_format" in r.text or "reasoning_effort" in r.text):
        log.warning("chat rejected response_format/reasoning_effort (status %s); retrying without them", r.status_code)
        _chat_extras_ok = False
        body.pop("response_format", None)
        body.pop("reasoning_effort", None)
        r = await _post(client, settings, "/v1/chat/completions", timeout, json=body)
    if r.status_code != 200:
        raise SarvamError("chat_http", r.status_code)
    data = r.json()
    try:
        content = data["choices"][0]["message"].get("content") or ""
    except (KeyError, IndexError, TypeError) as e:
        raise SarvamError("chat_shape") from e
    usage = data.get("usage") or {}
    return content, {k: usage.get(k) for k in ("prompt_tokens", "completion_tokens", "total_tokens") if k in usage}


async def speak(client: httpx.AsyncClient, settings: Settings, text: str) -> bytes:
    body = {"text": text[:2500], "language_code": "ta-IN", "model": settings.tts_model, "speaker": settings.tts_speaker,
            "pace": 0.95, "speech_sample_rate": 24000, "output_audio_codec": "mp3"}
    r = await _post(client, settings, "/text-to-speech", TTS_TIMEOUT, json=body)
    if r.status_code != 200:
        raise SarvamError("tts_http", r.status_code)
    audios = r.json().get("audios") or []
    if not audios:
        raise SarvamError("tts_empty")
    return b"".join(base64.b64decode(a) for a in audios)
