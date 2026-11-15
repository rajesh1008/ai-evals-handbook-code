"""Truss 0.29 multimodal document/image/voice eval helpers (Chapter 26).

Layered capture / recognition / interpretation metrics, degradation ladders,
WER versus task success, and transcription mutation checks. Callers label
SIMULATED fixtures explicitly; this module only scores.
"""
from __future__ import annotations
from typing import Any, Sequence


DEGRADATIONS = ("clean", "blur", "skew", "glare", "crop", "compression")


def layer_outcome(capture_ok: bool, recognition_ok: bool, interpretation_ok: bool) -> dict[str, Any]:
    """Separate three layers so a capture fail is not blamed on the model."""
    return {
        "capture_ok": capture_ok,
        "recognition_ok": recognition_ok,
        "interpretation_ok": interpretation_ok,
        "end_to_end_ok": bool(capture_ok and recognition_ok and interpretation_ok),
        "first_fail": (
            "capture" if not capture_ok else
            "recognition" if not recognition_ok else
            "interpretation" if not interpretation_ok else None
        ),
    }


def field_match(pred: dict, gold: dict, keys: Sequence[str]) -> dict[str, Any]:
    """Exact match per field; money compared as rounded cents when both numeric."""
    rows = []
    ok = 0
    for k in keys:
        g, p = gold.get(k), pred.get(k)
        match = False
        if isinstance(g, (int, float)) and isinstance(p, (int, float)):
            match = round(float(g), 2) == round(float(p), 2)
        else:
            match = (g == p) and g is not None
        rows.append({"key": k, "gold": g, "pred": p, "match": match})
        ok += int(match)
    n = len(keys)
    return {"n": n, "n_match": ok, "rate": ok / n if n else 0.0, "rows": rows}


def degrade_effect(level: str, base_rate: float) -> float:
    """Deterministic extraction-rate multipliers by degradation (lab stand-in)."""
    mult = {
        "clean": 1.0,
        "blur": 0.82,
        "skew": 0.88,
        "glare": 0.75,
        "crop": 0.70,
        "compression": 0.90,
    }.get(level, 0.8)
    return max(0.0, min(1.0, base_rate * mult))


def wer(ref_words: Sequence[str], hyp_words: Sequence[str]) -> float:
    """Classic word error rate via Levenshtein on word tokens."""
    r, h = list(ref_words), list(hyp_words)
    if not r:
        return 0.0 if not h else 1.0
    dp = [[0]*(len(h)+1) for _ in range(len(r)+1)]
    for i in range(len(r)+1):
        dp[i][0] = i
    for j in range(len(h)+1):
        dp[0][j] = j
    for i in range(1, len(r)+1):
        for j in range(1, len(h)+1):
            cost = 0 if r[i-1] == h[j-1] else 1
            dp[i][j] = min(dp[i-1][j]+1, dp[i][j-1]+1, dp[i-1][j-1]+cost)
    return dp[-1][-1] / len(r)


def drop_negative_amounts(text: str) -> str:
    """Failure injection: strip leading minus/accounting negatives from money tokens."""
    import re
    # remove minus before numbers and (123.45) style
    t = re.sub(r'(?<![\w])-((?:\d+)(?:\.\d+)?)', r'\1', text)
    t = re.sub(r'\((\d+\.\d{2})\)', r'\1', t)
    return t


def voice_task_table(rows: Sequence[dict]) -> dict[str, Any]:
    """Aggregate WER mean and task-success rate; show they can disagree."""
    if not rows:
        return {"n": 0}
    wers = [r["wer"] for r in rows]
    tasks = [r["task_ok"] for r in rows]
    return {
        "n": len(rows),
        "mean_wer": sum(wers)/len(wers),
        "task_success": sum(tasks)/len(tasks),
        "low_wer_task_fail": sum(1 for r in rows if r["wer"] < 0.1 and not r["task_ok"]),
        "high_wer_task_ok": sum(1 for r in rows if r["wer"] >= 0.25 and r["task_ok"]),
    }
