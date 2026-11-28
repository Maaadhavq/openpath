"""Ask OpenPath: a class teacher's questions about her class, documents and schemes.

Common questions are answered by rules from the class data, with no AI call, so they work in fake mode and when Sarvam
is slow. Anything else goes to Sarvam-105B with the class data and the scheme notes. Student names never reach Sarvam:
they are replaced by roll numbers before the call and put back in the answer here. Nothing here decides who is
eligible for a scheme; that is checked on the student's own phone by tested rules.
"""
from __future__ import annotations

import logging
import re
import time

import httpx

from . import sarvam
from .config import Settings
from .kb import guide, kb
from .schemas import paths

log = logging.getLogger("openpath.ask")
ROLL_RE = re.compile(r"10B-\d{2}")

SYSTEM = """You help a class teacher in a Tamil Nadu government school guide her Class 10 students towards further study and the support they can get.
Use only the class data and the reference notes below. Students appear only by roll number (like 10B-07); refer to them that way.
Rules:
- Never say or guess whether a student is eligible for a scheme. Eligibility is checked on the student's own phone by tested rules, using details that never leave the phone. If asked, say so and explain what the scheme requires in general.
- Never ask about or infer anyone's caste, community, religion, income or gender.
- Give practical steps a teacher can take this week. At most 8 short lines, plain text, no tables, no markdown headings.
- When you mention a scheme, name its source from the notes.
- If the notes do not cover the question, say you do not know.
- Answer in {lang}."""

SUGGESTIONS = [
    {"ta": "இந்த வாரம் யாருக்கு உதவி தேவை?", "en": "Who needs help this week?"},
    {"ta": "யார் இன்னும் பாதை தேர்வு செய்யவில்லை?", "en": "Who hasn't chosen a path?"},
    {"ta": "ஒரு வாரமாக யார் செயலியைத் திறக்கவில்லை?", "en": "Who hasn't opened the app for a week?"},
    {"ta": "வருமானச் சான்றிதழ் எப்படிப் பெறுவது?", "en": "How do students get an income certificate?"},
    {"ta": "தொழில் வாரியாக பார்வைப் பயணம் திட்டமிடு", "en": "Plan visits by career"},
    {"ta": "அடுத்து வரும் தேதிகள் என்ன?", "en": "What's coming up?"},
    {"ta": "புதுமைப் பெண் திட்டம் பற்றி சொல்", "en": "Explain Pudhumai Penn"},
    {"ta": "என் வகுப்பு எப்படி இருக்கிறது?", "en": "How is my class doing?"},
]

KW = {
    "eligible": ["eligible", "eligibility", "qualify", "qualifies", "தகுதி"],
    "no_path": ["no path", "not chosen", "haven't chosen", "hasn't chosen", "have not chosen", "not yet chosen", "not started",
                "without a path", "பாதை இல்லை", "பாதை தேர்வு செய்யவில்லை", "தொடங்கவில்லை"],
    "inactive": ["inactive", "not active", "haven't opened", "hasn't opened", "not opened", "opened the app", "not used", "absent",
                 "திறக்கவில்லை", "செயலில் இல்லை"],
    "needs_help": ["need help", "needs help", "stuck", "blocker", "blocked", "help this week", "உதவி தேவை", "தடை"],
    "deadlines": ["deadline", "due", "coming up", "what's next", "exam", "dates", "calendar", "தேதி", "எப்போது"],
    "visit": ["visit", "visits", "trip", "trips", "field visit", "outing", "பார்வை"],
    "mix": ["path mix", "which paths", "what paths", "careers", "career choices", "paths chosen", "பாதைகள்"],
    "summary": ["summary", "overview", "how is my class", "how is the class", "class doing", "class status", "சுருக்கம்", "வகுப்பு எப்படி"],
}
DOC_KW = {"bank": ["bank", "வங்கி"], "income": ["income", "வருமான"], "community": ["community", "caste certificate", "சாதி"],
          "aadhaar": ["aadhaar", "aadhar", "ஆதார்"]}
