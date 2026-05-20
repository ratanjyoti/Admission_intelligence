import os
from importlib.util import find_spec
from typing import Any, Optional

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from pydantic import BaseModel, Field

from backend.data_service import (
    build_charts,
    build_summary,
    clear_patient_caches,
    find_patient_by_id,
    get_llm_priority_limit,
    get_llm_priority_snapshot,
    load_live_patients,
    load_patients,
    load_raw_patients,
)
from backend.agentic.orchestrator import (
    AGENTIC_WORKFLOW_VERSION,
    get_cached_agentic_patient_pipeline,
    run_agentic_patient_pipeline,
)
from backend.agentic.prioritizer import (
    AGENTIC_PRIORITY_WORKFLOW_VERSION,
    run_agentic_priority_queue,
)
from backend.database import Base, database_connected, database_enabled, engine
from backend.llm_intelligence import (
    cache_backend,
    get_model_name,
    get_provider_name,
    llm_feature_enabled,
)
from backend.ml_predictor import (
    load_metadata,
    ml_feature_enabled,
    ml_models_ready,
    predict_new_patient,
)
from backend.operational_intelligence import (
    build_rule_based_operational_payload,
    enrich_patient_record,
    get_patient_identifier,
)
from backend.prescription_extraction import extract_prescription_payload, pdf_extraction_enabled
from backend.revenue_llm import explain_revenue_payload
from backend.revenue_knowledge import get_reference_data_status
from backend.official_reference_sync import get_sync_status, sync_reference_data
from backend import models


try:
    if database_enabled():
        Base.metadata.create_all(bind=engine)
except Exception:
    pass


MULTIPART_AVAILABLE = find_spec("multipart") is not None


