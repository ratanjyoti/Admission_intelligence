import json
import os
from functools import lru_cache
from pathlib import Path
from threading import Lock
from urllib.parse import unquote

from backend.operational_intelligence import (
    enrich_patients,
    get_patient_identifier,
    rank_patients_for_llm,
)
from backend.revenue_knowledge import get_reference_data_signature


ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT_DIR / "data" / "processed" / "dashboard_patients.json"
LIVE_DATA_PATH = ROOT_DIR / "data" / "processed" / "live_intake_patients.json"

RISK_ORDER = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}
ADMISSION_ORDER = {"Emergency": 0, "Urgent": 1, "Elective": 2}
PATIENT_CACHE_LOCK = Lock()


def normalize_text(value):
    return unquote(str(value or "")).strip().lower()


def sort_chart_entries(entries, preset=None):
    preset = preset or {}
    return sorted(
        entries,
        key=lambda item: (
            preset.get(item["name"], 999),
            -item["value"],
            item["name"],
        ),
    )


@lru_cache(maxsize=1)
def load_base_patients():
    with DATA_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


@lru_cache(maxsize=1)
def load_live_patients():
    if not LIVE_DATA_PATH.exists():
        return []

    with LIVE_DATA_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


@lru_cache(maxsize=1)
def load_raw_patients():
    return load_base_patients() + load_live_patients()


@lru_cache(maxsize=8)
def _load_patients_cached(reference_signature):
    return enrich_patients(
        load_raw_patients(),
        allow_live_llm=False,
        include_cached_agentic=False,
        allow_live_agentic=False,
    )


def load_patients():
    reference_signature = get_reference_data_signature()
    with PATIENT_CACHE_LOCK:
        return _load_patients_cached(reference_signature)


def get_llm_priority_limit():
    try:
        return max(0, int(os.getenv("LLM_PRIORITY_LIMIT", "3") or "3"))
    except ValueError:
        return 3


def clear_patient_caches():
    load_base_patients.cache_clear()
    load_live_patients.cache_clear()
    load_raw_patients.cache_clear()
    _load_patients_cached.cache_clear()
    get_llm_priority_snapshot.cache_clear()
    get_llm_priority_patient_id_set.cache_clear()


def save_live_patient(patient):
    existing_patients = list(load_live_patients())
    patient_id = normalize_text(get_patient_identifier(patient))

    replaced = False

    for index, existing_patient in enumerate(existing_patients):
        existing_id = normalize_text(get_patient_identifier(existing_patient))

        if existing_id and existing_id == patient_id:
            existing_patients[index] = patient
            replaced = True
            break

    if not replaced:
        existing_patients.append(patient)

    LIVE_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LIVE_DATA_PATH.open("w", encoding="utf-8") as file:
        json.dump(existing_patients, file, ensure_ascii=False, indent=2)

    clear_patient_caches()
    return patient


@lru_cache(maxsize=1)
def get_llm_priority_snapshot():
    limit = get_llm_priority_limit()

    if limit <= 0:
        return tuple()

    return tuple(rank_patients_for_llm(load_raw_patients(), limit=limit))


@lru_cache(maxsize=1)
def get_llm_priority_patient_id_set():
    return frozenset(
        normalize_text(item.get("patientId"))
        for item in get_llm_priority_snapshot()
        if item.get("patientId")
    )


def get_llm_priority_patients():
    priority_ids = get_llm_priority_patient_id_set()

    if not priority_ids:
        return []

    return [
        patient
        for patient in load_raw_patients()
        if normalize_text(get_patient_identifier(patient)) in priority_ids
    ]


def is_llm_priority_patient(patient_or_id):
    if isinstance(patient_or_id, dict):
        target = get_patient_identifier(patient_or_id)
    else:
        target = patient_or_id

    return normalize_text(target) in get_llm_priority_patient_id_set()


def find_patient_by_id(patient_id, patients=None):
    patients = patients or load_raw_patients()
    target = normalize_text(patient_id)

    if not target:
        return None

    for patient in patients:
        candidates = [
            patient.get("patientId"),
            patient.get("Patient_ID"),
            patient.get("patient_id"),
            patient.get("id"),
        ]
        normalized_candidates = [normalize_text(candidate) for candidate in candidates if candidate]

        if any(
            candidate == target
            or candidate in target
            or target in candidate
            for candidate in normalized_candidates
        ):
            return patient

    return None


def count_by(patients, accessor):
    counts = {}

    for patient in patients:
        key = accessor(patient) or "Unknown"
        counts[key] = counts.get(key, 0) + 1

    return [{"name": name, "value": value} for name, value in counts.items()]


def get_mid_lakhs(patient):
    return float(
        patient.get("operational", {})
        .get("packageIntelligence", {})
        .get("midLakhs")
        or 0
    )

def is_revenue_at_risk(patient):
    operational = patient.get("operational", {})
    package = operational.get("packageIntelligence", {})

    revenue_category = package.get("revenueCategory")
    readmission_risk = operational.get("readmissionRisk", {}).get("label")
    deferred_time = operational.get("deferredTime", {}).get("label")

    risk_category = patient.get("risk", {}).get("category")
    admission_type = patient.get("admission", {}).get("type")
    progression = patient.get("journey", {}).get("progressionTrend")

    is_high_value = revenue_category in {"High Value", "Strategic Value"}

    has_serious_risk_signal = (
        readmission_risk == "High"
        or deferred_time == "Cannot be safely delayed"
        or risk_category in {"High", "Critical"}
        or admission_type in {"Emergency", "Urgent"}
        or progression == "Worsening"
    )

    return is_high_value and has_serious_risk_signal


