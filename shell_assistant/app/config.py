import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass


APP_DIR = Path(__file__).resolve().parent
PROJECT_DIR = APP_DIR.parent


@dataclass(frozen=True)
class Settings:
    llm_api_key: str
    llm_base_url: str
    llm_model: str
    llm_timeout_seconds: float
    history_path: Path
    history_limit: int


def get_settings() -> Settings:
    return Settings(
        llm_api_key=os.getenv("LLM_API_KEY", ""),
        llm_base_url=os.getenv("LLM_BASE_URL", "https://api.minimax.io/v1"),
        llm_model=os.getenv("LLM_MODEL", "MiniMax-M2.7"),
        llm_timeout_seconds=float(os.getenv("LLM_TIMEOUT_SECONDS", "25")),
        history_path=Path(
            os.getenv("HISTORY_PATH", str(APP_DIR / "storage" / "history.json"))
        ),
        history_limit=int(os.getenv("HISTORY_LIMIT", "100")),
    )

