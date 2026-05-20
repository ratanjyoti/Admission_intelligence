from __future__ import annotations

import json
import os
from pathlib import Path
from threading import Lock
from typing import Any, Mapping

from backend.agentic.fallbacks import (
    fallback_priority_assessment,
    fallback_priority_queue_assessment,
)
from backend.agentic.nodes import llm_priority_queue_agent
from backend.agentic.safe_runner import run_stage_with_retries
from backend.agentic.validator import (
    DEFAULT_PRIORITY_ACTIONS,
    apply_priority_safety_validation,
    assign_priority_ranks,
    sort_prioritized_patients,
    validate_llm_priority_queue,
)
from backend.database import SessionLocal, database_enabled
from backend.llm_cache import get_cached_intelligence, make_source_hash, save_intelligence
from backend.llm_provider import get_agentic_model_name, get_agentic_provider_name
from backend.operational_intelligence import (
    build_rule_based_operational_payload,
    derive_llm_priority_score,
    detect_signals,
    get_patient_identifier,
    rank_patients_for_llm,
)


ROOT_DIR = Path(__file__).resolve().parents[2]
AGENTIC_PRIORITY_CACHE_PATH = ROOT_DIR / "data" / "processed" / "agentic_priority_cache.json"
_AGENTIC_PRIORITY_CACHE_LOCK = Lock()
_AGENTIC_PRIORITY_CACHE_DATA: dict[str, Any] | None = None
AGENTIC_PRIORITY_WORKFLOW_VERSION = (
    os.getenv("AGENTIC_PRIORITY_WORKFLOW_VERSION", "llm_priority_queue_v1").strip()
    or "llm_priority_queue_v1"
)


def _normalize_text(value: Any) -> str:
    return str(value or "").strip().lower()


def _max_retries() -> int:
    try:
        return max(0, int(os.getenv("AGENTIC_MAX_RETRIES", "2")))
    except ValueError:
        return 2


def _patient_id(patient: Mapping[str, Any]) -> str:
    return str(
        patient.get("patientId")
        or patient.get("patient_id")
        or patient.get("Patient_ID")
        or patient.get("Patient ID")
        or ""
    ).strip()


def _source_hash(patient: Mapping[str, Any]) -> str:
    return make_source_hash(dict(patient), workflow_version=AGENTIC_PRIORITY_WORKFLOW_VERSION)


def _confidence(payload: Mapping[str, Any]) -> float:
    try:
        return round(max(0.0, min(1.0, float(payload.get("confidence", 0.0)))), 3)
    except (TypeError, ValueError):
        return 0.0


def _load_priority_cache() -> dict[str, Any]:
    global _AGENTIC_PRIORITY_CACHE_DATA

    if _AGENTIC_PRIORITY_CACHE_DATA is None:
        if AGENTIC_PRIORITY_CACHE_PATH.exists():
            try:
                _AGENTIC_PRIORITY_CACHE_DATA = json.loads(
                    AGENTIC_PRIORITY_CACHE_PATH.read_text(encoding="utf-8")
                )
            except json.JSONDecodeError:
                _AGENTIC_PRIORITY_CACHE_DATA = {}
        else:
            _AGENTIC_PRIORITY_CACHE_DATA = {}

    return _AGENTIC_PRIORITY_CACHE_DATA


def _save_priority_cache(cache_data: Mapping[str, Any]) -> None:
    AGENTIC_PRIORITY_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    AGENTIC_PRIORITY_CACHE_PATH.write_text(
        json.dumps(dict(cache_data), ensure_ascii=True, indent=2),
        encoding="utf-8",
    )


def _get_cached_priority_from_file(patient: Mapping[str, Any]) -> dict[str, Any] | None:
    patient_id = _patient_id(patient)
    if not patient_id:
        return None

    entry = _load_priority_cache().get(patient_id)
    if not isinstance(entry, Mapping):
        return None

    if entry.get("source_hash") != _source_hash(patient):
        return None

    payload = entry.get("payload")
    return dict(payload) if isinstance(payload, Mapping) else None


def _save_cached_priority_to_file(patient: Mapping[str, Any], payload: Mapping[str, Any]) -> None:
    patient_id = _patient_id(patient)
    if not patient_id:
        return

    with _AGENTIC_PRIORITY_CACHE_LOCK:
        cache_data = _load_priority_cache()
        cache_data[patient_id] = {
            "source_hash": _source_hash(patient),
            "payload": dict(payload),
        }
        _save_priority_cache(cache_data)


