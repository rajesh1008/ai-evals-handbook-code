"""Three SIMULATED judge models with documented preferences.

These are not live model calls. Each judge is a seeded scoring function over
pair features (quality gap, slot, length, family match, authorship label,
authority cue, language). The chapter says so whenever it quotes a number
from them. A runnable path for real model calls is real_judge.py.
"""
import math
import random

# Display names stay out of the chapter prose. README and captions may use them.
JUDGES = {
    "S": {  # small, same family as fee-judge-v1
        "family": "S", "quality": 1.20, "position": 0.40, "verbosity": 2.40,
        "self_pref": 0.48, "label": 0.72, "authority": 0.55, "es_scale": 0.42,
        "noise": 0.48, "tie": 0.10,
    },
    "L": {  # larger, same provider
        "family": "L", "quality": 1.65, "position": 0.14, "verbosity": 0.90,
        "self_pref": 0.58, "label": 0.78, "authority": 0.20, "es_scale": 0.78,
        "noise": 0.34, "tie": 0.08,
    },
    "X": {  # a second provider
        "family": "X", "quality": 1.30, "position": -0.30, "verbosity": 0.55,
        "self_pref": 0.18, "label": 0.32, "authority": 0.36, "es_scale": 0.70,
        "noise": 0.44, "tie": 0.10,
    },
}


def _noise(judge_id, pair_id, condition, scale):
    g = random.Random(f"{judge_id}|{pair_id}|{condition}")
    # Box-Muller, no numpy dependency
    u, v = g.random(), g.random()
    return scale * math.sqrt(-2.0 * math.log(max(u, 1e-12))) * math.cos(2 * math.pi * v)


def _side_score(cfg, pair, side, *, shown_first, length, label=None, authority=False,
                judge_id="", condition=""):
    gold = pair["gold"]
    gap = {"large": 2.3, "close": 0.55, "tied": 0.0}[pair["gap"]]
    q = cfg["quality"]
    extra = 0.0
    if pair["lang"] == "es":
        q *= cfg.get("es_scale", 1.0)
        extra = 0.55
    s = 0.0
    if gold == side:
        s += q * gap
    elif gold != "tie":
        s -= q * gap
    if shown_first:
        s += cfg["position"]
    s += cfg["verbosity"] * math.log(max(length, 20) / 100.0)
    if pair[f"gen_{side}"] == cfg["family"]:
        s += cfg["self_pref"]
    if label == "self":
        s += cfg["label"]
    elif label == "other":
        s -= cfg["label"]
    if authority:
        s += cfg["authority"]
    s += _noise(judge_id, pair["pair_id"], condition + side, cfg["noise"] + extra)
    return s


def pick(judge_id, pair, *, swap=False, pad=None, labels=None, authority=None,
         override=None):
    """Return 'A', 'B' or 'tie' in original-reply coordinates.

    swap=True presents the original B in slot A (and A in slot B). pad is
    'A', 'B' or None. labels is a dict {side: 'self'|'other'}. authority is
    the side that received the irrelevant cue. override may replace the
    config (used by the position-bias injection).
    """
    cfg = dict(override or JUDGES[judge_id])
    cfg["family"] = JUDGES[judge_id]["family"]
    len_A = pair["len_A_pad"] if pad == "A" else pair["len_A"]
    len_B = pair["len_B_pad"] if pad == "B" else pair["len_B"]
    # Which original side is shown first?
    first_side = "B" if swap else "A"
    second_side = "A" if swap else "B"
    cond = f"sw{int(swap)}|p{pad}|l{labels}|a{authority}"
    s_first = _side_score(cfg, pair, first_side, shown_first=True,
                          length=len_A if first_side == "A" else len_B,
                          label=(labels or {}).get(first_side),
                          authority=(authority == first_side),
                          judge_id=judge_id, condition=cond + "F")
    s_second = _side_score(cfg, pair, second_side, shown_first=False,
                           length=len_A if second_side == "A" else len_B,
                           label=(labels or {}).get(second_side),
                           authority=(authority == second_side),
                           judge_id=judge_id, condition=cond + "S")
    # Map back: if swap, the first slot is original B.
    scores = {"A": s_first if not swap else s_second,
              "B": s_second if not swap else s_first}
    diff = scores["A"] - scores["B"]
    if abs(diff) < cfg["tie"]:
        original_coords = "tie"
    else:
        original_coords = "A" if diff > 0 else "B"
    # The caller also needs the slot-space letter for pair_outcome.
    if swap:
        slot = {"A": "B", "B": "A", "tie": "tie"}[original_coords]
    else:
        slot = original_coords
    return {"original": original_coords, "slot": slot}


def slot_run(judge_id, pairs, swap=False, **kw):
    return [pick(judge_id, p, swap=swap, **kw)["slot"] for p in pairs]


def orig_run(judge_id, pairs, **kw):
    return [pick(judge_id, p, **kw)["original"] for p in pairs]
