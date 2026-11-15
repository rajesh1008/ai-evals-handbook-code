"""Chapter 7: the error-analysis notebook. One entry per trace read, in five fields:
trace, first-pass note, open code, axial cluster, decision.

    python3 -m truss.notebook code SAMPLE.json NOTEBOOK.csv --annotator NAME [--script FILE]
    python3 -m truss.notebook report NOTEBOOK.csv [--second SECOND.csv]

Also here: a risk-weighted draw with fixed quotas per stratum, a frame audit that refuses
an undeclared exclusion, saturation (new clusters by trace position), agreement and the
adjudication record, the cluster decision rule, and the hours a notebook costs.
Plain Python, no dependencies beyond the rest of Truss.
"""
import argparse
import csv
import json
import random
import sys
from collections import Counter, OrderedDict
from dataclasses import asdict, dataclass, fields
from pathlib import Path

from .taxonomy import kappa

DECISIONS = ("pass", "existing mode", "new mode", "open code", "noise", "policy question")
FIELDS = ["n", "trace_id", "flow", "verdict", "first_pass", "open_code", "cluster", "decision",
          "code", "secondary", "annotator"]


@dataclass
class Entry:
    n: int
    trace_id: str
    flow: str
    verdict: str                 # pass | fail | cannot_tell
    first_pass: str = ""         # what the reader wrote on first reading, in the borrower's terms
    open_code: str = ""          # a short phrase naming what went wrong at the first wrong step
    cluster: str = ""            # axial cluster, filled after all entries are open-coded
    decision: str = ""           # one of DECISIONS
    code: str = ""               # taxonomy code the decision assigns (primary)
    secondary: str = ""          # further codes, ';'-separated
    annotator: str = ""

    def label(self):
        """The label kappa compares: the primary code, 'pass', or 'open:<cluster>'."""
        if self.verdict != "fail":
            return "pass"
        return self.code or f"open:{self.cluster or self.open_code}"


def write(entries, path):
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, FIELDS)
        w.writeheader()
        for e in entries:
            w.writerow(asdict(e))


def read(path):
    with open(path) as fh:
        return [Entry(**{**r, "n": int(r["n"])}) for r in csv.DictReader(fh)]


# ---- drawing

def pps_quota(frame, key, quotas, risk, seed=2026):
    """Exactly quotas[s] traces from each stratum s, drawn without replacement with
    probability proportional to risk(row) (Efraimidis-Spirakis keys). Returns
    [(trace_id, stratum, weight)] in stratum order, then time order; weight approximates
    the inverse inclusion probability so a rate can still be weighted back, though a
    discovery sample is read for modes, not rates."""
    rng = random.Random(seed)
    out = []
    for s, n in quotas.items():
        rows = sorted((r for r in frame if r[key] == s), key=lambda r: r["trace_id"])
        tot = sum(risk(r) for r in rows)
        keyed = sorted(rows, key=lambda r: rng.random() ** (1 / risk(r)), reverse=True)[:n]
        out += [(r["trace_id"], s, tot / (n * risk(r))) for r in sorted(keyed, key=lambda r: r["trace_id"])]
    return out


def frame_audit(window_rows, frame_ids, declared=(), field="status"):
    """Compare the frame a query returned with every trace in the window.
    Returns {excluded: {value: count}, undeclared: [...], ok: bool}. An exclusion is
    declared when the field value appears in `declared` (for example 'abandoned')."""
    keep = set(frame_ids)
    gone = Counter(r[field] for r in window_rows if r["trace_id"] not in keep)
    partial = {v: c for v, c in gone.items() if v not in declared}
    return {"window": len(window_rows), "frame": len(keep), "excluded": dict(gone),
            "undeclared": sorted(partial), "ok": not partial}


