import json
import logging
import re
import time
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
        max_attempts = 5
        for attempt in range(max_attempts):
            try:
                content = self._messages(system_prompt, prompt)
            except Exception as exc:
                last_error = str(exc)
                logger.debug("LLM request failed: %s", last_error)
                if attempt < max_attempts - 1 and _is_retryable(exc):
                    time.sleep(min(2**attempt, 4))
                    continue
                break

            parsed = _parse_json_object(content)
            if parsed is not None:
                return parsed

            last_error = "LLM returned non-JSON content"
            prompt = (
                "The previous response was not valid JSON. Return exactly one JSON "
                "object only, without Markdown or extra text. Original task:\n"
                + user_prompt
            )

        return {"error": last_error or "LLM request failed"}

    def _messages(self, system_prompt: str, user_prompt: str) -> str:
        payload = {
            "model": self.settings.llm_model,
            "max_tokens": self.settings.llm_max_tokens,
            "temperature": 0.1,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}],
        }
        headers = {
            "x-api-key": self.settings.llm_api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        with httpx.Client(timeout=self.settings.llm_timeout_seconds) as client:
            response = client.post(_messages_url(self.settings.llm_base_url), headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
        return _extract_text_content(data)


def _messages_url(base_url: str) -> str:
    base = base_url.rstrip("/")
    if base.endswith("/v1/messages"):
        return base
    if base.endswith("/anthropic"):
        return f"{base}/v1/messages"
    if base.endswith("/anthropic/v1"):
        return f"{base}/messages"
    return f"{base}/v1/messages"


def _extract_text_content(data: dict[str, Any]) -> str:
    content = data.get("content", [])
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""

    chunks: list[str] = []
    for block in content:
        if isinstance(block, str):
            chunks.append(block)
        elif isinstance(block, dict) and block.get("type") == "text":
            chunks.append(str(block.get("text", "")))
        elif isinstance(block, dict) and "text" in block:
            chunks.append(str(block.get("text", "")))
    return "".join(chunks)


def _is_retryable(exc: Exception) -> bool:
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in {429, 500, 502, 503, 504, 529}
    return isinstance(exc, httpx.TransportError)


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
