from __future__ import annotations

import json
from typing import Any, Mapping


JSON_ONLY_RULES = """
Return only valid JSON.
Do not wrap the response in markdown fences.
Do not add commentary before or after the JSON.
If a field is unknown, use a conservative empty value that still matches the schema.
Never invent labs, dates, procedures, diagnoses, or treatments that are unsupported by the record.
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
    return {
        "patientId": patient_record.get("patientId") or patient_record.get("Patient_ID"),
        "patientName": patient_record.get("patientName"),
        "age": patient_record.get("age") or patient_record.get("Age"),
        "gender": patient_record.get("gender") or patient_record.get("Gender"),
        "department": patient_record.get("department") or patient_record.get("Department"),
        "doctorName": patient_record.get("doctorName"),
        "customerType": patient_record.get("customerType"),
        "visitDate": patient_record.get("visitDate"),
        "repeatVisit": (
            patient_record.get("journey", {}).get("repeatVisit")
            if isinstance(patient_record.get("journey"), Mapping)
            else patient_record.get("repeatVisit")
        ),
        "visitCount": (
            patient_record.get("journey", {}).get("visitCount")
            if isinstance(patient_record.get("journey"), Mapping)
            else patient_record.get("visitCount")
        ),
        "diagnosis": _clinical_field(patient_record, "diagnosis"),
        "clinicalNotes": _clinical_field(patient_record, "clinicalNotes"),
        "physicalRemarks": _clinical_field(patient_record, "physicalRemarks"),
        "vitalRemarks": _clinical_field(patient_record, "vitalRemarks"),
        "investigations": _clinical_field(patient_record, "investigations"),
        "doctorAdvice": _clinical_field(patient_record, "doctorAdvice"),
        "medicineDetails": _clinical_field(patient_record, "medicineDetails"),
        "explicitProcedure": (
            patient_record.get("procedure", {}).get("explicitProcedure")
            if isinstance(patient_record.get("procedure"), Mapping)
            else patient_record.get("explicitProcedure")
        ),
    }


def build_clinical_analyst_prompt(patient_record: Mapping[str, Any]) -> str:
    snapshot = _patient_snapshot(patient_record)
    output_shape = {
        "confirmed_diagnosis": "string",
        "possible_symptoms": ["string"],
        "red_flags": ["string"],
        "comorbidities": ["string"],
        "history": "string",
        "progression": "stable | worsening | improving | acute_onset | unknown",
        "clinical_urgency_signals": ["string"],
        "missing_data_flags": ["string"],
        "evidence": [
            {
                "source_field": "diagnosis | clinicalNotes | physicalRemarks | vitalRemarks | investigations | doctorAdvice | medicineDetails",
                "quote": "short exact or near-exact supporting quote",
                "signal": "what the quote supports",
            }
        ],
        "confidence": 0.0,
    }

    return f"""
You are Agent 1: Clinical Analyst for a hospital admission intelligence pipeline.

Your responsibility is grounding and extraction only.
Do not make treatment decisions.
Do not estimate revenue.
Do not produce admission type, bed type, or risk category.
Be conservative and source-aware.

{JSON_ONLY_RULES}

Patient record:
{_as_json(snapshot)}

Tasks:
1. Extract the confirmed diagnosis from the record when supported.
2. Extract possible symptoms that are explicitly stated or strongly implied.
3. Identify red flags and urgency signals that are clinically important.
4. Extract comorbidities and relevant prior history.
5. Infer progression using only these values:
   - stable
   - worsening
   - improving
   - acute_onset
   - unknown
6. Add missing_data_flags for any ambiguity or missing clinical context.
7. Add evidence items that cite which source field supports each important signal.

Output JSON shape:
{_as_json(output_shape)}
""".strip()


def build_risk_scorer_prompt(
    patient_record: Mapping[str, Any],
    clinical_analysis: Mapping[str, Any],
) -> str:
    snapshot = _patient_snapshot(patient_record)
    output_shape = {
        "acuity_risk": 1,
        "deterioration_risk": 1,
        "readmission_risk": "High | Medium | Low",
        "dropout_risk": "High | Medium | Low",
        "composite_risk_score": 1,
        "risk_category": "Low | Medium | High | Critical",
        "top_risk_drivers": ["string"],
        "reasoning": "brief evidence-based rationale",
        "confidence": 0.0,
    }

    return f"""
You are Agent 2: Risk Scorer for a hospital admission intelligence pipeline.

Your responsibility is risk stratification only.
Do not recommend treatment pathways.
Do not estimate revenue.
Do not produce timeline or ICD-10 coding.

{JSON_ONLY_RULES}

Patient metadata:
{_as_json(snapshot)}

Clinical analysis from Agent 1:
{_as_json(clinical_analysis)}

Instructions:
1. Score acuity_risk from 1-10 for immediate clinical danger.
2. Score deterioration_risk from 1-10 for near-term worsening trajectory.
3. Classify readmission_risk as High, Medium, or Low.
4. Classify dropout_risk as High, Medium, or Low.
5. Derive composite_risk_score only after considering the sub-dimensions.
6. Map composite_risk_score to:
   - Low: 1-3
   - Medium: 4-5
   - High: 6-7
   - Critical: 8-10
7. Keep top_risk_drivers to the 3 most important evidence-based drivers.
8. If Agent 1 reported important missing_data_flags, reduce confidence appropriately.

