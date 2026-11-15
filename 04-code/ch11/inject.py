"""Chapter 11 failure injection: a currency normaliser that rounds to the nearest dollar.

The change ships as a tidy-up in the step that writes extracted amounts into the loan file. Every
check with a one-dollar tolerance still passes. Usage: python3 inject.py
"""
import docs as DOCS, score as S
from specs import BY, FIELDS
from truss import fields as F

docs = DOCS.load(); D = {d["id"]: d for d in docs}
H = S.parsed("haiku")
MONEY = [f for f in FIELDS if BY[f].kind == "money"]


def rounding(v):
    return float(round(F.money(v)))


def tolerant(f, tol):
    return F.FieldSpec(f, "money", tolerance=tol)


base = S.outcomes(docs, H)
inj = S.outcomes(docs, H, normaliser=rounding)
print("== money fields where a value exists, Haiku extraction, before and after the rounding normaliser")
print(f"  {'comparison':<26}{'before':>10}{'after':>10}")
for label, tol in (("within $1.00", 1.0), ("within 1%", None), ("to the cent", 0.005)):
    b = a = n = 0
    for d in docs:
        for f in MONEY:
            g = d["gold"][f]
            if g is None:
                continue
            n += 1
            raw = H[d["id"]]["obj"].get(f)
            for which, val in (("b", raw), ("a", rounding(raw) if raw is not None else None)):
                t = tol if tol is not None else abs(g) * 0.01
                ok = F.outcome(tolerant(f, t), val, g) == "tp"
                if which == "b":
                    b += ok
                else:
                    a += ok
    print(f"  {label:<26}{b:>6}/{n:<4}{a:>6}/{n:<4}")

flips = [i for i in D if S.decision(H[i]["obj"], D[i]) != S.decision(
    {**H[i]["obj"], **{f: rounding(H[i]["obj"][f]) for f in MONEY if H[i]["obj"].get(f) is not None}}, D[i])]
print(f"  hardship decisions changed by rounding: {len(flips)} {flips}")

# the reconciliation Harbor's auditors run: the file's income equals the document's, to the cent
recon = 0; drift = []
for d in docs:
    g = d["gold"]
    if g["doc_type"] == "pay_stub":
        fields = ["gross_pay", "net_pay", "ytd_gross"]
    elif g["doc_type"] == "bank_statement":
        fields = ["payroll_total"]
    else:
        fields = ["stated_monthly_income"] if g["stated_monthly_income"] is not None else []
    for f in fields:
        v = H[d["id"]]["obj"].get(f)
        if v is not None and abs(rounding(v) - F.money(v)) > 0.005:
            recon += 1; drift.append(abs(rounding(v) - F.money(v)))
print(f"  amounts that no longer reconcile to the cent: {recon}; largest drift ${max(drift):.2f}; "
      f"mean ${sum(drift) / len(drift):.2f}")
annual = 0.0
for d in docs:
    g = d["gold"]
    if g["doc_type"] == "pay_stub":
        v = H[d["id"]]["obj"].get("gross_pay")
        annual += abs(rounding(v) - F.money(v)) * S.PER_YEAR[H[d["id"]]["obj"]["pay_frequency"]]
print(f"  annualised income misstatement across the 90 stubs: ${annual:,.2f}")

# the check that catches it: the normaliser must return every printed amount unchanged
cases = []
for d in docs[:40]:
    for f in MONEY:
        g = d["gold"][f]
        if g is not None:
            cases.append((f"${g:,.2f}", round(float(g), 2)))
for name, fn in (("format-only normaliser (Truss)", F.money), ("rounding normaliser", rounding)):
    bad = F.identity_test(fn, cases)
    print(f"  identity test, {name:<32} {len(cases) - len(bad)}/{len(cases)} printed amounts returned unchanged")
