"""Failure injection: metric definition drift between pack and dashboard."""
from __future__ import annotations
import json
from pathlib import Path

OUT = Path(__file__).parent / "out"


def drift_caught(pack_metric: dict, dash_metric: dict) -> dict:
    mismatches = []
    for key in ("definition", "unit", "denominator", "version"):
        if pack_metric.get(key) != dash_metric.get(key):
            mismatches.append({"field": key, "pack": pack_metric.get(key), "dashboard": dash_metric.get(key)})
    return {
        "injection": "metric_definition_drift_pack_vs_dashboard",
        "caught": bool(mismatches),
        "mismatch_count": len(mismatches),
        "mismatches": mismatches,
        "rule": "pack metric is authoritative; dashboard must match unit, denominator, definition, version",
    }


def main():
    fix = json.loads((OUT / "fixture.json").read_text())
    lab = json.loads((OUT / "lab.json").read_text())
    result = drift_caught(fix["pack_metric"], fix["dashboard_metric_drift"])
    result["pack_sha12"] = lab["pack_sha12"]
    result["table_sha12"] = lab["table_sha12"]
    (OUT / "inject.json").write_text(json.dumps(result, indent=2) + "\n")
    print("drift_caught", result["caught"], "n", result["mismatch_count"])


if __name__ == "__main__":
    main()
