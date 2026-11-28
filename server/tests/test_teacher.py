"""Teacher workspace: the class code, summary and status maths, new shared fields, student detail, and Ask OpenPath."""
from __future__ import annotations

import json
import logging
import uuid

import httpx
import pytest
import respx
from fastapi.testclient import TestClient

from server.kb import kb
from server.main import create_app
from server.tests.conftest import PASSCODE, SARVAM, settings


def event(**kw) -> dict:
    ev = {"event_id": str(uuid.uuid4()), "student": "10B-07", "ts": "2026-11-20T11:12:00Z",
          "step": "plan", "path": "labtech", "plan_done": "1/7", "blocker": "bank_account_aadhaar",
          "weeks": ["1/2", "0/3", "0/1", "0/1"], "next_task": "stories"}
    ev.update(kw)
    return ev


def student(client, roll="10B-07") -> dict:
    return next(s for s in client.get("/api/class").json()["students"] if s["roll"] == roll)


def ask(client, q, lang="en"):
    r = client.post("/api/ask", json={"question": q, "lang": lang})
    assert r.status_code == 200, r.text
    return r.json()


# ---------------- the class code ----------------
def test_teacher_pages_need_the_code():
    with TestClient(create_app(settings())) as c:
        assert c.get("/api/class").status_code == 401
        assert c.get("/api/class", headers={"X-Teacher-Code": "000000"}).status_code == 401
        assert c.get("/api/student/10B-07").status_code == 401
        assert c.post("/api/ask", json={"question": "Who needs help?"}).status_code == 401
        assert c.get("/api/class", headers={"X-Teacher-Code": PASSCODE}).status_code == 200
        assert c.post("/api/sync", json={"events": [event()]}).status_code == 200      # phones sync without the code


def test_teacher_code_overrides_the_demo_passcode_and_wrong_codes_are_limited():
    with TestClient(create_app(settings(teacher_code="777777"))) as c:
        assert c.get("/api/class", headers={"X-Teacher-Code": PASSCODE}).status_code == 401
        assert c.get("/api/class", headers={"X-Teacher-Code": "777777"}).status_code == 200
        codes = [c.get("/api/class", headers={"X-Teacher-Code": "bad"}).status_code for _ in range(21)]
        assert codes[:19] == [401] * 19 and codes[20] == 429


def test_no_code_configured_says_so():
    with TestClient(create_app(settings(demo_passcode=""))) as c:
        r = c.get("/api/class", headers={"X-Teacher-Code": "anything"})
        assert r.status_code == 503 and r.json()["error"] == "teacher_code_not_set"
        assert c.get("/api/health").json()["teacher_code_set"] is False


# ---------------- summary and status ----------------
def test_seed_summary(client):
    s = client.get("/api/class").json()["summary"]
    assert (s["total"], s["chose_path"], s["on_track"], s["need_help"], s["not_started"], s["inactive"]) == (25, 21, 12, 8, 4, 6)
    assert s["status_counts"] == {"not_started": 4, "inactive": 3, "needs_help": 6, "on_track": 9, "done": 3}
    assert [(g["blocker"], g["count"]) for g in s["groups"]] == [("bank_account_aadhaar", 3), ("income_certificate", 3),
                                                                 ("community_certificate", 1), ("aadhaar", 1), ("no_path_yet", 4)]
    assert s["groups"][0]["where"]["en"].startswith("Nearest bank branch") and "post office" in s["groups"][0]["action"]["en"]
    assert sum(m["count"] for m in s["path_mix"]) == 21
    assert [d["count"] for d in s["deadlines"]] == [25, 10, 11]


def test_status_rules(client):
    assert student(client, "10B-02")["status"] == "done"            # 8/8
    assert student(client, "10B-09")["status"] == "inactive"        # 8 days since last use
    assert student(client, "10B-01")["status"] == "needs_help"      # bank account
    assert student(client, "10B-05")["status"] == "on_track"
    assert student(client, "10B-04")["status"] == "not_started"


def test_new_fields_flow_to_the_teacher(client):
    client.post("/api/sync", json={"events": [event()]})
    k = student(client)
    assert k["weeks"] == ["1/2", "0/3", "0/1", "0/1"] and k["next_task"] == "stories" and k["progress_pct"] == 14
    assert k["next_step"] == kb()["plan"]["labtech"]["stories"]
    client.post("/api/sync", json={"events": [event(next_task="documents", ts="2026-11-20T11:13:00Z")]})
    assert student(client)["next_step"] == kb()["doc_tasks"]["bank"]                  # the blocker says which document
    assert student(client)["deadlines"] == kb()["decisions"]["labtech"]


@pytest.mark.parametrize("field,value", [("next_task", "documents:bank"), ("weeks", ["1/2"] * 7), ("weeks", ["one of two"]),
                                          ("weeks", []), ("next_task", "visit the bank")])
def test_new_fields_are_validated(client, field, value):
    assert client.post("/api/sync", json={"events": [event(**{field: value})]}).status_code == 422


