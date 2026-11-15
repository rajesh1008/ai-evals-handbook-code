#!/bin/bash
# Chapter 16 lab. Replays cached REAL model runs over the SIMULATED fixture.
# No API key is required unless you pass `run` to judges.py, gen.py or agent.py.
set -euo pipefail
cd "$(dirname "$0")"
echo "===== fixture ====="
python3 fixture.py
echo
echo "===== lab ====="
python3 lab.py
echo
echo "===== inject ====="
python3 inject.py
echo
echo "===== try_its ====="
python3 try_its.py
