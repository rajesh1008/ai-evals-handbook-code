"""Failure injection: a redaction rule that strips every amount over $999."""
import json
import re

from common import ORDER, QUOTAS, SHARES, db, evidence_by_trace, frame, save
from truss import sampling as S
from truss.redact import Redactor, evidence_report

con = db()
EV = evidence_by_trace(con)
RULE = {"amount_over_999": re.compile(r"\$\d{1,3}(?:,\d{3})+(?:\.\d{2})?")}
before, after = Redactor(), Redactor(extra_rules=RULE)
print("rule added by privacy review: redact any dollar amount of $1,000 or more")
hard = next(e for e in EV.values() if e["flow"] == "hardship" and e.get("prior_deferral_on"))
print("hardship evidence before:", json.dumps({k: before.value(v) for k, v in hard.items() if k != "flow"}))
print("hardship evidence after: ", json.dumps({k: after.value(v) for k, v in hard.items() if k != "flow"}))
rep = evidence_report(after, [(e["flow"], e) for e in EV.values()])
lost_share = 0
for f in ORDER:
    k, n = rep[f]
    lost_share += SHARES[f] * (1 - k / n)
    print(f"  {f:<18} evidence kept {k:>5}/{n:<5} {k / n:6.1%}")
smp = [t for t, _ in S.stratified(frame(con), "flow", QUOTAS)]
blind = sum(1 for t in smp if rep[EV[t]["flow"]][0] < rep[EV[t]["flow"]][1] and
            any(after.value(EV[t].get(f)) != str(EV[t].get(f)) for f in EV[t] if f != "flow"))
print(f"first-pass sample: {blind} of 300 traces lose evidence a reader needs; "
      f"{lost_share:.1%} of traffic becomes unjudgeable")
gate = all(k == n for k, n in rep.values())
print("evidence check before the rule ships:", "PASS" if gate else "BLOCK (evidence removed for "
      + ", ".join(f for f in ORDER if rep[f][0] < rep[f][1]) + ")")
save("inject", {"kept": rep, "blind_in_sample": blind, "traffic_share": lost_share})
