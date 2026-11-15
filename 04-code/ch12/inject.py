"""Chapter 12 failure injection: forty golden cases pasted into Compass's knowledge base as worked
examples. Real model run (leak.py, cached). Shows the inflation, then the scan that catches it."""
import json
from pathlib import Path
import leak

r = leak.score()
c, l = r["clean/leaked"], r["leaked_index/leaked"]
cn, ln = r["clean/not_leaked"], r["leaked_index/not_leaked"]
print(f"model {r['model']}, {r['calls']} calls, 80 test cases, labels from policy.decide")
print(f"  the 40 leaked cases:     clean index {c['k']}/40 ({100 * c['acc']:.1f}%) -> leaked index {l['k']}/40 ({100 * l['acc']:.1f}%)")
print(f"  the 40 untouched cases:  clean index {cn['k']}/40 ({100 * cn['acc']:.1f}%) -> leaked index {ln['k']}/40 ({100 * ln['acc']:.1f}%)")
tot_c, tot_l = c["k"] + cn["k"], l["k"] + ln["k"]
print(f"  whole test set:          {tot_c}/80 ({100 * tot_c / 80:.1f}%) -> {tot_l}/80 ({100 * tot_l / 80:.1f}%): a gain no borrower would see")
print(f"  cases the leak turned from wrong to right: {r['leaked_fixed']}")
print(f"  clean run accuracy by action: { {a: f'{k}/{n}' for a, (k, n) in r['clean_by_action'].items()} }")
s = r["scan"]
print(f"leak scan over {s['docs']} knowledge-base documents (8-word shingles, containment >= 0.3, canary {leak.CANARY}):")
print(f"  leaked documents found {s['leaked_docs_found']} of 40; legitimate documents flagged {s['legit_docs_flagged']}; "
      f"smallest containment on a true hit {s['min_containment_true']}")
