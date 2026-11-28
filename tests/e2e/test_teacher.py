"""The teacher workspace in a browser: sign-in, Overview, the student drawer, Actions, Ask OpenPath, and the phone's
"What your teacher sees" screen. Also checks app/data/kb.json still matches the phone's engine."""
from __future__ import annotations

import json
import sys

import httpx

from helpers import PASSCODE, ROOT, kavya_to_plan, open_app, open_teacher

sys.path.insert(0, str(ROOT / "scripts"))
from export_kb import EXPORT_JS  # noqa: E402

SIZES = {"phone": {"width": 390, "height": 844}, "laptop": {"width": 1280, "height": 800}}


def reset(server):
    httpx.post(server + "/api/reset", headers={"X-Demo-Passcode": PASSCODE})


def test_kb_matches_the_engine(page, server):
    open_app(page, server)
    live = page.evaluate(EXPORT_JS)
    saved = json.loads((ROOT / "app" / "data" / "kb.json").read_text(encoding="utf-8"))
    saved.pop("_note")
    assert live == saved, "app/data/kb.json is out of date: run python scripts/export_kb.py"


def test_sign_in(page, server):
    reset(server)
    page.goto(server + "/teacher/")
    page.wait_for_selector("#signinForm")
    assert page.is_hidden("#app")
    page.fill("#code", "000000")
    page.click("#signinForm button")
    page.wait_for_selector("#signinMsg:not([hidden])")
    assert "not right" in page.inner_text("#signinMsg")
    page.fill("#code", PASSCODE)
    page.click("#signinForm button")
    page.wait_for_selector("#v-overview .figs")
    figs = page.inner_text("#v-overview .figs")
    assert "21 of 25" in figs and "chose a path" in figs
    page.click("#signout")
    page.wait_for_selector("#signinForm")


def test_overview_drawer_actions_after_kavya_syncs(page, context, server, shot):
    reset(server)
    teacher = context.new_page()
    teacher.set_viewport_size(SIZES["laptop"])
    open_teacher(teacher, server)
    assert "Nothing yet" in teacher.inner_text("#feed")

    open_app(page, server)
    kavya_to_plan(page)
    page.check("input[data-act=task][data-id=t1]")
    page.wait_for_function("document.getElementById('phStatus').innerText.includes('Synced')")

    teacher.wait_for_function("document.getElementById('feed').innerText.includes('chose Lab technician')", timeout=8000)
    teacher.wait_for_function("document.getElementById('feed').innerText.includes('finished a plan step (1/7)')", timeout=8000)
    shot(teacher, "teacher-laptop-overview")

    teacher.click("[data-tab=students]")
    teacher.wait_for_selector("tr[data-roll='10B-07']")
    row = teacher.inner_text("tr[data-roll='10B-07']")
    assert "Lab technician" in row and "Plan 1/7" in row and "Needs help" in row and "Bank account" in row and "(live)" in row
    shot(teacher, "teacher-laptop-students")
    teacher.click("[data-filter=new]")
    assert "No students match" in teacher.inner_text("#studentList")
    teacher.click("[data-filter=needs_help]")
    assert teacher.locator("#studentList tbody tr").count() == 9          # 8 sample students and Kavya
    teacher.click("[data-filter=all]")
    teacher.fill("#search", "kavya")
    assert teacher.locator("#studentList tbody tr").count() == 1

    teacher.click("tr[data-roll='10B-07']")
    teacher.wait_for_selector("#drawer h2")
    d = teacher.inner_text("#drawer")
    for want in ("Kavya S", "DMLT diploma", "Week 1", "1/2", "Next step", "Listen to two more stories", "How you can help",
                 "Bank account (Aadhaar)", "post office", "finished a plan step (1/7)", "What her phone shares", "Never shared"):
        assert want in d, want
    shot(teacher, "teacher-laptop-drawer")
    teacher.click("#closeDrawer")
    assert teacher.is_hidden("#drawer")

    teacher.click("[data-tab=actions]")
    teacher.wait_for_selector("#act-bank_account_aadhaar")
    act = teacher.inner_text("#act-bank_account_aadhaar")
    assert "4 need a bank account" in act and "Kavya S" in act and "Copy parent message" in act
    shot(teacher, "teacher-laptop-actions")


def test_ask(page, server, shot):
    reset(server)
    page.set_viewport_size(SIZES["laptop"])
    open_teacher(page, server, "ask")
    page.wait_for_selector("#suggest button")
    page.click("#suggest button:has-text('Who needs help this week?')")
    page.wait_for_selector(".a .text")
    a = page.inner_text(".a")
    assert "need help with a document" in a and "Anitha R (10B-01)" in a and "Answered from your class data" in a
    page.fill("#askInput", "Explain Pudhumai Penn")
    page.click("#askForm button")
    page.wait_for_function("document.querySelectorAll('.a .text').length === 2")
    second = page.locator(".a").nth(1).inner_text()
    assert "Pudhumai Penn" in second and "Sources:" in second and "phone" in second
    page.fill("#askInput", "Write a poem about my class")      # no AI in fake mode: offers what it can answer
    page.click("#askForm button")
    page.wait_for_function("document.querySelectorAll('.a').length === 3 && !document.querySelector('.a:last-child .muted')")
    assert "I can answer these straight away" in page.locator(".a").nth(2).inner_text()
    page.select_option("#askLang", "ta")
    page.click("#suggest button:has-text('இந்த வாரம் யாருக்கு உதவி தேவை?')")
    page.wait_for_function("document.querySelectorAll('.a .text').length === 4")
    assert "ஆவண உதவி தேவை" in page.locator(".a .text").nth(3).inner_text()
    shot(page, "teacher-laptop-ask")


def test_phone_shows_what_the_teacher_sees(page, server):
    open_app(page, server)
    kavya_to_plan(page)
    page.click("[data-act=settings]")
    page.click("[data-act=open-shared]")
    page.wait_for_selector(".sheet")
    t = page.inner_text(".sheet")
    for want in ("What your teacher sees", "10B-07", "Lab technician", "0/7", "0/2 · 0/3 · 0/1 · 0/1", "Lesson", "Bank account (Aadhaar)",
                 "Never leaves this phone", "community"):
        assert want in t, want


def test_teacher_screens_at_phone_size(browser, server, shot):
    ctx = browser.new_context(viewport=SIZES["phone"], device_scale_factor=1)
    p = ctx.new_page()
    open_teacher(p, server)
    shot(p, "teacher-phone-overview")
    p.click("[data-tab=students]")
    p.wait_for_selector("#studentList tbody tr")
    shot(p, "teacher-phone-students")
    p.click("tr[data-roll='10B-01']")
    p.wait_for_selector("#drawer h2")
    shot(p, "teacher-phone-drawer")
    ctx.close()
