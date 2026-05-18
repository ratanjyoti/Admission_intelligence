from typing import Optional

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from pydantic import BaseModel, Field

from backend.data_service import (
    build_charts,
    build_summary,
    find_patient_by_id,
    get_llm_priority_limit,
    get_llm_priority_snapshot,
    is_llm_priority_patient,
    load_live_patients,
    load_patients,
    load_raw_patients,
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
from backend.operational_intelligence import enrich_patient_record
from backend.prescription_extraction import extract_prescription_payload, pdf_extraction_enabled
from backend import models


try:
    if database_enabled():
        Base.metadata.create_all(bind=engine)
except Exception:
    pass


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
    }


@app.get("/api/health")
def api_health_check():
    ml_metadata = load_metadata() if ml_models_ready() else {}
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
    }


@app.get("/api/patients")
def get_patients():
    return load_patients()


@app.get("/api/patients/{patient_id}")
def get_patient(patient_id: str):
    patient = find_patient_by_id(patient_id)

    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    llm_allowed = is_llm_priority_patient(patient)
    return enrich_patient_record(
        patient,
        llm_allowed=llm_allowed,
        allow_live_llm=llm_allowed,
        include_predictive_modeling=True,
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
