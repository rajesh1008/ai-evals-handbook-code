"""Pending live run: verbalised and log-probability confidence on real decisions.

No model is called unless you pass `run` AND a provider client is wired.
The run reuses Chapter 15's 160 authored hardship cases (facts drawn in code,
so the required action is known) and asks the decision step for its action
plus a stated confidence from 0 to 100. Where the provider returns token
log-probabilities, it also records the probability of the action token.
It then reports, per field: ECE (10 uniform bins), AUROC, Brier, the share of
replies at the modal value, and the degenerate check from truss.calibration.

The output replaces the [RESULT PENDING] sentence in Chapter 20's section on
verbalised, logprob-derived and judge-estimated confidence. Authored cases are
gate coverage, never a rate (Chapter 15), so the run reports calibration on
the authored set as such and does not restate Harbor's routing numbers.

Usage:
  python3 real_confidence.py            # prints the plan and writes a pending record
  python3 real_confidence.py run        # live run once call() is wired to a client
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "ch15"))
sys.path.insert(0, str(HERE.parent / "truss"))

ASK = ("Answer with JSON only: {\"action\": \"<one of: ask_which_loan, ask_income, decline_window, "
       "refer_to_officer, draft_deferral>\", \"confidence\": <integer 0-100, how likely your action is the one "
       "the policy requires>}.")


def call(case):  # wire a provider client here; must return (action, stated_confidence, action_token_prob or None)
    raise NotImplementedError("no provider client wired; see the module docstring")


def main():
    print("=" * 96)
    print("Pending live run: verbalised and log-probability confidence on 160 authored hardship cases")
    print("=" * 96)
    print("  command: cd 04-code/ch20 && python3 real_confidence.py run")
    print("  input:   Chapter 15 authored cases pr-001 to pr-160 (eight segments of 20), prompt rc-0917-3")
    print("  asks:    action + stated confidence 0-100; action-token probability where the provider returns it")
    print("  reports: ECE, AUROC, Brier, modal-value share and truss.calibration.degenerate per field")
    print("  [RESULT PENDING: run `cd 04-code/ch20 && python3 real_confidence.py run` after a provider client is wired]")
    if len(sys.argv) > 1 and sys.argv[1] == "run":
        from probe import cases  # Chapter 15 authored cases
        from truss.calibration import auroc, brier, degenerate, ece
        rows = []
        for c in cases():
            act, conf, p = call(c)
            rows.append({"id": c["id"], "segment": c["segment"], "right": act == c["required"],
                         "verbal": conf / 100, "logprob": p})
        y = [r["right"] for r in rows]
        for f in ("verbal", "logprob"):
            T = [r for r in rows if r[f] is not None]
            if T:
                x = [r[f] for r in T]; yy = [r["right"] for r in T]
                print(f"  {f}: n={len(T)} ECE {ece(x, yy):.4f} AUROC {auroc(x, yy):.3f} Brier {brier(x, yy):.4f} "
                      f"degenerate {degenerate(x)}")
        (HERE / "out" / "real_confidence.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    (HERE / "out").mkdir(exist_ok=True)
    (HERE / "out" / "real_confidence.json").write_text('{"status": "pending", "cases": 160}\n')


if __name__ == "__main__":
    main()
