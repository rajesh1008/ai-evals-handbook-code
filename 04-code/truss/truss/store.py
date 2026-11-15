"""Read access to the Compass trace store (SQLite)."""
import sqlite3
from pathlib import Path

DEFAULT_STORE = Path(__file__).resolve().parent.parent / "fixtures" / "compass_pilot.db"


def open_store(path=DEFAULT_STORE):
    """Open the trace store read-only so an evaluation can never write to it."""
    return sqlite3.connect(f"file:{path}?mode=ro", uri=True)
