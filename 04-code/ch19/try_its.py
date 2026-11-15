"""Three Try It Yourself variations on the Chapter 19 fixture."""
from __future__ import annotations

import json
import sys
from copy import deepcopy
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "truss"))

from fixture import MODEL_PIN, NEW_RUBRIC, OLD_RUBRIC, PROMPT_V1, weeks
from truss.drift import (
    alert, change_control, track_split, version_record, week_report,
)


def head(s):
    print("\n" + "=" * 100 + "\n" + s + "\n" + "=" * 100)


WS = weeks()
history = [track_split(w["rows"]) for w in WS if w["week"] in ("w1", "w2", "w3")]
w4 = next(w for w in WS if w["week"] == "w4")
w4s = track_split(w4["rows"])

# -------------------------------------------------------------------------
head("Try It 1: watch only the frozen canary")
# A team that skipped the fresh sample would have seen week 4 as healthy.
frozen_only = w4s["frozen"]
print(f"  week-4 frozen kappa {frozen_only['kappa']:.4f}  "
      f"agree {frozen_only['agree_n']}/{frozen_only['n']}")
print(f"  week-4 pooled kappa {w4s['pooled']['kappa']:.4f}  (the number they missed)")
# Build a history of frozen-as-pooled so alert() sees a stable series.
fake_hist = []
for w in WS:
    if w["week"] not in ("w1", "w2", "w3"):
        continue
    s = track_split(w["rows"])
    fake = {"frozen": s["frozen"], "fresh": s["frozen"], "pooled": s["frozen"], "gap": 0.0}
    fake_hist.append(fake)
fake_this = {"frozen": frozen_only, "fresh": frozen_only, "pooled": frozen_only, "gap": 0.0}
a_frozen = alert(fake_hist, fake_this)
print(f"  frozen-only alert: verdict {a_frozen['verdict']}  "
      f"diagnostic {a_frozen['diagnostic']}  drop {a_frozen['drop']}")
print("  The policy change is invisible if the gold never moves.")

# -------------------------------------------------------------------------
head("Try It 2: a silent model swap the frozen canary does catch")
# Simulate a more lenient judge: every original false negative becomes a
# true positive? No - lenient means more pass, so gold-fail traces that
# were caught (TP) start being missed (FN), and some gold-pass stay pass.
# Simpler plant: flip 8 of the frozen TN (correct pass) to FP? That's
# stricter. Lenient = flip TP to FN (miss more fails).
#
# Take week-3 rows and flip the judge toward pass on 8 frozen traces
# that were TP (fail/fail -> fail/pass). Also flip 10 fresh TPs the same
# way. Frozen drops; fresh drops; diagnostic = both / judge_moved if we
# also... both drop means diagnostic "both". To get judge_moved we need
# frozen to drop and fresh to hold, which is the complementary lesson
# only if the mix didn't change. A model swap hits both tracks.
#
# That's the point: a model swap moves frozen AND fresh. A policy change
# moves fresh and leaves frozen. Try It 2 shows the other signature.

w3 = next(w for w in WS if w["week"] == "w3")
swapped = []
flipped_frozen = 0
flipped_fresh = 0
for r in w3["rows"]:
    q = dict(r)
    if q["truth"] == "fail" and q["pred"] == "fail":
        if q["track"] == "frozen" and flipped_frozen < 6:
            q["pred"] = "pass"
            flipped_frozen += 1
        elif q["track"] == "fresh" and flipped_fresh < 8:
            q["pred"] = "pass"
            flipped_fresh += 1
    swapped.append(q)
sw = track_split(swapped)
a_swap = alert(history, sw)
print(f"  planted flips: frozen {flipped_frozen}  fresh {flipped_fresh}  "
      "(true fails the lenient model now misses)")
print(f"  frozen kappa {sw['frozen']['kappa']:.4f}  "
      f"fresh kappa {sw['fresh']['kappa']:.4f}  "
      f"pooled kappa {sw['pooled']['kappa']:.4f}")
