from __future__ import annotations

from typing import Any, Mapping

from backend.agentic.prompts import build_llm_first_risk_prompt, build_priority_queue_prompt
from backend.llm_provider import call_llm_json


def _call_agent_prompt(prompt: str) -> dict[str, Any]:
    payload, _metadata = call_llm_json(
        [{"role": "user", "content": prompt}],
        temperature=0.1,
    )
    return payload


def llm_first_risk_agent(patient: Mapping[str, Any]) -> dict[str, Any]:
    return _call_agent_prompt(build_llm_first_risk_prompt(patient))


def llm_priority_queue_agent(shortlisted_patients: list[Mapping[str, Any]]) -> dict[str, Any]:
    return _call_agent_prompt(build_priority_queue_prompt(shortlisted_patients))


__all__ = ["llm_first_risk_agent", "llm_priority_queue_agent"]
