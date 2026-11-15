"""Chapter 14 fixture: five weeks of hardship traces, 2 August to 5 September 2027. SIMULATED.

Facts are generated (seed 2026); Compass's first-reply action is generated from the facts with planted
errors; the required action is computed by `required` and is hidden from everyone in the story. Trace
IDs: the week of Mon 2 August 2027 starts at t-141501, a range this chapter chose (575 conversations a
day, all flows); 240 hardship traces a week are placed in each week's range.

Two cases the operations guideline ops-1.0 does not mention are planted at their observed frequency:
  anniversary   relief that ended exactly twelve calendar months before the conversation (HP-2027-04 4.3:
                "fewer than 12 calendar months", so it does not count; branch habit says "within a year")
  stated work   the borrower says their work has changed (now self-employed, or now on a payroll) and the
                account record still shows the old status; the borrower's statement is the current status
Neither case occurs in the gold-set generator of Chapter 13, so no anchor or qualification case holds one.
"""
import random
from datetime import date, timedelta

SEED = 2026
LABELS = ("ask_which_loan", "ask_income", "decline_window", "refer_to_officer", "draft_deferral", "cannot_tell")
SHORT = {"ask_which_loan": "which", "ask_income": "income", "decline_window": "window",
         "refer_to_officer": "refer", "draft_deferral": "draft", "cannot_tell": "cannot tell"}
WEEKS = [date(2027, 8, 2) + timedelta(days=7 * i) for i in range(5)]   # frame weeks (conversation dates)
FIRST_ID, IDS_PER_WEEK, PER_WEEK = 141501, 4025, 240
# The decline letter says the borrower may ask again in twelve months, so returns cluster on the anniversary.
END_MONTHS = [2, 4, 6, 8, 9, 10, 11, 11, 12, 12, 12, 12, 13, 15, 18, 24]


def months_back(d, m):
    y, mo = d.year, d.month - m
    while mo <= 0:
        mo += 12; y -= 1
    day = min(d.day, [31, 29 if y % 4 == 0 else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][mo - 1])
    return date(y, mo, day)


def calendar_months(a, b):
    """Whole calendar months from a to b (b later): 12 on the anniversary, 11 the day before."""
    m = (b.year - a.year) * 12 + b.month - a.month
    return m - (1 if b.day < a.day else 0)


def facts(g, conv_date, gold_like=False):
    two = g.random() < 0.20
    f = {"date": conv_date.isoformat(), "loans": 2 if two else 1, "names_loan": (not two) or g.random() < 0.55,
         "income_basis": g.choices(["gross", "take_home", "none"], [0.50, 0.32, 0.18])[0],
         "behind": g.choices([0, 1, 2, 3, 4], [0.38, 0.30, 0.18, 0.09, 0.05])[0],
         "lang": "es" if g.random() < 0.14 else "en"}
    f["loan_unclear"] = two and f["names_loan"] and g.random() < 0.25
    f["income"] = None if f["income_basis"] == "none" else g.randrange(1800, 6400, 50)
    rec = g.choices(["employee", "self_employed", "retired"], [0.88, 0.09, 0.03])[0]
    cur = rec
    if not gold_like:
        if rec == "employee" and g.random() < 0.07:
            cur = "self_employed"
        elif rec == "self_employed" and g.random() < 0.25:
            cur = "employee"
    f["record_work"], f["current_work"] = rec, cur
    if g.random() < 0.58:
        f["relief"] = None
    else:
        kind = g.choices(["deferral", "extension", "disaster"], [0.50, 0.36, 0.14])[0]
        dur = {"deferral": g.choice([3, 6, 6, 9, 12]), "extension": g.choice([1, 2, 2, 3]), "disaster": g.choice([3, 6])}[kind]
        m = g.choice([x for x in END_MONTHS if not (gold_like and x == 12)])
        end = months_back(conv_date, m)
        f["relief"] = {"kind": kind, "granted": months_back(end, dur).isoformat(), "ended": end.isoformat(),
                       "end_missing": g.random() < 0.025}
    return f