SCHEME_KW = {
    "pudhumai": ["pudhumai", "புதுமைப்"], "pudhalvan": ["pudhalvan", "puthalvan", "புதல்வன்"], "quota75": ["7.5", "quota", "ஒதுக்கீடு"],
    "firstgrad": ["first graduate", "first-graduate", "முதல் பட்டதாரி"], "csss": ["csss", "central sector"], "pragati": ["pragati", "பிரகதி"],
    "yasasvi_pre": ["yasasvi", "யசஸ்வி"], "yasasvi_post": ["yasasvi", "யசஸ்வி"],
    "sc_pre": ["sc students", "sc scholarship", "for sc"], "sc_post": ["sc students", "sc scholarship", "for sc"],
    "st_post": ["st students", "st scholarship", "for st"],
}
PATH_KW = {
    "nursing": ["nurse", "nurses", "nursing"], "labtech": ["lab technician", "lab tech", "dmlt"], "solar": ["solar"],
    "bike": ["mechanic", "two-wheeler", "bike"], "accounts": ["accounts assistant", "accountant", "b.com", "commerce"],
    "mobile": ["mobile repair"], "agri": ["agriculture", "agri"], "garment": ["garment", "fashion", "tailoring"],
    "teacher": ["d.el.ed", "become a teacher", "teacher training"], "civil": ["civil"], "copa": ["computer operator", "copa"],
    "pharma": ["pharmacist", "pharmacy", "d.pharm"], "engineering": ["engineer", "engineering", "b.e."], "graphic": ["graphic"],
}
# Questions that try to list or count students by what OpenPath never stores.
PROTECTED = ["sc", "st", "obc", "bc", "mbc", "dnc", "dnt", "caste", "community", "religion", "girl", "girls", "boy", "boys", "gender",
             "income", "poor", "rich", "salary", "earn", "earns", "சாதி", "மதம்", "வருமான", "பெண்", "ஆண்", "ஏழை"]
ASKS_WHO = ["which", "who", "list", "how many", "count", "show", "what is", "what's", "யார்", "எத்தனை", "பட்டியல்"]
ABOUT_RULES = ["certificate", "scholarship", "scheme", "pudhumai", "penn", "pudhalvan", "yasasvi", "pragati", "csss", "quota",
               "explain", "tell me about", "only for", "rule", "rules", "சான்றிதழ்", "உதவித்தொகை", "திட்டம்", "புதுமைப்"]
KIND_KW = {"iti": ["iti"], "diploma": ["diploma", "polytechnic"], "degree": ["degree", "college"]}
WHEN = {"entry": {"ta": "பட்டம், டிப்ளமோ அல்லது ITI-யில் சேரும்போது", "en": "when joining a degree, diploma or ITI"},
        "9-10": {"ta": "9, 10ஆம் வகுப்பில்", "en": "in Class 9 and 10"}, "11+": {"ta": "11ஆம் வகுப்பு முதல்", "en": "from Class 11"}}


def _has(q: str, words: list[str]) -> bool:
    """Whole-word match for English keywords ("for st" must not match "for students"); substring match for Tamil."""
    for w in words:
        if w.isascii():
            if re.search(rf"(?<![a-z0-9]){re.escape(w)}(?![a-z0-9])", q):
                return True
        elif w in q:
            return True
    return False


def _who(students: list[dict]) -> str:
    return ", ".join(f"{s['name']} ({s['roll']})" for s in students) or "–"


def _t(lang: str, ta: str, en: str) -> str:
    return ta if lang == "ta" else en


def _used(students: list[dict]) -> list[dict]:
    return [{"roll": s["roll"], "name": s["name"]} for s in students]


def _source(sid: str) -> dict:
    s = next(x for x in kb()["schemes"] if x["id"] == sid)
    return {"label": s["source"]["label"], "url": s["source"]["url"], "scheme": s["name"]}


# ---------------- answers from rules ----------------
def a_needs_help(lang, students, summary):
    lines, used = [], []
    doc_groups = [g for g in summary["groups"] if g["blocker"] != "no_path_yet"]
    n = sum(g["count"] for g in doc_groups)
    lines.append(_t(lang, f"இந்த வாரம் {n} மாணவர்களுக்கு ஆவண உதவி தேவை:", f"{n} students need help with a document this week:") if n
                 else _t(lang, "இந்த வாரம் ஆவண உதவி தேவைப்படுபவர்கள் இல்லை.", "Nobody is waiting on a document this week."))
    for g in doc_groups:
        lines.append(f"• {g['label'][lang]} ({g['count']}): {_who(g['students'])}")
        lines.append(f"  → {g['action'][lang]}")
        used += g["students"]
    nop = next((g for g in summary["groups"] if g["blocker"] == "no_path_yet"), None)
    if nop:
        lines.append(_t(lang, f"{nop['count']} பேருக்கு பாதை இன்னும் இல்லை: {_who(nop['students'])}",
                        f"{nop['count']} have no path yet: {_who(nop['students'])}"))
        lines.append(f"  → {nop['action'][lang]}")
        used += nop["students"]
    return "\n".join(lines), used, []


