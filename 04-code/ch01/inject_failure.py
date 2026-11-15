"""Failure injection: a debugging override hides the variance until run 3.

Runs 1 and 2 happen in a notebook where someone once set
COMPASS_TEMPERATURE=0 to make a demo repeatable. Run 3 is the nightly job,
which starts in a fresh process without the override.
"""
import os

from replay import (check_manifest, flipped, open_store, pick_conversations,
                    replay)

db = open_store()
convs = pick_conversations(db)
os.environ["COMPASS_TEMPERATURE"] = "0"          # left over from debugging
first = replay(convs, runs=2)
print("runs 1-2 changed verdicts:", len(flipped(first)), "of", len(first))
del os.environ["COMPASS_TEMPERATURE"]            # the nightly job's fresh shell
third = replay(convs, runs=3)                     # we keep only its run 3
merged = {t: first[t] + [third[t][2]] for t in first}
print("runs 1-3 changed verdicts:", len(flipped(merged)), "of", len(merged))
for t in flipped(merged):
    print("  ", t, [(r["temperature"], r["verdict"]) for r in merged[t]])
try:
    check_manifest(merged)
except ValueError as err:
    print("manifest check:", err)
