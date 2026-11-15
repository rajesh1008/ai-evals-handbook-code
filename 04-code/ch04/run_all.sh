#!/usr/bin/env bash
# Chapter 4 Lab: tags every check with a layer, runs the suite by layer, writes OUTPUT.txt
set -euo pipefail
cd "$(dirname "$0")"
{
  echo "### lab.py"; python3 lab.py
  echo; echo "### inject.py"; python3 inject.py
  echo; echo "### try_its.py"; python3 try_its.py
} | tee OUTPUT.txt
(cd ../truss && python3 -m pytest -q)