def _get_cached_priority_result(patient: Mapping[str, Any]) -> dict[str, Any] | None:
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

    return _get_cached_priority_from_file(patient)


def _save_cached_priority_result(patient: Mapping[str, Any], payload: Mapping[str, Any]) -> None:
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

    _save_cached_priority_to_file(patient, payload)


def _build_priority_context(patient: Mapping[str, Any]) -> dict[str, Any]:
    signals = detect_signals(patient)
    baseline_operational = build_rule_based_operational_payload(patient, signals)
    priority_profile = derive_llm_priority_score(
        patient,
        base_payload=baseline_operational,
        signals=signals,
    )
    return {
        "patient": dict(patient),
        "baseline_operational": baseline_operational,
        "priority_profile": priority_profile,
    }


def _select_priority_contexts(
    patients: list[Mapping[str, Any]],
    limit: int,
) -> list[dict[str, Any]]:
    if limit <= 0:
        return []

    patient_map = {
        _normalize_text(get_patient_identifier(patient)): patient
        for patient in patients
        if get_patient_identifier(patient)
    }
    ranked = rank_patients_for_llm(patients, limit=limit)
    contexts = []

    for item in ranked:
        patient = patient_map.get(_normalize_text(item.get("patientId")))
        if patient:
            contexts.append(_build_priority_context(patient))

    return contexts


def _validation_payload(
    patient: Mapping[str, Any],
    adjusted_assessment: Mapping[str, Any],
    safety_validation: Mapping[str, Any],
    provider: str,
    model_name: str,
    stage_result: Mapping[str, Any],
    stage_issues: list[str],
    force_needs_review: bool = False,
) -> dict[str, Any]:
    validation_status = (
        "Needs Review" if stage_result.get("used_fallback") or force_needs_review else "Validated"
    )
    return {
        "workflow_version": AGENTIC_PRIORITY_WORKFLOW_VERSION,
        "provider": provider,
        "model_name": model_name,
        "priority_assessment": dict(adjusted_assessment),
        "safety_validation": dict(safety_validation),
        "pipeline_confidence": _confidence(adjusted_assessment),
        "validation_status": validation_status,
        "issues": list(stage_issues),
        "stage_results": {
            "llm_priority_queue": {
                "attempts": stage_result.get("attempts", 0),
                "used_fallback": bool(stage_result.get("used_fallback")),
                "issues": list(stage_result.get("issues", [])),
            }
        },
        "patient_summary": {
            "patientId": _patient_id(patient),
            "patientName": patient.get("patientName"),
            "department": patient.get("department"),
        },
    }


def _serialize_priority_item(
    patient: Mapping[str, Any],
    result: Mapping[str, Any],
    used_cache: bool,
) -> dict[str, Any]:
    assessment = result.get("priority_assessment", {})
    return {
        "patientId": _patient_id(patient),
        "name": patient.get("patientName") or "Unknown patient",
        "department": patient.get("department") or "Unknown",
        "urgencyLevel": assessment.get("urgencyLevel"),
        "priorityScore": int(assessment.get("priorityScore") or 0),
        "reason": assessment.get("reason") or "",
        "suggestedAction": assessment.get("suggestedAction") or DEFAULT_PRIORITY_ACTIONS["Medium"],
        "confidence": _confidence(assessment),
        "validationStatus": result.get("validation_status"),
        "usedCache": used_cache,
    }


