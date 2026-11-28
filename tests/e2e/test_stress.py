"""Browser stress cases: a flapping network, a long offline queue, a full class on the teacher page, hostile names,
and guessing a picture PIN on a shared phone."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import httpx

from helpers import PASSCODE, TEACHER, kavya_to_plan, open_app, open_teacher, unlock_kavya


def reset(server):
    httpx.post(server + "/api/reset", headers={"X-Demo-Passcode": PASSCODE})


def kavya_row(server):
    return next(s for s in httpx.get(server + "/api/class", headers=TEACHER).json()["students"] if s["roll"] == "10B-07")


def test_flapping_network_ends_consistent(page, context, server):
    """The signal drops and returns six times while she ticks and unticks steps. Nothing is lost or doubled."""
    reset(server)
    open_app(page, server)
    kavya_to_plan(page)
    for i, task in enumerate(["t1", "t2", "t3", "t2", "t4", "t1"]):
        context.set_offline(i % 2 == 0)
        box = page.locator(f"input[data-act=task][data-id={task}]")
        box.uncheck() if box.is_checked() else box.check()
        page.wait_for_timeout(250)
    context.set_offline(False)
    page.wait_for_function("document.getElementById('phStatus').innerText.includes('Synced')", timeout=20000)
    on_phone = page.inner_text("#planDone").split()[0]
    assert kavya_row(server)["plan_done"] == on_phone
    assert page.evaluate("JSON.parse(localStorage.getItem('op.queue') || '[]').length") == 0


def test_long_offline_queue_drains_in_batches(page, context, server):
    """A week offline: 120 queued updates go out in batches of 50 when the signal returns."""
    reset(server)
    open_app(page, server)
    kavya_to_plan(page)
    page.wait_for_function("document.getElementById('phStatus').innerText.includes('Synced')")
    context.set_offline(True)
    sizes = []
    page.on("request", lambda r: sizes.append(len(__import__("json").loads(r.post_data)["events"])) if r.url.endswith("/api/sync") else None)
    page.evaluate("""() => {
      const q = JSON.parse(localStorage.getItem('op.queue') || '[]');
      const base = Date.now() - 120 * 60000;
      for (let i = 0; i < 120; i++) q.push({ event_id: crypto.randomUUID(), student: '10B-07', ts: new Date(base + i * 60000).toISOString(),
        step: 'plan', path: 'labtech', plan_done: (i % 7) + '/7', blocker: 'bank_account_aadhaar' });
      localStorage.setItem('op.queue', JSON.stringify(q));
    }""")
    context.set_offline(False)
    page.wait_for_function("JSON.parse(localStorage.getItem('op.queue') || '[]').length === 0", timeout=20000)
    assert max(sizes) <= 50 and sum(sizes) >= 120


def test_teacher_page_with_a_full_class_and_hostile_names(page, server):
    reset(server)
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    evs = [{"event_id": str(uuid.uuid4()), "student": f"10B-{n:02d}", "ts": now, "step": "discover", "path": None, "plan_done": None,
            "blocker": "no_path_yet", "name": f"Student {n}"} for n in range(26, 99)]
    evs.append({"event_id": str(uuid.uuid4()), "student": "10B-99", "ts": now, "step": "discover", "path": None, "plan_done": None,
                "blocker": "no_path_yet", "name": "\"onmouseover=alert(1) x"})
    for i in range(0, len(evs), 50):
        assert httpx.post(server + "/api/sync", json={"events": evs[i:i + 50]}).status_code == 200
    page.on("dialog", lambda d: (_ for _ in ()).throw(AssertionError("a script ran from a name")))
    open_teacher(page, server, "students")
    assert page.locator("#studentList tbody tr").count() == 99
    row = page.locator("tr[data-roll='10B-99']")
    assert "onmouseover=alert(1)" in row.inner_text()            # shown as text
    assert row.get_attribute("onmouseover") is None
    page.click("[data-filter=new]")
    assert page.locator("#studentList tbody tr").count() == 74
    page.hover("tr[data-roll='10B-99']")


def test_guessing_a_picture_pin_is_slowed_down(page, server):
    open_app(page, server)
    page.click("[data-act=who][data-id=kavya]")
    for _ in range(5):
        for pin in ("fish", "fish", "fish"):
            page.click(f"[data-act=pin][data-id={pin}]")
    body = page.inner_text("#phBody")
    assert "30" in body and ("wait" in body.lower())
    page.click("[data-act=pin][data-id=sun]")              # taps are ignored while locked
    assert page.evaluate("window.OPENPATH.S().pin.length") == 0
