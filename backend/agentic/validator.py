from __future__ import annotations

from typing import Any, Literal, Mapping

from pydantic import BaseModel, ConfigDict, Field, field_validator


RISK_LEVEL_ORDER = {"Low": 0, "Medium": 1, "High": 2, "Critical": 3}
RISK_LEVEL_SCORES = {"Low": 3, "Medium": 5, "High": 7, "Critical": 9}
URGENCY_LEVEL_ORDER = {"Immediate": 0, "High": 1, "Medium": 2, "Low": 3}
URGENCY_SCORE_FLOORS = {"Immediate": 90, "High": 78, "Medium": 52, "Low": 20}
DEFAULT_ACTIONS = {
    "Low": "Routine clinician review and follow-up planning",
    "Medium": "Needs clinician review and short-interval follow-up",
    "High": "Needs urgent clinical review",
    "Critical": "Needs immediate escalation and monitored clinical review",
}
DEFAULT_PRIORITY_ACTIONS = {
    "Immediate": "Needs immediate specialist or critical-care review",
    "High": "Needs urgent same-day clinical review",
    "Medium": "Needs prioritized clinician review",
    "Low": "Routine queue review is acceptable",
}


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _list_of_strings(value: Any) -> list[str]:
    if value is None or value == "":
        return []
    if isinstance(value, list):
        return [_clean_text(item) for item in value if _clean_text(item)]
    cleaned = _clean_text(value)
    return [cleaned] if cleaned else []


def _normalize_risk_level(value: Any) -> str:
    mapping = {
        "low": "Low",
        "medium": "Medium",
        "moderate": "Medium",
        "high": "High",
        "critical": "Critical",
    }
    cleaned = _clean_text(value).lower()
    normalized = mapping.get(cleaned)
    if not normalized:
        raise ValueError(f"Invalid riskLevel: {cleaned or 'empty'}")
    return normalized


def _normalize_urgency_level(value: Any) -> str:
    mapping = {
        "immediate": "Immediate",
        "critical": "Immediate",
        "emergency": "Immediate",
        "high": "High",
        "urgent": "High",
        "medium": "Medium",
        "moderate": "Medium",
        "low": "Low",
    }
    cleaned = _clean_text(value).lower()
    normalized = mapping.get(cleaned)
    if not normalized:
        raise ValueError(f"Invalid urgencyLevel: {cleaned or 'empty'}")
    return normalized


def _combine_patient_text(patient: Mapping[str, Any]) -> str:
    clinical = patient.get("clinical", {}) if isinstance(patient.get("clinical"), Mapping) else {}
    parts = [
        patient.get("department"),
        patient.get("doctorName"),
        clinical.get("diagnosis", patient.get("diagnosis")),
        clinical.get("clinicalNotes", patient.get("clinicalNotes")),
        clinical.get("physicalRemarks", patient.get("physicalRemarks")),
        clinical.get("vitalRemarks", patient.get("vitalRemarks")),
        clinical.get("investigations", patient.get("investigations")),
        clinical.get("doctorAdvice", patient.get("doctorAdvice")),
        clinical.get("medicineDetails", patient.get("medicineDetails")),
    ]
    return " ".join(_clean_text(part) for part in parts if _clean_text(part)).lower()


def _extract_age(patient: Mapping[str, Any]) -> int | None:
    value = patient.get("age") or patient.get("Age")
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _repeat_visit_signals(patient: Mapping[str, Any]) -> tuple[bool, int]:
    journey = patient.get("journey", {}) if isinstance(patient.get("journey"), Mapping) else {}
    repeat_visit = journey.get("repeatVisit", patient.get("repeatVisit"))
    visit_count = journey.get("visitCount", patient.get("visitCount"))
    repeat_flag = repeat_visit is True or _clean_text(repeat_visit).lower() in {"true", "yes", "1"}

    try:
        visit_count_value = int(float(visit_count))
    except (TypeError, ValueError):
        visit_count_value = 1

    return repeat_flag, max(1, visit_count_value)


class AgenticBaseModel(BaseModel):
    model_config = ConfigDict(extra="ignore")


class LlmRiskAssessment(AgenticBaseModel):
    riskLevel: Literal["Low", "Medium", "High", "Critical"]
    reason: str
    keyRiskFactors: list[str] = Field(default_factory=list)
    suggestedAction: str
    confidence: float = Field(ge=0.0, le=1.0)

    @field_validator("riskLevel", mode="before")
    @classmethod
    def _validate_risk_level(cls, value: Any) -> str:
        return _normalize_risk_level(value)

    @field_validator("reason", "suggestedAction", mode="before")
    @classmethod
    def _validate_text(cls, value: Any) -> str:
        return _clean_text(value)

    @field_validator("keyRiskFactors", mode="before")
    @classmethod
    def _validate_key_risk_factors(cls, value: Any) -> list[str]:
        return _list_of_strings(value)


