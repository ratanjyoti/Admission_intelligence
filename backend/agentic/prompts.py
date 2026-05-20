from __future__ import annotations

import json
from typing import Any, Mapping


JSON_ONLY_RULES = """
Return only valid JSON.
Do not wrap the response in markdown fences.
Do not add commentary before or after the JSON.
If a field is uncertain, choose the safer conservative interpretation and lower confidence.
Never invent labs, dates, diagnoses, procedures, or vitals that are unsupported by the record.
""".strip()


def _as_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=True, indent=2, default=str)


def _safe_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _clinical_field(patient_record: Mapping[str, Any], field: str) -> str:
    clinical = patient_record.get("clinical", {})
    if isinstance(clinical, Mapping) and field in clinical:
        return _safe_text(clinical.get(field))
    return _safe_text(patient_record.get(field))


def _patient_snapshot(patient_record: Mapping[str, Any]) -> dict[str, Any]:
    journey = patient_record.get("journey", {}) if isinstance(patient_record.get("journey"), Mapping) else {}
    admission = patient_record.get("admission", {}) if isinstance(patient_record.get("admission"), Mapping) else {}
    bed = patient_record.get("bed", {}) if isinstance(patient_record.get("bed"), Mapping) else {}

    return {
        "patientId": patient_record.get("patientId") or patient_record.get("Patient_ID"),
        "patientName": patient_record.get("patientName"),
        "age": patient_record.get("age") or patient_record.get("Age"),
        "gender": patient_record.get("gender") or patient_record.get("Gender"),
        "department": patient_record.get("department") or patient_record.get("Department"),
        "doctorName": patient_record.get("doctorName"),
        "visitDate": patient_record.get("visitDate"),
        "repeatVisit": journey.get("repeatVisit", patient_record.get("repeatVisit")),
        "visitCount": journey.get("visitCount", patient_record.get("visitCount")),
        "progressionTrend": journey.get("progressionTrend"),
        "existingRiskCategory": (
            patient_record.get("risk", {}).get("category")
            if isinstance(patient_record.get("risk"), Mapping)
            else None
        ),
        "existingRiskScore": (
            patient_record.get("risk", {}).get("score")
            if isinstance(patient_record.get("risk"), Mapping)
            else None
        ),
        "existingAdmissionType": admission.get("type"),
        "existingBedType": bed.get("type"),
        "diagnosis": _clinical_field(patient_record, "diagnosis"),
        "clinicalNotes": _clinical_field(patient_record, "clinicalNotes"),
        "physicalRemarks": _clinical_field(patient_record, "physicalRemarks"),
        "vitalRemarks": _clinical_field(patient_record, "vitalRemarks"),
        "investigations": _clinical_field(patient_record, "investigations"),
        "doctorAdvice": _clinical_field(patient_record, "doctorAdvice"),
        "medicineDetails": _clinical_field(patient_record, "medicineDetails"),
    }


def _priority_patient_snapshot(
    patient_record: Mapping[str, Any],
    baseline_operational: Mapping[str, Any] | None = None,
    priority_profile: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    baseline = baseline_operational or {}
    profile = priority_profile or {}
    snapshot = _patient_snapshot(patient_record)

    snapshot.update(
        {
            "existingReadmissionRisk": baseline.get("readmissionRisk", {}).get("label"),
            "existingDeferredTime": baseline.get("deferredTime", {}).get("label"),
            "existingLengthOfStay": baseline.get("lengthOfStay", {}).get("label"),
            "baselinePriorityScore": profile.get("score"),
            "baselinePriorityReasons": list(profile.get("reasons", [])),
            "existingRiskReasoning": (
                patient_record.get("risk", {}).get("reasoning")
                if isinstance(patient_record.get("risk"), Mapping)
                else None
            ),
            "existingAdmissionReasoning": (
                patient_record.get("admission", {}).get("reasoning")
                if isinstance(patient_record.get("admission"), Mapping)
                else None
            ),
            "existingBedReasoning": (
                patient_record.get("bed", {}).get("reasoning")
                if isinstance(patient_record.get("bed"), Mapping)
                else None
            ),
        }
    )

    return snapshot


def build_llm_first_risk_prompt(patient_record: Mapping[str, Any]) -> str:
    snapshot = _patient_snapshot(patient_record)
    output_shape = {
        "riskLevel": "Low | Medium | High | Critical",
        "reason": "brief evidence-based explanation of why the patient is risky",
        "keyRiskFactors": ["string"],
        "suggestedAction": "single operational next step",
        "confidence": 0.0,
    }

    return f"""
You are a hospital admission risk analysis assistant.

Your job is to be the main reasoning layer for admission risk.
Understand the patient's condition from the record and classify the operational risk.

{JSON_ONLY_RULES}

Patient record:
{_as_json(snapshot)}

Instructions:
1. Understand the patient condition using age, diagnosis, symptoms, vitals, investigations, notes, repeat visits, and emergency indicators.
2. Classify riskLevel using only:
   - Low
   - Medium
   - High
   - Critical
3. Treat chest pain, breathlessness, low oxygen, altered sensorium, active bleeding, sepsis concern, stroke concern, or hemodynamic instability as strong risk indicators.
4. Use keyRiskFactors for the 3-6 strongest patient-specific reasons behind the risk.
5. suggestedAction must be concrete, short, and operationally useful.
6. Lower confidence when the source record is incomplete or ambiguous.

Return JSON shape:
{_as_json(output_shape)}
""".strip()


def build_priority_queue_prompt(
    patient_records: list[Mapping[str, Any]],
) -> str:
    shortlist = []

    for item in patient_records:
        patient = item.get("patient", {}) if isinstance(item, Mapping) else {}
        baseline_operational = (
            item.get("baseline_operational", {}) if isinstance(item, Mapping) else {}
        )
        priority_profile = item.get("priority_profile", {}) if isinstance(item, Mapping) else {}
        shortlist.append(
            _priority_patient_snapshot(
                patient,
                baseline_operational=baseline_operational,
                priority_profile=priority_profile,
            )
        )

    output_shape = {
        "prioritizedPatients": [
            {
                "patientId": "string",
                "urgencyLevel": "Immediate | High | Medium | Low",
                "priorityScore": 95,
                "reason": "short evidence-based reason for queue priority",
                "suggestedAction": "single operational next step",
                "confidence": 0.0,
            }
        ]
    }

    return f"""
You are a hospital patient prioritization assistant.

Your job is to prioritize only the shortlisted patients below for operational review.
The broader dashboard has already used rules and ML to shortlist suspicious patients.
Now use clinical judgment to rank only these shortlisted patients.

{JSON_ONLY_RULES}

Shortlisted patients:
{_as_json(shortlist)}

Instructions:
1. Analyze each patient using age, diagnosis, symptoms, vitals, investigations, notes, repeat visits, emergency indicators, and the baseline priority hints.
2. Return exactly one item per shortlisted patient. Do not skip patients and do not invent extra patients.
3. urgencyLevel must be one of:
   - Immediate
   - High
   - Medium
   - Low
4. Use Immediate only for patients needing the fastest queue placement, such as respiratory distress, low oxygen, shock, stroke concern, seizure with instability, active bleeding, ICU-level concern, or unsafe delay.
5. priorityScore must be an integer from 0 to 100, where higher means earlier review.
6. reason must be concise, patient-specific, and evidence-based.
7. suggestedAction must be short and operationally useful.
8. Lower confidence when the record is incomplete or ambiguous.

Return JSON shape:
{_as_json(output_shape)}
""".strip()


__all__ = ["build_llm_first_risk_prompt", "build_priority_queue_prompt"]
