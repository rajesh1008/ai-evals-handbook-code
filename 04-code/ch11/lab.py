"""Chapter 11 lab: score Compass's income-verification extraction per field on 200 documents.

Reads out/docs.jsonl and the cached real runs (extract.py). Prints each step and writes
out/scores.json for the figures. Usage: python3 lab.py [section]
"""
import json, sys
from collections import Counter, defaultdict
from datetime import date
import docs as DOCS, score as S
from specs import SPECS, BY, FIELDS, CRITICAL, APPLIES, PER_YEAR
from truss import fields as F

docs = DOCS.load()
D = {d["id"]: d for d in docs}
H = S.parsed("haiku")
SON = S.parsed("sonnet")
OUT = {}


def pct(x):
    return f"{100 * x:.1f}%"


def section(name):
    return len(sys.argv) < 2 or sys.argv[1] == name


# 1. layer one -------------------------------------------------------------------------------
strict = sum(1 for e in H.values() if not e["repaired"] and e["obj"] is not None)
fenced = sum(e["repaired"] for e in H.values())
l1 = {i: F.layer_one(H[i]["obj"], SPECS) for i in D}
L1 = {"strict_json": strict, "after_fence_repair": strict + fenced,
      "unknown_keys": sum(bool(r["unknown"]) for r in l1.values()),
      "absent_keys": sum(bool(r["absent"]) for r in l1.values()),
      "type_errors": sum(bool(r["type_errors"]) for r in l1.values()),
      "enum_errors": sum(bool(r["enum_errors"]) for r in l1.values()),
      "required_missing": sum(bool(r["required_missing"]) for r in l1.values())}
OUT["layer_one"] = L1
L1S = {"strict_json": sum(1 for e in SON.values() if not e["repaired"] and e["obj"] is not None),
       "after_fence_repair": sum(e["obj"] is not None for e in SON.values())}
OUT["layer_one_sonnet"] = L1S
if section("layer1"):
    print("== layer one (schema), 200 replies each")
    print(f"  {'check':<20}{'haiku':>6}{'sonnet':>8}")
    for k, v in L1.items():
        print(f"  {k:<20}{v:>6}{L1S.get(k, ''):>8}")

# 2. per-field outcomes ----------------------------------------------------------------------
oc = S.outcomes(docs, H)
T = F.field_table((f, o) for fo in oc.values() for f, o in fo.items())
OUT["fields"] = T
slots = sum(t["n"] for t in T.values()); right = sum(t["tp"] + t["tn"] for t in T.values())
present = sum(t["present"] for t in T.values()); tp = sum(t["tp"] for t in T.values())
if section("fields"):
    print(f"== per field, claude-haiku-4-5-20251001, {len(docs)} documents")
    print(f"  {'field':<22}{'TP':>4}{'wrong':>6}{'miss':>5}{'inv':>4}{'TN':>4}{'prec':>8}{'recall':>8}{'acc(all)':>9}")
    for f in FIELDS:
        t = T[f]
        print(f"  {f:<22}{t['tp']:>4}{t['wrong']:>6}{t['miss']:>5}{t['invented']:>4}{t['tn']:>4}"
              f"{pct(t['precision']):>8}{pct(t['recall']):>8}{pct(t['accuracy']):>9}")
    print(f"  all slots: {right}/{slots} right = {pct(right / slots)}; where a value exists: {tp}/{present} = {pct(tp / present)}")

# 3. documents and decisions -----------------------------------------------------------------
roll_all = F.doc_rollup(oc)
roll_req = {i: all(oc[i][f] in ("tp", "tn") for f in APPLIES[D[i]["gold"]["doc_type"]]) for i in D}
roll_crit = {i: all(oc[i][f] in ("tp", "tn") for f in CRITICAL) for i in D}
dec = {i: (S.decision(D[i]["gold"], D[i]), S.decision(H[i]["obj"], D[i])) for i in D}
flips = [i for i, (g, e) in dec.items() if g != e]
OUT["documents"] = {"all_fields": sum(r["all"] for r in roll_all.values()), "required": sum(roll_req.values()),
                    "critical": sum(roll_crit.values()), "decision_same": 200 - len(flips), "flips": flips,
                    "share_hist": Counter(round(r["share"], 3) for r in roll_all.values())}
