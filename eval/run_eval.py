"""Measures OpenPath's voice pipeline on real Tamil recordings, through the same /api/talk the phone uses.

    python eval/run_eval.py --base-url http://localhost:8000 --passcode 123456

Reads eval/manifest.csv (file, speaker_id, condition, question_id, reference_text, expected_option_id) and the audio
in eval/samples/ (16 kHz mono WAV; convert phone recordings with: ffmpeg -i in.m4a -ac 1 -ar 16000 out.wav).
Record only adults who agreed. The audio folder is git-ignored.

Writes eval/results/<timestamp>.json and .md, and copies the summary (no transcripts) to app/data/eval_results.json
for the Checks tab. Every output says the speakers were adults.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import statistics
import sys
import time
import unicodedata
from datetime import datetime
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
STT_RS_PER_MIN = 0.49
LLM_RS_PER_M_IN, LLM_RS_PER_M_OUT = 10.0, 25.0
ANSWERS_PER_CONVERSATION = 3
ADULTS = "The speakers were adults who agreed to be recorded."

try:
    import jiwer
    def cer(refs: list[str], hyps: list[str]) -> float:
        return float(jiwer.cer(refs, hyps))
    CER_TOOL = "jiwer.cer"
except ImportError:                                  # same measure, if jiwer cannot be installed
    def _dist(a: str, b: str) -> int:
        prev = list(range(len(b) + 1))
        for i, ca in enumerate(a, 1):
            cur = [i]
            for j, cb in enumerate(b, 1):
                cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
            prev = cur
        return prev[-1]

    def cer(refs: list[str], hyps: list[str]) -> float:
        return sum(_dist(r, h) for r, h in zip(refs, hyps)) / max(1, sum(len(r) for r in refs))
    CER_TOOL = "edit distance (jiwer not installed)"


def normalise(text: str) -> str:
    """Unicode NFC, no punctuation, single spaces (the same for reference and transcript)."""
    text = unicodedata.normalize("NFC", text or "").lower()
    text = "".join(" " if unicodedata.category(ch).startswith("P") else ch for ch in text)
    return re.sub(r"\s+", " ", text).strip()


def pct(values: list[float], q: float) -> float | None:
    if not values:
        return None
    v = sorted(values)
    k = (len(v) - 1) * q
    lo, hi = int(k), min(int(k) + 1, len(v) - 1)
    return round(v[lo] + (v[hi] - v[lo]) * (k - lo))


def wav_seconds(data: bytes) -> float:
    pos, byte_rate, size = 12, None, None
    while pos + 8 <= len(data):
        cid, n = data[pos:pos + 4], int.from_bytes(data[pos + 4:pos + 8], "little")
        if cid == b"fmt ":
            byte_rate = int.from_bytes(data[pos + 16:pos + 20], "little")
        elif cid == b"data":
            size = min(n, len(data) - pos - 8)
            break
        pos += 8 + n + (n & 1)
    if data[:4] != b"RIFF" or not byte_rate or size is None:
        raise ValueError("not a WAV file")
    return size / byte_rate


def post(client: httpx.Client, base: str, passcode: str, path: Path, qid: str) -> tuple[int, dict, float]:
    for _ in range(6):
        t0 = time.perf_counter()
        r = client.post(base + "/api/talk", data={"question_id": qid}, files={"audio": (path.name, path.read_bytes(), "audio/wav")},
                        headers={"X-Demo-Passcode": passcode, "X-Debug": "1"}, timeout=30)
        ms = (time.perf_counter() - t0) * 1000
        if r.status_code == 429:                     # the server allows 20 a minute
            time.sleep(float(r.headers.get("retry-after", 4)))
            continue
        try:
            body = r.json()
        except ValueError:
            body = {}
        return r.status_code, body, ms
    return 429, {}, 0.0


def summarise(items: list[dict], fake: bool, server: dict) -> dict:
    ok = [x for x in items if x["status"] == 200]
    refs = [normalise(x["reference_text"]) for x in ok if x["reference_text"].strip()]
    hyps = [normalise(x["transcript"]) for x in ok if x["reference_text"].strip()]
    correct = sum(1 for x in items if x["correct"])
    shown = sum(1 for x in items if x["highlighted_correct"])
    none = sum(1 for x in ok if not x["suggestion"])
    secs = [x["audio_seconds"] for x in items]
    lat = {k: [x["timings_ms"][k] for x in ok if x.get("timings_ms")] for k in ("total", "stt", "llm")}
    lat["client"] = [x["client_ms"] for x in ok]
    tok_in = [x["usage"]["llm"].get("prompt_tokens") or 0 for x in ok if (x.get("usage") or {}).get("llm")]
    tok_out = [x["usage"]["llm"].get("completion_tokens") or 0 for x in ok if (x.get("usage") or {}).get("llm")]
    per_answer = (statistics.mean(secs) / 60 * STT_RS_PER_MIN if secs else 0.0)
    llm_per_answer = ((statistics.mean(tok_in) * LLM_RS_PER_M_IN + statistics.mean(tok_out) * LLM_RS_PER_M_OUT) / 1e6 if tok_in else 0.0)
    cost = round((per_answer + llm_per_answer) * ANSWERS_PER_CONVERSATION, 2)
    by_cond = {}
    for cond in sorted({x["condition"] for x in items}):
        sub = [x for x in items if x["condition"] == cond]
        sub_ok = [x for x in sub if x["status"] == 200 and x["reference_text"].strip()]
        by_cond[cond] = {"recordings": len(sub), "correct": sum(1 for x in sub if x["correct"]),
                         "cer": round(cer([normalise(x["reference_text"]) for x in sub_ok], [normalise(x["transcript"]) for x in sub_ok]), 4) if sub_ok else None}
    n = len(items)
    return {
        "date": datetime.now().strftime("%d %b %Y"),
        "recordings": n,
        "speakers": len({x["speaker_id"] for x in items}),
        "speakers_note": ADULTS,
        "cer": round(cer(refs, hyps), 4) if refs else None,
        "cer_tool": CER_TOOL,
        "correct": correct,
        "option_accuracy": round(correct / n, 4) if n else None,
        "highlighted_correct": shown,
        "no_suggestion_rate": round(none / len(ok), 4) if ok else None,
        "errors": n - len(ok),
        "latency_ms": {k: {"p50": pct(v, 0.5), "p90": pct(v, 0.9)} for k, v in lat.items()},
        "cost_per_conversation_inr": cost,
        "cost_basis": (f"{ANSWERS_PER_CONVERSATION} answers of {statistics.mean(secs):.1f} s on average at Rs {STT_RS_PER_MIN}/min speech-to-text, "
                       f"plus Sarvam-105B tokens at Rs {LLM_RS_PER_M_IN:g}/{LLM_RS_PER_M_OUT:g} per million in/out"
                       + ("" if tok_in else " (token counts were not returned)") + ". Before GST. Check against the Sarvam dashboard.") if secs else "",
        "by_condition": by_cond,
        "models": server.get("models", {}),
        "fake": fake,
    }


def markdown(s: dict) -> str:
    lat = s["latency_ms"]
    rows = [
        ("Recordings", f"{s['recordings']} from {s['speakers']} speakers"),
        ("Character error rate (speech to text)", f"{s['cer'] * 100:.1f}%" if s["cer"] is not None else "–"),
        ("Answers matched to the right picture", f"{s['correct']}/{s['recordings']} ({(s['option_accuracy'] or 0) * 100:.0f}%)"),
        ("Right picture highlighted (confidence 0.5 or more)", f"{s['highlighted_correct']}/{s['recordings']}"),
        ("No suggestion (student taps)", f"{(s['no_suggestion_rate'] or 0) * 100:.0f}%"),
        ("Response time, median / 90th percentile", f"{(lat['client']['p50'] or 0) / 1000:.1f} s / {(lat['client']['p90'] or 0) / 1000:.1f} s"),
        ("Estimated cost per conversation (3 answers)", f"Rs {s['cost_per_conversation_inr']:.2f} before GST"),
    ]
    for cond, c in s["by_condition"].items():
        rows.append((f"{cond.capitalize()} recordings", f"{c['correct']}/{c['recordings']} right" + (f", CER {c['cer'] * 100:.1f}%" if c["cer"] is not None else "")))
    out = [f"**Measured on real Tamil speech, {s['date']}.** {ADULTS}" + (" SIMULATED VOICE: not a real measurement." if s["fake"] else ""), "",
           "| Measure | Result |", "|---|---|"] + [f"| {a} | {b} |" for a, b in rows]
    out += ["", f"Models: {', '.join(f'{k} {v}' for k, v in s['models'].items())}. CER by {s['cer_tool']}."]
    return "\n".join(out) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base-url", default="http://localhost:8000")
    ap.add_argument("--passcode", required=True)
    ap.add_argument("--manifest", default=str(ROOT / "eval" / "manifest.csv"))
    ap.add_argument("--samples", default=str(ROOT / "eval" / "samples"))
    ap.add_argument("--out-dir", default=str(ROOT / "eval" / "results"))
    ap.add_argument("--app-copy", default=str(ROOT / "app" / "data" / "eval_results.json"), help="where the Checks tab reads the summary; '' to skip")
    ap.add_argument("--allow-fake", action="store_true", help="allow a run against a server in fake mode (never for the slide)")
    args = ap.parse_args()

    base = args.base_url.rstrip("/")
    with httpx.Client() as client:
        server = client.get(base + "/api/health", timeout=60).json()
        if server.get("fake") and not args.allow_fake:
            print("The server is in fake mode, so these would not be real measurements. Use --allow-fake only to test this script.")
            return 2
        rows = list(csv.DictReader(open(args.manifest, encoding="utf-8-sig", newline="")))
        items = []
        for i, row in enumerate(rows, 1):
            path = Path(args.samples) / row["file"]
            if not path.is_file():
                print(f"  skip {row['file']}: not in {args.samples}")
                continue
            try:
                seconds = wav_seconds(path.read_bytes())
            except ValueError:
                print(f"  skip {row['file']}: not a WAV (convert: ffmpeg -i in.m4a -ac 1 -ar 16000 out.wav)")
                continue
            status, body, ms = post(client, base, args.passcode, path, row["question_id"])
            if status == 401:
                print("Wrong passcode.")
                return 2
            sug = body.get("suggestion") if status == 200 else None
            expected = (row.get("expected_option_id") or "").strip() or None
            got = sug["option_id"] if sug else None
            items.append({"file": row["file"], "speaker_id": row["speaker_id"], "condition": (row.get("condition") or "quiet").strip().lower(),
                          "question_id": row["question_id"], "reference_text": row.get("reference_text") or "", "expected_option_id": expected,
                          "status": status, "transcript": body.get("transcript", ""), "suggestion": sug,
                          "correct": status == 200 and got == expected and got is not None or (status == 200 and expected is None and got is None),
                          "highlighted_correct": bool(sug and got == expected and sug.get("confidence", 0) >= 0.5),
                          "timings_ms": body.get("timings_ms"), "client_ms": round(ms), "usage": body.get("usage"), "audio_seconds": round(seconds, 2)})
            mark = "ok " if items[-1]["correct"] else "MISS"
            print(f"  {i:>3}/{len(rows)} {mark} {row['file']}  got={got} want={expected}  {ms / 1000:.1f}s")
    if not items:
        print("No recordings found. Put the WAVs in eval/samples/ and list them in eval/manifest.csv.")
        return 1

    summary = summarise(items, bool(server.get("fake")), server)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{stamp}.json").write_text(json.dumps({"summary": summary, "items": items}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    md = markdown(summary)
    (out / f"{stamp}.md").write_text(md, encoding="utf-8", newline="\n")
    if args.app_copy:
        Path(args.app_copy).write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print()
    print(md)
    print(f"Wrote {out / (stamp + '.json')}" + (f" and {args.app_copy} (bump CACHE in app/sw.js before deploying)" if args.app_copy else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
