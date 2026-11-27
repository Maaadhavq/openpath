# OpenPath: build context for Claude

> **Humans:** put this file in the root of an empty folder as `CLAUDE.md`, with the Round 2 prototype at `reference/openpath_prototype.html`. Open Claude Code in that folder. Claude Code reads this file automatically. You can also paste it into a Claude chat.
>
> **Claude:** this file is written to you. It describes everything you need to build the finale version of OpenPath. Read all of it before writing code.

Version: Saturday 28 Nov 2026, 3 AM IST. Team lead: Madhav K. The working build is due by Sunday 29 Nov, 2 PM IST, and the demo is on Monday 30 Nov.

---

## 0. How to work on this project (instructions to Claude)

- **Read first:** read this whole file before writing code. If it conflicts with your habits, this file wins. If it conflicts with reality (for example, an API behaves differently from what is written here), stop, tell the human what you found, and propose the smallest fix.
- **Order:** build in the phase order in section 12. Finish a phase, run its checks, show the result, then move on. Commit after each phase with a clear message.
- **Keep it simple:**
  - the app is plain JavaScript: no framework, no bundler, no build step
  - the server is FastAPI, with no database server
  - ask before adding any dependency not listed in section 7
- **The prototype is the source of truth:** `reference/openpath_prototype.html` defines the data, rules, copy and look. Port it; do not redesign it. Its 47 rule tests must still pass with the same results.
- **Privacy and secrets:**
  - never put the Sarvam API key in the app, the repo or logs
  - never send a student's profile (gender, class, school, medium, community, income, documents) to the server
  - section 2 has the full list
- **Scheme rules:** never change a rule or a test's expected result unless a human gives you the official source. Then update the rule, its test, its `source` and the `CHECKED` date together.
- **Before you call a phase done:**
  - run the tests
  - look at the page in a browser with Playwright at phone size (390×844) and laptop size (1280×800)
  - save the screenshots to `test-results/`
- **Sarvam details:** if you are unsure about one, open the doc pages in section 16 instead of guessing.
- **No API key yet:** build with `FAKE_SARVAM=1` (section 8.4) and switch to the real API when the key arrives.

**Ask the human at the start, then carry on with defaults if they are not around:**
1. Is the Sarvam API key ready? Default: fake mode until it is.
2. GitHub repo and Render account to deploy from? Default: build locally first.
3. Demo passcode? Default: a random 6-digit code written to `.env` and shown to the human.
4. Which Bulbul voice (`TTS_SPEAKER`)? Default: leave unset and skip audio generation until it is chosen.

---

## 1. Mission and deadlines

**What OpenPath is:** a voice-first career and scheme guide for rural Tamil Nadu students in Classes 9 to 12.

**The finale:** Team 5fire (VIT Chennai) is a finalist in the Citi India Hackathon 2026, Celebrating Ada Lovelace Day. The finale is in person on Monday 30 Nov 2026 at Citi, DLF IT Park, Porur, Chennai. Each team gets 15 minutes to present, with a mandatory live demo, plus 5 minutes of questions. Citi's technical leadership is on the panel.

**What changes:** in Round 2 the prototype was one offline HTML page with browser speech. For the finale, the panel must see it working for real:

1. An app installed on a real Android phone that works in airplane mode.
2. Real Tamil speech-to-text (Sarvam Saaras v4).
3. Real AI (Sarvam-105B) turning a spoken answer into one of the answer choices, which the student confirms by tapping a picture.
4. A live teacher dashboard on a laptop, fed by our server. The phone queues updates while offline and syncs when it gets signal back.
5. Data points measured on real Tamil recordings.

**Deadlines (IST):**

| When | What |
|---|---|
| Sat 28 Nov, 11 PM | First end-to-end run on a real phone |
| Sun 29 Nov, 2 PM | Feature freeze: bug fixes only after this |
| Sun 29 Nov, 8 PM | Deck, prototype link and demo video sent to Citi |
| Mon 30 Nov, 9:30 AM | Report at Citi. Presentations run 11:00 to 12:40 |

---

## 2. Ground rules (do not break these)

1. **The AI never decides eligibility.**
   - Scheme eligibility comes only from the rules engine (`evaluate()`), which runs on the phone.
   - The language model only maps speech to one of the fixed answer options.
   - In P1, it may also write a one-line explanation from facts we give it.
2. **Gender never affects paths.**
   - `recommend()` must not read the profile.
   - The gender-swap test (1,000 random students, 0 changed) must stay at 0.
   - The speech mapping must never receive the profile.
3. **Sensitive data stays on the phone.**
   - These are stored only in the phone's browser: gender, class, school type, since Class 6, medium, community, family income, first-graduate status, marks band and documents held.
   - The server rejects any sync event with fields outside the allowed list (section 8.8).
4. **Voice is processed, not kept.** Audio sent to `/api/talk` is transcribed in memory and discarded. Never write audio or transcripts to disk or logs on the server. Log only timings, sizes and error codes.
5. **Offline first.**
   - Everything except voice and sync works with no network: Discover by tapping pictures, details, skills, paths, the 4-week plan, scheme eligibility and "Get ready to apply".
   - No external fonts, CDNs, analytics or trackers.
6. **Bilingual.** Every user-facing string is Tamil plus English, using the prototype's `L(ta, en)` helper and `bi()` renderer.
7. **Honest UI.**
   - If the server runs in fake mode, the app shows "(simulated voice)".
   - Copy must never claim something that isn't built.
8. **Secrets.** `SARVAM_API_KEY` and `DEMO_PASSCODE` live only in environment variables: the Render dashboard, or `.env` locally, which is git-ignored.

---

## 3. The product in two minutes (context)

**Persona:** Kavya, 15, in Class 10 at a government school in Ramanathapuram. She keeps her family shop's accounts. The only careers she knows of are teacher and nurse.

