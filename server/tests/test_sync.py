"""/api/sync, /api/class and /api/reset: strict schema, idempotent, latest ts wins, roster seed and reset."""
from __future__ import annotations

import uuid

import pytest

from server.tests.conftest import PASSCODE


def event(**kw) -> dict:
    ev = {"event_id": str(uuid.uuid4()), "student": "10B-07", "ts": "2026-11-30T11:12:00Z",
          "step": "plan", "path": "labtech", "plan_done": "1/7", "blocker": "bank_account_aadhaar"}
    ev.update(kw)
    return ev


def row(client, roll="10B-07") -> dict:
    return next(s for s in client.get("/api/class").json()["students"] if s["roll"] == roll)


def test_roster_seed(client):
    j = client.get("/api/class").json()
    assert j["class_id"] == "10B" and j["school"].endswith("(sample)") and j["last_event"] is None
    assert len(j["students"]) == 25
    assert [s["roll"] for s in j["students"]] == sorted(s["roll"] for s in j["students"])
    k = row(client)
    assert k == {"roll": "10B-07", "name": "Kavya S", "step": "discover", "path": None, "path_name": None, "plan_done": None,
                 "blocker": "no_path_yet", "live": True, "last_event_at": None}
    a = row(client, "10B-01")
    assert a["plan_done"] == "5/8" and a["blocker"] == "bank_account_aadhaar" and a["path_name"]["en"] == "Nurse" and a["live"] is False
    assert row(client, "10B-04")["blocker"] == "no_path_yet" and row(client, "10B-16")["blocker"] == "community_certificate"
    assert row(client, "10B-06")["blocker"] == "aadhaar" and row(client, "10B-03")["blocker"] == "income_certificate"
    assert sum(1 for s in j["students"] if s["live"]) == 1


def test_sync_updates_the_live_row(client):
    ev = event()
    r = client.post("/api/sync", json={"events": [ev]})
    assert r.status_code == 200 and r.json() == {"accepted": [ev["event_id"]], "duplicates": []}
    k = row(client)
    assert k["path"] == "labtech" and k["path_name"] == {"ta": "ஆய்வக தொழில்நுட்பர்", "en": "Lab technician"}
    assert k["plan_done"] == "1/7" and k["blocker"] == "bank_account_aadhaar" and k["last_event_at"] == "2026-11-30T11:12:00Z"
    assert client.get("/api/class").json()["last_event"]["event_id"] == ev["event_id"]


@pytest.mark.parametrize("field,value", [("community", "MBC"), ("income", "1to2.5"), ("gender", "girl"), ("name", "Kavya S"),
                                          ("answers", {"home": "accounts"}), ("docs", {"bank": False})])
def test_sync_rejects_personal_fields(client, field, value):
    r = client.post("/api/sync", json={"events": [event(**{field: value})]})
    assert r.status_code == 422
    assert row(client)["path"] is None                        # nothing was stored


def test_sync_rejects_extra_top_level_keys(client):
    assert client.post("/api/sync", json={"events": [event()], "profile": {"gender": "girl"}}).status_code == 422


@pytest.mark.parametrize("field,value", [("step", "done"), ("blocker", "caste_certificate"), ("plan_done", "one of seven"),
                                          ("student", "10A-07"), ("path", "astronaut"), ("ts", "yesterday"), ("event_id", "x")])
def test_sync_rejects_bad_values(client, field, value):
    assert client.post("/api/sync", json={"events": [event(**{field: value})]}).status_code == 422


def test_sync_rejects_unknown_roll_and_big_batches(client):
    assert client.post("/api/sync", json={"events": [event(student="10B-99")]}).status_code == 422
    assert client.post("/api/sync", json={"events": [event() for _ in range(51)]}).status_code == 422


def test_sync_is_idempotent(client):
    ev = event()
    client.post("/api/sync", json={"events": [ev]})
    r = client.post("/api/sync", json={"events": [ev, event(plan_done="2/7", ts="2026-11-30T11:13:00Z")]})
    j = r.json()
    assert j["duplicates"] == [ev["event_id"]] and len(j["accepted"]) == 1
    assert row(client)["plan_done"] == "2/7"


def test_latest_ts_wins(client):
    newer = event(plan_done="3/7", ts="2026-11-30T11:20:00Z")
    older = event(plan_done="1/7", ts="2026-11-30T11:10:00Z")
    client.post("/api/sync", json={"events": [newer]})
    client.post("/api/sync", json={"events": [older]})          # arrives late
    assert row(client)["plan_done"] == "3/7"
    client.post("/api/sync", json={"events": [event(plan_done=None, path=None, step="paths", blocker="no_path_yet", ts="2026-11-30T11:21:00+05:30")]})
    assert row(client)["plan_done"] == "3/7"                    # 11:21 IST is 05:51 UTC, older than 11:20 UTC


def test_reset_needs_the_passcode_and_reseeds(client):
    client.post("/api/sync", json={"events": [event()]})
    assert client.post("/api/reset").status_code == 401
    assert client.post("/api/reset", headers={"X-Demo-Passcode": "nope"}).status_code == 401
    assert row(client)["path"] == "labtech"
    assert client.post("/api/reset", headers={"X-Demo-Passcode": PASSCODE}).json() == {"ok": True}
    k = row(client)
    assert k["path"] is None and k["blocker"] == "no_path_yet"
    assert client.get("/api/class").json()["last_event"] is None
    # an event id seen before the reset is accepted again afterwards
    ev = event()
    assert client.post("/api/sync", json={"events": [ev]}).json()["accepted"] == [ev["event_id"]]


def test_class_is_not_cached(client):
    assert client.get("/api/class").headers["cache-control"] == "no-store"