def a_no_path(lang, students, summary):
    sel = [s for s in students if not s["path"]]
    if not sel:
        return _t(lang, "எல்லா மாணவர்களும் ஒரு பாதையைத் தேர்ந்தெடுத்துவிட்டனர்.", "Every student has chosen a path."), [], []
    act = guide()["blockers"]["no_path_yet"]["action"][lang]
    return (_t(lang, f"{len(sel)} மாணவர்கள் இன்னும் பாதை தேர்வு செய்யவில்லை: {_who(sel)}\n→ {act}",
               f"{len(sel)} students have not chosen a path yet: {_who(sel)}\n→ {act}"), _used(sel), [])


def a_inactive(lang, students, summary):
    sel = sorted([s for s in students if s["days_since_active"] is not None and s["days_since_active"] >= 7],
                 key=lambda s: -s["days_since_active"])
    if not sel:
        return _t(lang, "எல்லோரும் கடந்த வாரத்தில் செயலியைத் திறந்துள்ளனர்.", "Everyone has used the app in the last week."), [], []
    who = ", ".join(f"{s['name']} ({s['roll']}, {s['days_since_active']} " + _t(lang, "நாள்", "days") + ")" for s in sel)
    return (_t(lang, f"{len(sel)} மாணவர்களின் போனிலிருந்து 7 நாளுக்கு மேல் புதுப்பிப்பு இல்லை (இணையம் இல்லாமல் பயன்படுத்தியிருக்கலாம்): {who}\n→ வகுப்பில் சிறு உரையாடல் நடத்து; செயலியைத் திறந்து ஒரு படியை முடிக்கச் சொல். இணையம் கிடைத்ததும் புதுப்பிப்பு வரும்.",
               f"{len(sel)} students have sent no update for 7 days or more (they may be working offline): {who}\n→ Have a quick word in class and ask each of them to open the app and finish one step; the update arrives when their phone has a signal."),
            _used(sel), [])


def a_deadlines(lang, students, summary):
    lines = [_t(lang, "உங்கள் வகுப்புக்கு அடுத்து வருபவை:", "Coming up for your class:")]
    for d in summary["deadlines"]:
        lines.append(f"• {d['text'][lang]}: {d['count']} " + _t(lang, "மாணவர்கள்", "students"))
    return "\n".join(lines), [], []


def a_visit(lang, students, summary):
    places: dict[str, dict] = {}
    for s in students:
        if s["path"]:
            v = paths()[s["path"]]["visit"]
            places.setdefault(v["en"], {"visit": v, "students": []})["students"].append(s)
    if not places:
        return _t(lang, "இன்னும் யாரும் பாதை தேர்வு செய்யவில்லை.", "Nobody has chosen a path yet."), [], []
    lines = [_t(lang, "பாதை வாரியாக பார்வைப் பயணங்கள்:", "Visits grouped by career path:")]
    used = []
    for p in sorted(places.values(), key=lambda x: -len(x["students"])):
        lines.append(f"• {p['visit'][lang]} ({len(p['students'])}): {_who(p['students'])}")
        used += p["students"]
    lines.append(_t(lang, "→ பெரிய குழுவில் தொடங்கு; ஒரே பயணத்தில் பல மாணவர்கள் பயன்பெறுவர்.", "→ Start with the biggest group: one trip helps the most students."))
    return "\n".join(lines), _used(used), []


def a_mix(lang, students, summary):
    lines = [_t(lang, "உங்கள் வகுப்பின் பாதைத் தேர்வுகள்:", "Path choices in your class:")]
    for m in summary["path_mix"]:
        lines.append(f"• {m['name'][lang]}: {m['count']}")
    lines.append(_t(lang, f"{summary['not_started']} பேர் இன்னும் தேர்வு செய்யவில்லை.", f"{summary['not_started']} have not chosen yet."))
    return "\n".join(lines), [], []


