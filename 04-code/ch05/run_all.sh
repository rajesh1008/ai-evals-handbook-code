#!/usr/bin/env bash
# Chapter 5 Lab: reads 150 December traces, builds taxonomy v0.1; writes OUTPUT.txt
set -euo pipefail
cd "$(dirname "$0")"
{
  echo "### lab.py"; python3 lab.py
  echo; echo "### inject.py"; python3 inject.py
  echo; echo "### model_coding.py (cached real responses; --live re-calls the API)"; python3 model_coding.py
  echo; echo "### try_its.py"; python3 try_its.py
} | tee OUTPUT.txt
(cd ../truss && python3 -m pytest -q)
