import json

from trading_agents.alphavantage import AlphaVantageClient
from trading_agents.indicators import compute_indicators
from trading_agents.llm import get_llm
from trading_agents.schemas import AnalystReport

TECHNICAL_SYSTEM = """You are the technical analyst on a trading desk.
Use ONLY the indicator data provided. Do not invent numbers or use outside knowledge.
Cite specific values (RSI, MACD histogram, price vs moving averages) in your key points.
If signals conflict (for example, strong trend but overbought RSI), say so and lower your confidence.
RSI above 70 is overbought and below 30 is oversold. You analyse price action only, not the business."""


def technical_analyst(ticker: str, indicators: dict) -> AnalystReport:
    llm = get_llm().with_structured_output(AnalystReport)
    return llm.invoke(
        [
            ("system", TECHNICAL_SYSTEM),
            ("human", f"Ticker: {ticker}\nIndicators:\n{json.dumps(indicators, indent=2)}"),
        ]
    )


if __name__ == "__main__":
    ticker = "AAPL"
    prices = AlphaVantageClient().daily_prices(ticker)
    indicators = compute_indicators(prices)
    print("INDICATORS:", json.dumps(indicators, indent=2))

    report = technical_analyst(ticker, indicators)
    print("\nREPORT:", report.model_dump_json(indent=2))