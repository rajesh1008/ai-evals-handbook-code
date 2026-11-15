"""Chapter 10: score every reply against a reference set with five reference metrics.
Exact match (normalised), sentence BLEU (sacrebleu 2.6), ROUGE-L F1 (Truss), BERTScore F1
(bert-score with distilbert-base-uncased, a small model, layer default, no rescaling) and
embedding cosine (fastembed, BAAI/bge-small-en-v1.5). Scores are cached per reference set."""
import json, sys
from pathlib import Path
import fee200 as F, refs as RF, replies as RP
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "truss"))
from truss.reference import exact_match, rouge_l  # noqa: E402

HERE = Path(__file__).resolve().parent
METRICS = ("exact", "bleu", "rouge_l", "bertscore", "cosine")


def compute(pairs):
    import numpy as np, sacrebleu, logging, warnings
    warnings.filterwarnings("ignore"); logging.disable(logging.WARNING)
    from bert_score import score as bscore
    from fastembed import TextEmbedding
    hyp, ref = [p[0] for p in pairs], [p[1] for p in pairs]
    _, _, f = bscore(hyp, ref, model_type="distilbert-base-uncased", verbose=False, batch_size=32)
    emb = TextEmbedding("BAAI/bge-small-en-v1.5")
    eh, er = np.array(list(emb.embed(hyp))), np.array(list(emb.embed(ref)))
    cos = (eh * er).sum(1) / (np.linalg.norm(eh, axis=1) * np.linalg.norm(er, axis=1))
    return [{"exact": exact_match(h, r), "bleu": sacrebleu.sentence_bleu(h, [r]).score / 100,
             "rouge_l": rouge_l(h, r), "bertscore": float(f[i]), "cosine": float(cos[i])}
            for i, (h, r) in enumerate(pairs)]


def scored(name, refset=None, replies=None, traces=None):
    """Cached scores for (reply, reference) over the 200 traces, or over a supplied reply dict."""
    path = HERE / "out" / f"scores-{name}.json"
    if path.exists():
        return json.loads(path.read_text())
    traces = traces or F.draw()
    replies = replies or {k: v["reply"] for k, v in RP.load().items()}
    pairs = [(replies[t["trace_id"]], RF.ref_for(t, refset or RF.CURRENT)) for t in traces]
    rows = compute(pairs)
    out = {t["trace_id"]: s for t, s in zip(traces, rows)}
    path.write_text(json.dumps(out, indent=0))
    return out


if __name__ == "__main__":
    s = scored("current")
    s2 = scored("stale", RF.STALE)
    print(len(s), len(s2))
