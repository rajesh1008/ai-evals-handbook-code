"""Chapter 10 Try It Yourself: a sixth metric, a wrong amount, and a dropped negation."""
import json, sys, warnings, logging
from pathlib import Path
import fee200 as F, refs as RF, replies as RP, restyle as RS, score as S
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "truss"))
from truss.reference import auc, gate_cost, rouge_l, token_f1  # noqa: E402
warnings.filterwarnings("ignore"); logging.disable(logging.WARNING)
import sacrebleu  # noqa: E402
T = F.draw(); R = RP.load(); RR = RS.load(); ids = [t["trace_id"] for t in T]
wrong = [t["verdict"] == "wrong" for t in T]

print("== Try it 1: chrF as a sixth metric")
ref = {t["trace_id"]: RF.ref_for(t) for t in T}
c0 = [sacrebleu.sentence_chrf(R[i]["reply"], [ref[i]]).score / 100 for i in ids]
c1 = [sacrebleu.sentence_chrf(RR[i]["reply"], [ref[i]]).score / 100 for i in ids]
cut, caught, fl = gate_cost(c0, wrong, 15)
fl1 = sum(1 for x, w in zip(c1, wrong) if x <= cut and not w)
print(f"chrF AUC {auc([x for x, w in zip(c0, wrong) if not w], [x for x, w in zip(c0, wrong) if w]):.3f}; "
      f"cut {cut:.3f} catches 15 and flags {fl} right; on the longer replies it flags {fl1} right")

print("\n== Try it 2: a wrong amount, $25 changed to $35 in twenty right 'stands' replies")
src = [t for t in T if t["kind"] == "right_no" and "$25" in R[t["trace_id"]]["reply"]][:20]
alt = {t["trace_id"]: R[t["trace_id"]]["reply"].replace("$25", "$35") for t in src}
cur = S.scored("current"); sa = S.scored("amount-35", RF.CURRENT, alt, src)
for m in ("bleu", "rouge_l", "bertscore", "cosine"):
    d = sum(sa[t["trace_id"]][m] - cur[t["trace_id"]][m] for t in src) / len(src)
    below = sum(sa[t["trace_id"]][m] <= gate_cost([cur[i][m] for i in ids], wrong, 15)[0] for t in src)
    print(f"{m:10} mean change {d:+.4f}; below the catch-15 cut-off: {below} of 20")

print("\n== Try it 3: a dropped negation in a contract clause (the Frankfurt cameo)")
REF = "The supplier shall not be liable for indirect or consequential loss arising under this agreement."
CANDS = {"drops 'not'": "The supplier shall be liable for indirect or consequential loss arising under this agreement.",
         "right, reworded": "Indirect and consequential losses under this agreement are excluded from the supplier's liability."}
from fastembed import TextEmbedding  # noqa: E402
from bert_score import score as bscore  # noqa: E402
import numpy as np  # noqa: E402
emb = TextEmbedding("BAAI/bge-small-en-v1.5")
e = np.array(list(emb.embed([REF] + list(CANDS.values()))))
_, _, f = bscore(list(CANDS.values()), [REF] * len(CANDS), model_type="distilbert-base-uncased", verbose=False)
for j, (k, c) in enumerate(CANDS.items()):
    cos = float(e[0] @ e[j + 1] / (np.linalg.norm(e[0]) * np.linalg.norm(e[j + 1])))
    print(f"{k:16} ROUGE-L {rouge_l(c, REF):.3f}  BLEU {sacrebleu.sentence_bleu(c, [REF]).score/100:.3f}  "
          f"BERTScore {float(f[j]):.3f}  cosine {cos:.3f}")
print(f"token F1, 'fifty years' against '50 years': {token_f1('fifty years', '50 years'):.2f}")
