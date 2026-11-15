"""Chapter 10 Lab: five reference metrics on the 200 labelled March fee traces, where they help,
where they mislead, partial credit by fact, and the role each instrument earns.
Analyses the cached real model runs (replies.py, restyle.py, extract.py); no API calls here."""
import json, sys, warnings, logging
from collections import Counter, defaultdict
from pathlib import Path
from scipy.stats import spearmanr
import fee200 as F, refs as RF, replies as RP, restyle as RS, extract as E, score as S
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "truss"))
from truss.reference import (FactKey, auc, auc_interval, gate_cost, partial_credit, recall_at_k,  # noqa: E402
                             supported_role)
warnings.filterwarnings("ignore"); logging.disable(logging.WARNING)
HERE = Path(__file__).resolve().parent
NAMES = {"exact": "exact match", "bleu": "BLEU", "rouge_l": "ROUGE-L", "bertscore": "BERTScore", "cosine": "embedding cosine"}
T = F.draw(); R = RP.load(); RR = RS.load(); X = E.load()
ids = [t["trace_id"] for t in T]; wrong = [t["verdict"] == "wrong" for t in T]
n_w, n_r = sum(wrong), len(T) - sum(wrong)
OUT = {}


def split(sc):
    return [x for x, w in zip(sc, wrong) if not w], [x for x, w in zip(sc, wrong) if w]


print("== 1. The 200 labelled traces (Chapter 8's March fee draw, MC-02 v1.1)")
print(f"traces {len(T)}: {T[0]['trace_id']} to {T[-1]['trace_id']}; verdicts {dict(Counter(t['verdict'] for t in T))}")
print(f"wrong by mode: {dict(Counter(t['mode'] for t in T if t['mode']))}")
words = [len(R[i]['reply'].split()) for i in ids]
print(f"reply texts written by {next(iter(R.values()))['model']} from each trace's facts; mean {sum(words)/len(words):.0f} words")

print("\n== 2. Five reference metrics against per-trace references (fee-refs-2027-05)")
cur = S.scored("current")
print(f"{'metric':17}{'AUC':>6}  {'95% interval':13}{'mean right':>11}{'mean wrong':>11}{'rho len':>8}{'wrong in 40 lowest':>20}{'right flagged to catch 15':>27}")
OUT["current"] = {}
for m in S.METRICS:
    sc = [cur[i][m] for i in ids]; r, w = split(sc)
    a = auc(r, w); lo, hi = auc_interval(r, w)
    rho = spearmanr(sc, words)[0] if len(set(sc)) > 1 else float("nan")
    cut, caught, fl = gate_cost(sc, wrong, 15)
    k40 = recall_at_k(sc, wrong, 40)
    OUT["current"][m] = {"auc": a, "lo": lo, "hi": hi, "rho": rho, "k40": k40, "cut": cut, "flagged": fl,
                         "right": r, "wrong": w}
    print(f"{NAMES[m]:17}{a:6.3f}  {lo:.3f}-{hi:.3f}  {sum(r)/len(r):11.3f}{sum(w)/len(w):11.3f}{rho:8.2f}{k40:>13} of {n_w}{fl:>20} of {n_r}")
print(f"reading 40 at random finds {40 * n_w / len(T):.0f} of {n_w} on average")
rt = [not w for w in wrong]
print("Spearman with being right: " + "; ".join(f"{NAMES[m]} {spearmanr([cur[i][m] for i in ids], rt)[0]:.2f}" for m in S.METRICS if m != "exact"))
ww = [x for x, w in zip(words, wrong) if w]; wr = [x for x, w in zip(words, wrong) if not w]
print(f"mean words: wrong replies {sum(ww)/len(ww):.0f}, right replies {sum(wr)/len(wr):.0f}")

print("\n== 3. Mean score by situation (cosine, BLEU)")
by = defaultdict(list)
for t in T:
    by[t["kind"]].append(t["trace_id"])
OUT["by_kind"] = {}
for k in ("right_no", "right_waive", "defer_review", "defer_tool", "defer_needless", "F_waive", "X_wrongloan", "X_invent"):
    c = sum(cur[i]["cosine"] for i in by[k]) / len(by[k]); b = sum(cur[i]["bleu"] for i in by[k]) / len(by[k])
    OUT["by_kind"][k] = {"n": len(by[k]), "cosine": c, "bleu": b}
    print(f"{k:15} n={len(by[k]):3}  cosine {c:.3f}  BLEU {b:.3f}")

print("\n== 4. Where no per-trace reference exists: one reference per question (the 'stands' answer for all)")
one = S.scored("one-ref", traces=T, replies={i: R[i]["reply"] for i in ids}) if (HERE / "out/scores-one-ref.json").exists() else None
if one is None:
    pairs = [(R[t["trace_id"]]["reply"], RF.CURRENT.text("stands", asked=t["asked"], days=t["days"])) for t in T]
    one = {i: s for i, s in zip(ids, S.compute(pairs))}
    (HERE / "out/scores-one-ref.json").write_text(json.dumps(one))
OUT["one_ref"] = {}
for m in S.METRICS:
    r, w = split([one[i][m] for i in ids]); a = auc(r, w); lo, hi = auc_interval(r, w)
    OUT["one_ref"][m] = {"auc": a, "lo": lo, "hi": hi}
    print(f"{NAMES[m]:17} AUC {a:.3f} ({lo:.3f}-{hi:.3f})")

