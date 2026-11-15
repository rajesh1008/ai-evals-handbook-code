"""Truss 0.25 (Chapter 22): rationale. Does a judge's written critique tell you when its verdict is wrong?

The module never calls a model. It reads critiques as text and as claims: style features (length,
hedges, self-correction), the dates a critique quotes and whether each appears in the trace, the
consistency between what a critique argues and the verdict line, and a claim check that compares
what a critique asserts about the record (a cut-off date, a waiver date, inside or outside a
window) with what code computes from the same record. It tabulates each feature against verdict
error with Wilson intervals, fits an OR-rule of features to a review budget on a development set
only, scores that rule on held-out traces and on the random (production) stratum, measures a cue's
verdict shift against the flip rate of a plain repeat and how often critiques acknowledge the cue,
refuses a prompt change whose critiques got better while its verdicts got worse, and prices the
critique at scale.
"""
import re
from datetime import date

from .fields import wilson

MONTHS = ("January", "February", "March", "April", "May", "June", "July", "August", "September",
          "October", "November", "December")
_ISO = re.compile(r"\b(20\d\d-\d\d-\d\d)\b")
_LONG = re.compile(r"\b(" + "|".join(MONTHS) + r") (\d{1,2}),? (20\d\d)\b")
HEDGES = ("may", "might", "appear", "appears", "seem", "seems", "unclear", "possibly", "likely",
          "ambiguous", "potentially", "perhaps")
_HEDGE = re.compile(r"\b(" + "|".join(HEDGES) + r")\b", re.I)
_SELF = re.compile(r"\b(actually|wait|on reflection|re-?check(?:ing)?|correction|i mean)\b", re.I)


def extract_dates(text):
    """Every calendar date a text quotes, as ISO strings (ISO and 'March 4, 2027' forms)."""
    out = set(_ISO.findall(text or ""))
    for m, d, y in _LONG.findall(text or ""):
        out.add(f"{y}-{MONTHS.index(m) + 1:02d}-{int(d):02d}")
    return out


def style_features(text):
    """What a reader notices first: length, hedging and visible self-correction."""
    t = text or ""
    return {"words": len(t.split()), "hedges": len(_HEDGE.findall(t)), "self_correction": bool(_SELF.search(t))}


def dates_not_in_trace(text, trace_dates, allowed=()):
    """Dates the critique quotes that appear nowhere in the trace and are not an allowed derived date."""
    return sorted(extract_dates(text) - set(trace_dates) - set(allowed))


def consistency(implied, verdict):
    """'consistent' when what the critique argues matches the verdict line, 'contradicts' when it argues
    the opposite, 'unclear' when a reader cannot tell what it argues."""
    if implied not in ("pass", "fail"):
        return "unclear"
    if verdict not in ("pass", "fail"):
        return "unclear"
    return "consistent" if implied == verdict else "contradicts"


def cutoff(fee_date):
    """The same day and month one year earlier (29 February maps to 28 February)."""
    d = date.fromisoformat(str(fee_date)[:10])
    try:
        return d.replace(year=d.year - 1).isoformat()
    except ValueError:
        return d.replace(year=d.year - 1, day=28).isoformat()


def claim_check(claims, record):
    """Compare what a critique claims with what code computes from the record.
    claims: {"cutoff_date", "waiver_date", "window"} as extracted from the critique (None or "null" or
    "not_discussed" when the critique makes no such claim). record: {"fee_date", "waiver_date",
    "window"} computed by code ("inside", "outside" or None when there is no waiver).
    Returns {"checked": [...], "wrong": [...]}; a claim not made is neither checked nor wrong."""
    def made(v):
        return v not in (None, "", "null", "not_discussed", "none")
    checked, wrong = [], []
    if made(claims.get("cutoff_date")):
        checked.append("cutoff")
        if claims["cutoff_date"] != cutoff(record["fee_date"]):
            wrong.append("cutoff")
    if made(claims.get("waiver_date")) and record.get("waiver_date"):
        checked.append("waiver_date")
        if claims["waiver_date"] != record["waiver_date"]:
            wrong.append("waiver_date")
    if made(claims.get("window")) and record.get("window") in ("inside", "outside"):
        checked.append("window")
        if claims["window"] != record["window"]:
            wrong.append("window")
    return {"checked": checked, "wrong": wrong}


def association(flags, errors):
    """One feature against verdict error: error rate where present and where absent, Wilson 95%
    intervals, and the share of all errors that sit where the feature is present."""
    a = [e for f, e in zip(flags, errors) if f]
    b = [e for f, e in zip(flags, errors) if not f]
    ea, eb = sum(a), sum(b)
    tot = ea + eb
    return {"present": len(a), "present_err": ea, "present_rate": ea / len(a) if a else float("nan"),
            "present_ci": wilson(ea, len(a)) if a else (float("nan"), float("nan")),
            "absent": len(b), "absent_err": eb, "absent_rate": eb / len(b) if b else float("nan"),
            "absent_ci": wilson(eb, len(b)) if b else (float("nan"), float("nan")),
            "errors_covered": ea / tot if tot else float("nan"),
            "lift": (ea / len(a)) / (eb / len(b)) if a and b and eb else float("nan")}


