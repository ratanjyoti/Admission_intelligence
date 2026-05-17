import pandas as pd
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]

INPUT_PATH = ROOT_DIR / "data" / "processed" / "patients_with_traceability.csv"
OUTPUT_PATH = ROOT_DIR / "data" / "processed" / "validated_patient_profiles.csv"


def get_combined_text(row):
    parts = [
        row.get("combined_clinical_text", ""),
        row.get("clinicalnotes", ""),
        row.get("admission_reasoning", ""),
        row.get("procedure_name", ""),
        row.get("Department", ""),
    ]
    return " ".join([str(x) for x in parts]).lower()


def is_stable_elective_critical(row):
    admission = str(row.get("admission_type", "")).lower()
    risk = str(row.get("patient_risk_category", "")).lower()
    stability = str(row.get("clinical_stability_state", "")).lower()
    progression = str(row.get("progression_trend", "")).lower()
    text = get_combined_text(row)

    stable_terms = ["stable", "controlled", "well controlled", "chronic"]
    has_stable_indicator = any(term in text for term in stable_terms)

    if risk != "critical" or admission != "elective":
        return False

    if progression == "worsening":
        return False

    if stability == "stable" or has_stable_indicator:
        return True

    strong_emergency = sum(term in text for term in ["stroke", "seizure", "bleeding", "retractions"])
    weak_emergency = sum(term in text for term in ["acute", "stat"])

    if strong_emergency >= 1 or weak_emergency >= 2:
        return False

    return True


def has_oncology_infusion_pathway(row):
    text = get_combined_text(row)
    infusion_terms = ["chemotherapy", "chemo", "rituximab", "infusion", "daycare infusion", "short stay", "opd"]
    return any(term in text for term in infusion_terms)


def detect_inconsistencies(row):
    issues = []

    risk = str(row.get("patient_risk_category", "")).lower()
    admission = str(row.get("admission_type", "")).lower()
    bed = str(row.get("smart_bed_type", "")).lower()
    case_type = str(row.get("case_type", row.get("inferred_case_type", ""))).lower()       
    procedure = str(row.get("procedure_name", "")).lower()
    department = str(row.get("Department", "")).lower()

    # 1. Critical but elective
    if risk == "critical" and admission == "elective" and not is_stable_elective_critical(row):
        issues.append(
            "Critical-risk patient marked as elective admission"
        )

    # 2. Low risk but ICU
    if risk == "low" and "icu" in bed:
        issues.append(
            "Low-risk patient allocated ICU bed"
        )

    # 3. Daycare + critical
    if case_type == "daycare" and risk == "critical":
        issues.append(
            "Critical-risk patient assigned daycare pathway"
        )

    # 4. Emergency + General Ward
    if admission == "emergency" and "general ward" in bed:
        issues.append(
            "Emergency patient allocated standard general ward"
        )

    # 5. Surgical but no procedure
    if case_type == "surgical" and (
        procedure == "not explicitly mentioned"
        or procedure == "not available"
    ):
        issues.append(
            "Surgical case without clear procedure identification"
        )

    # 6. Oncology + Daycare
    text = " ".join([
        str(row.get("combined_clinical_text", "")).lower(),
        str(row.get("clinicalnotes", "")).lower(),
        str(row.get("medicinedetails", "")).lower(),
        str(row.get("other_medication_freetext", "")).lower(),
    ])

    oncology_daycare_allowed_terms = [
        "chemotherapy",
        "rituximab",
        "infusion",
        "daycare",
        "chemo",
        "cycle",
    ]

    if (
        ("oncology" in department or "onco" in department)
        and "daycare" in bed
        and not any(
            term in text
            for term in oncology_daycare_allowed_terms
        )
    ):
        issues.append(
            "Oncology patient assigned daycare without explicit infusion pathway"
        )
    return issues


def assign_validation_status(issues):
    if len(issues) == 0:
        return "Validated"

    if len(issues) <= 2:
        return "Needs Review"

    return "High Inconsistency"


def generate_validation_summary(row):
    issues = row["consistency_issues"]

    if not issues:
        return (
            "AI-generated profile passed consistency validation checks."
        )

    return (
        "Potential inconsistency detected: "
        + "; ".join(issues)
    )


def build_validation_layer():
    df = pd.read_csv(INPUT_PATH)

    df["consistency_issues"] = df.apply(
        detect_inconsistencies,
        axis=1
    )

    df["consistency_issue_count"] = df[
        "consistency_issues"
    ].apply(len)

    df["validation_status"] = df[
        "consistency_issues"
    ].apply(assign_validation_status)

    df["validation_summary"] = df.apply(
        generate_validation_summary,
        axis=1
    )

    df.to_csv(OUTPUT_PATH, index=False)

    print("\nConsistency validation engine completed.")
    print(f"Saved at: {OUTPUT_PATH}")

    print("\nValidation Status Distribution:")
    print(df["validation_status"].value_counts())

    print("\nPatients with highest inconsistencies:")

    inconsistent_df = df[
        df["consistency_issue_count"] > 0
    ].sort_values(
        by="consistency_issue_count",
        ascending=False
    )

    cols = [
        "Patient_ID",
        "patient_risk_category",
        "admission_type",
        "smart_bed_type",
        "validation_status",
        "consistency_issue_count",
        "validation_summary",
    ]

    print(inconsistent_df[cols].head(15).to_string())


if __name__ == "__main__":
    build_validation_layer()