def build_summary(patients=None):
    patients = patients or load_patients()

    return {
        "totalPatients": len(patients),
        "criticalPatients": sum(1 for patient in patients if patient.get("risk", {}).get("category") == "Critical"),
        "emergencyPatients": sum(1 for patient in patients if patient.get("admission", {}).get("type") == "Emergency"),
        "icuPatients": sum(1 for patient in patients if patient.get("bed", {}).get("type") == "ICU"),
        "repeatPatients": sum(1 for patient in patients if patient.get("journey", {}).get("repeatVisit") == "Yes"),
        "validatedPatients": sum(1 for patient in patients if patient.get("validation", {}).get("status") == "Validated"),
        "highRevenueCases": sum(
            1
            for patient in patients
            if patient.get("operational", {}).get("packageIntelligence", {}).get("revenueCategory")
            in {"High Value", "Strategic Value"}
        ),
        "cannotBeDelayedCases": sum(
            1
            for patient in patients
            if patient.get("operational", {}).get("deferredTime", {}).get("label")
            == "Cannot be safely delayed"
        ),
        "highReadmissionRiskCases": sum(
            1
            for patient in patients
            if patient.get("operational", {}).get("readmissionRisk", {}).get("label") == "High"
        ),
        "worseningPatients": sum(
            1
            for patient in patients
            if patient.get("journey", {}).get("progressionTrend") == "Worsening"
        ),
        "surgicalOpportunities": sum(
            1
            for patient in patients
            if patient.get("operational", {}).get("caseType", {}).get("label") == "Surgical"
        ),
        "renalCohortPatients": sum(
            1
            for patient in patients
            if "Renal" in patient.get("operational", {}).get("clinicalIntelligence", {}).get("diseaseCohorts", [])
        ),
        "oncologyCohortPatients": sum(
            1
            for patient in patients
            if "Oncology" in patient.get("operational", {}).get("clinicalIntelligence", {}).get("diseaseCohorts", [])
        ),
        "cardiacCohortPatients": sum(
            1
            for patient in patients
            if "Cardiac" in patient.get("operational", {}).get("clinicalIntelligence", {}).get("diseaseCohorts", [])
        ),
        "orthopedicCohortPatients": sum(
            1
            for patient in patients
            if "Orthopedic" in patient.get("operational", {}).get("clinicalIntelligence", {}).get("diseaseCohorts", [])
        ),
        "neurologyCohortPatients": sum(
            1
            for patient in patients
            if "Neurology" in patient.get("operational", {}).get("clinicalIntelligence", {}).get("diseaseCohorts", [])
        ),
        "respiratoryCohortPatients": sum(
            1
            for patient in patients
            if "Respiratory" in patient.get("operational", {}).get("clinicalIntelligence", {}).get("diseaseCohorts", [])
        ),
        "totalAddressableRevenueLakhs": round(sum(get_mid_lakhs(patient) for patient in patients), 1),
        "revenueAtRiskLakhs": round(
            sum(
                get_mid_lakhs(patient)
                for patient in patients
                if is_revenue_at_risk(patient)
            ),
            1,
        ),
        "departmentCount": len({patient.get("department") or "Unknown" for patient in patients}),
    }


def build_charts(patients=None):
    patients = patients or load_patients()
    department_metrics = {}

    for patient in patients:
        department = patient.get("department") or "Unknown"

        if department not in department_metrics:
            department_metrics[department] = {
                "department": department,
                "totalPatients": 0,
                "criticalPatients": 0,
                "icuDemand": 0,
                "emergencyAdmissions": 0,
            }

        entry = department_metrics[department]
        entry["totalPatients"] += 1

        if patient.get("risk", {}).get("category") == "Critical":
            entry["criticalPatients"] += 1

        if patient.get("bed", {}).get("type") == "ICU":
            entry["icuDemand"] += 1

        if patient.get("admission", {}).get("type") == "Emergency":
            entry["emergencyAdmissions"] += 1

    return {
        "riskDistribution": sort_chart_entries(
            count_by(patients, lambda patient: patient.get("risk", {}).get("category")),
            RISK_ORDER,
        ),
        "admissionDistribution": sort_chart_entries(
            count_by(patients, lambda patient: patient.get("admission", {}).get("type")),
            ADMISSION_ORDER,
        ),
        "bedDistribution": sorted(
            count_by(patients, lambda patient: patient.get("bed", {}).get("type")),
            key=lambda item: (-item["value"], item["name"]),
        ),
        "cohortDistribution": sorted(
            count_by(
                patients,
                lambda patient: patient.get("operational", {})
                .get("clinicalIntelligence", {})
                .get("primaryCohort"),
            ),
            key=lambda item: (-item["value"], item["name"]),
        ),
        "departmentMetrics": sorted(
            department_metrics.values(),
            key=lambda item: (-item["totalPatients"], item["department"]),
        ),
    }