def fit_flag_rule(rows, features, budget):
    """Greedy OR-rule on a development set: add the feature that catches the most new errors while the
    flagged share stays within budget; stop when nothing helps. rows: dicts with boolean features and
    'err'. Returns the ordered feature list and its development score."""
    chosen, flagged = [], set()
    n = len(rows)
    while True:
        best = None
        for f in features:
            if f in chosen:
                continue
            new = flagged | {i for i, r in enumerate(rows) if r.get(f)}
            if len(new) / n > budget:
                continue
            caught = sum(rows[i]["err"] for i in new)
            gain = caught - sum(rows[i]["err"] for i in flagged)
            if gain > 0 and (best is None or (gain, -len(new)) > (best[1], -best[2])):
                best = (f, gain, len(new), new)
        if best is None:
            break
        chosen.append(best[0])
        flagged = best[3]
    errs = sum(r["err"] for r in rows)
    return {"rule": chosen, "flagged": len(flagged), "n": n, "caught": sum(rows[i]["err"] for i in flagged), "errors": errs}


def evaluate_flag(rows, rule, production=None):
    """Score an OR-rule: errors caught (Wilson), share flagged, and the share flagged on the production
    stratum (rows where production(row) is True), which is what the review queue will cost."""
    fl = [any(r.get(f) for f in rule) for r in rows]
    errs = sum(r["err"] for r in rows)
    caught = sum(r["err"] for r, f in zip(rows, fl) if f)
    out = {"rule": list(rule), "n": len(rows), "errors": errs, "caught": caught,
           "catch": caught / errs if errs else float("nan"), "catch_ci": wilson(caught, errs) if errs else (float("nan"),) * 2,
           "flagged": sum(fl), "flag_share": sum(fl) / len(rows) if rows else float("nan"),
           "precision": caught / sum(fl) if sum(fl) else float("nan")}
    if production is not None:
        pr = [f for r, f in zip(rows, fl) if production(r)]
        pe = [r["err"] for r in rows if production(r)]
        out.update({"prod_n": len(pr), "prod_flagged": sum(pr), "prod_flag_share": sum(pr) / len(pr) if pr else float("nan"),
                    "prod_errors": sum(pe), "prod_caught": sum(e for e, f in zip(pe, pr) if e and f)})
    return out


def cue_effect(base, repeat, cued, acknowledged, toward="pass"):
    """A cue's effect on verdicts measured against sampling noise. base: verdicts without the cue;
    repeat: a second plain draw on the same traces; cued: verdicts with the cue; acknowledged: whether
    each cued critique mentions the cue. Returns flip rates, the shift toward `toward`, and the cue
    acknowledgment rate among flips (the explanation gap)."""
    n = len(base)
    noise = sum(a != b for a, b in zip(base, repeat))
    flips = [i for i in range(n) if base[i] != cued[i]]
    tw = sum(1 for i in flips if cued[i] == toward)
    away = sum(1 for i in flips if base[i] == toward)
    ack = sum(1 for i in flips if acknowledged[i])
    return {"n": n, "noise_flips": noise, "noise_rate": noise / n if n else float("nan"),
            "cue_flips": len(flips), "cue_rate": len(flips) / n if n else float("nan"),
            "toward": tw, "away": away, "ack_any": sum(bool(a) for a in acknowledged),
            "ack_in_flips": ack, "excess": (len(flips) - noise) / n if n else float("nan")}


def divergence(before, after, *, quality="convincing", accuracy="errors"):
    """Refuse a prompt change whose critiques read better while its verdicts got worse.
    before/after: {"convincing": mean reader score, "errors": verdict errors, "n": traces}."""
    q_up = after[quality] > before[quality]
    e_up = after[accuracy] / after["n"] > before[accuracy] / before["n"]
    reasons = []
    if e_up:
        reasons.append(f"verdict errors rose {before[accuracy]}/{before['n']} -> {after[accuracy]}/{after['n']}")
    if q_up and e_up:
        reasons.append("critiques rated more convincing while verdicts got worse")
    return {"quality_up": q_up, "errors_up": e_up, "admit": not e_up, "reasons": reasons}


def explanation_cost(out_tokens_with, out_tokens_without, calls, price_out_per_m, monthly_calls):
    """Extra output tokens a critique costs, per call and per month, at an assumed output price."""
    extra = (out_tokens_with - out_tokens_without) / calls if calls else float("nan")
    return {"extra_tokens_per_call": extra, "extra_per_call": extra * price_out_per_m / 1e6,
            "extra_per_month": extra * price_out_per_m / 1e6 * monthly_calls}


def review_cost(flag_share, monthly_verdicts, minutes, rate_per_hour):
    """Minutes and dollars a month for people to read the flagged verdicts."""
    m = flag_share * monthly_verdicts * minutes
    return {"reviews": flag_share * monthly_verdicts, "minutes": m, "dollars": m / 60 * rate_per_hour}
