"""Browser tests for the student app, run against the server in fake mode."""
from __future__ import annotations

from helpers import kavya_to_plan, open_app, unlock_kavya


def test_checks_pass(page, server):
    open_app(page, server)
    c = page.evaluate("window.OPENPATH_CHECKS")
    assert c["passed"] == c["total"] == 47
    assert c["genderSwapChanged"] == 0 and c["genderSwapN"] == 1000
    assert c["networkCallsInFlow"] == 0
    assert c["schemes"] == 11 and c["paths"] == 14 and c["ruleChecks"] == 26


def test_round2_demo_path(page, server, shot):
    """Kavya's Round 2 path still gives the same paths, plan and scheme results."""
    open_app(page, server)
    unlock_kavya(page)
    page.click("[data-act=sample-answers]")
    page.click("[data-act=go][data-s=details]")
    page.click("[data-act=sample-profile]")
    page.click("[data-act=go][data-s=skills]")
    page.click("[data-act=go][data-s=paths]")
    ids = page.eval_on_selector_all("article[data-path]", "els => els.map(e => e.dataset.path)")
    assert ids == ["nursing", "labtech", "accounts", "agri"]
    page.click("[data-act=choose][data-id=labtech]")
    page.wait_for_selector("#planDone")
    assert page.inner_text("#planDone").startswith("0/7")
    page.click("[data-act=go][data-s=support]")
    pud = page.locator("article[data-scheme=pudhumai]")
    assert pud.get_attribute("data-status") == "later"
    assert "Bank account linked to Aadhaar" in pud.inner_text()
    assert page.get_attribute("article[data-scheme=yasasvi_pre]", "data-status") == "likely"
    page.click("[data-act=ready][data-id=yasasvi_pre]")
    page.wait_for_selector(".sheet")
    shot(page, "laptop-support-sheet")
    page.click(".sheet [data-act=close-sheet]")
    page.click("[data-act=panel][data-id=checks]")
    assert page.inner_text("#ckRules") == "47/47"


def test_progress_survives_reload(page, server):
    open_app(page, server)
    kavya_to_plan(page)
    page.check("input[data-act=task][data-id=t1]")
    page.reload()
    page.wait_for_function("window.OPENPATH && window.OPENPATH_CHECKS")
    unlock_kavya_any(page)
    page.wait_for_selector("#planDone")
    assert page.inner_text("#planDone").startswith("1/7")


def unlock_kavya_any(page):
    page.click("[data-act=who][data-id=kavya]")
    for pin in ("sun", "leaf", "star"):
        page.click(f"[data-act=pin][data-id={pin}]")


def test_installable_and_offline(page, context, server, shot):
    """The service worker installs; with the network off, a reload still works and the rules still run."""
    open_app(page, server)
    m = page.evaluate("fetch('/manifest.webmanifest').then(r => r.json())")
    assert m["display"] == "standalone" and m["start_url"] == "/" and m["theme_color"] == "#1e6b52"
    assert {i["sizes"] for i in m["icons"]} == {"192x192", "512x512"} and any(i.get("purpose") == "maskable" for i in m["icons"])
    page.evaluate("navigator.serviceWorker.ready")
    page.wait_for_function("navigator.serviceWorker.controller !== null")
    cached = page.evaluate("caches.keys().then(k => Promise.all(k.map(n => caches.open(n).then(c => c.keys()).then(r => r.map(x => new URL(x.url).pathname))))).then(a => a.flat())")
    for must in ("/index.html", "/js/engine.js", "/data/paths.json", "/icons/icon-192.png"):
        assert must in cached

    context.set_offline(True)
    page.reload()
    page.wait_for_function("window.OPENPATH && window.OPENPATH_CHECKS")
    c = page.evaluate("window.OPENPATH_CHECKS")
    assert c["passed"] == 47 and c["networkCallsInFlow"] == 0
    assert "Offline" in page.inner_text("#phStatus")
    kavya_to_plan(page)
    page.click("[data-act=go][data-s=support]")
    pud = page.locator("article[data-scheme=pudhumai]")
    assert pud.get_attribute("data-status") == "later"
    assert "Bank account linked to Aadhaar" in pud.inner_text()
    shot(page, "laptop-offline-support")
    context.set_offline(False)
