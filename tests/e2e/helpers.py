"""Shared helpers for the browser tests."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PASSCODE = "246810"
SHOTS = ROOT / "test-results"
FAKE_WAV = Path(__file__).resolve().parent / "kavya_home.wav"


def open_app(page, base: str):
    page.goto(base + "/")
    page.wait_for_function("window.OPENPATH && window.OPENPATH_CHECKS")
    page.evaluate("window.OPENPATH.ready")


def unlock_kavya(page):
    page.click("[data-act=who][data-id=kavya]")
    for pin in ("sun", "leaf", "star"):
        page.click(f"[data-act=pin][data-id={pin}]")
    page.wait_for_selector("[data-act=ans]")


def kavya_to_plan(page, path_id: str = "labtech"):
    """Kavya's demo path by taps: sample answers, sample details, skills, paths, choose a path."""
    unlock_kavya(page)
    page.click("[data-act=sample-answers]")
    page.click("[data-act=go][data-s=details]")
    page.click("[data-act=sample-profile]")
    page.click("[data-act=go][data-s=skills]")
    page.click("[data-act=go][data-s=paths]")
    page.click(f"[data-act=choose][data-id={path_id}]")
    page.wait_for_selector("#planDone")