**Flow:**
- **Lock:** on a shared family phone, each student has a private picture-PIN profile. Kavya's PIN is sun, leaf, star; Anbu's is fish, moon, flower.
- **Discover:** three questions: work at home, favourite school subject, and how she likes to work. She answers by voice or by tapping a picture.
- **Details:** a few questions about her: class, school type, since Class 6, medium, community, income, first graduate and documents held. These stay on the phone.
- **Skills:** the skills found from her answers.
- **Paths:** 3 best-fit paths plus 1 wildcard, never filtered by gender. Each shows the route, a short story from someone like her, and a place to visit.
- **Plan:** a 4-week plan (lessons, documents, a visit, a decision) that moves missed steps to the next week.
- **Support:** 11 schemes checked by rules on the phone. Each gets one status: yes, likely, later, if (depends on the course), ask, or no. Missing documents are listed, with a "Get ready to apply" checklist. A teacher or e-Sevai operator submits the application on the official portal.
- **Teacher view:** one screen per class showing who chose a path, their progress, and the one blocker the teacher can help with. It never shows community, income or gender.

**Success measure (for context):** the share of students who move on to Class 11, ITI, college or an apprenticeship. The pilot target is 5 percentage points more (8 more for girls), at about ₹5,000 per extra student.

---

## 4. What exists today: the Round 2 prototype

**The file:** `reference/openpath_prototype.html`, about 110 KB in one file with no external resources.

**Layout:** a `<style>` block with design tokens (section 11), then markup with the phone on the left and a panel with three tabs on the right: Teacher view, How it decides, Checks. Below 920 px the panel stacks under the phone.

**Script sections, in order:**

- **Network counter:** wraps `fetch` and `XMLHttpRequest` to count calls in `NET.calls`, to prove the student flow makes 0 network calls.
- **Helpers:**
  - text: `L(ta, en)` returns `{ta, en}`; also `esc()`, `bi()`, `joinL()`, `catL()`
  - icons: `ICON`, `ic()`
  - picture PIN: `PIN_SVG`, `PIN_NAME`, `PIN_CODE`
- **`SKILL`:** 9 skill keys: `numbers, mechanical, electrical, care, people, outdoors, craft, science, computers`.
- **`QUESTIONS`:** 3 questions. Each option is `{id, icon, label, tags: {skill: weight}, kw: [keywords]}`. The option ids are:
  - `home`: `accounts, repair, care, farm, craft`
  - `school`: `maths, science, computer, language, art`
  - `style`: `hands, help, numbers, outside`
- **`PATHS`:** 14 paths.
  - fields: `{id, name, route, after: 10|12, kind: 'iti'|'diploma'|'degree', tech, prof, usual, tags, subject, group, visit, story}`
  - ids: `nursing, labtech, solar, bike, accounts, mobile, agri, garment, teacher, civil, copa, pharma, engineering, graphic`
- **Recommending paths:** `skillsFrom(answers)`, `primaryTag(p)` and `recommend(answers, profile)`, which returns `{picks: [3], wild, skills}`.
  - Score: the dot product of path tags and answer skills.
  - At most 1 "usual" career, a diversity penalty for repeating the same primary tag, and at least one non-degree pick.
  - Wildcard: not a usual career, with a new primary tag.
  - **It takes `profile` only so tests can prove it is ignored. It never reads it.**
- **Scheme helpers:** `INC`, `incomeAtMost`, `schoolOK`, `obcDnt`, `comm`, `needPath`, `C(code, label, fn, extra)`, `STAY`.
- **`SCHEMES`:** 11 schemes with 26 rule checks.
  - ids: `pudhumai, pudhalvan, quota75, firstgrad, csss, pragati, yasasvi_pre, yasasvi_post, sc_pre, sc_post, st_post`
  - fields: `{id, name, by, when: 'entry'|'9-10'|'11+', benefit, checks, docs, source: {label, url}}`
  - Each check function returns `true`, `false`, `null` (we need an answer), `'likely'`, `'future'` (met later if she stays on track) or `'path'` (depends on the course).
- **Evaluating:**
  - `timing(when, cls)`
  - `evaluate(s, p, path)` returns `{s, status, trace, timing, likely, missing}`. `status` is one of `yes, likely, later, if, ask, no`.
  - `evaluateAll(p, path)`
- **Documents and the plan:**
  - `DOCS` (aadhaar, bank, income, community), `BLOCKER`, `relevantMissing(evals)`, `DOC_TASK`
  - `makePlan(path, p, evals)` returns 4 weeks of tasks
  - `nextDecision(path, p)`
- **`CLASSMATES`:** 24 sample rows for class 10-B: `[roll, name, pathId|null, tasksDone (of 8), blockerKey|null]`.
- **State:**
  - `blankProfile()`, `freshState()`, the global `S`, `render()`
  - `KAVYA`'s sample answers: `home: accounts`, `school: science`, `style: help`
  - `KAVYA`'s profile: girl, Class 10, government school since Class 6, Tamil medium, MBC, income ₹1–2.5 lakh, first graduate. Documents: Aadhaar yes, bank no, income no, community yes.
- **Speech:** `speak()` (browser speechSynthesis) and `listen()` (browser SpeechRecognition with keyword matching on `kw`). **Both are replaced in the finale build.**
- **Actions:** `answer()`, `choosePath()`, `reroute()`, and `syncPayload()`, which returns `{student: '10B-07', step, path, plan_done, blocker, synced_at}`.
- **Screens:** `scrLock, scrDiscover, scrDetails, scrSkills, scrPaths, scrPlan, scrSupport`, plus sheets and the bottom nav.
- **Panels:** `panelTeacher` (simulated live row), `panelRules` (rule traces) and `panelChecks`.
- **Checks:**
  - `CASES`: 47 rule tests as `[schemeId, name, profile, pathId|null, expectedStatus]`
  - seeded `rng`, `randomProfile`, `randomAnswers`
  - `runChecks()` sets `window.OPENPATH_CHECKS = {passed, total, genderSwapChanged, genderSwapN, evalMsTotal, evalProfiles, networkCallsInFlow, pageKB, schemes, paths, ruleChecks}`

**Measured on 22 Nov 2026:**
- 47 of 47 rule tests pass.
- 0 of 1,000 gender swaps change the paths.
- 10,000 students × 11 schemes are checked in about 85 ms.
- The student flow makes 0 network calls.

