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


def test_new_student_filled_in_offline_reaches_the_teacher(page, context, browser, server, shot):
    """A student new to the phone registers (roll 26, a first name, a picture PIN) and does everything with no network.
    When the network comes back, her progress reaches the server and the teacher's laptop shows a new row."""
    httpx.post(server + "/api/reset", headers={"X-Demo-Passcode": PASSCODE})
    bodies = []
    page.on("request", lambda r: bodies.append(r.post_data) if r.url.endswith("/api/sync") else None)
    laptop = browser.new_context(viewport={"width": 1280, "height": 800})
    teacher = laptop.new_page()
    teacher.goto(server + "/teacher/")
    teacher.wait_for_selector("tr[data-roll='10B-07']")
    assert teacher.locator("#rows tr").count() == 25

    open_app(page, server)
    context.set_offline(True)
    page.wait_for_function("document.getElementById('phStatus').innerText.includes('Offline')")
    page.click("[data-act=who][data-id=new]")
    page.fill("#regRoll", "7")
    page.click("[data-act=reg-next]")
    assert "already has a profile" in page.inner_text("#phBody")       # Kavya is roll 07 on this phone
    page.fill("#regRoll", "22")
    page.click("[data-act=reg-next]")
    assert "already on the class list" in page.inner_text("#phBody")   # roll 22 is Pavithra D in the sample class
    page.fill("#regRoll", "26")
    page.fill("#regName", "Meena")
    page.click("[data-act=reg-next]")
    for pin in ("moon", "sun", "fish"):
        page.click(f"[data-act=pin][data-id={pin}]")
    page.wait_for_selector("[data-act=ans]")
    assert "Meena" in page.inner_text("#phBody")
    page.click("[data-act=ans][data-q=home][data-o=repair]")
    page.click("[data-act=ans][data-q=school][data-o=computer]")
    page.click("[data-act=ans][data-q=style][data-o=hands]")
    page.click("[data-act=go][data-s=details]")
    for k, v in (("gender", '"girl"'), ("cls", "10"), ("school", '"govt"'), ("since6", "true"), ("medium", '"tamil"'),
                 ("community", '"BC"'), ("income", '"lt1"'), ("firstGen", "true")):
        page.click(f"[data-act=set][data-k={k}][data-v='{v}']")
    page.click("[data-act=doc][data-d=aadhaar]")
    page.click("[data-act=go][data-s=skills]")
    page.click("[data-act=go][data-s=paths]")
    pid = page.get_attribute("article[data-path]", "data-path")
    page.click(f"[data-act=choose][data-id={pid}]")
    page.wait_for_selector("#planDone")
    total = page.inner_text("#planDone").split("/")[1].split()[0]
    page.check("input[data-act=task][data-id=t1]")
    page.wait_for_function("document.getElementById('phStatus').innerText.includes('updates waiting')")
    shot(page, "laptop-new-student-offline")
    assert all(s["roll"] != "10B-26" for s in httpx.get(server + "/api/class").json()["students"])   # nothing sent yet

    context.set_offline(False)
    page.wait_for_function("document.getElementById('phStatus').innerText.includes('Synced')", timeout=15000)
    row = next(s for s in httpx.get(server + "/api/class").json()["students"] if s["roll"] == "10B-26")
    assert row["name"] == "Meena" and row["new"] is True and row["live"] is True
    assert row["path"] == pid and row["plan_done"] == f"1/{total}"
    teacher.wait_for_selector("tr[data-roll='10B-26']", timeout=8000)
    t = teacher.inner_text("tr[data-roll='10B-26']")
    assert "Meena" in t and "(new)" in t and "10B-26" in t and f"1/{total}" in t
    assert teacher.locator("#rows tr").count() == 26
    teacher.locator("tr[data-roll='10B-26']").scroll_into_view_if_needed()
    shot(teacher, "laptop-teacher-new-student")

    # what went over the network: roll number, progress and her first name, never her details
    assert bodies
    for b in bodies:
        assert "girl" not in b and "BC" not in b and "lt1" not in b
        for ev in json.loads(b)["events"]:
            assert set(ev) == ALLOWED | {"name"} and ev["name"] == "Meena"
    assert any(ev["student"] == "10B-26" for b in bodies for ev in json.loads(b)["events"])

    # her profile is saved on the phone behind her picture PIN
    page.click("[data-act=lock]")
    page.click("[data-act=who][data-id='10B-26']")
    for pin in ("sun", "sun", "sun"):
        page.click(f"[data-act=pin][data-id={pin}]")
    assert "Not quite" in page.inner_text("#phBody")
    for pin in ("moon", "sun", "fish"):
        page.click(f"[data-act=pin][data-id={pin}]")
    page.wait_for_selector("#planDone")
    assert page.inner_text("#planDone").startswith(f"1/{total}")
    laptop.close()
