from __future__ import annotations

from typing import Any, Mapping

from backend.agentic.prompts import (
    clinical_analyst_prompt,
    operational_summarizer_prompt,
    pathway_planner_prompt,
    risk_scorer_prompt,
)
from backend.llm_provider import call_llm_json


def _value(patient: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in patient and patient.get(key) not in {None, ""}:
            return patient.get(key)
    return ""


def _clinical_value(patient: Mapping[str, Any], field: str, *fallback_keys: str) -> Any:
    clinical = patient.get("clinical", {})
    if isinstance(clinical, Mapping) and clinical.get(field) not in {None, ""}:
        return clinical.get(field)
    return _value(patient, *fallback_keys)


def build_patient_text(patient: Mapping[str, Any]) -> str:
    return f"""
Patient ID: {_value(patient, "patientId", "patient_id", "Patient_ID", "Patient ID")}
Department: {_value(patient, "department", "Department", "Department_Name", "department_name")}
Diagnosis: {_clinical_value(patient, "diagnosis", "diagnosis", "ProvisionalDiagnosis", "provisionaldiagnosis")}
Clinical Notes: {_clinical_value(patient, "clinicalNotes", "clinical_notes", "Clinical Notes", "clinicalnotes")}
Doctor Advice: {_clinical_value(patient, "doctorAdvice", "doctor_advice", "otheradvice")}
Medicine Details: {_clinical_value(patient, "medicineDetails", "medicine_details", "medicinedetails")}
Investigations: {_clinical_value(patient, "investigations", "investigations", "nameofinvestigation", "other_investigation_freetext")}
Vitals/History: {_clinical_value(patient, "vitalRemarks", "vital_remarks", "vitalremarks", "Other_Medication_freetext")}
Repeat Visit: {_value(patient, "repeatVisit", "Repeat Visit")}
Visit Count: {_value(patient, "visitCount", "visit_count")}
""".strip()


def _call_agent_prompt(prompt: str) -> dict[str, Any]:
    payload, _metadata = call_llm_json(
        [{"role": "user", "content": prompt}],
        temperature=0.1,
    )
    return payload


def clinical_analyst_agent(patient: Mapping[str, Any]) -> dict[str, Any]:
    return _call_agent_prompt(clinical_analyst_prompt(patient))


def risk_scorer_agent(
    patient: Mapping[str, Any],
    clinical: Mapping[str, Any],
) -> dict[str, Any]:
    return _call_agent_prompt(risk_scorer_prompt(patient, clinical))


def pathway_planner_agent(
    patient: Mapping[str, Any],
    clinical: Mapping[str, Any],
    risk: Mapping[str, Any],
) -> dict[str, Any]:
    return _call_agent_prompt(pathway_planner_prompt(patient, clinical, risk))


def operational_summarizer_agent(
    patient: Mapping[str, Any],
    clinical: Mapping[str, Any],
    risk: Mapping[str, Any],
    pathway: Mapping[str, Any],
) -> dict[str, Any]:
    return _call_agent_prompt(
        operational_summarizer_prompt(patient, clinical, risk, pathway)
    )


__all__ = [
    "build_patient_text",
    "clinical_analyst_agent",
    "risk_scorer_agent",
    "pathway_planner_agent",
    "operational_summarizer_agent",
]
