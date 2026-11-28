# OpenPath stress test

Run on Saturday 28 Nov 2026 against the build that goes to the finale. Re-run any time with `python scripts/stress_test.py` (load and integrity), `pytest server/tests/test_stress.py` and `pytest tests/e2e/test_stress.py` (edge cases).

## 1. Load and integrity

One server process (uvicorn, one worker), fake voice mode, on a laptop. Simulated phones use roll numbers 26 to 99 and send events one request at a time, like the real queue; about 15% are resent (duplicates) and about 10% arrive out of order.

| Scenario | Sync requests | Sync time p50 / p95 / p99 | Teacher page p50 / p95 | Ask p50 / p95 | Errors | Rows wrong |
|---|---|---|---|---|---|---|
| A real class: 40 phones tapping about once a second, 3 teacher pages polling every 3 s | 600 | 13 / 80 / 144 ms | 38 / 66 ms | 14 / 56 ms | 0 | 0 of 65 |
| Worst-case burst: 74 phones sending 40 events each with no pause, 5 teacher pages polling every 0.5 s | 2,960 (161 a second) | 300 / 1,269 / 1,925 ms | 294 / 1,116 ms | 338 / 759 ms | 0 | 0 of 99 |

- **Integrity:** in both runs every student's row on the server matched the latest event her phone sent, despite resends and late deliveries.
- **Where the time goes:** building the whole class view for 99 students takes 0.4 ms, and applying one sync event 0.015 ms. The burst latency is one Python worker juggling about 200 open connections on the same laptop as the load generator, not the app's own logic.
- **Live server:** Render's free plan has a fraction of one CPU. A health check from Chennai answered in 0.12 s. A demo with one or two phones is far below these loads. For a pilot, a paid instance or a second worker would be the first step.

## 2. Edge cases

| Case | Result | Proof |
|---|---|---|
| The signal drops and returns six times while she ticks and unticks steps | Server and phone agree; queue empty | `tests/e2e/test_stress.py` |
| A week offline: 120 queued updates | Sent in batches of at most 50 when the signal returns | `tests/e2e/test_stress.py` |
| A full class of 99 on the teacher page | Renders, filters and searches | `tests/e2e/test_stress.py` |
| A name built to inject a script | Markup refused (422); quotes shown as plain text; no script runs | `test_stress.py` (both) |
| The same update sent 100 times | Stored once; 99 reported as duplicates | `server/tests/test_stress.py` |
| A phone clock behind | Its own updates still apply in order | `server/tests/test_stress.py` |
| Memory over hours of use | Bounded: 50 history items per student, 30 feed items, 20,000 remembered event ids | `server/tests/test_stress.py` |
| Ask with a student's name | Sarvam gets roll numbers only; no profile words in the class data | `server/tests/test_teacher.py` |

## 3. Found and fixed tonight

| # | What broke | Why it matters | Fix |
|---|---|---|---|
| 1 | A phone with its clock set years ahead froze that student's row: every later update looked "older" | Cheap phones often have wrong clocks after a battery change | If a phone's time is more than 2 minutes ahead, the server uses its own time |
| 2 | No limit on how often one address could sync | One script could flood the class list | 600 syncs a minute per address; the phone keeps its updates and retries |
| 3 | Ask answered "Which boys need help?" with the full help list, as if it had filtered by gender | It looks like OpenPath knows gender. It doesn't, but the answer misled | Ask refuses to list or count students by caste, community, religion, income or gender, and says why; nearby honest questions still work |
| 4 | The teacher page said "not active" for students working offline | Offline use is the point of the app | Now "No update for 7+ days", and Ask adds "they may be working offline" |
| 5 | A picture PIN has 216 combinations and no limit on guesses | A sibling could open her profile | After 5 wrong tries, the phone waits 30 seconds |

## 4. Known and not fixed before the freeze (pilot work)

