# OpenPath user stories

Status: **Built** means it is in the finale build and a test proves it. **Pilot** is Horizon 2 (10 schools, Jan–Jun 2027). **Scale** is Horizon 3. The privacy tier for each story is in `PRODUCT_MAP.md`.

## Student: a private profile on a shared phone

| # | Story | Acceptance | Status | Proof |
|---|---|---|---|---|
| S1 | As Kavya, I want my own picture PIN, so that my brother can't see my answers on the family phone | Wrong PIN never opens the profile; Kavya's details load only after sun, leaf, star | Built | `test_app.py::test_round2_demo_path` |
| S2 | As Kavya, I want guesses at my PIN slowed down, so that nobody can try all 216 combinations | After 5 wrong tries the phone waits 30 seconds and ignores taps | Built | `test_stress.py::test_guessing_a_picture_pin_is_slowed_down` |
| S3 | As a new student on the same phone, I want my own profile in a minute, so that I can start without anyone setting me up | Roll number (26 to 99), optional first name, 3 pictures; rolls already on the phone or the class list are refused | Built | `test_sync.py::test_new_student_filled_in_offline_reaches_the_teacher` |
| S4 | As Kavya, I want to find my progress where I left it, so that I don't redo the questions | After a reload and the PIN, the plan shows the same ticks | Built | `test_app.py::test_progress_survives_reload` |

## Student: discover careers by voice or by tapping

| # | Story | Acceptance | Status | Proof |
|---|---|---|---|---|
| S5 | As Kavya, I want to answer by speaking Tamil, so that I don't have to read or type | Speak → transcript shown → the suggested picture lights up → only a tap saves the answer | Built (fake voice until the key) | `test_voice.py::test_speak_suggests_and_tap_confirms` |
| S6 | As Kavya, I want tapping to always work, so that no signal or a noisy room doesn't stop me | Offline, Speak is disabled with "Voice needs a signal. Tap a picture."; taps save answers | Built | `test_voice.py::test_offline_disables_speak` |
| S7 | As Kavya, I want questions and confirmations read aloud in Tamil, so that I can follow without reading | Clips play after taps: question, "you said", option, "is this right?" | Built (clips need a chosen voice) | `test_voice.py::test_voice_plays_confirm_clips` |
| S8 | As Kavya, I want skills found from what I do at home, so that I see I already have strengths | Skills come from the three answers, not marks | Built | `test_port.py` (same as Round 2) |

## Student: paths, plan and support

| # | Story | Acceptance | Status | Proof |
|---|---|---|---|---|
| S9 | As Kavya, I want three paths that fit and one I haven't thought of, so that I see beyond teacher and nurse | 3 picks plus a wildcard; at most one usual career; at least one non-degree route | Built | `test_port.py` |
| S10 | As Kavya, I want paths that never depend on my gender, so that being a girl doesn't narrow my options | 1,000 random gender swaps change 0 recommendations | Built | Checks tab; `test_app.py::test_checks_pass` |
| S11 | As Kavya, I want a 4-week plan of small steps, so that I know what to do this week | Lessons, documents, a visit, a decision; "Missed a step?" moves open steps to the next week | Built | `test_port.py` |
| S12 | As Kavya, I want to see the schemes I can get and the documents I'm missing, without internet, so that I can get ready in time | 11 schemes, each yes, likely, later, depends on the course, needs an answer, or not for you; checked on the phone | Built | `test_app.py::test_installable_and_offline` |
| S13 | As Kavya, I want a checklist to show my teacher, so that an adult can submit the application | "Get ready to apply" lists documents held and missing, and where to get them | Built | `test_app.py::test_round2_demo_path` |

## Student: offline and trust

| # | Story | Acceptance | Status | Proof |
|---|---|---|---|---|
| S14 | As Kavya, I want my progress to reach my teacher when I get signal, without doing anything, so that she knows how I'm doing | Updates queue offline and send within seconds of the signal returning, even if it flaps | Built | `test_stress.py::test_flapping_network_ends_consistent` |
| S15 | As Kavya, I want to see exactly what my teacher sees, so that I can trust the app | Settings → "What your teacher sees" shows my roll number, path, progress, next step kind and blocker, and lists what never leaves the phone | Built | `test_teacher.py::test_phone_shows_what_the_teacher_sees` |
| S16 | As Kavya, I want my community, income and documents never sent anywhere, so that sharing my progress doesn't expose my family | The server refuses any sync with other fields | Built | `server/tests/test_sync.py::test_sync_rejects_personal_fields` |

## Teacher: see the class

