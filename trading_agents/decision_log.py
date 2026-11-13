import json
import sqlite3
import sys
from datetime import datetime, timezone

from trading_agents.config import get_settings
from trading_agents.db import connect
from trading_agents.state import TradingState


def _jsonable(value):
    """Pydantic objects become dicts; everything else is already plain data."""
    return value.model_dump() if hasattr(value, "model_dump") else value


def save_decision(state: dict, model_tag: str | None = None) -> int:
    decision = state["decision"]
    outcome = state["outcome"]
    full_state = json.dumps({k: _jsonable(v) for k, v in state.items()})

    with connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO decisions (
                run_at, ticker, model, action, shares, entry_price,
                stop_loss_price, take_profit_price, confidence, risk_level,
                verdict_leaning, verdict_conviction, rationale, state_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                datetime.now(timezone.utc).isoformat(),
                decision.ticker,
                model_tag or get_settings().openai_model,
                decision.action,
                decision.shares,
                decision.entry_price,
                decision.stop_loss_price,
                decision.take_profit_price,
                decision.confidence,
                decision.risk_level,
                outcome.leaning,
                outcome.conviction,
                decision.rationale,
                full_state,
            ),
        )
        return cursor.lastrowid


def log_node(state: TradingState) -> dict:
    """Final graph node: persist the run."""
    decision_id = save_decision(state)
    print(f"-> logged as decision #{decision_id}")
    return {"decision_id": decision_id}


def recent_decisions(ticker: str | None = None, limit: int = 10) -> list[sqlite3.Row]:
    query = "SELECT * FROM decisions"
    params: list = []
    if ticker:
        query += " WHERE ticker = ?"
        params.append(ticker)
    query += " ORDER BY id DESC LIMIT ?"
    params.append(limit)
    with connect() as conn:
        conn.row_factory = sqlite3.Row
        return conn.execute(query, params).fetchall()


def get_decision(decision_id: int) -> sqlite3.Row | None:
    with connect() as conn:
        conn.row_factory = sqlite3.Row
        return conn.execute(
            "SELECT * FROM decisions WHERE id = ?", (decision_id,)
        ).fetchone()


if __name__ == "__main__":
    if len(sys.argv) > 1:  # python -m trading_agents.decision_log 3
        row = get_decision(int(sys.argv[1]))
        if row is None:
            print("No such decision.")
        else:
            print(json.dumps(json.loads(row["state_json"]), indent=2))
    else:
        rows = recent_decisions()
        if not rows:
            print("No decisions logged yet.")
        for r in rows:
            print(
                f"#{r['id']:<3} {r['run_at'][:19]}  {r['ticker']:<6} {r['action']:<4} "
                f"x{r['shares']:<4} @ {r['entry_price']:<8} conf={r['confidence']} "
                f"verdict={r['verdict_leaning']}({r['verdict_conviction']}) "
                f"result={r['outcome_label'] or 'pending'}"
            )