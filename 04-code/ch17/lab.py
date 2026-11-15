"""Chapter 17 lab: the bias battery on three SIMULATED judges.

Prints every number the chapter uses and writes out/lab.json. No model is
called. Real-model runs go through real_judge.py and are marked pending.
"""
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "truss"))

from fixture import pairs, describe
from judges import orig_run, slot_run, JUDGES
from truss.bias import (
    position_calls, position_summary, mitigate_position, flip_summary,
    self_pref_summary, label_effect, rubric_anchor, segment_table,
    majority, correlated_errors, pairwise_agree, evaluate_tests, disqualify,
)

OUT = {}
PS = pairs()


def head(s):
    print("\n" + "=" * 100 + "\n" + s + "\n" + "=" * 100)


def pct(x):
    return "nan" if x != x else f"{100 * x:.1f}%"


def show_pos(name, s):
    print(f"  {name}: n={s['parsed']}  position {s['position']}/{s['parsed']} "
          f"= {pct(s['position_rate'])}  (Wilson {pct(s['position_ci'][0])} to "
          f"{pct(s['position_ci'][1])})  consistency {pct(s['consistency'])}  "
          f"original {s['original']} other {s['other']} tie {s['tie']}")


head("1. Fixture (SIMULATED): 200 fee-explanation pairs, seed 2026")
d = describe(PS)
print(f"pairs {d['first']} to {d['last']}: {d['n']}")
print("gap:", d["gap"], " lang:", d["lang"], " gold:", d["gold"])
print(f"quality-matched (tied) pairs: {d['tied']}; mixed-family pairs: {d['mixed_family']}")
OUT["fixture"] = d


head("2. Position bias: each pair judged twice, slots swapped")
pos = {}
for j in ("S", "L", "X"):
    first = slot_run(j, PS, swap=False)
    swapped = slot_run(j, PS, swap=True)
    calls = position_calls(first, swapped)
    s = position_summary(calls)
    gold = [p["gold"] for p in PS]
    mit = mitigate_position(first, swapped, gold=gold)
    # accuracy of the single-order (first) run, original coords
    orig = orig_run(j, PS)
    scored = [(o, g) for o, g in zip(orig, gold) if g != "tie"]
    acc = sum(o == g for o, g in scored) / len(scored)
    pos[j] = {**s, "mitigation": mit, "single_acc": acc,
              "single_n": len(scored)}
    show_pos(f"J-{j}", s)
    print(f"     single-order accuracy {pct(acc)} on {len(scored)} pairs with a better reply; "
          f"after dual-order mitigation kept {mit['n']}, accuracy {pct(mit.get('accuracy', float('nan')))} "
          f"on {mit.get('n_scored', 0)}")
    # by gap
    for gap in ("large", "close", "tied"):
        idx = [i for i, p in enumerate(PS) if p["gap"] == gap]
        sub = position_summary([calls[i] for i in idx])
        pos[j][f"gap_{gap}"] = sub
        print(f"     gap={gap} n={sub['parsed']}: position {pct(sub['position_rate'])}")
OUT["position"] = {j: {k: v for k, v in pos[j].items() if k != "mitigation"} | {
    "mit_n": pos[j]["mitigation"]["n"],
    "mit_acc": pos[j]["mitigation"].get("accuracy"),
    "mit_scored": pos[j]["mitigation"].get("n_scored"),
} for j in pos}


