"""Chapter 11: the 200 hardship income documents (fixture).

Each document is a text rendering of what Harbor Lending's document service hands Compass after
OCR: a pay stub, a bank statement or a hardship letter, in one of 30 layouts, in English or Spanish,
clean or photographed (simulated OCR confusions). Every document is generated from known values,
so the gold record is exact (the reverse-annotation approach: fill the layout from the values).
Uploads: hardship conversations Mon 3 May to Fri 28 May 2027. Document IDs hd-0001 to hd-0200.
Seed 2026. Usage: python3 docs.py   (writes out/docs.jsonl and prints the mix)
"""
import json, random
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "out" / "docs.jsonl"
SEED = 2026
N = {"pay_stub": 90, "bank_statement": 60, "hardship_letter": 50}

FIRST = ["Emily", "Daniel", "Maria", "Jose", "Ashley", "Michael", "Jessica", "Luis", "Sarah", "David",
         "Ana", "Carlos", "Megan", "Kevin", "Rosa", "Brandon", "Laura", "Miguel", "Nicole", "James",
         "Gabriela", "Tyler", "Veronica", "Robert", "Amanda", "Jorge", "Rachel", "Eric", "Lucia", "Steven"]
LAST = ["Carter", "Nguyen", "Gonzalez", "Ramirez", "Thompson", "Hernandez", "Walker", "Lopez", "Mitchell",
        "Reyes", "Patel", "Sanchez", "Brooks", "Torres", "Kim", "Flores", "Bennett", "Morales", "Price", "Castillo"]
ACCENT = {"Maria": "María", "Jose": "José", "Lucia": "Lucía", "Gonzalez": "González", "Ramirez": "Ramírez",
          "Hernandez": "Hernández", "Lopez": "López", "Sanchez": "Sánchez"}
EMPLOYERS = ["Sonoran Freight Lines", "Valley Medical Group", "Copper State Logistics", "Tempe Home Health",
             "Gilbert Fresh Markets", "Chandler Precision Machining", "Red Rock Hospitality", "Pima Solar Installations",
             "Agua Fria Landscaping", "Desert Ridge Auto", "Camelback Motors", "Saguaro Coffee Roasters",
             "Superstition Dental Partners", "Salt River Warehousing", "Mesquite Grill Group", "Verde Valley Plumbing"]
SUFFIX = ["", " LLC", " Inc.", ", Inc.", " Co."]
BANKS = ["Sun Valley Federal Credit Union", "Grand Canyon Community Bank", "Mogollon Rim Savings", "Cactus State Bank"]
FREQ = {"weekly": 52, "biweekly": 26, "semimonthly": 24, "monthly": 12}
REASONS = ["job_loss", "reduced_hours", "medical", "divorce_separation", "death_in_family", "disaster"]
MES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre",
       "noviembre", "diciembre"]
MON = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
       "November", "December"]


def money(x, sym=True):
    return ("$" if sym else "") + f"{x:,.2f}"


def fmt_date(d, style, lang="en"):
    if style == "us":
        return d.strftime("%m/%d/%Y")
    if style == "iso":
        return d.isoformat()
    if style == "long":
        return f"{MON[d.month-1]} {d.day}, {d.year}" if lang == "en" else f"{d.day} de {MES[d.month-1]} de {d.year}"
    if style == "short":
        return d.strftime("%b %d, %Y") if lang == "en" else f"{d.day:02d}/{d.month:02d}/{d.year}"
    raise ValueError(style)


OCR = {"0": "O", "1": "l", "5": "S", "8": "B", "O": "0", "l": "1", "S": "5", "I": "1", "e": "c", "m": "rn"}


def photograph(text, rng, rate):
    """Simulated OCR confusions on a photographed page: character swaps, a few dropped spaces."""
    out = []
    for ch in text:
        if ch in OCR and rng.random() < rate:
            out.append(OCR[ch])
        elif ch == " " and rng.random() < rate / 3:
            continue
        else:
            out.append(ch)
    return "".join(out)


