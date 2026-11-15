#!/usr/bin/env bash
# Chapter 20 lab. Decisions, gold and confidence fields are SIMULATED (see
# fixture.py). real_confidence.py records a pending live run and does not call a model.
set -euo pipefail
cd "$(dirname "$0")"
python3 lab.py
python3 inject.py
python3 try_its.py
python3 real_confidence.py
python3 listings.py
(cd ../truss && python3 -m pytest -q tests/test_ch20.py | tail -1)
