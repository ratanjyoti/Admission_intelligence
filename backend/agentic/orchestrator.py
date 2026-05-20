from __future__ import annotations

import json
import os
from pathlib import Path
from threading import Lock
from typing import Any, Mapping

from backend.agentic.fallbacks import (
    baseline_bed_type,
    baseline_case_type,
    baseline_estimated_los,
    baseline_revenue_fields,
    baseline_timeline,
    fallback_llm_risk_assessment,
    risk_level_to_admission_type,
    risk_level_to_deferred_time,
    risk_level_to_readmission,
    risk_level_to_score,
)
from backend.agentic.nodes import llm_first_risk_agent
from backend.agentic.safe_runner import run_stage_with_retries
from backend.agentic.validator import (
    DEFAULT_ACTIONS,
    apply_rule_safety_validation,
    validate_llm_risk_assessment,
)
from backend.database import SessionLocal, database_enabled
from backend.llm_cache import get_cached_intelligence, make_source_hash, save_intelligence
from backend.llm_provider import get_agentic_model_name, get_agentic_provider_name


ROOT_DIR = Path(__file__).resolve().parents[2]
AGENTIC_CACHE_PATH = ROOT_DIR / "data" / "processed" / "agentic_risk_cache.json"
_AGENTIC_CACHE_LOCK = Lock()
_AGENTIC_CACHE_DATA: dict[str, Any] | None = None
AGENTIC_WORKFLOW_VERSION = (
    os.getenv("AGENTIC_WORKFLOW_VERSION", "llm_first_risk_v1").strip() or "llm_first_risk_v1"
)


def _patient_id(patient: Mapping[str, Any]) -> str:
    return str(
        patient.get("patientId")
        or patient.get("patient_id")
        or patient.get("Patient_ID")
        or patient.get("Patient ID")
        or ""
    ).strip()


def _source_hash(patient: Mapping[str, Any]) -> str:
    return make_source_hash(dict(patient), workflow_version=AGENTIC_WORKFLOW_VERSION)


def _max_retries() -> int:
    try:
        return max(0, int(os.getenv("AGENTIC_MAX_RETRIES", "2")))
    except ValueError:
        return 2


