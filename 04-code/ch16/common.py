"""Shared loading and scoring for the Chapter 16 analyses (no model calls)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "truss"))
from truss import judge as TJ  # noqa: E402

import agent  # noqa: E402
import fixture as F  # noqa: E402
import gen  # noqa: E402
import judges as J  # noqa: E402
import llm  # noqa: E402

DEV, TEST = F.judge_set()
BUGS, NORMAL = F.agent_set()
BY_ID = {t["trace_id"]: t for t in F.frame()}
RES = J.load_all()


def verdicts(name, ids=None, field="verdict"):
    v = RES[name]
    ids = ids if ids is not None else list(v)
    return {i: J.verdict(v[i]["text"], field) for i in ids if i in v}


def score(name, traces, truth_key="v11", res=None):
    """Score a run against labels. truth_key 'truth' is the adjudicated label (for the eval set it
    equals the v1.1 label except on tool_bug traces); 'v11' is what the card v1.1 asks."""
    res = res if res is not None else verdicts(name, [t["trace_id"] for t in traces])
    ts = [t for t in traces if t["trace_id"] in res]
    truth = [t[truth_key] for t in ts]
    pred = [res[t["trace_id"]] for t in ts]
    cm = TJ.confusion(truth, pred)
    r = TJ.rates(cm)
    r.update(cm=cm, kappa=TJ.agreement_kappa(truth, pred), n=len(ts),
             by_kind=TJ.by_kind([t["kind"] for t in ts], truth, pred), pred=dict(zip([t["trace_id"] for t in ts], pred)))
    return r


def usage(recs):
    recs = list(recs)
    u = llm.usage(recs)
    lat = [r["latency"] for r in recs]
    u.update(per_call=u["cost"] / len(recs) if recs else float("nan"),
             p50=TJ.percentile(lat, 0.5), p95=TJ.percentile(lat, 0.95),
             in_per=u["in"] / len(recs) if recs else 0, out_per=u["out"] / len(recs) if recs else 0)
    return u


def ci(lo_hi):
    return f"{lo_hi[0]:.3f} to {lo_hi[1]:.3f}"


def line(name, r):
    return (f"{name:28s} n={r['n']:3d}  TPR {r['cm']['tp']}/{r['P']} = {r['tpr']:.3f} ({ci(r['tpr_ci'])})  "
            f"TNR {r['cm']['tn']}/{r['N']} = {r['tnr']:.3f} ({ci(r['tnr_ci'])})  kappa {r['kappa']:.3f}  "
            f"abstain {r['cm']['abstain_pos'] + r['cm']['abstain_neg']}")
