import json
from typing import Any, Mapping

JSON_ONLY_RULES = """
Return only valid JSON.
Do not wrap the response in markdown fences.
Do not add commentary before or after the JSON.
If a field is uncertain, choose the safer conservative interpretation and lower confidence.
""".strip()


def _as_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=True, indent=2, default=str)


def _patient_snapshot(patient_record: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "patientId": patient_record.get("patientId") or patient_record.get("Patient_ID"),
        "patientName": patient_record.get("patientName"),
        "age": patient_record.get("age") or patient_record.get("Age"),
        "gender": patient_record.get("gender") or patient_record.get("Gender"),
        "department": patient_record.get("department"),
        "doctorName": patient_record.get("doctorName"),
        "admissionType": patient_record.get("admission", {}).get("type"),
        "bedType": patient_record.get("bed", {}).get("type"),
        "diagnosis": patient_record.get("clinical", {}).get("diagnosis"),
        "clinicalNotes": patient_record.get("clinical", {}).get("clinicalNotes"),
        "investigations": patient_record.get("clinical", {}).get("investigations"),
        "medicineDetails": patient_record.get("clinical", {}).get("medicineDetails"),
    }


def build_revenue_explanation_prompt(
    patient_record: Mapping[str, Any],
    package_payload: Mapping[str, Any],
) -> str:
    output_shape = {
        "selectedBundle": {
            "packageCode": "string",
            "packageName": "string",
            "estimatedRevenue": "string",
        },
        "explanation": "string",
        "keyCostDrivers": ["string"],
        "confidence": 0.0,
    }

    return f"""
You are a hospital revenue explanation assistant.

Use the patient record and the revenue estimate payload below to explain why the selected treatment bundle and revenue band are appropriate.

{JSON_ONLY_RULES}

Patient record:
{_as_json(_patient_snapshot(patient_record))}

Revenue estimate payload:
{_as_json(package_payload)}

Instructions:
1. Confirm the chosen package code and package name.
2. Explain the major reasons why this bundle fits the patient.
3. Mention the cost drivers that created the lower and upper revenue range.
4. Use short, factual sentences.
5. Set confidence lower if the record is ambiguous or missing details.

Return JSON shape:
{_as_json(output_shape)}
""".strip()
