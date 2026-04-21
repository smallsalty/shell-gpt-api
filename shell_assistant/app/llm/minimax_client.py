import json
import logging
import re
from typing import Any

import httpx

from app.config import Settings, get_settings


logger = logging.getLogger(__name__)


class MiniMaxClient:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()

    def generate_json(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        if not self.settings.llm_api_key:
            return {"error": "LLM_API_KEY is not set"}

        last_error = ""
        prompt = user_prompt
        for attempt in range(2):
            try:
                content = self._chat(system_prompt, prompt)
            except Exception as exc:
                last_error = str(exc)
                logger.warning("LLM request failed: %s", last_error)
                continue

            parsed = _parse_json_object(content)
            if parsed is not None:
                return parsed

            last_error = "LLM returned non-JSON content"
            prompt = (
                "上一轮输出不是合法 JSON。请只输出一个 JSON 对象，不要 Markdown，"
                "不要解释文字。原始任务如下：\n"
                + user_prompt
            )

        return {"error": last_error or "LLM request failed"}

    def _chat(self, system_prompt: str, user_prompt: str) -> str:
        base = self.settings.llm_base_url.rstrip("/")
        url = base if base.endswith("/chat/completions") else f"{base}/chat/completions"
        payload = {
            "model": self.settings.llm_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
        }
        headers = {
            "Authorization": f"Bearer {self.settings.llm_api_key}",
            "Content-Type": "application/json",
        }
        with httpx.Client(timeout=self.settings.llm_timeout_seconds) as client:
            response = client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
        return data["choices"][0]["message"]["content"]


def _parse_json_object(text: str) -> dict[str, Any] | None:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        value = json.loads(text)
        return value if isinstance(value, dict) else None
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", text, flags=re.S)
    if not match:
        return None
    try:
        value = json.loads(match.group(0))
        return value if isinstance(value, dict) else None
    except json.JSONDecodeError:
        return None

