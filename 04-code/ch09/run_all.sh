#!/usr/bin/env bash
# Chapter 9 Lab: eight code checks for Compass (format, policy, arithmetic, citations), composition,
# the fee replay set and the gate, census rates, validation, the day-count injection, three try-its,
# and a small real model run comparing a judge with the code checks.
set -euo pipefail
cd "$(dirname "$0")"
{
  echo "### lab.py"; python3 lab.py
  echo; echo "### inject.py"; python3 inject.py
  echo; echo "### try_its.py"; python3 try_its.py
  echo; echo "### judge_vs_code.py (real model run, 1 November 2026; analyses the cached calls)"; python3 judge_vs_code.py
} | tee OUTPUT.txt
(cd ../truss && python3 -m pytest -q)
