"""Runnable path for a live three-model bias battery.

Live model calls are not executed in this chapter. The script records a pending
run and exits 0. When the pending runs are made, this file should be wired
to a provider client and write out/real_battery.json with position, verbosity
and label results for three models.

Usage: python3 real_judge.py
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "out" / "real_battery.json"

PROMPT = (
    "You are checking two explanations of a late fee (A and B) against the "
    "same tool result. Say which explanation states the fee and the waiver "
    "rule more accurately. Reply with JSON only: {\"winner\": \"A\"} or "
    "{\"winner\": \"B\"} or {\"winner\": \"tie\"}."
)


def main():
    payload = {
        "status": "pending",
        "command": "cd 04-code/ch17 && python3 real_judge.py",
        "would_call": "three judge models x 200 pairs x (swap + 30% pad) pairwise prompts",
        "replaces": (
            "Chapter 17 numbers marked [RESULT PENDING] for a live "
            "cross-family bias battery (position, verbosity, labels)."
        ),
        "prompt_preview": PROMPT[:220],
    }
    print("[RESULT PENDING: run `cd 04-code/ch17 && python3 real_judge.py` "
          "once a provider client is wired]")
    print("This would judge 200 pairs twice (slots swapped) and once with "
          "reply A padded by 30%, on three models.")
    OUT.write_text(json.dumps(payload, indent=2))
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