head("3. Verbosity bias: pad reply A by 30% (courtesy filler, no new facts)")
verb = {}
for j in ("S", "L", "X"):
    base = orig_run(j, PS)
    padded = orig_run(j, PS, pad="A")
    toward = ["A"] * len(PS)
    f = flip_summary(base, padded, toward=toward)
    verb[j] = f
    print(f"  J-{j}: flipped {f['flipped']}/{f['n']} = {pct(f['flip_rate'])}  "
          f"(Wilson {pct(f['flip_ci'][0])} to {pct(f['flip_ci'][1])}); "
          f"toward padded A {f['toward']}/{f['flipped'] or 0} = {pct(f['toward_rate'])}")
    idx = [i for i, p in enumerate(PS) if p["quality_matched"]]
    ft = flip_summary([base[i] for i in idx], [padded[i] for i in idx],
                      toward=[toward[i] for i in idx])
    verb[j]["tied"] = ft
    print(f"     on {len(idx)} tied-quality pairs: flipped {ft['flipped']}/{ft['n']} "
          f"= {pct(ft['flip_rate'])}; toward padded {pct(ft['toward_rate'])}")
    # Harm: pad the worse reply (gold known) and count flips onto it.
    harm_base, harm_pad, harm_toward = [], [], []
    for p in PS:
        if p["gold"] not in ("A", "B"):
            continue
        worse = "B" if p["gold"] == "A" else "A"
        harm_base.append(orig_run(j, [p])[0])
        harm_pad.append(orig_run(j, [p], pad=worse)[0])
        harm_toward.append(worse)
    fh = flip_summary(harm_base, harm_pad, toward=harm_toward)
    verb[j]["harm"] = fh
    print(f"     padding the worse reply: flipped {fh['flipped']}/{fh['n']} = "
          f"{pct(fh['flip_rate'])}; onto the worse reply {fh['toward']}/{fh['flipped'] or 0} "
          f"= {pct(fh['toward_rate'])}")
OUT["verbosity"] = {j: {"n": verb[j]["n"], "flipped": verb[j]["flipped"],
                        "flip_rate": verb[j]["flip_rate"], "flip_ci": verb[j]["flip_ci"],
                        "toward": verb[j]["toward"], "toward_rate": verb[j]["toward_rate"],
                        "tied": {k: verb[j]["tied"][k] for k in
                                 ("n", "flipped", "flip_rate", "toward", "toward_rate")},
                        "harm": {k: verb[j]["harm"][k] for k in
                                 ("n", "flipped", "flip_rate", "toward", "toward_rate")}}
                    for j in verb}


head("4. Self-preference: family match on quality-matched mixed-family pairs")
# Build a dedicated tied-quality view: use the 20 tied pairs PLUS treat large/close
# gold-known pairs as unmatched (quality_matched False) so they are skipped.
# To have more matched pairs, also construct "as-if-tied" rows? No: only the 20
# tied pairs are honestly matched. That's few for a rate. Alternative: use ALL
# pairs but mark quality_matched=True only for tied, and ALSO run a second
# measurement that uses every pair where gold is known and report separately
# (the confound the papers warn about).
sp = {}
for j in ("S", "L", "X"):
    picks = orig_run(j, PS)
    rows_tied = []
    rows_all = []
    for p, pick in zip(PS, picks):
        rec = {"judge_family": j, "gen_A": p["gen_A"], "gen_B": p["gen_B"],
               "pick": pick, "gold": p["gold"]}
        rows_all.append({**rec, "quality_matched": True})  # un-controlled (confounded)
        rows_tied.append({**rec, "quality_matched": p["quality_matched"]})
    tied = self_pref_summary(rows_tied)
    raw = self_pref_summary(rows_all)
    sp[j] = {"tied": tied, "raw": raw}
    print(f"  J-{j} gold-controlled (tied pairs, mixed family): used {tied['used']} "
          f"decisive {tied['decisive']} own {tied['own']} other {tied['other']} "
          f"self_pref {tied['self_pref'] if tied['self_pref']==tied['self_pref'] else float('nan'):.3f} "
          f"own_rate {pct(tied['own_rate'])}")
    print(f"     uncontrolled (every mixed-family pair): used {raw['used']} "
          f"decisive {raw['decisive']} own {raw['own']} other {raw['other']} "
          f"self_pref {raw['self_pref']:.3f} own_rate {pct(raw['own_rate'])}")
OUT["self_pref"] = {j: {"tied": sp[j]["tied"], "raw": sp[j]["raw"]} for j in sp}