by_type = defaultdict(lambda: [0, 0, 0])
for i, d in D.items():
    t = d["gold"]["doc_type"]; by_type[t][0] += 1; by_type[t][1] += roll_req[i]; by_type[t][2] += i not in flips
OUT["by_type"] = dict(by_type)
if section("documents"):
    print("== from fields to documents to decisions")
    print(f"  field slots right                 {right}/{slots} = {pct(right / slots)}")
    print(f"  documents with every field right  {OUT['documents']['all_fields']}/200")
    print(f"  documents with every critical field right {OUT['documents']['critical']}/200")
    print(f"  documents whose decision matches gold     {200 - len(flips)}/200")
    for t, (n, ok, dok) in by_type.items():
        print(f"    {t:<16} n={n:<3} all fields right {ok:>3} ({pct(ok / n)})  decision right {dok:>3}")
    for i in flips:
        g, e = dec[i]
        bad = [f for f in CRITICAL if oc[i][f] not in ("tp", "tn")]
        print(f"  flip {i} {D[i]['layout']:<10} gold {g} -> extracted {e}  [{', '.join(bad)}]")

# 4. Victor's threshold (fixed Fri 14 May 2027, before the run) ------------------------------
VICT = []
for f in CRITICAL:
    t = T[f]
    n, k = t["present"] + t["invented"], t["errors_where_present"] + t["invented"]
    ub = F.upper_one_sided(k, n)
    VICT.append({"field": f, "n": n, "errors": k, "rate": k / n, "upper": ub, "pass": k / n < 0.02 and ub < 0.05})
OUT["victor"] = VICT
if section("threshold"):
    print("== Victor's threshold: error rate under 2% and one-sided 95% upper bound under 5%")
    for v in VICT:
        print(f"  {v['field']:<22} {v['errors']:>2}/{v['n']:<3} {pct(v['rate']):>6}  upper {pct(v['upper']):>6}  {'PASS' if v['pass'] else 'FAIL'}")

# 5. slices -----------------------------------------------------------------------------------
def slice_acc(key):
    agg = defaultdict(lambda: [0, 0])
    for i, d in D.items():
        for f in APPLIES[d["gold"]["doc_type"]]:
            agg[key(d)][0] += oc[i][f] in ("tp", "tn"); agg[key(d)][1] += 1
    return {k: (a, n) for k, (a, n) in agg.items()}


SL = {"lang": slice_acc(lambda d: d["lang"]), "quality": slice_acc(lambda d: d["quality"]),
      "layout": slice_acc(lambda d: d["layout"])}
OUT["slices"] = SL
heat = {}
for i, d in D.items():
    for f in APPLIES[d["gold"]["doc_type"]]:
        c = heat.setdefault(f, {}).setdefault(d["layout"], [0, 0]); c[0] += oc[i][f] in ("tp", "tn"); c[1] += 1
OUT["heat"] = heat
if section("slices"):
    print("== applicable fields right, by slice")
    for k in ("lang", "quality"):
        for v, (a, n) in sorted(SL[k].items()):
            print(f"  {k:<8}{v:<8}{a:>4}/{n:<4} {pct(a / n)}")
    worst = sorted(SL["layout"].items(), key=lambda kv: kv[1][0] / kv[1][1])[:6]
    print("  weakest layouts:", ", ".join(f"{k} {pct(a / n)} ({n - a} of {n} wrong)" for k, (a, n) in worst))


