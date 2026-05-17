import json
import pandas as pd
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]

INPUT_PATH = ROOT_DIR / "data" / "processed" / "validated_patient_profiles.csv"
OUTPUT_PATH = ROOT_DIR / "data" / "processed" / "dashboard_patients.json"


def safe_value(value, default=""):
    if pd.isna(value):
        return default
    return value


def build_patient_record(row):
    return {
        "patientId": safe_value(row.get("Patient_ID")),
        "patientName": safe_value(row.get("Patient_Name")),
        "visitDate": str(safe_value(row.get("Visit_Date"))),
        "doctorName": safe_value(row.get("Doctor_Name")),
        "department": safe_value(row.get("Department")),
        "customerType": safe_value(row.get("Customer_Type")),

        "risk": {
            "score": int(safe_value(row.get("patient_risk_score"), 0)),
            "category": safe_value(row.get("patient_risk_category")),
            "reasoning": safe_value(row.get("risk_reasoning")),
            "redFlags": safe_value(row.get("current_red_flags"), "[]"),
        },

        "admission": {
            "type": safe_value(row.get("admission_type")),
            "reasoning": safe_value(row.get("admission_reasoning")),
            "summary": safe_value(row.get("admission_summary")),
        },

        "bed": {
            "type": safe_value(row.get("smart_bed_type")),
            "reasoning": safe_value(row.get("bed_reasoning")),
            "summary": safe_value(row.get("operational_bed_summary")),
        },

        "procedure": {
            "explicitProcedure": safe_value(row.get("procedure_name")),
            "explicitConfidence": int(safe_value(row.get("procedure_confidence"), 0)),
            "explicitSource": safe_value(row.get("procedure_source")),
            "inferredProcedure": safe_value(row.get("inferred_procedure_name")),
            "inferredConfidence": int(safe_value(row.get("inferred_procedure_confidence"), 0)),
            "inferredSource": safe_value(row.get("inferred_procedure_source")),
        },

        "journey": {
            "visitCount": int(safe_value(row.get("visit_count"), 1)),
            "firstVisitDate": str(safe_value(row.get("first_visit_date"))),
            "latestVisitDate": str(safe_value(row.get("latest_visit_date"))),
            "repeatVisit": safe_value(row.get("repeat_visit_flag")),
            "progressionTrend": safe_value(row.get("progression_trend")),
            "timelineSummary": safe_value(row.get("timeline_summary")),
            "riskProgression": safe_value(row.get("risk_progression"), "[]"),
        },

        "traceability": {
            "evidenceCount": int(safe_value(row.get("evidence_count"), 0)),
            "summary": safe_value(row.get("traceability_summary")),
            "safetyNote": safe_value(row.get("clinical_safety_note")),
            "sourceSections": safe_value(row.get("source_sections_used"), "[]"),
            "evidenceTrace": safe_value(row.get("ai_evidence_trace"), "[]"),
        },

        "validation": {
            "status": safe_value(row.get("validation_status")),
            "issueCount": int(safe_value(row.get("consistency_issue_count"), 0)),
            "summary": safe_value(row.get("validation_summary")),
        },

        "clinical": {
            "diagnosis": safe_value(row.get("provisionaldiagnosis")),
            "clinicalNotes": safe_value(row.get("clinicalnotes")),
            "physicalRemarks": safe_value(row.get("physical_remarks_clean")),
            "vitalRemarks": safe_value(row.get("vitalremarks")),
            "investigations": safe_value(row.get("other_investigation_freetext")),
            "doctorAdvice": safe_value(row.get("otheradvice")),
            "medicineDetails": safe_value(row.get("medicinedetails")),
        },
    }


def generate_dashboard_json():
    df = pd.read_csv(INPUT_PATH)

    records = [build_patient_record(row) for _, row in df.iterrows()]

    # Sort by risk score desc, then visit count desc
    records = sorted(
        records,
        key=lambda x: (
            x["risk"]["score"],
            x["journey"]["visitCount"],
            x["traceability"]["evidenceCount"]
        ),
        reverse=True,
    )

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)

    print("\nDashboard JSON generated successfully.")
    print(f"Saved at: {OUTPUT_PATH}")
    print(f"Total patient profiles: {len(records)}")

    print("\nSample patient record:")
    print(json.dumps(records[0], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    generate_dashboard_json()