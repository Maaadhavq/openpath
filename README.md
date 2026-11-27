# OpenPath

A voice-first career and scheme guide for rural Tamil Nadu students in Classes 9 to 12. Team 5fire, VIT Chennai, for the Citi India Hackathon 2026 finale.

- **Phone:** an installable web app (PWA). The scheme rules, the 14 paths and the 4-week plan run on the phone and work in airplane mode.
- **Voice:** the phone records a 16 kHz WAV and sends it to `/api/talk`. Saaras v4 turns it into text and Sarvam-105B matches it to one of the picture options. The student confirms every answer by tapping the picture. The language model never decides who is eligible.
- **Teacher:** `/teacher` shows class 10-B live. The phone sends only progress and one blocker, never community, income, gender, documents or answers.

**Live:** student app https://openpath-nx3v.onrender.com · teacher dashboard https://openpath-nx3v.onrender.com/teacher/ (free Render server: the first visit after 15 idle minutes takes about a minute).

`CLAUDE.md` is the full build brief. `reference/openpath_prototype.html` is the Round 2 prototype the app was ported from.

## Run locally

```
python -m venv .venv
.venv\Scripts\activate                 # macOS/Linux: source .venv/bin/activate
pip install -r server/requirements.txt -r server/requirements-dev.txt
playwright install chromium
uvicorn server.main:app --reload --port 8000
```

Open http://localhost:8000 (the microphone works on localhost) and http://localhost:8000/teacher/ in a second tab.

Settings come from `.env` (git-ignored; see `.env.example`). With `FAKE_SARVAM=1`, voice answers return Kavya's canned answers and the app shows "(simulated voice)". Enter the `DEMO_PASSCODE` in the app's Settings sheet so voice works.

The service worker serves the app cache-first. After changing anything in `app/`, bump `CACHE` in `app/sw.js`, or tick "Update on reload" in DevTools.

## Tests

```
pytest server/tests        # API: talk pipeline (Sarvam mocked), limits, sync schema, privacy, roster
pytest tests/e2e           # browser: 47 rule tests, port vs prototype, offline, voice (fake), sync, teacher
```

The e2e run saves phone (390×844) and laptop (1280×800) screenshots in `test-results/`.

## Voice clips

```
python scripts/gen_audio.py              # needs SARVAM_API_KEY and TTS_SPEAKER; about Rs 4 for all 52 clips
```

It writes `app/audio/*.mp3` and `app/audio/index.json`. Commit them and bump `CACHE`.

## Measuring on real Tamil speech

1. Put 16 kHz mono WAVs in `eval/samples/` (adults who agreed only; the folder is git-ignored). Convert phone recordings with `ffmpeg -i in.m4a -ac 1 -ar 16000 out.wav`.
2. List them in `eval/manifest.csv`: `file, speaker_id, condition (quiet|noisy), question_id, reference_text, expected_option_id`.
3. Run the server with the real key, then `python eval/run_eval.py --base-url http://localhost:8000 --passcode <code>`.

It writes `eval/results/<time>.json` and `.md` (a table for the slide) and copies the summary to `app/data/eval_results.json`, which the Checks tab shows.

## Deploy (Render, free plan)

`render.yaml` defines one web service: the app, `/teacher` and the API on one origin. Set `SARVAM_API_KEY`, `DEMO_PASSCODE` and `TTS_SPEAKER` in the Render dashboard; never in the repo. After each deploy: bump `CACHE` in `app/sw.js`, open `/api/health`, then open the app on the phone twice. Free servers sleep after 15 minutes: open `/teacher` early, and its polling keeps the server awake.
