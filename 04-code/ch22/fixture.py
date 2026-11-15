"""Chapter 22 fixture (SIMULATED traffic, planted truth): 300 fee-explanation traces from the four
weeks Monday 31 January to Sunday 27 February 2028, the set on which fee-judge-v2's written
critiques are studied. Truth comes from the planted kind, not from reading text; the reply text is
written later by a real model from a brief (gen.py), as in Chapter 16.

Policy in force: fee-schedule-2026-03 plus hardship bulletin HB-2027-12.
  - $25 late fee when a payment posts more than 15 days after the due date.
  - One courtesy waiver in any twelve calendar months for borrowers on autopay. A waiver applied
    fewer than twelve calendar months before the fee date bars a new one; the anniversary day is
    outside the window (the Chapter 15 C-03 v1.1 reading, applied to fees).
  - HB-2027-12 (effective Monday 6 December 2027): the late fee on the payment that triggered an
    approved hardship plan is waived automatically, whatever the autopay or waiver history.

Kinds (MC-02 verdict in brackets):
  stand_noauto   fee stands, borrower not on autopay                                   [pass]
  stand_inside   fee stands, a courtesy waiver was used inside twelve months           [pass]
  waive_ok       autopay, no waiver inside twelve months; fee waived                    [pass]
  waive_hb       payment triggered an approved hardship plan; fee waived (HB-2027-12)   [pass]
  defer_open     a waiver request is already open; reply defers to a loan officer       [pass]
  F_stand_elig   autopay, last waiver outside twelve months; reply says the fee stands  [fail]
  F_waive_inside waiver used inside twelve months; reply waives the fee anyway          [fail]
  F_hb_stand     payment triggered a hardship plan; reply says the fee stands           [fail]
  X_wrongloan    history pulled for the borrower's other loan; reply quotes it          [fail]
  F_terms        reply states a 10-day grace period (the schedule says 15)              [fail]

Edge flag: a prior courtesy waiver dated between 340 and 395 days before the fee date sits near
the twelve-month anniversary; that is where date arithmetic goes wrong.

Study set: 120 at random from the fresh weekly gold of Chapter 19's two-track monitor (30 a week),
plus 180 targeted (officer-overturned verdicts, HB-2027-12 trigger payments, waiver dates near the
anniversary). Split 100 development / 200 held-out, stratified by kind, seed 2026.
"""
import random
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "truss"))
from truss.checks import within_months  # noqa: E402

SEED = 2026
WEEKS = {"2028-01-31": 245201, "2028-02-07": 249201, "2028-02-14": 253201, "2028-02-21": 257201}
LATE_FEE, GRACE = 25, 15
PASS_KINDS = ("stand_noauto", "stand_inside", "waive_ok", "waive_hb", "defer_open")
FAIL_KINDS = ("F_stand_elig", "F_waive_inside", "F_hb_stand", "X_wrongloan", "F_terms")
MODE = {"F_stand_elig": "FM-06", "F_waive_inside": "FM-06", "F_hb_stand": "FM-06",
        "X_wrongloan": "FM-22", "F_terms": "FM-06"}
# production mix on the fee flow (random stratum); fail kinds about 6% together
PROD = {"stand_noauto": 0.30, "stand_inside": 0.22, "waive_ok": 0.30, "waive_hb": 0.06, "defer_open": 0.06,
        "F_stand_elig": 0.020, "F_waive_inside": 0.010, "F_hb_stand": 0.015, "X_wrongloan": 0.010, "F_terms": 0.005}
# targeted 180: where verdicts get disputed
TARGET = {"stand_inside": 25, "waive_ok": 25, "waive_hb": 20, "defer_open": 5, "stand_noauto": 5,
          "F_stand_elig": 30, "F_waive_inside": 25, "F_hb_stand": 25, "X_wrongloan": 12, "F_terms": 8}
TONES = ("warm", "curt")


def _used_elsewhere():
    """Trace IDs Chapter 20 already featured in these weeks (hardship decisions)."""
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("fixture_ch20", Path(__file__).resolve().parents[1] / "ch20" / "fixture.py")
        f20 = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(f20)
        if getattr(f20, "WEEK_START_ID", None) is None:
            return set()
        w = f20.world()
        ids = set()
        for part in w.values():
            rows = part if isinstance(part, list) else [r for v in part.values() for r in v]
            ids |= {r.get("trace_id") for r in rows if isinstance(r, dict)}
        return ids
    except Exception:
        return set()


def _edge(g):
    return g.random() < 0.55


def _history(g, kind, fee_date):
    autopay, waiver, hb = True, None, False
    edge = False
    if kind == "stand_noauto":
        autopay = False
        if g.random() < 0.3:
            waiver = fee_date - timedelta(days=g.randint(400, 900))
    elif kind in ("stand_inside", "F_waive_inside"):
        if _edge(g):
            waiver = fee_date - timedelta(days=g.randint(340, 362)); edge = True
        else:
            waiver = fee_date - timedelta(days=g.randint(35, 300))
    elif kind in ("waive_ok", "F_stand_elig"):
        r = g.random()
        if r < 0.55:
            waiver = fee_date - timedelta(days=g.randint(367, 395)); edge = True
        elif r < 0.8:
            waiver = fee_date - timedelta(days=g.randint(420, 1000))
    elif kind in ("waive_hb", "F_hb_stand"):
        hb = True
        r = g.random()
        if r < 0.45:
            autopay = False
        elif r < 0.9:
            waiver = fee_date - timedelta(days=g.randint(40, 300))
    elif kind == "defer_open":
        if g.random() < 0.5:
            waiver = fee_date - timedelta(days=g.randint(400, 900))
    elif kind in ("X_wrongloan", "F_terms"):
        if g.random() < 0.5:
            waiver = fee_date - timedelta(days=g.randint(420, 900))
    if waiver and kind not in ("waive_hb", "F_hb_stand", "stand_noauto", "defer_open"):
        inside = within_months(waiver, fee_date, 12, anniversary_inside=False)
        want_inside = kind in ("stand_inside", "F_waive_inside")
        assert inside == want_inside, (kind, waiver, fee_date)
    return autopay, waiver, hb, edge


