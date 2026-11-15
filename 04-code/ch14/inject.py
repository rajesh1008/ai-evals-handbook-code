"""Lab failure injection: rerun weeks 2-5 with the anniversary sentence deleted from ops-1.1 and print the
Daniel-Kevin agreement matrix before and after. SIMULATED readers."""
import lab
from truss.adjudication import matrix

base, inj = lab.run(), lab.run(inject=True)
S = [s[:6] for s in lab.L]
for name, weeks in [("ops-1.1 as written", base), ("ops-1.1 without the anniversary sentence", inj)]:
    m = lab.pooled_matrix(weeks, "daniel", "kevin", {2, 3, 4, 5})
    print(f"== Daniel (rows) x Kevin (columns), weeks 2-5, {name}")
    print("           " + " ".join(f"{s:>7}" for s in S))
    for s, row in zip(S, m):
        print(f"  {s:>8} " + " ".join(f"{x:>7}" for x in row))
    print("  window x draft cell (both directions):", lab.cell(m, "decline_window", "draft_deferral"))
    wrong = [(t, wk["readings"][t]) for wk in weeks[1:] for t in wk["anniv"] if t in wk["final"] and wk["final"][t] != wk["required"][t]]
    print("  anniversary traces with a wrong final label:", len(wrong), wrong)
