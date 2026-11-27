"""/api/talk: speech -> transcript -> one option, with Sarvam mocked by respx."""
from __future__ import annotations

import json
import logging

import httpx
import pytest
import respx

from server import talk as talk_mod
from server.tests.conftest import PASSCODE, SARVAM, make_wav, talk

SAID = "நான் எங்க கடையில கணக்கு எழுதுவேன்"


def stt_ok(transcript: str = SAID):
    return httpx.Response(200, json={"request_id": "r1", "transcript": transcript, "language_code": "ta-IN"})


def chat_ok(content: str):
    return httpx.Response(200, json={"choices": [{"message": {"role": "assistant", "content": content, "reasoning_content": None}, "finish_reason": "stop"}],
                                     "usage": {"prompt_tokens": 900, "completion_tokens": 30, "total_tokens": 930}})


@pytest.fixture()
def sarvam():
    with respx.mock(base_url=SARVAM, assert_all_called=False) as m:
        yield m


def test_good_json(client, sarvam):
    stt = sarvam.post("/speech-to-text").mock(return_value=stt_ok())
    chat = sarvam.post("/v1/chat/completions").mock(return_value=chat_ok('{"option_id":"accounts","confidence":0.86,"evidence":"கடையில கணக்கு"}'))
    r = talk(client)
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["transcript"] == SAID and j["fake"] is False and j["language_code"] == "ta-IN"
    assert j["suggestion"] == {"option_id": "accounts", "confidence": 0.86, "evidence": "கடையில கணக்கு", "source": "llm"}
    assert set(j["timings_ms"]) == {"stt", "llm", "total"}
    assert j["models"] == {"stt": "saaras:v4", "llm": "sarvam-105b"}
    assert "usage" not in j
    # what Sarvam received
    sreq = stt.calls.last.request
    assert sreq.headers["api-subscription-key"] == "test-key"
    body = sreq.content
    assert b'name="model"' in body and b"saaras:v4" in body and b"ta-IN" in body and b'name="mode"' in body
    creq = json.loads(chat.calls.last.request.content)
    assert creq["model"] == "sarvam-105b" and creq["response_format"] == {"type": "json_object"}
    assert "reasoning_effort" in creq and creq["reasoning_effort"] is None
    assert creq["messages"][0]["role"] == "system" and SAID in creq["messages"][-1]["content"]


def test_json_in_code_fences(client, sarvam):
    sarvam.post("/speech-to-text").mock(return_value=stt_ok())
    sarvam.post("/v1/chat/completions").mock(return_value=chat_ok('```json\n{"option_id": "accounts", "confidence": 1.7, "evidence": "கணக்கு"}\n```'))
    j = talk(client).json()
    assert j["suggestion"]["option_id"] == "accounts" and j["suggestion"]["source"] == "llm"
    assert j["suggestion"]["confidence"] == 1.0          # clamped to 0..1


def test_unknown_option_falls_back_to_keywords(client, sarvam):
    sarvam.post("/speech-to-text").mock(return_value=stt_ok())
    sarvam.post("/v1/chat/completions").mock(return_value=chat_ok('{"option_id":"shopkeeper","confidence":0.9,"evidence":"x"}'))
    j = talk(client).json()
    assert j["suggestion"] == {"option_id": "accounts", "confidence": 0.6, "evidence": "கணக்கு", "source": "keywords"}


def test_null_option_is_no_suggestion(client, sarvam):
    sarvam.post("/speech-to-text").mock(return_value=stt_ok("தெரியல"))
    sarvam.post("/v1/chat/completions").mock(return_value=chat_ok('{"option_id":null,"confidence":0,"evidence":""}'))
    assert talk(client).json()["suggestion"] is None


def test_llm_timeout_falls_back_to_keywords(client, sarvam):
    sarvam.post("/speech-to-text").mock(return_value=stt_ok())
    sarvam.post("/v1/chat/completions").mock(side_effect=httpx.ReadTimeout("slow"))
    j = talk(client).json()
    assert j["suggestion"]["source"] == "keywords" and j["suggestion"]["option_id"] == "accounts"


def test_keyword_fallback_needs_exactly_one_match(client, sarvam):
    sarvam.post("/speech-to-text").mock(return_value=stt_ok("கடையில கணக்கு எழுதுவேன், மோட்டார் ரிப்பேர் பண்ணுவேன்"))
    sarvam.post("/v1/chat/completions").mock(return_value=httpx.Response(500))
    assert talk(client).json()["suggestion"] is None


def test_stt_failure_is_502_with_tap_fallback(client, sarvam):
    sarvam.post("/speech-to-text").mock(return_value=httpx.Response(500, json={"error": "boom"}))
    chat = sarvam.post("/v1/chat/completions")
    r = talk(client)
    assert r.status_code == 502 and r.json() == {"error": "stt_failed", "fallback": "tap"}
    assert not chat.called


def test_retry_once_on_429(client, sarvam):
    sarvam.post("/speech-to-text").mock(side_effect=[httpx.Response(429), stt_ok()])
    sarvam.post("/v1/chat/completions").mock(return_value=chat_ok('{"option_id":"accounts","confidence":0.9,"evidence":"கணக்கு"}'))
    assert talk(client).json()["suggestion"]["option_id"] == "accounts"


