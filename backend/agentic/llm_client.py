from __future__ import annotations

import json
import os
import time
from typing import Any

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover
    OpenAI = None

try:
    import google.generativeai as genai
except ImportError:  # pragma: no cover
    genai = None

PROVIDER = os.getenv("AGENTIC_PROVIDER", "groq").strip().lower()
GROQ_MODEL = os.getenv("AGENTIC_GROQ_MODEL", "llama-3.3-70b-versatile").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash").strip().strip("'\"")

MAX_TOKENS = int(os.getenv("AGENTIC_MAX_TOKENS", "2048"))
TEMPERATURE = float(os.getenv("AGENTIC_TEMPERATURE", "0.05"))
RETRY_ATTEMPTS = int(os.getenv("AGENTIC_RETRY_ATTEMPTS", "2"))
RETRY_DELAY = int(os.getenv("AGENTIC_RETRY_DELAY_SECONDS", "2"))

_OPENAI_CLIENT = None


def clean_json_text(text: str) -> str:
    cleaned = (text or "").strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.replace("```json", "", 1).replace("```", "").strip()
    if "{" in cleaned and "}" in cleaned:
        cleaned = cleaned[cleaned.find("{") : cleaned.rfind("}") + 1]
    return cleaned


def llm_feature_enabled() -> bool:
    if PROVIDER == "groq":
        return bool(os.getenv("GROQ_API_KEY")) and OpenAI is not None
    elif PROVIDER == "gemini":
        return bool(os.getenv("GEMINI_API_KEY")) and genai is not None
    return False


def _get_groq_client():
    global _OPENAI_CLIENT
    if _OPENAI_CLIENT is None:
        _OPENAI_CLIENT = OpenAI(
            api_key=os.getenv("GROQ_API_KEY"),
            base_url="https://api.groq.com/openai/v1"
        )
    return _OPENAI_CLIENT


def _call_groq(prompt: str) -> str:
    client = _get_groq_client()
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=TEMPERATURE,
        max_tokens=MAX_TOKENS,
        response_format={"type": "json_object"},
    )
    if not getattr(response, "choices", None) or not response.choices[0].message:
        raise ValueError("Groq response was empty.")
    return response.choices[0].message.content


def _call_gemini(prompt: str) -> str:
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    model = genai.GenerativeModel(GEMINI_MODEL)
    response = model.generate_content(
        prompt,
        generation_config={
            "response_mime_type": "application/json",
            "temperature": TEMPERATURE,
            "max_output_tokens": MAX_TOKENS,
        },
    )
    return getattr(response, "text", "") or ""


def call_llm_json(prompt: str) -> dict[str, Any]:
    if not llm_feature_enabled():
        raise RuntimeError(f"Agentic LLM client is unavailable for provider: {PROVIDER}.")

    last_error = None
    for attempt in range(RETRY_ATTEMPTS + 1):
        try:
            if PROVIDER == "groq":
                content = _call_groq(prompt)
            else:
                content = _call_gemini(prompt)

            content = clean_json_text(content)
            if not content:
                raise ValueError("LLM response content was empty.")

            return json.loads(content)
            
        except Exception as exc:
            last_error = exc
            if attempt < RETRY_ATTEMPTS:
                time.sleep(RETRY_DELAY * (2 ** attempt))  # Exponential backoff

    raise RuntimeError(f"LLM call failed after {RETRY_ATTEMPTS + 1} attempts. Last error: {last_error}")


__all__ = ["call_llm_json", "clean_json_text", "llm_feature_enabled"]
