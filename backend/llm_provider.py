from __future__ import annotations

import json
import os
from pathlib import Path
from threading import Lock
from typing import Any

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover
    OpenAI = None


ROOT_DIR = Path(__file__).resolve().parents[1]
GROQ_BASE_URL = "https://api.groq.com/openai/v1"
_CLIENT_CACHE: dict[str, OpenAI] = {}
_CLIENT_LOCK = Lock()

if load_dotenv:
    load_dotenv(ROOT_DIR / ".env")
    load_dotenv(ROOT_DIR / "backend" / ".env")


def get_agentic_provider_name() -> str:
    return os.getenv("AGENTIC_PROVIDER", "groq").strip().lower() or "groq"


def get_agentic_api_key(provider: str | None = None) -> str:
    provider_name = provider or get_agentic_provider_name()

    if provider_name == "groq":
        return os.getenv("GROQ_API_KEY", "").strip()
    if provider_name == "openai":
        return os.getenv("OPENAI_API_KEY", "").strip()

    raise ValueError(f"Unsupported AGENTIC_PROVIDER: {provider_name}")


def get_agentic_model_name(provider: str | None = None) -> str:
    provider_name = provider or get_agentic_provider_name()
    default_model = "llama-3.3-70b-versatile" if provider_name == "groq" else "gpt-4o-mini"
    return os.getenv("AGENTIC_MODEL", default_model).strip().strip("'\"") or default_model


def get_llm_client() -> tuple[OpenAI, str, str]:
    if OpenAI is None:
        raise RuntimeError(
            "OpenAI client is unavailable. Install the `openai` package to use the agentic pipeline."
        )

    provider = get_agentic_provider_name()
    api_key = get_agentic_api_key(provider)

    if not api_key:
        raise RuntimeError(f"{provider.title()} client is unavailable. Set the required API key.")

    with _CLIENT_LOCK:
        client = _CLIENT_CACHE.get(provider)
        if client is None:
            if provider == "groq":
                client = OpenAI(api_key=api_key, base_url=GROQ_BASE_URL)
            elif provider == "openai":
                client = OpenAI(api_key=api_key)
            else:  # pragma: no cover - guarded above
                raise ValueError(f"Unsupported AGENTIC_PROVIDER: {provider}")

            _CLIENT_CACHE[provider] = client

    return client, get_agentic_model_name(provider), provider


def clean_json_text(text: str) -> str:
    cleaned = (text or "").strip()

    if cleaned.startswith("```"):
        cleaned = cleaned.replace("```json", "", 1).replace("```", "").strip()

    if "{" in cleaned and "}" in cleaned:
        cleaned = cleaned[cleaned.find("{") : cleaned.rfind("}") + 1]

    return cleaned


def call_llm_json(messages: list[dict[str, str]], temperature: float = 0.1) -> tuple[dict[str, Any], dict[str, str]]:
    client, model, provider = get_llm_client()

    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        response_format={"type": "json_object"},
    )

    if not getattr(response, "choices", None):
        raise ValueError(f"{provider} response did not contain choices.")

    content = response.choices[0].message.content if response.choices[0].message else ""
    cleaned = clean_json_text(content or "")

    if not cleaned:
        raise ValueError(f"{provider} response content was empty.")

    return json.loads(cleaned), {"provider": provider, "model": model}


__all__ = [
    "call_llm_json",
    "clean_json_text",
    "get_agentic_api_key",
    "get_agentic_model_name",
    "get_agentic_provider_name",
    "get_llm_client",
]
