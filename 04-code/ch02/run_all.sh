#!/usr/bin/env bash
# Chapter 2 Lab: runs every step and writes OUTPUT.txt
set -euo pipefail
cd "$(dirname "$0")"
{
  echo "### lab.py"; python3 lab.py
  echo; echo "### inject.py"; python3 inject.py
  echo; echo "### gate_run.py"; python3 gate_run.py
  echo; echo "### monitor.py"; python3 monitor.py
  echo; echo "### try_its.py"; python3 try_its.py
} | tee OUTPUT.txt
(cd ../truss && python3 -m pytest -q)
