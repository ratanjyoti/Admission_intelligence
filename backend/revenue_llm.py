from typing import Any

from backend.llm_provider import call_llm_json
from backend.revenue_prompts import build_revenue_explanation_prompt


def explain_revenue_payload(patient: dict[str, Any], revenue_payload: dict[str, Any]) -> dict[str, Any]:
    prompt = build_revenue_explanation_prompt(patient, revenue_payload)
    messages = [
        {"role": "system", "content": "You are a concise hospital revenue explanation assistant."},
        {"role": "user", "content": prompt},
    ]
    explanation, metadata = call_llm_json(messages, temperature=0.2)
    return {
        "llmExplanation": explanation,
        "llmProvider": metadata.get("provider"),
        "llmModel": metadata.get("model"),
    }