def is_anniversary(f):
    r = f["relief"]
    return bool(r and not r["end_missing"] and r["kind"] != "disaster"
                and calendar_months(date.fromisoformat(r["ended"]), date.fromisoformat(f["date"])) == 12)


def is_stated_work(f):
    return f["record_work"] != f["current_work"]


def required(f, anniversary_inside=False, use_record=False, unclear_is_named=False):
    """HP-2027-04 first-reply action with bulletin HB-2027-07 (disaster forbearance outside the window).
    The keyword arguments are the readings the guideline must settle."""
    if f["loans"] > 1 and (not f["names_loan"] or (f["loan_unclear"] and not unclear_is_named)):
        return "ask_which_loan"
    if f["income_basis"] == "none":
        return "ask_income"
    r = f["relief"]
    if r and r["kind"] != "disaster":
        if r["end_missing"]:
            return "cannot_tell"
        m = calendar_months(date.fromisoformat(r["ended"]), date.fromisoformat(f["date"]))
        if m < 12 or (m == 12 and anniversary_inside):
            return "decline_window"
    work = f["record_work"] if use_record else f["current_work"]
    if work == "self_employed" or f["behind"] >= 3:
        return "refer_to_officer"
    return "draft_deferral"


def compass_action(f, g):
    """Compass's first reply, with planted errors (seeded)."""
    t = required(f)
    if t == "cannot_tell":
        return g.choice(["draft_deferral", "refer_to_officer"])
    if is_anniversary(f) and g.random() < 0.55:
        return "decline_window"                                          # FM-20 pattern
    if is_stated_work(f) and g.random() < 0.5:
        return required(f, use_record=True)
    if f["income_basis"] == "take_home" and t != "ask_which_loan" and g.random() < 0.12:
        return "ask_income"
    if f["loan_unclear"] and g.random() < 0.35:
        return required(f, unclear_is_named=True)
    if g.random() < 0.025:
        return g.choice([x for x in LABELS[:5] if x != t])
    return t


EMP = {"employee": "W-2 employee (verified at origination)", "self_employed": "self-employed (Schedule C at origination)",
       "retired": "retired (pension and Social Security)"}


def render(t):
    """The trace as an annotator (and the pre-labeller) sees it before Compass's reply is shown."""
    f = t["facts"]
    lines = [f"Trace {t['trace_id']} | hardship | {f['date']} | language: {'Spanish' if f['lang'] == 'es' else 'English'}",
             "ACCOUNT FACTS (servicing system)"]
    for i in range(f["loans"]):
        lines.append(f"  Loan {i + 1}: auto loan ending {t['loan_digits'][i]}")
    lines.append(f"  Payments behind (account): {f['behind']}")
    lines.append(f"  Employment on file: {EMP[f['record_work']]}")
    r = f["relief"]
    if not r:
        lines.append("  Relief history: none")
    else:
        kind = {"deferral": "payment deferral", "extension": "payment extension", "disaster": "disaster forbearance"}[r["kind"]]
        end = "end date not recorded" if r["end_missing"] else f"ended {r['ended']}"
        lines.append(f"  Relief history: {kind} on loan ending {t['loan_digits'][0]}, granted {r['granted']}, {end}")
    lines.append("BORROWER MESSAGE")
    lines.append("  " + t["message"])
    return "\n".join(lines)