class PriorityPatientAssessment(AgenticBaseModel):
    patientId: str
    urgencyLevel: Literal["Immediate", "High", "Medium", "Low"]
    priorityScore: int = Field(ge=0, le=100)
    reason: str
    suggestedAction: str
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)

    @field_validator("patientId", mode="before")
    @classmethod
    def _validate_patient_id(cls, value: Any) -> str:
        cleaned = _clean_text(value)
        if not cleaned:
            raise ValueError("patientId is required")
        return cleaned

    @field_validator("urgencyLevel", mode="before")
    @classmethod
    def _validate_urgency_level(cls, value: Any) -> str:
        return _normalize_urgency_level(value)

    @field_validator("reason", "suggestedAction", mode="before")
    @classmethod
    def _validate_priority_text(cls, value: Any) -> str:
        return _clean_text(value)


class PriorityQueueResponse(AgenticBaseModel):
    prioritizedPatients: list[PriorityPatientAssessment] = Field(default_factory=list)


def validate_llm_risk_assessment(payload: dict[str, Any]) -> dict[str, Any]:
    return LlmRiskAssessment(**payload).model_dump()


def validate_llm_priority_queue(payload: dict[str, Any]) -> dict[str, Any]:
    return PriorityQueueResponse(**payload).model_dump()


def _max_risk_level(first: str, second: str) -> str:
    return first if RISK_LEVEL_ORDER[first] >= RISK_LEVEL_ORDER[second] else second


def _max_urgency_level(first: str, second: str) -> str:
    return first if URGENCY_LEVEL_ORDER[first] <= URGENCY_LEVEL_ORDER[second] else second


