from __future__ import annotations

import re
from typing import Any, Mapping


ICD10_PATTERN = re.compile(r"^[A-TV-Z][0-9][0-9A-Z](\.[0-9A-Z]{1,4})?$")


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _optional_text(value: Any) -> str | None:
    cleaned = _clean_text(value)
    return cleaned or None


def _int_or_default(value: Any, default: int, minimum: int | None = None, maximum: int | None = None) -> int:
    try:
        parsed = int(round(float(value)))
    except (TypeError, ValueError):
        parsed = default

    if minimum is not None:
        parsed = max(minimum, parsed)
    if maximum is not None:
        parsed = min(maximum, parsed)

    return parsed


def _normalize_label(value: Any, mapping: dict[str, str], default: str) -> str:
    cleaned = _clean_text(value).lower()
    return mapping.get(cleaned, default)


def _clinical_field(patient: Mapping[str, Any], field: str) -> str:
    clinical = patient.get("clinical", {})
    if isinstance(clinical, Mapping):
        return _clean_text(clinical.get(field) or patient.get(field))
    return _clean_text(patient.get(field))


def _list_labels(items: Any) -> list[str]:
    if not isinstance(items, list):
        return []

    labels = []
    for item in items:
        if isinstance(item, Mapping):
            label = _clean_text(item.get("label") or item.get("code"))
        else:
            label = _clean_text(item)

        if label:
            labels.append(label)

    return labels


def _build_evidence(patient: Mapping[str, Any]) -> list[dict[str, str]]:
    evidence = []
    source_fields = [
        ("diagnosis", _clinical_field(patient, "diagnosis")),
        ("clinicalNotes", _clinical_field(patient, "clinicalNotes")),
        ("vitalRemarks", _clinical_field(patient, "vitalRemarks")),
        ("investigations", _clinical_field(patient, "investigations")),
        ("doctorAdvice", _clinical_field(patient, "doctorAdvice")),
    ]

    for source_field, text in source_fields:
        if text:
            evidence.append(
                {
                    "source_field": source_field,
                    "quote": text[:180],
                    "signal": f"Fallback evidence extracted from {source_field}.",
                }
            )

        if len(evidence) >= 4:
            break

    return evidence


def _get_progression(patient: Mapping[str, Any]) -> str:
    journey = patient.get("journey", {})
    trend = ""

    if isinstance(journey, Mapping):
        trend = _clean_text(journey.get("progressionTrend"))

    mapping = {
        "stable": "stable",
        "worsening": "worsening",
        "improving": "improving",
        "acute": "acute_onset",
        "acute onset": "acute_onset",
        "acute_onset": "acute_onset",
    }

    return mapping.get(trend.lower(), "unknown")


def _get_repeat_visit(patient: Mapping[str, Any]) -> bool:
    journey = patient.get("journey", {})

    if isinstance(journey, Mapping) and journey.get("repeatVisit") not in {None, ""}:
        value = journey.get("repeatVisit")
    else:
        value = patient.get("repeatVisit")

    text_value = _clean_text(value).lower()
    return value is True or text_value in {"true", "yes", "1"}


def _get_visit_count(patient: Mapping[str, Any]) -> int:
    journey = patient.get("journey", {})

    if isinstance(journey, Mapping) and journey.get("visitCount") not in {None, ""}:
        value = journey.get("visitCount")
    else:
        value = patient.get("visitCount")

    return _int_or_default(value, 1, minimum=1, maximum=20)


def _fallback_red_flags(patient: Mapping[str, Any]) -> list[str]:
    red_flags = []
    risk_category = _clean_text(patient.get("risk", {}).get("category")).lower()
    admission_type = _clean_text(patient.get("admission", {}).get("type")).lower()
    bed_type = _clean_text(patient.get("bed", {}).get("type")).lower()

    if risk_category == "critical":
        red_flags.append("Critical-risk status is already present in the baseline record.")
    elif risk_category == "high":
        red_flags.append("High-risk status is already present in the baseline record.")

    if admission_type == "emergency":
        red_flags.append("Emergency admission intent suggests clinically unsafe delay.")
    if "icu" in bed_type or "hdu" in bed_type:
        red_flags.append("High-dependency bed planning indicates close inpatient monitoring.")

    return red_flags