def a_path(lang, students, pids, label):
    sel = [s for s in students if s["path"] in pids]
    if not sel:
        return _t(lang, f"{label[lang]}: யாரும் இல்லை.", f"Nobody has chosen {label['en']} yet."), [], []
    lines = [_t(lang, f"{label[lang]} — {len(sel)} மாணவர்கள்: {_who(sel)}", f"{label['en']}: {len(sel)} students: {_who(sel)}")]
    for pid in pids:
        if any(s["path"] == pid for s in sel):
            p = paths()[pid]
            lines.append(f"• {p['name'][lang]}: {p['route'][lang]}. " + _t(lang, "பார்வை: ", "Visit: ") + p["visit"][lang])
    return "\n".join(lines), _used(sel), []


def a_summary(lang, students, summary):
    top = ", ".join(m["name"][lang] for m in summary["path_mix"][:3])
    g = summary["groups"][0] if summary["groups"] else None
    lines = [_t(lang,
                f"10-B: {summary['total']} பேரில் {summary['chose_path']} பேர் பாதை தேர்ந்தெடுத்தனர்; {summary['on_track']} பேர் சரியாகப் போகின்றனர்; {summary['need_help']} பேருக்கு ஆவண உதவி தேவை; {summary['inactive']} பேர் 7 நாளுக்கு மேல் திறக்கவில்லை.",
                f"10-B: {summary['chose_path']} of {summary['total']} chose a path; {summary['on_track']} are on track; {summary['need_help']} need help with a document; {summary['inactive']} have not opened the app for 7+ days.")]
    if top:
        lines.append(_t(lang, f"அதிகம் தேர்ந்தெடுக்கப்பட்டவை: {top}.", f"Most chosen: {top}."))
    if g:
        lines.append(_t(lang, f"இந்த வாரத்தின் முதல் வேலை: {g['label']['ta']} ({g['count']}) → {g['action']['ta']}",
                        f"First job this week: {g['label']['en']} ({g['count']}) → {g['action']['en']}"))
    return "\n".join(lines), [], []


def a_doc(lang, students, summary, doc):
    d = kb()["docs"][doc]
    key = next(k for k, b in guide()["blockers"].items() if b["doc"] == doc)
    b = guide()["blockers"][key]
    sel = [s for s in students if s.get("blocker") == key]
    lines = [f"{d['name'][lang]}: " + _t(lang, "எங்கே: ", "where: ") + d["how"][lang] + "."]
    lines.append(_t(lang, f"{len(sel)} மாணவர்களுக்கு இப்போது இது தேவை: {_who(sel)}", f"{len(sel)} students need it now: {_who(sel)}") if sel
                 else _t(lang, "இப்போது இதற்காகக் காத்திருப்பவர்கள் இல்லை.", "Nobody is waiting on this right now."))
    lines.append(f"→ {b['action'][lang]}")
    return "\n".join(lines), _used(sel), []


def a_scheme(lang, sids):
    lines, sources = [], []
    docs = kb()["docs"]
    for sid in sids:
        s = next(x for x in kb()["schemes"] if x["id"] == sid)
        lines.append(f"{s['name'][lang]} ({s['by']}): {s['benefit'][lang]}, {WHEN[s['when']][lang]}.")
        lines.append(_t(lang, "நிபந்தனைகள்: ", "Conditions: ") + "; ".join(c[lang] for c in s["conditions"]) + ".")
        if s["docs"]:
            lines.append(_t(lang, "ஆவணங்கள்: ", "Documents: ") + ", ".join(docs[d]["name"][lang] for d in s["docs"]) + ".")
        lines.append(_t(lang, "ஆதாரம்: ", "Source: ") + s["source"]["label"])
        sources.append(_source(sid))
    lines.append(_t(lang, "ஒவ்வொரு மாணவியின் தகுதியும் அவளுடைய போனிலேயே சரிபார்க்கப்படுகிறது; \"உதவி\" பகுதியைத் திறக்கச் சொல்.",
                    "Each student's eligibility is checked on her own phone; ask her to open Support."))
    return "\n".join(lines), [], sources


