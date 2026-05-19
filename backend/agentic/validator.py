from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


ICD10_PATTERN = re.compile(r"^[A-TV-Z][0-9][0-9A-Z](\.[0-9A-Z]{1,4})?$")


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _optional_text(value: Any) -> str | None:
    cleaned = _clean_text(value)
    return cleaned or None


def _list_of_strings(value: Any) -> list[str]:
    if value is None or value == "":
        return []
    if isinstance(value, list):
        return [_clean_text(item) for item in value if _clean_text(item)]
    cleaned = _clean_text(value)
    return [cleaned] if cleaned else []


def _normalize_choice(value: Any, mapping: dict[str, str], field_name: str) -> str:
    cleaned = _clean_text(value)
    normalized = mapping.get(cleaned.lower())

    if normalized:
        return normalized

    raise ValueError(f"Invalid {field_name}: {cleaned or 'empty'}")


class AgenticBaseModel(BaseModel):
    model_config = ConfigDict(extra="ignore")


class EvidenceItem(AgenticBaseModel):
    source_field: str
    quote: str
    signal: str

    @field_validator("source_field", "quote", "signal", mode="before")
    @classmethod
    def _validate_text(cls, value: Any) -> str:
        return _clean_text(value)


class ClinicalAnalysis(AgenticBaseModel):
    confirmed_diagnosis: str
    possible_symptoms: list[str] = Field(default_factory=list)
    red_flags: list[str] = Field(default_factory=list)
    comorbidities: list[str] = Field(default_factory=list)
    history: str = ""
    progression: Literal["stable", "worsening", "improving", "acute_onset", "unknown"]
    clinical_urgency_signals: list[str] = Field(default_factory=list)
    missing_data_flags: list[str] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)

    @field_validator(
        "confirmed_diagnosis",
        "history",
        mode="before",
    )
    @classmethod
    def _validate_required_text(cls, value: Any) -> str:
        return _clean_text(value)

    @field_validator(
        "possible_symptoms",
        "red_flags",
        "comorbidities",
        "clinical_urgency_signals",
        "missing_data_flags",
        mode="before",
    )
    @classmethod
    def _validate_lists(cls, value: Any) -> list[str]:
        return _list_of_strings(value)

    @field_validator("progression", mode="before")
    @classmethod
    def _validate_progression(cls, value: Any) -> str:
        mapping = {
            "stable": "stable",
            "worsening": "worsening",
            "improving": "improving",
            "acute_onset": "acute_onset",
            "acute onset": "acute_onset",
            "acute": "acute_onset",
            "unknown": "unknown",
        }
        return _normalize_choice(value, mapping, "progression")


class RiskScores(AgenticBaseModel):
    acuity_risk: int = Field(ge=1, le=10)
    deterioration_risk: int = Field(ge=1, le=10)
    composite_risk_score: int = Field(ge=1, le=10)
    risk_category: Literal["Low", "Medium", "High", "Critical"]
    readmission_risk: Literal["Low", "Medium", "High"]
    dropout_risk: Literal["Low", "Medium", "High"]
    top_risk_drivers: list[str] = Field(default_factory=list)
    reasoning: str
    confidence: float = Field(ge=0.0, le=1.0)

    @field_validator("risk_category", mode="before")
    @classmethod
    def _validate_risk_category(cls, value: Any) -> str:
        mapping = {
            "low": "Low",
            "medium": "Medium",
            "moderate": "Medium",
            "high": "High",
            "critical": "Critical",
        }
        return _normalize_choice(value, mapping, "risk_category")

    @field_validator("readmission_risk", "dropout_risk", mode="before")
    @classmethod
    def _validate_risk_labels(cls, value: Any) -> str:
        mapping = {
            "low": "Low",
            "medium": "Medium",
            "moderate": "Medium",
            "high": "High",
        }
        return _normalize_choice(value, mapping, "risk label")

    @field_validator("top_risk_drivers", mode="before")
    @classmethod
    def _validate_top_risk_drivers(cls, value: Any) -> list[str]:
        return _list_of_strings(value)

    @field_validator("reasoning", mode="before")
    @classmethod
    def _validate_reasoning(cls, value: Any) -> str:
        return _clean_text(value)


