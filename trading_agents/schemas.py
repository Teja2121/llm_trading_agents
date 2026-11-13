from typing import Literal

from pydantic import BaseModel, Field


class AnalystReport(BaseModel):
    stance: Literal["bullish", "bearish", "neutral"] = Field(
        description="Overall view from this analyst's perspective"
    )
    confidence: float = Field(
        description="0.0 to 1.0. Lower it when signals conflict or data is thin"
    )
    key_points: list[str] = Field(
        description="2 to 4 short points, each citing a specific number from the data"
    )
    risks: list[str] = Field(
        description="1 to 3 things that could make this view wrong"
    )

class NewsReport(AnalystReport):
    relevant_count: int = Field(
        description="How many headlines were genuinely about this company and could affect its stock"
    )
    ignored_count: int = Field(
        description="How many headlines were off-topic, generic or promotional and ignored"
    )

class DebateOutcome(BaseModel):
    leaning: Literal["bullish", "bearish", "neutral"] = Field(
        description="Which way the evidence leans after the debate"
    )
    conviction: float = Field(
        description="0.0 to 1.0. Lower it if the sides were evenly matched or data was thin"
    )
    summary: str = Field(description="2-3 sentences explaining the verdict")
    strongest_bull_point: str
    strongest_bear_point: str
    unresolved_questions: list[str] = Field(
        description="1 to 3 things the available data could not settle"
    )