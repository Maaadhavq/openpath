# OpenPath product map

## The north star and what moves it

**North star:** the share of Class 10 students who move on to Class 11, ITI, college or an apprenticeship. The pilot target is +5 points, and +8 for girls.

| Input metric | Why it moves the north star | Where we see it |
|---|---|---|
| Students who chose a path | A named goal beats "teacher or nurse by default" | Teacher Overview: "22 of 25 chose a path" |
| Plan steps done each week | Small steps carry the decision through to May | Students tab: week-by-week bars |
| Blockers cleared per week | A missing bank account or certificate stops scholarships | Actions tab; "blocker cleared" in the activity feed |
| Students with no update for 7+ days | Early warning that a student has stopped | Overview figure; Students filter |
| Parent follow-through (pilot) | Parents make the Class 11 group and ITI decision | Parent messages copied or sent |

## Who it is for

| Persona | Situation | What she needs from OpenPath |
|---|---|---|
| **Kavya**, 15, Class 10, government school, Ramanathapuram | Keeps the family shop's accounts; knows only teacher and nurse as careers; a shared family phone; patchy signal | Careers that fit what she already does, in Tamil, by voice or by tapping; the schemes she can get and the documents missing; all of it without a signal, and private |
| **New student** on the same phone (Kavya's cousin, roll 29) | Not on the teacher's sample list yet | Her own profile in a minute, without anyone else seeing her details |
| **Ms Selvi**, class teacher of 10-B | 40 students, little time, no counselling training | Who is stuck and what to do this week; answers about documents and schemes without searching |
| **Kavya's mother** (pilot) | Decides on the Class 11 group, ITI and travel | A short message in Tamil about the next step and the document needed |
| **Headmaster** (pilot) | Arranges visits and camps | A weekly one-page report per class |
| **e-Sevai operator** (pilot) | Submits applications on official portals | A printed list: which student, which document |
| **District officer** (Horizon 3) | Places camps, counsellors and ITI seats | Counts by block and school, never names, never a group under 10 |

## The surfaces

```
  Student phone (installed web app)              Teacher laptop or phone
  ┌─────────────────────────────────┐            ┌──────────────────────────────────┐
  │ Lock: picture PIN per student   │            │ Sign-in: class code              │
  │ Discover: voice or tap          │            │ Overview: figures, this week,    │
  │ Details: stay on the phone      │            │   live feed, paths, coming up    │
  │ Skills → Paths (3 + wildcard)   │            │ Students: search, filters,       │
  │ Plan: 4 weeks, re-route         │            │   detail drawer per student      │
  │ Support: 11 schemes by rules    │            │ Actions: one card per blocker,   │
  │ Get ready to apply              │            │   parent message, print view     │
  │ Settings: language, what my     │            │ Ask OpenPath: class, documents,  │
  │   teacher sees, checks          │            │   schemes; never eligibility     │
  └───────────────┬─────────────────┘            └────────────────┬─────────────────┘
     offline queue │ sync: roll, path, progress,           polls    │ every 3 s
                   │ next step kind, one blocker                    │
                   ▼                                                ▼
  ┌──────────────────────────────────────────────────────────────────────────────────┐
  │ Server (FastAPI, one origin): /api/sync · /api/class · /api/student · /api/ask ·  │
  │ /api/talk · /api/reset    In memory today; Postgres in the pilot                  │
  └───────────────────────────────┬──────────────────────────────────────────────────┘
                                  │ speech, transcripts, roll numbers (never names)
                                  ▼
                 Sarvam: Saaras v4 (speech) · Sarvam-105B (understanding) · Bulbul (voice)
```

## The privacy tiers

| Tier | Data | Seen by |
|---|---|---|
| Never leaves the phone | gender, community, family income, documents held, marks, answers, voice, scheme eligibility | the student |
| Shared with the class teacher | roll number, first name (students who joined on the phone), path, plan progress overall and per week, kind of next step, one blocker, last update | her class teacher |
| Aggregates only (Horizon 3) | counts by path, blocker and status; never a group under 10 | headmaster, block, district |

## Journeys

**Kavya:**
1. **Unlock:** picture PIN (sun, leaf, star).
2. **Discover:** she *says* her answer in Tamil. The suggested picture lights up, the app asks "is this right?" in Tamil, and she taps to confirm.
3. **Details:** class, school, community, income and documents, kept on the phone.
4. **Skills:** what she already uses.
5. **Paths:** 3 good fits and a wildcard, with a story and a place to visit. She picks Lab technician.
6. **Plan:** 4 weeks of small steps. "Missed a step?" moves it to the next week.
7. **Support:** Pudhumai Penn "later", with "Missing: bank account"; PM YASASVI pre-matric "likely". She opens "Get ready to apply" to show her teacher.
8. **Sync:** when the signal returns, her progress and one blocker reach her teacher. She can check exactly what is sent in Settings.

**Ms Selvi:**
1. **Sign in:** with the class code.
2. **Overview:** "4 need a bank account → hold a bank day at the post office". The live feed shows "Kavya S chose Lab technician".
3. **Students:** filter to Needs help, then open Kavya: week-by-week plan, next step, how to help, and a message for her mother.
4. **Actions:** print the bank-account list for the post office, and copy the Tamil parent message into the class WhatsApp group.
5. **Ask:** "How do students get an income certificate?" or "Explain Pudhumai Penn". If she asks "Is Kavya eligible?", OpenPath says that's checked on Kavya's phone.

## Feature map

| Area | Feature | Persona | Tier | Status | Proof |
|---|---|---|---|---|---|
| Phone | Installable, works in airplane mode | Kavya | phone | Built | `test_app.py::test_installable_and_offline` |
| Phone | Picture-PIN profiles, guess lockout | Kavya, new student | phone | Built | `test_stress.py::test_guessing_a_picture_pin_is_slowed_down` |
| Phone | New student: roll number, optional name, PIN | New student | shared (roll, name) | Built | `test_sync.py::test_new_student_filled_in_offline_reaches_the_teacher` |
| Phone | Voice answer, confirm by tap | Kavya | voice processed, not kept | Built (fake voice until the key) | `test_voice.py` |
| Phone | Paths never use gender | Kavya | phone | Built | Checks tab: 0 of 1,000 swaps |
| Phone | 11 schemes by tested rules, missing documents | Kavya | phone | Built | Checks tab: 47/47 rule tests |
| Phone | Offline queue, fast resend | Kavya | shared | Built | `test_stress.py::test_flapping_network_ends_consistent` |
| Phone | "What my teacher sees" | Kavya | shared | Built | `test_teacher.py::test_phone_shows_what_the_teacher_sees` |
| Teacher | Class code sign-in | Ms Selvi | — | Built | `server/tests/test_teacher.py` |
| Teacher | Overview: figures, this week, live feed, paths, coming up | Ms Selvi | shared | Built | `test_teacher.py::test_overview_drawer_actions_after_kavya_syncs` |
| Teacher | Students: search, filters, drawer | Ms Selvi | shared | Built | same |
| Teacher | Actions: blocker cards, parent message, print | Ms Selvi, parent, operator | shared | Built | same |
| Teacher | Ask OpenPath: rules first, Sarvam second, privacy refusals | Ms Selvi | shared; names never sent | Built (rules); Sarvam path untested live | `server/tests/test_teacher.py`, `test_stress.py` |
| Proof | Checks tab, measured speech numbers | Panel, department | — | Built (speech numbers pending recordings) | `test_eval.py` |
| Pilot | Teacher ↔ student loop: help requests, group notes | Kavya, Ms Selvi | shared | Planned | — |
| Pilot | Document camps booked from a blocker group | Ms Selvi, operator | shared | Planned | — |
| Pilot | Parent voice notes in Tamil (consented) | Parent | shared | Planned | — |
| Pilot | QR enrollment of phones | Ms Selvi | — | Planned (fixes spoofing and roll typos) | — |
| Pilot | Accounts, Postgres, several classes | Ms Selvi | shared | Planned | — |
| Pilot | Outcome tracking after results | Kavya, headmaster | shared (outcome type) | Planned | — |
| Scale | District dashboards, aggregates only | District officer | aggregate | Planned | — |
| Scale | Signed, versioned scheme-rules pack | Department | — | Planned | — |
| Scale | Self-hosted Tamil models, on-device voice | Kavya | phone | Planned | — |
