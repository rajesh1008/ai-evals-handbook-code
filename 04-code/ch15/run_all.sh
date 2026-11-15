#!/usr/bin/env bash
# Chapter 15 lab. Model replies are cached in out/; pass "run" to call the model for anything uncached
# (needs ANTHROPIC_API_KEY in the environment; it is never printed).
set -euo pipefail
cd "$(dirname "$0")"
MODE="${1:-}"
python3 probe.py $MODE
python3 lab.py
python3 inject.py
python3 try_its.py
(cd ../truss && python3 -m pytest -q tests/test_ch15.py | tail -1)
