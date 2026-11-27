"""Offline queue -> /api/sync -> /api/class -> the teacher dashboard."""
from __future__ import annotations

import json

import httpx

from helpers import PASSCODE, kavya_to_plan, open_app

ALLOWED = {"event_id", "student", "ts", "step", "path", "plan_done", "blocker"}


def kavya_row(server):
    return next(s for s in httpx.get(server + "/api/class").json()["students"] if s["roll"] == "10B-07")


def test_offline_queue_then_sync_to_teacher(page, context, server, shot):
    httpx.post(server + "/api/reset", headers={"X-Demo-Passcode": PASSCODE})
    bodies = []
    page.on("request", lambda r: bodies.append(r.post_data) if r.url.endswith("/api/sync") else None)
    teacher = context.new_page()
    teacher.goto(server + "/teacher/")
    teacher.wait_for_selector("tr[data-roll='10B-07']")
    assert teacher.locator("#rows tr").count() == 25
    assert "No path yet" in teacher.inner_text("tr[data-roll='10B-07']")

    open_app(page, server)
    kavya_to_plan(page)
    page.wait_for_function("document.getElementById('phStatus').innerText.includes('Synced')")
    assert kavya_row(server)["path"] == "labtech"

    context.set_offline(True)
    page.wait_for_function("document.getElementById('phStatus').innerText.includes('Offline')")
    page.click("[data-act=go][data-s=support]")
    assert page.get_attribute("article[data-scheme=pudhumai]", "data-status") == "later"
    page.click("[data-act=go][data-s=plan]")
    page.check("input[data-act=task][data-id=t1]")
    page.wait_for_function("document.getElementById('phStatus').innerText.includes('1 update waiting')")
    shot(page, "laptop-offline-waiting")
    assert kavya_row(server)["plan_done"] == "0/7"        # nothing reached the server while offline

    context.set_offline(False)
    page.wait_for_function("document.getElementById('phStatus').innerText.includes('Synced')")
    row = kavya_row(server)
    assert row["path"] == "labtech" and row["plan_done"] == "1/7" and row["blocker"] == "bank_account_aadhaar"
    # the teacher page picks it up on its next poll
    teacher.wait_for_function("document.querySelector(\"tr[data-roll='10B-07']\").innerText.includes('1/7')", timeout=8000)
    t = teacher.inner_text("tr[data-roll='10B-07']")
    assert "Lab technician" in t and "Bank account" in t and "(live)" in t
    sent = json.loads(teacher.inner_text("#lastEvent"))
    assert set(sent) == ALLOWED and sent["plan_done"] == "1/7"
    teacher.set_viewport_size({"width": 1280, "height": 800})
    shot(teacher, "laptop-teacher")
    # every sync request carried only the allowed keys: no profile, no answers
    assert bodies
    for b in bodies:
        payload = json.loads(b)
        assert set(payload) == {"events"}
        for ev in payload["events"]:
            assert set(ev) == ALLOWED and ev["student"] == "10B-07"
    for word in ("MBC", "girl", "community", "income", "gender", "1to2.5", "accounts\"", "science"):
        assert all(word not in b for b in bodies)