app = FastAPI(
    title="Docstribe API",
    version="1.0.0",
    description="FastAPI backend for the Docstribe hospital intelligence dashboard.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)


@app.on_event("startup")
def prewarm_dashboard_cache():
    should_sync_reference = os.getenv("AUTO_SYNC_OFFICIAL_REFERENCE", "true").strip().lower() == "true"
    if should_sync_reference:
        try:
            sync_reference_data(force=False)
        except Exception:
            # Keep startup resilient even if PDF parsing dependencies are unavailable.
            pass

    should_prewarm = os.getenv("PREWARM_PATIENT_CACHE", "true").strip().lower() == "true"
    if not should_prewarm:
        return

    try:
        load_patients()
    except Exception:
        # Keep startup resilient; slow-path cache warmup should never block API availability.
        pass


class IntakePatientPayload(BaseModel):
    patientId: Optional[str] = None
    patientName: str = Field(default="Incoming patient", min_length=1)
    department: str = Field(default="General Medicine", min_length=1)
    doctorName: str = Field(default="Triage desk", min_length=1)
    customerType: str = "Incoming"
    diagnosis: str = ""
    clinicalNotes: str = ""
    physicalRemarks: str = ""
    vitalRemarks: str = ""
    investigations: str = ""
    doctorAdvice: str = ""
    medicineDetails: str = ""
    explicitProcedure: str = ""
    repeatVisit: bool = False
    visitCount: int = Field(default=1, ge=1, le=20)
    firstVisitDate: Optional[str] = None
    firstVisitRiskScore: float = Field(default=0.0, ge=0.0, le=10.0)


class AgenticAnalyzePayload(BaseModel):
    patientId: Optional[str] = None
    patient: Optional[dict[str, Any]] = None
    useCache: bool = True
    forceRefresh: bool = False


class AgenticPrioritizePayload(BaseModel):
    limit: Optional[int] = Field(default=None, ge=1, le=50)
    patientIds: list[str] = Field(default_factory=list)
    useCache: bool = True
    forceRefresh: bool = False


class RevenueEstimatePayload(BaseModel):
    patient: dict[str, Any]
    useLlm: bool = False
    forceRefresh: bool = False


class ReferenceSyncPayload(BaseModel):
    force: bool = False
    warmCache: bool = True


@app.get("/")
def read_root():
    ml_metadata = load_metadata() if ml_models_ready() else {}
    return {
        "message": "Docstribe API is running",
        "ml_enabled": ml_feature_enabled(),
        "ml_models_ready": ml_models_ready(),
        "ml_model_version": ml_metadata.get("model_version"),
    }


@app.get("/health")
def health_check():
    ml_metadata = load_metadata() if ml_models_ready() else {}
    reference_data_status = get_reference_data_status()
    reference_sync_status = get_sync_status()
    return {
        "status": "ok",
        "patients_loaded": len(load_raw_patients()),
        "llm_enabled": llm_feature_enabled(),
        "llm_provider": get_provider_name(),
        "llm_model": get_model_name(),
        "llm_priority_limit": get_llm_priority_limit(),
        "llm_priority_patients": len(get_llm_priority_snapshot()),
        "cache_backend": cache_backend(),
        "database_connected": database_connected(),
        "ml_enabled": ml_feature_enabled(),
        "ml_models_ready": ml_models_ready(),
        "ml_model_version": ml_metadata.get("model_version"),
        "live_patients_loaded": len(load_live_patients()),
        "agentic_risk_enabled": os.getenv("AGENTIC_RISK_ENABLED", "false").lower() == "true",
        "agentic_provider": os.getenv("AGENTIC_PROVIDER", "groq"),
        "agentic_model": os.getenv("AGENTIC_MODEL", "llama-3.3-70b-versatile"),
        "agentic_workflow_version": os.getenv("AGENTIC_WORKFLOW_VERSION", AGENTIC_WORKFLOW_VERSION),
        "agentic_priority_workflow_version": os.getenv(
            "AGENTIC_PRIORITY_WORKFLOW_VERSION",
            AGENTIC_PRIORITY_WORKFLOW_VERSION,
        ),
        "multipart_available": MULTIPART_AVAILABLE,
        "reference_data": reference_data_status,
        "reference_sync": reference_sync_status,
    }


@app.get("/api/health")
def api_health_check():
    ml_metadata = load_metadata() if ml_models_ready() else {}
    reference_data_status = get_reference_data_status()
    reference_sync_status = get_sync_status()
    return {
        "status": "ok",
        "patients_loaded": len(load_raw_patients()),
        "llm_enabled": llm_feature_enabled(),
        "llm_provider": get_provider_name(),
        "llm_model": get_model_name(),
        "llm_priority_limit": get_llm_priority_limit(),
        "llm_priority_patients": len(get_llm_priority_snapshot()),
        "cache_backend": cache_backend(),
        "database_connected": database_connected(),
        "ml_enabled": ml_feature_enabled(),
        "ml_models_ready": ml_models_ready(),
        "ml_model_version": ml_metadata.get("model_version"),
        "live_patients_loaded": len(load_live_patients()),
        "agentic_risk_enabled": os.getenv("AGENTIC_RISK_ENABLED", "false").lower() == "true",
        "agentic_provider": os.getenv("AGENTIC_PROVIDER", "groq"),
        "agentic_model": os.getenv("AGENTIC_MODEL", "llama-3.3-70b-versatile"),
        "agentic_workflow_version": os.getenv("AGENTIC_WORKFLOW_VERSION", AGENTIC_WORKFLOW_VERSION),
        "agentic_priority_workflow_version": os.getenv(
            "AGENTIC_PRIORITY_WORKFLOW_VERSION",
            AGENTIC_PRIORITY_WORKFLOW_VERSION,
        ),
        "multipart_available": MULTIPART_AVAILABLE,
        "reference_data": reference_data_status,
        "reference_sync": reference_sync_status,
    }


@app.get("/api/patients")
def get_patients():
    return load_patients()


@app.get("/api/patients/{patient_id}")
def get_patient(patient_id: str):
    patient = find_patient_by_id(patient_id)

    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    return enrich_patient_record(
        patient,
        llm_allowed=False,
        allow_live_llm=False,
        include_predictive_modeling=True,
        include_cached_agentic=True,
        allow_live_agentic=False,
    )


@app.get("/api/dashboard/summary")
def get_dashboard_summary():
    return build_summary()


@app.get("/api/dashboard/charts")
def get_dashboard_charts():
    return build_charts()


@app.post("/api/predict/patient")
def predict_patient(payload: IntakePatientPayload):
    return predict_new_patient(payload.model_dump(), persist=False)


@app.post("/api/patients/intake")
def create_intake_patient(payload: IntakePatientPayload):
    return predict_new_patient(payload.model_dump(), persist=True)


@app.post("/api/agentic/analyze")
def analyze_agentic_patient(payload: AgenticAnalyzePayload):
    patient = None

    if payload.patientId:
        patient = find_patient_by_id(payload.patientId)
        if patient is None:
            raise HTTPException(status_code=404, detail="Patient not found")

    if patient is None:
        patient = payload.patient

    if patient is None:
        raise HTTPException(
            status_code=400,
            detail="Provide either `patientId` for an existing patient or a `patient` object to analyze.",
        )

    patient_id = get_patient_identifier(patient) or payload.patientId or "unknown"
    use_cache = payload.useCache and not payload.forceRefresh
    cached_analysis = get_cached_agentic_patient_pipeline(patient) if use_cache else None
    used_cache = cached_analysis is not None

    analysis = cached_analysis
    if analysis is None:
        baseline_operational = build_rule_based_operational_payload(patient)
        analysis = run_agentic_patient_pipeline(
            patient,
            baseline_operational=baseline_operational,
            use_cache=use_cache,
            save_cache=True,
        )

    enriched_patient = enrich_patient_record(
        patient,
        llm_allowed=False,
        allow_live_llm=False,
        include_predictive_modeling=True,
        include_cached_agentic=True,
        allow_live_agentic=False,
    )

    return {
        "patientId": patient_id,
        "usedCache": used_cache,
        "analysis": analysis,
        "patient": enriched_patient,
    }


@app.post("/api/revenue/estimate")
def estimate_revenue(payload: RevenueEstimatePayload):
    operational = build_rule_based_operational_payload(payload.patient)
    revenue_payload = operational.get("packageIntelligence", {})
    output = {
        "patient": payload.patient,
        "revenueEstimate": revenue_payload,
        "operational": operational,
    }

    if payload.useLlm:
        try:
            explanation = explain_revenue_payload(payload.patient, revenue_payload)
            output["revenueExplanation"] = explanation
        except Exception as exc:
            output["revenueExplanationError"] = str(exc)

    return output


@app.post("/api/reference/sync")
def sync_reference_data_from_official_sources(payload: ReferenceSyncPayload):
    status = sync_reference_data(force=payload.force)

    if status.get("status") == "failed":
        raise HTTPException(status_code=500, detail=status)

    clear_patient_caches()
    if payload.warmCache:
        try:
            load_patients()
        except Exception:
            pass

    return {
        "referenceSync": status,
        "referenceData": get_reference_data_status(),
    }


@app.post("/api/agentic/prioritize")
def prioritize_agentic_patients(payload: AgenticPrioritizePayload):
    selected_patients: list[dict[str, Any]]

    if payload.patientIds:
        selected_patients = []
        missing_patient_ids = []
        for patient_id in payload.patientIds:
            patient = find_patient_by_id(patient_id)
            if patient:
                selected_patients.append(patient)
            else:
                missing_patient_ids.append(patient_id)

        if missing_patient_ids:
            raise HTTPException(
                status_code=404,
                detail=f"Patients not found: {', '.join(missing_patient_ids)}",
            )
    else:
        selected_patients = list(load_raw_patients())

    if payload.patientIds and payload.limit is None:
        limit = len(selected_patients)
    else:
        limit = payload.limit or get_llm_priority_limit()

    return run_agentic_priority_queue(
        patients=selected_patients,
        limit=limit,
        use_cache=payload.useCache,
        force_refresh=payload.forceRefresh,
    )


if MULTIPART_AVAILABLE:
    @app.post("/api/prescription/extract")
    async def extract_prescription(file: UploadFile = File(...)):
        if not pdf_extraction_enabled():
            raise HTTPException(
                status_code=503,
                detail="Prescription PDF extraction is unavailable because PyMuPDF is not installed on the backend.",
            )

        if not file.filename or not file.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail="Please upload a PDF prescription file.")

        file_bytes = await file.read()

        if len(file_bytes) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="PDF is too large. Please upload a file smaller than 10 MB.")

        try:
            return extract_prescription_payload(file_bytes, filename=file.filename)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:  # pragma: no cover - defensive API guard
            raise HTTPException(
                status_code=500,
                detail=f"Prescription extraction failed: {exc}",
            ) from exc
else:
    @app.post("/api/prescription/extract")
    async def extract_prescription_unavailable():
        raise HTTPException(
            status_code=503,
            detail='Prescription PDF extraction is unavailable because "python-multipart" is not installed on the backend.',
        )
