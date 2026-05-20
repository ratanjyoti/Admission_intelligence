import json
from typing import Any

from backend.llm_intelligence import llm_feature_enabled
from backend.llm_provider import call_llm_json


def build_clinical_plan_prompt(patient: dict[str, Any]) -> str:
    serialized_patient = json.dumps(patient, ensure_ascii=True, indent=2)

    return f"""
You are a clinical treatment reasoning assistant for hospital admission planning.

Task:
- Infer the likely admission pathway, procedures, bed type, and estimated length of stay.
- Do not estimate revenue, prices, or costs.
- Use only information available in the patient record.
- Return valid JSON only, with no markdown fences or extra text.

Expected JSON structure:
{
  "likelyAdmission": true,
  "likelyProcedures": ["string"],
  "likelyBedType": "string",
  "estimatedLOS": 0,
  "confidence": 0.0,
  "reasoning": "string"
}

Patient record:
{serialized_patient}
""".strip()


def generate_clinical_plan(patient: dict[str, Any]) -> dict[str, Any]:
    messages = [
        {"role": "system", "content": "You are a concise hospital clinical reasoning assistant."},
        {"role": "user", "content": build_clinical_plan_prompt(patient)},
    ]

    result, metadata = call_llm_json(messages, temperature=0.2)
    return {
        "clinicalPlan": {
            "likelyAdmission": bool(result.get("likelyAdmission")),
            "likelyProcedures": result.get("likelyProcedures", []),
            "likelyBedType": result.get("likelyBedType") or "Unknown",
            "estimatedLOS": int(result.get("estimatedLOS") or 0),
            "confidence": float(result.get("confidence") or 0.0),
            "reasoning": result.get("reasoning") or "",
            "llmProvider": metadata.get("provider"),
            "llmModel": metadata.get("model"),
        }
    }


def maybe_generate_clinical_plan(patient: dict[str, Any], allow_live_generation: bool = False) -> dict[str, Any] | None:
    if not llm_feature_enabled() or not allow_live_generation:
        return None

    try:
        return generate_clinical_plan(patient)
    except Exception:
        return None
