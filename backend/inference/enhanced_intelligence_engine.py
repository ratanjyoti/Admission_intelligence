import pandas as pd
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]

INPUT_PATH = ROOT_DIR / "data" / "processed" / "final_patient_profiles.csv"
OUTPUT_PATH = ROOT_DIR / "data" / "processed" / "enhanced_patient_profiles.csv"


def extract_explicit_procedure(row):
    """
    Extract procedure if explicitly mentioned.
    """
    text = str(row.get("combined_clinical_text", "")).lower()

    procedure_keywords = {
        "abdominal wall reconstruction": "Abdominal Wall Reconstruction",
        "hernia repair": "Hernia Repair Surgery",
        "renal transplant": "Renal Transplant",
        "cataract surgery": "Cataract Surgery",
        "laparotomy": "Exploratory Laparotomy",
    }

    for keyword, value in procedure_keywords.items():
        if keyword in text:
            return value

    return "Not Explicitly Mentioned"


def calculate_confidence(row):
    """
    Higher confidence if explicit procedure exists.
    """
    procedure = row["procedure_name"]

    if procedure != "Not Explicitly Mentioned":
        return "90%"

    inferred = row["inferred_procedure_name"]

    if inferred != "Not Explicitly Mentioned":
        return "70%"

    return "50%"


def calculate_priority_score(row):
    score = 0

    risk = row["patient_risk_category"]

    if risk == "Critical":
        score += 5
    elif risk == "High":
        score += 4
    elif risk == "Medium":
        score += 2

    if row["admission_type"] == "Emergency":
        score += 3

    if row["case_type"] == "Surgical":
        score += 2

    if row["readmission_risk"] == "High":
        score += 2

    if row["bed_type_required"] == "ICU":
        score += 2

    return min(score, 10)


def recommend_action(row):
    risk = row["patient_risk_category"]
    case_type = row["case_type"]
    admission_type = row["admission_type"]

    if risk == "Critical":
        return "Immediate clinical escalation and ICU coordination"

    if case_type == "Surgical":
        return "Schedule surgical admission and pre-operative planning"

    if admission_type == "Urgent":
        return "Priority follow-up and admission coordination"

    if case_type == "Daycare":
        return "Schedule daycare procedure"

    return "Routine follow-up and medication management"


def generate_enhanced_summary(row):
    diagnosis = str(row.get("provisionaldiagnosis", ""))
    risk = str(row.get("patient_risk_category", ""))
    department = str(row.get("Department", ""))
    bed = str(row.get("bed_type_required", ""))
    treatment = str(row.get("best_possible_treatment", ""))

    return (
        f"Patient belongs to {department} department with diagnosis/history related to "
        f"{diagnosis}. Current clinical risk is categorized as {risk}. "
        f"Recommended treatment pathway includes {treatment}. "
        f"Operational planning suggests requirement of {bed} level care."
    )


def build_enhanced_profiles():
    df = pd.read_csv(INPUT_PATH)

    # Explicit procedure extraction
    df["procedure_name"] = df.apply(
        extract_explicit_procedure,
        axis=1
    )

    # Confidence score
    df["confidence_score"] = df.apply(
        calculate_confidence,
        axis=1
    )

    # Priority score
    df["priority_score"] = df.apply(
        calculate_priority_score,
        axis=1
    )

    # Recommended action
    df["recommended_action"] = df.apply(
        recommend_action,
        axis=1
    )

    # Better summary
    df["enhanced_clinical_summary"] = df.apply(
        generate_enhanced_summary,
        axis=1
    )

    # Priority labels
    df["priority_label"] = pd.cut(
        df["priority_score"],
        bins=[0, 3, 6, 8, 10],
        labels=[
            "Low Priority",
            "Medium Priority",
            "High Priority",
            "Critical Priority"
        ]
    )

    # Sort by priority
    df = df.sort_values(
        by=["priority_score", "patient_risk_score"],
        ascending=False
    )

    df.to_csv(OUTPUT_PATH, index=False)

    print("\nEnhanced intelligence engine completed.")
    print(f"Saved at: {OUTPUT_PATH}")

    print("\nPriority Distribution:")
    print(df["priority_label"].value_counts())

    print("\nSample Enhanced Output:")
    cols = [
        "Patient_ID",
        "patient_risk_category",
        "priority_score",
        "priority_label",
        "procedure_name",
        "inferred_procedure_name",
        "confidence_score",
        "recommended_action",
    ]

    print(df[cols].head(10).to_string())


if __name__ == "__main__":
    build_enhanced_profiles()