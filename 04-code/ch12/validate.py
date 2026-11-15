"""Chapter 12: validate the 400 synthetic hardship cases before any of them is admitted.

Five checks, in order: parse, schema, internal consistency (the message against its own facts),
label (the generator's label against policy.decide), near-duplicates. Survivors get the policy's
label, never the generator's. Writes out/synth_cases.json and out/validate.json.
"""
import json, re, sys
from collections import Counter
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "truss"))
from truss.datasets import near_duplicates
from policy import decide, ACTIONS
import synth

HERE = Path(__file__).resolve().parent
ES = {"que", "mi", "el", "la", "de", "y", "no", "por", "para", "con", "tengo", "pagar", "préstamo", "estoy", "mes"}
TYPES = {"salaried", "hourly", "self_employed", "benefits", "none"}
PRODUCTS = {"auto", "personal", "small_business"}


def parse(text):
    m = re.search(r"\[.*\]", text, re.S)
    try:
        xs = json.loads(m.group(0)) if m else None
    except json.JSONDecodeError:
        return None
    return xs if isinstance(xs, list) else None


def schema_ok(c):
    try:
        assert isinstance(c["message"], str) and c["message"].strip()
        assert c["language"] in ("en", "es") and c["income_type"] in TYPES
        assert c["income_monthly"] is None or isinstance(c["income_monthly"], (int, float))
        assert isinstance(c["loans"], list) and c["loans"]
        for l in c["loans"]:
            assert re.fullmatch(r"\d{4}", str(l["last4"])) and l["product"] in PRODUCTS
            assert isinstance(l["payments_behind"], int)
        assert isinstance(c["names_loan"], bool)
        pr = c["prior_relief"]
        assert pr is None or (pr["type"] in ("deferral", "extension") and isinstance(pr["months_ago"], int))
        assert c["expected_decision"] in ACTIONS
        return True
    except (KeyError, TypeError, AssertionError, AttributeError):
        return False


def amounts(msg):
    return [float(a.replace(",", "")) for a in re.findall(r"\$\s?(\d[\d,]*(?:\.\d+)?)", msg)]


YEARS = {str(y) for y in range(1990, 2031)}


def strip_money(msg):
    return re.sub(r"\$\s?\d[\d,]*(?:\.\d+)?", " ", msg)


def consistency(c):
    """Reasons the message contradicts its own facts (empty list when consistent)."""
    msg, out = c["message"], []
    words = set(re.findall(r"[a-záéíóúñ]+", msg.lower()))
    lang = "es" if len(words & ES) >= 3 else "en"
    if lang != c["language"]:
        out.append("language")
    inc = c["income_monthly"]
    if inc and not any(abs(a - inc) <= .02 * inc for a in amounts(msg)):
        out.append("income_not_in_message")
    digits = set(re.findall(r"\b(\d{4})\b", strip_money(msg))) - YEARS
    last4 = {str(l["last4"]) for l in c["loans"]}
    if digits - last4:
        out.append("loan_digits")
    if len(c["loans"]) > 1:
        named = bool(digits & last4) or any(l["product"].replace("_", " ") in msg.lower()
                                            for l in c["loans"] if [x["product"] for x in c["loans"]].count(l["product"]) == 1)
        if c["names_loan"] and not named:
            out.append("names_loan_unsupported")
    return out


def run():
    raw = synth.load()
    cases, parsed_cells = [], 0
    for r in raw:
        xs = parse(r["text"])
        if xs is None:
            continue
        parsed_cells += 1
        for j, c in enumerate(xs):
            cases.append({"sid": f"s-{len(cases) + 1:03d}", "persona": r["persona"], "cell": r["reason_cell"], "raw": c})
    funnel = {"generated": len(cases)}
    for c in cases:
        c["schema"] = schema_ok(c["raw"]) if isinstance(c["raw"], dict) else False
        c["consistency"] = consistency(c["raw"]) if c["schema"] else None
        c["policy_label"] = decide(c["raw"]) if c["schema"] else None
        c["label_agrees"] = c["schema"] and c["policy_label"] == c["raw"]["expected_decision"]
    ok = [c for c in cases if c["schema"]]
    funnel["schema"] = len(ok)
    ok = [c for c in ok if not c["consistency"]]
    funnel["consistency"] = len(ok)
    dups = near_duplicates([c["raw"]["message"] for c in ok], threshold=0.5)
    drop = {j for _, j, _ in dups}
    for k in drop:
        ok[k]["duplicate"] = True
    admitted = [c for k, c in enumerate(ok) if k not in drop]
    funnel["deduplicated"] = len(admitted)
    for c in admitted:
        c["admitted"] = True
    sch = [c for c in cases if c["schema"]]
    disagree = Counter((c["raw"]["expected_decision"], c["policy_label"]) for c in sch if not c["label_agrees"])
    feats = lambda xs: {
        "two_loans": sum(len(c["raw"]["loans"]) > 1 for c in xs) / len(xs),
        "prior_relief": sum(c["raw"]["prior_relief"] is not None for c in xs) / len(xs),
        "edge": sum(bool(c["raw"]["prior_relief"]) and 10 <= c["raw"]["prior_relief"]["months_ago"] <= 14 for c in xs) / len(xs),
        "spanish": sum(c["raw"]["language"] == "es" for c in xs) / len(xs),
        "self_employed": sum(c["raw"]["income_type"] == "self_employed" for c in xs) / len(xs),
        "income_missing": sum(c["raw"]["income_monthly"] in (None, 0) for c in xs) / len(xs),
        "tool_error": 0.0}
    summary = {
        "cells": len(raw), "cells_parsed": parsed_cells, "funnel": funnel,
        "consistency_reasons": dict(Counter(r for c in sch for r in (c["consistency"] or [])).most_common()),
        "label_disagree": sum(not c["label_agrees"] for c in sch), "label_checked": len(sch),
        "label_disagree_pairs": {f"{a} -> {b}": n for (a, b), n in disagree.most_common()},
        "label_disagree_admitted": sum(not c["label_agrees"] for c in admitted),
        "near_duplicate_pairs": len(dups), "dup_sims": [s for _, _, s in dups],
        "policy_labels_admitted": dict(Counter(c["policy_label"] for c in admitted).most_common()),
        "generator_labels_schema": dict(Counter(c["raw"]["expected_decision"] for c in sch).most_common()),
        "features_admitted": feats(admitted), "by_persona_spanish": dict(Counter(c["persona"].split(" in ")[0] for c in admitted if c["raw"]["language"] == "es")),
        "months_ago": dict(sorted(Counter(c["raw"]["prior_relief"]["months_ago"] for c in admitted if c["raw"]["prior_relief"]).items())),
        "mean_words": sum(len(c["raw"]["message"].split()) for c in admitted) / len(admitted),
        "states_all": sum(c["raw"]["income_monthly"] not in (None, 0) and bool(amounts(c["raw"]["message"])) for c in admitted) / len(admitted),
    }
    json.dump(cases, open(HERE / "out/synth_cases.json", "w"), indent=1, ensure_ascii=False)
    json.dump(summary, open(HERE / "out/validate.json", "w"), indent=1)
    return cases, summary


if __name__ == "__main__":
    _, s = run()
    print(json.dumps({k: v for k, v in s.items() if k != "dup_sims"}, indent=1))
