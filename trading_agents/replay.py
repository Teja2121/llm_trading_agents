import sys

from trading_agents.alphavantage import AlphaVantageClient
from trading_agents.analysts import technical_analyst
from trading_agents.decision_log import save_decision
from trading_agents.indicators import compute_indicators
from trading_agents.risk import compute_risk_limits
from trading_agents.schemas import DebateOutcome, FinalDecision

EQUITY = 100_000.0


def replay(ticker: str, offsets) -> None:
    prices = AlphaVantageClient().daily_prices(ticker)
    for offset in offsets:
        history = prices[: len(prices) + offset + 1]  # only data up to that day
        indicators = compute_indicators(history)
        report = technical_analyst(ticker, indicators)
        limits = compute_risk_limits(indicators, EQUITY)

        buy = report.stance == "bullish" and report.confidence >= 0.6 and limits["max_shares"] > 0
        shares = limits["max_shares"] // 2 if buy else 0
        price = limits["entry_price"]
        decision = FinalDecision(
            ticker=ticker,
            action="BUY" if buy else "HOLD",
            shares=shares,
            entry_price=price,
            stop_loss_price=limits["stop_loss_price"] if buy else None,
            take_profit_price=limits["take_profit_price"] if buy else None,
            position_value=round(shares * price, 2),
            risk_amount=round(shares * price * limits["stop_pct"] / 100, 2) if buy else 0.0,
            confidence=report.confidence,
            risk_level="n/a",
            rationale="Replay (technical only): " + " ".join(report.key_points[:2]),
        )
        outcome = DebateOutcome(
            leaning=report.stance,
            conviction=report.confidence,
            summary="Replay: technical analyst only",
            strongest_bull_point="n/a",
            strongest_bear_point="n/a",
            unresolved_questions=[],
        )
        state = {
            "ticker": ticker, "company": ticker, "indicators": indicators,
            "technical_report": report, "risk_limits": limits, "risk_flags": [],
            "adjustments": [], "outcome": outcome, "decision": decision,
        }
        decision_id = save_decision(state, model_tag="replay-technical")
        print(
            f"#{decision_id} {indicators['as_of']}: {report.stance} ({report.confidence}) "
            f"-> {decision.action} x{shares}"
        )


if __name__ == "__main__":
    replay(sys.argv[1] if len(sys.argv) > 1 else "AAPL", range(-35, -9, 5))