head("5. Authorship labels: same replies, a self or other tag, no model name")
lab = {}
for j in ("S", "L", "X"):
    blind = orig_run(j, PS)
    # Half the pairs get a 'self' tag on A; half get an 'other' tag on A.
    tagged, tags = [], []
    for i, p in enumerate(PS):
        kind = "self" if i % 2 == 0 else "other"
        tags.append((kind, "A"))
        tagged.append(orig_run(j, [p], labels={"A": kind})[0])
    e = label_effect(blind, tagged, tags)
    lab[j] = e
    print(f"  J-{j}: flipped {e['flipped']}/{e['n']} = {pct(e['flip_rate'])}; "
          f"toward self-tag {e['toward_self']}, away from other-tag {e['away_other']}; "
          f"directional {e['directional']}/{e['n']} = {pct(e['label_shift'])}")
OUT["labels"] = {j: {k: lab[j][k] for k in
                     ("n", "flipped", "flip_rate", "flip_ci", "toward_self",
                      "away_other", "directional", "label_shift")} for j in lab}


head("6. Irrelevant authority cue: prepend a staff-newsletter attribution to A")
auth = {}
for j in ("S", "L", "X"):
    base = orig_run(j, PS)
    cued = orig_run(j, PS, authority="A")
    toward = ["A"] * len(PS)
    f = flip_summary(base, cued, toward=toward)
    auth[j] = f
    print(f"  J-{j}: flipped {f['flipped']}/{f['n']} = {pct(f['flip_rate'])}; "
          f"toward the cued side {f['toward']}/{f['flipped'] or 0} = {pct(f['toward_rate'])}")
OUT["authority"] = {j: {k: auth[j][k] for k in
                        ("n", "flipped", "flip_rate", "flip_ci", "toward", "toward_rate")}
                    for j in auth}


head("7. Rubric anchoring: three MC-02 options, two orders")
# Pointwise stand-in: the judge's original pick is mapped to pass/fail/cannot_tell
# via gold and the pick, then we re-present the options in two orders and let
# a slot preference pull the option.
# Simpler honest simulation: take the judge's private preference among
# (pass, fail, cannot_tell) from whether orig pick matches gold, then add the
# same position coefficient as a first-slot bonus when scoring options.
def rubric_picks(judge_id, orders):
    recs = []
    cfg = JUDGES[judge_id]
    orig = orig_run(judge_id, PS)
    for p, pick in zip(PS, orig):
        # content preference: the option that matches gold (pass if pick==gold
        # or gold is tie and pick is not a wild fail...). For a fee judge,
        # gold A/B names the better reply; pointwise on reply A:
        # if gold==A the right option is pass; if gold==B, fail; if tie, pass.
        # We'll grade reply A as the item.
        content = "pass" if p["gold"] in ("A", "tie") else "fail"
        h = int(hashlib.md5(f"{p['pair_id']}|{judge_id}".encode()).hexdigest(), 16)
        if p["gap"] == "close" and (h % 12 == 0):
            content = "cannot_tell"
        content_w = {"large": 1.70, "close": 0.45, "tied": 0.12}[p["gap"]]
        for order in orders:
            best, best_s = None, -1e9
            for slot, opt in enumerate(order):
                s = content_w if opt == content else 0.0
                if slot == 0:
                    s += 0.62 if cfg["position"] >= 0 else 0.18
                if slot == len(order) - 1 and cfg["position"] < 0:
                    s += 0.55  # J-X leans to the last option
                s += _rubric_noise(judge_id, p["pair_id"], order, opt)
                if s > best_s:
                    best, best_s = opt, s
            recs.append((p["pair_id"], order, best))
    return recs


def _rubric_noise(j, pid, order, opt):
    import random as _r
    g = _r.Random(f"rub|{j}|{pid}|{order}|{opt}")
    return (g.random() - 0.5) * 0.35


ORDERS = (("pass", "fail", "cannot_tell"), ("cannot_tell", "fail", "pass"))
rub = {}
for j in ("S", "L", "X"):
    recs = rubric_picks(j, ORDERS)
    a = rubric_anchor(recs, n_options=3)
    rub[j] = a
    print(f"  J-{j}: n={a['n']} first-slot {a['first']}/{a['n']} = {pct(a['first_rate'])} "
          f"(excess {a['excess_first']:+.3f} vs 1/3); last-slot {pct(a['last_rate'])}; "
          f"content consistency {a['content_consistent']}/{a['items']} = "
          f"{pct(a['content_consistency'])}")
