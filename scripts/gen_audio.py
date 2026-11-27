"""Makes the fixed Tamil voice clips once with Sarvam Bulbul, so the app can play them offline.

    python scripts/gen_audio.py --prompts-only   # rebuild app/data/prompts.json only (no API call)
    python scripts/gen_audio.py                  # prompts.json + any missing app/audio/<key>.mp3
    python scripts/gen_audio.py --force          # remake every clip
    python scripts/gen_audio.py --only confirm,q_home

Needs SARVAM_API_KEY and TTS_SPEAKER (a Bulbul v4 Flash persona ID) in the environment or in .env.
Writes app/audio/index.json, which the app and the service worker read to know which clips exist.
Prints the characters sent and the estimated cost at Rs 2 per 1,000 characters (before GST).
"""
from __future__ import annotations

import argparse
import base64
import json
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from server.config import DATA_DIR, load_settings  # noqa: E402

AUDIO_DIR = ROOT / "app" / "audio"
RS_PER_1000_CHARS = 2.0

# Fixed lines. Keys are used by app/js/ui.js; keep the Tamil exactly as shown on screen.
FIXED = {
    "greeting": {"ta": "வணக்கம்! மூன்று சிறு கேள்விகள். பேசலாம், அல்லது படத்தைத் தொடலாம்.", "en": "Hello! Three short questions. Speak, or tap a picture."},
    "confirm": {"ta": "சரியா? படத்தைத் தொட்டு உறுதி செய்.", "en": "Is this right? Tap the picture to confirm."},
    "not_caught": {"ta": "புரியவில்லை. அருகிலுள்ள படத்தைத் தொடு.", "en": "I didn't catch that. Tap the closest picture."},
    "voice_offline": {"ta": "குரலுக்கு இணையம் தேவை. படத்தைத் தொடு.", "en": "Voice needs a signal. Tap a picture."},
    "heard_prefix": {"ta": "நீ சொன்னது:", "en": "You said:"},
    "plan_ready": {"ta": "உன் நான்கு வாரத் திட்டம் தயார்.", "en": "Your 4-week plan is ready."},
    "support_intro": {"ta": "உனக்குக் கிடைக்கும் உதவி இதோ. இவை இந்த போனிலேயே சரிபார்க்கப்பட்டன.", "en": "Here is the support you can get. It was checked on this phone."},
}


def build_prompts() -> dict:
    questions = json.loads((DATA_DIR / "questions.json").read_text(encoding="utf-8"))
    paths = json.loads((DATA_DIR / "paths.json").read_text(encoding="utf-8"))
    prompts = dict(FIXED)
    for q in questions:
        prompts[f"q_{q['id']}"] = q["q"]
    for q in questions:
        for o in q["opts"]:
            prompts[f"opt_{q['id']}_{o['id']}"] = o["label"]
    for p in paths:
        prompts[f"path_{p['id']}"] = p["name"]
    for p in paths:
        prompts[f"story_{p['id']}"] = p["story"]
    return prompts


def tts(client: httpx.Client, settings, text: str) -> bytes:
    body = {"text": text, "language_code": "ta-IN", "model": settings.tts_model, "speaker": settings.tts_speaker,
            "pace": 0.95, "speech_sample_rate": 24000, "output_audio_codec": "mp3"}
    for attempt in (1, 2):
        r = client.post(f"{settings.sarvam_base}/text-to-speech", json=body,
                        headers={"api-subscription-key": settings.sarvam_api_key}, timeout=20)
        if r.status_code in (429, 503) and attempt == 1:
            time.sleep(1.0)
            continue
        if r.status_code != 200:
            raise SystemExit(f"Bulbul returned {r.status_code}: {r.text[:300]}")
        audios = r.json().get("audios") or []
        if not audios:
            raise SystemExit("Bulbul returned no audio")
        return b"".join(base64.b64decode(a) for a in audios)
    raise SystemExit("Bulbul kept failing")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--prompts-only", action="store_true", help="only rebuild app/data/prompts.json")
    ap.add_argument("--force", action="store_true", help="remake clips that already exist")
    ap.add_argument("--only", default="", help="comma-separated keys to make")
    args = ap.parse_args()

    prompts = build_prompts()
    (DATA_DIR / "prompts.json").write_text(json.dumps(prompts, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    total_chars = sum(len(v["ta"]) for v in prompts.values())
    print(f"prompts.json: {len(prompts)} lines, {total_chars} Tamil characters (about Rs {total_chars * RS_PER_1000_CHARS / 1000:.2f} for all)")
    if args.prompts_only:
        return

    settings = load_settings()
    if not settings.sarvam_api_key:
        raise SystemExit("SARVAM_API_KEY is not set")
    if not settings.tts_speaker:
        raise SystemExit("TTS_SPEAKER is not set. Pick a Tamil Bulbul v4 Flash persona on Sarvam's Voices page and put its ID in .env")

    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    only = {k.strip() for k in args.only.split(",") if k.strip()}
    sent = 0
    with httpx.Client() as client:
        for key, line in prompts.items():
            if only and key not in only:
                continue
            out = AUDIO_DIR / f"{key}.mp3"
            if out.exists() and not args.force:
                continue
            out.write_bytes(tts(client, settings, line["ta"]))
            sent += len(line["ta"])
            print(f"  {key}.mp3  ({len(line['ta'])} chars)")
    keys = [k for k in prompts if (AUDIO_DIR / f"{k}.mp3").exists()]
    index = {"model": settings.tts_model, "speaker": settings.tts_speaker, "keys": keys}
    (AUDIO_DIR / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"sent {sent} characters, estimated Rs {sent * RS_PER_1000_CHARS / 1000:.2f} before GST; {len(keys)}/{len(prompts)} clips in app/audio")
    print("Remember to bump CACHE in app/sw.js so phones pick up the new clips.")


if __name__ == "__main__":
    main()
