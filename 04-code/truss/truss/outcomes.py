"""Chapter 3: joining traces to what happened afterwards.

A direct join uses the trace ID the servicing system now stores with each
event. A fuzzy join, all the pilot allows, matches borrower token and a time
window, and attributes an event to the most recent earlier conversation.
"""
from bisect import bisect_right
from datetime import datetime, timedelta


def _t(s):
    return datetime.fromisoformat(s)


def link_direct(outcomes):
    return {o["outcome_id"]: o["trace_id"] for o in outcomes if o.get("trace_id")}


def link_fuzzy(traces, outcomes, days=7, key="borrower_token"):
    """Attribute each outcome to the latest trace by the same key within `days` before it."""
    by = {}
    for t in traces:
        by.setdefault(t[key], []).append((t["started_at_utc"], t["trace_id"]))
    for v in by.values():
        v.sort()
    links = {}
    for o in outcomes:
        conv = by.get(o[key], [])
        i = bisect_right(conv, (o["occurred_at_utc"], "~")) - 1
        if i >= 0 and _t(o["occurred_at_utc"]) - _t(conv[i][0]) <= timedelta(days=days):
            links[o["outcome_id"]] = conv[i][1]
    return links


def score_links(found, truth):
    """Precision and recall of a link map against the true one."""
    right = sum(1 for k, v in found.items() if truth.get(k) == v)
    return right / max(1, len(found)), right / max(1, len(truth))


def matured(traces, horizon_days, as_of):
    """Traces old enough for an outcome with this horizon to have arrived."""
    cut = _t(as_of) - timedelta(days=horizon_days)
    return [t for t in traces if _t(t["started_at_utc"]) <= cut]
