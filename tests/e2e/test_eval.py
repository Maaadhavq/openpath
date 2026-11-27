"""The eval harness runs end to end (against the fake server here), and the Checks tab shows its numbers."""
from __future__ import annotations

import io
import json
import struct
import subprocess
import sys
import wave

from helpers import PASSCODE, ROOT, open_app


def _wav(path, seconds=1.2):
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000)
        w.writeframes(struct.pack("<h", 0) * int(seconds * 16000))
    path.write_bytes(buf.getvalue())


def test_eval_harness_and_checks(page, browser, server, tmp_path):
    samples = tmp_path / "samples"; samples.mkdir()
    rows = [("a.wav", "s1", "quiet", "home", "நான் எங்க கடையில கணக்கு எழுதுவேன்", "accounts"),
            ("b.wav", "s2", "noisy", "school", "எனக்கு அறிவியல் பிடிக்கும்", "science"),
            ("c.wav", "s2", "noisy", "style", "உதவி செய்யப் பிடிக்கும்", "hands")]
    for r in rows:
        _wav(samples / r[0])
    manifest = tmp_path / "manifest.csv"
    manifest.write_text("file,speaker_id,condition,question_id,reference_text,expected_option_id\n" + "\n".join(",".join(r) for r in rows) + "\n", encoding="utf-8")
    copy = tmp_path / "eval_results.json"
    cmd = [sys.executable, str(ROOT / "eval" / "run_eval.py"), "--base-url", server, "--passcode", PASSCODE, "--manifest", str(manifest),
           "--samples", str(samples), "--out-dir", str(tmp_path / "out"), "--app-copy", str(copy)]
    refused = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    assert refused.returncode == 2 and "fake mode" in refused.stdout
    done = subprocess.run(cmd + ["--allow-fake"], capture_output=True, text=True, encoding="utf-8")
    assert done.returncode == 0, done.stdout + done.stderr
    s = json.loads(copy.read_text(encoding="utf-8"))
    assert s["recordings"] == 3 and s["speakers"] == 2 and s["fake"] is True and "adults" in s["speakers_note"]
    assert s["correct"] == 2 and s["no_suggestion_rate"] == 0 and s["by_condition"]["noisy"]["recordings"] == 2
    assert 0 < s["cer"] < 0.5 and s["cost_per_conversation_inr"] > 0
    assert "transcript" not in json.dumps(s)               # the copy for the app has no transcripts
    assert list((tmp_path / "out").glob("*.md"))

    # the Checks tab reads it
    ctx = browser.new_context(service_workers="block")
    p = ctx.new_page()
    p.route("**/data/eval_results.json", lambda route: route.fulfill(status=200, content_type="application/json", body=copy.read_text(encoding="utf-8")))
    open_app(p, server)
    p.click("[data-act=panel][data-id=checks]")
    p.wait_for_function("document.getElementById('pbody').innerText.includes('Measured on real Tamil speech')")
    text = p.inner_text("#pbody")
    assert "2/3" in text and "The speakers were adults." in text and "Simulated voice: not a real measurement." in text
    ctx.close()


def test_checks_say_not_measured_yet(page, server):
    open_app(page, server)
    page.click("[data-act=panel][data-id=checks]")
    assert "Not measured yet." in page.inner_text("#pbody")