# 6. error classes, by reading each error ----------------------------------------------------
def err_class(i, f):
    d, got, gold = D[i], H[i]["obj"].get(f), D[i]["gold"][f]
    if f == "pay_frequency":
        return "frequency word or inference"
    if f == "period_end" and got:
        g, x = date.fromisoformat(gold), F.to_date(got)
        return "day and month swapped" if (x.month, x.day) == (g.day, g.month) else "other date"
    if f == "payroll_total":
        return "rows right, sum wrong" if F.match_rows(H[i]["obj"].get("payroll_deposits"), gold["payroll_deposits"] if False else d["gold"]["payroll_deposits"])["tp"] == len(d["gold"]["payroll_deposits"]) else "rows wrong"
    if isinstance(got, str) and got.replace(" ", "").lower() in d["text"].replace(" ", "").lower():
        return "copied from the page as printed"
    return "space dropped by the photograph"


ERR = Counter(); ERRS = []
for i in D:
    for f in FIELDS:
        if oc[i][f] in ("wrong", "miss", "invented"):
            c = err_class(i, f); ERR[c] += 1
            ERRS.append({"id": i, "field": f, "class": c, "got": H[i]["obj"].get(f), "gold": D[i]["gold"][f],
                         "layout": D[i]["layout"], "lang": D[i]["lang"], "quality": D[i]["quality"],
                         "conf": (H[i]["obj"].get("confidence") or {}).get(f)})
OUT["errors"] = ERRS
if section("errors"):
    print(f"== the {len(ERRS)} field errors, classified by reading each one")
    for c, n in ERR.most_common():
        print(f"  {n:>3}  {c}")

# 7. the payroll table -----------------------------------------------------------------------
TB = {"docs": 0, "rows_gold": 0, "tp": 0, "extra": 0, "missed": 0, "all_rows_right": 0, "total_right": 0,
      "rows_right_total_wrong": [], "sum_check_fails": 0, "sum_check_catches": 0}
for i, d in D.items():
    if d["gold"]["doc_type"] != "bank_statement":
        continue
    obj = H[i]["obj"]; m = F.match_rows(obj.get("payroll_deposits"), d["gold"]["payroll_deposits"])
    TB["docs"] += 1; TB["rows_gold"] += len(d["gold"]["payroll_deposits"])
    TB["tp"] += m["tp"]; TB["extra"] += m["extra"]; TB["missed"] += m["missed"]
    rows_ok = m["extra"] == 0 and m["missed"] == 0
    tot_ok = oc[i]["payroll_total"] == "tp"
    TB["all_rows_right"] += rows_ok; TB["total_right"] += tot_ok
    if rows_ok and not tot_ok:
        TB["rows_right_total_wrong"].append(i)
    try:
        s = round(sum(F.money(r["amount"]) for r in obj.get("payroll_deposits") or []), 2)
        fails = abs(s - F.money(obj.get("payroll_total"))) > 0.005
    except (TypeError, ValueError):
        fails = True
    TB["sum_check_fails"] += fails; TB["sum_check_catches"] += fails and not tot_ok
OUT["table"] = TB
if section("table"):
    print("== payroll deposit table, 60 statements")
    print(f"  gold rows {TB['rows_gold']}; matched {TB['tp']}; extra {TB['extra']}; missed {TB['missed']}")
    print(f"  statements with every row right {TB['all_rows_right']}/60; total right {TB['total_right']}/60")
    print(f"  every row right, total wrong: {', '.join(TB['rows_right_total_wrong'])}")
    for i in TB["rows_right_total_wrong"]:
        print(f"    {i} {D[i]['layout']}: stated {H[i]['obj']['payroll_total']:,.2f}, rows sum "
              f"{sum(r['amount'] for r in H[i]['obj']['payroll_deposits']):,.2f}, gold {D[i]['gold']['payroll_total']:,.2f}")
    print(f"  sum check (total equals its own rows) fires on {TB['sum_check_fails']}, catches {TB['sum_check_catches']} wrong totals")

