"""Failure injection: a second annotator with a different definition of 'wrong fee explanation'.
Ryan Mitchell's working definition: an explanation is wrong only if it misstates the amount or the
rule; whether a fee should have been waived is a servicing decision, not an explanation.
The 100 fee traces read so far: Chapter 2's 70 first-pass traces and December's 30."""
import random
from collections import Counter

import reading as R
from truss.coding import cohen_kappa, confusion

con = R.store()
sample, hid, *_ = R.read_sample(con)
fp_rows = [r for r in R.first_pass_rows() if r["flow"] == R.F]
traces = []
for r in fp_rows:
    cause = R.CAUSE.get(r["note"]) if r["verdict"] == "fail" else None
    traces.append((r["trace_id"], "first_pass", r["verdict"], cause))
for c in sample:
    if c.flow == R.F:
        v = "pass" if c.verdict == "cannot_tell" else c.verdict   # Victor Lane's day-15 ruling
        traces.append((c.trace_id, "sample", v, hid[c.trace_id]["cause"]))
mine = [v for _, _, v, _ in traces]


def ryan(defn):
    out = []
    for t, src, v, cause in traces:
        if defn == "narrow" and cause == "F_waive":
            out.append("pass")
        else:
            out.append(v)
    return out


narrow = ryan("narrow")
agreed = ryan("agreed")
k_n, k_a = cohen_kappa(mine, narrow), cohen_kappa(mine, agreed)
fails = Counter(cause for (_, _, v, cause) in traces if v == "fail")
print(f"fee traces {len(traces)} (first pass {len(fp_rows)}, December {len(traces) - len(fp_rows)})")
print(f"your failures {mine.count('fail')}: {dict(fails)}")
print(f"Ryan, narrow definition: failures {narrow.count('fail')}, agreement "
      f"{sum(a == b for a, b in zip(mine, narrow))}/{len(mine)}, kappa {k_n:.3f}, "
      f"disagreements {dict(confusion(mine, narrow))}")
print(f"wrong-fee rate on these traces: yours {mine.count('fail') / len(mine):.1%}, Ryan's {narrow.count('fail') / len(mine):.1%}")
print(f"under Ryan's definition the fee flow has {len({c for (_, _, v, c), w in zip(traces, narrow) if w == 'fail'})} "
      f"mode(s); FM-06 disappears and its owner with it")
print(f"after the written definition: agreement {sum(a == b for a, b in zip(mine, agreed))}/{len(mine)}, kappa {k_a:.3f}")
# what overall kappa on all 53 failing notes would hide: the two waiver cases are 2 of 53
print(f"share of all 53 pooled failing notes affected: {fails['F_waive']}/53 = {fails['F_waive'] / 53:.1%}")

import json
from pathlib import Path
json.dump({"n": len(traces), "mine_fail": mine.count("fail"), "narrow_fail": narrow.count("fail"),
           "kappa_narrow": round(k_n, 3), "kappa_agreed": round(k_a, 3), "causes": dict(fails),
           "agree_narrow": sum(a == b for a, b in zip(mine, narrow))},
          open(Path(__file__).parent / "out" / "inject.json", "w"))