**Round 2 demo path (must still work):**
1. Kavya, PIN sun, leaf, star.
2. Answers: accounts, science, help.
3. Fill Kavya's sample details, confirm the skills, and choose Lab technician.
4. Go offline.
5. Support shows Pudhumai Penn "later" with a missing bank account, and PM YASASVI pre-matric "likely".
6. Get ready to apply.
7. Teacher view, then Checks.

**Checked on 28 Nov 2026 by running the prototype:**
- Kavya's answers give the paths nursing, labtech and accounts, with agri as the wildcard.
- With Lab technician chosen:
  - her plan has 7 tasks
  - the missing documents are bank, then income
  - Pudhumai Penn is "later" and PM YASASVI pre-matric is "likely"

**Where the code lives:** the prototype's script is wrapped in an IIFE (`(function(){ 'use strict'; ... })()`). It exposes only `window.OPENPATH = {S, evaluate, evaluateAll, recommend, SCHEMES, PATHS}` and `window.OPENPATH_CHECKS`.

---

## 5. Scope

### P0: must work on Monday
1. **PWA:** installable on Android Chrome, shows the student app full screen on the phone, and works offline after the first load.
2. **Voice answers:**
   - The app records the answer and sends it to `/api/talk`.
   - Saaras v4 makes a transcript, and Sarvam-105B maps it to one option.
   - The app highlights the suggested picture and the student confirms by tapping.
   - Taps always work, with or without voice.
3. **Fixed Tamil audio:** the questions, prompts, option names and path names are made once with Bulbul and shipped with the app.
4. **Sync:** an offline queue on the phone sends to `/api/sync`; `/api/class` feeds a live teacher dashboard at `/teacher`.
5. **Privacy:** enforced in code and tested.
6. **Eval harness:** run on 40 real Tamil recordings, with the results shown in the Checks tab.
7. **Deployment:** on Render, with the app, teacher page and API on one origin.

### P1: only if P0 is done by Saturday evening
- `/api/explain` and `/api/say`: a one-line Tamil "why this path fits", written only from the path's own facts and read aloud with live Bulbul.
- Compare Saaras `transcribe` and `codemix` modes, and tune `keyterms`, on the eval set.
- Show a rules-pack version and SHA-256 in the Checks tab.

### Out of scope (say so plainly if asked)
- the Flutter app
- DigiLocker
- live job listings
- self-hosted AI4Bharat models
- real student data
- accounts and login
- Postgres

---

## 6. Architecture

```
Android phone (installed PWA, Chrome)               Laptop
+--------------------------------------+           +----------------------+
| index.html + js/engine.js            |           | /teacher page        |
|   rules, paths, plan: all offline    |           | polls GET /api/class |
| js/voice.js  records 16 kHz WAV      |           | every 3 seconds      |
| js/sync.js   queue in localStorage   |           +----------+-----------+
| sw.js        caches app and audio    |                      |
+--------+---------------+-------------+                      |
         | POST /api/talk| POST /api/sync                     |
         v               v                                    v
+----------------------------------------------------------------------+
| FastAPI on Render: one service, one origin, HTTPS                    |
|   /            static student app     /teacher   static dashboard    |
|   /api/talk    audio -> Saaras v4 -> Sarvam-105B -> option suggestion|
|   /api/sync    strict event schema -> in-memory class store          |
|   /api/class   roster + live rows     /api/health   /api/reset       |
|   (P1) /api/explain   /api/say                                       |
+-----------------------------------+----------------------------------+
                                    v
                       Sarvam API (api.sarvam.ai)
           speech-to-text  |  chat completions  |  text-to-speech
```

**Why one origin:** there is no CORS to configure, no mixed-content problem, only one deploy, and opening `/teacher` wakes the free server. This replaces the "GitHub Pages for the app" idea in the team's weekend plan.

**Free Render servers sleep:**
- They sleep after 15 minutes without traffic, and take about a minute to wake.
- During the demo, the teacher page's polling keeps the server awake.
- The in-memory store is wiped when the server restarts, and the roster is re-seeded automatically. Run uvicorn with one worker.

---

## 7. Repository layout and dependencies

```
openpath/
  CLAUDE.md                 this file
  README.md                 short setup and run notes
  .env.example              SARVAM_API_KEY= DEMO_PASSCODE= FAKE_SARVAM=0 ...
  .gitignore                .env .venv/ eval/samples/ __pycache__/ test-results/
  render.yaml
  reference/
    openpath_prototype.html   Round 2 prototype (read-only)
  app/                      served at /
    index.html
    app.css
    manifest.webmanifest
    sw.js
    data/
      questions.json        the 3 questions and their options (single source)
      paths.json            the 14 paths (single source)
      prompts.json          every fixed Tamil line that has audio
      eval_results.json     written by eval/run_eval.py
    js/
      engine.js             rules, recommend, plan (no DOM); loads data/*.json
      strings.js            UI strings built with L(ta, en)
      ui.js                 screens, sheets, render
      voice.js              WAV recorder + /api/talk client
      sync.js               offline queue + /api/sync client
      audio.js              plays the pre-made clips
      checks.js             CASES + runChecks, sets window.OPENPATH_CHECKS
    audio/*.mp3             made by scripts/gen_audio.py
    icons/                  icon-192.png, icon-512.png, maskable-512.png
  teacher/                  served at /teacher
    index.html
    teacher.js
  server/
    main.py                 FastAPI app, routes, static mounts
    config.py               reads env vars
    sarvam.py               HTTP calls to Sarvam with httpx
    talk.py                 STT -> mapping -> validation -> fallback
    prompts.py              LLM prompt and few-shot examples
    schemas.py              Pydantic models (extra="forbid")
    store.py                in-memory class store + seed roster
    requirements.txt
    requirements-dev.txt
    tests/
  scripts/
    gen_audio.py            Bulbul -> app/audio/*.mp3
    gen_icons.py            simple PNG icons with Pillow
  eval/
    manifest.csv            list of recordings (committed)
    samples/                the audio (git-ignored; adults who agreed only)
    run_eval.py
    requirements.txt
    results/
  tests/
    e2e/test_app.py         Playwright for Python
```

