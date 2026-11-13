import json
import sqlite3
import sys
from datetime import datetime, timezone

from trading_agents.db import connect
from trading_agents.llm import get_llm
from trading_agents.schemas import Lesson

MAX_LESSONS = 5

REFLECT_SYSTEM = """You are the post-trade reviewer for a trading desk.
You receive one past decision (the analysts' key inputs, the verdict, the risk assessment, the action)
and what actually happened over the following 5 trading days.
Decide whether there is a lesson that could improve FUTURE decisions of one specific component
(technical, fundamental, news, risk, trader), or a general one.
Be skeptical: one 5-day result is mostly noise. Prefer worth_keeping=false unless the inputs contained a
specific signal or warning that the outcome plausibly relates to (for example a flag that was ignored,
or a signal that misled).
Write the lesson as a hypothesis tied to the numbers involved. Never claim certainty.
Never recommend specific trades."""


def _summary(state: dict) -> str:
    keys = [
        "indicators", "technical_report", "fundamental_report", "news_report",
        "outcome", "risk_flags", "risk_assessment", "adjustments", "decision",
    ]
    return json.dumps({k: state[k] for k in keys if k in state}, indent=2)


def reflect_pending() -> int:
    with connect() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT id, ticker, action, return_pct, eval_price, outcome_label, state_json "
            "FROM decisions WHERE outcome_label IN ('good', 'bad') ORDER BY id"
        ).fetchall()

    llm = get_llm(temperature=0.2).with_structured_output(Lesson)
    written = 0
    for r in rows:
        state = json.loads(r["state_json"])
        as_of = state["indicators"]["as_of"]

        with connect() as conn:
            seen = conn.execute(
                "SELECT 1 FROM lessons WHERE ticker = ? AND as_of = ?", (r["ticker"], as_of)
            ).fetchone()
        if seen:
            continue

        prompt = (
            f"Decision #{r['id']}: {r['action']} {r['ticker']} as of {as_of}\n"
            f"Outcome after 5 trading days: {r['return_pct']}% (exit price {r['eval_price']}), "
            f"labelled {r['outcome_label']}.\n\n"
            f"What the system saw and decided:\n{_summary(state)}"
        )
        lesson = llm.invoke([("system", REFLECT_SYSTEM), ("human", prompt)])

        with connect() as conn:
            conn.execute(
                "INSERT INTO lessons (decision_id, created_at, ticker, as_of, scope, lesson, "
                "kept, outcome_label, return_pct) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    r["id"], datetime.now(timezone.utc).isoformat(), r["ticker"], as_of,
                    lesson.scope, lesson.lesson, int(lesson.worth_keeping),
                    r["outcome_label"], r["return_pct"],
                ),
            )
        print(f"#{r['id']} {as_of} {r['outcome_label']}: kept={lesson.worth_keeping} [{lesson.scope}] {lesson.lesson}")
        written += 1
    return written


def lessons_block(scope: str) -> str:
    """Text appended to an agent's system prompt. Empty if there is nothing to say."""
    with connect() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT lesson, outcome_label, return_pct, as_of FROM lessons "
            "WHERE kept = 1 AND scope IN (?, 'general') ORDER BY id DESC LIMIT ?",
            (scope, MAX_LESSONS),
        ).fetchall()
    if not rows:
        return ""
    print(f"[lessons] {scope}: injecting {len(rows)}")
    lines = [
        f"- ({r['as_of']}, {r['outcome_label']} {r['return_pct']:+.1f}%) {r['lesson']}"
        for r in rows
    ]
    return (
        "\n\nLessons from past decisions. These are hypotheses from small samples, not rules. "
        "Weigh them against the current data and never let them override it:\n" + "\n".join(lines)
    )


if __name__ == "__main__":
    if "--show" in sys.argv:
        scope = sys.argv[sys.argv.index("--show") + 1]
        print(lessons_block(scope) or "(no lessons for this scope)")
    else:
        print(f"{reflect_pending()} decision(s) reflected on.")