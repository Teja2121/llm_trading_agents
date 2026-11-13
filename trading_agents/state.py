import operator
from typing import Annotated, TypedDict

from trading_agents.schemas import AnalystReport, DebateOutcome, NewsReport, RiskAssessment, FinalDecision


class TradingState(TypedDict):
    # inputs / loaded data
    ticker: str
    company: str
    indicators: dict
    facts: dict
    market: dict
    headlines: list[dict]
    # analyst outputs (each written by exactly one node)
    technical_report: AnalystReport
    fundamental_report: AnalystReport
    news_report: NewsReport
    # debate
    debate: Annotated[list[str], operator.add]
    round: int
    max_rounds: int
    # verdict
    outcome: DebateOutcome
    # portfolio inputs
    equity: float
    position_shares: int
    # risk and decision
    risk_limits: dict
    risk_flags: list[str]
    risk_assessment: RiskAssessment
    adjustments: Annotated[list[str], operator.add]  # every code override, for the log
    decision: FinalDecision
    decision_id: int