def share_check(frame_rows, sample_ids, flag, tol=0.5):
    """Share of `flag` rows in the frame vs the sample. Flags a sample with none of a
    condition present in the frame, or with less than tol x its frame share."""
    ids = set(sample_ids)
    f = sum(1 for r in frame_rows if r[flag]) / len(frame_rows)
    s_rows = [r for r in frame_rows if r["trace_id"] in ids]
    s = sum(1 for r in s_rows if r[flag]) / len(s_rows) if s_rows else 0.0
    return {"frame_share": f, "sample_share": s, "ok": not (f > 0 and s < tol * f)}


# ---- after reading

def saturation(entries):
    """[(n, failures so far, distinct clusters so far)] in reading order."""
    seen, fails, out = OrderedDict(), 0, []
    for e in sorted(entries, key=lambda e: e.n):
        if e.verdict == "fail":
            fails += 1
            seen.setdefault(e.cluster or e.open_code, e.n)
        out.append((e.n, fails, len(seen)))
    return out


def agreement(a, b):
    """a, b: entries for the same traces by two annotators. Verdict and label kappa, and the
    disagreements, each typed by what would settle it."""
    bi = {e.trace_id: e for e in b}
    pairs = [(e, bi[e.trace_id]) for e in sorted(a, key=lambda e: e.n) if e.trace_id in bi]
    va = [x.verdict for x, _ in pairs]; vb = [y.verdict for _, y in pairs]
    la = [x.label() for x, _ in pairs]; lb = [y.label() for _, y in pairs]
    dis = [{"n": x.n, "trace_id": x.trace_id, "first": x.label(), "second": y.label(),
            "kind": "verdict" if x.verdict != y.verdict else "code"}
           for x, y in pairs if x.label() != y.label()]
    return {"n": len(pairs), "verdict_agree": sum(p == q for p, q in zip(va, vb)),
            "label_agree": sum(p == q for p, q in zip(la, lb)),
            "verdict_kappa": kappa(va, vb), "label_kappa": kappa(la, lb), "disagreements": dis}


SETTLED_BY = {
    "facts": "re-read the evidence line; the trace settles it",
    "two tests pass": "earliest wrong step is primary; the other is secondary",
    "test meaning": "the mode's owner rules in writing and the test is reworded",
    "is it a failure": "the cluster rule's first question; the policy owner rules if policy is silent",
}


def adjudicate(dis, rulings):
    """rulings: {n: (kind, final label, decider, reason)}. Every disagreement needs one,
    with a named decider and a reason; there is no tally of opinions to fall back on."""
    out = []
    for d in dis:
        if d["n"] not in rulings:
            raise ValueError(f"trace {d['n']} ({d['trace_id']}) has no ruling")
        kind, final, who, why = rulings[d["n"]]
        if kind not in SETTLED_BY or not who or not why:
            raise ValueError(f"trace {d['n']}: ruling needs a kind in {list(SETTLED_BY)}, a decider and a reason")
        out.append({**d, "kind_of_question": kind, "final": final, "decider": who, "reason": why,
                    "first_right": final == d["first"], "second_right": final == d["second"]})
    return out


def cluster_decision(harms, fits_existing, one_fix_owner, traces, critical=False, confirmed_elsewhere=0):
    """The four questions a cluster answers before it becomes a mode.
    harms: a borrower or a policy is failed (not taste); fits_existing: an existing inclusion
    test answers yes without stretching; one_fix_owner: one cause, one owner; traces: count in
    this reading; confirmed_elsewhere: matching traces from another month or a look-alike search."""
    if not harms:
        return "noise"
    if fits_existing:
        return "existing mode"
    if not one_fix_owner:
        return "split before adding"
    if traces + confirmed_elsewhere >= 2 or critical:
        return "new mode"
    return "open code"


def hours(plan, rates):
    """plan: [(activity, person, count, minutes each)]; rates: {person: dollars per hour}.
    Returns rows with hours and dollars, and totals."""
    rows = [{"activity": a, "person": p, "count": c, "minutes": m, "hours": c * m / 60,
             "dollars": c * m / 60 * rates[p]} for a, p, c, m in plan]
    return {"rows": rows, "hours": sum(r["hours"] for r in rows), "dollars": sum(r["dollars"] for r in rows)}


