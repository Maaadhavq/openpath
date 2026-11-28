"""The port must behave exactly like the Round 2 prototype.

Loads reference/openpath_prototype.html and the new app side by side, feeds both the same inputs,
and compares: the data, every answer combination's paths, scheme results for random profiles on
every path, the 4-week plan, and what the phone may sync.
"""
from __future__ import annotations

import itertools
import json
import random

from helpers import ROOT, open_app

EXPOSE = ("window.__PROTO = {QUESTIONS:QUESTIONS, PATHS:PATHS, recommend:recommend, evaluateAll:evaluateAll, makePlan:makePlan, "
          "nextDecision:nextDecision, relevantMissing:relevantMissing, syncPayload:syncPayload, getS:function(){ return S; }}; window.OPENPATH = {")

COMPUTE = r"""
(input) => {
  const api = input.proto ? window.__PROTO : window.OPENPATH;
  const PATHS = api.PATHS, byId = id => id ? PATHS.find(p => p.id === id) : null, out = {};
  out.paths = JSON.stringify(PATHS);
  out.questions = JSON.stringify(api.QUESTIONS);
  out.rec = input.combos.map((a, i) => {
    const r = api.recommend(a, input.profiles[i % input.profiles.length]);
    return r.picks.map(c => c.path.id).concat(r.wild ? ['*' + r.wild.path.id] : []).join(',');
  });
  out.evals = input.profiles.map(p => [null].concat(PATHS.map(x => x.id)).map(pid =>
    api.evaluateAll(p, byId(pid)).map(e => [e.s.id, e.status, e.timing, e.likely, e.missing.join('+'),
      e.trace.map(t => String(t.r)).join('/')].join(':')).join('|')));
  out.plans = input.profiles.slice(0, 80).map(p => PATHS.map(x => {
    const ev = api.evaluateAll(p, x);
    return JSON.stringify(api.makePlan(x, p, ev)) + JSON.stringify(api.nextDecision(x, p)) + api.relevantMissing(ev).join(',');
  }));
  out.sync = input.states.map(st => {
    const path = byId(st.path), plan = path ? api.makePlan(path, st.profile, api.evaluateAll(st.profile, path)) : null, done = {};
    if (plan) [].concat(...plan).forEach((t, i) => { if (st.mask[i]) done[t.id] = true; });
    if (input.proto) {
      const S = api.getS(); S.answers = st.answers; S.path = st.path; S.plan = plan; S.done = done; S.profile = st.profile;
      const p = api.syncPayload(); delete p.synced_at; delete p.student; return JSON.stringify(p);
    }
    const r = api.progressOf(st.answers, st.path, plan, done, st.profile);   // the prototype's four fields
    return JSON.stringify({ step: r.step, path: r.path, plan_done: r.plan_done, blocker: r.blocker });
  });
  return out;
}
"""

OPTS = {"home": ["accounts", "repair", "care", "farm", "craft"], "school": ["maths", "science", "computer", "language", "art"],
        "style": ["hands", "help", "numbers", "outside"]}
PATH_IDS = ["nursing", "labtech", "solar", "bike", "accounts", "mobile", "agri", "garment", "teacher", "civil", "copa", "pharma", "engineering", "graphic"]


def _profile(r: random.Random) -> dict:
    c = r.choice
    return {"gender": c([None, "girl", "boy", "third"]), "cls": c([None, 9, 10, 11, 12, 13]), "school": c([None, "govt", "aided", "private"]),
            "since6": c([None, True, False]), "medium": c([None, "tamil", "english"]),
            "community": c([None, "SC", "ST", "BC", "MBC", "DNC", "OC", "NA"]),
            "income": c([None, "lt1", "1to2.5", "2.5to4.5", "4.5to8", "gt8", "unknown"]),
            "firstGen": c([None, True, False, "unknown"]), "top20": c([None, True, False, "unknown"]),
            "docs": {d: c([None, True, False]) for d in ("aadhaar", "bank", "income", "community")}}


def _inputs() -> dict:
    r = random.Random(20261128)
    profiles = [_profile(r) for _ in range(400)]
    combos = [dict(zip(OPTS, v)) for v in itertools.product(*OPTS.values())]
    states = []
    for _ in range(300):
        answers = {q: r.choice(o) for q, o in OPTS.items() if r.random() < 0.85}
        states.append({"answers": answers, "path": r.choice([None] + PATH_IDS), "profile": _profile(r), "mask": [r.random() < 0.4 for _ in range(12)]})
    return {"profiles": profiles, "combos": combos, "states": states}


def test_port_matches_prototype(page, browser, server):
    data = _inputs()
    proto_html = (ROOT / "reference" / "openpath_prototype.html").read_text(encoding="utf-8")
    assert "window.OPENPATH = {" in proto_html
    proto_page = browser.new_page()
    proto_page.set_content(proto_html.replace("window.OPENPATH = {", EXPOSE, 1))
    proto_page.wait_for_function("window.__PROTO")
    want = proto_page.evaluate(COMPUTE, {**data, "proto": True})
    proto_page.close()

    open_app(page, server)
    got = page.evaluate(COMPUTE, {**data, "proto": False})

    assert json.loads(got["paths"]) == json.loads(want["paths"])
    assert json.loads(got["questions"]) == json.loads(want["questions"])
    assert len(want["rec"]) == 100 and got["rec"] == want["rec"]
    assert got["evals"] == want["evals"]
    assert got["plans"] == want["plans"]
    assert got["sync"] == want["sync"]
    # Kavya's demo answers, checked by hand on 28 Nov 2026.
    assert want["rec"][list(map(tuple, (c.values() for c in data["combos"]))).index(("accounts", "science", "help"))] == "nursing,labtech,accounts,*agri"