| # | Story | Acceptance | Status | Proof |
|---|---|---|---|---|
| T1 | As Ms Selvi, I want the class page behind a code, so that students' names aren't public | Without the code: sign-in screen; wrong codes are limited | Built | `server/tests/test_teacher.py::test_teacher_pages_need_the_code` |
| T2 | As Ms Selvi, I want four numbers at a glance, so that I know where the class stands | Chose a path, on track, need help with a document, no update for 7+ days | Built | `server/tests/test_teacher.py::test_seed_summary` |
| T3 | As Ms Selvi, I want to see updates arrive from phones, so that I know who is working now | "Live from the phones" shows each sync within 3 seconds | Built | `test_teacher.py::test_overview_drawer_actions_after_kavya_syncs` |
| T4 | As Ms Selvi, I want to find a student and see her plan week by week, so that I can talk to her about the next step | Search and filters; a drawer with path, weeks, next step, how to help, deadlines, activity and what her phone shares | Built | same |
| T5 | As Ms Selvi, I want "no update" not to accuse a student who works offline, so that I talk to her fairly | The label says "no update for 7+ days"; Ask adds "they may be working offline" | Built | `server/tests/test_stress.py::test_ask_inactive_wording_allows_for_offline_use` |
| T6 | As Ms Selvi, I want new students to appear when their phones sync, so that the class list stays complete | A roll number not on the list appears with the first name sent, marked (new) | Built | `test_sync.py::test_new_student_filled_in_offline_reaches_the_teacher` |

## Teacher: act this week

| # | Story | Acceptance | Status | Proof |
|---|---|---|---|---|
| T7 | As Ms Selvi, I want students grouped by what blocks them, with what to do, so that one action helps several | One card per blocker: students, steps, where to go | Built | `test_teacher.py::test_overview_drawer_actions_after_kavya_syncs` |
| T8 | As Ms Selvi, I want a parent message in Tamil and English to copy, so that families act at home | Copy button puts the message on the clipboard | Built | same |
| T9 | As Ms Selvi, I want a printed list for the post office or e-Sevai, so that the operator knows who and what | "Print this list" prints only that card | Built | manual check |

## Teacher: Ask OpenPath

| # | Story | Acceptance | Status | Proof |
|---|---|---|---|---|
| T10 | As Ms Selvi, I want to ask "who needs help this week?" and get names and steps, so that I don't build lists by hand | Answered from class data with no AI call, in English or Tamil | Built | `server/tests/test_teacher.py::test_ask_rules` |
| T11 | As Ms Selvi, I want a scheme explained with its source, so that I can trust it and show parents | Benefit, conditions, documents, source; ends by saying eligibility is checked on the student's phone | Built | `server/tests/test_teacher.py::test_ask_scheme_cites_its_source_and_never_judges_a_student` |
| T12 | As Ms Selvi, I want other questions answered too, so that I can plan visits or write notes | Free text goes to Sarvam-105B with roll numbers instead of names; names come back on our server | Built (not yet tried with the real key) | `server/tests/test_teacher.py::test_ask_llm_gets_roll_numbers_not_names` |
| T13 | As a student, I want Ask to refuse to sort us by caste, income or gender, so that the teacher tool can't be used against us | Lists or counts by those are refused with the reason; questions about certificates and schemes still work | Built | `server/tests/test_stress.py::test_ask_cannot_reveal_what_is_never_stored` |

## Pilot (Horizon 2)

| # | Story | Acceptance |
|---|---|---|
| P1 | As Kavya, I want to tap "Ask my teacher for help" on a blocker, so that she knows I'm stuck | The request shows on the teacher's Actions card |
| P2 | As Ms Selvi, I want to post a note to a blocker group, so that those students' phones show "Bank day at the post office, Wednesday 10 AM" | The note arrives with the next sync |
| P3 | As Ms Selvi, I want to book a document camp from a blocker card, so that I don't arrange it by phone calls | The operator gets a printed list; students get the note |
| P4 | As Kavya's mother, I want a short Tamil voice note about the next step, so that I can help even if I don't read much | Opt-in; Bulbul voice; no profile data |
| P5 | As Ms Selvi, I want to enroll each phone with a QR code, so that nobody posts progress for someone else and roll typos can't happen | A sync from a phone not enrolled for that roll number is refused |
| P6 | As Ms Selvi, I want the class list kept after a restart and several classes in one account, so that I can rely on it | Postgres; sign-in by school code |
| P7 | As the headmaster, I want a weekly one-page report per class, so that I can arrange visits and camps | PDF with counts and the teacher's action list |
| P8 | As Kavya, I want to record where I went after the results, so that the school knows if OpenPath helped | Outcome type only: Class 11 group, ITI, polytechnic, apprenticeship, other |

## Scale (Horizon 3)

| # | Story | Acceptance |
|---|---|---|
| D1 | As a district officer, I want transition rates and blockers by block, so that I can place camps and counsellors | Aggregates only; never a group under 10; no names |
| D2 | As the department, I want to publish rule changes as a signed, versioned pack, so that every phone uses the current rules | Phones verify the signature; each rule carries its G.O. and check date |
| D3 | As Kavya, I want voice to work without a signal, so that I don't need data for Tamil speech | On-device or state-hosted AI4Bharat models |
| D4 | As Kavya, I want my documents checked from DigiLocker with my consent, so that I don't make a wasted trip | Consent each time; the result stays on the phone |
