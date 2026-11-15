#!/usr/bin/env bash
# Regenerates OUTPUT.txt for the Chapter 1 Lab.
set -euo pipefail
cd "$(dirname "$0")"
unset COMPASS_TEMPERATURE
{
  for s in lab.py inject_failure.py try_temperature.py try_ten_runs.py try_ryan_sheet.py; do
    echo "\$ python3 $s"; python3 "$s"; echo
  done
} > OUTPUT.txt
