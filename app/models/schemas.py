from typing import Literal

from pydantic import BaseModel, Field


RiskLevel = Literal["low", "medium", "high"]


class GenerateRequest(BaseModel):
    query: str = Field(..., min_length=1)
    shell_type: str = "bash"
    os: str = "linux"
    context: str = ""


class GenerateResponse(BaseModel):
    query: str
    command: str
    alternatives: list[str] = []
    explanation: str
    risk_level: RiskLevel
    risk_reasons: list[str] = []
    safety_tips: list[str] = []
    source: str


class ExplainRequest(BaseModel):
    command: str = Field(..., min_length=1)


class CommandPart(BaseModel):
    token: str
    meaning: str


class ExplainResponse(BaseModel):
    command: str
    summary: str
    parts: list[CommandPart] = []
    risk_level: RiskLevel
    notes: list[str] = []


class CheckRequest(BaseModel):
    command: str = Field(..., min_length=1)


class RiskResponse(BaseModel):
    risk_level: RiskLevel
    risk_reasons: list[str] = []
    safety_tips: list[str] = []


class CategoryCount(BaseModel):
    name: str
    count: int


class HistoryHighlightsResponse(BaseModel):
    total_records: int
    top_categories: list[CategoryCount] = []
    high_risk_count: int
    frequent_patterns: list[str] = []
    summary: str

