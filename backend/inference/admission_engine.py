import pandas as pd
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]

INPUT_PATH = ROOT_DIR / "data" / "processed" / "patients_with_procedure.csv"
OUTPUT_PATH = ROOT_DIR / "data" / "processed" / "patients_with_admission.csv"


EMERGENCY_STRONG_KEYWORDS = [
    "stroke",
    "seizure",
    "bleeding",
    "retractions",
    "acute renal injury",
    "unconscious",
    "respiratory distress",
]

EMERGENCY_WEAK_KEYWORDS = [
    "emergency",
    "acute",
    "severe",
    "stat",
    "breathlessness",
]

DETERIORATION_KEYWORDS = [
    "deteriorating",
    "worsening",
    "progressive",
    "decline",
    "worse",
]

URGENT_KEYWORDS = [
    "surgery",
    "reconstruction",
    "hernia",
    "swelling",
    "obstruction",
    "transplant",
    "infection",
]

ELECTIVE_KEYWORDS = [
    "follow up",
    "routine",
    "stable",
    "cataract",
    "daycare",
]

STABLE_KEYWORDS = [
    "stable",
    "controlled",
    "well controlled",
    "chronic",
    "follow up",
    "routine",
]


def get_text(row):
    text_parts = [
        row.get("combined_clinical_text", ""),
        row.get("clinicalnotes", ""),
        row.get("vitalremarks", ""),
        row.get("physical_remarks_clean", ""),
    ]

    return " ".join([str(x) for x in text_parts]).lower()


def infer_clinical_state(row):
    text = get_text(row)
    strong_count = count_matches(text, EMERGENCY_STRONG_KEYWORDS)
    weak_count = count_matches(text, EMERGENCY_WEAK_KEYWORDS)

    if strong_count >= 1 or weak_count >= 2:
        return "Emergency"

    if any(keyword in text for keyword in DETERIORATION_KEYWORDS):
        return "Deteriorating"

    if any(keyword in text for keyword in STABLE_KEYWORDS):
        return "Stable Chronic"

    if count_matches(text, URGENT_KEYWORDS) >= 2 or row.get("patient_risk_category") in ["Critical", "High"]:
        return "Monitoring Required"

    return "Stable Chronic"


def count_matches(text, keywords):
    return sum(keyword in text for keyword in keywords)


def infer_admission_type(row):
    text = get_text(row)

    strong_emergency = count_matches(text, EMERGENCY_STRONG_KEYWORDS)
    weak_emergency = count_matches(text, EMERGENCY_WEAK_KEYWORDS)
    urgent_score = count_matches(text, URGENT_KEYWORDS)
    elective_score = count_matches(text, ELECTIVE_KEYWORDS)

    risk = row["patient_risk_category"]
    case_type = str(row.get("case_type", "")).lower()
    procedure = str(row.get("procedure_name", "")).lower()
    clinical_state = infer_clinical_state(row)
    emergency_trigger = strong_emergency >= 1 or weak_emergency >= 2

    # True emergency logic
    if emergency_trigger:
        return (
            "Emergency",
            "Detected active emergency indicators in current clinical text"
        )

    # Surgical cases with explicit procedure should be treated as planned urgent admissions.
    if case_type == "surgical" and procedure not in ["not explicitly mentioned", "not available", ""]:
        return (
            "Urgent",
            "Explicit surgical procedure detected; planned surgical admission is recommended"
        )

    # Stable chronic critical cases can still be planned if no active instability indicators are present.
    if risk == "Critical" and clinical_state == "Stable Chronic":
        return (
            "Elective",
            "High-risk stable condition with planned admission pathway"
        )

    # Urgent surgical / deterioration logic
    if urgent_score >= 2 or clinical_state == "Deteriorating":
        return (
            "Urgent",
            "Detected surgical or deterioration indicators requiring near-term admission"
        )

    # Stable medium/high-risk
    if risk in ["High", "Medium"] and elective_score >= 1:
        return (
            "Elective",
            "Condition appears stable and suitable for planned admission"
        )

    if risk == "Critical":
        return (
            "Urgent",
            "High-risk chronic condition requiring monitored admission"
        )

    return (
        "Elective",
        "No active emergency indicators detected"
    )


def infer_bed_type(row):
    risk = row["patient_risk_category"]
    admission_type = row["admission_type"]

    text = get_text(row)

    if (
        admission_type == "Emergency"
        and (
            "breathlessness" in text
            or "retractions" in text
            or "stroke" in text
            or "seizure" in text
        )
    ):
        return "ICU"

    if risk == "Critical":
        return "HDU"

    if "cataract" in text or "daycare" in text:
        return "Daycare Bay"

    return "General"


def generate_admission_reasoning(row):
    return (
        f"Admission categorized as {row['admission_type']} because "
        f"{row['admission_reasoning']}. "
        f"Recommended bed type: {row['bed_type_required']}."
    )


def build_admission_features():
    df = pd.read_csv(INPUT_PATH)

    admission_results = df.apply(
        infer_admission_type,
        axis=1
    )

    df["admission_type"] = admission_results.apply(lambda x: x[0])
    df["admission_reasoning"] = admission_results.apply(lambda x: x[1])
    df["clinical_state"] = df.apply(infer_clinical_state, axis=1)
    df["clinical_stability_state"] = df["clinical_state"]

    df["bed_type_required"] = df.apply(
        infer_bed_type,
        axis=1
    )

    df["admission_summary"] = df.apply(
        generate_admission_reasoning,
        axis=1
    )

    df.to_csv(OUTPUT_PATH, index=False)

    print("\nImproved admission engine completed.")
    print(f"Saved at: {OUTPUT_PATH}")

    print("\nAdmission Type Distribution:")
    print(df["admission_type"].value_counts())

    print("\nBed Type Distribution:")
    print(df["bed_type_required"].value_counts())

    print("\nSample admission output:")
    cols = [
        "Patient_ID",
        "patient_risk_category",
        "admission_type",
        "bed_type_required",
        "admission_reasoning",
        "admission_summary",
    ]

    print(df[cols].head(15).to_string())


if __name__ == "__main__":
    build_admission_features()