# 8. confidence ------------------------------------------------------------------------------
conf, corr, fld = [], [], []
for i in D:
    c = H[i]["obj"].get("confidence") or {}
    for f in APPLIES[D[i]["gold"]["doc_type"]]:
        if isinstance(c.get(f), (int, float)):
            conf.append(float(c[f])); corr.append(int(oc[i][f] in ("tp", "tn"))); fld.append((i, f))
rows, ece = F.calibration(conf, corr)
OUT["calibration"] = {"rows": rows, "ece": ece, "n": len(conf)}
wrong_idx = [k for k, c in enumerate(corr) if not c]
pol = {}
for thr in (0.9, 0.95, 0.99):
    flagged = [k for k, c in enumerate(conf) if c < thr]
    pol[f"confidence<{thr}"] = (len(flagged), sum(1 for k in flagged if not corr[k]))
agree_flag = []
if SON:
    for k, (i, f) in enumerate(fld):
        if i not in SON or SON[i]["obj"] is None:
            continue
        a, b = H[i]["obj"].get(f), SON[i]["obj"].get(f)
        same = F.outcome(BY[f], a, b) in ("tp", "tn")
        if not same:
            agree_flag.append(k)
    pol["second reader disagrees"] = (len(agree_flag), sum(1 for k in agree_flag if not corr[k]))
OUT["review_policies"] = pol
if section("confidence"):
    print(f"== stated confidence, {len(conf)} applicable fields, {len(wrong_idx)} wrong")
    for r in rows:
        print(f"  {r['bin']:<11} n={r['n']:<5} mean conf {r['mean_conf']:.3f}  accuracy {r['accuracy']:.3f}")
    print(f"  expected calibration error {ece:.3f}")
    wc = sorted(conf[k] for k in wrong_idx)
    print(f"  confidence on the wrong fields: min {wc[0]:.2f}, median {wc[len(wc) // 2]:.2f}, max {wc[-1]:.2f}")
    for name, (n, caught) in pol.items():
        print(f"  route to officer if {name:<26} flags {n:>4} fields, catches {caught}/{len(wrong_idx)} errors")

# 9. second reader as an extractor ------------------------------------------------------------
if SON and len(SON) == 200:
    oc2 = S.outcomes(docs, SON)
    T2 = F.field_table((f, o) for fo in oc2.values() for f, o in fo.items())
    OUT["sonnet_fields"] = T2
    dec2 = [i for i in D if S.decision(D[i]["gold"], D[i]) != S.decision(SON[i]["obj"], D[i])]
    OUT["sonnet_flips"] = dec2
    if section("second"):
        print("== second reader, claude-sonnet-4-6, same prompt")
        print(f"  {'field':<22}{'haiku errors':>13}{'sonnet errors':>14}")
        for f in FIELDS:
            print(f"  {f:<22}{T[f]['wrong'] + T[f]['miss'] + T[f]['invented']:>13}{T2[f]['wrong'] + T2[f]['miss'] + T2[f]['invented']:>14}")
        print(f"  decisions changed: haiku {len(flips)}, sonnet {len(dec2)}")

# 10. what the definitions change (gold-set guideline) ---------------------------------------
gap = 0; stubs = 0
for d in docs:
    g = d["gold"]
    if g["doc_type"] != "pay_stub":
        continue
    stubs += 1
    cur = g["gross_pay"] * PER_YEAR[g["pay_frequency"]] / 12
    ytd_avg = g["ytd_gross"] / d["extra"]["periods_elapsed"] * PER_YEAR[g["pay_frequency"]] / 12
    gap += abs(cur - ytd_avg) / ytd_avg > 0.05
band_change = 0
for d in docs:
    g = d["gold"]
    if g["doc_type"] == "pay_stub":
        alt = dict(g); alt["gross_pay"] = g["ytd_gross"] / d["extra"]["periods_elapsed"]
        band_change += S.decision(g, d)[2] != S.decision(alt, d)[2]
