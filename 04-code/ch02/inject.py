"""Chapter 2 failure injection: a logging bug drops tool calls from 10% of traces.

Annotators read what the trace shows. A reply that quotes a balance with no
lookup recorded looks invented, so they fail it. The completeness check
catches the gap before anyone reads the trace."""
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[0] / "truss"))
from truss.complete import completeness  # noqa: E402
from truss.report import per_flow, table  # noqa: E402
from truss.store import open_store  # noqa: E402
from lab import shares  # noqa: E402
from pilot_detail import ORDER, SEED, first_pass_labels, trace_view  # noqa: E402


def drop_tool_calls(ids, rate=0.10, seed=SEED):
    rng = random.Random(f"logging-bug|{seed}")
    return {t for t in ids if rng.random() < rate}


def relabel(labels, dropped):
    """What an annotator writes when the lookup is missing from the trace."""
    out = []
    for r in labels:
        if r["trace_id"] in dropped and r["verdict"] == "pass":
            r = {**r, "verdict": "fail", "note": "quoted account data with no lookup"}
        out.append(r)
    return out


def main():
    db = open_store()
    sh, _ = shares(db)
    labels = first_pass_labels(db)
    dropped = drop_tool_calls([r["trace_id"] for r in labels])
    print(f"traces with tool calls dropped by the bug: {len(dropped)} of {len(labels)}")
    print("\n-- labelled without the check --")
    print(table(relabel(labels, dropped), sh, ORDER))
    views = [trace_view(db, r["trace_id"], drop_tools=r["trace_id"] in dropped) for r in labels]
    ok, bad = completeness(views)
    print(f"\n-- completeness check: {len(bad)} incomplete, e.g. {bad[0]['trace_id']} "
          f"({bad[0]['flow']}) missing {', '.join(bad[0]['missing'])}")
    keep = {t["trace_id"] for t in ok}
    print("\n-- labelled with the check (incomplete traces refused) --")
    print(table([r for r in labels if r["trace_id"] in keep], sh, ORDER))


if __name__ == "__main__":
    main()
