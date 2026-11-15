"""Every code listing printed in Chapter 13, run against the lab's output, with the output the chapter quotes."""
import json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "truss"))
from truss.adjudication import Label, adjudicate, gold, rederive, per_label_kappa, kappa, percent_agreement

print("--- Listing 13.1: the rule refuses a disagreement without a written ruling")
a = Label("t-031682", "grace", "decline_window", "r2")
b = Label("t-031682", "ben", "draft_deferral", "r2")
try:
    adjudicate("t-031682", a, b, adjudicator="diane", guideline="r2", policy="HP-2027-04", decided_on="2027-07-12")
except ValueError as e:
    print(e)
r = adjudicate("t-031682", a, b, {"gold": "decline_window", "kind": "guideline",
               "rationale": "G-06 counts twelve months from the end of the relief"},
               adjudicator="diane", guideline="r3", policy="HP-2027-04", decided_on="2027-07-12")
print(r.kind, r.gold, r.labels, r.digest())

print("--- Listing 13.2: a policy question stays pending, and the gold set refuses it")
c = Label("t-087528", "grace", "draft_deferral", "r3"); d = Label("t-087528", "ben", "draft_deferral", "r3")
p = adjudicate("t-087528", c, d, {"gold": "draft_deferral", "kind": "policy", "escalated_to": "victor",
               "rationale": "disaster forbearance: officers exclude it, the policy text counts it"},
               adjudicator="diane", guideline="r3", policy="HP-2027-04", decided_on="2027-07-14",
               audit="policy code says decline_window")
print(p.status, p.gold)
try:
    gold([r, p])
except ValueError as e:
    print(e)

print("--- Listing 13.3: Victor's bulletin re-derives the label without a re-read")
rederive(p, "draft_deferral", policy="HP-2027-04 + HB-2027-07", ruling_id="HB-2027-07",
         decided_on="2027-07-15", why="disaster forbearance is outside the 4.3 window")
print(p.status, p.gold, p.policy, len(p.history), "old digest kept:", p.history[0]["digest"])
print(gold([r, p]))

print("--- Listing 13.4: where in the label set session one disagreed")
L = [x for x in json.load(open(HERE / "out/labels.json")) if x["guideline"] == "r2"]
by = {}
for x in L:
    by.setdefault(x["trace_id"], {})[x["annotator"]] = x["label"]
ids = sorted(t for t, v in by.items() if len(v) == 2)
G, B = [by[t]["grace"] for t in ids], [by[t]["ben"] for t in ids]
print(len(ids), f"{percent_agreement(G, B):.1%}", round(kappa(G, B), 2))
for k, v in per_label_kappa(G, B, ["ask_which_loan", "ask_income", "decline_window",
                                   "refer_to_officer", "draft_deferral"]).items():
    print(f"  {k:18s} {v:.2f}")
