from __future__ import annotations

import os
from typing import Any, Mapping

from backend.agentic.fallbacks import (
    fallback_clinical_analysis,
    fallback_operational_summary_from_baseline,
    fallback_pathway_from_baseline,
    fallback_risk_from_baseline,
)
from backend.agentic.nodes import (
    clinical_analyst_agent,
    operational_summarizer_agent,
    pathway_planner_agent,
    risk_scorer_agent,
)
from backend.agentic.safe_runner import run_stage_with_retries
from backend.agentic.validator import (
    validate_clinical_analysis,
    validate_operational_summary,
    validate_pathway_plan,
    validate_risk_scores,
)
from backend.database import SessionLocal, database_enabled
from backend.llm_cache import get_cached_intelligence, make_source_hash, save_intelligence
from backend.llm_provider import get_agentic_model_name, get_agentic_provider_name


AGENTIC_WORKFLOW_VERSION = (
    os.getenv("AGENTIC_WORKFLOW_VERSION", "agentic_v1_safe").strip() or "agentic_v1_safe"
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


def _stage_trace(stage_result: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "attempts": stage_result.get("attempts", 0),
        "used_fallback": bool(stage_result.get("used_fallback")),
        "issues": list(stage_result.get("issues", [])),
    }


def _collect_stage_issues(stage_name: str, stage_result: Mapping[str, Any]) -> list[str]:
    return [f"{stage_name}: {issue}" for issue in stage_result.get("issues", [])]


def _pipeline_confidence(*stages: Mapping[str, Any]) -> float:
    scores = []
    for stage in stages:
        confidence = stage.get("data", {}).get("confidence")
        try:
            numeric = float(confidence)
        except (TypeError, ValueError):
            continue
        scores.append(max(0.0, min(1.0, numeric)))

    if not scores:
        return 0.0

    return round(sum(scores) / len(scores), 3)


def _get_cached_agentic_intelligence(patient: Mapping[str, Any]) -> dict[str, Any] | None:
    if not database_enabled():
        return None

    patient_id = _patient_id(patient)
    if not patient_id:
        return None

    db = SessionLocal()
    try:
        cached = get_cached_intelligence(db, patient_id, _source_hash(patient))
        return cached.intelligence_json if cached else None
    except Exception:
        return None
    finally:
        db.close()


def _save_cached_agentic_intelligence(patient: Mapping[str, Any], payload: Mapping[str, Any]) -> None:
    if not database_enabled():
        return

    patient_id = _patient_id(patient)
    if not patient_id:
        return

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
    except Exception:
        return
    finally:
        db.close()


def run_agentic_patient_pipeline(
    patient: Mapping[str, Any],
    baseline_operational: Mapping[str, Any] | None = None,
    use_cache: bool = True,
) -> dict[str, Any]:
    if use_cache:
        cached = _get_cached_agentic_intelligence(patient)
        if cached:
            return cached

    baseline = dict(baseline_operational or {})
    max_retries = _max_retries()
    provider = get_agentic_provider_name()
    model_name = get_agentic_model_name(provider)

    clinical_stage = run_stage_with_retries(
        stage_name="clinical_analysis",
        stage_func=lambda: clinical_analyst_agent(patient),
        validator_func=validate_clinical_analysis,
        fallback_func=lambda: fallback_clinical_analysis(patient, baseline),
        max_retries=max_retries,
    )
    clinical = clinical_stage["data"]

    risk_stage = run_stage_with_retries(
        stage_name="risk_scores",
        stage_func=lambda: risk_scorer_agent(patient, clinical),
        validator_func=validate_risk_scores,
        fallback_func=lambda: fallback_risk_from_baseline(patient, baseline, clinical),
        max_retries=max_retries,
    )
    risk = risk_stage["data"]

    pathway_stage = run_stage_with_retries(
        stage_name="pathway_plan",
        stage_func=lambda: pathway_planner_agent(patient, clinical, risk),
        validator_func=validate_pathway_plan,
        fallback_func=lambda: fallback_pathway_from_baseline(patient, baseline),
        max_retries=max_retries,
    )
    pathway = pathway_stage["data"]

    summary_stage = run_stage_with_retries(
        stage_name="operational_summary",
        stage_func=lambda: operational_summarizer_agent(patient, clinical, risk, pathway),
        validator_func=validate_operational_summary,
        fallback_func=lambda: fallback_operational_summary_from_baseline(
            patient,
            baseline,
            clinical,
            risk,
            pathway,
        ),
        max_retries=max_retries,
    )
    summary = summary_stage["data"]

    stage_results = {
        "clinical_analysis": _stage_trace(clinical_stage),
        "risk_scores": _stage_trace(risk_stage),
        "pathway_plan": _stage_trace(pathway_stage),
        "operational_summary": _stage_trace(summary_stage),
    }
    issues = (
        _collect_stage_issues("clinical_analysis", clinical_stage)
        + _collect_stage_issues("risk_scores", risk_stage)
        + _collect_stage_issues("pathway_plan", pathway_stage)
        + _collect_stage_issues("operational_summary", summary_stage)
    )
    used_fallback = any(stage["used_fallback"] for stage in [clinical_stage, risk_stage, pathway_stage, summary_stage])
    validation_status = "Needs Review" if used_fallback else "Validated"
    pipeline_confidence = _pipeline_confidence(
        clinical_stage,
        risk_stage,
        pathway_stage,
        summary_stage,
    )

    result = {
        "workflow_version": AGENTIC_WORKFLOW_VERSION,
        "provider": provider,
        "model_name": model_name,
        "clinical_analysis": clinical,
        "risk_scores": risk,
        "pathway_plan": pathway,
        "operational_summary": summary,
        "pipeline_confidence": pipeline_confidence,
        "validation_status": validation_status,
        "issues": issues,
        "stage_results": stage_results,
    }

    if use_cache and validation_status == "Validated":
        _save_cached_agentic_intelligence(patient, result)

    return result


__all__ = [
    "AGENTIC_WORKFLOW_VERSION",
    "run_agentic_patient_pipeline",
]
