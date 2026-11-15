#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p out
python3 lab.py | tee out/lab.txt
python3 inject.py | tee out/inject.txt
python3 try_its.py | tee out/try_its.txt
{
  echo "==== lab ===="
  cat out/lab.txt
  echo
  echo "==== inject ===="
  cat out/inject.txt
  echo
  echo "==== try_its ===="
  cat out/try_its.txt
  if [[ -f out/real_grounding.json ]]; then
    echo
    echo "==== real_grounding ===="
    python3 real_grounding.py report
    # OUTPUT.txt also carries the block as it was first appended after the live run; same cached file.
    echo
    echo "==== real_grounding (LIVE Anthropic) ===="
    python3 real_grounding.py report
  fi
} | tee OUTPUT.txt