def message(f, digits, g):
    es = f["lang"] == "es"
    cause = g.choice([("my hours were cut", "me recortaron las horas"), ("I was laid off", "me despidieron"),
                      ("my partner lost their job", "mi pareja perdió su trabajo"),
                      ("I had a medical bill", "tuve una cuenta médica")])
    parts = ["Hola, " + cause[1] + "." if es else "Hi, " + cause[0] + "."]
    if f["loans"] > 1:
        if not f["names_loan"]:
            parts.append("No puedo hacer el pago este mes." if es else "I can't make my payment this month.")
        elif f["loan_unclear"]:
            parts.append("No puedo pagar el préstamo del carro." if es else "I can't make the car loan payment.")
        else:
            parts.append(f"No puedo pagar el préstamo que termina en {digits[1]}." if es else f"I can't pay the loan ending {digits[1]}.")
    else:
        parts.append("No puedo hacer el pago este mes." if es else "I can't make my payment this month.")
    if f["income_basis"] == "gross":
        parts.append(f"Gano ${f['income']:,} al mes antes de impuestos." if es else f"I make ${f['income']:,} a month before taxes.")
    elif f["income_basis"] == "take_home":
        parts.append(f"Me quedan como ${f['income']:,} al mes después de impuestos." if es else f"I take home about ${f['income']:,} a month.")
    if f["record_work"] == "employee" and f["current_work"] == "self_employed":
        parts.append(g.choice(["Ahora manejo para una app de entregas a tiempo completo, por mi cuenta." if es else
                               "I'm driving for a delivery app full time now, on my own.",
                               "Ahora tengo mi propio negocio de limpieza." if es else "I started my own cleaning business.",
                               ]))
    if f["record_work"] == "self_employed" and f["current_work"] == "employee":
        parts.append("Cerré mi negocio y ahora trabajo en planilla en un almacén." if es else
                     "I closed my shop and I'm on the payroll at a warehouse now.")
    parts.append("¿Qué opciones tengo?" if es else "What can I do?")
    return " ".join(parts)


def build():
    g = random.Random(SEED)
    weeks = []
    for w, start in enumerate(WEEKS):
        lo = FIRST_ID + w * IDS_PER_WEEK
        ids = sorted(g.sample(range(lo, lo + IDS_PER_WEEK), PER_WEEK))
        rows = []
        for i in ids:
            d = start + timedelta(days=int((i - lo) / IDS_PER_WEEK * 7))
            f = facts(g, d)
            digits = [f"{g.randrange(1000, 9999)}" for _ in range(f["loans"])]
            t = {"trace_id": f"t-{i}", "week": w + 1, "facts": f, "loan_digits": digits}
            t["message"] = message(f, digits, g)
            t["required"] = required(f)
            t["compass"] = compass_action(f, g)
            t["text"] = render(t)
            rows.append(t)
        weeks.append(rows)
    # Wrong offers (a deferral drafted where the policy says refer or ask) are rare in Harbor's
    # monitoring (Chapter 2: one in 196 hardship traces). A separate seeded stream keeps one
    # in seven of the planted ones; the rest become correct replies. The trace text is unchanged.
    g2 = random.Random(SEED + 1)
    for rows in weeks:
        for t in rows:
            if (t["compass"] == "draft_deferral" and t["required"] not in ("draft_deferral", "cannot_tell")
                    and g2.random() >= 1 / 7):
                t["compass"] = t["required"]
    return weeks


def gold_cases(n, seed, prefix):
    """Cases with the gold set's facts model (Chapter 13): no anniversary, no stated change of work."""
    g = random.Random(seed)
    out = []
    for k in range(n):
        d = date(2027, 7, 1) + timedelta(days=g.randrange(0, 9))
        f = facts(g, d, gold_like=True)
        digits = [f"{g.randrange(1000, 9999)}" for _ in range(f["loans"])]
        t = {"trace_id": f"{prefix}-{k + 1:02d}", "week": 0, "facts": f, "loan_digits": digits}
        t["message"] = message(f, digits, g)
        t["required"] = required(f)
        t["compass"] = compass_action(f, g)
        t["text"] = render(t)
        out.append(t)
    return out


if __name__ == "__main__":
    from collections import Counter
    W = build()
    allt = [t for w in W for t in w]
    print(len(allt), Counter(t["required"] for t in allt))
    print("anniversary", sum(is_anniversary(t["facts"]) for t in allt), "stated work", sum(is_stated_work(t["facts"]) for t in allt))
    print("compass wrong", sum(t["compass"] != t["required"] and t["required"] != "cannot_tell" for t in allt))
    print(allt[3]["text"])
