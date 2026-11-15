"""Chapter 15 failure injection: a gate that passes because its gold under-represents self-employed borrowers.

Ryan proposes a "clean" gate set: only gold cases whose income was verified from an uploaded pay document,
since the label on those can never be argued. Self-employed borrowers rarely have a pay stub, so the set
quietly loses most of them. Candidate rc-0920-1 (SIMULATED; the real probe did not show this behaviour,
see probe.py) changes the no-document path: when income is stated but no document is on file, it drafts
the deferral now and asks for the document later, which skips the 4.5 referral for self-employed borrowers.
Run: python3 inject.py"""
import json
import random
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[0] / "truss"))
import fixture as FX  # noqa: E402
from truss import flowsuite as FS  # noqa: E402

G, F = FX.gold(), FX.frame()
OFFER = FX.OFFER


def se(c):
    return {"now_self": True, "now_payroll": False}.get(c.get("stated_work"), c["self_employed"])


def flags(c):
    return FX.flags(c) + ["income documented" if c["documented"] else "no income document"]


def rc0920(c, g):
    """The candidate's first action: production's, except the no-document path for self-employed borrowers."""
    if c["gold"] == "refer_to_officer" and se(c) and not c["documented"] and c["behind"] < 3 and g.random() < 0.8:
        return OFFER
    return c["prod"]


g = random.Random(920)
cand = {c["trace_id"]: rc0920(c, g) for c in G}
doc = [c for c in G if c["documented"]]
print("== The documented-only gate set (Ryan's proposal, Mon 20 September 2027)")
for name, cases in (("traffic, 6-19 Sep", F), (f"hardship gold ({len(G)})", G), ("documented only", doc)):
    n = len(cases)
    s = sum(se(c) for c in cases)
    print(f"  {name:22s} n {n:4d}; self-employed (any route) {s:3d} ({s / n:.1%}); "
          f"self-employed referrals in gold {sum(se(c) and c.get('gold', FX.required(c)) == 'refer_to_officer' for c in cases)}")
R = {}
for name, cases in (("documented only", doc), ("stratified (all gold)", G)):
    req = {c["trace_id"]: c["gold"] for c in cases}
    base = [{c["trace_id"]: c["prod"] for c in cases}] * 2
    cr = [{c["trace_id"]: cand[c["trace_id"]] for c in cases}] * 2
    gate = FS.two_way_gate(req, base, cr)
    R[name] = {"n": len(cases), "new_offer": gate["offer"]["new"], "verdict": gate["verdict"], "acc": gate["accuracy"]}
    print(f"  gate on {name:22s} n {len(cases)}: wrong offers {gate['offer']['base'][0]} -> {gate['offer']['cand'][0]}, "
          f"stable new {len(gate['offer']['new'])}; verdict {gate['verdict'].upper()}")
newly = [c for c in G if c["trace_id"] in R["stratified (all gold)"]["new_offer"]]
print(f"  the new wrong offers by route: {dict(Counter('stated' if c.get('stated_work') else 'record' for c in newly))}; "
      f"documented among them {sum(c['documented'] for c in newly)}")
print("\n== Composition audit of the documented-only set against September traffic (min 20, at least half the traffic share)")
aud = FS.composition_audit(doc, F, flags, min_n=20, min_ratio=0.5)
for s, r in aud["segments"].items():
    if not r["pass"]:
        print(f"  FAIL {s:26s} {r['why']}")
print(f"  verdict {aud['verdict'].upper()}: {len(aud['failing'])} segments failing")
aud_all = FS.composition_audit(G, F, flags, min_n=20, min_ratio=0.5)
print(f"  same audit on all {len(G)} gold: {aud_all['verdict'].upper()}, failing {aud_all['failing']}")
R["audit_doc"] = {"verdict": aud["verdict"], "failing": aud["failing"],
                  "rows": {k: v for k, v in aud["segments"].items() if not v["pass"]}}
R["audit_all"] = {"verdict": aud_all["verdict"], "failing": aud_all["failing"]}
R["shares"] = {name: (sum(se(c) for c in cases), len(cases)) for name, cases in
               (("traffic", F), ("gold", G), ("documented", doc))}
(HERE / "out" / "inject.json").write_text(json.dumps(R, indent=1, default=str))