def test_chat_extras_dropped_if_rejected(client, sarvam, monkeypatch):
    monkeypatch.setattr("server.sarvam._chat_extras_ok", True)
    sarvam.post("/speech-to-text").mock(return_value=stt_ok())
    chat = sarvam.post("/v1/chat/completions").mock(side_effect=[
        httpx.Response(400, json={"error": "unsupported parameter: reasoning_effort"}),
        chat_ok('{"option_id":"accounts","confidence":0.9,"evidence":"கணக்கு"}')])
    assert talk(client).json()["suggestion"]["source"] == "llm"
    second = json.loads(chat.calls[1].request.content)
    assert "reasoning_effort" not in second and "response_format" not in second


def test_empty_transcript_skips_llm(client, sarvam):
    sarvam.post("/speech-to-text").mock(return_value=stt_ok(""))
    chat = sarvam.post("/v1/chat/completions")
    j = talk(client).json()
    assert j["transcript"] == "" and j["suggestion"] is None and not chat.called


def test_debug_usage_only_with_header(client, sarvam):
    sarvam.post("/speech-to-text").mock(return_value=stt_ok())
    sarvam.post("/v1/chat/completions").mock(return_value=chat_ok('{"option_id":"accounts","confidence":0.9,"evidence":"கணக்கு"}'))
    j = talk(client, headers={"X-Debug": "1"}).json()
    assert j["usage"]["llm"] == {"prompt_tokens": 900, "completion_tokens": 30, "total_tokens": 930}
    assert j["usage"]["audio_seconds"] == 1.5


def test_wrong_passcode(client, sarvam):
    stt = sarvam.post("/speech-to-text")
    assert talk(client, passcode="000000").status_code == 401
    assert talk(client, passcode="").status_code == 401
    assert not stt.called


def test_size_and_length_limits(client, sarvam):
    stt = sarvam.post("/speech-to-text")
    assert talk(client, audio=make_wav(30)).status_code == 413          # 30 s is over 25 s
    big = make_wav(1) + b"\0" * 1_600_000
    assert talk(client, audio=big).status_code == 413                   # over 1.5 MB
    assert talk(client, audio=b"not a wav file at all, just text " * 3).status_code == 422
    assert talk(client, question_id="caste").status_code == 422
    assert not stt.called


def test_extra_profile_field_rejected_and_never_reaches_llm(client, sarvam):
    stt = sarvam.post("/speech-to-text").mock(return_value=stt_ok())
    chat = sarvam.post("/v1/chat/completions").mock(return_value=chat_ok('{"option_id":"accounts","confidence":0.9,"evidence":"x"}'))
    r = talk(client, extra={"profile": json.dumps({"gender": "girl", "community": "MBC", "income": "1to2.5"})})
    assert r.status_code == 422 and r.json()["error"] == "bad_fields"
    assert not stt.called and not chat.called
    # and a normal call sends the model only the question, options and transcript
    talk(client)
    sent = chat.calls.last.request.content.decode()
    assert "MBC" not in sent and "1to2.5" not in sent and "profile" not in sent and "Kavya" not in sent


def test_rate_limit(client, sarvam):
    sarvam.post("/speech-to-text").mock(return_value=stt_ok())
    sarvam.post("/v1/chat/completions").mock(return_value=chat_ok('{"option_id":"accounts","confidence":0.9,"evidence":"x"}'))
    codes = [talk(client).status_code for _ in range(21)]
    assert codes[:20] == [200] * 20 and codes[20] == 429


def test_no_audio_or_transcript_in_logs(client, sarvam, caplog):
    sarvam.post("/speech-to-text").mock(return_value=stt_ok())
    sarvam.post("/v1/chat/completions").mock(return_value=chat_ok('{"option_id":"accounts","confidence":0.9,"evidence":"கடையில கணக்கு"}'))
    with caplog.at_level(logging.DEBUG):
        assert talk(client).status_code == 200
    text = "\n".join(r.getMessage() for r in caplog.records)
    assert "talk ok q=home" in text
    assert SAID not in text and "கணக்கு" not in text and "RIFF" not in text


def test_fake_mode(fake_client):
    j = talk(fake_client, "school").json()
    assert j["fake"] is True and j["suggestion"]["option_id"] == "science" and j["transcript"] == "எனக்கு அறிவியல் ரொம்ப பிடிக்கும்"
    assert talk(fake_client, "style").json()["suggestion"]["option_id"] == "help"
    assert talk(fake_client, passcode="nope").status_code == 401


def test_health(client):
    assert client.get("/api/health").json() == {"ok": True, "version": "2026-11-28", "fake": False,
                                                 "models": {"stt": "saaras:v4", "llm": "sarvam-105b", "tts": "bulbul:v4-flash"}}


def test_parse_reply_and_keywords_units():
    q = talk_mod.questions()["school"]
    assert talk_mod.parse_reply('<think>hmm</think>{"option_id":"science","confidence":"0.7","evidence":"அறிவியல்"}', q)["confidence"] == 0.7
    with pytest.raises(talk_mod.InvalidReply):
        talk_mod.parse_reply("I think it is science", q)
    assert talk_mod.keyword_suggestion(q, "எனக்கு கம்ப்யூட்டர் பிடிக்கும்!")["option_id"] == "computer"
    assert talk_mod.normalise("  Hello,   WORLD! ") == "hello world"
    assert talk_mod.wav_seconds(make_wav(2.0)) == pytest.approx(2.0)
