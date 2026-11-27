"""Starts the server in fake mode for the browser tests and configures Playwright."""
from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest

from helpers import FAKE_WAV, PASSCODE, ROOT, SHOTS


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="session")
def server():
    port = _free_port()
    env = dict(os.environ, FAKE_SARVAM="1", DEMO_PASSCODE=PASSCODE, OPENPATH_NO_DOTENV="1", SARVAM_API_KEY="", LOG_LEVEL="warning")
    SHOTS.mkdir(exist_ok=True)
    log = open(SHOTS / "server.log", "w", encoding="utf-8")
    proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "server.main:app", "--host", "127.0.0.1", "--port", str(port), "--workers", "1"],
                            cwd=ROOT, env=env, stdout=log, stderr=log)
    base = f"http://127.0.0.1:{port}"
    for _ in range(100):
        try:
            if httpx.get(base + "/api/health", timeout=1).status_code == 200:
                break
        except httpx.HTTPError:
            pass
        time.sleep(0.1)
    else:
        proc.terminate()
        raise RuntimeError("server did not start")
    yield base
    proc.terminate()
    proc.wait(timeout=10)


@pytest.fixture(scope="session")
def browser_type_launch_args(browser_type_launch_args):
    # Fake microphone that plays a WAV file, with the permission prompt auto-accepted (used by the voice test).
    args = ["--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream", f"--use-file-for-fake-audio-capture={FAKE_WAV}"]
    return {**browser_type_launch_args, "args": args}


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    return {**browser_context_args, "viewport": {"width": 1280, "height": 800}}


@pytest.fixture()
def shot():
    SHOTS.mkdir(exist_ok=True)

    def save(page, name: str):
        page.screenshot(path=str(SHOTS / f"{name}.png"), full_page=False)
    return save