def a_eligible(lang, sids):
    text = _t(lang,
              "OpenPath சர்வரில் தகுதியை முடிவு செய்வதில்லை. சமூகம், வருமானம் போன்ற விவரங்கள் போனை விட்டு வெளியே வருவதில்லை; ஒவ்வொரு மாணவியின் போனும் சோதிக்கப்பட்ட விதிகளால் தகுதியைச் சரிபார்க்கிறது. அவளிடம் போனில் \"உதவி\" பகுதியைத் திறக்கச் சொல்: நிலையும் இல்லாத ஆவணங்களும் அங்கே தெரியும்.",
              "OpenPath does not decide eligibility on the server. Details like community and income never leave the student's phone; her phone checks each scheme with tested rules. Ask her to open Support on her phone: it shows her status and any missing documents.")
    if sids:
        more, _, sources = a_scheme(lang, sids)
        return text + "\n" + more, [], sources
    return text, [], []


def a_private(lang):
    return (_t(lang,
               "OpenPath ஒரு மாணவியின் சாதி, சமூகம், மதம், குடும்ப வருமானம் அல்லது பாலினத்தை ஒருபோதும் சேமிப்பதில்லை: அவை அவளுடைய போனிலேயே இருக்கும், உதவித்தொகை விதிகளையும் அவள் போனே தனிப்பட்ட முறையில் சரிபார்க்கிறது. அதனால் இவற்றை வைத்து மாணவர்களைப் பட்டியலிடவோ எண்ணவோ முடியாது. யாருக்கு ஆவணம் தேவை, யாருக்குப் பாதை இல்லை, ஒரு திட்டம் எப்படி வேலை செய்கிறது என்று சொல்ல முடியும்.",
               "OpenPath never stores a student's caste, community, religion, family income or gender: they stay on her phone, and her phone checks scheme rules privately. So I can't list or count students by them. I can tell you who needs a document, who has no path yet, or how a scheme works."),
            [], [])


def rules_answer(q: str, lang: str, students: list[dict], summary: dict):
    """Returns (intent, text, used, sources) or None if no rule fits."""
    ql = q.lower()
    if _has(ql, PROTECTED) and _has(ql, ASKS_WHO) and not _has(ql, ABOUT_RULES):
        return ("private", *a_private(lang))
    sids = [sid for sid, words in SCHEME_KW.items() if _has(ql, words)]
    if "pre" in ql and "post" not in ql:
        sids = [s for s in sids if not s.endswith("_post")] or sids
    if "post" in ql and "pre" not in ql:
        sids = [s for s in sids if not s.endswith("_pre")] or sids
    if _has(ql, KW["eligible"]):
        return ("eligible", *a_eligible(lang, sids))
    if sids:
        return ("scheme", *a_scheme(lang, sids))
    for doc, words in DOC_KW.items():
        if _has(ql, words):
            return ("doc", *a_doc(lang, students, summary, doc))
    for intent, fn in (("no_path", a_no_path), ("inactive", a_inactive), ("needs_help", a_needs_help), ("visit", a_visit),
                       ("deadlines", a_deadlines), ("mix", a_mix), ("summary", a_summary)):
        if _has(ql, KW[intent]):
            return (intent, *fn(lang, students, summary))
    for pid, p in paths().items():
        if p["name"]["en"].lower() in ql or p["name"]["ta"] in q or _has(ql, PATH_KW.get(pid, [])):
            return ("path", *a_path(lang, students, [pid], p["name"]))
    for kind, words in KIND_KW.items():
        if any(re.search(rf"\b{re.escape(w)}\b", ql) for w in words):
            pids = [pid for pid, p in paths().items() if p["kind"] == kind]
            label = {"iti": {"ta": "ITI பாதைகள்", "en": "ITI paths"}, "diploma": {"ta": "டிப்ளமோ பாதைகள்", "en": "diploma paths"},
                     "degree": {"ta": "பட்டப் படிப்புப் பாதைகள்", "en": "degree paths"}}[kind]
            return ("path", *a_path(lang, students, pids, label))
    return None


