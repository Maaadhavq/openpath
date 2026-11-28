# OpenPath setup

Everything Team 5fire needs to get OpenPath running for Monday's demo. Do the steps in order.

- Student app: https://openpath-nx3v.onrender.com
- Teacher dashboard: https://openpath-nx3v.onrender.com/teacher/
- Code: https://github.com/Maaadhavq/openpath
- Server: Render dashboard → workspace "mapro" → service **openpath** (free plan, Singapore)

## 1. Server secrets (Madhav, once)

Render dashboard → openpath → **Environment** → add:

| Key | Value |
|---|---|
| `DEMO_PASSCODE` | a 6-digit code; share it with the team only. It also opens the teacher page unless `TEACHER_CODE` is set |
| `TEACHER_CODE` | optional: a separate class code for the teacher page |
| `SARVAM_API_KEY` | the key from the Sarvam dashboard (when it arrives) |
| `FAKE_SARVAM` | change to `0` once the key is in (it is `1` now: the app shows "(simulated voice)") |

Saving restarts the server. Check https://openpath-nx3v.onrender.com/api/health: `"fake": false` means real voice is on.

Never put the key or passcode in the code, GitHub, chat groups or slides.

## 2. The Android phone (Rohit)

1. Open the student app link in **Chrome**.
2. Tap ⋮ → **Install app**. OpenPath appears in the app drawer.
3. Open OpenPath from the app drawer, tap the **sliders icon** (Settings), enter the demo passcode, tap **Save**.
4. Allow the microphone when the app asks the first time you tap **Speak**.
5. A new student taps **New student** and uses roll **26 or above** (01 to 25 are the sample class already on the teacher page).
6. Test: Kavya, PIN **sun, leaf, star** → answer → details → Lab technician. Turn on **airplane mode**: Support still works and a tick shows "1 update waiting". Turn airplane mode off: it shows "Synced".

After every new deploy, open the app **twice** to get the new version. If it still looks old: Android Settings → Apps → Chrome → Storage → manage space → clear data for the site, then open the link again.

## 3. The teacher laptop

1. Open the teacher dashboard link and enter the class code (`TEACHER_CODE`, or the demo passcode). It refreshes every 3 seconds and keeps the free server awake.
2. Tabs: **Overview** (figures, this week's blockers, live activity from phones, paths chosen, coming up, what the phone sent), **Students** (search, filters, click a student for details), **Actions** (one card per blocker, with a parent message to copy and a print view) and **Ask OpenPath**.
3. **Reset demo** (top right) puts the class back to the 25 sample students.

The free server sleeps after 15 minutes without visits and takes about a minute to wake. Open the dashboard at least 15 minutes before presenting.

## 4. Showing the phone on the big screen

1. On the phone: Settings → About phone → tap **Build number** 7 times → Developer options → turn on **USB debugging**.
2. On the demo laptop, install scrcpy (https://github.com/Genymobile/scrcpy, Windows release zip), connect the phone by USB, accept the prompt on the phone, run `scrcpy`.

## 5. Tamil voice clips (Nischay, once the key arrives)

1. Listen to the Tamil Bulbul v4 Flash voices on Sarvam's Voices page and pick one: `aravind_ta_ads`, `aravind_ta_suspense`, `gokul_ta_narration` or `vijay_ta_narration`.
2. In your local `.env` set `SARVAM_API_KEY=...` and `TTS_SPEAKER=<the voice>`.
3. Run `python scripts/gen_audio.py` (about ₹4 for all 52 clips). It writes `app/audio/`.
4. Bump `CACHE` in `app/sw.js` (for example `op-v2` → `op-v3`), commit, push, deploy (step 8).

## 6. Speech measurements for the slide (Nischay, Joshnavi)

1. Record adults who agreed. Convert each to 16 kHz mono WAV: `ffmpeg -i in.m4a -ac 1 -ar 16000 out.wav`. Put them in `eval/samples/` (never committed).
2. List each file in `eval/manifest.csv`: `file, speaker_id, condition (quiet|noisy), question_id (home|school|style), reference_text, expected_option_id`.
3. Start the server locally with the real key and `FAKE_SARVAM=0`, then run `python eval/run_eval.py --base-url http://localhost:8000 --passcode <code>`.
4. Use the Markdown table it prints for the slide, with its date, and say the speakers were adults. It also writes `app/data/eval_results.json`, which the Checks tab shows: bump `CACHE`, commit, push, deploy.
5. Check the real cost on the Sarvam dashboard after the run.

## 7. Running it on your laptop (anyone)

Needs Python 3.10 or newer and Git.

```
git clone https://github.com/Maaadhavq/openpath.git
cd openpath
python -m venv .venv
.venv\Scripts\activate
pip install -r server/requirements.txt -r server/requirements-dev.txt
playwright install chromium
copy .env.example .env
```

In `.env`, set `DEMO_PASSCODE` to any code and `FAKE_SARVAM=1` (or add the real key). Then:

```
uvicorn server.main:app --reload --port 8000
```

Open http://localhost:8000 and http://localhost:8000/teacher/. Tests: `pytest server/tests` and `pytest tests/e2e` (screenshots land in `test-results/`).

## 8. Deploying a change

1. Run both test suites; they must pass.
2. If anything in `app/` changed, bump `CACHE` in `app/sw.js`.
3. Commit and `git push`.
4. Render dashboard → openpath → **Manual Deploy** → Deploy latest commit. Pushing alone does not deploy.
5. Open `/api/health`, then open the app on the phone twice.

A deploy or restart clears the teacher dashboard back to the 25 sample students. No new features after Sunday 2 PM.

## 9. If something breaks on Monday

| Problem | What to do |
|---|---|
| Voice slow or failing | Tap the pictures. Say: "Voice needs a signal; tapping always works." |
| "Enter the demo passcode" | Settings (sliders icon) → passcode → Save |
| Venue Wi-Fi fails | Phone hotspot. The offline part needs no internet at all |
| Teacher page says it cannot reach the server | Wait a minute: the free server is waking up |
| Teacher row did not update | On the phone, check the top line says "Synced"; if it says "updates waiting", turn airplane mode off and wait a few seconds |
| Mirroring fails | Play the voice part from the demo video, then do the offline part live |
