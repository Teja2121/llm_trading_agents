import operator
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph


class DebateState(TypedDict):
    topic: str
    messages: Annotated[list[str], operator.add]  # append, don't overwrite
    round: int


def bull(state: DebateState) -> dict:
    n = state["round"] + 1
    return {"messages": [f"BULL r{n}: {state['topic']} looks strong."]}


def bear(state: DebateState) -> dict:
    n = state["round"] + 1
    return {
        "messages": [f"BEAR r{n}: {state['topic']} looks overvalued."],
        "round": n,
    }


MAX_ROUNDS = 2


def should_continue(state: DebateState) -> str:
    return "again" if state["round"] < MAX_ROUNDS else "done"


def build_graph():
    graph = StateGraph(DebateState)
    graph.add_node("bull", bull)
    graph.add_node("bear", bear)
    graph.add_edge(START, "bull")
    graph.add_edge("bull", "bear")
    graph.add_conditional_edges(
        "bear", should_continue, {"again": "bull", "done": END}
    )
    return graph.compile()


if __name__ == "__main__":
    app = build_graph()
    start = {"topic": "AAPL", "messages": [], "round": 0}

    print("--- step by step ---")
    for update in app.stream(start, stream_mode="updates"):
        print(update)

    print("\n--- final state ---")
    final = app.invoke(start)
    for line in final["messages"]:
        print(line)
    print("rounds:", final["round"])

    print("\n--- graph as Mermaid (paste into mermaid.live) ---")
    print(app.get_graph().draw_mermaid())