**Dependencies:**
- `server/requirements.txt`: `fastapi`, `uvicorn[standard]`, `httpx`, `pydantic>=2`, `python-multipart`
- `server/requirements-dev.txt`: `pytest`, `respx`, `pytest-playwright`
- `eval/requirements.txt`: `jiwer`, `httpx`
- scripts: `Pillow`

Pin exact versions after the first working install (`pip freeze`). No Node toolchain is needed: every test runs with Python.

---

## 8. Component specs

### 8.1 Engine and data
- **Content goes in JSON, rules stay in JavaScript:**
  - `app/data/questions.json` holds `QUESTIONS` exactly as in the prototype, with `L()` objects written as `{"ta": ..., "en": ...}`
  - `app/data/paths.json` holds `PATHS` the same way
  - the server reads the same two files, so there is one source of truth
- **`app/js/engine.js`:**
  - is an ES module with no DOM access
  - exports `loadData()`, which fetches the two JSON files once at start (from the service-worker cache when offline) and builds `PATH`
  - after that, exports everything else from the prototype unchanged in behaviour: `L, SKILL, QUESTIONS, PATHS, PATH, skillsFrom, primaryTag, recommend, SCHEMES, SCHEME, timing, evaluate, evaluateAll, DOCS, BLOCKER, relevantMissing, DOC_TASK, makePlan, nextDecision, CLASSMATES, blankProfile, KAVYA, CHECKED` and the scheme helpers
- **`app/js/checks.js`:**
  - holds `CASES`, `rng`, `randomProfile`, `randomAnswers` and `runChecks()`, and sets `window.OPENPATH_CHECKS`
  - install the network counter before any other script runs
  - count only the calls made during the student-flow check (the data load at start, voice and sync happen outside that window)

### 8.2 Student app (PWA)
- **Layout:**
  - At widths of 920 px and up (laptop), keep the prototype layout: the phone frame on the left; on the right, the tabs How it decides and Checks, plus a link "Open the live teacher dashboard" (`/teacher`). The simulated teacher tab goes away.
  - Below 920 px, and always in `display-mode: standalone`, show only the student app, full screen, with no phone frame. On the phone, Checks is reached from the Settings sheet.
- **Screens and flow:** as in the prototype. Keep "Fill Kavya's sample details" (the demo shortcut) and "Reset demo".
- **Top bar:**
  - online or offline, from `navigator.onLine` plus failed requests
  - the sync state: "2 updates waiting / 2 புதுப்பிப்புகள் காத்திருக்கின்றன" or "Synced 10:52 / ஒத்திசைக்கப்பட்டது 10:52"
- **Settings sheet:**
  - language (Tamil + English, Tamil, English)
  - demo passcode, stored in `localStorage` and sent as the `X-Demo-Passcode` header
  - Reset demo, Checks, and the app version (the service-worker cache version)
- **Manifest:**
  - `name` and `short_name`: `"OpenPath"`
  - `start_url` and `scope`: `"/"`; `display: "standalone"`; `lang: "ta"`
  - `background_color: "#f2f4f2"`, `theme_color: "#1e6b52"`
  - icons at 192 and 512, plus a maskable 512
- **Service worker (`sw.js`):**
  - **Version:** `const CACHE = 'op-v<N>'`. Bump N on every deploy, otherwise phones keep the old version.
  - **On install:** precache `/`, `/index.html`, `/app.css`, every `/js/*.js`, `/manifest.webmanifest`, the icons, `/data/*.json` and every `/audio/*.mp3`.
  - **On fetch:**
    - never intercept `/api/*` or `/teacher*`; they go to the network
    - static files are cache-first, falling back to the network
    - navigations get the cached `/index.html` when offline
  - **On activate:** delete old caches, then `clients.claim()`.
- **Persistence:** keep each student's state (the prototype's `S`, minus transient UI fields) in `localStorage` under `op.state.<roll>`, so a reload keeps her progress. The picture PIN gates each profile.

### 8.3 Voice capture (`app/js/voice.js`)
- **Button:** a large "பேசு / Speak" button under the question, with the picture options below it as now.
- **Offline:** the button is disabled with the message "குரலுக்கு இணையம் தேவை. படத்தைத் தொடு. / Voice needs a signal. Tap a picture."
- **Recording:**
  - capture with `getUserMedia({audio: {channelCount: 1, echoCancellation: true, noiseSuppression: true}})`
  - feed it into `new AudioContext({sampleRate: 16000})` through an `AudioWorklet`, with `ScriptProcessorNode` as the fallback
  - collect Float32 samples, convert them to 16-bit PCM, and write a 44-byte RIFF/WAV header (mono, 16 kHz)
- **Controls:** tap to start and tap to stop, with a timer showing. Recording stops by itself at 20 s, and anything shorter than 0.8 s is ignored.
- **Upload:** POST `multipart/form-data` to `/api/talk` with `audio` (the WAV) and `question_id`, plus the `X-Demo-Passcode` header. Time out after 15 s with an AbortController.
- **States:** idle → recording → "புரிந்துகொள்கிறேன்… / Understanding…" → result.
- **Result:**
  - show the transcript in quotes
  - if there is a `suggestion` with confidence 0.5 or higher, highlight that option card and play the `confirm` clip: "சரியா? படத்தைத் தொட்டு உறுதி செய். / Is this right? Tap the picture to confirm."
  - the student taps the highlighted picture, or a different one, to answer
  - if there is no suggestion, show and play "புரியவில்லை. அருகிலுள்ள படத்தைத் தொடு. / I didn't catch that. Tap the closest picture."
  - **never record an answer without a tap**
- **Errors:**
  - network failures and 5xx: a toast, then taps as usual
  - 401: "Enter the demo passcode in Settings"
  - microphone permission denied: explain it and fall back to taps

### 8.4 Server API (`server/`)
All responses are UTF-8 JSON, and every route is under `/api`.

**`GET /api/health`**
```json
{"ok": true, "version": "2026-11-28", "fake": false,
 "models": {"stt": "saaras:v4", "llm": "sarvam-105b", "tts": "bulbul:v4-flash"}}
```

