import json
import sqlite3
import sys
from datetime import datetime, timezone

from trading_agents.alphavantage import AlphaVantageClient
from trading_agents.db import connect

HORIZON_DAYS = 5
GOOD_RETURN_PCT = 1.0      # BUY: at least +1% is good
BAD_RETURN_PCT = -1.0      # BUY: at most -1% is bad
MISSED_GAIN_PCT = 3.0      # HOLD/SELL: stock rose 3%+ after we stayed out
AVOIDED_LOSS_PCT = -1.0    # HOLD/SELL: stock fell 1%+ after we stayed out


def _result(entry, exit_price, reason, date):
    return {
        "exit_price": round(exit_price, 2),
        "exit_reason": reason,
        "exit_date": date,
        "return_pct": round((exit_price / entry - 1) * 100, 2),
    }


def simulate_trade(prices, as_of, entry, stop, take_profit, horizon=HORIZON_DAYS):
    """Walk forward from as_of. Returns None if there isn't enough data yet."""
    if not prices or as_of < prices[0]["date"]:
        return None  # decision is older than our price window
    future = [p for p in prices if p["date"] > as_of][:horizon]
    if len(future) < horizon:
        return None

    for day in future:
        if stop is not None and day["low"] <= stop:
            # a gap down through the stop fills at the open, which is worse
            return _result(entry, min(stop, day["open"]), "stop hit", day["date"])
        if take_profit is not None and day["high"] >= take_profit:
            return _result(entry, max(take_profit, day["open"]), "target hit", day["date"])

    last = future[-1]
    return _result(entry, last["close"], "horizon", last["date"])


def label_outcome(action, return_pct):
    if action == "BUY":
        if return_pct >= GOOD_RETURN_PCT:
            return "good"
        if return_pct <= BAD_RETURN_PCT:
            return "bad"
        return "neutral"
    # HOLD or SELL: we stayed out, so judge by what we missed or avoided
    if return_pct >= MISSED_GAIN_PCT:
        return "bad"
    if return_pct <= AVOIDED_LOSS_PCT:
        return "good"
    return "neutral"


def evaluate_pending(horizon=HORIZON_DAYS) -> int:
    with connect() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT id, ticker, action, entry_price, stop_loss_price, "
            "take_profit_price, state_json FROM decisions WHERE evaluated_at IS NULL"
        ).fetchall()

    av = AlphaVantageClient()
    prices_by_ticker: dict = {}
    evaluated = 0
    for r in rows:
        as_of = json.loads(r["state_json"])["indicators"]["as_of"]
        if r["ticker"] not in prices_by_ticker:
            prices_by_ticker[r["ticker"]] = av.daily_prices(r["ticker"])

        result = simulate_trade(
            prices_by_ticker[r["ticker"]], as_of, r["entry_price"],
            r["stop_loss_price"], r["take_profit_price"], horizon,
        )
        if result is None:
            print(f"#{r['id']} {r['ticker']} (as of {as_of}): not enough trading days yet")
            continue

        label = label_outcome(r["action"], result["return_pct"])
        with connect() as conn:
            conn.execute(
                "UPDATE decisions SET evaluated_at = ?, eval_price = ?, "
                "return_pct = ?, outcome_label = ? WHERE id = ?",
                (
                    datetime.now(timezone.utc).isoformat(),
                    result["exit_price"], result["return_pct"], label, r["id"],
                ),
            )
        print(
            f"#{r['id']} {r['ticker']} {r['action']}: {result['return_pct']}% "
            f"({result['exit_reason']} on {result['exit_date']}) -> {label}"
        )
        evaluated += 1
    return evaluated


if __name__ == "__main__":
    if "--demo" in sys.argv:
        # Hypothetical BUYs on past dates, using our 5.28% stop and 2:1 target. Nothing is saved.
        prices = AlphaVantageClient().daily_prices("AAPL")
        print("Hypothetical AAPL buys, evaluated over 5 trading days:")
        for i in range(-40, -9, 5):
            day = prices[i]
            entry = day["close"]
            stop = round(entry * (1 - 0.0528), 2)
            target = round(entry * (1 + 2 * 0.0528), 2)
            print(day["date"], entry, simulate_trade(prices, day["date"], entry, stop, target))
    else:
        print(f"{evaluate_pending()} decision(s) evaluated.")