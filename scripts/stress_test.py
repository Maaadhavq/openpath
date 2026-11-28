"""Load and integrity test: many phones syncing at once while teachers poll and ask.

    python scripts/stress_test.py                     # starts its own local server in fake mode
    python scripts/stress_test.py --phones 74 --events 40 --teachers 5

Simulated phones use roll numbers 26 to 99 (new students), so the 25 sample students stay as they are. Each phone
sends its events one request at a time like the real queue, resends some (duplicates) and delivers some late (out of
order). At the end every row on the server must match that phone's latest event. Prints latency percentiles,
throughput and errors. Do not point it at the live demo server: it adds rows to the teacher page.
"""
from __future__ import annotations

import argparse
import asyncio
import os
import random
import socket
import statistics
import subprocess
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
PATHS = ["nursing", "labtech", "solar", "bike", "accounts", "mobile", "agri", "garment", "teacher", "civil", "copa", "pharma", "engineering", "graphic"]
BLOCKERS = ["bank_account_aadhaar", "income_certificate", "community_certificate", "aadhaar", None]
KINDS = ["lesson", "stories", "practice", "documents", "visit", "decide"]
POLL = [0.5]
QUESTIONS = ["Who needs help this week?", "Who hasn't chosen a path?", "What's coming up?", "How is my class doing?", "Plan visits by career"]


def pct(xs: list[float], q: float) -> float:
    if not xs:
        return 0.0
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(round(q * (len(xs) - 1))))]


def make_events(roll: str, n: int, rng: random.Random) -> list[dict]:
    path, total = rng.choice(PATHS), rng.choice([6, 7, 8])
    start = datetime.now(timezone.utc) - timedelta(minutes=n + 5)
    evs = []
    for i in range(n):
        if i < 2:
            ev = {"step": "discover" if i == 0 else "paths", "path": None, "plan_done": None, "blocker": "no_path_yet"}
        else:
            done = min(total, i - 2)
            ev = {"step": "plan", "path": path, "plan_done": f"{done}/{total}", "blocker": rng.choice(BLOCKERS),
                  "weeks": [f"{min(done, 2)}/2", f"{max(0, min(done - 2, total - 4))}/{total - 4}", "0/1", "0/1"],
                  "next_task": KINDS[min(done, 5)] if done < total else None}
            if ev["next_task"] is None:
                del ev["next_task"]
        ev.update(event_id=str(uuid.uuid4()), student=roll, ts=(start + timedelta(minutes=i)).isoformat().replace("+00:00", "Z"))
        if rng.random() < 0.5:
            ev["name"] = "Student" + roll[-2:]
        evs.append(ev)
    return evs


