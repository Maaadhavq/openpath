"""Takes the real screenshots used on the teacher home page (teacher/img/*.webp), from a local server with sample data.

    python scripts/teacher_shots.py

Kavya's phone chooses Lab technician and ticks one step, so the workspace shows live activity. Re-run after changing
the teacher workspace, so the home page always shows the product as it is.
"""
from __future__ import annotations

import io
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx
from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "teacher" / "img"
CODE = "246810"
sys.path.insert(0, str(ROOT / "tests" / "e2e"))
from helpers import kavya_to_plan  # noqa: E402


def save(png: bytes, name: str, width: int = 1280) -> None:
    im = Image.open(io.BytesIO(png)).convert("RGB")
    if im.width > width:
        im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
    im.save(OUT / f"{name}.webp", "WEBP", quality=82, method=6)
    print(f"  {name}.webp {im.width}x{im.height} {(OUT / f'{name}.webp').stat().st_size // 1024} KB")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    env = dict(os.environ, FAKE_SARVAM="1", DEMO_PASSCODE=CODE, OPENPATH_NO_DOTENV="1", LOG_LEVEL="warning")
    proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "server.main:app", "--host", "127.0.0.1", "--port", str(port)],
                            cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    base = f"http://127.0.0.1:{port}"
    try:
        for _ in range(100):
            try:
                if httpx.get(base + "/api/health", timeout=1).status_code == 200:
                    break
            except httpx.HTTPError:
                time.sleep(0.1)
        with sync_playwright() as p:
            b = p.chromium.launch()
            phone = b.new_context(viewport={"width": 390, "height": 844})
            pg = phone.new_page()
            pg.goto(base + "/")
            pg.wait_for_function("window.OPENPATH && window.OPENPATH_CHECKS")
            kavya_to_plan(pg)
            pg.check("input[data-act=task][data-id=t1]")
            pg.wait_for_function("document.getElementById('phStatus').innerText.includes('Synced')")

            laptop = b.new_context(viewport={"width": 1280, "height": 800}, device_scale_factor=1.5, color_scheme="light")
            t = laptop.new_page()
            t.add_init_script(f"localStorage.setItem('op.teacher.code', '{CODE}')")
            t.goto(base + "/teacher/")
            t.wait_for_function("document.getElementById('feed') && document.getElementById('feed').innerText.includes('chose Lab technician')")
            save(t.screenshot(), "overview", 1600)
            # A closer crop for the "Live from the phones" feature: the figures, this week's blockers and the live feed.
            save(t.screenshot(clip={"x": 50, "y": 130, "width": 1180, "height": 330}), "overview-live", 1600)
            t.click("[data-tab=students]")
            t.wait_for_selector("tr[data-roll='10B-07']")
            t.click("tr[data-roll='10B-07']")
            t.wait_for_selector("#drawer h2")
            t.wait_for_timeout(300)
            save(t.screenshot(), "student", 1600)
            t.click("#closeDrawer")
            t.click("[data-tab=actions]")
            t.wait_for_selector("#act-bank_account_aadhaar")
            save(t.screenshot(), "actions", 1600)
            t.click("[data-tab=ask]")
            t.click("#suggest button:has-text('Who needs help this week?')")
            t.wait_for_selector(".a .text")
            t.wait_for_timeout(300)
            save(t.screenshot(), "ask", 1600)
            b.close()
    finally:
        proc.terminate()


if __name__ == "__main__":
    main()
