from trading_agents.db import connect
from trading_agents.reflect import lessons_block


def test_lessons_block_filters_scope_and_kept(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "t.db"))
    monkeypatch.setenv("OPENAI_API_KEY", "x")
    monkeypatch.setenv("ALPHAVANTAGE_API_KEY", "x")
    rows = [
        (1, "2026-01-01T00:00:00", "AAPL", "2026-01-01", "technical", "tech lesson", 1, "bad", -3.0),
        (2, "2026-01-02T00:00:00", "AAPL", "2026-01-02", "risk", "risk lesson", 1, "good", 2.0),
        (3, "2026-01-03T00:00:00", "AAPL", "2026-01-03", "technical", "dropped lesson", 0, "bad", -2.0),
        (4, "2026-01-04T00:00:00", "AAPL", "2026-01-04", "general", "general lesson", 1, "good", 1.5),
    ]
    with connect() as conn:
        conn.executemany(
            "INSERT INTO lessons (decision_id, created_at, ticker, as_of, scope, lesson, kept, "
            "outcome_label, return_pct) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            rows,
        )
    block = lessons_block("technical")
    assert "tech lesson" in block and "general lesson" in block
    assert "risk lesson" not in block and "dropped lesson" not in block
    assert lessons_block("fundamental").count("lesson") >= 1