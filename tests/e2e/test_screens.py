"""Screenshots of every screen at phone (390x844) and laptop (1280x800) size, saved to test-results/ for a human to look at."""
from __future__ import annotations

import pytest

from helpers import open_app, unlock_kavya

SIZES = {"phone": {"width": 390, "height": 844}, "laptop": {"width": 1280, "height": 800}}


@pytest.mark.parametrize("size", list(SIZES))
def test_screens(browser, server, shot, size):
    ctx = browser.new_context(viewport=SIZES[size], device_scale_factor=1)
    page = ctx.new_page()
    open_app(page, server)
    shot(page, f"{size}-1-lock")
    unlock_kavya(page)
    shot(page, f"{size}-2-discover")
    page.click("[data-act=sample-answers]")
    page.click("[data-act=go][data-s=details]")
    page.click("[data-act=sample-profile]")
    shot(page, f"{size}-3-details")
    page.click("[data-act=go][data-s=skills]")
    shot(page, f"{size}-4-skills")
    page.click("[data-act=go][data-s=paths]")
    shot(page, f"{size}-5-paths")
    page.click("[data-act=choose][data-id=labtech]")
    page.wait_for_selector("#planDone")
    shot(page, f"{size}-6-plan")
    page.click("[data-act=go][data-s=support]")
    shot(page, f"{size}-7-support")
    page.click("[data-act=settings]")
    page.wait_for_selector(".sheet")
    shot(page, f"{size}-8-settings")
    page.click("[data-act=open-checks]")
    if size == "phone":
        page.wait_for_selector("#ckRules")
    else:
        page.wait_for_selector("#pbody #ckRules")
    shot(page, f"{size}-9-checks")
    ctx.close()
