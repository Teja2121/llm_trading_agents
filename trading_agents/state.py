import operator
from typing import Annotated, TypedDict

from trading_agents.schemas import AnalystReport, DebateOutcome, NewsReport


class TradingState(TypedDict):
    # inputs / loaded data
    ticker: str
    company: str
    indicators: dict
    facts: dict
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