def apply_rule_safety_validation(
    assessment: Mapping[str, Any],
    patient: Mapping[str, Any],
    baseline_operational: Mapping[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    adjusted = dict(assessment)
    baseline = baseline_operational or {}
    issues: list[str] = []
    adjustments: list[str] = []
    missing_data_flags: list[str] = []
    safety_flags: list[str] = []
    text = _combine_patient_text(patient)
    risk_level = adjusted.get("riskLevel", "Medium")
    age = _extract_age(patient)
    repeat_visit, visit_count = _repeat_visit_signals(patient)

    risk_rules = [
        (["low oxygen", "spo2", "hypoxia", "oxygen saturation"], "Critical", "Possible hypoxia or low oxygen concern."),
        (["stroke", "cva", "hemiparesis", "altered sensorium"], "Critical", "Neurologic emergency indicators present."),
        (["unconscious", "collapse", "seizure", "fits"], "Critical", "Acute neurologic instability indicators present."),
        (["shock", "hypotension", "active bleeding", "hemorrhage"], "Critical", "Hemodynamic instability or bleeding concern."),
        (["chest pain", "breathlessness", "shortness of breath", "troponin"], "High", "Cardiorespiratory high-risk indicators present."),
        (["creatinine", "dialysis", "transplant", "sepsis"], "High", "Complex renal, transplant, or infectious risk indicators present."),
    ]

    for keywords, minimum_risk, message in risk_rules:
        if any(keyword in text for keyword in keywords):
            safety_flags.append(message)
            new_level = _max_risk_level(risk_level, minimum_risk)
            if new_level != risk_level:
                adjustments.append(f"Safety rules escalated risk from {risk_level} to {new_level}: {message}")
                risk_level = new_level

    if age is not None and age >= 75:
        safety_flags.append("Advanced age increases clinical fragility.")
        new_level = _max_risk_level(risk_level, "Medium")
        if new_level != risk_level:
            adjustments.append(f"Safety rules escalated risk from {risk_level} to {new_level}: advanced age factor.")
            risk_level = new_level

    if repeat_visit and visit_count >= 3:
        safety_flags.append("Repeat visits and frequent reassessment suggest unresolved clinical risk.")
        new_level = _max_risk_level(risk_level, "Medium")
        if new_level != risk_level:
            adjustments.append(f"Safety rules escalated risk from {risk_level} to {new_level}: repeat-visit pattern.")
            risk_level = new_level

    if not _clean_text(patient.get("diagnosis")) and not _clean_text(
        (patient.get("clinical", {}) if isinstance(patient.get("clinical"), Mapping) else {}).get("diagnosis")
    ):
        missing_data_flags.append("Diagnosis field is missing.")
    if not text:
        missing_data_flags.append("Clinical notes are empty or too sparse for a strong LLM judgment.")
    if not _clean_text(
        (patient.get("clinical", {}) if isinstance(patient.get("clinical"), Mapping) else {}).get("doctorAdvice")
        or patient.get("doctorAdvice")
    ):
        missing_data_flags.append("Doctor advice is missing.")

    key_risk_factors = list(adjusted.get("keyRiskFactors", []))
    baseline_red_flags = baseline.get("red_flags", [])
    if not isinstance(baseline_red_flags, list):
        baseline_red_flags = []

    for factor in safety_flags + baseline_red_flags:
        cleaned = _clean_text(factor)
        if cleaned and cleaned not in key_risk_factors:
            key_risk_factors.append(cleaned)

    if not key_risk_factors:
        key_risk_factors.append("Structured clinician review is still required because the record is limited.")

    confidence = float(adjusted.get("confidence", 0.0))
    if missing_data_flags:
        confidence = min(confidence, 0.72)
    if adjustments:
        confidence = min(confidence, 0.82)

    suggested_action = _clean_text(adjusted.get("suggestedAction")) or DEFAULT_ACTIONS[risk_level]
    if adjustments and "escalation" not in suggested_action.lower() and risk_level == "Critical":
        suggested_action = DEFAULT_ACTIONS["Critical"]

    reason = _clean_text(adjusted.get("reason")) or "LLM assessment requires clinician review."
    if adjustments:
        reason = f"{reason} Safety validation adjusted the final risk because obvious high-risk signals were present."

    adjusted.update(
        {
            "riskLevel": risk_level,
            "reason": reason,
            "keyRiskFactors": key_risk_factors[:6],
            "suggestedAction": suggested_action,
            "confidence": round(max(0.0, min(1.0, confidence)), 3),
        }
    )

    issues.extend(adjustments)
    if missing_data_flags:
        issues.extend(f"Missing data: {flag}" for flag in missing_data_flags)

    safety_validation = {
        "applied": bool(adjustments or missing_data_flags or safety_flags),
        "finalRiskLevel": risk_level,
        "adjustments": adjustments,
        "safetyFlags": safety_flags,
        "missingDataFlags": missing_data_flags,
    }

    return adjusted, safety_validation, issues


def apply_priority_safety_validation(
    assessment: Mapping[str, Any],
    patient: Mapping[str, Any],
    baseline_operational: Mapping[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    adjusted = dict(assessment)
    baseline = baseline_operational or {}
    issues: list[str] = []
    adjustments: list[str] = []
    missing_data_flags: list[str] = []
    safety_flags: list[str] = []
    text = _combine_patient_text(patient)
    urgency_level = _normalize_urgency_level(adjusted.get("urgencyLevel", "Medium"))

    try:
        priority_score = int(float(adjusted.get("priorityScore", URGENCY_SCORE_FLOORS["Medium"])))
    except (TypeError, ValueError):
        priority_score = URGENCY_SCORE_FLOORS["Medium"]

    age = _extract_age(patient)
    repeat_visit, visit_count = _repeat_visit_signals(patient)
    baseline_risk = _clean_text(patient.get("risk", {}).get("category")).lower()
    baseline_admission = _clean_text(patient.get("admission", {}).get("type")).lower()
    baseline_bed = _clean_text(patient.get("bed", {}).get("type")).lower()
    deferred_label = _clean_text(baseline.get("deferredTime", {}).get("label")).lower()

    urgency_rules = [
        (
            ["low oxygen", "spo2", "hypoxia", "oxygen saturation", "retractions", "respiratory distress"],
            "Immediate",
            94,
            "Respiratory distress or oxygenation concern present.",
        ),
        (
            ["stroke", "cva", "hemiparesis", "altered sensorium", "unconscious", "collapse"],
            "Immediate",
            93,
            "Neurologic emergency indicators present.",
        ),
        (
            ["shock", "hypotension", "active bleeding", "hemorrhage", "seizure", "fits"],
            "Immediate",
            92,
            "Hemodynamic or neurologic instability indicators present.",
        ),
        (
            ["chest pain", "breathlessness", "shortness of breath", "troponin", "nebulization"],
            "High",
            84,
            "Cardiorespiratory high-risk indicators present.",
        ),
        (
            ["creatinine", "dialysis", "transplant", "sepsis"],
            "High",
            80,
            "Renal, transplant, or infectious risk indicators present.",
        ),
    ]

    for keywords, minimum_urgency, minimum_score, message in urgency_rules:
        if any(keyword in text for keyword in keywords):
            safety_flags.append(message)
            new_level = _max_urgency_level(urgency_level, minimum_urgency)
            if new_level != urgency_level:
                adjustments.append(
                    f"Safety rules escalated urgency from {urgency_level} to {new_level}: {message}"
                )
                urgency_level = new_level
            priority_score = max(priority_score, minimum_score)

    if baseline_risk == "critical" or baseline_admission == "emergency" or baseline_bed in {"icu", "hdu"}:
        safety_flags.append("Existing critical-risk, emergency, or high-dependency pathway is already present.")
        new_level = _max_urgency_level(urgency_level, "Immediate")
        if new_level != urgency_level:
            adjustments.append(
                f"Safety rules escalated urgency from {urgency_level} to {new_level}: existing critical pathway."
            )
            urgency_level = new_level
        priority_score = max(priority_score, 91)

    if baseline_risk == "high" or baseline_admission == "urgent" or deferred_label == "cannot be safely delayed":
        safety_flags.append("Existing rule-based triage suggests urgent queue placement.")
        new_level = _max_urgency_level(urgency_level, "High")
        if new_level != urgency_level:
            adjustments.append(
                f"Safety rules escalated urgency from {urgency_level} to {new_level}: rule-based urgency context."
            )
            urgency_level = new_level
        priority_score = max(priority_score, 80)

    if age is not None and age >= 75:
        safety_flags.append("Advanced age increases fragility and queue priority.")
        new_level = _max_urgency_level(urgency_level, "Medium")
        if new_level != urgency_level:
            adjustments.append(
                f"Safety rules escalated urgency from {urgency_level} to {new_level}: advanced age factor."
            )
            urgency_level = new_level
        priority_score = max(priority_score, 58)

    if repeat_visit and visit_count >= 3:
        safety_flags.append("Repeat visits suggest unresolved risk that should be prioritized.")
        new_level = _max_urgency_level(urgency_level, "Medium")
        if new_level != urgency_level:
            adjustments.append(
                f"Safety rules escalated urgency from {urgency_level} to {new_level}: repeat-visit pattern."
            )
            urgency_level = new_level
        priority_score = max(priority_score, 55)

    if not _clean_text(patient.get("diagnosis")) and not _clean_text(
        (patient.get("clinical", {}) if isinstance(patient.get("clinical"), Mapping) else {}).get("diagnosis")
    ):
        missing_data_flags.append("Diagnosis field is missing.")
    if not text:
        missing_data_flags.append("Clinical notes are empty or too sparse for a strong LLM judgment.")
    if not _clean_text(
        (patient.get("clinical", {}) if isinstance(patient.get("clinical"), Mapping) else {}).get("doctorAdvice")
        or patient.get("doctorAdvice")
    ):
        missing_data_flags.append("Doctor advice is missing.")

    confidence = float(adjusted.get("confidence", 0.0))
    if missing_data_flags:
        confidence = min(confidence, 0.72)
    if adjustments:
        confidence = min(confidence, 0.82)

    reason = _clean_text(adjusted.get("reason")) or "Priority assessment requires clinician review."
    if adjustments:
        reason = f"{reason} Safety validation adjusted the final urgency because stronger risk signals were present."

    suggested_action = (
        _clean_text(adjusted.get("suggestedAction")) or DEFAULT_PRIORITY_ACTIONS[urgency_level]
    )

    adjusted.update(
        {
            "urgencyLevel": urgency_level,
            "priorityScore": max(0, min(100, max(priority_score, URGENCY_SCORE_FLOORS[urgency_level]))),
            "reason": reason,
            "suggestedAction": suggested_action,
            "confidence": round(max(0.0, min(1.0, confidence)), 3),
        }
    )

    issues.extend(adjustments)
    if missing_data_flags:
        issues.extend(f"Missing data: {flag}" for flag in missing_data_flags)

    safety_validation = {
        "applied": bool(adjustments or missing_data_flags or safety_flags),
        "finalUrgencyLevel": urgency_level,
        "adjustments": adjustments,
        "safetyFlags": safety_flags,
        "missingDataFlags": missing_data_flags,
    }

    return adjusted, safety_validation, issues


def sort_prioritized_patients(prioritized_patients: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        (dict(item) for item in prioritized_patients),
        key=lambda item: (
            URGENCY_LEVEL_ORDER.get(_clean_text(item.get("urgencyLevel")), 99),
            -int(item.get("priorityScore") or 0),
            _clean_text(item.get("patientId")),
        ),
    )


def assign_priority_ranks(prioritized_patients: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    ranked = []

    for index, item in enumerate(sort_prioritized_patients(prioritized_patients), start=1):
        row = dict(item)
        row["priorityRank"] = index
        ranked.append(row)

    return ranked


__all__ = [
    "DEFAULT_ACTIONS",
    "DEFAULT_PRIORITY_ACTIONS",
    "LlmRiskAssessment",
    "PriorityPatientAssessment",
    "PriorityQueueResponse",
    "RISK_LEVEL_ORDER",
    "RISK_LEVEL_SCORES",
    "URGENCY_LEVEL_ORDER",
    "apply_rule_safety_validation",
    "apply_priority_safety_validation",
    "assign_priority_ranks",
    "sort_prioritized_patients",
    "validate_llm_risk_assessment",
    "validate_llm_priority_queue",
]