async def phone(client, base, roll, n, rng, lat, errs, sent_last, think=0.0):
    evs = make_events(roll, n, rng)
    order = list(range(n))
    for _ in range(max(1, n // 10)):                       # some events arrive late
        a, b = rng.randrange(n), rng.randrange(n)
        order[a], order[b] = order[b], order[a]
    for idx in order:
        batch = [evs[idx]] + ([evs[rng.randrange(n)]] if rng.random() < 0.15 else [])   # some resends
        t0 = time.perf_counter()
        try:
            r = await client.post(base + "/api/sync", json={"events": batch})
            lat["sync"].append((time.perf_counter() - t0) * 1000)
            if r.status_code != 200:
                errs.append(f"sync {r.status_code}")
        except httpx.HTTPError as e:
            errs.append(f"sync {type(e).__name__}")
        if think:
            await asyncio.sleep(think * rng.uniform(0.5, 1.5))     # a student tapping, not a script
    sent_last[roll] = max(evs, key=lambda e: e["ts"])


async def teacher(client, base, code, stop, lat, errs, ask: bool):
    i = 0
    while not stop.is_set():
        t0 = time.perf_counter()
        try:
            if ask:
                r = await client.post(base + "/api/ask", json={"question": QUESTIONS[i % len(QUESTIONS)]}, headers={"X-Teacher-Code": code})
                lat["ask"].append((time.perf_counter() - t0) * 1000)
            else:
                r = await client.get(base + "/api/class", headers={"X-Teacher-Code": code})
                lat["class"].append((time.perf_counter() - t0) * 1000)
            if r.status_code != 200:
                errs.append(f"{'ask' if ask else 'class'} {r.status_code}")
        except httpx.HTTPError as e:
            errs.append(f"teacher {type(e).__name__}")
        i += 1
        await asyncio.sleep(1.0 if ask else POLL[0])


async def run(base: str, code: str, phones: int, events: int, teachers: int, seed: int, think: float = 0.0, poll: float = 0.5) -> dict:
    rng = random.Random(seed)
    lat = {"sync": [], "class": [], "ask": []}
    errs: list[str] = []
    sent_last: dict[str, dict] = {}
    limits = httpx.Limits(max_connections=200, max_keepalive_connections=200)
    async with httpx.AsyncClient(timeout=30, limits=limits) as client:
        await client.post(base + "/api/reset", headers={"X-Teacher-Code": code})
        stop = asyncio.Event()
        watchers = [asyncio.create_task(teacher(client, base, code, stop, lat, errs, ask=i == 0)) for i in range(teachers)]
        t0 = time.perf_counter()
        rolls = [f"10B-{n:02d}" for n in range(26, 26 + phones)]
        POLL[0] = poll
        await asyncio.gather(*(phone(client, base, r, events, random.Random(rng.random()), lat, errs, sent_last, think) for r in rolls))
        elapsed = time.perf_counter() - t0
        stop.set()
        await asyncio.gather(*watchers)
        snap = (await client.get(base + "/api/class", headers={"X-Teacher-Code": code})).json()
    rows = {s["roll"]: s for s in snap["students"]}
    wrong = [r for r, ev in sent_last.items() if r not in rows or rows[r]["plan_done"] != ev.get("plan_done") or rows[r]["path"] != ev.get("path")]
    return {"phones": phones, "events_per_phone": events, "think_seconds": think, "teacher_poll_seconds": poll, "sync_requests": len(lat["sync"]), "seconds": round(elapsed, 2),
            "sync_per_second": round(len(lat["sync"]) / elapsed, 1),
            "latency_ms": {k: {"p50": round(pct(v, .5), 1), "p95": round(pct(v, .95), 1), "p99": round(pct(v, .99), 1), "n": len(v)} for k, v in lat.items()},
            "errors": len(errs), "error_kinds": sorted(set(errs))[:10], "rows_on_server": len(rows),
            "rows_wrong": len(wrong), "wrong_examples": wrong[:5]}


def start_server(port: int) -> subprocess.Popen:
    env = dict(os.environ, FAKE_SARVAM="1", DEMO_PASSCODE="246810", OPENPATH_NO_DOTENV="1", LOG_LEVEL="warning", SYNC_PER_MINUTE="100000")
    return subprocess.Popen([sys.executable, "-m", "uvicorn", "server.main:app", "--host", "127.0.0.1", "--port", str(port), "--workers", "1"],
                            cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base-url", default="", help="an already running server; default: start one locally")
    ap.add_argument("--code", default="246810")
    ap.add_argument("--phones", type=int, default=74)
    ap.add_argument("--events", type=int, default=40)
    ap.add_argument("--teachers", type=int, default=5)
    ap.add_argument("--seed", type=int, default=2026)
    ap.add_argument("--think", type=float, default=0.0, help="seconds between a phone's events (0 = burst)")
    ap.add_argument("--poll", type=float, default=0.5, help="seconds between a teacher page's polls (the real page uses 3)")
    a = ap.parse_args()
    proc = None
    base = a.base_url.rstrip("/")
    if not base:
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]
        proc = start_server(port)
        base = f"http://127.0.0.1:{port}"
        for _ in range(100):
            try:
                if httpx.get(base + "/api/health", timeout=1).status_code == 200:
                    break
            except httpx.HTTPError:
                time.sleep(0.1)
    try:
        res = asyncio.run(run(base, a.code, a.phones, a.events, a.teachers, a.seed, a.think, a.poll))
    finally:
        if proc:
            proc.terminate()
    import json
    print(json.dumps(res, indent=2))
    ok = res["errors"] == 0 and res["rows_wrong"] == 0
    print("RESULT:", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
