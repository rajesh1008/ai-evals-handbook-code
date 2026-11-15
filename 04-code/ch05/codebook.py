"""The categories axial coding produced, and the decisions that produced them.
Names, flows, definitions, layers, owners and severities are taxonomy v0.1 exactly as
Chapter 6 inherits it. Codes follow Chapter 4's order: flow by flow, hardship first."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "truss"))
from truss.coding import Category  # noqa: E402
from reading import H, F, A, P, L, S  # noqa: E402

GRACE, LEAD = "Grace Holloway (loan officers)", "evaluation lead"

V01 = [
    ("FM-01", "offer drafted before income confirmed", (H,), "Compass drafts a hardship offer before the borrower has confirmed current income.", 3, GRACE, "critical", "H_income"),
    ("FM-02", "no hand-off when borrower asked for a person", (H,), "The borrower asked for a person and no loan officer took over.", 3, GRACE, "high", "H_person"),
    ("FM-03", "offer sent without saying a loan officer must approve it", (H,), "A hardship offer reaches the borrower without the sentence that a loan officer must approve it.", 1, GRACE, "critical", "H_approval"),
    ("FM-04", "second deferral within 12 months offered", (H,), "Compass offers a deferral to a borrower who had one in the last twelve months.", 1, GRACE, "critical", "H_second"),
    ("FM-05", "ten-day grace period quoted (policy is 15)", (F,), "Compass quotes the retired ten-day grace period; policy is fifteen days.", 1, LEAD, "high", "F_tenday"),
    ("FM-06", "fee not waived when policy says waive", (F,), "Compass explains a late fee that policy says should be waived.", 3, LEAD, "high", "F_waive"),
    ("FM-07", "wrong balance date", (A,), "The balance Compass quotes is dated wrongly.", 2, LEAD, "medium", "A_date"),
    ("FM-08", "missed borrower's second loan", (A,), "Compass answers about one loan when the borrower has two.", 3, LEAD, "medium", "A_second"),
    ("FM-09", "per diem interest omitted", (P,), "The payoff quote leaves out daily interest.", 1, LEAD, "high", "P_perdiem"),
    ("FM-10", "wrong good-through date", (P,), "The payoff quote's good-through date is wrong.", 1, LEAD, "high", "P_goodthru"),
    ("FM-11", "release promised before title office date", (L,), "Compass promises the lien release sooner than the title office can record it.", 3, LEAD, "medium", "L_early"),
    ("FM-12", "wrong title state", (L,), "The release goes to, or names, the wrong state's title office.", 2, LEAD, "medium", "L_state"),
    ("FM-13", "wrong statement period", (S,), "The statement sent covers a different period from the one asked for.", 2, LEAD, "high", "S_month"),
]
CODE_OF = {cause: code for code, *_, cause in V01}

# The axial session's draft (Mon 21 Dec): twelve clusters, payoff as one.
DRAFT_MERGE = {"FM-09": "PAY", "FM-10": "PAY"}
DRAFT_PAY = ("PAY", "payoff quote wrong", (P,), "The payoff quote disagrees with the payoff tool.", 1, LEAD, "high")

# The decisions of the session, in order, with the reason recorded at the time.
DECISIONS = [
    ("drop", "notes on passing traces", "Nothing went wrong: verbosity and repeated questions are style, not failure. Kept in the notebook, not the taxonomy."),
    ("rule", "day-15 payments", "Victor Lane ruled day 15 is inside the grace period; both cannot-tell traces become passes."),
    ("merge", "three wordings of 'asked for a person'", "Ignored, out-of-hours and Spanish requests kept as one category at v0.1: one owner, three first-pass notes and no December case to separate them."),
    ("merge", "income notes", "'Before asking income', 'built on income from the tool' and 'plan before earnings' share one fix: confirm income in this conversation first."),
    ("split", "fee cluster", "Ten-day quotes and unwaived fees have different causes (a retired document, a reading of policy) and different checks (L1 string, L3 reading)."),
    ("split", "payoff cluster", "Ryan Mitchell expected different fixes: per diem lives in the letter template, the good-through date in date arithmetic. Twelve clusters became thirteen."),
    ("keep", "second deferral", "One complaint only. Kept: severity critical, and the eligibility tool already holds the fact a check needs."),
]


def categories(draft=False):
    cats = []
    seen = set()
    for code, name, flows, d, layer, owner, sev, cause in V01:
        if draft and code in DRAFT_MERGE:
            if "PAY" in seen:
                continue
            seen.add("PAY")
            c, n, fl, dd, ly, ow, sv = DRAFT_PAY
            cats.append(Category(c, n, fl, dd, ly, ow, sv))
            continue
        cats.append(Category(code, name, flows, d, layer, owner, sev))
    return cats


def assigner(hidden, draft=False):
    def assign(oc):
        cause = hidden[oc.trace_id]["cause"]
        if cause is None:
            return None
        code = CODE_OF[cause]
        return DRAFT_MERGE.get(code, code) if draft else code
    return assign
