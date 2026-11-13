import json

from trading_agents.llm import get_llm
from trading_agents.schemas import DebateOutcome
from trading_agents.state import TradingState

BULL_SYSTEM = """You are the bull researcher in an investment debate.
Argue the strongest honest case that this stock is worth buying now, using ONLY the analyst
reports provided. Cite specific numbers. If the bear has spoken, rebut their strongest point
directly, and concede any point that is simply true. Do not invent facts.
Maximum 120 words. Plain prose, no bullet points."""

BEAR_SYSTEM = """You are the bear researcher in an investment debate.
Argue the strongest honest case that this stock should be avoided or reduced now, using ONLY
the analyst reports provided. Cite specific numbers. Rebut the bull's strongest point directly,
and concede any point that is simply true. Do not invent facts.
Maximum 120 words. Plain prose, no bullet points."""

JUDGE_SYSTEM = """You are the impartial research director.
Read the analyst reports and the full debate. Decide which way the EVIDENCE leans, not which
side sounded more persuasive. Reward arguments backed by specific numbers and penalise claims
the reports do not support. Note anything the data could not settle.
Do not give a trade order; that is the trader's job."""


def _reports_text(state: TradingState) -> str:
    reports = {
        "technical": state["technical_report"].model_dump(),
        "fundamental": state["fundamental_report"].model_dump(),
        "news": state["news_report"].model_dump(),
    }
    return json.dumps(reports, indent=2)


def _speak(system: str, state: TradingState, side: str) -> str:
    n = state["round"] + 1
    transcript = "\n".join(state["debate"]) or "(you speak first)"
    prompt = (
        f"Ticker: {state['ticker']} ({state['company']})\n\n"
        f"Analyst reports:\n{_reports_text(state)}\n\n"
        f"Debate so far:\n{transcript}\n\n"
        f"This is round {n} of {state['max_rounds']}. Give your argument."
    )
    reply = get_llm(temperature=0.5).invoke([("system", system), ("human", prompt)])
    return f"{side} (round {n}): {reply.content.strip()}"


def bull_node(state: TradingState) -> dict:
    print(f"-> bull speaks (round {state['round'] + 1})")
    return {"debate": [_speak(BULL_SYSTEM, state, "BULL")]}


def bear_node(state: TradingState) -> dict:
    print(f"-> bear speaks (round {state['round'] + 1})")
    return {
        "debate": [_speak(BEAR_SYSTEM, state, "BEAR")],
        "round": state["round"] + 1,
    }


def should_continue(state: TradingState) -> str:
    return "again" if state["round"] < state["max_rounds"] else "done"


def judge_node(state: TradingState) -> dict:
    print("-> judge deciding")
    llm = get_llm(temperature=0.2).with_structured_output(DebateOutcome)
    prompt = (
        f"Ticker: {state['ticker']} ({state['company']})\n\n"
        f"Analyst reports:\n{_reports_text(state)}\n\n"
        f"Full debate:\n" + "\n\n".join(state["debate"])
    )
    return {"outcome": llm.invoke([("system", JUDGE_SYSTEM), ("human", prompt)])}