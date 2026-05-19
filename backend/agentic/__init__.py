"""Agentic backend package for staged hospital admission intelligence."""

from .gemini_client import call_gemini_json, gemini_feature_enabled
from .mapper import map_agentic_to_operational, safe_merge_agentic_into_operational
from .nodes import (
    clinical_analyst_agent,
    operational_summarizer_agent,
    pathway_planner_agent,
    risk_scorer_agent,
)
from .orchestrator import AGENTIC_WORKFLOW_VERSION, run_agentic_patient_pipeline
from .prompts import (
    build_clinical_analyst_prompt,
    build_operational_summarizer_prompt,
    build_pathway_planner_prompt,
    build_risk_scorer_prompt,
)
from .validator import (
    validate_clinical_analysis,
    validate_operational_summary,
    validate_pathway_plan,
    validate_risk_scores,
)

__all__ = [
    "AGENTIC_WORKFLOW_VERSION",
    "build_clinical_analyst_prompt",
    "build_risk_scorer_prompt",
    "build_pathway_planner_prompt",
    "build_operational_summarizer_prompt",
    "call_gemini_json",
    "gemini_feature_enabled",
    "clinical_analyst_agent",
    "risk_scorer_agent",
    "pathway_planner_agent",
    "operational_summarizer_agent",
    "run_agentic_patient_pipeline",
    "map_agentic_to_operational",
    "safe_merge_agentic_into_operational",
    "validate_clinical_analysis",
    "validate_risk_scores",
    "validate_pathway_plan",
    "validate_operational_summary",
]
