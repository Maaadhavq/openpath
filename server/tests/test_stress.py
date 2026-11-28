"""Stress and edge cases: wrong phone clocks, duplicate storms, floods, a full class, bounded memory, and Ask questions
that try to get at what OpenPath never stores."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from server.main import create_app
from server.tests.conftest import PASSCODE, settings


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def event(**kw) -> dict:
    ev = {"event_id": str(uuid.uuid4()), "student": "10B-07", "ts": iso(datetime.now(timezone.utc)),
          "step": "plan", "path": "labtech", "plan_done": "1/7", "blocker": "bank_account_aadhaar"}
    ev.update(kw)
    return ev


def row(client, roll="10B-07") -> dict:
    return next(s for s in client.get("/api/class").json()["students"] if s["roll"] == roll)


def test_phone_clock_years_ahead_does_not_freeze_her_row(client):
    """A cheap phone with its clock set to 2031 syncs, then the clock is fixed. Her later progress must still show."""
    now = datetime.now(timezone.utc)
    client.post("/api/sync", json={"events": [event(ts=iso(now.replace(year=2031)), plan_done="1/7")]})
    r = row(client)
    assert r["last_event_at"] <= iso(now + timedelta(minutes=5))           # stored as 'now', not 2031
    client.post("/api/sync", json={"events": [event(ts=iso(now + timedelta(seconds=30)), plan_done="2/7")]})
    assert row(client)["plan_done"] == "2/7"


def test_phone_clock_behind_still_orders_its_own_events(client):
    old = datetime(2025, 1, 1, tzinfo=timezone.utc)
    client.post("/api/sync", json={"events": [event(ts=iso(old), plan_done="1/7"), event(ts=iso(old + timedelta(minutes=1)), plan_done="3/7")]})
    assert row(client)["plan_done"] == "3/7"


def test_duplicate_storm(client):
    ev = event()
    results = [client.post("/api/sync", json={"events": [ev]}).json() for _ in range(100)]
    assert sum(len(r["accepted"]) for r in results) == 1 and sum(len(r["duplicates"]) for r in results) == 99


def test_full_class_of_99(client):
    evs = [event(student=f"10B-{n:02d}", name=f"Student {n}") for n in range(26, 100)]
    for i in range(0, len(evs), 50):
        assert client.post("/api/sync", json={"events": evs[i:i + 50]}).status_code == 200
    j = client.get("/api/class").json()
    assert len(j["students"]) == 99 and j["summary"]["total"] == 99
    assert sum(j["summary"]["status_counts"].values()) == 99


def test_memory_stays_bounded(client):
    for i in range(300):
        client.post("/api/sync", json={"events": [event(plan_done=f"{i % 7}/7", ts=iso(datetime(2026, 11, 28, tzinfo=timezone.utc) + timedelta(seconds=i)))]})
    store = client.app.state.store
    assert len(store.history["10B-07"]) <= 50 and len(store.feed) <= 30
    assert len(client.get("/api/class").json()["feed"]) <= 12


def test_sync_flood_from_one_address_is_limited():
    with TestClient(create_app(settings(sync_per_minute=30)), headers={"X-Teacher-Code": PASSCODE}) as c:
        codes = [c.post("/api/sync", json={"events": [event()]}).status_code for _ in range(31)]
    assert codes[:30] == [200] * 30 and codes[30] == 429


def test_names_cannot_carry_markup(client):
    for bad in ("<img src=x onerror=alert(1)>", "a&b", "{{7*7}}", "x\\y"):
        assert client.post("/api/sync", json={"events": [event(student="10B-50", name=bad)]}).status_code == 422


# ---------------- Ask: questions about what is never stored ----------------
@pytest.mark.parametrize("q", ["Which students are SC?", "How many girls chose engineering?", "What is Kavya's caste?",
                               "List the students from poor families", "Which boys need help?", "What is the family income of 10B-01?"])
def test_ask_cannot_reveal_what_is_never_stored(client, q):
    a = client.post("/api/ask", json={"question": q}).json()
    assert a["intent"] == "private" and a["used"] == []
    assert "never" in a["answer"].lower() and "phone" in a["answer"].lower()


@pytest.mark.parametrize("q,intent", [("Who needs a community certificate?", "doc"), ("Explain the SC scholarship", "scheme"),
                                      ("Is Pudhumai Penn only for girls?", "scheme")])
def test_ask_still_answers_honest_questions_near_those_words(client, q, intent):
    assert client.post("/api/ask", json={"question": q}).json()["intent"] == intent


def test_ask_inactive_wording_allows_for_offline_use(client):
    a = client.post("/api/ask", json={"question": "Who hasn't opened the app for a week?"}).json()
    assert "no update" in a["answer"].lower() and "offline" in a["answer"].lower()
