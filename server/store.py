"""In-memory class store for class 10-B. Wiped when the server restarts; the roster is re-seeded automatically.

Everything here is what a student's phone may share with her class teacher: roll number, first name (students who
joined on the phone), path, plan progress, the kind of next step, one blocker and when she last used the app.
Never gender, community, income, documents held, answers or scheme eligibility.
"""
from __future__ import annotations

from collections import deque
from datetime import datetime, timedelta, timezone

from .kb import exam_text, guide, kb
from .schemas import SyncEvent, paths

CLASS_ID = "10B"
SCHOOL = "Government Higher Secondary School (sample)"

# The prototype's sample class: [roll, name, path id or None, tasks done of 8, blocker key or None]
CLASSMATES = [
    ["10B-01", "Anitha R", "nursing", 5, "bank"], ["10B-02", "Karthik S", "bike", 8, None], ["10B-03", "Divya M", "labtech", 3, "income"],
    ["10B-04", "Ravi P", None, 0, "nopath"], ["10B-05", "Meena K", "civil", 6, None], ["10B-06", "Arun K", "solar", 4, "aadhaar"],
    ["10B-08", "Priya V", "accounts", 7, None], ["10B-09", "Suresh T", "mobile", 2, "bank"], ["10B-10", "Kaviya B", "garment", 5, None],
    ["10B-11", "Vignesh R", None, 0, "nopath"], ["10B-12", "Deepa L", "teacher", 6, None], ["10B-13", "Manoj G", "copa", 8, None],
    ["10B-14", "Lakshmi N", "pharma", 4, "income"], ["10B-15", "Sathish V", "agri", 3, None], ["10B-16", "Revathi S", "graphic", 5, "community"],
    ["10B-17", "Balaji M", "engineering", 2, "bank"], ["10B-18", "Nandhini P", "labtech", 6, None], ["10B-19", "Gokul A", "solar", 7, None],
    ["10B-20", "Janani R", None, 0, "nopath"], ["10B-21", "Harish K", "bike", 5, None], ["10B-22", "Pavithra D", "nursing", 8, None],
    ["10B-23", "Dinesh S", "civil", 3, "income"], ["10B-24", "Sowmya T", "accounts", 6, None], ["10B-25", "Ajay V", "mobile", 1, None],
]
# Sample "days since the app was last used", so the dashboard has realistic variety. Sample data, like the names.
SEED_DAYS = {"10B-01": 1, "10B-02": 0, "10B-03": 3, "10B-04": 9, "10B-05": 2, "10B-06": 5, "10B-08": 1, "10B-09": 8, "10B-10": 0,
             "10B-11": 12, "10B-12": 2, "10B-13": 0, "10B-14": 4, "10B-15": 1, "10B-16": 6, "10B-17": 10, "10B-18": 0, "10B-19": 2,
             "10B-20": 15, "10B-21": 1, "10B-22": 0, "10B-23": 3, "10B-24": 2, "10B-25": 7}
BLOCKER_KEY = {"bank": "bank_account_aadhaar", "income": "income_certificate", "community": "community_certificate",
               "aadhaar": "aadhaar", "nopath": "no_path_yet"}
BLOCKER_ORDER = ["bank_account_aadhaar", "income_certificate", "community_certificate", "aadhaar", "no_path_yet"]
DOC_BLOCKERS = BLOCKER_ORDER[:4]
# An 8-step sample plan: week sizes and the kind of each step, in the order the phone's makePlan creates them.
SEED_WEEKS = [2, 3, 2, 1]
SEED_KINDS = ["lesson", "stories", "practice", "documents", "documents", "documents", "visit", "decide"]
INACTIVE_DAYS = 7
MAX_SEEN = 20_000


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _now() -> str:
    return _iso(datetime.now(timezone.utc))


def _parse(s: str | None) -> datetime | None:
    return datetime.fromisoformat(s.replace("Z", "+00:00")) if s else None


def _path_name(pid: str | None) -> dict | None:
    return paths()[pid]["name"] if pid else None


def _frac(s: str | None) -> tuple[int, int] | None:
    if not s or "/" not in s:
        return None
    a, b = s.split("/")
    return int(a), int(b)


def _seed_weeks(done: int) -> list[str]:
    out, left = [], done
    for size in SEED_WEEKS:
        d = min(size, left)
        out.append(f"{d}/{size}")
        left -= d
    return out


def _L(ta: str, en: str) -> dict:
    return {"ta": ta, "en": en}


def next_step(row: dict) -> dict:
    """What the student does next, in words, from the shared fields only."""
    g = guide()
    if not row["path"]:
        return g["start_steps"]["paths" if row["step"] == "paths" else "discover"]
    kind = row.get("next_task")
    if not kind:
        return _L("எல்லாப் படிகளும் முடிந்தன", "Every step is done") if _status_done(row) else g["start_steps"]["paths"]
    if kind == "documents":
        b = g["blockers"].get(row.get("blocker") or "")
        doc = b and b["doc"]
        return kb()["doc_tasks"][doc] if doc else g["documents_step"]
    return kb()["plan"][row["path"]][kind]