# ---------------- answers from Sarvam-105B ----------------
def class_context(students: list[dict], summary: dict) -> str:
    rows = []
    for s in students:
        blk = guide()["blockers"].get(s.get("blocker") or "")
        rows.append(" | ".join([s["roll"], "path: " + (s["path_name"]["en"] if s.get("path_name") else "none"),
                                "plan: " + (s.get("plan_done") or "-"), "weeks: " + (",".join(s["weeks"]) if s.get("weeks") else "-"),
                                "next: " + s["next_step"]["en"], "blocker: " + (blk["label"]["en"] if blk else "-"),
                                "status: " + s["status"], "last active: " + (f"{s['days_since_active']} days ago" if s["days_since_active"] is not None else "never")]))
    notes = []
    for sc in kb()["schemes"]:
        notes.append(f"- {sc['name']['en']} ({sc['by']}; {WHEN[sc['when']]['en']}): {sc['benefit']['en']}. Conditions: "
                     + "; ".join(c["en"] for c in sc["conditions"]) + ". Documents: " + (", ".join(sc["docs"]) or "none")
                     + f". Source: {sc['source']['label']}.")
    docs = [f"- {d['name']['en']}: {d['how']['en']}" for d in kb()["docs"].values()]
    acts = [f"- {b['label']['en']}: {b['action']['en']}" for b in guide()["blockers"].values()]
    return ("CLASS 10-B (Class 10, government school, sample data). One line per student:\n" + "\n".join(rows)
            + f"\n\nSUMMARY: {summary['chose_path']} of {summary['total']} chose a path; {summary['on_track']} on track; "
              f"{summary['need_help']} need help with a document; {summary['inactive']} inactive 7+ days.\n\nSCHEMES:\n" + "\n".join(notes)
            + "\n\nWHERE DOCUMENTS ARE MADE:\n" + "\n".join(docs) + "\n\nSUGGESTED TEACHER ACTIONS:\n" + "\n".join(acts))


def pseudonymise(text: str, students: list[dict]) -> str:
    """Replaces student names in the teacher's question with roll numbers before anything goes to Sarvam."""
    names = []
    for s in students:
        if s["name"] == "New student":
            continue
        names.append((s["name"], s["roll"]))
        first = s["name"].split()[0]
        if len(first) >= 3:
            names.append((first, s["roll"]))
    for name, roll in sorted(names, key=lambda x: -len(x[0])):
        if name.isascii():
            text = re.sub(rf"\b{re.escape(name)}\b", roll, text, flags=re.I)
        else:
            text = text.replace(name, roll)
    return text


def restore_names(text: str, students: list[dict]) -> tuple[str, list[dict]]:
    by_roll = {s["roll"]: s for s in students}
    used = []
    def put(m):
        s = by_roll.get(m.group(0))
        if not s:
            return m.group(0)
        if s not in used:
            used.append(s)
        return f"{s['name']} ({s['roll']})"
    return ROLL_RE.sub(put, text), _used(used)


async def answer(client: httpx.AsyncClient | None, settings: Settings, question: str, lang: str, students: list[dict], summary: dict) -> dict:
    t0 = time.perf_counter()
    hit = rules_answer(question, lang, students, summary)
    if hit:
        intent, text, used, sources = hit
        log.info("ask source=rules intent=%s ms=%d", intent, (time.perf_counter() - t0) * 1000)
        return {"answer": text, "used": used, "sources": sources, "source": "rules", "intent": intent}
    fallback = {"answer": _t(lang, "இதற்கு இப்போது பதில் சொல்ல முடியவில்லை. இவற்றுக்கு உடனே பதில் சொல்ல முடியும்:", "I can't answer that one right now. I can answer these straight away:"),
                "used": [], "sources": [], "source": "none", "intent": None, "suggestions": SUGGESTIONS}
    if settings.fake_sarvam or not settings.sarvam_api_key or client is None:
        log.info("ask source=none reason=%s", "fake" if settings.fake_sarvam else "no_key")
        return fallback
    messages = [{"role": "system", "content": SYSTEM.format(lang="Tamil" if lang == "ta" else "English") + "\n\n" + class_context(students, summary)},
                {"role": "user", "content": pseudonymise(question, students)}]
    try:
        content, usage = await sarvam.chat(client, settings, messages, max_tokens=700, timeout=12.0, json_mode=False)
    except sarvam.SarvamError as e:
        log.warning("ask source=none llm_error=%s ms=%d", e.kind, (time.perf_counter() - t0) * 1000)
        return fallback
    content = re.sub(r"<think>.*?</think>", "", content or "", flags=re.S).strip()
    if not content:
        log.warning("ask source=none llm_error=empty")
        return fallback
    text, used = restore_names(content, students)
    sources = [_source(sc["id"]) for sc in kb()["schemes"] if sc["name"]["en"].lower() in text.lower() or sc["name"]["ta"] in text]
    log.info("ask source=llm ms=%d tokens_in=%s tokens_out=%s", (time.perf_counter() - t0) * 1000, usage.get("prompt_tokens"), usage.get("completion_tokens"))
    return {"answer": text, "used": used, "sources": sources, "source": "llm", "intent": None}