def _load_agentic_cache() -> dict[str, Any]:
    global _AGENTIC_CACHE_DATA

    if _AGENTIC_CACHE_DATA is None:
        if AGENTIC_CACHE_PATH.exists():
            try:
                _AGENTIC_CACHE_DATA = json.loads(AGENTIC_CACHE_PATH.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                _AGENTIC_CACHE_DATA = {}
        else:
            _AGENTIC_CACHE_DATA = {}

    return _AGENTIC_CACHE_DATA


def _save_agentic_cache(cache_data: Mapping[str, Any]) -> None:
    AGENTIC_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    AGENTIC_CACHE_PATH.write_text(
        json.dumps(dict(cache_data), ensure_ascii=True, indent=2),
        encoding="utf-8",
    )


def _get_cached_agentic_from_file(patient: Mapping[str, Any]) -> dict[str, Any] | None:
    patient_id = _patient_id(patient)
    if not patient_id:
        return None

    entry = _load_agentic_cache().get(patient_id)
    if not isinstance(entry, Mapping):
        return None

    if entry.get("source_hash") != _source_hash(patient):
        return None

    payload = entry.get("payload")
    return dict(payload) if isinstance(payload, Mapping) else None


def _save_cached_agentic_to_file(patient: Mapping[str, Any], payload: Mapping[str, Any]) -> None:
    patient_id = _patient_id(patient)
    if not patient_id:
        return

    with _AGENTIC_CACHE_LOCK:
        cache_data = _load_agentic_cache()
        cache_data[patient_id] = {
            "source_hash": _source_hash(patient),
            "payload": dict(payload),
        }
        _save_agentic_cache(cache_data)


def _get_cached_agentic_intelligence(patient: Mapping[str, Any]) -> dict[str, Any] | None:
    patient_id = _patient_id(patient)
    if patient_id and database_enabled():
        db = SessionLocal()
        try:
            cached = get_cached_intelligence(db, patient_id, _source_hash(patient))
            if cached and isinstance(cached.intelligence_json, Mapping):
                return dict(cached.intelligence_json)
        except Exception:
            pass
        finally:
            db.close()

    return _get_cached_agentic_from_file(patient)


def _save_cached_agentic_intelligence(patient: Mapping[str, Any], payload: Mapping[str, Any]) -> None:
    patient_id = _patient_id(patient)
    if not patient_id:
        return

    if database_enabled():
        db = SessionLocal()
        try:
            save_intelligence(
                db=db,
                patient_id=patient_id,
                source_hash=_source_hash(patient),
                intelligence=dict(payload),
                provider=str(payload.get("provider") or get_agentic_provider_name()),
                model_name=str(payload.get("model_name") or get_agentic_model_name()),
            )
            return
        except Exception:
            pass
        finally:
            db.close()

    _save_cached_agentic_to_file(patient, payload)


def _confidence(payload: Mapping[str, Any]) -> float:
    try:
        return round(max(0.0, min(1.0, float(payload.get("confidence", 0.0)))), 3)
    except (TypeError, ValueError):
        return 0.0


def _clinical_analysis_from_assessment(
    patient: Mapping[str, Any],
    assessment: Mapping[str, Any],
    safety_validation: Mapping[str, Any],
) -> dict[str, Any]:
    clinical = patient.get("clinical", {}) if isinstance(patient.get("clinical"), Mapping) else {}
    diagnosis = (
        clinical.get("diagnosis")
        or patient.get("diagnosis")
        or "Diagnosis requires clinician confirmation"
    )
    return {
        "confirmed_diagnosis": str(diagnosis).strip(),
        "possible_symptoms": [],
        "red_flags": list(assessment.get("keyRiskFactors", [])),
        "comorbidities": [],
        "history": str(clinical.get("vitalRemarks") or patient.get("vitalRemarks") or "").strip(),
        "progression": "unknown",
        "clinical_urgency_signals": list(safety_validation.get("safetyFlags", [])),
        "missing_data_flags": list(safety_validation.get("missingDataFlags", [])),
        "evidence": [],
        "confidence": _confidence(assessment),
    }


def _risk_scores_from_assessment(assessment: Mapping[str, Any]) -> dict[str, Any]:
    risk_level = str(assessment.get("riskLevel") or "Medium")
    score = risk_level_to_score(risk_level)
    return {
        "acuity_risk": score,
        "deterioration_risk": score,
        "readmission_risk": risk_level_to_readmission(risk_level),
        "dropout_risk": risk_level_to_readmission(risk_level),
        "composite_risk_score": score,
        "risk_category": risk_level,
        "top_risk_drivers": list(assessment.get("keyRiskFactors", [])),
        "reasoning": str(assessment.get("reason") or "").strip(),
        "confidence": _confidence(assessment),
    }


def _pathway_plan_from_assessment(
    patient: Mapping[str, Any],
    assessment: Mapping[str, Any],
    baseline_operational: Mapping[str, Any] | None,
) -> dict[str, Any]:
    risk_level = str(assessment.get("riskLevel") or "Medium")
    baseline = baseline_operational or {}
    treatment_plan = baseline.get("treatmentPlan", {})
    suggested_action = str(assessment.get("suggestedAction") or DEFAULT_ACTIONS[risk_level]).strip()
    case_type = baseline_case_type(baseline)
    bed_type = baseline_bed_type(baseline, patient)
    estimated_los = baseline_estimated_los(baseline)

    if not bed_type:
        bed_type = "ICU" if risk_level == "Critical" else "HDU" if risk_level == "High" else "General"

    return {
        "admission_type": risk_level_to_admission_type(risk_level),
        "case_type": case_type,
        "primary_treatment": str(treatment_plan.get("primary") or suggested_action).strip(),
        "secondary_treatment": str(
            treatment_plan.get("secondary")
            or "Continue close observation and escalate if symptoms or vitals worsen."
        ).strip(),
        "deferred_time": risk_level_to_deferred_time(risk_level),
        "bed_type": bed_type,
        "estimated_los_days": estimated_los,
        "procedure_name": None,
        "inferred_procedure_name": None,
        "reasoning": suggested_action,
        "confidence": _confidence(assessment),
    }


def _operational_summary_from_assessment(
    patient: Mapping[str, Any],
    assessment: Mapping[str, Any],
    baseline_operational: Mapping[str, Any] | None,
) -> dict[str, Any]:
    clinical = patient.get("clinical", {}) if isinstance(patient.get("clinical"), Mapping) else {}
    diagnosis = str(clinical.get("diagnosis") or patient.get("diagnosis") or "This patient").strip()
    revenue_estimate, revenue_category = baseline_revenue_fields(baseline_operational)
    timeline = baseline_timeline(baseline_operational)
    reason = str(assessment.get("reason") or "").strip()
    risk_level = str(assessment.get("riskLevel") or "Medium")

    return {
        "clinical_summary": (
            f"{diagnosis}. The LLM-first risk layer classified this case as {risk_level} risk "
            f"based on the current clinical narrative and documented indicators."
        ),
        "icd10_code": None,
        "icd10_description": None,
        "clinical_timeline": timeline,
        "revenue_estimate": revenue_estimate,
        "revenue_category": revenue_category,
        "ai_rationale": reason,
        "operational_action": str(
            assessment.get("suggestedAction") or DEFAULT_ACTIONS.get(risk_level, DEFAULT_ACTIONS["Medium"])
        ).strip(),
        "confidence": _confidence(assessment),
    }


def get_cached_agentic_patient_pipeline(patient: Mapping[str, Any]) -> dict[str, Any] | None:
    return _get_cached_agentic_intelligence(patient)


def run_agentic_patient_pipeline(
    patient: Mapping[str, Any],
    baseline_operational: Mapping[str, Any] | None = None,
    use_cache: bool = True,
    save_cache: bool = True,
) -> dict[str, Any]:
    if use_cache:
        cached = _get_cached_agentic_intelligence(patient)
        if cached:
            return cached

    baseline = dict(baseline_operational or {})
    provider = get_agentic_provider_name()
    model_name = get_agentic_model_name(provider)

    llm_stage = run_stage_with_retries(
        stage_name="llm_first_risk_assessment",
        stage_func=lambda: llm_first_risk_agent(patient),
        validator_func=validate_llm_risk_assessment,
        fallback_func=lambda: fallback_llm_risk_assessment(patient, baseline),
        max_retries=_max_retries(),
    )

    llm_assessment, safety_validation, safety_issues = apply_rule_safety_validation(
        llm_stage["data"],
        patient,
        baseline,
    )
    issues = [f"llm_first_risk_assessment: {issue}" for issue in llm_stage.get("issues", [])]
    issues.extend(safety_issues)

    clinical_analysis = _clinical_analysis_from_assessment(patient, llm_assessment, safety_validation)
    risk_scores = _risk_scores_from_assessment(llm_assessment)
    pathway_plan = _pathway_plan_from_assessment(patient, llm_assessment, baseline)
    operational_summary = _operational_summary_from_assessment(patient, llm_assessment, baseline)

    result = {
        "workflow_version": AGENTIC_WORKFLOW_VERSION,
        "provider": provider,
        "model_name": model_name,
        "llm_assessment": llm_assessment,
        "safety_validation": safety_validation,
        "clinical_analysis": clinical_analysis,
        "risk_scores": risk_scores,
        "pathway_plan": pathway_plan,
        "operational_summary": operational_summary,
        "pipeline_confidence": _confidence(llm_assessment),
        "validation_status": "Needs Review" if llm_stage.get("used_fallback") else "Validated",
        "issues": issues,
        "stage_results": {
            "llm_first_risk_assessment": {
                "attempts": llm_stage.get("attempts", 0),
                "used_fallback": bool(llm_stage.get("used_fallback")),
                "issues": list(llm_stage.get("issues", [])),
            }
        },
    }

    if save_cache and result["validation_status"] == "Validated":
        _save_cached_agentic_intelligence(patient, result)

    return result


__all__ = [
    "AGENTIC_WORKFLOW_VERSION",
    "get_cached_agentic_patient_pipeline",
    "run_agentic_patient_pipeline",
]