**`POST /api/talk`** (multipart, with the `X-Demo-Passcode` header)
- **Fields:** `audio` (WAV, at most 1.5 MB and 25 s) and `question_id` (`home`, `school` or `style`). Nothing else is accepted.
- **200 response:**
```json
{
  "transcript": "நான் எங்க கடையில கணக்கு எழுதுவேன்",
  "language_code": "ta-IN",
  "suggestion": {"option_id": "accounts", "confidence": 0.86, "evidence": "கடையில கணக்கு", "source": "llm"},
  "timings_ms": {"stt": 1400, "llm": 2100, "total": 3600},
  "models": {"stt": "saaras:v4", "llm": "sarvam-105b"},
  "fake": false
}
```
- **`suggestion`:** `null` when nothing fits. Its `source` is `llm`, or `keywords` when the fallback was used.
- **Errors:**
  - 401: wrong passcode
  - 413: too long or too large
  - 422: bad input
  - 429: rate limit
  - 502 `{"error": "stt_failed", "fallback": "tap"}`: Sarvam failed
- **Rate limit:** in memory, 20 requests per minute per IP.

**`POST /api/sync`** and **`GET /api/class`:** see section 8.8.

**`POST /api/reset`** (passcode): clears the live rows and re-seeds the roster.

**Fake mode:**
- When `FAKE_SARVAM=1`, `/api/talk` skips Sarvam and returns Kavya's canned transcript and suggestion for each question, with `"fake": true`.
- Use it for tests, for rehearsals that shouldn't spend credit, and as a last resort.
- The app shows "(simulated voice)" whenever a response has `fake: true`.

**Config (environment variables):**

| Variable | Value |
|---|---|
| `SARVAM_API_KEY` | secret |
| `DEMO_PASSCODE` | secret |
| `FAKE_SARVAM` | `0` or `1` |
| `STT_MODEL` | `saaras:v4` |
| `STT_MODE` | `transcribe` |
| `LLM_MODEL` | `sarvam-105b` |
| `TTS_MODEL` | `bulbul:v4-flash` |
| `TTS_SPEAKER` | chosen by the team |
| `LOG_LEVEL` | `info` |

### 8.5 Sarvam API (checked against docs.sarvam.ai on 28 Nov 2026)
- **Client:** call the REST endpoints with plain HTTP using `httpx` (async). Don't rely on the `sarvamai` SDK's defaults: its PyPI page still shows older defaults (saarika, bulbul:v1, sarvam-m).
- **Every call:** send the header `api-subscription-key: <SARVAM_API_KEY>`.
- **Timeouts:** STT 10 s, chat 12 s, TTS 10 s. Retry once on 429 or 503, after 500 ms.

**Speech to text:** `POST https://api.sarvam.ai/speech-to-text`, multipart:
- `file`: the WAV
- `model`: `saaras:v4`
- `mode`: `transcribe` (in P1, compare `codemix` for Tamil-English mixing)
- `language_code`: `ta-IN` (or `unknown` to auto-detect)
- `keyterms` (optional, saaras:v4 only): a JSON-encoded array of up to 50 terms, each at most 64 characters, for example `["கணக்கு","அறிவியல்","கணினி","ITI","DMLT"]`
- Response: `{"request_id", "transcript", "language_code", ...}`
- This REST endpoint is for audio under 30 seconds. It accepts WAV, MP3, AAC, OGG, OPUS, FLAC, M4A, WebM and more, and works best at 16 kHz.

**Chat completions:** `POST https://api.sarvam.ai/v1/chat/completions` (OpenAI-compatible shape):
```json
{
  "model": "sarvam-105b",
  "messages": [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}],
  "temperature": 0.2,
  "max_tokens": 300,
  "response_format": {"type": "json_object"},
  "reasoning_effort": null
}
```
- **Reasoning:** Sarvam-105B has reasoning on by default, and reasoning tokens count toward `max_tokens`. The docs say to turn it off by setting `reasoning_effort` to None.
- **Check the first real call:** it should be quick and return only the JSON. If the API rejects `response_format` or `reasoning_effort`, drop that field and rely on the prompt and the parser.
- **Don't use Sarvam-M:** it is deprecated and no longer available on the API.

**Text to speech:** `POST https://api.sarvam.ai/text-to-speech`, JSON:
```json
{"text": "...", "language_code": "ta-IN", "model": "bulbul:v4-flash", "speaker": "<TTS_SPEAKER>",
 "pace": 0.95, "speech_sample_rate": 24000, "output_audio_codec": "mp3"}
```
- **Response:** `{"request_id", "audios": ["<base64>"]}`.
- **Limits:** at most 2,500 characters per request.
- **Model:** if `model` is left out, the API uses `bulbul:v3`. v3 speaker names and v4-flash persona IDs are different, so don't mix them.
- **Speaker:** v4-flash persona IDs follow the pattern `name_language_style` (for example `simran_en_customer`). The team picks a Tamil persona by listening on the Voices page and puts its ID in `TTS_SPEAKER`.

