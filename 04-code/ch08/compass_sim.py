"""Stand-in Compass replies for the fee replay set, and the simulated readers of the scale study.
Every number here is a stated assumption, seeded per trace ID; nothing calls a model."""
import random

# ---- candidate fee prompts (Ryan's): what each changes, as probabilities
RC = {
    "production": dict(fix_waive=0.0, length=1.00, recite=0.0),
    # rc1: read the waiver field, then explain the whole fee schedule
    "rc-0322-1": dict(fix_waive=0.85, length=1.62, recite=0.022),
    # rc2: read the waiver field; mention only fees that are on this loan
    "rc-0326-2": dict(fix_waive=0.85, length=1.31, recite=0.0),
}


def reply(r, name):
    """Outcome of one fee conversation under a release: pass, fail or deferred; plus words, terms."""
    from march import terms
    p = RC[name]
    u = r["_u_cand"]
    out = "deferred" if r["deferred"] else ("fail" if r["wrong_fee"] else "pass")
    cause = r["cause"]
    if cause == "F_waive" and u[0] < p["fix_waive"]:
        out, cause = "pass", None
    recited = out == "pass" and not r["deferred"] and u[1] < p["recite"]
    if recited:
        out, cause = "fail", "recite"
    words = r["words"] if r["deferred"] else int((r["words"] - 20) * p["length"]) + 20
    return {"outcome": out, "cause": cause, "words": words, "terms": terms(words, r["_u_terms"])}


# ---- readers (assumptions, stated in the chapter and the README)
READERS = {
    "lead": dict(miss=0.06, false_alarm=0.006, leniency=0.0),
    "Ben": dict(miss=0.10, false_alarm=0.012, leniency=0.45),
}
POLISH = 0.45      # Likert points per standard deviation of reply length, when the facts are equal
NOISE = 0.55       # reader noise on the 1-to-5 scale
LONGER = 0.68      # pairwise: chance a reader prefers the longer reply when both are equally right
TIE = 0.10         # pairwise: chance of "no preference" when both are equally right


def binary(r, who, outcome):
    g = random.Random(f"bin-{who}-{r['trace_id']}")
    p = READERS[who]
    if outcome == "deferred":
        return "deferred"
    if outcome == "fail":
        return "pass" if g.random() < p["miss"] else "fail"
    return "fail" if g.random() < p["false_alarm"] else "pass"


def likert(r, who, outcome, words, mean_w, sd_w):
    g = random.Random(f"lik-{who}-{r['trace_id']}")
    p = READERS[who]
    z = (words - mean_w) / sd_w
    latent = 4.2 - 2.1 * (outcome == "fail") - 0.8 * (outcome == "deferred") + POLISH * z + p["leniency"] \
        + g.gauss(0, NOISE)
    return int(min(5, max(1, round(latent))))


def pairwise(r, who, a, b):
    """a, b: (outcome, words) for production and candidate. Returns 'A', 'B' or 'tie'."""
    g = random.Random(f"pair-{who}-{r['trace_id']}")
    ra, rb = (a[0] != "fail"), (b[0] != "fail")
    if ra != rb:
        right = "A" if ra else "B"
        return right if g.random() < 0.93 else ("B" if right == "A" else "A")
    if g.random() < TIE:
        return "tie"
    longer = "A" if a[1] >= b[1] else "B"
    return longer if g.random() < LONGER else ("B" if longer == "A" else "A")
