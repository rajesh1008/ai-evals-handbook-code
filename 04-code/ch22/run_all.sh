#!/usr/bin/env bash
# Chapter 22 lab. Traffic and truth are SIMULATED (fixture.py, seed 2026). Reply text, judge verdicts,
# critiques and rationale readings are REAL model runs cached in out/*.jsonl; nothing here calls the
# model unless you pass 'run' to gen.py or judges.py (needs ANTHROPIC_API_KEY, never printed).
set -euo pipefail
cd "$(dirname "$0")"
python3 fixture.py | head -4
python3 gen.py
python3 lab.py
python3 inject.py
python3 try_its.py
(cd ../truss && python3 -m pytest -q tests/test_ch22.py | tail -1 && python3 -m pytest -q | tail -1)