def account_span(t):
    """What the get_account_history tool returned for the loan it was called on (logged in the trace)."""
    loan = t["other"] if t["kind"] == "X_wrongloan" else t["asked"]
    h = t["hist_other"] if t["kind"] == "X_wrongloan" else t
    lines = [f'get_account_history(loan="{loan}") ->']
    lines.append(f'  {h["due"]} payment_due amount ${h["amount"]:.2f}')
    lines.append(f'  {h["fee_date"]} payment_posted ({h["days"]} days after due)')
    lines.append(f'  {h["fee_date"]} late_fee_assessed ${LATE_FEE}')
    lines.append(f'  autopay: {"enrolled since " + h["enrolled"] if h["autopay"] else "not enrolled"}')
    lines.append(f'  courtesy waivers applied: {h["waiver"] if h["waiver"] else "none on record"}')
    if h["hb"]:
        lines.append(f'  hardship plan approved {h["hb_date"]}; trigger payment: the payment due {h["due"]}')
    if t["kind"] == "defer_open":
        lines.append(f'  waiver request opened {h["fee_date"]} (open, assigned to a loan officer)')
    return "\n".join(lines)


def question(t):
    return (f"Why was I charged a late fee on my loan ending {t['asked']}? "
            f"My payment went through {t['days']} days after the due date.")


def _make(tid, kind, day, stratum, g):
    autopay, waiver, hb, edge = _history(g, kind, day)
    days = g.randint(16, 29)
    due = day - timedelta(days=days)
    t = {"trace_id": tid, "kind": kind, "stratum": stratum, "fee_date": day.isoformat(), "due": due.isoformat(),
         "days": days, "amount": 380 + g.randint(0, 320) + g.randint(0, 99) / 100, "autopay": autopay,
         "enrolled": (day - timedelta(days=g.randint(200, 1400))).isoformat() if autopay else None,
         "waiver": waiver.isoformat() if waiver else None, "hb": hb,
         "hb_date": (day + timedelta(days=g.randint(1, 6))).isoformat() if hb else None,
         "edge": edge, "asked": str(g.randint(1000, 9999)), "other": str(g.randint(1000, 9999)),
         "tone": g.choice(TONES), "words": g.randint(55, 140),
         "truth": "fail" if kind in FAIL_KINDS else "pass", "mode": MODE.get(kind)}
    if kind == "X_wrongloan":
        ow = day - timedelta(days=g.randint(40, 200))
        t["hist_other"] = {"due": due.isoformat(), "fee_date": day.isoformat(), "days": days, "amount": t["amount"] - 61.5,
                           "autopay": True, "enrolled": t["enrolled"] or (day - timedelta(days=500)).isoformat(),
                           "waiver": ow.isoformat(), "hb": False}
    return t


def study_set():
    rng = random.Random(SEED + 22)
    used = _used_elsewhere()
    pool = [n for wk, s in WEEKS.items() for n in range(s, s + 4000) if n % 10 == 6 and f"t-{n:06d}" not in used]
    ids = sorted(rng.sample(pool, 300))
    rng.shuffle(ids)
    plan = []
    kinds, w = list(PROD), [PROD[k] for k in PROD]
    for i in range(120):
        plan.append(("random", rng.choices(kinds, w)[0]))
    for k, n in TARGET.items():
        plan += [("targeted", k)] * n
    out = []
    for (stratum, kind), n in zip(plan, ids):
        tid = f"t-{n:06d}"
        wk = max(d for d, s in WEEKS.items() if s <= n)
        day = date.fromisoformat(wk) + timedelta(days=(n - WEEKS[wk]) * 7 // 4000)
        g = random.Random(f"ch22-{tid}")
        out.append(_make(tid, kind, day, stratum, g))
    out.sort(key=lambda t: t["trace_id"])
    # stratified dev / test split by kind
    order = []
    for k in sorted({t["kind"] for t in out}):
        ts = [t for t in out if t["kind"] == k]
        rng.shuffle(ts)
        order += ts
    for i, t in enumerate(order):
        t["split"] = "dev" if i % 3 == 0 else "test"
    return out


def splits():
    S = study_set()
    return [t for t in S if t["split"] == "dev"], [t for t in S if t["split"] == "test"]


if __name__ == "__main__":
    from collections import Counter
    S = study_set()
    d, te = splits()
    print(len(S), S[0]["trace_id"], S[-1]["trace_id"], "dev", len(d), "test", len(te))
    print(Counter(t["kind"] for t in S))
    print("fail", sum(t["truth"] == "fail" for t in S), "random fail", sum(t["truth"] == "fail" for t in S if t["stratum"] == "random"))
    print("edge", sum(t["edge"] for t in S), "hb", sum(t["hb"] for t in S))
    print(account_span(S[0]))
