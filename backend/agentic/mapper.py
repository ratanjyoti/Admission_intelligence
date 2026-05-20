from __future__ import annotations

from typing import Any, Mapping


def map_agentic_to_operational(agentic: Mapping[str, Any]) -> dict[str, Any]:
    assessment = agentic.get("llm_assessment", {})
    risk = agentic.get("risk_scores", {})
    summary = agentic.get("operational_summary", {})
    validation_status = agentic.get("validation_status")
    risk_source = "agentic_llm" if validation_status == "Validated" else "fallback_ml_rules"

    return {
        "risk_score": risk.get("composite_risk_score"),
        "risk_category": assessment.get("riskLevel") or risk.get("risk_category"),
        "risk_reasoning": assessment.get("reason") or risk.get("reasoning"),
        "risk_confidence": assessment.get("confidence") or risk.get("confidence"),
        "pipeline_confidence": agentic.get("pipeline_confidence"),
        "readmission_risk": risk.get("readmission_risk"),
        "dropout_risk": risk.get("dropout_risk"),
        "red_flags": assessment.get("keyRiskFactors", []),
        "key_risk_factors": assessment.get("keyRiskFactors", []),
        "missing_data_flags": agentic.get("safety_validation", {}).get("missingDataFlags", []),
        "clinical_summary": summary.get("clinical_summary"),
        "ai_rationale": assessment.get("reason") or summary.get("ai_rationale"),
        "operational_action": assessment.get("suggestedAction") or summary.get("operational_action"),
        "llm_first_assessment": dict(assessment),
        "safety_validation": agentic.get("safety_validation", {}),
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
    final["llm_first_assessment"] = agentic.get("llm_assessment", {})
    final["safety_validation"] = agentic.get("safety_validation", {})

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