def periods(freq, end):
    if freq == "weekly":
        return end - timedelta(days=6), 7
    if freq == "biweekly":
        return end - timedelta(days=13), 14
    if freq == "semimonthly":
        return (end.replace(day=1) if end.day <= 15 else end.replace(day=16)), None
    return end.replace(day=1), None


def periods_elapsed(freq, end):
    doy = (end - date(end.year, 1, 1)).days + 1
    if freq == "weekly":
        return max(1, doy // 7)
    if freq == "biweekly":
        return max(1, doy // 14)
    if freq == "semimonthly":
        return (end.month - 1) * 2 + (1 if end.day <= 15 else 2)
    return end.month


def name_for(rng):
    f, l = rng.choice(FIRST), rng.choice(LAST)
    return f, l


# ---------------------------------------------------------------- pay stubs
STUB_LAYOUTS = [f"stub-{i:02d}" for i in range(1, 15)]


def make_stub(rng, i):
    lay = STUB_LAYOUTS[i % len(STUB_LAYOUTS)]
    lang = "es" if lay in ("stub-06", "stub-13") else "en"
    f, l = name_for(rng)
    shown = f"{ACCENT.get(f, f)} {ACCENT.get(l, l)}" if lang == "es" else f"{f} {l}"
    emp = rng.choice(EMPLOYERS)
    emp_shown = emp + rng.choice(SUFFIX)
    freq = rng.choices(list(FREQ), [15, 45, 30, 10])[0]
    if lay in ("stub-06", "stub-13") and freq == "weekly":
        freq = "biweekly"
    end = date(2027, 4, 1) + timedelta(days=rng.randint(0, 40))
    if freq == "semimonthly":
        end = end.replace(day=15) if end.day <= 15 else (end.replace(day=28) if end.month == 2 else
                                                          (date(end.year, end.month + 1, 1) - timedelta(days=1)))
    if freq == "monthly":
        end = date(end.year, end.month + 1, 1) - timedelta(days=1)
    start, _ = periods(freq, end)
    paydate = end + timedelta(days=rng.choice([3, 4, 5, 6]))
    hourly = rng.random() < 0.6
    if hourly:
        rate = round(rng.uniform(15.5, 32.0) * 4) / 4
        hours = {"weekly": 40, "biweekly": 80, "semimonthly": 86.67, "monthly": 173.33}[freq]
        hours = round(hours * rng.uniform(0.45, 1.0), 2)
        reg = round(rate * hours, 2)
        ot_h = round(rng.choice([0, 0, 0, 3.5, 6, 8.25]), 2)
        ot = round(ot_h * rate * 1.5, 2)
    else:
        annual = rng.randrange(34000, 78000, 250)
        reg = round(annual / FREQ[freq], 2)
        rate, hours, ot_h, ot = None, None, 0, 0.0
    gross = round(reg + ot, 2)
    k = periods_elapsed(freq, end)
    ytd = round(gross * k * rng.uniform(0.93, 1.07), 2)
    if ytd < gross:
        ytd = gross
    fed = round(gross * rng.uniform(0.06, 0.11), 2); ss = round(gross * 0.062, 2); med = round(gross * 0.0145, 2)
    st = round(gross * rng.uniform(0.02, 0.03), 2); ins = round(rng.choice([0, 42.18, 61.5, 88.0]), 2)
    net = round(gross - fed - ss - med - st - ins, 2)
    freq_label = {"weekly": "Weekly", "biweekly": rng.choice(["Bi-Weekly", "Biweekly", "Every two weeks"]),
                  "semimonthly": rng.choice(["Semi-Monthly", "Semimonthly", "Twice monthly"]), "monthly": "Monthly"}[freq]
    es_freq = {"biweekly": "Catorcenal", "semimonthly": "Quincenal", "monthly": "Mensual"}.get(freq, "Semanal")
    ds = rng.choice(["us", "us", "long", "iso", "short"])
    D = lambda d: fmt_date(d, ds, lang)
    earn = []
    if hourly:
        earn.append(("Regular", hours, rate, reg))
        if ot:
            earn.append(("Overtime", ot_h, rate * 1.5, ot))
    else:
        earn.append(("Salary", None, None, reg))
    traps = []
    if lay == "stub-01":
        lines = [emp_shown.upper(), "EARNINGS STATEMENT", f"Employee: {shown}", f"Pay period: {D(start)} to {D(end)}",
                 f"Pay date: {D(paydate)}", f"Pay frequency: {freq_label}", "",
                 f"{'Description':<14}{'Hours':>8}{'Rate':>9}{'Current':>12}{'YTD':>13}"]
        for n, h, r, a in earn:
            lines.append(f"{n:<14}{(f'{h:.2f}' if h else ''):>8}{(f'{r:.2f}' if r else ''):>9}{money(a, False):>12}{'':>13}")
        lines += [f"{'Gross pay':<31}{money(gross, False):>12}{money(ytd, False):>13}",
                  f"{'Federal tax':<31}{money(fed, False):>12}", f"{'Social Security':<31}{money(ss, False):>12}",
                  f"{'Medicare':<31}{money(med, False):>12}", f"{'AZ state tax':<31}{money(st, False):>12}",
                  f"{'Net pay':<31}{money(net, False):>12}"]
    elif lay == "stub-02":
        lines = [f"{emp_shown}", f"NET PAY {money(net)}", f"Paid to {shown} on {D(paydate)}",
                 f"Period ending {D(end)} ({freq_label})", "", "Total earnings this period  " + money(gross),
                 "Total earnings year to date  " + money(ytd), "Deductions this period  " + money(round(gross - net, 2))]
    elif lay == "stub-03":
        lines = [f"Company: {emp_shown}", f"Name: {shown}", f"Pay Period: {D(start)} - {D(end)}",
                 f"Pay Date: {D(paydate)}", f"Gross: {money(gross)}", f"Net: {money(net)}", f"YTD Gross: {money(ytd)}"]
        traps.append("frequency_unlabelled")
    elif lay == "stub-04":
        lines = [f"{emp_shown} payroll", f"{shown}", f"Period {D(start)} through {D(end)}, paid {D(paydate)}, {freq_label}",
                 "", f"{'Earnings':<12}{'Hrs':>7}{'Rate':>8}{'This period':>14}"]
        for n, h, r, a in earn:
            lines.append(f"{n:<12}{(f'{h:.2f}' if h else ''):>7}{(f'{r:.2f}' if r else ''):>8}{money(a, False):>14}")
        lines += ["", f"Year to date gross {money(ytd)}", f"Taxes and deductions {money(round(gross - net, 2))}",
                  f"Take-home {money(net)}"]
        if len(earn) > 1:
            traps.append("gross_not_printed")
    elif lay == "stub-05":
        lines = [f"{emp_shown.upper()[:22]} PR {D(paydate)}", f"EE {shown.upper()}",
                 f"PER END {D(end)} FREQ {freq[:2].upper()}",
                 f"GRS {money(gross, False)} YTD {money(ytd, False)} NET {money(net, False)}",
                 f"FIT {money(fed, False)} SS {money(ss, False)} MED {money(med, False)} SIT {money(st, False)}"]
        traps.append("abbreviated")
    elif lay in ("stub-06", "stub-13"):
        lines = ["TALÓN DE PAGO", f"Empresa: {emp_shown}", f"Empleado: {shown}",
                 f"Periodo: del {D(start)} al {D(end)}", f"Fecha de pago: {D(paydate)}", f"Frecuencia: {es_freq}",
                 f"Sueldo bruto: {money(gross)}", f"Deducciones: {money(round(gross - net, 2))}",
                 f"Pago neto: {money(net)}", f"Bruto acumulado del año: {money(ytd)}"]
        if lay == "stub-13":
            lines.insert(1, "Copia del empleado")
    elif lay == "stub-07":
        lines = [f"{emp_shown}", f"Employee {shown}", f"Net pay {money(net)}",
                 f"Deductions: federal {money(fed)}, FICA {money(round(ss + med, 2))}, state {money(st)}",
                 f"Year-to-date: gross {money(ytd)}, net {money(round(ytd * net / gross, 2))}",
                 f"This period ({freq_label}, ending {D(end)}): gross {money(gross)}", f"Check date {D(paydate)}"]
        traps.append("ytd_first")
    elif lay == "stub-08":
        lines = [f"PAY ADVICE  {emp_shown}", f"{shown}", f"Period beginning {D(start)}  Period ending {D(end)}",
                 f"Check date {D(paydate)}", f"Schedule {freq_label}",
                 f"Current: Gross {money(gross)}  Net {money(net)}", f"Year to date: Gross {money(ytd)}"]
    elif lay == "stub-09":
        lines = [f"{shown} / {emp_shown}", f"{D(end)} period end, {freq_label.lower()} payroll",
                 f"Earned {money(gross)} gross; deposited {money(net)}", f"{D(paydate)} deposit date",
                 f"Earned so far this year {money(ytd)}"]
    elif lay == "stub-10":
        prev_end = end - timedelta(days={"weekly": 7, "biweekly": 14}.get(freq, 15 if freq == "semimonthly" else 30))
        prev_gross = round(gross * rng.uniform(0.85, 1.12), 2)
        prev_net = round(prev_gross * net / gross, 2)
        lines = [f"{emp_shown} - two most recent pay statements", f"Employee: {shown}", f"Frequency: {freq_label}", "",
                 f"Period ending {D(prev_end)}: gross {money(prev_gross)}, net {money(prev_net)}, YTD gross {money(round(ytd - gross, 2))}",
                 f"Period ending {D(end)}: gross {money(gross)}, net {money(net)}, YTD gross {money(ytd)}"]
        traps.append("two_periods")
    elif lay == "stub-11":
        lines = [f"Statement of earnings | {emp_shown}", f"Payee | {shown}", f"Period | {D(start)} | {D(end)}",
                 f"Paid | {D(paydate)}", f"Frequency | {freq_label}", "Item | Current | YTD",
                 f"Gross | {money(gross, False)} | {money(ytd, False)}", f"Net | {money(net, False)} | {money(round(ytd * net / gross, 2), False)}"]
    elif lay == "stub-12":
        lines = [f"{emp_shown}", f"{shown}", f"Hours worked {hours if hours else 'salaried'}",
                 f"Rate {money(rate) + '/hr' if rate else money(reg) + ' per period'}",
                 f"Pay period {D(start)}-{D(end)} ({freq_label})", f"Gross wages {money(gross)}",
                 f"Net wages {money(net)}", f"YTD {money(ytd)}"]
    else:  # stub-14
        lines = [f"{emp_shown} | Direct deposit advice", f"{shown}", f"Advice date {D(paydate)}",
                 f"Pay period end {D(end)}", f"Pay cycle: {freq_label}", f"Gross earnings {money(gross)}",
                 f"Bonus {money(0)}", f"Net deposit {money(net)}", f"Year to date earnings {money(ytd)}"]
    gold = {"doc_type": "pay_stub", "person_name": f"{f} {l}", "employer": emp, "period_end": end.isoformat(),
            "pay_frequency": freq, "gross_pay": gross, "net_pay": net, "ytd_gross": ytd, "payroll_total": None,
            "stated_monthly_income": None, "loan_last4": None, "hardship_reason": None, "payroll_deposits": None}
    extra = {"pay_date": paydate.isoformat(), "hourly": hourly, "overtime": ot, "periods_elapsed": k}
    return lay, lang, "\n".join(lines), gold, traps, extra


# ---------------------------------------------------------------- bank statements
BANK_LAYOUTS = [f"bank-{i:02d}" for i in range(1, 9)]


def make_statement(rng, i):
    lay = BANK_LAYOUTS[i % len(BANK_LAYOUTS)]
    lang = "es" if lay == "bank-07" else "en"
    f, l = name_for(rng)
    shown = f"{ACCENT.get(f, f)} {ACCENT.get(l, l)}" if lang == "es" else f"{f} {l}"
    emp = rng.choice(EMPLOYERS)
    payer = emp.upper().replace(" ", " ")[:20]
    bank = rng.choice(BANKS)
    month = rng.choice([3, 4])
    start = date(2027, month, 1); end = date(2027, month + 1, 1) - timedelta(days=1)
    freq = rng.choices(["weekly", "biweekly", "semimonthly"], [20, 55, 25])[0]
    if freq == "semimonthly":
        days = [15, end.day]
    elif freq == "weekly":
        d0 = rng.randint(1, 7); days = list(range(d0, end.day + 1, 7))
    else:
        d0 = rng.randint(1, 14); days = list(range(d0, end.day + 1, 14))
    netpay = round(rng.uniform(780, 2100) if freq != "semimonthly" else rng.uniform(1100, 2600), 2)
    rows = []
    for d in days:
        amt = round(netpay * rng.uniform(0.9, 1.1), 2)
        rows.append({"date": date(2027, month, d), "desc": f"DIRECT DEP {payer} PAYROLL", "amt": amt, "payroll": True})
    others = [("TRANSFER FROM SAVINGS x4410", (100, 900)), ("ZELLE FROM " + rng.choice(LAST).upper(), (40, 400)),
              ("IRS TREAS 310 TAX REF", (300, 2400)), ("MOBILE DEPOSIT", (50, 600)), ("REFUND AMAZON MKTPLACE", (10, 90))]
    for desc, (a, b) in rng.sample(others, rng.randint(1, 3)):
        rows.append({"date": date(2027, month, rng.randint(1, end.day)), "desc": desc,
                     "amt": round(rng.uniform(a, b), 2), "payroll": False})
    debits = [("POS PURCHASE FRYS FOOD", 25, 180), ("APS ELECTRIC AUTOPAY", 90, 260), ("HARBOR LENDING PMT", 240, 720),
              ("CIRCLE K", 8, 60), ("RENT PAYMENT", 900, 1650), ("VERIZON WIRELESS", 60, 140), ("ATM WITHDRAWAL", 20, 200),
              ("TARGET T-1123", 15, 160), ("STATE FARM INS", 90, 210), ("NETFLIX.COM", 15.49, 15.49)]
    for desc, a, b in rng.sample(debits, rng.randint(6, 10)):
        rows.append({"date": date(2027, month, rng.randint(1, end.day)), "desc": desc,
                     "amt": -round(rng.uniform(a, b), 2), "payroll": False})
    rows.sort(key=lambda r: (r["date"], -r["amt"]))
    bal = round(rng.uniform(900, 3200), 2); opening = bal
    for r in rows:
        bal = round(bal + r["amt"], 2); r["bal"] = bal
    ds = rng.choice(["us", "short", "iso"])
    D = lambda d: fmt_date(d, ds, lang)
    traps = []
    head = [bank, f"Account holder: {shown}" if lang == "en" else f"Titular: {shown}",
            (f"Statement period: {D(start)} to {D(end)}" if lang == "en" else f"Periodo del estado: {D(start)} al {D(end)}"),
            f"Opening balance {money(opening)}" if lang == "en" else f"Saldo inicial {money(opening)}"]
    body = []
    split = len(rows) // 2 + rng.randint(-2, 2)
    if lay in ("bank-01", "bank-05"):
        body.append(f"{'Date':<14}{'Description':<32}{'Withdrawals':>12}{'Deposits':>12}{'Balance':>12}")
        for j, r in enumerate(rows):
            if lay == "bank-05" and j == split:
                body += ["", "--- Page 2 of 2 ---", bank, f"Account holder: {shown}",
                         f"{'Date':<14}{'Description':<32}{'Withdrawals':>12}{'Deposits':>12}{'Balance':>12}",
                         f"{'':<14}{'Balance forward':<32}{'':>12}{'':>12}{money(rows[j-1]['bal'], False):>12}"]
                traps.append("page_break")
            w = money(-r["amt"], False) if r["amt"] < 0 else ""
            dp = money(r["amt"], False) if r["amt"] > 0 else ""
            body.append(f"{D(r['date']):<14}{r['desc'][:31]:<32}{w:>12}{dp:>12}{money(r['bal'], False):>12}")
    elif lay in ("bank-02", "bank-06"):
        body.append(f"{'Date':<14}{'Description':<34}{'Amount':>12}{'Balance':>12}")
        for r in rows:
            body.append(f"{D(r['date']):<14}{r['desc'][:33]:<34}{money(r['amt'], False):>12}{money(r['bal'], False):>12}")
        traps.append("signed_amounts")
    elif lay in ("bank-03", "bank-07"):
        dep = [r for r in rows if r["amt"] > 0]; wd = [r for r in rows if r["amt"] < 0]
        body.append("DEPOSITS AND ADDITIONS" if lang == "en" else "DEPÓSITOS Y ABONOS")
        for r in dep:
            body.append(f"{D(r['date']):<14}{r['desc'][:33]:<34}{money(r['amt'], False):>12}")
        tot = round(sum(r["amt"] for r in dep), 2)
        body.append(("Total deposits and additions " if lang == "en" else "Total de depósitos ") + money(tot))
        body += ["", "WITHDRAWALS AND PAYMENTS" if lang == "en" else "RETIROS Y PAGOS"]
        for r in wd:
            body.append(f"{D(r['date']):<14}{r['desc'][:33]:<34}{money(-r['amt'], False):>12}")
        traps.append("total_deposits_line")
    elif lay == "bank-04":
        body.append("Date | Description | Debit | Credit | Balance")
        for r in rows:
            body.append(f"{D(r['date'])} | {r['desc']} | {money(-r['amt'], False) if r['amt'] < 0 else ''} | "
                        f"{money(r['amt'], False) if r['amt'] > 0 else ''} | {money(r['bal'], False)}")
    else:  # bank-08: app export with a pending section after the period
        body.append("Posted transactions")
        for r in rows:
            body.append(f"{D(r['date'])}  {r['desc']}  {money(r['amt'])}  bal {money(r['bal'])}")
        nxt = end + timedelta(days=rng.randint(1, 4))
        body += ["", "Pending (not yet posted)", f"{D(nxt)}  DIRECT DEP {payer} PAYROLL  {money(round(netpay, 2))}"]
        traps.append("pending_after_period")
    if lay == "bank-06":
        traps.append("balance_adjacent")
    pay = [r for r in rows if r["payroll"]]
    gold = {"doc_type": "bank_statement", "person_name": f"{f} {l}", "employer": emp, "period_end": end.isoformat(),
            "pay_frequency": None, "gross_pay": None, "net_pay": None, "ytd_gross": None,
            "payroll_total": round(sum(r["amt"] for r in pay), 2), "stated_monthly_income": None,
            "loan_last4": None, "hardship_reason": None,
            "payroll_deposits": [{"date": r["date"].isoformat(), "amount": r["amt"]} for r in pay]}
    extra = {"bank": bank, "rows": len(rows), "deposit_rows": sum(r["amt"] > 0 for r in rows), "payer": payer,
             "pay_freq_true": freq}
    return lay, lang, "\n".join(head + [""] + body), gold, traps, extra


# ---------------------------------------------------------------- hardship letters
LETTER_LAYOUTS = [f"letter-{i:02d}" for i in range(1, 9)]
REASON_EN = {"job_loss": ["I was laid off from {emp} on {d}", "my position at {emp} was eliminated in {m}"],
             "reduced_hours": ["{emp} cut my hours from 40 to {h} a week starting in {m}",
                               "my shifts at {emp} were reduced in {m}"],
             "medical": ["I had surgery in {m} and could not work for six weeks", "my son was in the hospital in {m}"],
             "divorce_separation": ["my husband and I separated in {m} and I am now the only income",
                                    "since my divorce was finalised in {m} I pay the household bills alone"],
             "death_in_family": ["my father passed away in {m} and I covered the funeral costs",
                                 "my wife passed away in {m}"],
             "disaster": ["the monsoon flood in {m} damaged our home and my car", "a fire in our building in {m} displaced us"]}
REASON_ES = {"job_loss": ["me despidieron de {emp} en {m}"], "reduced_hours": ["{emp} me redujo las horas a {h} por semana en {m}"],
             "medical": ["tuve una cirugía en {m} y no pude trabajar"], "divorce_separation": ["me separé de mi esposo en {m}"],
             "death_in_family": ["mi padre falleció en {m}"], "disaster": ["la inundación de {m} dañó nuestra casa"]}


def make_letter(rng, i):
    lay = LETTER_LAYOUTS[i % len(LETTER_LAYOUTS)]
    lang = "es" if lay in ("letter-04", "letter-08") else "en"
    f, l = name_for(rng)
    shown = f"{ACCENT.get(f, f)} {ACCENT.get(l, l)}" if lang == "es" else f"{f} {l}"
    reason = rng.choice(REASONS)
    emp = rng.choice(EMPLOYERS) if reason in ("job_loss", "reduced_hours") or rng.random() < 0.4 else None
    when = date(2027, rng.choice([1, 2, 3, 4]), rng.randint(1, 28))
    ldate = date(2027, 5, rng.randint(1, 27))
    loan = f"{rng.randint(1000, 9999)}"
    other = f"{rng.randint(1000, 9999)}" if rng.random() < 0.3 else None
    kind = rng.choice(["auto loan", "personal loan", "car loan"])
    ds = rng.choice(["us", "long", "long", "short"])
    D = lambda d: fmt_date(d, ds, lang)
    m = MON[when.month - 1] if lang == "en" else MES[when.month - 1]
    hrs = rng.choice([16, 20, 24, 28])
    tmpl = rng.choice((REASON_EN if lang == "en" else REASON_ES)[reason])
    reason_text = tmpl.format(emp=emp or "my employer" if lang == "en" else emp or "mi empleador", d=D(when), m=m, h=hrs)
    traps = []
    second = None
    if rng.random() < 0.3:
        second = rng.choice([r for r in REASONS if r != reason])
        s_t = rng.choice((REASON_EN if lang == "en" else REASON_ES)[second]).format(
            emp=emp or ("my employer" if lang == "en" else "mi empleador"), d=D(when), m=m, h=hrs)
        traps.append("two_reasons")
    income_mode = rng.choices(["monthly_gross", "monthly_net", "hourly_only", "none"], [35, 30, 20, 15])[0]
    inc = round(rng.uniform(1200, 3600) / 5) * 5
    rate = round(rng.uniform(15, 26) * 4) / 4
    if lang == "en":
        inc_text = {"monthly_gross": f"I now earn about {money(inc, True)[:-3]} a month before taxes.",
                    "monthly_net": f"My take-home pay is now {money(inc)[:-3]} per month.",
                    "hourly_only": f"I am paid {money(rate)} an hour for {hrs} hours a week.",
                    "none": "I am looking for work and hope to be back on my feet soon."}[income_mode]
        loan_text = f"my {kind} ending in {loan}"
        if other:
            loan_text += f" (I also have a personal loan with you ending {other}, which is not part of this request)"
            traps.append("two_loans")
        body = [f"Dear Harbor Lending,", "",
                f"I am writing to ask for help with {loan_text}. {reason_text[0].upper() + reason_text[1:]}."
                + (f" On top of that, {s_t}." if second else ""),
                inc_text, "I would like to ask for a deferral of my next payments while I get back on track.",
                "", "Thank you,", shown]
    else:
        inc_text = {"monthly_gross": f"Ahora gano alrededor de {money(inc)[:-3]} al mes antes de impuestos.",
                    "monthly_net": f"Ahora recibo {money(inc)[:-3]} netos al mes.",
                    "hourly_only": f"Me pagan {money(rate)} por hora, {hrs} horas por semana.",
                    "none": "Estoy buscando trabajo."}[income_mode]
        loan_text = f"mi préstamo de auto terminado en {loan}"
        if other:
            loan_text += f" (también tengo un préstamo personal terminado en {other}, que no es parte de esta solicitud)"
            traps.append("two_loans")
        body = ["Estimados señores de Harbor Lending:", "",
                f"Les escribo para pedir ayuda con {loan_text}. {reason_text[0].upper() + reason_text[1:]}."
                + (f" Además, {s_t}." if second else ""), inc_text,
                "Quisiera solicitar un aplazamiento de mis próximos pagos.", "", "Atentamente,", shown]
    if income_mode == "hourly_only":
        traps.append("hourly_only")
    if income_mode == "monthly_net":
        traps.append("net_stated")
    header = {"letter-01": [D(ldate), ""], "letter-02": [shown, D(ldate), ""], "letter-03": [f"Date: {D(ldate)}", f"Re: hardship request", ""],
              "letter-04": [D(ldate), ""], "letter-05": [f"Sent {D(ldate)} via Compass upload", ""],
              "letter-06": [""], "letter-07": [f"{D(ldate)}", "To whom it may concern,", ""], "letter-08": [f"Fecha: {D(ldate)}", ""]}[lay]
    if lay == "letter-06":
        body.append(D(ldate))
        traps.append("date_at_end")
    text = "\n".join(header + body)
    if emp and emp not in text:
        emp = None
    gold = {"doc_type": "hardship_letter", "person_name": f"{f} {l}", "employer": emp, "period_end": ldate.isoformat(),
            "pay_frequency": None, "gross_pay": None, "net_pay": None, "ytd_gross": None, "payroll_total": None,
            "stated_monthly_income": inc if income_mode in ("monthly_gross", "monthly_net") else None,
            "loan_last4": loan, "hardship_reason": reason, "payroll_deposits": None}
    extra = {"income_mode": income_mode, "second_reason": second, "other_loan": other, "event_date": when.isoformat(),
             "hourly_rate": rate if income_mode == "hourly_only" else None, "hours": hrs}
    return lay, lang, text, gold, traps, extra


def build():
    rng = random.Random(SEED)
    docs = []
    makers = [("pay_stub", make_stub), ("bank_statement", make_statement), ("hardship_letter", make_letter)]
    for kind, fn in makers:
        for i in range(N[kind]):
            lay, lang, text, gold, traps, extra = fn(rng, i)
            quality = "photo" if rng.random() < 0.25 else "clean"
            if quality == "photo":
                text = photograph(text, rng, 0.04)
            docs.append({"layout": lay, "lang": lang, "quality": quality, "text": text, "gold": gold,
                         "traps": traps, "extra": extra})
    rng.shuffle(docs)
    # the case each document belongs to: monthly loan payment for the hardship decision
    for j, d in enumerate(docs, 1):
        d["id"] = f"hd-{j:04d}"
        bd = (j - 1) * 20 // 200                      # 20 business days, Mon 3 to Fri 28 May 2027
        d["uploaded"] = (date(2027, 5, 3) + timedelta(days=bd + bd // 5 * 2)).isoformat()
        d["payment"] = round(rng.uniform(240, 720), 2)
        # a document cannot be uploaded before the period it covers ends: move to the next business day
        up, pe = date.fromisoformat(d["uploaded"]), date.fromisoformat(d["gold"]["period_end"])
        while up <= pe or up.weekday() > 4:
            up += timedelta(days=1)
        assert up <= date(2027, 5, 28), (d["id"], pe)
        d["uploaded"] = up.isoformat()
    if not any(d["gold"]["person_name"] == "Emily Carter" for d in docs):
        e = next(d for d in docs if d["gold"]["doc_type"] == "pay_stub" and d["lang"] == "en" and d["quality"] == "clean")
        old = e["gold"]["person_name"]; e["text"] = e["text"].replace(old, "Emily Carter").replace(old.upper(), "EMILY CARTER")
        e["gold"]["person_name"] = "Emily Carter"
    return docs


def load():
    return [json.loads(x) for x in OUT.read_text().splitlines()]


if __name__ == "__main__":
    docs = build()
    OUT.write_text("".join(json.dumps(d, ensure_ascii=False) + "\n" for d in docs))
    from collections import Counter
    print("documents:", len(docs), dict(Counter(d["gold"]["doc_type"] for d in docs)))
    print("layouts:", len({d["layout"] for d in docs}), "languages:", dict(Counter(d["lang"] for d in docs)),
          "quality:", dict(Counter(d["quality"] for d in docs)))
    print("traps:", dict(Counter(t for d in docs for t in d["traps"])))
    print("uploads:", min(d["uploaded"] for d in docs), "to", max(d["uploaded"] for d in docs))
