#!/usr/bin/env bash
# Chapter 13 lab. Model replies are cached in out/; pass "run" to call the models for anything uncached
# (needs ANTHROPIC_API_KEY in the environment; it is never printed).
set -euo pipefail
cd "$(dirname "$0")"
MODE="${1:-}"
python3 lab.py 2>&1 | grep -v ScriptRunContext
python3 try_its.py
python3 listings.py
python3 june_docs.py
python3 june_run.py $MODE
python3 probe.py $MODE
(cd ../truss && python3 -m pytest -q tests/test_ch13.py | tail -1)
