"""Teacher-side knowledge: kb.json (exported from the phone's engine by scripts/export_kb.py) and guide.json (teacher
guidance written by the team). Neither contains rule code: the server never decides who is eligible."""
from __future__ import annotations

import json
from functools import lru_cache

from .config import DATA_DIR


@lru_cache(maxsize=1)
def kb() -> dict:
    return json.loads((DATA_DIR / "kb.json").read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def guide() -> dict:
    return json.loads((DATA_DIR / "guide.json").read_text(encoding="utf-8"))


def exam_text() -> dict:
    """The Class 10 public exam line: the first decision for every path in Class 10."""
    return next(iter(kb()["decisions"].values()))[0]
