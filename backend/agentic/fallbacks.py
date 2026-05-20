from __future__ import annotations

from typing import Any, Mapping

from backend.agentic.validator import (
    DEFAULT_ACTIONS,
    DEFAULT_PRIORITY_ACTIONS,
    RISK_LEVEL_SCORES,
)


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _clinical_field(patient: Mapping[str, Any], field: str) -> str:
    clinical = patient.get("clinical", {}) if isinstance(patient.get("clinical"), Mapping) else {}
    return _clean_text(clinical.get(field) or patient.get(field))


def _repeat_visit_info(patient: Mapping[str, Any]) -> tuple[bool, int]:
    journey = patient.get("journey", {}) if isinstance(patient.get("journey"), Mapping) else {}
    repeat_visit = journey.get("repeatVisit", patient.get("repeatVisit"))
    visit_count = journey.get("visitCount", patient.get("visitCount"))
    repeat_flag = repeat_visit is True or _clean_text(repeat_visit).lower() in {"true", "yes", "1"}

    try:
        visit_count_value = int(float(visit_count))
    except (TypeError, ValueError):
        visit_count_value = 1

    return repeat_flag, max(1, visit_count_value)


def baseline_case_type(baseline_operational: Mapping[str, Any] | None) -> str:
    baseline = baseline_operational or {}
    case_type = baseline.get("case_type")
    if case_type:
        return _clean_text(case_type) or "Medication Management"
    return _clean_text(baseline.get("caseType", {}).get("label")) or "Medication Management"


def baseline_bed_type(baseline_operational: Mapping[str, Any] | None, patient: Mapping[str, Any]) -> str:
    baseline = baseline_operational or {}
    return (
        _clean_text(baseline.get("bed_type_required"))
        or _clean_text(patient.get("bed", {}).get("type"))
        or "General"
    )


def baseline_estimated_los(baseline_operational: Mapping[str, Any] | None) -> int | None:
    baseline = baseline_operational or {}
    estimated = baseline.get("estimated_los")
    if estimated in {None, ""}:
        estimated = baseline.get("lengthOfStay", {}).get("maxDays")

    try:
        return int(float(estimated))
    except (TypeError, ValueError):
        return None


def baseline_revenue_fields(baseline_operational: Mapping[str, Any] | None) -> tuple[str | None, str | None]:
    baseline = baseline_operational or {}
    revenue_estimate = _clean_text(
        baseline.get("revenue_estimate")
        or baseline.get("packageIntelligence", {}).get("expectedRevenue")
    )
    revenue_category = _clean_text(
        baseline.get("revenue_category")
        or baseline.get("packageIntelligence", {}).get("revenueCategory")
    )

    normalized_category = {
        "standard value": "Low",
        "moderate value": "Medium",
        "significant value": "Medium",
        "high value": "High",
        "strategic value": "High",
        "low": "Low",
        "medium": "Medium",
        "high": "High",
    }.get(revenue_category.lower(), None if not revenue_category else "Medium")

    return (revenue_estimate or None, normalized_category)


def baseline_timeline(baseline_operational: Mapping[str, Any] | None) -> list[str]:
    baseline = baseline_operational or {}
    timeline = baseline.get("clinical_timeline")
    if isinstance(timeline, list) and timeline:
        return [str(item) for item in timeline]

    stages = baseline.get("clinicalTimeline", {}).get("stages", [])
    if isinstance(stages, list):
        timeline_items = []
        for stage in stages:
            if not isinstance(stage, Mapping):
                continue
            title = _clean_text(stage.get("stage"))
            summary = _clean_text(stage.get("summary"))
            if title or summary:
                timeline_items.append(f"{title}: {summary}".strip(": "))
        return timeline_items

    return []


def risk_level_to_score(risk_level: str) -> int:
    return RISK_LEVEL_SCORES.get(risk_level, 5)


def risk_level_to_readmission(risk_level: str) -> str:
    return {
        "Low": "Low",
        "Medium": "Medium",
        "High": "High",
        "Critical": "High",
    }.get(risk_level, "Medium")


def risk_level_to_admission_type(risk_level: str) -> str:
    return {
        "Low": "Elective",
        "Medium": "Urgent",
        "High": "Urgent",
        "Critical": "Emergency",
    }.get(risk_level, "Urgent")


def risk_level_to_deferred_time(risk_level: str) -> str:
    return {
        "Low": "1-2 weeks acceptable",
        "Medium": "3-5 days acceptable",
        "High": "24-48 hours only",
        "Critical": "Cannot be safely delayed",
    }.get(risk_level, "3-5 days acceptable")


