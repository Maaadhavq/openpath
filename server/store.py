"""In-memory class store for class 10-B. Wiped when the server restarts; the roster is re-seeded automatically."""
from __future__ import annotations

from datetime import datetime, timezone

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
BLOCKER_KEY = {"bank": "bank_account_aadhaar", "income": "income_certificate", "community": "community_certificate",
               "aadhaar": "aadhaar", "nopath": "no_path_yet"}
MAX_SEEN = 20_000


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _path_name(pid: str | None) -> dict | None:
    return paths()[pid]["name"] if pid else None


class ClassStore:
    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        rows = {}
        for roll, name, pid, done, blk in CLASSMATES:
            rows[roll] = {"roll": roll, "name": name, "step": "plan" if pid else "discover", "path": pid, "path_name": _path_name(pid),
                          "plan_done": f"{done}/8" if pid else None, "blocker": BLOCKER_KEY.get(blk) if blk else None,
                          "live": False, "new": False, "last_event_at": None}
        rows["10B-07"] = {"roll": "10B-07", "name": "Kavya S", "step": "discover", "path": None, "path_name": None, "plan_done": None,
                          "blocker": "no_path_yet", "live": True, "new": False, "last_event_at": None}
        self.rows = dict(sorted(rows.items()))
        self.latest: dict[str, datetime] = {}
        self.seen: set[str] = set()
        self.last_event: dict | None = None
        self.updated_at = _now()

    def _row(self, roll: str) -> dict:
        """A roll number that is not on the roster is a student new to the class list: add a row for them.
        The phone never sends a name, so the teacher sees 'New student' and the roll number."""
        if roll not in self.rows:
            self.rows[roll] = {"roll": roll, "name": "New student", "step": "discover", "path": None, "path_name": None, "plan_done": None,
                               "blocker": "no_path_yet", "live": True, "new": True, "last_event_at": None}
            self.rows = dict(sorted(self.rows.items()))
        return self.rows[roll]

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
            self.last_event = ev.model_dump(mode="json")
            prev = self.latest.get(ev.student)
            if prev is not None and ev.ts <= prev:
                continue                       # an older snapshot arrived late: the latest ts wins
            self.latest[ev.student] = ev.ts
            row = self._row(ev.student)
            row.update(step=ev.step, path=ev.path, path_name=_path_name(ev.path), plan_done=ev.plan_done, blocker=ev.blocker,
                       live=True, last_event_at=_iso(ev.ts))
        if accepted:
            self.updated_at = _now()
        return accepted, duplicates

    def snapshot(self) -> dict:
        return {"class_id": CLASS_ID, "school": SCHOOL, "updated_at": self.updated_at,
                "students": list(self.rows.values()), "last_event": self.last_event}
