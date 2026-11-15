"""Chapter 10 failure injection: a reference set authored from the old policy.
Score the same 200 replies against Ryan's build-phase answer key (fee-schedule-2024-01 text), then
plant ten wrong replies that quote the retired ten-day grace period and see where each key ranks them.
The ten are copies of right 'stands' replies (first ten by trace ID that say "15-day grace"), with
"15-day" changed to "ten-day"; under policy they are wrong."""
import json, random, re, sys, warnings, logging
from pathlib import Path
import fee200 as F, refs as RF, replies as RP, score as S
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "truss"))
from truss.reference import auc, auc_interval, gate_cost, recall_at_k, stale, supported_role  # noqa: E402
warnings.filterwarnings("ignore"); logging.disable(logging.WARNING)
HERE = Path(__file__).resolve().parent
T = F.draw(); R = RP.load(); ids = [t["trace_id"] for t in T]
wrong = [t["verdict"] == "wrong" for t in T]; n_w, n_r = sum(wrong), len(T) - sum(wrong)
OUT = {}

print("== Staleness check before scoring (truss.reference.stale)")
for rs in (RF.CURRENT, RF.STALE):
    why = stale(rs, {"fee-schedule-2026-03"}, ("stands", "waive", "officer", "officer_tool"))
    print(f"{rs.name} ({rs.source}, digest {rs.digest()}): {'; '.join(why) or 'current'}")

print("\n== The 200 against the stale key")
st, cur = S.scored("stale", RF.STALE), S.scored("current")
OUT["stale"] = {}
for m in S.METRICS:
    sc = [st[i][m] for i in ids]
    r = [x for x, w in zip(sc, wrong) if not w]; w = [x for x, w in zip(sc, wrong) if w]
    a = auc(r, w); lo, hi = auc_interval(r, w); _, _, fl = gate_cost(sc, wrong, 14)
    role = supported_role([(lo, 14, n_w, fl, n_r)])
    OUT["stale"][m] = {"auc": a, "lo": lo, "hi": hi, "flag14": fl, "k40": recall_at_k(sc, wrong, 40)}
    print(f"{m:10} AUC {a:.3f} ({lo:.3f}-{hi:.3f}) vs current {auc([cur[i][m] for i, x in zip(ids, wrong) if not x], [cur[i][m] for i, x in zip(ids, wrong) if x]):.3f}; "
          f"right flagged to catch 14 of 15: {fl} of {n_r}; wrong in 40 lowest {OUT['stale'][m]['k40']}; role {role}")
waive_ids = [t["trace_id"] for t in T if t["kind"] == "right_waive"]
print(f"right waiver replies, mean cosine: current key {sum(cur[i]['cosine'] for i in waive_ids)/len(waive_ids):.3f}, "
      f"stale key {sum(st[i]['cosine'] for i in waive_ids)/len(waive_ids):.3f}")

print("\n== Ten planted ten-day replies")
src = [t for t in T if t["kind"] == "right_no" and re.search(r"15-day grace", R[t["trace_id"]]["reply"])][:10]
planted = {t["trace_id"]: R[t["trace_id"]]["reply"].replace("15-day grace", "ten-day grace") for t in src}
pc = S.scored("planted-current", RF.CURRENT, planted, src); ps = S.scored("planted-stale", RF.STALE, planted, src)
OUT["planted"] = {}
for name, base, plant in (("current", cur, pc), ("stale", st, ps)):
    for m in ("bleu", "rouge_l", "bertscore", "cosine"):
        d = [plant[t["trace_id"]][m] - base[t["trace_id"]][m] for t in src]
        pool = [base[i][m] for i in ids] + [plant[t["trace_id"]][m] for t in src]
        flags = [False] * len(ids) + [True] * len(src)
        k = recall_at_k(pool, flags, 40)
        OUT["planted"][f"{name}|{m}"] = {"delta": sum(d) / len(d), "k40": k}
        print(f"{name:8}{m:10} mean change, planted minus original {sum(d)/len(d):+.4f}; planted in the 40 lowest of 210: {k} of 10")
(HERE / "out" / "inject.json").write_text(json.dumps(OUT))

print("\n== The same ten against the fee tool's value (a reference value, not a reference text)")
pat = re.compile(r"\b(\d+|ten|fifteen)-day grace")
said = [pat.search(planted[t["trace_id"]]).group(1) for t in src]
tool = F.GRACE
caught = sum(s not in (str(tool), "fifteen") for s in said)
print(f"grace period stated: {sorted(set(said))}; tool returns {tool}; mismatches {caught} of 10; "
      f"originals mismatched {sum(pat.search(R[t['trace_id']]['reply']).group(1) not in ('15', 'fifteen') for t in src)} of 10")
