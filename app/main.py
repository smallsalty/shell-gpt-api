from fastapi import FastAPI

from app.models.schemas import (
    CheckRequest,
    ExplainRequest,
    ExplainResponse,
    GenerateRequest,
    GenerateResponse,
    HistoryHighlightsResponse,
    RiskResponse,
)
from app.services.command_service import generate_command
from app.services.explain_service import explain_command
from app.services.history_service import build_highlights
from app.services.safety_service import check_command_safety


app = FastAPI(title="Shell-GPT Minimal Command Assistant")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/shell/generate", response_model=GenerateResponse)
def api_generate(request: GenerateRequest) -> dict:
    return generate_command(request)


@app.post("/api/shell/explain", response_model=ExplainResponse)
def api_explain(request: ExplainRequest) -> dict:
    return explain_command(request)


@app.post("/api/shell/check", response_model=RiskResponse)
def api_check(request: CheckRequest) -> dict:
    return check_command_safety(request.command)


@app.get("/api/shell/history/highlights", response_model=HistoryHighlightsResponse)
def api_highlights() -> dict:
    return build_highlights()