OUT["rubric"] = {j: {k: (dict(v) if isinstance(v, dict) else v)
                     for k, v in rub[j].items()} for j in rub}


head("8. Segment bias: English vs Spanish position consistency and single-order accuracy")
seg = {}
for j in ("S", "L", "X"):
    first = slot_run(j, PS, swap=False)
    swapped = slot_run(j, PS, swap=True)
    calls = position_calls(first, swapped)
    orig = orig_run(j, PS)
    rows_cons = []
    rows_acc = []
    for i, p in enumerate(PS):
        rows_cons.append({"segment": p["lang"],
                          "success": calls[i] != "position" and calls[i] != "unparsed"})
        if p["gold"] != "tie":
            rows_acc.append({"segment": p["lang"], "success": orig[i] == p["gold"]})
    tc, ta = segment_table(rows_cons), segment_table(rows_acc)
    seg[j] = {"consistency": tc, "accuracy": ta}
    print(f"  J-{j} consistency by language: en {tc['en']['k']}/{tc['en']['n']} = "
          f"{pct(tc['en']['rate'])}; es {tc['es']['k']}/{tc['es']['n']} = "
          f"{pct(tc['es']['rate'])}; gap {pct(tc['_max_gap'])}")
    print(f"     accuracy by language: en {ta['en']['k']}/{ta['en']['n']} = "
          f"{pct(ta['en']['rate'])}; es {ta['es']['k']}/{ta['es']['n']} = "
          f"{pct(ta['es']['rate'])}; gap {pct(ta['_max_gap'])}")
OUT["segment"] = {}
for j in seg:
    OUT["segment"][j] = {
        "consistency": {s: seg[j]["consistency"][s] for s in ("en", "es", "_max_gap") if s in seg[j]["consistency"] or s == "_max_gap"},
        "accuracy": {s: seg[j]["accuracy"][s] for s in ("en", "es", "_max_gap")},
    }
    OUT["segment"][j]["consistency"]["_max_gap"] = seg[j]["consistency"]["_max_gap"]
    OUT["segment"][j]["accuracy"]["_max_gap"] = seg[j]["accuracy"]["_max_gap"]


head("9. Battery report and admission (Harbor thresholds)")
reports = {}
for j in ("S", "L", "X"):
    metrics = {
        "position_rate": pos[j]["position_rate"],
        "verbosity_flip": verb[j]["flip_rate"],
        "self_pref": abs(sp[j]["tied"]["self_pref"]) if sp[j]["tied"]["self_pref"] == sp[j]["tied"]["self_pref"] else 0.0,
        "label_shift": lab[j]["label_shift"],
        "authority_flip": auth[j]["flip_rate"],
        "rubric_slot": max(0.0, rub[j]["excess_first"],
                           rub[j]["last_rate"] - (1 / rub[j]["n_options"])),
        "segment_gap": seg[j]["accuracy"]["_max_gap"],
    }
    rows = evaluate_tests(metrics)
    adm_order = disqualify(rows, role="order")
    adm_pw = disqualify(rows, role="pairwise")
    adm_pt = disqualify(rows, role="pointwise")
    reports[j] = {"metrics": metrics, "rows": rows,
                  "order": adm_order, "pairwise": adm_pw, "pointwise": adm_pt}
    print(f"  J-{j}:")
    for r in rows:
        print(f"     {r['name']:16s} {r['value']:.3f}  {r['verdict']}  "
              f"(flag {r['flag']}, fail {r['fail']})")
    print(f"     admit order={adm_order['admit']} {adm_order['reasons'] or '—'}  "
          f"flags={adm_order['flags']} fails={adm_order['fails']}")
    print(f"     admit pairwise={adm_pw['admit']} {adm_pw['reasons'] or '—'}; "
          f"pointwise={adm_pt['admit']} {adm_pt['reasons'] or '—'}")
