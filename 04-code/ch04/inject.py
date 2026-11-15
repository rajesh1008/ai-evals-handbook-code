"""Chapter 4 failure injection: a layer-three judge wired in as a layer-one
gate on every commit. The judge is a stand-in: it returns the reference
verdict except for an assumed 3% of verdicts that flip from run to run, as a
model judge at non-zero temperature does. Nothing in the code changes between
the 40 commits, so every hold below is a false alarm."""
import json
import random
import time

import harbor as H
import suite as SU
from truss.gate import decide, paired_changes
from truss.layers import Check, Cost, lint

FLIP = 0.03
RUBRIC_TOKENS, JUDGE_OUT = 1500, 400


def main():
    con = H.store()
    tok = H.tokens_by_flow(con)
    S = SU.build(tok)
    sample, _ = H.gate_sample(con)
    flow = dict(con.execute("SELECT trace_id, flow FROM traces"))
    ids = [t for t, _ in sample]
    # transcript length the judge reads: the last chat span's context, per trace
    ctxlen = dict(con.execute(
        "SELECT trace_id, MAX(json_extract(attrs,'$.input_tokens')) FROM spans WHERE kind='chat' "
        "AND trace_id IN (%s) GROUP BY 1" % ",".join("?" * len(ids)), ids))
    judge_in = sum(ctxlen.values()) / len(ids) + RUBRIC_TOKENS
    judge = Cost(input_tokens=judge_in, output_tokens=JUDGE_OUT)
    replay = sum(H.QUOTAS[f] * H.conv_dollars(tok[f]) for f in H.FLOWS)
    per_commit = judge.dollars(len(ids), H.PRICES) + replay

    S.add(Check("judge on the 300 gate traces", 3, "judge evals", "Ryan (wired into the commit hook)",
                ("commit",), None, judge))
    print("== The change: the stand-in judge added to the commit hook ==")
    print(f"judge reads {judge_in:,.0f} tokens and writes {JUDGE_OUT} per trace; 300 traces per commit")
    print("lint(suite):")
    for p in lint(S):
        print("  ", p)

    print("\n== The bill ==")
    l1 = sum(c.cost.dollars(5, H.PRICES) for c in S.at("commit") if c.layer == 1)
    print(f"layer-one checks per commit: {len([c for c in S.at('commit') if c.layer == 1])}, cost ${l1:.4f}")
    print(f"judge per commit: replay ${replay:,.2f} + judging ${judge.dollars(len(ids), H.PRICES):,.2f} = ${per_commit:,.2f}")
    n = H.RUNS_PER_MONTH["commit"]
    print(f"at {n} commits a month: ${per_commit * n:,.0f} a month; ${per_commit * n * 12:,.0f} a year")
    print(f"against two release-stage judge runs a month: ${per_commit * 2:,.0f}")
    lat = {f: tok[f]["latency_s"] for f in H.FLOWS}
    replay_min = sum(H.QUOTAS[f] * lat[f] for f in H.FLOWS) / 3 / 60
    judge_min = len(ids) * 4.0 / 3 / 60
    print(f"wall time per commit at three model slots: replay {replay_min:.1f} min + judging {judge_min:.1f} min "
          f"= {replay_min + judge_min:.0f} min (layer one: under a second)")

    print("\n== Forty commits, no change to Compass ==")
    ref = {t: (flow[t], "fail" if random.Random(f"ref|{t}").random() < 0.08 else "pass") for t in ids}
    holds, reasons_seen, strip = 0, {}, []
    t0 = time.perf_counter()
    for c in range(40):
        r = random.Random(f"judge|commit{c}")
        cand = {t: (f, ("pass" if v == "fail" else "fail") if r.random() < FLIP else v) for t, (f, v) in ref.items()}
        verdict, reasons = decide(True, 0, paired_changes(ref, cand), 0)
        strip.append(verdict)
        if verdict == "hold":
            holds += 1
            for x in reasons:
                k = x.split(":")[0]
                reasons_seen[k] = reasons_seen.get(k, 0) + 1
    print(f"commits held: {holds} of 40 ({holds / 40:.0%}); reasons by flow: {reasons_seen}")
    hp = sum(1 for f, v in ref.values() if f == "hardship" and v == "pass")
    print(f"chance a commit passes the hardship rule alone, {hp} passing hardship traces each flipping "
          f"{FLIP:.0%} of the time: {(1 - FLIP) ** hp:.3f}")
    print(f"(simulation took {time.perf_counter() - t0:.2f} s)")

    json.dump({"strip": strip, "per_commit": per_commit, "month": per_commit * n, "replay_min": replay_min,
               "judge_min": judge_min, "l1": l1}, open(H.OUT / "inject.json", "w"), indent=1)
    print("\n== The fix: the judge moves back to the release stage ==")
    S.checks[-1] = Check("judge on the 300 gate traces", 3, "judge evals", "evaluation lead", ("release",), None, judge)
    print("lint(suite):", lint(S) or "none")


if __name__ == "__main__":
    main()
