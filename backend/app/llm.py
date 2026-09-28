"""Thin LLM client wrapper.

Every pipeline stage talks to the model through `LLM.complete`, so tests can swap
in a scripted fake and a different provider only needs a new subclass.
"""
from __future__ import annotations

import json
import re
from typing import Any

from . import config


class LLMError(RuntimeError):
    pass


class LLM:
    def complete(self, messages: list[dict], *, json_mode: bool = False,
                 temperature: float = 0.0, max_tokens: int = 1024) -> str:
        raise NotImplementedError

    def complete_json(self, messages: list[dict], **kwargs) -> dict[str, Any]:
        raw = self.complete(messages, json_mode=True, **kwargs)
        return parse_json(raw)


class GroqLLM(LLM):
    def __init__(self, api_key: str, model: str):
        from groq import Groq

        self._client = Groq(api_key=api_key)
        self.model = model

    def complete(self, messages, *, json_mode=False, temperature=0.0, max_tokens=1024):
        kwargs: dict[str, Any] = dict(model=self.model, messages=messages,
                                      temperature=temperature, max_tokens=max_tokens)
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        try:
            resp = self._client.chat.completions.create(**kwargs)
        except Exception as e:  # network, auth, rate limit
            raise LLMError(str(e)) from e
        return (resp.choices[0].message.content or "").strip()


def parse_json(raw: str) -> dict[str, Any]:
    """Parse a JSON object out of a model reply, tolerating code fences or stray prose."""
    text = raw.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if fence:
        text = fence.group(1).strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end <= start:
            raise LLMError(f"Model did not return JSON: {raw[:200]}")
        try:
            data = json.loads(text[start:end + 1])
        except json.JSONDecodeError as e:
            raise LLMError(f"Model returned malformed JSON: {e}") from e
    if not isinstance(data, dict):
        raise LLMError("Model returned JSON that is not an object")
    return data


_llm: LLM | None = None


def get_llm() -> LLM | None:
    """Return the configured client, or None when no API key is set."""
    global _llm
    if _llm is None and config.GROQ_API_KEY:
        _llm = GroqLLM(config.GROQ_API_KEY, config.LLM_MODEL)
    return _llm


def set_llm(llm: LLM | None) -> None:
    """Override the client (used by tests)."""
    global _llm
    _llm = llm