print("\n== 5. The same replies in a candidate's longer style (restyle.py), cut-offs carried from section 2")
rs = S.scored("restyled", replies={i: RR[i]["reply"] for i in ids})
w1 = [len(RR[i]['reply'].split()) for i in ids]
print(f"mean words {sum(words)/len(words):.0f} -> {sum(w1)/len(w1):.0f}; decisions changed by the rewrite (model extraction): "
      f"{sum(X['base:'+i]['status'] != X['restyled:'+i]['status'] for i in ids)}")
OUT["restyled"] = {}
roles = {}
for m in S.METRICS:
    sc = [rs[i][m] for i in ids]; r, w = split(sc); a = auc(r, w); lo, hi = auc_interval(r, w)
    cut = OUT["current"][m]["cut"]
    fl = sum(1 for x, ww in zip(sc, wrong) if x <= cut and not ww); ca = sum(1 for x, ww in zip(sc, wrong) if x <= cut and ww)
    OUT["restyled"][m] = {"auc": a, "lo": lo, "hi": hi, "flagged": fl, "caught": ca, "right": r, "wrong": w}
    c0 = OUT["current"][m]
    roles[m] = supported_role([(c0["lo"], 15, n_w, c0["flagged"], n_r), (lo, ca, n_w, fl, n_r)])
    print(f"{NAMES[m]:17} AUC {a:.3f}  at cut {cut:.3f}: wrong caught {ca} of {n_w}, right flagged {c0['flagged']} -> {fl} of {n_r}; role {roles[m]}")
OUT["roles"] = roles

print("\n== 6. Partial credit by fact: pattern extraction against model extraction")
keys = [FactKey("status", critical=True), FactKey("loan", critical=True), FactKey("amount")]
acc = {"regex": Counter(), "model": Counter()}; conf = Counter()
pc = defaultdict(list); flagged = Counter()
bymode = Counter()
for t in T:
    i = t["trace_id"]; claimed_truth = E.CLAIMED[t["kind"]]
    rg = E.regex(R[i]["reply"]); md = X["base:" + i]
    acc["regex"][rg["status"] == claimed_truth] += 1; acc["model"][md["status"] == claimed_truth] += 1
    if rg["status"] != claimed_truth:
        conf[(t["kind"], rg["status"])] += 1
    right = RF_status = E.RIGHT_STATUS[F.RIGHT[t["kind"]]]
    truth = {"status": right, "loan": t["asked"], "amount": None if F.RIGHT[t["kind"]] == "officer_tool" else 25}
    claim = {"status": md["status"], "loan": md["loan"], "amount": md["amount"]}
    if claim["status"] == "officer":          # a deferral is a pass under MC-02 v1.1
        claim["status"] = truth["status"]; claim["amount"] = truth["amount"]
    share, crit, per = partial_credit(claim, truth, keys)
    pc[t["verdict"]].append(share)
    flagged[(t["verdict"] == "wrong", bool(crit))] += 1
    if t["verdict"] == "wrong":
        bymode[(t["mode"], ",".join(crit) or "none")] += 1
print(f"status read correctly: pattern {acc['regex'][True]} of 200, model {acc['model'][True]} of 200 "
      f"(model on the restyled replies: {sum(X['restyled:'+t['trace_id']]['status'] == E.CLAIMED[t['kind']] for t in T)} of 200)")
print("pattern misreads: " + "; ".join(f"{k[0]} read as {k[1]} {v}" for k, v in sorted(conf.items())))
for v in ("pass", "deferred", "wrong"):
    print(f"mean partial credit, {v:8}: {sum(pc[v])/len(pc[v]):.3f} (n={len(pc[v])})")
print(f"critical fact wrong: wrong replies {flagged[(True, True)]} of {n_w}; right replies {flagged[(False, True)]} of {n_r}")
print("failed critical facts by mode: " + "; ".join(f"{m} {c}: {n}" for (m, c), n in sorted(bymode.items())))
OUT["extract"] = {"regex": acc["regex"][True], "model": acc["model"][True], "conf": {f'{a}|{b}': c for (a, b), c in conf.items()},
                  "pc": {k: sum(v) / len(v) for k, v in pc.items()}, "crit_wrong": flagged[(True, True)], "crit_right": flagged[(False, True)]}
tok_in = sum(x["in_tok"] for k, x in X.items() if k.startswith("base")); tok_out = sum(x["out_tok"] for k, x in X.items() if k.startswith("base"))
print(f"model extraction cost for 200 replies: {tok_in:,} input and {tok_out:,} output tokens")
OUT["tokens"] = (tok_in, tok_out)
(HERE / "out" / "lab.json").write_text(json.dumps(OUT, default=float))

print("\n== 7. Reading in score order: replies read, lowest first, until all 15 wrong are found")
st = S.scored("stale", RF.STALE)
for name, sc in (("per-trace reference", cur), ("longer style", rs), ("build-phase key", st)):
    line = []
    for m in ("bleu", "rouge_l", "bertscore", "cosine"):
        v = [sc[i][m] for i in ids]; order = sorted(range(len(v)), key=lambda j: (v[j], j)); k = 0
        for n, j in enumerate(order, 1):
            k += wrong[j]
            if k == n_w:
                break
        line.append(f"{NAMES[m]} {n}")
    print(f"{name:20} " + "; ".join(line))
print("reading at random finds all 15 after about 188 replies on average (expected maximum position of 15 in 200)")
for name, sc in (("per-trace reference", cur), ("longer style", rs)):
    v = [sc[i]["cosine"] for i in ids]; order = sorted(range(len(v)), key=lambda j: (v[j], j))
    print(f"{name}: embedding cosine order, wrong replies among the first five read: {sum(wrong[j] for j in order[:5])}")
