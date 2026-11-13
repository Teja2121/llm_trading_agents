import sys

from langgraph.graph import END, START, StateGraph

from trading_agents.alphavantage import AlphaVantageClient
from trading_agents.analysts import fundamental_analyst, news_analyst, technical_analyst
from trading_agents.debate import bear_node, bull_node, judge_node, should_continue
from trading_agents.fundamentals import build_fundamental_facts
from trading_agents.indicators import compute_indicators, compute_market_stress
from trading_agents.state import TradingState
from trading_agents.yahoo import YahooClient
from trading_agents.trading import risk_node, trader_node
from trading_agents.decision_log import log_node


def load_data(state: TradingState) -> dict:
    print("-> loading data")
    ticker = state["ticker"]
    av, yc = AlphaVantageClient(), YahooClient()
    indicators = compute_indicators(av.daily_prices(ticker))
    snapshot = yc.snapshot(ticker)
    facts = build_fundamental_facts(
        snapshot,
        av.earnings(ticker),
        av.income_statement(ticker, quarters=5),
        price=indicators["close"],
    )
    market = compute_market_stress(av.daily_prices("SPY"))

    return {
        "company": snapshot["name"],
        "indicators": indicators,
        "facts": facts,
        "headlines": yc.news(ticker, limit=15),
        "market": market
    }


def technical_node(state: TradingState) -> dict:
    print("-> technical analyst")
    return {"technical_report": technical_analyst(state["ticker"], state["indicators"])}


def fundamental_node(state: TradingState) -> dict:
    print("-> fundamental analyst")
    return {"fundamental_report": fundamental_analyst(state["ticker"], state["facts"])}


def news_node(state: TradingState) -> dict:
    print("-> news analyst")
    return {
        "news_report": news_analyst(
            state["ticker"], state["company"], state["headlines"]
        )
    }


def build_graph():
    g = StateGraph(TradingState)
    g.add_node("load_data", load_data)
    g.add_node("technical", technical_node)
    g.add_node("fundamental", fundamental_node)
    g.add_node("news", news_node)
    g.add_node("bull", bull_node)
    g.add_node("bear", bear_node)
    g.add_node("judge", judge_node)
    g.add_node("risk", risk_node)
    g.add_node("trader", trader_node)
    g.add_node("log", log_node)

    g.add_edge(START, "load_data")
    for analyst in ("technical", "fundamental", "news"):
        g.add_edge("load_data", analyst)  # fan-out: run in parallel
    g.add_edge(["technical", "fundamental", "news"], "bull")  # fan-in: wait for all
    g.add_edge("bull", "bear")
    g.add_conditional_edges("bear", should_continue, {"again": "bull", "done": "judge"})
    g.add_edge("judge", "risk")
    g.add_edge("risk", "trader")
    g.add_edge("trader", "log")
    g.add_edge("log", END)
    return g.compile()


if __name__ == "__main__":
    ticker = sys.argv[1] if len(sys.argv) > 1 else "AAPL"
    app = build_graph()
    final = app.invoke(
        {
            "ticker": ticker,
            "debate": [],
            "adjustments": [],
            "round": 0,
            "max_rounds": 2,
            "equity": 100_000.0,   # paper money
            "position_shares": 0,  # start flat
        }
    )

    print("\n=== DEBATE ===")
    for line in final["debate"]:
        print("\n" + line)

    print("\n=== VERDICT ===")
    print(final["outcome"].model_dump_json(indent=2))

    print("\n=== RISK ===")
    print("flags:", final["risk_flags"])
    print("limits:", final["risk_limits"])
    print(final["risk_assessment"].model_dump_json(indent=2))

    print("\n=== CODE ADJUSTMENTS ===")
    print(final["adjustments"] or "none")

    print("\n=== FINAL DECISION ===")
    print(final["decision"].model_dump_json(indent=2))