def fallback_llm_risk_assessment(
    patient: Mapping[str, Any],
    baseline_operational: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    baseline = baseline_operational or {}
    baseline_risk_level = _clean_text(
        baseline.get("risk_category") or patient.get("risk", {}).get("category")
    )
    risk_level = {
        "low": "Low",
        "medium": "Medium",
        "moderate": "Medium",
        "high": "High",
        "critical": "Critical",
    }.get(baseline_risk_level.lower(), "Medium")

    repeat_visit, visit_count = _repeat_visit_info(patient)
    key_risk_factors = []
    if _clinical_field(patient, "diagnosis"):
        key_risk_factors.append(f"Diagnosis context: {_clinical_field(patient, 'diagnosis')}")
    if _clinical_field(patient, "clinicalNotes"):
        key_risk_factors.append("Clinical notes indicate active symptoms requiring review.")
    if repeat_visit:
        key_risk_factors.append("Repeat visit history increases concern for unresolved disease burden.")
    if visit_count >= 3:
        key_risk_factors.append("Multiple visits suggest persistent or worsening clinical need.")

    if not key_risk_factors:
        key_risk_factors.append("Baseline ML and rule signals were used because the live LLM assessment was unavailable.")

    reasoning_parts = [
        "Fallback assessment generated from the validated baseline ML and rule engine.",
        _clean_text(patient.get("risk", {}).get("reasoning")),
        _clean_text(baseline.get("readmissionRisk", {}).get("reasoning")),
    ]

    return {
        "riskLevel": risk_level,
        "reason": " ".join(part for part in reasoning_parts if part),
        "keyRiskFactors": key_risk_factors[:6],
        "suggestedAction": DEFAULT_ACTIONS[risk_level],
        "confidence": 0.45,
    }


def fallback_priority_assessment(
    patient: Mapping[str, Any],
    baseline_operational: Mapping[str, Any] | None = None,
    priority_profile: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    baseline = baseline_operational or {}
    profile = priority_profile or {}
    patient_id = _clean_text(
        patient.get("patientId")
        or patient.get("patient_id")
        or patient.get("Patient_ID")
        or patient.get("Patient ID")
    )
    risk_category = _clean_text(patient.get("risk", {}).get("category")).lower()
    admission_type = _clean_text(patient.get("admission", {}).get("type")).lower()
    bed_type = _clean_text(patient.get("bed", {}).get("type")).lower()
    deferred_time = _clean_text(baseline.get("deferredTime", {}).get("label")).lower()
    base_score = int(profile.get("score") or 0)

    if (
        risk_category == "critical"
        or admission_type == "emergency"
        or bed_type in {"icu", "hdu"}
        or deferred_time == "cannot be safely delayed"
    ):
        urgency_level = "Immediate"
        priority_score = max(90, min(99, base_score or 95))
    elif risk_category == "high" or admission_type == "urgent":
        urgency_level = "High"
        priority_score = max(78, min(89, base_score or 84))
    elif risk_category == "medium":
        urgency_level = "Medium"
        priority_score = max(52, min(74, base_score or 61))
    else:
        urgency_level = "Low"
        priority_score = max(20, min(49, base_score or 32))

    reason = (
        " ".join(profile.get("reasons", [])[:2])
        or _clean_text(patient.get("risk", {}).get("reasoning"))
        or _clean_text(baseline.get("readmissionRisk", {}).get("reasoning"))
        or "Fallback priority assessment generated from the validated rule and ML engine."
    )

    return {
        "patientId": patient_id,
        "urgencyLevel": urgency_level,
        "priorityScore": priority_score,
        "reason": reason,
        "suggestedAction": DEFAULT_PRIORITY_ACTIONS[urgency_level],
        "confidence": 0.45,
    }


def fallback_priority_queue_assessment(
    shortlisted_contexts: list[Mapping[str, Any]],
) -> dict[str, Any]:
    prioritized_patients = []

    for context in shortlisted_contexts:
        patient = context.get("patient", {}) if isinstance(context, Mapping) else {}
        baseline_operational = (
            context.get("baseline_operational", {}) if isinstance(context, Mapping) else {}
        )
        priority_profile = context.get("priority_profile", {}) if isinstance(context, Mapping) else {}
        prioritized_patients.append(
            fallback_priority_assessment(
                patient,
                baseline_operational=baseline_operational,
                priority_profile=priority_profile,
            )
        )

    return {"prioritizedPatients": prioritized_patients}


__all__ = [
    "baseline_bed_type",
    "baseline_case_type",
    "baseline_estimated_los",
    "baseline_revenue_fields",
    "baseline_timeline",
    "fallback_priority_assessment",
    "fallback_priority_queue_assessment",
    "fallback_llm_risk_assessment",
    "risk_level_to_admission_type",
    "risk_level_to_deferred_time",
    "risk_level_to_readmission",
    "risk_level_to_score",
]