| Risk | Today | Pilot fix |
|---|---|---|
| Anyone with the link can post progress for any roll number | Sync takes no login, by design for the demo | The teacher enrolls each phone with a QR code that ties a roll number to that phone |
| Two phones choosing the same new roll number overwrite each other | Possible | The same QR enrollment |
| A typo in a roll number makes a stray row the student can't change | Possible | QR enrollment; the teacher can merge or remove a row |
| Without a separate `TEACHER_CODE`, the demo passcode students type for voice also opens the teacher page | Fine for the demo team | Set `TEACHER_CODE` for any real class |
| The class list lives in memory | A deploy or restart clears it | Postgres |
| The free server sleeps after 15 minutes | Open the teacher page early on Monday | A paid instance |
| The teacher can't record "bank day booked"; a blocker clears only when the student updates her documents | By design for now | The teacher ↔ student loop (roadmap, Horizon 2) |
| Voice and Ask's free-text answers have not run against the real Sarvam API | No key yet | Test the moment the key arrives |

## 5. Panel questions, with short answers

1. **"What stops a student's data reaching the teacher, or you?"** Three tiers. Gender, community, income, documents, answers and voice never leave her phone. The server refuses any sync field outside the shared list, and tests prove it.
2. **"If the AI gets it wrong, does a student miss a scholarship?"** No. The AI never decides eligibility: tested rules on the phone do, with a source and a check date for each rule. The AI only suggests which picture she meant, and she confirms with a tap.
3. **"How accurate is the Tamil speech?"** Give the measured character error rate and answer accuracy from `eval/run_eval.py`, with the date. Say that the speakers were adults.
4. **"What happens with no internet?"** Everything except voice and sync works in airplane mode. Updates wait on the phone and reach the teacher seconds after the signal returns. We tested a flapping network and a week offline.
5. **"How do you know the scheme rules are right?"** Each rule has a source and a check date, and 47 rule tests run on every phone. The two Tamil Nadu schemes are being checked against the government orders. The pilot plan is a signed, versioned rules pack maintained with the department.
6. **"Teachers are overloaded. Why would they use this?"** The Actions tab turns "who is stuck" into one card per blocker: who, what to do, where, and a parent message to copy. About five minutes a week.
7. **"Can a teacher find out a student's caste?"** No. It's never stored, and Ask refuses to list or count students by caste, community, religion, income or gender.
8. **"How many students can it handle?"** Measured: 40 phones at classroom pace with a 95th-percentile sync of 80 ms, and bursts of 160 syncs a second, on one worker. The demo runs on the free plan; a pilot would use a paid instance.
9. **"What does it cost?"** About ₹1 per voice conversation (use the measured figure) and about ₹0.03 per free-text Ask question. Rule answers and every eligibility check cost nothing, because they run on the phone.
10. **"Is it biased by gender?"** Path matching never reads the profile. 1,000 random gender swaps changed 0 recommendations, and the test runs on every phone.
11. **"Why a web app and not native?"** It installs like an app, works offline and updates without a store. Flutter is for the pilot, for very low-end phones.
12. **"Why Sarvam and not the open models on your slide?"** Sarvam's hosted Indian-language models gave us real Tamil voice in a weekend. The same pipeline can run on self-hosted open models, so the state owns it.
13. **"A shared family phone: what about privacy between siblings?"** Each student has a picture-PIN profile, and wrong guesses are slowed down. Her details are stored only under her own profile.
14. **"How do you measure impact?"** The share of students who move on to Class 11, ITI, college or an apprenticeship. The pilot adds outcome tracking after results. The target is +5 points, and +8 for girls.
15. **"What's your riskiest assumption?"** That teachers act on blockers each week. The pilot measures blockers cleared per week, per class.
16. **"What if a student types the wrong roll number?"** Today it makes a stray row. In the pilot, the teacher enrolls each phone with a QR code, which fixes this and stops anyone posting for someone else.
