"""Eval data governance helpers (Chapter 33 / Truss v5.5).

Run manifests, retention jobs, redaction signal checks, residency tags,
gold access records and eval inventory rows.
"""
from __future__ import annotations
import hashlib, json
from dataclasses import asdict, dataclass
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class RunManifest:
    run_id: str
    model_pin: str
    prompt_digest: str
    dataset_digest: str
    seed: int
    suite: str
    created_at: str
    residency: str
    owner: str

    def digest(self) -> str:
        blob = json.dumps(asdict(self), sort_keys=True).encode()
        return hashlib.sha256(blob).hexdigest()[:12]

    def as_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["manifest_digest"] = self.digest()
        return d


def build_manifest(**kwargs: Any) -> dict[str, Any]:
    m = RunManifest(**kwargs)
    required = ["run_id", "model_pin", "prompt_digest", "dataset_digest", "seed", "suite", "created_at", "residency", "owner"]
    for k in required:
        if not str(getattr(m, k)):
            raise ValueError(f"missing {k}")
    return m.as_dict()


def reexecute_from_manifest(manifest: Mapping[str, Any], available: Mapping[str, Any]) -> dict[str, Any]:
    """Check whether pins in manifest still resolve; return replay verdict."""
    checks = {}
    for key in ("model_pin", "prompt_digest", "dataset_digest", "seed", "suite"):
        checks[key] = available.get(key) == manifest.get(key)
    ok = all(checks.values())
    return {"ok": ok, "checks": checks, "run_id": manifest.get("run_id"), "manifest_digest": manifest.get("manifest_digest")}


def redaction_signal_check(
    rows: Sequence[Mapping[str, Any]],
    *,
    metric_fields: Sequence[str],
    redacted_fields: Sequence[str],
) -> dict[str, Any]:
    """Fail when redaction removed fields a metric still needs."""
    missing = [f for f in metric_fields if f in redacted_fields]
    destroyed = []
    for r in rows:
        for f in metric_fields:
            if r.get(f) in (None, "", "[REDACTED]"):
                destroyed.append({"id": r.get("case_id"), "field": f})
    return {
        "metric_fields": list(metric_fields),
        "redacted_fields": list(redacted_fields),
        "overlap_removed": missing,
        "n_destroyed": len(destroyed),
        "destroyed": destroyed[:20],
        "signal_ok": len(missing) == 0 and len(destroyed) == 0,
    }


def retention_job(
    items: Sequence[Mapping[str, Any]],
    *,
    retain_days: int,
    as_of_day: int,
    age_key: str = "age_days",
) -> dict[str, Any]:
    keep, retire = [], []
    for it in items:
        age = int(it[age_key])
        if age > retain_days:
            retire.append(it.get("case_id"))
        else:
            keep.append(it.get("case_id"))
    n = len(keep) + len(retire)
    return {
        "retain_days": retain_days,
        "as_of_day": as_of_day,
        "n": n,
        "n_keep": len(keep),
        "n_retire": len(retire),
        "retire_rate": (len(retire) / n) if n else 0.0,
        "retire_ids": retire,
        "keep_ids": keep,
    }


def residency_tag(region: str, allowed: Sequence[str]) -> dict[str, Any]:
    ok = region in allowed
    return {"region": region, "allowed": list(allowed), "ok": ok}


def gold_access_record(actor: str, role: str, action: str, case_id: str, ts: str) -> dict[str, Any]:
    if action not in {"read", "export", "label", "deny"}:
        raise ValueError(action)
    return {"actor": actor, "role": role, "action": action, "case_id": case_id, "ts": ts}


def eval_inventory(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    required = {"artefact", "location", "owner", "residency", "retention_days"}
    out = []
    for r in rows:
        miss = required - set(r)
        if miss:
            raise ValueError(f"inventory missing {sorted(miss)}")
        out.append({k: r[k] for k in list(required) + (["notes"] if "notes" in r else [])})
    return out