print(f"  alert verdict {a_swap['verdict']}  diagnostic {a_swap['diagnostic']}")
print(f"  frozen drop {a_swap['frozen_drop']:.4f}  fresh drop {a_swap['fresh_drop']:.4f}")
print("  Both tracks moved: the judge moved, not the policy.")

# -------------------------------------------------------------------------
head("Try It 3: a rubric wording change moves the pass rate as far as the swap")
# Compare two interventions on the same week-3 pooled traces:
# (a) the model swap above (already computed)
# (b) a rubric edit that adds a generosity line: treat it as flipping the
#     same number of verdicts toward pass on the pooled set.
w3s = track_split(w3["rows"])
before_fail = w3s["pooled"]["judge_fail"] / w3s["pooled"]["n"]
swap_fail = sw["pooled"]["judge_fail"] / sw["pooled"]["n"]
# Rubric edit: same total extra passes as the swap (flipped_frozen + flipped_fresh).
n_flip = flipped_frozen + flipped_fresh
edited = []
left = n_flip
for r in w3["rows"]:
    q = dict(r)
    if left and q["truth"] == "fail" and q["pred"] == "fail":
        q["pred"] = "pass"
        left -= 1
    edited.append(q)
ed = week_report([r["truth"] for r in edited], [r["pred"] for r in edited])
edit_fail = ed["judge_fail"] / ed["n"]
print(f"  week-3 judge fail rate before either change: {before_fail:.3f} "
      f"({w3s['pooled']['judge_fail']}/{w3s['pooled']['n']})")
print(f"  after model swap: {swap_fail:.3f} ({sw['pooled']['judge_fail']}/{sw['pooled']['n']})")
print(f"  after a generosity-line rubric edit of the same {n_flip} verdicts: "
      f"{edit_fail:.3f} ({ed['judge_fail']}/{ed['n']})")
print(f"  kappa after swap {sw['pooled']['kappa']:.4f}; "
      f"after rubric edit {ed['kappa']:.4f}")
v_before = version_record(
    "fee-judge-v1", PROMPT_V1, MODEL_PIN, OLD_RUBRIC,
    "HP-2027-04", "MC-02 v1.1", "decide")
generous = deepcopy(OLD_RUBRIC)
generous.append({"id": "generous",
                 "text": "When the borrower is on a hardship plan, prefer pass."})
v_edit = version_record(
    "fee-judge-v1-generous", PROMPT_V1, MODEL_PIN, generous,
    "HP-2027-04", "MC-02 v1.1", "decide")
print(f"  digest before {v_before['digest']}; after the extra line {v_edit['digest']}")
gate = change_control(OLD_RUBRIC, generous, frozen_ids={c["id"] for c in OLD_RUBRIC})
print(f"  change-control on the extra line (addition only): {gate['verdict']}  "
      f"added {gate['added']}")
print("  Additions pass the freeze; they still need a labelled revalidation "
      "before anyone serves them.")

out = {
    "try1": {"frozen_kappa": frozen_only["kappa"], "pooled_kappa": w4s["pooled"]["kappa"],
             "frozen_only_alert": a_frozen},
    "try2": {"flipped_frozen": flipped_frozen, "flipped_fresh": flipped_fresh,
             "split": sw, "alert": a_swap},
    "try3": {"before_fail": before_fail, "swap_fail": swap_fail, "edit_fail": edit_fail,
             "n_flip": n_flip, "edit_kappa": ed["kappa"],
             "digest_before": v_before["digest"], "digest_after": v_edit["digest"],
             "gate": gate["verdict"]},
}
(HERE / "out").mkdir(exist_ok=True)
(HERE / "out" / "try_its.json").write_text(json.dumps(out, indent=2, default=str) + "\n")
print("\nwrote out/try_its.json")