Output JSON shape:
{_as_json(output_shape)}
""".strip()


def build_pathway_planner_prompt(
    patient_record: Mapping[str, Any],
    clinical_analysis: Mapping[str, Any],
    risk_scores: Mapping[str, Any],
) -> str:
    snapshot = _patient_snapshot(patient_record)
    output_shape = {
        "admission_type": "Emergency | Urgent | Elective",
        "case_type": "Surgical | Medication Management | Daycare",
        "primary_treatment": "string",
        "secondary_treatment": "string",
        "deferred_time": "string",
        "bed_type": "ICU | HDU | General | Suite | Daycare Bay",
        "estimated_los_days": 0,
        "procedure_name": "string or null",
        "inferred_procedure_name": "string or null",
        "reasoning": "brief evidence-based rationale",
        "confidence": 0.0,
    }

    return f"""
You are Agent 3: Pathway Planner for a hospital admission intelligence pipeline.

Your responsibility is deciding the care pathway from the already structured facts and risk profile.
Do not rewrite the entire case summary.
Do not estimate revenue.
Do not generate ICD-10 codes.

{JSON_ONLY_RULES}

Original patient record:
{_as_json(snapshot)}

Clinical analysis from Agent 1:
{_as_json(clinical_analysis)}

Risk assessment from Agent 2:
{_as_json(risk_scores)}

Instructions:
1. Determine admission_type:
   - Emergency: needs admission within hours
   - Urgent: should be admitted within 24-48 hours
   - Elective: can be scheduled later
2. Determine case_type:
   - Surgical
   - Medication Management
   - Daycare
3. Provide a primary_treatment that is operationally useful and clinically conservative.
4. Provide a secondary_treatment when the first pathway is not feasible or needs a fallback.
5. Set deferred_time in plain language.
6. Choose the most appropriate bed_type.
7. Set estimated_los_days as an integer, or null if daycare is more appropriate.
8. If the procedure is explicitly named in the record, place it in procedure_name.
9. If the procedure is not explicitly named but can be reasonably inferred, use inferred_procedure_name.
10. If the case is primarily medical and no procedure is justified, leave both procedure fields null.
11. Lower confidence when important clinical details are missing or the pathway is ambiguous.

Output JSON shape:
{_as_json(output_shape)}
""".strip()


def build_operational_summarizer_prompt(
    patient_record: Mapping[str, Any],
    clinical_analysis: Mapping[str, Any],
    risk_scores: Mapping[str, Any],
    pathway_plan: Mapping[str, Any],
) -> str:
    snapshot = _patient_snapshot(patient_record)
    output_shape = {
        "clinical_summary": "2-3 sentence operational summary",
        "icd10_code": "string",
        "icd10_description": "string",
        "clinical_timeline": [
            "First symptom onset or prior history",
            "Initial evaluation or OPD event",
            "Diagnosis or workup milestone",
            "Admission advice or escalation milestone",
            "Current status",
        ],
        "revenue_estimate": "string",
        "revenue_category": "High | Medium | Low",
        "ai_rationale": "short explainability summary",
        "operational_action": "single most important next action",
        "confidence": 0.0,
    }

    return f"""
You are Agent 4: Operational Summarizer for a hospital admission intelligence pipeline.

Your responsibility is synthesis.
Use the upstream agent outputs and original record to produce the final operational card.
Do not contradict clear upstream facts unless the original record strongly supports a correction.

{JSON_ONLY_RULES}

Original patient record:
{_as_json(snapshot)}

Clinical analysis from Agent 1:
{_as_json(clinical_analysis)}

Risk scores from Agent 2:
{_as_json(risk_scores)}

Pathway plan from Agent 3:
{_as_json(pathway_plan)}

Instructions:
1. Write a concise clinical_summary that a clinician can scan quickly.
2. Provide the most likely primary ICD-10 code and description from the available evidence.
3. Build a clinical_timeline as a list of short chronological entries.
4. Estimate a revenue_estimate as a practical package-value range.
5. Map revenue_category to High, Medium, or Low.
6. Write ai_rationale that explains why the patient was prioritized this way.
7. Write one operational_action that is concrete and immediately useful.
8. Lower confidence when upstream agents show ambiguity or when the record lacks critical data.

Output JSON shape:
{_as_json(output_shape)}
""".strip()


def clinical_analyst_prompt(patient_record: Mapping[str, Any]) -> str:
    return build_clinical_analyst_prompt(patient_record)


def risk_scorer_prompt(
    patient_record: Mapping[str, Any],
    clinical_analysis: Mapping[str, Any],
) -> str:
    return build_risk_scorer_prompt(patient_record, clinical_analysis)


def pathway_planner_prompt(
    patient_record: Mapping[str, Any],
    clinical_analysis: Mapping[str, Any],
    risk_scores: Mapping[str, Any],
) -> str:
    return build_pathway_planner_prompt(patient_record, clinical_analysis, risk_scores)


def operational_summarizer_prompt(
    patient_record: Mapping[str, Any],
    clinical_analysis: Mapping[str, Any],
    risk_scores: Mapping[str, Any],
    pathway_plan: Mapping[str, Any],
) -> str:
    return build_operational_summarizer_prompt(
        patient_record,
        clinical_analysis,
        risk_scores,
        pathway_plan,
    )


__all__ = [
    "build_clinical_analyst_prompt",
    "build_risk_scorer_prompt",
    "build_pathway_planner_prompt",
    "build_operational_summarizer_prompt",
    "clinical_analyst_prompt",
    "risk_scorer_prompt",
    "pathway_planner_prompt",
    "operational_summarizer_prompt",
]
