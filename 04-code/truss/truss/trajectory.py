"""Truss 0.27 (Chapter 24): trajectory. Score what the agent did, not just what it said.

The book calls this release Truss v4. The module never calls a model. It scores a sequence of
tool steps against a reference or a grounded checklist: tool-choice and argument correctness,
step efficiency and loops, recovery after a tool error, lucky-pass / false-success detection
(correct outcome reached by a wrong process), partial credit, a transition-failure heatmap,
pass^k across repeated trials of the same task, and whether a compacted context still carries
a named constraint. Judges that read trajectories sit outside this module and are validated
with the same report-card machinery earlier chapters built for reply judges.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from math import comb
from typing import Any, Iterable, Mapping, Sequence


def score_step(step: Mapping[str, Any], expected: Mapping[str, Any] | None = None,
               required_args: Sequence[str] = ()) -> dict:
    """Score one tool step: tool choice, required arguments present and matching, and status.

    expected may name tool and args. A missing expected means only structural checks run
    (tool present, required_args keys present, status in ok/error/unknown).
    """
    tool = step.get("tool")
    args = dict(step.get("args") or {})
    status = step.get("status", "unknown")
    out = {
        "tool_ok": True if expected is None else (tool == expected.get("tool")),
        "args_present": all(k in args for k in required_args),
        "args_match": True,
        "status": status,
        "ok": status == "ok",
    }
    if expected is not None:
        exp_args = dict(expected.get("args") or {})
        for k, v in exp_args.items():
            if args.get(k) != v:
                out["args_match"] = False
                break
        for k in required_args:
            if k not in args:
                out["args_match"] = False
    out["pass"] = bool(out["tool_ok"] and out["args_present"] and out["args_match"] and out["ok"])
    return out


def score_trajectory(steps: Sequence[Mapping[str, Any]],
                     reference: Sequence[Mapping[str, Any]] | None = None,
                     checklist: Sequence[Mapping[str, Any]] | None = None) -> dict:
    """Score a full trajectory.

    Modes:
    - reference: compare step i to reference[i] when lengths match; otherwise mark length_mismatch.
    - checklist: each item is {id, tool?, args?, required_args?, any_order?}; credit when a step
      satisfies it. Partial credit = credited / len(checklist).
    Without either, returns structural stats only (n_steps, n_ok, n_error, loops).
    """
    steps = list(steps)
    n = len(steps)
    tools = [s.get("tool") for s in steps]
    statuses = [s.get("status", "unknown") for s in steps]
    loops = detect_loops(steps)
    base = {
        "n_steps": n,
        "n_ok": sum(1 for s in statuses if s == "ok"),
        "n_error": sum(1 for s in statuses if s == "error"),
        "n_unknown": sum(1 for s in statuses if s == "unknown"),
        "loops": loops["n_loops"],
        "looped": loops["looped"],
        "tools": tools,
    }
    if reference is not None:
        ref = list(reference)
        if len(ref) != n:
            base.update({"mode": "reference", "length_mismatch": True, "step_passes": 0,
                         "step_total": len(ref), "exact_match": False, "partial": 0.0})
            return base
        scores = [score_step(steps[i], ref[i], required_args=list((ref[i].get("args") or {}).keys()))
                  for i in range(n)]
        passes = sum(1 for s in scores if s["pass"])
        base.update({
            "mode": "reference",
            "length_mismatch": False,
            "step_passes": passes,
            "step_total": n,
            "exact_match": passes == n and n > 0,
            "partial": (passes / n) if n else 0.0,
            "step_scores": scores,
        })
        return base
    if checklist is not None:
        credited = []
        remaining = list(steps)
        for item in checklist:
            req = list(item.get("required_args") or list((item.get("args") or {}).keys()))
            hit = None
            for i, st in enumerate(remaining):
                sc = score_step(st, {"tool": item["tool"], "args": item.get("args") or {}}
                                if item.get("tool") else None, required_args=req)
                # If tool is specified, require tool_ok; else only args/status
                ok = sc["pass"] if item.get("tool") else (sc["args_present"] and sc["ok"])
                if item.get("tool") and not sc["tool_ok"]:
                    ok = False
                if item.get("args") and not sc["args_match"]:
                    ok = False
                if ok:
                    hit = i
                    break
            if hit is not None:
                credited.append(item.get("id", item.get("tool")))
                if not item.get("keep_step"):
                    remaining.pop(hit)
        total = len(checklist)
        base.update({
            "mode": "checklist",
            "credited": credited,
            "step_passes": len(credited),
            "step_total": total,
            "exact_match": len(credited) == total and total > 0,
            "partial": (len(credited) / total) if total else 0.0,
        })
        return base
    base.update({"mode": "structural", "partial": None, "exact_match": None})
    return base


def detect_loops(steps: Sequence[Mapping[str, Any]], key_fields: Sequence[str] = ("tool", "args")) -> dict:
    """A loop is a repeated (tool, canonical args) pair after at least one intervening step,
    or the same tool called three or more times with identical args. Returns count and whether
    the trajectory looped at least once.
    """
    import json
    seen: dict[str, list[int]] = defaultdict(list)
    n_loops = 0
    for i, s in enumerate(steps):
        payload = {k: s.get(k) for k in key_fields}
        # canonicalise args
        if "args" in payload and isinstance(payload["args"], dict):
            payload["args"] = {k: payload["args"][k] for k in sorted(payload["args"])}
        key = json.dumps(payload, sort_keys=True, default=str)
        prev = seen[key]
        if prev and (i - prev[-1]) >= 1:
            n_loops += 1
        seen[key].append(i)
    return {"n_loops": n_loops, "looped": n_loops > 0, "unique_keys": len(seen)}


def recovery(steps: Sequence[Mapping[str, Any]]) -> dict:
    """After each error status, did a later step with the same tool (or a documented recovery tool)
    succeed before the trajectory ended?
    """
    events = []
    for i, s in enumerate(steps):
        if s.get("status") != "error":
            continue
        tool = s.get("tool")
        recovered = False
        for later in steps[i + 1:]:
            if later.get("tool") == tool and later.get("status") == "ok":
                recovered = True
                break
            if later.get("recovery_of") == tool and later.get("status") == "ok":
                recovered = True
                break
        events.append({"at": i, "tool": tool, "recovered": recovered})
    n = len(events)
    return {
        "n_errors": n,
        "n_recovered": sum(1 for e in events if e["recovered"]),
        "rate": (sum(1 for e in events if e["recovered"]) / n) if n else None,
        "events": events,
    }


def lucky_pass(outcome_ok: bool, process_ok: bool) -> dict:
    """A lucky pass (false success) is a correct outcome reached by a wrong process."""
    kind = "lucky_pass" if (outcome_ok and not process_ok) else (
        "true_success" if (outcome_ok and process_ok) else (
            "false_failure" if (not outcome_ok and process_ok) else "true_failure"))
    return {"outcome_ok": outcome_ok, "process_ok": process_ok, "kind": kind,
            "is_lucky_pass": kind == "lucky_pass"}


def transition_matrix(trajectories: Sequence[Sequence[Mapping[str, Any]]],
                      fail_when: str = "error") -> dict:
    """Count state -> next-tool transitions. A transition is a failure when the next step's
    status equals fail_when (default 'error'), or when the caller tags the step failed=True.
    Returns counts, failure counts, and failure rates per (from_tool, to_tool).
    """
    counts: Counter = Counter()
    fails: Counter = Counter()
    for steps in trajectories:
        prev = "START"
        for s in steps:
            tool = s.get("tool") or "UNKNOWN"
            key = (prev, tool)
            counts[key] += 1
            is_fail = s.get("failed") is True or s.get("status") == fail_when
            if is_fail:
                fails[key] += 1
            prev = tool
        counts[(prev, "END")] += 1
    rates = {}
    for k, c in counts.items():
        rates[k] = fails.get(k, 0) / c if c else 0.0
    return {"counts": dict(counts), "fails": dict(fails), "rates": rates,
            "n_trajectories": len(trajectories)}


def pass_at_k(trials: Sequence[bool]) -> float:
    """pass@k: fraction of tasks that succeeded at least once (here, on this task's trials)."""
    return 1.0 if any(trials) else 0.0


def pass_hat_k(trials: Sequence[bool]) -> float:
    """pass^k: succeeded on every trial of the task."""
    return 1.0 if trials and all(trials) else 0.0


def pass_hat_k_unbiased(n: int, c: int, k: int) -> float:
    """Unbiased estimator of pass^k from n trials with c successes (tau-bench style).

    Estimates the probability that k independent draws are all successes, given the
    empirical success count. Returns 0 when c < k or n < k.
    """
    if k <= 0 or n <= 0 or c < k or n < k:
        return 0.0
    # P(all k succeed) ≈ C(c,k) / C(n,k)
    return comb(c, k) / comb(n, k)


def aggregate_pass_hat_k(task_trials: Sequence[Sequence[bool]], k: int | None = None) -> dict:
    """Aggregate pass^k across tasks. Each task is a sequence of trial booleans of equal length
    when k is None (k = len of first). Also reports pass@k for comparison.
    """
    if not task_trials:
        return {"n_tasks": 0, "k": k or 0, "pass_hat_k": 0.0, "pass_at_k": 0.0}
    k = k or len(task_trials[0])
    hat = [pass_hat_k(t[:k]) for t in task_trials]
    at = [pass_at_k(t[:k]) for t in task_trials]
    return {
        "n_tasks": len(task_trials),
        "k": k,
        "pass_hat_k": sum(hat) / len(hat),
        "pass_at_k": sum(at) / len(at),
        "n_pass_hat_k": int(sum(hat)),
        "n_pass_at_k": int(sum(at)),
    }


def compaction_survives(original_constraint: str, compacted_text: str,
                        aliases: Sequence[str] = ()) -> dict:
    """Whether a named constraint still appears (literally or via an alias) after compaction."""
    text = (compacted_text or "").lower()
    needles = [original_constraint.lower()] + [a.lower() for a in aliases]
    found = [n for n in needles if n and n in text]
    return {"survives": bool(found), "found": found, "constraint": original_constraint}


def step_efficiency(steps: Sequence[Mapping[str, Any]],
                    reference_len: int | None = None) -> dict:
    """Steps taken, loops, and ratio to a reference length when one is known."""
    loops = detect_loops(steps)
    n = len(steps)
    return {
        "n_steps": n,
        "looped": loops["looped"],
        "n_loops": loops["n_loops"],
        "reference_len": reference_len,
        "extra_steps": (n - reference_len) if reference_len is not None else None,
        "efficiency": (reference_len / n) if (reference_len and n) else None,
    }
