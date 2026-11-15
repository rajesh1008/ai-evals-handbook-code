#!/usr/bin/env bash
# Chapter 18 lab. Labels and judge verdicts are SIMULATED (see fixture.py).
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p out
python3 lab.py
python3 inject.py
python3 try_its.py
(cd ../truss && python3 -m pytest -q tests/test_ch18.py)