def _normalize_risk_category(value: Any, score: int) -> str:
    mapping = {
        "low": "Low",
        "medium": "Medium",
        "moderate": "Medium",
        "high": "High",
        "critical": "Critical",
    }
    normalized = mapping.get(_clean_text(value).lower())
    if normalized:
        return normalized

    if score >= 8:
        return "Critical"
    if score >= 6:
        return "High"
    if score >= 4:
        return "Medium"
    return "Low"


def _normalize_three_level_risk(value: Any, score: int, default: str = "Medium") -> str:
    mapping = {
        "low": "Low",
        "medium": "Medium",
        "moderate": "Medium",
        "high": "High",
    }
    normalized = mapping.get(_clean_text(value).lower())
    if normalized:
        return normalized

    if score >= 7:
        return "High"
    if score >= 4:
        return "Medium"
    return default if default in {"Low", "Medium", "High"} else "Medium"


def _normalize_admission_type(value: Any, deferred_time: str = "") -> str:
    text = _clean_text(value).lower()
    if text == "emergency":
        return "Emergency"
    if text == "urgent":
        return "Urgent"
    if text == "elective":
        return "Elective"

    if "cannot be safely delayed" in deferred_time.lower():
        return "Emergency"
    if "24-48" in deferred_time or "3-5" in deferred_time:
        return "Urgent"
    return "Elective"


def _normalize_case_type(value: Any) -> str:
    return _normalize_label(
        value,
        {
            "surgical": "Surgical",
            "medication management": "Medication Management",
            "medical management": "Medication Management",
            "daycare": "Daycare",
            "day care": "Daycare",
        },
        "Medication Management",
    )


def _normalize_bed_type(value: Any) -> str:
    return _normalize_label(
        value,
        {
            "icu": "ICU",
            "hdu": "HDU",
            "general": "General",
            "general ward": "General",
            "general oncology ward": "General",
            "suite": "Suite",
            "daycare bay": "Daycare Bay",
            "day care bay": "Daycare Bay",
            "daycare": "Daycare Bay",
        },
        "General",
    )


def _normalize_revenue_category(value: Any) -> str:
    return _normalize_label(
        value,
        {
            "low": "Low",
            "medium": "Medium",
            "moderate": "Medium",
            "high": "High",
            "standard value": "Low",
            "moderate value": "Low",
            "significant value": "Medium",
            "high value": "High",
            "strategic value": "High",
        },
        "Medium",
    )


def _primary_icd10(baseline_operational: Mapping[str, Any]) -> tuple[str | None, str | None]:
    top_level_code = _optional_text(baseline_operational.get("icd10_code"))
    top_level_description = _optional_text(baseline_operational.get("icd10_description"))

    if top_level_code and ICD10_PATTERN.match(top_level_code.upper()):
        return top_level_code.upper(), top_level_description

    clinical_intelligence = baseline_operational.get("clinicalIntelligence", {})
    primary_icd10 = clinical_intelligence.get("primaryIcd10", {}) if isinstance(clinical_intelligence, Mapping) else {}
    code = _optional_text(primary_icd10.get("code"))
    description = _optional_text(primary_icd10.get("label"))

    if code and ICD10_PATTERN.match(code.upper()):
        return code.upper(), description

    return None, None


