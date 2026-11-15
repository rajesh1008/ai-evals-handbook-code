"""Chapter 2: Gate v0 on a candidate that adds generic 'best practice' lines
to the system prompt. The candidate's effects on each trace are simulated
from fixed, stated probabilities (below), drawn with the seed."""
import json
import random
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[0] / "truss"))
from truss.gate import decide, paired_changes  # noqa: E402
from truss.report import per_flow  # noqa: E402
from truss.rates import weighted_rate  # noqa: E402
from truss.store import open_store  # noqa: E402
from lab import shares  # noqa: E402
from pilot_detail import ORDER, SEED, first_pass_labels  # noqa: E402

GENERIC_LINES = ("Be concise. Reassure the borrower. "
                 "Do not ask the borrower for information you do not need.")
# chance a baseline pass becomes a fail, and a baseline fail becomes a pass
EFFECT = {"hardship": (0.10, 0.0), "fee_explanation": (0.03, 0.0),
          "account_question": (0.0, 0.5), "statement_request": (0.0, 0.5),
          "payoff_letter": (0.03, 0.0), "lien_release": (0.0, 0.0)}

# scripted annotator notes for traces the candidate newly fails (stated, not drawn)
CANDIDATE_NOTES = {"hardship": "offer drafted before income confirmed",
                   "fee_explanation": "fee amount given without the grace period",
                   "payoff_letter": "per diem interest omitted"}


def replay_candidate(labels, seed=SEED):
    rng = random.Random(f"candidate|{seed}")
    out = {}
    for r in labels:
        down, up = EFFECT[r["flow"]]
        v = r["verdict"]
        u = rng.random()
        if v == "pass" and u < down:
            v = "fail"
        elif v == "fail" and u < up:
            v = "pass"
        out[r["trace_id"]] = (r["flow"], v)
    return out


def main():
    labels = first_pass_labels(open_store())
    base = {r["trace_id"]: (r["flow"], r["verdict"]) for r in labels}
    cand = replay_candidate(labels)
    b_rows = per_flow(labels)
    c_rows = per_flow([{"flow": f, "verdict": v} for f, v in cand.values()])
    changes = paired_changes(base, cand)
    print(f"candidate adds: {GENERIC_LINES!r}")
    print("flow               baseline  candidate  newly fail  newly pass")
    for f in ORDER:
        print(f"{f:<18} {b_rows[f][0]:>4}/{b_rows[f][1]:<4} {c_rows[f][0]:>5}/{c_rows[f][1]:<4}"
              f" {changes[f][0]:>8} {changes[f][1]:>10}")
    kb = sum(k for k, _ in b_rows.values()); kc = sum(k for k, _ in c_rows.values())
    print(f"{'all strata':<18} {kb:>4}/300  {kc:>5}/300")
    sh = shares(open_store())[0]
    print(f"traffic-weighted   {weighted_rate(b_rows, sh):8.1%}  {weighted_rate(c_rows, sh):8.1%}")
    verdict, reasons = decide(manifest_ok=True, incomplete=0, changes=changes, new_wrong_offers=0)
    print(f"gate: {verdict.upper()}")
    for r in reasons:
        print(f"  - {r}")
    newly = sorted(t for t in base if base[t][1] == "pass" and cand[t][1] == "fail")
    print("newly failing traces (annotator note):")
    for t in newly:
        print(f"  {t}  {base[t][0]:<18} {CANDIDATE_NOTES[base[t][0]]}")
    json.dump({"base": {f: list(v) for f, v in b_rows.items()},
               "cand": {f: list(v) for f, v in c_rows.items()},
               "changes": {f: list(v) for f, v in changes.items()}},
              open(HERE / "out" / "gate.json", "w"))


if __name__ == "__main__":
    main()
