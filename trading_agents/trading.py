import json
import math

from trading_agents.debate import reports_text
from trading_agents.llm import get_llm
from trading_agents.risk import (
    SIZE_FRACTION, SIZE_ORDER, compute_risk_limits, risk_flags,
)
from trading_agents.schemas import FinalDecision, RiskAssessment, TradeDecision
from trading_agents.state import TradingState
from trading_agents.reflect import lessons_block

RISK_SYSTEM = """You are the risk manager on a trading desk.
You do not decide direction; you decide how much risk is acceptable.
You receive the research verdict, the analyst reports, risk flags computed in code, and hard limits
already computed in code (stop-loss price and maximum shares).
Choose a size: none, quarter, half or full of the maximum allowed. Choose 'none' if the evidence is
too weak or the risk too high. Several risk flags, or conviction below 0.6, argue for a smaller size.
Every main risk must cite a specific number. You cannot raise the limits; you only choose how much
of them to use."""

TRADER_SYSTEM = """You are the trader for a long-only paper portfolio.
BUY opens or adds to a long position. SELL reduces or closes an existing long position. HOLD does nothing.
You receive the research verdict, the risk manager's assessment and the current position.
If the risk manager's size is 'none', choose HOLD (or SELL if a position exists and the verdict is bearish).
A bearish verdict with no position means HOLD (stay out), not SELL.
Your confidence cannot exceed the research director's conviction."""


def risk_node(state: TradingState) -> dict:
    print("-> risk manager")
    limits = compute_risk_limits(state["indicators"], state["equity"])
    flags = risk_flags(state["indicators"], state["facts"], state["market"])

    llm = get_llm(temperature=0.2).with_structured_output(RiskAssessment)
    prompt = (
        f"Ticker: {state['ticker']} ({state['company']})\n\n"
        f"Research verdict:\n{state['outcome'].model_dump_json(indent=2)}\n\n"
        f"Risk flags (computed in code): {flags or 'none'}\n\n"
        f"Hard limits (computed in code):\n{json.dumps(limits, indent=2)}\n\n"
        f"Market conditions (SPY, computed in code):\n{json.dumps(state['market'], indent=2)}\n\n"
        f"Analyst reports:\n{reports_text(state)}"
    )
    assessment = llm.invoke([("system", RISK_SYSTEM + lessons_block("risk")), ("human", prompt)])

    adjustments = []
    too_risky = assessment.risk_level == "high" or len(flags) >= 3
    if too_risky and SIZE_ORDER.index(assessment.size) > SIZE_ORDER.index("half"):
        adjustments.append(
            f"size reduced from {assessment.size} to half "
            f"(risk level {assessment.risk_level}, {len(flags)} flags)"
        )
        assessment.size = "half"

    return {
        "risk_limits": limits,
        "risk_flags": flags,
        "risk_assessment": assessment,
        "adjustments": adjustments,
    }


def trader_node(state: TradingState) -> dict:
    print("-> trader")
    outcome, limits, assessment = (
        state["outcome"], state["risk_limits"], state["risk_assessment"],
    )
    llm = get_llm(temperature=0.2).with_structured_output(TradeDecision)
    prompt = (
        f"Ticker: {state['ticker']} ({state['company']})\n"
        f"Current position: {state['position_shares']} shares\n\n"
        f"Research verdict:\n{outcome.model_dump_json(indent=2)}\n\n"
        f"Risk assessment:\n{assessment.model_dump_json(indent=2)}"
    )
    trade = llm.invoke([("system", TRADER_SYSTEM + lessons_block("trader")), ("human", prompt)])

    # ---- code guards: what must hold, whatever the LLM said ----
    adjustments = []
    action = trade.action
    confidence = trade.confidence

    if confidence > outcome.conviction:
        adjustments.append(f"trader confidence {confidence} capped to {outcome.conviction}")
        confidence = outcome.conviction
    if action == "BUY" and outcome.leaning == "bearish":
        adjustments.append("BUY changed to HOLD: research verdict is bearish")
        action = "HOLD"
    if action == "SELL" and state["position_shares"] == 0:
        adjustments.append("SELL changed to HOLD: no position to sell")
        action = "HOLD"

    price = limits["entry_price"]
    shares = 0
    if action == "BUY":
        shares = math.floor(limits["max_shares"] * SIZE_FRACTION[assessment.size])
        if shares == 0:
            adjustments.append("BUY changed to HOLD: risk-adjusted size is 0 shares")
            action = "HOLD"
    elif action == "SELL":
        shares = state["position_shares"]  # simple rule: close the whole position

    buying = action == "BUY"
    decision = FinalDecision(
        ticker=state["ticker"],
        action=action,
        shares=shares,
        entry_price=price,
        stop_loss_price=limits["stop_loss_price"] if buying else None,
        take_profit_price=limits["take_profit_price"] if buying else None,
        position_value=round(shares * price, 2),
        risk_amount=round(shares * price * limits["stop_pct"] / 100, 2) if buying else 0.0,
        confidence=confidence,
        risk_level=assessment.risk_level,
        rationale=trade.rationale,
    )
    return {"decision": decision, "adjustments": adjustments}