def test_feed_history_and_detail(client):
    client.post("/api/sync", json={"events": [event(step="discover", path=None, plan_done=None, blocker="no_path_yet", weeks=None,
                                                    next_task=None, ts="2026-11-20T11:00:00Z")]})
    client.post("/api/sync", json={"events": [event(plan_done="0/7", weeks=["0/2", "0/3", "0/1", "0/1"], next_task="lesson",
                                                    ts="2026-11-20T11:05:00Z")]})
    client.post("/api/sync", json={"events": [event(ts="2026-11-20T11:10:00Z")]})
    feed = client.get("/api/class").json()["feed"]
    assert feed[0]["text"]["en"] == "finished a plan step (1/7)" and feed[0]["name"] == "Kavya S"
    assert feed[1]["text"]["en"] == "chose Lab technician"
    d = client.get("/api/student/10B-07").json()
    assert d["route"]["en"].startswith("DMLT") and d["visit"]["en"].startswith("Visit a government hospital lab")
    assert d["help"]["label"]["en"] == "Bank account (Aadhaar)" and d["help"]["where"]["en"].startswith("Nearest bank")
    assert [h["text"]["en"] for h in d["history"]][:2] == ["finished a plan step (1/7)", "chose Lab technician"]
    assert "Gender" in d["never"]["en"] and "Roll number" in d["shared"]["en"]
    assert client.get("/api/student/10B-99").status_code == 404
    client.post("/api/sync", json={"events": [event(student="10B-40", name="Meena", step="discover", path=None, plan_done=None,
                                                    blocker="no_path_yet", weeks=None, next_task=None)]})
    assert client.get("/api/class").json()["feed"][0]["text"]["en"] == "joined on a phone as a new student"


# ---------------- Ask OpenPath: rules ----------------
@pytest.mark.parametrize("q,intent,expect", [
    ("Who needs help this week?", "needs_help", "Anitha R (10B-01)"),
    ("Who hasn't chosen a path?", "no_path", "Kavya S (10B-07)"),
    ("Who hasn't opened the app for a week?", "inactive", "Janani R (10B-20, 15 days)"),
    ("How do students get an income certificate?", "doc", "e-Sevai"),
    ("Plan visits by career", "visit", "Government ITI"),
    ("What's coming up?", "deadlines", "Class 10 public exam"),
    ("Explain Pudhumai Penn", "scheme", "Deccan Herald"),
    ("How is my class doing?", "summary", "21 of 25 chose a path"),
    ("Who chose nursing?", "path", "Anitha R (10B-01)"),
    ("Which students are on ITI paths?", "path", "Karthik S (10B-02)"),
    ("Is Kavya eligible for the SC scholarship?", "eligible", "does not decide eligibility"),
])
def test_ask_rules(client, q, intent, expect):
    a = ask(client, q)
    assert a["source"] == "rules" and a["intent"] == intent and expect in a["answer"]


def test_ask_rules_in_tamil(client):
    a = ask(client, "இந்த வாரம் யாருக்கு உதவி தேவை?", "ta")
    assert a["intent"] == "needs_help" and "வங்கிக் கணக்கு" in a["answer"]


def test_ask_scheme_cites_its_source_and_never_judges_a_student(client):
    a = ask(client, "Tell me about PM YASASVI pre-matric")
    assert a["sources"] and a["sources"][0]["label"].startswith("PIB")
    assert "phone" in a["answer"]                                     # eligibility is checked on her phone


def test_ask_validation(client):
    assert client.post("/api/ask", json={"question": ""}).status_code == 422
    assert client.post("/api/ask", json={"question": "x" * 501}).status_code == 422
    assert client.post("/api/ask", json={"question": "hi", "profile": {"community": "MBC"}}).status_code == 422


def test_ask_without_ai_offers_what_it_can_answer():
    with TestClient(create_app(settings(fake_sarvam=True, sarvam_api_key="")), headers={"X-Teacher-Code": PASSCODE}) as c:
        a = ask(c, "Write a poem about my class")
    assert a["source"] == "none" and len(a["suggestions"]) >= 6


# ---------------- Ask OpenPath: Sarvam, names never sent ----------------
def chat_reply(text):
    return httpx.Response(200, json={"choices": [{"message": {"role": "assistant", "content": text}}],
                                     "usage": {"prompt_tokens": 2100, "completion_tokens": 120}})


def test_ask_llm_gets_roll_numbers_not_names(client, caplog):
    client.post("/api/sync", json={"events": [event()]})
    with respx.mock(base_url=SARVAM, assert_all_called=False) as m:
        route = m.post("/v1/chat/completions").mock(
            return_value=chat_reply("10B-07 has chosen Lab technician. Help 10B-07 open a bank account this week."))
        with caplog.at_level(logging.DEBUG):
            a = ask(client, "Write a short note for Kavya's parents about her next step")
    sent = route.calls.last.request.content.decode()
    body = json.loads(sent)
    assert "10B-07" in body["messages"][-1]["content"] and "Kavya" not in sent and "Anitha" not in sent
    class_lines = body["messages"][0]["content"].split("CLASS 10-B")[1].split("SUMMARY")[0]     # one line per student
    assert class_lines.count("10B-") >= 25
    for word in ("girl", "boy", "gender", "MBC", "lakh", "1to2.5", "caste", "Kavya", "Anitha"):   # the one blocker (e.g. "Income certificate") is shared; income is not
        assert word not in class_lines
    assert "response_format" not in body and body["reasoning_effort"] is None
    assert a["source"] == "llm" and "Kavya S (10B-07) has chosen Lab technician" in a["answer"]
    assert a["used"] == [{"roll": "10B-07", "name": "Kavya S"}]
    logs = "\n".join(r.getMessage() for r in caplog.records)
    assert "ask source=llm" in logs and "parents" not in logs and "Kavya" not in logs


def test_ask_llm_failure_falls_back(client):
    with respx.mock(base_url=SARVAM, assert_all_called=False) as m:
        m.post("/v1/chat/completions").mock(side_effect=httpx.ReadTimeout("slow"))
        a = ask(client, "Write a poem about my class")
    assert a["source"] == "none" and a["suggestions"]
