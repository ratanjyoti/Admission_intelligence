import json
from functools import lru_cache
from pathlib import Path
from urllib.parse import unquote


ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT_DIR / "data" / "processed" / "dashboard_patients.json"

RISK_ORDER = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}
ADMISSION_ORDER = {"Emergency": 0, "Urgent": 1, "Elective": 2}


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
def load_patients():
    with DATA_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def find_patient_by_id(patient_id, patients=None):
    patients = patients or load_patients()
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


def build_summary(patients=None):
    patients = patients or load_patients()

    return {
        "totalPatients": len(patients),
        "criticalPatients": sum(1 for patient in patients if patient.get("risk", {}).get("category") == "Critical"),
        "emergencyPatients": sum(1 for patient in patients if patient.get("admission", {}).get("type") == "Emergency"),
        "icuPatients": sum(1 for patient in patients if patient.get("bed", {}).get("type") == "ICU"),
        "repeatPatients": sum(1 for patient in patients if patient.get("journey", {}).get("repeatVisit") == "Yes"),
        "validatedPatients": sum(1 for patient in patients if patient.get("validation", {}).get("status") == "Validated"),
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
        "departmentMetrics": sorted(
            department_metrics.values(),
            key=lambda item: (-item["totalPatients"], item["department"]),
        ),
    }