**Prices** (before GST, from Sarvam's pricing page on 27 Nov 2026):
- speech-to-text: ₹0.49 per minute
- Bulbul v4 Flash: ₹2 per 1,000 characters
- Sarvam-105B: ₹10 per million input tokens and ₹25 per million output tokens
- ₹100 free credit on sign-up

### 8.6 Mapping speech to an answer (`server/talk.py`, `server/prompts.py`)
**What the model gets:** the question (Tamil and English), its options (id, Tamil label, English label and keyword hints, read from `app/data/questions.json`) and the transcript. Nothing else: no profile and no name.

**System prompt:**
```
You help a Tamil-speaking school student answer a question by voice.
Given the question, its options and what the student said, choose the ONE option that best matches.
Rules:
- Reply with JSON only: {"option_id": <one of the given ids, or null>, "confidence": <0 to 1>, "evidence": <a short quote from what they said>}
- If nothing matches, use null. Do not guess.
- The student may mix Tamil and English, and spelling may be informal.
- Do not mention or infer gender, caste, religion, income or anything personal. Do not give advice.
```

**User message:**
```
Question: <ta> / <en>
Options:
- accounts: கணக்கு எழுதுவது / Writing the accounts (hints: கணக்கு, பணம், கடை, account, money, shop)
- repair: ...
Student said: "<transcript>"
```

**Few-shot examples** (send them as earlier user and assistant turns):

| Question | Student said | Answer |
|---|---|---|
| home | நான் எங்க கடையில கணக்கு எழுதுவேன் | `{"option_id":"accounts","confidence":0.9,"evidence":"கடையில கணக்கு"}` |
| home | நான் பைக் ரிப்பேர் பண்ணுவேன் | `repair` |
| home | தங்கச்சிய பாத்துக்குவேன் | `care` |
| school | கம்ப்யூட்டர் கிளாஸ் ரொம்ப பிடிக்கும் | `computer` |
| style | மத்தவங்களுக்கு உதவி செய்யப் பிடிக்கும் | `help` |
| any | தெரியல | `{"option_id":null,"confidence":0,"evidence":""}` |

**Validation:**
1. Parse the JSON, stripping code fences if there are any.
2. `option_id` must be one of the question's ids, or null. Anything else is invalid.
3. Clamp `confidence` to the range 0 to 1.
4. **If the reply is invalid or the call fails, use the keyword fallback:**
   - normalise the transcript: Unicode NFC, lower case, no punctuation
   - match it against each option's `kw` list, as the prototype's `listen()` did
   - one match: `source: "keywords"` with confidence 0.6
   - no match, or more than one: `suggestion: null`
5. Return `suggestion` even at low confidence; the app highlights only at 0.5 and above.

### 8.7 Fixed audio (`scripts/gen_audio.py`)
- **`app/data/prompts.json`:** `{"key": {"ta": "...", "en": "..."}}`. It covers:
  - the greeting and the 3 questions
  - `confirm`, `not_caught`, `voice_offline`, `heard_prefix` ("நீ சொன்னது:"), `plan_ready`, `support_intro`
  - each option label (14) and each path name (14)
  - build the option and path entries from `questions.json` and `paths.json`
- **The script:**
  - calls Bulbul for every Tamil line and writes `app/audio/<key>.mp3`
  - skips files that already exist unless given `--force`
  - prints the characters used and the estimated cost at ₹2 per 1,000 characters
- **Size:** about 40 clips. Commit them.
- **Playback:** one `<audio>` element plays the clips, always after a user tap.

### 8.8 Sync and the teacher dashboard
**An event, from phone to server** (built from the prototype's `syncPayload()`):
```json
{"event_id": "a4f1c2e0-...", "student": "10B-07", "ts": "2026-11-30T11:12:00Z",
 "step": "plan", "path": "labtech", "plan_done": "1/7", "blocker": "bank_account_aadhaar"}
```

**Allowed values:**

| Field | Allowed |
|---|---|
| `step` | `discover`, `paths` or `plan` |
| `path` | a path id, or null |
| `plan_done` | matches `^\d{1,2}/\d{1,2}$`, or null |
| `blocker` | `no_path_yet`, `bank_account_aadhaar`, `income_certificate`, `community_certificate`, `aadhaar`, or null |
| `student` | matches `^10B-\d{2}$` |

**Validation:** a Pydantic model with `extra="forbid"`. Any other key (`community`, `income`, `gender`, `name`, `answers`, ...) gets a 422. The phone never sends the student's name; the server looks it up from the roll number in its roster.

**`POST /api/sync`:**
- body: `{"events": [...]}`, up to 50 events
- returns `{"accepted": [ids], "duplicates": [ids]}`
- idempotent by `event_id`; for each student, the event with the latest `ts` wins

**The queue (`app/js/sync.js`):**
- **What to queue:** after every state change that changes the payload, add a snapshot event. That means answers completed, a path chosen, a task ticked, a re-route, or details and documents changed. Skip it if it is identical to the last one queued.
- **Where:** `localStorage`, key `op.queue`.
- **When to send:** at start, on the `online` event, and every 15 s while online. Remove the accepted and duplicate ids.
- **Display:** the top-bar sync state described in section 8.2.

**`GET /api/class`:**
```json
{
  "class_id": "10B",
  "school": "Government Higher Secondary School (sample)",
  "updated_at": "2026-11-30T11:12:03Z",
  "students": [
    {"roll": "10B-07", "name": "Kavya S", "path": "labtech",
     "path_name": {"ta": "ஆய்வக தொழில்நுட்பர்", "en": "Lab technician"},
     "plan_done": "1/7", "blocker": "bank_account_aadhaar", "live": true,
     "last_event_at": "2026-11-30T11:12:00Z"}
  ],
  "last_event": {"...": "the last raw event received"}
}
```

**Seed roster:**
- the 24 `CLASSMATES` rows: write tasks done as `"n/8"`, and convert the blocker keys
  - `bank` → `bank_account_aadhaar`
  - `income` → `income_certificate`
  - `community` → `community_certificate`
  - `aadhaar` → `aadhaar`
  - `nopath` → `no_path_yet`
- plus `10B-07 Kavya S`: live, no path yet, blocker `no_path_yet`
- 25 students in all, kept in memory

**The teacher page (`/teacher`):**
- **Header:** "Class 10-B", with summary figures:
  - how many chose a path (n of 25)
  - how many finished the plan
  - how many need help, by blocker type (for example "4 need a bank account")
- **Table:** Student, Path, Progress, Blocker, Updated.
  - The live row is marked "(live)".
  - When the live row changes, its background changes briefly. No other animation.
- **Privacy panels:**
  - "What the phone sent": a `<details>` showing `last_event` as JSON
  - "What never leaves the phone": community, family income, gender, documents held, her answers, and her voice recording
- **Polling:** asks `/api/class` every 3 s. Shows "Updated 10:52:31", and a notice if a poll fails.
- **Reset demo:** asks for the passcode once and stores it in `localStorage`.
- **Language:** English, with Tamil labels where useful.

### 8.9 Privacy in code (each with a test)
- **Sync:** `/api/sync` rejects extra fields with a 422. Test with `community`, `income`, `gender` and `name`.
- **Talk:** `/api/talk` takes only `audio` and `question_id`. Test that an extra `profile` field is rejected and never reaches the LLM call, by checking the mocked request body.
- **Logs:** no audio or transcript is written to disk or logs. Test by capturing logs during a `/api/talk` call and checking the transcript text is absent.
- **Phone payload:** the phone's sync request never includes profile fields. The e2e test inspects the request body.
- **UI copy:** update "What never leaves the phone" to add: "Her voice answer is sent only to be turned into text, and is not stored." The Round 2 copy said her answers never leave the phone, which is no longer exactly true.

### 8.10 Checks tab
- **Keep the prototype's live checks:**
  - 47 rule tests
  - the gender swap
  - the 10,000-student timing
  - 0 network calls in the student flow
  - size: change "page size" to app size, the total precached bytes
- **Add "Measured on real Tamil speech"**, read from `app/data/eval_results.json`: the date, number of recordings and speakers (adults), character error rate, answers mapped correctly, median and 90th-percentile response time, and estimated cost per conversation.
- **If the file is missing:** show "Not measured yet".

### 8.11 Eval harness (`eval/`)
- **`manifest.csv`:** the columns are `file, speaker_id, condition (quiet|noisy), question_id, reference_text, expected_option_id`.
  - The audio goes in `eval/samples/`, which is git-ignored.
  - Record only adults who agreed.
- **Converting phone recordings:** if needed, `ffmpeg -i in.m4a -ac 1 -ar 16000 out.wav`.
- **`run_eval.py --base-url http://localhost:8000 --passcode ...`:** posts each file to `/api/talk` (the full pipeline), and records the transcript, suggestion and timings.
- **Metrics:**
  - character error rate with `jiwer.cer`, after normalising both texts (Unicode NFC, no punctuation, single spaces)
  - option accuracy: `suggestion.option_id == expected_option_id`, counting null as wrong
  - the share of answers with no suggestion
  - p50 and p90 latency for `total`, `stt` and `llm`
  - estimated cost per conversation of 3 answers: audio minutes × ₹0.49, plus tokens × price when the server returns usage. Return `usage` only when the request has `X-Debug: 1` and the right passcode.
- **Outputs:**
  - `eval/results/<timestamp>.json`
  - a Markdown table ready for the slide
  - a copy at `app/data/eval_results.json`
  - all of them say "speakers were adults"

---

## 9. Tests that must pass before Sunday 2 PM

**`pytest server/tests`** (Sarvam mocked with respx):
- talk pipeline:
  - good JSON
  - JSON inside code fences
  - unknown option id
  - LLM timeout → keyword fallback
  - STT failure → 502 with `fallback: "tap"`
- passcode, size limit, rate limit
- sync validation: extra fields, bad enums, duplicates, ordering by `ts`
- the roster seed, and reset

**`pytest tests/e2e`** (Playwright for Python, Chromium, server in fake mode):
- **Checks:** the app loads; `window.OPENPATH_CHECKS` shows `passed == total == 47`, `genderSwapChanged == 0` and `networkCallsInFlow == 0`.
- **Offline:**
  - the service worker installs
  - after `context.set_offline(True)`, a reload still works
  - with Kavya's sample details and Lab technician, Support shows Pudhumai Penn "later" with the bank account missing
- **Queue and sync:**
  - while offline, ticking a task raises the queue count
  - after `context.set_offline(False)`, the queue empties and `/api/class` shows `1/7` for 10B-07
  - the sync request body contains only the allowed keys
- **Voice, in fake mode:**
  - launch Chromium with `--use-fake-ui-for-media-stream`, `--use-fake-device-for-media-stream` and `--use-file-for-fake-audio-capture=<tests/e2e/kavya_home.wav>`
  - press Speak, then Stop
  - the suggestion is highlighted; a tap confirms it; the answer is saved
- **Screenshots:** at 390×844 and 1280×800, into `test-results/`, for a human to look at.

**By hand on a real phone (Saturday's 8 PM run):** install the app, turn on airplane mode, use real voice, and watch the teacher laptop update.

---

## 10. Deployment

**Render:** one web service on the free plan, defined in `render.yaml`:
```yaml
services:
  - type: web
    name: openpath
    runtime: python
    plan: free
    buildCommand: pip install -r server/requirements.txt
    startCommand: uvicorn server.main:app --host 0.0.0.0 --port $PORT --workers 1
    healthCheckPath: /api/health
    envVars:
      - key: PYTHON_VERSION      # confirm the name and format in Render's Python docs
        value: 3.12.7
      - key: SARVAM_API_KEY
        sync: false
      - key: DEMO_PASSCODE
        sync: false
      - key: TTS_SPEAKER
        sync: false
      - key: FAKE_SARVAM
        value: "0"
      - key: STT_MODEL
        value: saaras:v4
      - key: LLM_MODEL
        value: sarvam-105b
      - key: TTS_MODEL
        value: bulbul:v4-flash
```

**Secrets:** Render asks for the `sync: false` values only when the Blueprint is first created. If the service already exists, add them in the dashboard.

**After every deploy:**
1. Bump `CACHE` in `sw.js`.
2. Open `/api/health`.
3. On the phone, open the app twice: the new service worker takes over on the second open. If it still shows the old version, clear the site data.

**Running locally:**
```
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r server/requirements.txt -r server/requirements-dev.txt
playwright install chromium
uvicorn server.main:app --reload --port 8000
```
Open `http://localhost:8000`; the microphone works on localhost.

**Testing on a phone before deploying:** an HTTPS tunnel such as `cloudflared tunnel --url http://localhost:8000` gives a temporary https address the phone can open.

**Demo day:** mirror the phone to the laptop with `scrcpy` over USB (turn on USB debugging first).

---

## 11. Design rules (UI)
Keep the prototype's flat look.

**Tokens:**
```
--bg #f2f4f2   --surface #ffffff   --ink #1f2421   --muted #56605b   --line #c9d0cb   --tint #eef2ef
--green #1e6b52   --on-green #ffffff   --green-tint #ddebe4   --ochre #94580b   --ochre-tint #f8ebd6   --no #7f8682
font: "Noto Sans Tamil", "Nirmala UI", "Latha", "Segoe UI", system-ui, Roboto, Arial, sans-serif
```
The prototype also has dark-mode tokens; keep them.

**Rules:**
- **Type:** readable, with normal letter spacing. No decorative serif, no italics, and monospace only for codes and JSON.
- **No decoration:** no pills, badges, eyebrow headings, all-caps labels or decorative numbering. Use plain words for status, such as "Likely now" or "(live)".
- **Surfaces:**
  - flat fills on `--tint`
  - borders only where they mark a control or a table cell
  - never a one-sided border with rounded corners
  - no gradients, decorative shadows or layered opacity
- **Actions:** one clear primary action per screen, and touch targets of at least 44 px.
- **Copy:** short. Don't repeat what the layout already shows.
- **Check every screen** at 390×844 and 1280×800 before calling it done.

---

## 12. Build order

| Phase | What | Done when |
|---|---|---|
| 0 | Repo scaffold. Port the prototype into `app/` (engine.js, data JSON, ui.js, checks.js). FastAPI serves `/` | The app works locally as before; e2e checks show 47/47 and 0 gender changes |
| 1 | PWA: manifest, icons, service worker | It installs, and a reload works offline (e2e offline test) |
| 2 | `/api/talk` with Sarvam and fake mode, validation and fallbacks; pytest | A real Tamil WAV returns the right option; tests are green |
| 3 | Voice UI: WAV recorder, upload, confirm UI. `gen_audio.py` and playback | On a laptop: speak → suggestion → tap confirms; the clips play |
| 4 | Sync queue, `/api/sync`, `/api/class`, `/teacher`, reset; privacy tests | Offline → queue → online → the teacher row updates; privacy tests are green |
| 5 | Eval harness; results in Checks | `eval_results.json` from at least 40 recordings shows in Checks |
| 6 | Deploy to Render; a run on a real phone | Install from the Render address; the full demo flow works on the phone |
| 7 (P1) | `/api/explain` and `/api/say`; codemix vs transcribe; rules-pack hash | Only after phases 0 to 6 are done |

---

## 13. Acceptance test: the Monday demo (about 5 minutes)
1. The phone is mirrored on the big screen, and the teacher dashboard is open on the laptop.
2. Kavya opens the installed app with her picture PIN: sun, leaf, star.
3. A team member speaks Kavya's three answers in Tamil:
   - "நான் எங்க கடையில கணக்கு எழுதுவேன்"
   - "எனக்கு அறிவியல் ரொம்ப பிடிக்கும்"
   - "மத்தவங்களுக்கு உதவி செய்யப் பிடிக்கும்"

   Each time, the transcript appears, the right picture is highlighted, the app asks in Tamil if it's right, and a tap confirms.
4. Fill Kavya's sample details. She sees her skills, then three paths and a wildcard. She chooses Lab technician, and the plan appears.
5. **Airplane mode goes on.**
   - Support shows Pudhumai Penn "later", with "Missing: Bank account linked to Aadhaar".
   - PM YASASVI pre-matric shows "likely". She opens "Get ready to apply".
   - She ticks a task, and the app shows "2 updates waiting".
6. **Airplane mode goes off.** The app shows "Synced". The laptop shows Kavya's row (Lab technician, 1/7, blocker: bank account) and the raw event, with no caste or income in it.
7. **Checks:** 47/47, 0 of 1,000, the timing, and the measured speech numbers.

If voice fails, tap the pictures and say: "Voice needs a signal; tapping always works."

---

## 14. Team and ownership

| Person | Role | Owns |
|---|---|---|
| Madhav K | Team lead, architecture and AI | the server, `/api/talk`, prompts, deployment |
| Rohit A S | Prototype, rules engine and demo | the PWA, voice UI, sync queue and teacher page; drives the demo |
| Nischay Kuchibhotla | Tamil speech and AI | recordings, `gen_audio.py`, the eval harness, choosing the voice |
| Joshnavi Pokala | Research, schemes and data | checking the rules against the government orders, sources, test cases |
| Jeevika Iniyarajan | Product, user flow and impact | the demo script, deck, copy review and privacy check |

---

## 15. Copy and honesty changes
- **Speech wording:** replace every mention of IndicConformer, Indic Parler-TTS or browser speech in the app with what is real now: Saaras v4 (speech to text), Sarvam-105B (understanding) and Bulbul v4 Flash (voice).
- **"How it decides":** keep the line "The language model never decides who is eligible."
- **"What never leaves the phone":** update it as described in section 8.9.
- **Checks:** show the measured numbers with their date, and say the speakers were adults.
- **Deck (not code):**
  - the architecture slide should name Sarvam-105B, Saaras v4 and Bulbul v4 Flash
  - for the phone, say "installable web app now, Flutter for the pilot"

---

## 16. Reference

**Docs:**
- [Sarvam pricing](https://docs.sarvam.ai/api/getting-started/pricing)
- [Saaras v4](https://docs.sarvam.ai/api/api-guides-tutorials/models/saaras)
- [Speech-to-text REST reference](https://docs.sarvam.ai/api-reference/speech-to-text/transcribe)
- [Bulbul](https://docs.sarvam.ai/api/api-guides-tutorials/models/bulbul)
- [Text-to-speech REST reference](https://docs.sarvam.ai/api-reference/text-to-speech/convert)
- [Voices](https://docs.sarvam.ai/api/api-guides-tutorials/text-to-speech/voices)
- [Chat completions](https://docs.sarvam.ai/api/token-factory/chat-completions)
- [Sarvam-105B](https://docs.sarvam.ai/api/token-factory/models/sarvam-105b)
- [Render free plan](https://render.com/docs/free)
- [Render Blueprint spec](https://render.com/docs/blueprint-spec)

**Scheme sources:** each `SCHEMES[].source` in the prototype has its source. The Pudhumai Penn and Tamil Pudhalvan conditions are encoded as reported in the news; Joshnavi is checking them against the government orders.

**Glossary:**
- **ITI:** Industrial Training Institute
- **DMLT:** Diploma in Medical Laboratory Technology
- **COPA:** Computer Operator and Programming Assistant
- **e-Sevai:** Tamil Nadu government service centres
- **DIKSHA:** India's national school learning platform
- **G.O.:** Government Order
- **DPDP Act:** India's Digital Personal Data Protection Act, 2023
