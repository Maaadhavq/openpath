"""What the phone may send. Any field outside this list (community, income, gender, name, answers, ...) is a 422."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from functools import lru_cache
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

from .config import DATA_DIR

Step = Literal["discover", "paths", "plan"]
Blocker = Literal["no_path_yet", "bank_account_aadhaar", "income_certificate", "community_certificate", "aadhaar"]
PlanDone = Annotated[str, StringConstraints(pattern=r"^\d{1,2}/\d{1,2}$")]
Weeks = Annotated[list[PlanDone], Field(min_length=1, max_length=6)]   # done/total per plan week, e.g. ["2/2", "1/3"]
NextTask = Literal["lesson", "stories", "practice", "documents", "visit", "decide"]     # the kind of next step, never which document
# A new student's first name, typed on the phone: letters in any script and spaces, no markup or control characters.
FirstName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=24, pattern=r"^[^\x00-\x1f<>&{}\[\]\\]+$")]


@lru_cache(maxsize=1)
def paths() -> dict[str, dict]:
    data = json.loads((DATA_DIR / "paths.json").read_text(encoding="utf-8"))
    return {p["id"]: p for p in data}


class SyncEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9-]{8,64}$")]
    student: Annotated[str, StringConstraints(pattern=r"^10B-(0[1-9]|[1-9][0-9])$")]   # roll 01 to 99 in class 10-B
    ts: datetime
    step: Step
    path: str | None
    plan_done: PlanDone | None
    blocker: Blocker | None
    name: FirstName | None = None          # sent only for students who joined on the phone
    weeks: Weeks | None = None
    next_task: NextTask | None = None

    @field_validator("path")
    @classmethod
    def known_path(cls, v: str | None) -> str | None:
        if v is not None and v not in paths():
            raise ValueError("unknown path id")
        return v

    @field_validator("ts")
    @classmethod
    def aware(cls, v: datetime) -> datetime:
        return v if v.tzinfo else v.replace(tzinfo=timezone.utc)


class SyncBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    events: Annotated[list[SyncEvent], Field(max_length=50)]


class AskBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]
    lang: Literal["en", "ta"] = "en"
