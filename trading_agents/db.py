import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

from trading_agents.config import get_settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS api_cache (
    cache_key  TEXT PRIMARY KEY,
    payload    TEXT NOT NULL,
    fetched_at TEXT NOT NULL
);
"""


@contextmanager
def connect():
    """Open the database, make sure tables exist, commit and close afterwards."""
    path = Path(get_settings().db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    try:
        conn.executescript(SCHEMA)
        yield conn
        conn.commit()
    finally:
        conn.close()


def cache_get(key: str, max_age_hours: float):
    """Return cached data if it exists and is fresh enough, else None."""
    with connect() as conn:
        row = conn.execute(
            "SELECT payload, fetched_at FROM api_cache WHERE cache_key = ?", (key,)
        ).fetchone()
    if row is None:
        return None
    payload, fetched_at = row
    age = datetime.now(timezone.utc) - datetime.fromisoformat(fetched_at)
    if age > timedelta(hours=max_age_hours):
        return None
    return json.loads(payload)


def cache_set(key: str, data) -> None:
    with connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO api_cache (cache_key, payload, fetched_at) "
            "VALUES (?, ?, ?)",
            (key, json.dumps(data), datetime.now(timezone.utc).isoformat()),
        )