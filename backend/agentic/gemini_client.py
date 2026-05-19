from __future__ import annotations

import json
import os
from typing import Any

try:
    import google.generativeai as genai
except ImportError:  # pragma: no cover
    genai = None


MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-1.5-flash").strip().strip("'\"")


def clean_json_text(text: str) -> str:
    cleaned = (text or "").strip()
    cleaned = cleaned.replace("```json", "").replace("```", "").strip()
    return cleaned


def gemini_feature_enabled() -> bool:
    return bool(os.getenv("GEMINI_API_KEY")) and genai is not None


def call_gemini_json(prompt: str) -> dict[str, Any]:
    if not gemini_feature_enabled():
        raise RuntimeError(
            "Gemini client is unavailable. Install google-generativeai and set GEMINI_API_KEY."
        )

    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    model = genai.GenerativeModel(MODEL_NAME)
    response = model.generate_content(
        prompt,
        generation_config={
            "response_mime_type": "application/json",
            "temperature": 0.1,
        },
    )

    content = clean_json_text(getattr(response, "text", "") or "")
    if not content:
        raise ValueError("Gemini response was empty.")

    return json.loads(content)


__all__ = ["MODEL_NAME", "call_gemini_json", "clean_json_text", "gemini_feature_enabled"]
