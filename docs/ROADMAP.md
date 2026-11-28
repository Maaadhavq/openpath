# OpenPath roadmap

**The idea in one line:** every rural Tamil Nadu student in Classes 9 to 12 gets a career and scheme guide that speaks Tamil, works without a signal and keeps her details on her own phone. Her class teacher gets a workspace that turns "who is stuck" into "what I do this week".

**The success measure:** the share of students who move on to Class 11, ITI, college or an apprenticeship. The pilot target is 5 percentage points more, and 8 more for girls, at about ₹5,000 per extra student.

## The rule everything follows

| Tier | What | Who sees it |
|---|---|---|
| Never leaves the phone | gender, community, income, documents held, marks, answers, voice, scheme eligibility | the student only |
| Shared with the class teacher | roll number, first name (new students), path, plan progress (overall and per week), kind of next step, one blocker, last use | her class teacher |
| Aggregates only | counts by path, blocker and status; never a group smaller than 10 | headmaster, block and district (Horizon 3) |

The AI never decides eligibility. Tested rules on the phone do. The AI turns speech into an answer option, and answers a teacher's questions from shared data, with roll numbers in place of names.

## Horizon 1: the finale (built, 28–29 Nov 2026)

| Feature | What it does | Privacy guard |
|---|---|---|
| Installable phone app | Rules, 14 paths and the 4-week plan work in airplane mode | No server needed for eligibility |
| Tamil voice answers | Saaras v4 transcribes; Sarvam-105B picks a picture; she confirms by tapping | Voice is processed in memory, never stored |
| Offline sync | Progress queues offline and syncs seconds after the signal returns | The server rejects any field outside the shared list |
| New students | Roll number, optional first name, picture PIN, on a shared family phone | The PIN protects each profile on the phone |
| Teacher workspace | Overview, Students with a detail drawer, Actions with parent messages and print views | A class code; only the shared tier appears |
| Ask OpenPath | "Who needs help this week?", "How do they get an income certificate?", "Explain Pudhumai Penn" | Rules answer most questions without AI; Sarvam gets roll numbers, not names |
| Live checks | 47 rule tests, a gender-swap test, 0 network calls in the student flow | The tests run on every phone, every time the app opens |

## Horizon 2: the pilot (10 schools in Ramanathapuram, Jan–Jun 2027)

| Feature | Why it matters | Privacy guard | Moves |
|---|---|---|---|
| **Teacher ↔ student loop:** a student taps "Ask my teacher for help"; the teacher posts a note to a blocker group ("Bank day at the post office, Wednesday 10 AM") that shows on those phones | Turns a dashboard into action, and the student sees that someone acted | Notes go to roll numbers in her class only | Blockers cleared per week |
| **Document camps:** one tap books an IPPB post-office day or an e-Sevai certificate drive for a blocker group, with a list for the operator | Bank accounts and certificates are the most common blockers in the sample class | The operator's list shows names and the document needed, nothing else | Days from blocker to cleared |
| **Parent voice notes in Tamil (WhatsApp, with consent):** the Actions parent message, read by Bulbul | Parents make the decision on Class 11 group and ITI | Opt-in per parent; no profile data in messages | Parent follow-through |
| **Real accounts and storage:** Postgres, teacher sign-in by school (UDISE) code, several classes per teacher | Survives restarts; one teacher, three sections | Shared tier only; data in Indian regions | Teachers active weekly |
| **Headmaster weekly report:** a one-page PDF per class | The headmaster can unblock camps and visits | Counts plus the teacher's action list | Visits held |
| **DIKSHA deep links and recorded alumni stories:** real voices from the same district for each path | Role models are the strongest pull to an unfamiliar career | Alumni consent, recorded by the school | Students who finish week 1 |
| **Outcome tracking:** after the results, the student records where she went: Class 11 group, ITI, polytechnic or apprenticeship | This is the success measure | Self-reported on the phone; only the outcome type is shared | Transition rate, by school |
| **Offline teacher app:** the workspace cached for a teacher with poor signal | Rural schools lose signal too | Same class code | Teacher sessions per week |

## Horizon 3: state scale (2027–28)

| Feature | Why it matters | Privacy guard |
|---|---|---|
| **District dashboards:** transition rates, blockers and path mix by block and school | Lets the department place camps, counsellors and ITI seats where they are needed | Aggregates only, never a group smaller than 10, no names |
| **Signed scheme-rules pack:** each rule with its G.O. link and check date, maintained with the department and pushed to phones as a versioned, signed update | Rules change every year; one source for every phone | The rules run on the phone; the pack contains no student data |
| **Self-hosted Tamil models:** on-device or state-hosted AI4Bharat speech and language models in place of a hosted API | The state owns the pipeline, and voice works without a signal | Voice never leaves the phone or the state's own cloud |
| **DigiLocker document check, with consent:** "you already have an income certificate" | Fewer wasted trips to the taluk office | Consent each time; the result stays on the phone |
| **Seats and apprenticeships:** NAPS apprenticeships and ITI seat availability near her block | From "a path that fits" to "a place I can apply to" | Public data in; nothing about her goes out |
| **Flutter app on low-end Android:** the same engine, packaged for 1 GB phones and shared family use | Reaches students without Chrome or with older phones | Same three tiers |

## What it costs (Horizon 1 prices, before GST)

- **Voice:** about ₹1 per Discover conversation (three 10-second answers through Saaras v4 and Sarvam-105B). Use the measured figure from `eval/run_eval.py` on the slide.
- **Ask OpenPath:** about ₹0.03 per free-text question (around 3,000 tokens). Rule answers cost nothing.
- **Hosting:** ₹0 on Render's free plan for the demo. A pilot server and database cost a few thousand rupees a month.
- **The rules, paths, plan and checks run on the phone,** so cost does not grow with the number of eligibility checks.

## Risks we name ourselves

- Test voices are adults; testing with teenagers is part of the pilot.
- Scheme rules come from news reports for two schemes; they are being checked against the government orders.
- The class list resets when the free server restarts; Horizon 2 adds storage.
- A shared family phone is protected by a picture PIN, which is a soft lock, not strong security.
