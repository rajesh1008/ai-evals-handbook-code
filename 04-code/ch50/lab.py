"""Ch50 lab: Truss configuration linter + release-gate adjudicator."""
from __future__ import annotations
import hashlib, json
from pathlib import Path

OUT = Path(__file__).parent / "out"


def lint_config(cfg: dict) -> dict:
    """Structural linter: required keys, types, digest shape. Does NOT prove judge validity."""
    errors = []
    for key in ("name", "suite_digest", "population", "metric", "bound", "judge", "gate", "owner"):
        if key not in cfg:
            errors.append(f"missing:{key}")
    if cfg.get("suite_digest") and len(str(cfg["suite_digest"])) < 8:
        errors.append("suite_digest_too_short")
    if not isinstance(cfg.get("bound"), (int, float)):
        errors.append("bound_not_numeric")
    judge = cfg.get("judge") or {}
    for jk in ("id", "validated", "gold_n"):
        if jk not in judge:
            errors.append(f"judge_missing:{jk}")
    gate = cfg.get("gate") or {}
    if gate.get("kind") not in ("release", "monitor", "shadow"):
        errors.append("gate_kind_invalid")
    # Empty population is a lint error (structural)
    if "population" in cfg and not str(cfg.get("population") or "").strip():
        errors.append("population_empty")
    return {
        "config": cfg.get("name"),
        "lint_pass": len(errors) == 0,
        "errors": errors,
        "note": "linter checks structure only; judge validity is a separate gate",
    }


def release_gate(cfg: dict, lint: dict) -> dict:
    """Release gate: fail-closed when judge unvalidated even if linter passed."""
    if not lint["lint_pass"]:
        return {
            "config": cfg["name"],
            "gate_result": "HOLD",
            "reason": "lint_failed",
            "lint_errors": lint["errors"],
        }
    judge = cfg["judge"]
    requires = bool(cfg.get("gate", {}).get("requires_validated_judge", True))
    if requires and not judge.get("validated"):
        return {
            "config": cfg["name"],
            "gate_result": "HOLD",
            "reason": "unvalidated_judge",
            "judge_id": judge.get("id"),
            "gold_n": judge.get("gold_n"),
            "FAILURE_INJECTION_CAUGHT": bool(cfg.get("FAILURE_INJECTION")),
        }
    return {
        "config": cfg["name"],
        "gate_result": "PASS",
        "reason": "lint_ok_and_judge_validated",
        "judge_id": judge.get("id"),
    }


def main():
    fix = json.loads((OUT / "fixture.json").read_text())
    rows = []
    for name, cfg in fix["configs"].items():
        lint = lint_config(cfg)
        gate = release_gate(cfg, lint)
        rows.append({"lint": lint, "gate": gate, "FAILURE_INJECTION": bool(cfg.get("FAILURE_INJECTION"))})
    # Primary inject: config that lints clean but HOLD on unvalidated judge
    inject_row = next(r for r in rows if r["FAILURE_INJECTION"])
    evidence = {
        "control_objective": "config linter passes structure; release gate still HOLDs unvalidated judges",
        "digest": fix["digest"],
        "seed": fix["seed"],
        "n_configs": fix["n_configs"],
        "rows": rows,
        "inject_config": inject_row["lint"]["config"],
        "inject_lint_pass": inject_row["lint"]["lint_pass"],
        "inject_gate": inject_row["gate"]["gate_result"],
        "inject_reason": inject_row["gate"]["reason"],
        "inject_caught": (
            inject_row["lint"]["lint_pass"]
            and inject_row["gate"]["gate_result"] == "HOLD"
            and inject_row["gate"]["reason"] == "unvalidated_judge"
        ),
        "SIMULATED": True,
        "live_provider_eval_sweeps": "PENDING",
        "paid_calls": False,
        "ch16_ceiling_kinds_unchanged": True,
        "ch16_ceiling_sum": 6.291941,
    }
    raw = json.dumps(evidence, sort_keys=True, separators=(",", ":")).encode()
    record = {"record_sha12": hashlib.sha256(raw).hexdigest()[:12], "experiment_id": "ch50-config-linter-unvalidated-judge"}
    payload = {"SIMULATED": True, "evidence_pack": evidence, "record": record, "digest": fix["digest"]}
    (OUT / "lab.json").write_text(json.dumps(payload, indent=2))
    print(json.dumps({
        "digest": fix["digest"],
        "record": record["record_sha12"],
        "inject_caught": evidence["inject_caught"],
        "inject_lint_pass": evidence["inject_lint_pass"],
        "inject_gate": evidence["inject_gate"],
    }, indent=2))


if __name__ == "__main__":
    main()
