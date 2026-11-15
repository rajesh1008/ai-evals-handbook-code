"""A seeded stand-in for Compass, used by the Chapter 1 Lab.

Harbor Lending and Compass are fictional. This module plays the part of the
assistant so that every number printed in the chapter reproduces exactly on
the reader's machine. Each trace gets a fixed difficulty from its trace ID;
each reply is a draw whose spread depends on the sampling temperature, the
way a language model's replies do. The stand-in also reports whether its
reply matches the policy answer key, which is the job a person (Chapter 5)
or a validated judge (Chapter 18) does for the real system.
"""
import hashlib
import math
import random

PRODUCTION_TEMPERATURE = 0.7

# flow: (alpha, beta) of the per-trace difficulty distribution, and the
# failure modes a wrong reply in that flow tends to show.
FLOW_DIFFICULTY = {
    "account_question":  ((0.5, 9.0), ["wrong balance date", "missed second loan"]),
    "statement_request": ((0.4, 9.0), ["wrong statement period"]),
    "fee_explanation":   ((0.9, 6.0), ["wrong grace period", "fee not waived"]),
    "payoff_letter":     ((0.8, 6.5), ["per diem omitted", "wrong good-through date"]),
    "lien_release":      ((0.8, 6.0), ["wrong title state", "release promised early"]),
    "hardship":          ((1.2, 5.0), ["offer outside policy", "income not verified"]),
}


def _rng(*parts):
    key = "|".join(str(p) for p in parts).encode()
    return random.Random(int.from_bytes(hashlib.sha256(key).digest()[:8], "big"))


def difficulty(trace_id, flow):
    """Probability that a typical reply to this conversation is wrong."""
    (a, b), _ = FLOW_DIFFICULTY[flow]
    return _rng("difficulty", trace_id).betavariate(a, b)


def fail_probability(p, temperature):
    """Sharpen or flatten p around 0.5: temperature 0 is greedy decoding."""
    if temperature == 0:
        return 1.0 if p > 0.5 else 0.0
    logit = math.log(p / (1 - p))
    return 1 / (1 + math.exp(-logit / temperature))


def respond(trace_id, flow, temperature, run):
    """One Compass reply to a replayed conversation, checked against the key."""
    p = fail_probability(difficulty(trace_id, flow), temperature)
    draw = _rng("reply", trace_id, run, temperature)
    failed = draw.random() < p
    mode = draw.choice(FLOW_DIFFICULTY[flow][1]) if failed else None
    return {"trace_id": trace_id, "run": run, "temperature": temperature,
            "verdict": "fail" if failed else "pass", "failure_mode": mode}
