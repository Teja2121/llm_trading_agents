from typing import Literal

from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from trading_agents.config import get_settings


def get_llm(temperature: float = 0.2) -> ChatOpenAI:
    """Build the chat model every agent will use."""
    s = get_settings()
    return ChatOpenAI(
        model=s.openai_model,
        api_key=s.openai_api_key,
        temperature=temperature,
    )


class Signal(BaseModel):
    """A simple structured opinion, used here as a demo."""

    stance: Literal["bullish", "bearish", "neutral"] = Field(
        description="Overall market view"
    )
    confidence: float = Field(description="Confidence from 0.0 to 1.0")
    reasoning: str = Field(description="One or two sentences of justification")


if __name__ == "__main__":
    llm = get_llm()

    # 1) Plain call: text in, message out
    reply = llm.invoke("In one sentence, what is a moving average?")
    print("TEXT:", reply.content)
    print("TOKENS:", reply.usage_metadata)

    # 2) Structured call: text in, Python object out
    structured_llm = llm.with_structured_output(Signal)
    result = structured_llm.invoke(
        "A stock trades above its 50-day average and its RSI is 72. "
        "Give your trading signal."
    )
    print("STRUCTURED:", result)
    print("Stance only:", result.stance)