def to_markdown(entries):
    lines = ["| No. | Trace | Flow | First-pass note | Open code | Cluster | Decision |", "|---|---|---|---|---|---|---|"]
    for e in sorted(entries, key=lambda e: e.n):
        dec = e.decision + (f" {e.code}" if e.code else "") + (f" (+{e.secondary})" if e.secondary else "")
        lines.append(f"| {e.n} | {e.trace_id} | {e.flow} | {e.first_pass} | {e.open_code} | {e.cluster} | {dec} |")
    return "\n".join(lines)


# ---- CLI

def show(t, i, n, out=None):
    out = out or sys.stdout
    print(f"[{i}/{n}] {t['trace_id']}  flow={t['flow']}  turns={t['turns']}  status={t.get('status', '?')}", file=out)
    for who, text in t.get("messages", []):
        print(f"  {who:>9}: {text}", file=out)


def code_session(traces, out_path, annotator, answers, out=None):
    """Open-code a sample one trace at a time. Each answer line:
    p [note]  |  f <open code> :: <first-pass note>  |  c <note>. Resumable, like the Chapter 2 CLI."""
    done = {e.trace_id for e in read(out_path)} if Path(out_path).exists() else set()
    entries = read(out_path) if done else []
    for i, t in enumerate(traces, 1):
        if t["trace_id"] in done:
            continue
        show(t, i, len(traces), out)
        raw = next(answers).strip()
        v, _, rest = raw.partition(" ")
        verdict = {"p": "pass", "f": "fail", "c": "cannot_tell"}.get(v.lower())
        if verdict is None:
            raise ValueError(f"need p, f or c, got {raw!r}")
        code, _, note = rest.partition("::") if verdict == "fail" else ("", "", rest)
        if verdict == "fail" and not code.strip():
            raise ValueError("a fail needs an open code")
        entries.append(Entry(i, t["trace_id"], t["flow"], verdict, note.strip(), code.strip(), annotator=annotator))
        write(entries, out_path)
    return entries


def report(entries, second=None, out=None):
    out = out or sys.stdout
    fails = [e for e in entries if e.verdict == "fail"]
    print(f"traces read {len(entries)}, failing {len(fails)}, distinct open codes {len({e.open_code for e in fails})}", file=out)
    for c, k in Counter(e.cluster or e.open_code for e in fails).most_common():
        print(f"  {k:>2}  {c}", file=out)
    sat = saturation(entries)
    print("saturation (n: clusters) " + ", ".join(f"{n}:{c}" for n, _, c in sat if n % 10 == 0), file=out)
    if second:
        a = agreement(entries, second)
        print(f"agreement on {a['n']}: verdict {a['verdict_agree']} (kappa {a['verdict_kappa']:.2f}), "
              f"label {a['label_agree']} (kappa {a['label_kappa']:.2f}), disagreements {len(a['disagreements'])}", file=out)


def main(argv=None, load=None):
    ap = argparse.ArgumentParser(prog="truss.notebook")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("code"); c.add_argument("sample"); c.add_argument("notebook")
    c.add_argument("--annotator", required=True); c.add_argument("--script")
    r = sub.add_parser("report"); r.add_argument("notebook"); r.add_argument("--second")
    a = ap.parse_args(argv)
    if a.cmd == "code":
        traces = (load or (lambda p: json.load(open(p))))(a.sample)
        answers = iter(open(a.script).read().splitlines()) if a.script else iter(sys.stdin.readline, "")
        n = len(code_session(traces, a.notebook, a.annotator, answers))
        print(f"notebook has {n} entries")
    else:
        report(read(a.notebook), read(a.second) if a.second else None)


if __name__ == "__main__":
    main()