def run_agentic_priority_queue(
    patients: list[Mapping[str, Any]],
    limit: int,
    use_cache: bool = True,
    force_refresh: bool = False,
) -> dict[str, Any]:
    shortlist = _select_priority_contexts(patients, limit=max(0, int(limit)))
    provider = get_agentic_provider_name()
    model_name = get_agentic_model_name(provider)
    issues: list[str] = []
    used_cache_count = 0
    result_map: dict[str, dict[str, Any]] = {}
    cache_map: dict[str, bool] = {}
    pending_contexts: list[dict[str, Any]] = []

    for context in shortlist:
        patient = context["patient"]
        patient_id = _normalize_text(_patient_id(patient))
        cached = None if force_refresh else (_get_cached_priority_result(patient) if use_cache else None)
        if cached:
            result_map[patient_id] = cached
            cache_map[patient_id] = True
            used_cache_count += 1
        else:
            pending_contexts.append(context)

    llm_stage = None
    response_by_id: dict[str, dict[str, Any]] = {}

    if pending_contexts:
        llm_stage = run_stage_with_retries(
            stage_name="llm_priority_queue",
            stage_func=lambda: llm_priority_queue_agent(pending_contexts),
            validator_func=validate_llm_priority_queue,
            fallback_func=lambda: fallback_priority_queue_assessment(pending_contexts),
            max_retries=_max_retries(),
        )

        response_items = llm_stage.get("data", {}).get("prioritizedPatients", [])
        response_by_id = {
            _normalize_text(item.get("patientId")): dict(item)
            for item in response_items
            if item.get("patientId")
        }

        expected_ids = {_normalize_text(_patient_id(context["patient"])) for context in pending_contexts}
        extra_ids = sorted(item_id for item_id in response_by_id if item_id not in expected_ids)
        for extra_id in extra_ids:
            issues.append(f"llm_priority_queue: Ignored unexpected patientId in response: {extra_id}")

        for context in pending_contexts:
            patient = context["patient"]
            patient_id = _normalize_text(_patient_id(patient))
            baseline_operational = context["baseline_operational"]
            priority_profile = context["priority_profile"]
            raw_item = response_by_id.get(patient_id)
            stage_issues = [f"llm_priority_queue: {issue}" for issue in llm_stage.get("issues", [])]

            if raw_item is None:
                raw_item = fallback_priority_assessment(
                    patient,
                    baseline_operational=baseline_operational,
                    priority_profile=priority_profile,
                )
                stage_issues.append("llm_priority_queue: Missing patient in LLM response. Rule-based fallback item used.")
                force_needs_review = True
            else:
                force_needs_review = False

            adjusted_item, safety_validation, safety_issues = apply_priority_safety_validation(
                raw_item,
                patient,
                baseline_operational=baseline_operational,
            )
            stage_issues.extend(safety_issues)

            result = _validation_payload(
                patient,
                adjusted_item,
                safety_validation,
                provider=provider,
                model_name=model_name,
                stage_result=llm_stage,
                stage_issues=stage_issues,
                force_needs_review=force_needs_review,
            )

            result_map[patient_id] = result
            cache_map[patient_id] = False
            issues.extend(stage_issues)

            if result["validation_status"] == "Validated":
                _save_cached_priority_result(patient, result)

    prioritized_patients = []

    for context in shortlist:
        patient = context["patient"]
        patient_id = _normalize_text(_patient_id(patient))
        result = result_map.get(patient_id)
        if not result:
            adjusted_item, safety_validation, safety_issues = apply_priority_safety_validation(
                fallback_priority_assessment(
                    patient,
                    baseline_operational=context["baseline_operational"],
                    priority_profile=context["priority_profile"],
                ),
                patient,
                baseline_operational=context["baseline_operational"],
            )
            result = _validation_payload(
                patient,
                adjusted_item,
                safety_validation,
                provider=provider,
                model_name=model_name,
                stage_result={"attempts": 0, "used_fallback": True, "issues": []},
                stage_issues=safety_issues,
            )
            result_map[patient_id] = result
            cache_map[patient_id] = False

        prioritized_patients.append(
            _serialize_priority_item(
                patient,
                result,
                used_cache=cache_map.get(patient_id, False),
            )
        )

    ranked_patients = assign_priority_ranks(sort_prioritized_patients(prioritized_patients))

    return {
        "workflow_version": AGENTIC_PRIORITY_WORKFLOW_VERSION,
        "provider": provider,
        "model_name": model_name,
        "totalPatients": len(patients),
        "shortlistedCount": len(shortlist),
        "usedCacheCount": used_cache_count,
        "prioritizedPatients": ranked_patients,
        "issues": issues,
        "stage_results": (
            {
                "llm_priority_queue": {
                    "attempts": llm_stage.get("attempts", 0),
                    "used_fallback": bool(llm_stage.get("used_fallback")),
                    "issues": list(llm_stage.get("issues", [])),
                }
            }
            if llm_stage
            else {}
        ),
    }


__all__ = ["AGENTIC_PRIORITY_WORKFLOW_VERSION", "run_agentic_priority_queue"]