def _status_done(row: dict) -> bool:
    f = _frac(row.get("plan_done"))
    return bool(row["path"] and f and f[1] > 0 and f[0] >= f[1])


def derived(row: dict, now: datetime) -> dict:
    """The row as the teacher sees it: shared fields plus status, progress, next step and coming deadlines."""
    f = _frac(row.get("plan_done")) or (0, 0)
    last = _parse(row.get("last_event_at"))
    days = (now - last).days if last else None
    if not row["path"]:
        status = "not_started"
    elif _status_done(row):
        status = "done"
    elif days is not None and days >= INACTIVE_DAYS:
        status = "inactive"
    elif row.get("blocker") in DOC_BLOCKERS:
        status = "needs_help"
    else:
        status = "on_track"
    deadlines = kb()["decisions"][row["path"]] if row["path"] else [exam_text()]
    return {**row, "status": status, "done": f[0], "total": f[1], "progress_pct": round(100 * f[0] / f[1]) if f[1] else 0,
            "days_since_active": days, "next_step": next_step(row), "deadlines": deadlines}


def change_text(prev: dict | None, row: dict) -> dict | None:
    """One line for the activity feed and the student's timeline, from what changed."""
    if prev is None:
        return _L("போனில் புதிய மாணவராகச் சேர்ந்தார்", "joined on a phone as a new student")
    pname = _path_name(row["path"])
    if row["path"] and not prev["path"]:
        return _L(f"{pname['ta']} பாதையைத் தேர்ந்தெடுத்தார்", f"chose {pname['en']}")
    if row["path"] and prev["path"] and row["path"] != prev["path"]:
        return _L(f"பாதையை {pname['ta']} என மாற்றினார்", f"changed path to {pname['en']}")
    a, b = _frac(prev.get("plan_done")), _frac(row.get("plan_done"))
    if a and b and b[0] > a[0]:
        return _L(f"ஒரு திட்டப் படியை முடித்தார் ({row['plan_done']})", f"finished a plan step ({row['plan_done']})")
    if a and b and b[0] < a[0]:
        return _L(f"ஒரு திட்டப் படியைத் திரும்பத் திறந்தார் ({row['plan_done']})", f"reopened a plan step ({row['plan_done']})")
    if row.get("blocker") != prev.get("blocker"):
        blk = guide()["blockers"].get(row.get("blocker") or "")
        if blk and row.get("blocker") != "no_path_yet":
            return _L(f"தடை: {blk['label']['ta']}", f"blocker: {blk['label']['en']}")
        if not row.get("blocker"):
            return _L("தடை நீங்கியது", "blocker cleared")
    if row["step"] != prev["step"] and not row["path"]:
        if row["step"] == "paths":
            return _L("மூன்று கேள்விகளுக்கும் பதில் சொன்னார்", "answered the three questions")
        return _L("கண்டறி பகுதியைத் தொடங்கினார்", "started Discover")
    return None


