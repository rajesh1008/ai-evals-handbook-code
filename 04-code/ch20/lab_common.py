"""Small helpers shared by the Chapter 20 scripts."""
import hashlib
import json


def digest(rows):
    return hashlib.sha256(json.dumps(rows, sort_keys=True, default=str).encode()).hexdigest()[:12]