letters = [d for d in docs if d["gold"]["doc_type"] == "hardship_letter"]
DEF = {"stubs": stubs, "current_vs_ytd_gap_over_5pct": gap, "band_changes_if_ytd_average": band_change,
       "letters": len(letters), "net_stated": sum("net_stated" in d["traps"] for d in letters),
       "hourly_only": sum("hourly_only" in d["traps"] for d in letters),
       "two_reasons": sum("two_reasons" in d["traps"] for d in letters),
       "two_loans": sum("two_loans" in d["traps"] for d in letters),
       "statements_with_non_payroll_deposits": sum(1 for d in docs if d["gold"]["doc_type"] == "bank_statement"
                                                   and d["extra"]["deposit_rows"] > len(d["gold"]["payroll_deposits"]))}
OUT["definitions"] = DEF
if section("definitions"):
    print("== where the definition decides the answer")
    for k, v in DEF.items():
        print(f"  {k:<40}{v:>4}")

json.dump(OUT, open(S.EX.HERE / "out" / "scores.json", "w"), indent=1, default=str)

# 11. which errors the second reader missed --------------------------------------------------
if SON and section("missed"):
    print("== errors the second reader agreed with (disagreement cannot flag them)")
    for e in ERRS:
        s = (SON[e["id"]]["obj"] or {}).get(e["field"])
        if F.outcome(BY[e["field"]], e["got"], s) in ("tp", "tn"):
            print(f"  {e['id']} {e['field']:<15} {e['class']:<38} both said {e['got']!r}")
    print("  error list:")
    for e in ERRS:
        print(f"  {e['id']} {e['layout']:<10} {e['lang']} {e['quality']:<5} {e['field']:<15} {e['class']:<38} got {e['got']!r} gold {e['gold']!r} conf {e['conf']}")

# 12. after the two fixes (rows summed in code; prompt v2 on Spanish documents) --------------
V2P = S.EX.HERE / "out" / "extract-haiku-v2-es.jsonl"
if V2P.exists() and section("after"):
    fixed = {}
    v2 = {j["id"]: F.parse_json(j["raw"])[0] for j in map(json.loads, V2P.read_text().splitlines())}
    for i, d in D.items():
        o = dict(v2[i]) if i in v2 else dict(H[i]["obj"])
        if d["gold"]["doc_type"] == "bank_statement" or o.get("doc_type") == "bank_statement":
            o["payroll_total"] = round(sum(F.money(r["amount"]) for r in o.get("payroll_deposits") or []), 2)
        fixed[i] = {"obj": o}
    ocf = S.outcomes(docs, fixed)
    TF = F.field_table((f, o) for fo in ocf.values() for f, o in fo.items())
    print("== after the two fixes, Victor's threshold again")
    after = []
    for f in CRITICAL:
        t = TF[f]; n = t["present"] + t["invented"]; k = t["errors_where_present"] + t["invented"]
        ub = F.upper_one_sided(k, n); ok = k / n < 0.02 and ub < 0.05
        after.append({"field": f, "n": n, "errors": k, "upper": ub, "pass": ok})
        print(f"  {f:<22} {k:>2}/{n:<3} {pct(k / n):>6}  upper {pct(ub):>6}  {'PASS' if ok else 'FAIL'}")
    fl = [i for i in D if S.decision(D[i]["gold"], D[i]) != S.decision(fixed[i]["obj"], D[i])]
    allr = sum(all(v in ("tp", "tn") for v in ocf[i].values()) for i in D)
    print(f"  documents with every field right {allr}/200; decisions changed {len(fl)} {fl}")
    OUT["after"] = {"victor": after, "all_right": allr, "flips": fl}
    json.dump(OUT, open(S.EX.HERE / "out" / "scores.json", "w"), indent=1, default=str)