class ClassStore:
    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        now = datetime.now(timezone.utc)
        rows = {}
        for roll, name, pid, done, blk in CLASSMATES:
            rows[roll] = {"roll": roll, "name": name, "step": "plan" if pid else "discover", "path": pid, "path_name": _path_name(pid),
                          "plan_done": f"{done}/8" if pid else None, "blocker": BLOCKER_KEY.get(blk) if blk else None,
                          "weeks": _seed_weeks(done) if pid else None, "next_task": (SEED_KINDS[done] if done < 8 else None) if pid else None,
                          "live": False, "new": False, "last_event_at": _iso(now - timedelta(days=SEED_DAYS[roll], hours=3))}
        rows["10B-07"] = {"roll": "10B-07", "name": "Kavya S", "step": "discover", "path": None, "path_name": None, "plan_done": None,
                          "blocker": "no_path_yet", "weeks": None, "next_task": None, "live": True, "new": False, "last_event_at": None}
        self.rows = dict(sorted(rows.items()))
        self.latest: dict[str, datetime] = {}
        self.seen: set[str] = set()
        self.history: dict[str, deque] = {}
        self.feed: deque = deque(maxlen=30)
        self.last_event: dict | None = None
        self.updated_at = _now()

    def _row(self, roll: str) -> tuple[dict, bool]:
        """A roll number that is not on the roster is a student new to the class list: add a row for them.
        It shows the first name the phone sent, or 'New student'."""
        created = roll not in self.rows
        if created:
            self.rows[roll] = {"roll": roll, "name": "New student", "step": "discover", "path": None, "path_name": None, "plan_done": None,
                               "blocker": "no_path_yet", "weeks": None, "next_task": None, "live": True, "new": True, "last_event_at": None}
            self.rows = dict(sorted(self.rows.items()))
        return self.rows[roll], created

    def apply(self, events: list[SyncEvent]) -> tuple[list[str], list[str]]:
        accepted, duplicates = [], []
        if len(self.seen) > MAX_SEEN:
            self.seen.clear()
        for ev in events:
            if ev.event_id in self.seen:
                duplicates.append(ev.event_id)
                continue
            self.seen.add(ev.event_id)
            accepted.append(ev.event_id)
            self.last_event = ev.model_dump(mode="json", exclude_unset=True)   # exactly the fields the phone sent
            prev_ts = self.latest.get(ev.student)
            if prev_ts is not None and ev.ts <= prev_ts:
                continue                       # an older snapshot arrived late: the latest ts wins
            self.latest[ev.student] = ev.ts
            row, created = self._row(ev.student)
            before = None if created else dict(row)
            row.update(step=ev.step, path=ev.path, path_name=_path_name(ev.path), plan_done=ev.plan_done, blocker=ev.blocker,
                       weeks=ev.weeks, next_task=ev.next_task, live=True, last_event_at=_iso(ev.ts))
            if row["new"]:                     # roster students keep the roster name
                row["name"] = ev.name or "New student"
            text = change_text(before, row)
            if text:
                item = {"ts": _iso(ev.ts), "roll": row["roll"], "text": text}
                self.history.setdefault(row["roll"], deque(maxlen=50)).append(item)
                self.feed.append(item)
        if accepted:
            self.updated_at = _now()
        return accepted, duplicates

    def students(self, now: datetime | None = None) -> list[dict]:
        now = now or datetime.now(timezone.utc)
        return [derived(r, now) for r in self.rows.values()]

    def summary(self, students: list[dict]) -> dict:
        g = guide()
        groups = []
        for key in BLOCKER_ORDER:
            members = [{"roll": s["roll"], "name": s["name"]} for s in students if s.get("blocker") == key]
            if members:
                b = g["blockers"][key]
                doc = kb()["docs"].get(b["doc"]) if b["doc"] else None
                groups.append({"blocker": key, "label": b["label"], "need": b["need"], "count": len(members), "students": members,
                               "action": b["action"], "where": doc["how"] if doc else None, "parent": b["parent"]})
        mix: dict[str, int] = {}
        for s in students:
            if s["path"]:
                mix[s["path"]] = mix.get(s["path"], 0) + 1
        path_mix = [{"path": pid, "name": paths()[pid]["name"], "count": n, "visit": paths()[pid]["visit"], "kind": paths()[pid]["kind"]}
                    for pid, n in sorted(mix.items(), key=lambda kv: (-kv[1], kv[0]))]
        due: dict[str, dict] = {}
        for s in students:
            for d in s["deadlines"]:
                due.setdefault(d["en"], {"text": d, "count": 0})["count"] += 1
        return {
            "total": len(students),
            "chose_path": sum(1 for s in students if s["path"]),
            "on_track": sum(1 for s in students if s["status"] in ("on_track", "done")),
            "done": sum(1 for s in students if s["status"] == "done"),
            "need_help": sum(1 for s in students if s.get("blocker") in DOC_BLOCKERS),
            "not_started": sum(1 for s in students if s["status"] == "not_started"),
            "inactive": sum(1 for s in students if s["days_since_active"] is not None and s["days_since_active"] >= INACTIVE_DAYS),
            "status_counts": {k: sum(1 for s in students if s["status"] == k) for k in g["status"]},
            "groups": groups, "path_mix": path_mix, "deadlines": list(due.values()),
        }

    def _named(self, item: dict) -> dict:
        r = self.rows.get(item["roll"])
        return {**item, "name": r["name"] if r else item["roll"]}

    def snapshot(self) -> dict:
        students = self.students()
        return {"class_id": CLASS_ID, "school": SCHOOL, "updated_at": self.updated_at, "students": students,
                "summary": self.summary(students), "feed": [self._named(x) for x in reversed(self.feed)][:12],
                "last_event": self.last_event, "status_labels": guide()["status"]}

    def detail(self, roll: str) -> dict | None:
        if roll not in self.rows:
            return None
        s = derived(self.rows[roll], datetime.now(timezone.utc))
        p = paths().get(s["path"]) if s["path"] else None
        g = guide()
        blk = g["blockers"].get(s.get("blocker") or "")
        doc = kb()["docs"].get(blk["doc"]) if blk and blk["doc"] else None
        return {**s,
                "route": p["route"] if p else None, "visit": p["visit"] if p else None, "after": p["after"] if p else None,
                "help": {"label": blk["label"], "action": blk["action"], "where": doc["how"] if doc else None, "parent": blk["parent"]} if blk else None,
                "history": list(reversed(self.history.get(roll, []))),
                "shared": g["shared"], "never": g["never"]}
