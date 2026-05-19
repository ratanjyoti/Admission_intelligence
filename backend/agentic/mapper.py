from __future__ import annotations

from typing import Any, Mapping


def map_agentic_to_operational(agentic: Mapping[str, Any]) -> dict[str, Any]:
    risk = agentic.get("risk_scores", {})
    pathway = agentic.get("pathway_plan", {})
    summary = agentic.get("operational_summary", {})
    clinical = agentic.get("clinical_analysis", {})
    validation_status = agentic.get("validation_status")
    risk_source = "agentic_llm" if validation_status == "Validated" else "fallback_ml_rules"

    return {
        "risk_score": risk.get("composite_risk_score"),
        "risk_category": risk.get("risk_category"),
        "risk_reasoning": risk.get("reasoning"),
        "risk_confidence": risk.get("confidence"),
        "pipeline_confidence": agentic.get("pipeline_confidence"),
        "readmission_risk": risk.get("readmission_risk"),
        "dropout_risk": risk.get("dropout_risk"),
        "red_flags": clinical.get("red_flags", []),
        "comorbidities": clinical.get("comorbidities", []),
        "possible_symptoms": clinical.get("possible_symptoms", []),
        "missing_data_flags": clinical.get("missing_data_flags", []),
        "admission_type": pathway.get("admission_type"),
        "case_type": pathway.get("case_type"),
        "bed_type_required": pathway.get("bed_type"),
        "deferred_time": pathway.get("deferred_time"),
        "estimated_los": pathway.get("estimated_los_days"),
        "procedure_name": pathway.get("procedure_name"),
        "inferred_procedure_name": pathway.get("inferred_procedure_name"),
        "primary_treatment": pathway.get("primary_treatment"),
        "secondary_treatment": pathway.get("secondary_treatment"),
        "clinical_summary": summary.get("clinical_summary"),
        "icd10_code": summary.get("icd10_code"),
        "icd10_description": summary.get("icd10_description"),
        "clinical_timeline": summary.get("clinical_timeline", []),
        "revenue_estimate": summary.get("revenue_estimate"),
        "revenue_category": summary.get("revenue_category"),
        "ai_rationale": summary.get("ai_rationale"),
        "operational_action": summary.get("operational_action"),
        "validation_status": validation_status,
        "validation_issues": agentic.get("issues", []),
        "agentic_workflow_version": agentic.get("workflow_version"),
        "agentic_provider": agentic.get("provider"),
        "agentic_model": agentic.get("model_name"),
        "agentic_stage_results": agentic.get("stage_results", {}),
        "risk_source": risk_source,
        "agentic_trace": dict(agentic),
    }


def safe_merge_agentic_into_operational(
    baseline: Mapping[str, Any],
    agentic: Mapping[str, Any],
) -> dict[str, Any]:
    final = dict(baseline)

    final["agentic_trace"] = dict(agentic)
    final["agentic_workflow_version"] = agentic.get("workflow_version")
    final["agentic_provider"] = agentic.get("provider")
    final["agentic_model"] = agentic.get("model_name")
    final["agentic_stage_results"] = agentic.get("stage_results", {})
    final["validation_status"] = agentic.get("validation_status")
    final["validation_issues"] = agentic.get("issues", [])

    if agentic.get("validation_status") == "Validated":
        final.update(map_agentic_to_operational(agentic))
        final["risk_source"] = "agentic_llm_validated"
    else:
        final["risk_source"] = "fallback_ml_rules"
        final["agentic_trace"] = dict(agentic)
        final["validation_issues"] = agentic.get("issues", [])
        if agentic.get("issues"):
            final["agentic_error"] = "; ".join(agentic.get("issues", []))

    return final


__all__ = ["map_agentic_to_operational", "safe_merge_agentic_into_operational"]
