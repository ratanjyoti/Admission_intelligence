from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from backend.data_service import build_charts, build_summary, find_patient_by_id, load_patients


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


@app.get("/")
def read_root():
    return {"message": "Docstribe API is running"}


@app.get("/health")
def health_check():
    return {"status": "ok", "patients_loaded": len(load_patients())}


@app.get("/api/health")
def api_health_check():
    return {"status": "ok", "patients_loaded": len(load_patients())}


@app.get("/api/patients")
def get_patients():
    return load_patients()


@app.get("/api/patients/{patient_id}")
def get_patient(patient_id: str):
    patient = find_patient_by_id(patient_id)

    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    return patient


@app.get("/api/dashboard/summary")
def get_dashboard_summary():
    return build_summary()


@app.get("/api/dashboard/charts")
def get_dashboard_charts():
    return build_charts()