OUT["battery"] = reports


head("10. Panel of three: majority and correlated errors (same-family S+L vs X)")
picks = {j: orig_run(j, PS) for j in ("S", "L", "X")}
gold = [p["gold"] for p in PS]
maj = majority([picks["S"], picks["L"], picks["X"]])
# accuracy of each and of the majority, ignoring ties in gold
def acc(pred):
    scored = [(a, g) for a, g in zip(pred, gold) if g != "tie"]
    return sum(a == g for a, g in scored), len(scored)

panel = {"acc": {}}
for name, pred in (("S", picks["S"]), ("L", picks["L"]), ("X", picks["X"]), ("majority", maj)):
    k, n = acc(pred)
    panel["acc"][name] = {"k": k, "n": n, "rate": k / n}
    print(f"  {name:9s} {k}/{n} = {pct(k / n)}")
panel["agree_SL"] = pairwise_agree(picks["S"], picks["L"])
panel["agree_SX"] = pairwise_agree(picks["S"], picks["X"])
panel["agree_LX"] = pairwise_agree(picks["L"], picks["X"])
print(f"  pairwise agreement: S-L {pct(panel['agree_SL']['rate'])} "
      f"({panel['agree_SL']['agree']}/{panel['agree_SL']['n']}); "
      f"S-X {pct(panel['agree_SX']['rate'])}; L-X {pct(panel['agree_LX']['rate'])}")
for a, b, lab_ in (("S", "L", "SL"), ("S", "X", "SX"), ("L", "X", "LX")):
    c = correlated_errors(picks[a], picks[b], gold)
    panel[f"corr_{lab_}"] = c
    print(f"  shared mistakes {a}-{b}: both {c['both']}/{c['n']} = {pct(c['both_rate'])}; "
          f"both|either {pct(c['both_given_either'])}; vs independence {c['indep_both']:.3f}; "
          f"ratio {c['ratio']:.2f}")
# Shared position-bias pairs: preferences that move together, even when gold-accuracy is high.
pos_calls = {}
for j in ("S", "L", "X"):
    pos_calls[j] = position_calls(slot_run(j, PS, swap=False), slot_run(j, PS, swap=True))
for a, b, lab_ in (("S", "L", "SL"), ("S", "X", "SX"), ("L", "X", "LX")):
    both = sum(x == "position" and y == "position" for x, y in zip(pos_calls[a], pos_calls[b]))
    a_n = sum(x == "position" for x in pos_calls[a])
    b_n = sum(y == "position" for y in pos_calls[b])
    panel[f"shared_pos_{lab_}"] = {"both": both, "a": a_n, "b": b_n, "n": len(PS)}
    print(f"  shared position outcomes {a}-{b}: {both} (J-{a} has {a_n}, J-{b} has {b_n})")
OUT["panel"] = panel


# Flatten a few headline numbers for figures and the chapter.
OUT["headline"] = {
    "pos_S": pos["S"]["position_rate"], "pos_S_n": pos["S"]["position"],
    "pos_S_parsed": pos["S"]["parsed"], "pos_S_ci": pos["S"]["position_ci"],
    "pos_L": pos["L"]["position_rate"], "pos_X": pos["X"]["position_rate"],
    "pos_S_large": pos["S"]["gap_large"]["position_rate"],
    "pos_S_close": pos["S"]["gap_close"]["position_rate"],
    "pos_S_tied": pos["S"]["gap_tied"]["position_rate"],
    "verb_S_tied": verb["S"]["tied"]["flip_rate"],
    "verb_S": verb["S"]["flip_rate"],
    "self_S_tied": sp["S"]["tied"]["self_pref"],
    "label_S": lab["S"]["label_shift"],
    "auth_S": auth["S"]["flip_rate"],
    "rubric_S_excess": rub["S"]["excess_first"],
    "seg_S_acc_gap": seg["S"]["accuracy"]["_max_gap"],
}

path = HERE / "out" / "lab.json"
path.write_text(json.dumps(OUT, indent=2, default=float))
print(f"\nWrote {path}")