class PathwayPlan(AgenticBaseModel):
    admission_type: Literal["Emergency", "Urgent", "Elective"]
    case_type: Literal["Surgical", "Medication Management", "Daycare"]
    primary_treatment: str
    secondary_treatment: str
    deferred_time: str
    bed_type: Literal["ICU", "HDU", "General", "Suite", "Daycare Bay"]
    estimated_los_days: int | None = Field(default=None, ge=0, le=60)
    procedure_name: str | None = None
    inferred_procedure_name: str | None = None
    reasoning: str
    confidence: float = Field(ge=0.0, le=1.0)

    @field_validator("admission_type", mode="before")
    @classmethod
    def _validate_admission_type(cls, value: Any) -> str:
        mapping = {
            "emergency": "Emergency",
            "urgent": "Urgent",
            "elective": "Elective",
        }
        return _normalize_choice(value, mapping, "admission_type")

    @field_validator("case_type", mode="before")
    @classmethod
    def _validate_case_type(cls, value: Any) -> str:
        mapping = {
            "surgical": "Surgical",
            "medication management": "Medication Management",
            "medical management": "Medication Management",
            "daycare": "Daycare",
            "day care": "Daycare",
        }
        return _normalize_choice(value, mapping, "case_type")

    @field_validator("bed_type", mode="before")
    @classmethod
    def _validate_bed_type(cls, value: Any) -> str:
        mapping = {
            "icu": "ICU",
            "hdu": "HDU",
            "general": "General",
            "general ward": "General",
            "general oncology ward": "General",
            "suite": "Suite",
            "daycare bay": "Daycare Bay",
            "day care bay": "Daycare Bay",
            "daycare": "Daycare Bay",
        }
        return _normalize_choice(value, mapping, "bed_type")

    @field_validator(
        "primary_treatment",
        "secondary_treatment",
        "deferred_time",
        "reasoning",
        mode="before",
    )
    @classmethod
    def _validate_text_fields(cls, value: Any) -> str:
        return _clean_text(value)

    @field_validator("procedure_name", "inferred_procedure_name", mode="before")
    @classmethod
    def _validate_optional_text_fields(cls, value: Any) -> str | None:
        return _optional_text(value)


class OperationalSummary(AgenticBaseModel):
    clinical_summary: str
    icd10_code: str | None = None
    icd10_description: str | None = None
    clinical_timeline: list[str] = Field(default_factory=list)
    revenue_estimate: str | None = None
    revenue_category: Literal["Low", "Medium", "High"] | None = None
    ai_rationale: str
    operational_action: str
    confidence: float = Field(ge=0.0, le=1.0)

    @field_validator("clinical_summary", "ai_rationale", "operational_action", mode="before")
    @classmethod
    def _validate_summary_text(cls, value: Any) -> str:
        return _clean_text(value)

    @field_validator("clinical_timeline", mode="before")
    @classmethod
    def _validate_timeline(cls, value: Any) -> list[str]:
        return _list_of_strings(value)

    @field_validator("icd10_code", mode="before")
    @classmethod
    def _validate_icd10_code(cls, value: Any) -> str | None:
        cleaned = _optional_text(value)
        if not cleaned:
            return None

        normalized = cleaned.upper()
        return normalized if ICD10_PATTERN.match(normalized) else None

    @field_validator("icd10_description", "revenue_estimate", mode="before")
    @classmethod
    def _validate_optional_summary_text(cls, value: Any) -> str | None:
        return _optional_text(value)

    @field_validator("revenue_category", mode="before")
    @classmethod
    def _validate_revenue_category(cls, value: Any) -> str | None:
        cleaned = _optional_text(value)
        if not cleaned:
            return None

        mapping = {
            "low": "Low",
            "medium": "Medium",
            "moderate": "Medium",
            "high": "High",
        }
        return _normalize_choice(cleaned, mapping, "revenue_category")


def validate_clinical_analysis(payload: dict[str, Any]) -> dict[str, Any]:
    return ClinicalAnalysis(**payload).model_dump()


def validate_risk_scores(payload: dict[str, Any]) -> dict[str, Any]:
    return RiskScores(**payload).model_dump()


def validate_pathway_plan(payload: dict[str, Any]) -> dict[str, Any]:
    return PathwayPlan(**payload).model_dump()


def validate_operational_summary(payload: dict[str, Any]) -> dict[str, Any]:
    return OperationalSummary(**payload).model_dump()


__all__ = [
    "ClinicalAnalysis",
    "OperationalSummary",
    "PathwayPlan",
    "RiskScores",
    "validate_clinical_analysis",
    "validate_operational_summary",
    "validate_pathway_plan",
    "validate_risk_scores",
]