def fallback_clinical_analysis(
    patient: Mapping[str, Any],
    baseline_operational: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    baseline = baseline_operational or {}
    clinical_intelligence = baseline.get("clinicalIntelligence", {})
    structured_history = (
        clinical_intelligence.get("structuredHistory", {})
        if isinstance(clinical_intelligence, Mapping)
        else {}
    )
    symptoms = _list_labels(clinical_intelligence.get("possibleSymptoms", []))
    comorbidities = _list_labels(clinical_intelligence.get("comorbidities", []))
    diagnosis = _clinical_field(patient, "diagnosis")
    missing_data_flags = []

    if not diagnosis:
        missing_data_flags.append("Diagnosis missing in the source record.")
    if not symptoms:
        missing_data_flags.append("Symptoms were not confidently extracted from the baseline record.")
    if not _clinical_field(patient, "doctorAdvice"):
        missing_data_flags.append("Doctor advice is missing or empty.")

    history_summary = _clean_text(structured_history.get("summary")) or _clinical_field(patient, "vitalRemarks")
    urgency_signals = _fallback_red_flags(patient)

    if _get_repeat_visit(patient):
        urgency_signals.append("Repeat visit history suggests unresolved clinical need.")
    if _get_visit_count(patient) >= 3:
        urgency_signals.append("Multiple visits increase concern for instability or incomplete resolution.")

    return {
        "confirmed_diagnosis": diagnosis or "Diagnosis requires clinician confirmation",
        "possible_symptoms": symptoms,
        "red_flags": urgency_signals,
        "comorbidities": comorbidities,
        "history": history_summary,
        "progression": _get_progression(patient),
        "clinical_urgency_signals": urgency_signals,
        "missing_data_flags": missing_data_flags,
        "evidence": _build_evidence(patient),
        "confidence": 0.55,
    }


def fallback_risk_from_baseline(
    patient: Mapping[str, Any],
    baseline_operational: Mapping[str, Any] | None = None,
    clinical_analysis: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    baseline = baseline_operational or {}
    risk_score = _int_or_default(
        baseline.get("risk_score") or patient.get("risk", {}).get("score"),
        5,
        minimum=1,
        maximum=10,
    )
    baseline_readmission = (
        baseline.get("readmission_risk")
        or baseline.get("readmissionRisk", {}).get("label")
    )
    baseline_dropout = (
        baseline.get("dropout_risk")
        or baseline.get("noShowRisk", {}).get("label")
    )
    drivers = []
    if isinstance(clinical_analysis, Mapping):
        drivers.extend(clinical_analysis.get("red_flags", []))
    drivers.extend(_list_labels(baseline.get("readmissionRisk", {}).get("drivers", [])))
    drivers.extend(_list_labels(baseline.get("noShowRisk", {}).get("drivers", [])))

    unique_drivers = []
    for driver in drivers:
        if driver and driver not in unique_drivers:
            unique_drivers.append(driver)

    reasoning_parts = [
        "Fallback used from ML/rule baseline because agentic output was unavailable or invalid.",
        _clean_text(patient.get("risk", {}).get("reasoning")),
        _clean_text(baseline.get("readmissionRisk", {}).get("reasoning")),
    ]

    return {
        "composite_risk_score": risk_score,
        "risk_category": _normalize_risk_category(
            baseline.get("risk_category") or patient.get("risk", {}).get("category"),
            risk_score,
        ),
        "acuity_risk": risk_score,
        "deterioration_risk": risk_score,
        "readmission_risk": _normalize_three_level_risk(baseline_readmission, risk_score),
        "dropout_risk": _normalize_three_level_risk(baseline_dropout, risk_score),
        "top_risk_drivers": unique_drivers[:3],
        "reasoning": " ".join(part for part in reasoning_parts if part),
        "confidence": 0.45,
    }


def fallback_pathway_from_baseline(
    patient: Mapping[str, Any],
    baseline_operational: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    baseline = baseline_operational or {}
    deferred_time = _clean_text(
        baseline.get("deferred_time") or baseline.get("deferredTime", {}).get("label")
    ) or "3-5 days acceptable"
    treatment_plan = baseline.get("treatmentPlan", {})
    case_type = _normalize_case_type(
        baseline.get("case_type") or baseline.get("caseType", {}).get("label")
    )
    primary_treatment = _clean_text(
        baseline.get("primary_treatment") or treatment_plan.get("primary")
    ) or "Medication optimization with monitored clinical review"
    secondary_treatment = _clean_text(
        baseline.get("secondary_treatment") or treatment_plan.get("secondary")
    ) or "Observation with clinician reassessment if symptoms or labs worsen"
    bed_type = _normalize_bed_type(
        baseline.get("bed_type_required") or patient.get("bed", {}).get("type")
    )
    procedure = _optional_text(
        patient.get("procedure", {}).get("explicitProcedure") or patient.get("explicitProcedure")
    )
    inferred_procedure = _optional_text(patient.get("procedure", {}).get("inferredProcedure"))
    estimated_los_days = baseline.get("estimated_los")

    if estimated_los_days in {None, ""}:
        estimated_los_days = baseline.get("lengthOfStay", {}).get("maxDays")

    if case_type == "Daycare":
        estimated_los_days = 0

    reasoning = _clean_text(
        baseline.get("treatmentPlan", {}).get("reasoning")
        or patient.get("admission", {}).get("reasoning")
    ) or "Fallback pathway mapped from the baseline admission, bed, and treatment plan."

    return {
        "admission_type": _normalize_admission_type(
            patient.get("admission", {}).get("type"),
            deferred_time=deferred_time,
        ),
        "case_type": case_type,
        "primary_treatment": primary_treatment,
        "secondary_treatment": secondary_treatment,
        "deferred_time": deferred_time,
        "bed_type": bed_type,
        "estimated_los_days": (
            _int_or_default(estimated_los_days, 0, minimum=0, maximum=60)
            if estimated_los_days not in {None, ""}
            else None
        ),
        "procedure_name": procedure,
        "inferred_procedure_name": None if procedure else inferred_procedure,
        "reasoning": reasoning,
        "confidence": 0.5,
    }


def fallback_operational_summary_from_baseline(
    patient: Mapping[str, Any],
    baseline_operational: Mapping[str, Any] | None = None,
    clinical_analysis: Mapping[str, Any] | None = None,
    risk_scores: Mapping[str, Any] | None = None,
    pathway_plan: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    baseline = baseline_operational or {}
    diagnosis = (
        _clean_text((clinical_analysis or {}).get("confirmed_diagnosis"))
        or _clinical_field(patient, "diagnosis")
        or "Diagnosis requires clinician confirmation"
    )
    risk = risk_scores or {}
    pathway = pathway_plan or {}
    icd10_code, icd10_description = _primary_icd10(baseline)
    timeline = baseline.get("clinical_timeline")

    if not isinstance(timeline, list) or not timeline:
        stages = baseline.get("clinicalTimeline", {}).get("stages", [])
        timeline = [
            f"{_clean_text(stage.get('stage'))}: {_clean_text(stage.get('summary'))}"
            for stage in stages
            if isinstance(stage, Mapping)
            and (_clean_text(stage.get("stage")) or _clean_text(stage.get("summary")))
        ]

    revenue_estimate = _optional_text(
        baseline.get("revenue_estimate")
        or baseline.get("packageIntelligence", {}).get("expectedRevenue")
    )
    revenue_category = _normalize_revenue_category(
        baseline.get("revenue_category")
        or baseline.get("packageIntelligence", {}).get("revenueCategory")
    )
    clinical_summary = (
        f"{diagnosis}. "
        f"Current operational pathway is {pathway.get('admission_type', 'Urgent')} "
        f"with {pathway.get('bed_type', 'General')} bed planning and "
        f"{risk.get('risk_category', 'Medium')} risk prioritization."
    ).strip()
    ai_rationale = " ".join(
        part
        for part in [
            _clean_text(risk.get("reasoning")),
            _clean_text(pathway.get("reasoning")),
            "Fallback operational summary derived from the validated baseline engine.",
        ]
        if part
    )
    operational_action = (
        _clean_text(patient.get("admission", {}).get("summary"))
        or _clinical_field(patient, "doctorAdvice")
        or "Validate the admission pathway, confirm bed planning, and complete clinician review."
    )

    return {
        "clinical_summary": clinical_summary,
        "icd10_code": icd10_code,
        "icd10_description": icd10_description,
        "clinical_timeline": timeline or [],
        "revenue_estimate": revenue_estimate,
        "revenue_category": revenue_category,
        "ai_rationale": ai_rationale,
        "operational_action": operational_action,
        "confidence": 0.5,
    }


__all__ = [
    "fallback_clinical_analysis",
    "fallback_operational_summary_from_baseline",
    "fallback_pathway_from_baseline",
    "fallback_risk_from_baseline",
]
