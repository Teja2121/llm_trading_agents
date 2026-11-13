import json

from trading_agents.llm import get_llm
from trading_agents.schemas import DebateOutcome
from trading_agents.state import TradingState

BULL_SYSTEM = """You are the bull researcher in an investment debate.
Argue the strongest honest case that this stock is worth buying now, using ONLY the analyst reports provided.
Quote numbers exactly. Do not describe a number more strongly than the reports do, and do not state
causes (for example 'effective cost management') that the reports do not state.
Never repeat an argument already made in the debate. If the bear has spoken, answer their latest points
specifically and concede any that are simply true; then add at least one point not yet raised, or say
plainly that you have nothing new.
Maximum 120 words. Plain prose, no bullet points."""

BEAR_SYSTEM = """You are the bear researcher in an investment debate.
Argue the strongest honest case that this stock should be avoided or reduced now, using ONLY the analyst reports provided.
Quote numbers exactly. Do not describe a number more strongly than the reports do (an RSI of 59 is not
'near 70'), and do not state causes the reports do not state.
Never repeat an argument already made in the debate. Answer the bull's latest points specifically and concede
any that are simply true; then add at least one point not yet raised, or say plainly that you have nothing new.
Maximum 120 words. Plain prose, no bullet points."""

JUDGE_SYSTEM = """You are the impartial research director.
Read the analyst reports and the full debate. Decide which way the EVIDENCE leans, not which side sounded
more persuasive. Check each side's claims against the reports and disregard any the reports do not support.
Your conviction cannot exceed the analysts' own confidence, because the debate adds no new evidence.
unresolved_questions must be specific to the data provided (for example, whether weak volume reflects low
interest), never generic market questions.
Do not give a trade order; that is the trader's job."""


def reports_text(state: TradingState) -> str:
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
        f"Analyst reports:\n{reports_text(state)}\n\n"
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
        f"Analyst reports:\n{reports_text(state)}\n\n"
        f"Full debate:\n" + "\n\n".join(state["debate"])
    )
    outcome = llm.invoke([("system", JUDGE_SYSTEM), ("human", prompt)])

    best = max(
        state["technical_report"].confidence,
        state["fundamental_report"].confidence,
        state["news_report"].confidence,
    )
    adjustments = []
    if outcome.conviction > best:
        adjustments.append(
            f"judge conviction {outcome.conviction} capped to {best} (debate adds no new evidence)"
        )
        outcome.conviction = best
    return {"outcome": outcome, "adjustments": adjustments}