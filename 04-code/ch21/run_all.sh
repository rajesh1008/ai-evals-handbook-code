#!/usr/bin/env bash
# Chapter 21 lab. Judges and gold are SIMULATED (see fixture.py). real_judge.py records a
# pending live run and does not call a model.
set -euo pipefail
cd "$(dirname "$0")"
python3 lab.py
python3 inject.py
python3 try_its.py
python3 real_judge.py
(cd ../truss && python3 -m pytest -q tests/test_ch21.py | tail -1)
