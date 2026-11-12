import json

from trading_agents.alphavantage import AlphaVantageClient
from trading_agents.indicators import compute_indicators
from trading_agents.llm import get_llm
from trading_agents.schemas import AnalystReport

from trading_agents.fundamentals import build_fundamental_facts
from trading_agents.yahoo import YahooClient

TECHNICAL_SYSTEM = """You are the technical analyst on a trading desk.
Use ONLY the indicator data provided. Do not invent numbers or use outside knowledge.
Cite specific values (RSI, MACD histogram, price vs moving averages) in your key points.
If signals conflict (for example, strong trend but overbought RSI), say so and lower your confidence.
RSI above 70 is overbought and below 30 is oversold. You analyse price action only, not the business. 
Every risk must be tied to a specific number in the data; do not give generic market risks.
Treat weak volume (below 0.8 of average) or a flat MACD histogram as reasons to cap confidence at 0.7."""


def technical_analyst(ticker: str, indicators: dict) -> AnalystReport:
    llm = get_llm().with_structured_output(AnalystReport)
    return llm.invoke(
        [
            ("system", TECHNICAL_SYSTEM),
            ("human", f"Ticker: {ticker}\nIndicators:\n{json.dumps(indicators, indent=2)}"),
        ]
    )


FUNDAMENTAL_SYSTEM = """You are the fundamental analyst on a trading desk.
Use ONLY the facts provided. Do not invent numbers or use outside knowledge.
Judge: growth (revenue and net income year over year), profitability (margins),
earnings quality (beats vs. estimates), and valuation (P/E, forward P/E vs. growth,
price vs. analyst target and 52-week high).
No sector or peer benchmarks are provided, so never claim a stock is cheap or expensive
relative to peers; judge valuation only against its own growth and the numbers given.
Every key point and every risk must cite a specific number from the facts.
If growth is strong but valuation is stretched (or the reverse), say so and cap confidence at 0.7.
You analyse the business and valuation only, not price charts."""


def fundamental_analyst(ticker: str, facts: dict) -> AnalystReport:
    llm = get_llm().with_structured_output(AnalystReport)
    return llm.invoke(
        [
            ("system", FUNDAMENTAL_SYSTEM),
            ("human", f"Ticker: {ticker}\nFacts:\n{json.dumps(facts, indent=2)}"),
        ]
    )

if __name__ == "__main__":
    ticker = "AAPL"
    av = AlphaVantageClient()
    prices = av.daily_prices(ticker)
    indicators = compute_indicators(prices)

    print("=== TECHNICAL ===")
    print(technical_analyst(ticker, indicators).model_dump_json(indent=2))

    facts = build_fundamental_facts(
        YahooClient().snapshot(ticker),
        av.earnings(ticker),
        av.income_statement(ticker, quarters=5),
        price=indicators["close"],
    )
    print("\nFACTS:", json.dumps(facts, indent=2))
    print("\n=== FUNDAMENTAL ===")
    print(fundamental_analyst(ticker, facts).model_dump_json(indent=2))