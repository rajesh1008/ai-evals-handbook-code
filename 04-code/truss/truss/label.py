"""Chapter 2: the labeller CLI. One trace at a time, one verdict, one note.

    python3 -m truss.label SAMPLE.csv LABELS.csv --annotator "Grace Holloway"

Verdicts: p (pass), f (fail), c (cannot tell). A fail needs a one-line note
in the borrower's terms. Labels are appended as the annotator goes, so a
session can stop and resume. --script FILE replays recorded answers.
"""
import argparse
import csv
import sys
from datetime import datetime
from pathlib import Path

VERDICTS = {"p": "pass", "f": "fail", "c": "cannot_tell"}
FIELDS = ["trace_id", "flow", "verdict", "note", "annotator", "labelled_at"]


def show(t, i, n, out=sys.stdout):
    print(f"[{i}/{n}] {t['trace_id']}  flow={t['flow']}  turns={t['turns']}", file=out)
    print(f"  tools: {', '.join(t['tools']) or '(none recorded)'}", file=out)
    if t.get("missing"):
        print(f"  WARNING incomplete trace, missing: {', '.join(t['missing'])}", file=out)
    for who, text in t["messages"]:
        print(f"  {who:>8}: {text}", file=out)


def ask(answers):
    raw = next(answers).strip().split(" ", 1)
    verdict = VERDICTS.get(raw[0].lower())
    note = raw[1].strip() if len(raw) > 1 else ""
    if verdict is None or (verdict == "fail" and not note):
        raise ValueError(f"need p, f <note> or c, got {' '.join(raw)!r}")
    return verdict, note


def done_ids(path):
    if not Path(path).exists():
        return set()
    with open(path) as fh:
        return {r["trace_id"] for r in csv.DictReader(fh)}


def session(traces, out_path, annotator, answers, out=sys.stdout):
    seen = done_ids(out_path)
    todo = [t for t in traces if t["trace_id"] not in seen]
    new = not Path(out_path).exists()
    with open(out_path, "a", newline="") as fh:
        w = csv.DictWriter(fh, FIELDS)
        if new:
            w.writeheader()
        for i, t in enumerate(todo, len(seen) + 1):
            show(t, i, len(traces), out)
            verdict, note = ask(answers)
            w.writerow({"trace_id": t["trace_id"], "flow": t["flow"], "verdict": verdict,
                        "note": note, "annotator": annotator,
                        "labelled_at": datetime.now().isoformat(timespec="seconds")})
    return len(todo)


def main(argv=None, load=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("sample"); ap.add_argument("labels")
    ap.add_argument("--annotator", required=True); ap.add_argument("--script")
    a = ap.parse_args(argv)
    traces = load(a.sample)
    answers = iter(open(a.script).read().splitlines()) if a.script else iter(sys.stdin.readline, "")
    print(f"labelled {session(traces, a.labels, a.annotator, answers)} traces")
