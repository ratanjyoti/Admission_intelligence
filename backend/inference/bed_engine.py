import pandas as pd
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]

INPUT_PATH = ROOT_DIR / "data" / "processed" / "patients_with_admission.csv"
OUTPUT_PATH = ROOT_DIR / "data" / "processed" / "patients_with_bed_logic.csv"


STRICT_ICU_KEYWORDS = [
    "ventilator",
    "unconscious",
    "seizure",
    "stroke",
    "severe respiratory distress",
    "retractions",
    "chest ae reduced",
]

HDU_KEYWORDS = [
    "cpap",
    "heart block",
    "post lrrt",
    "transplant",
    "acute renal injury",
    "infection",
]

DAYCARE_KEYWORDS = [
    "cataract",
    "daycare",
    "infusion",
]

SURGERY_KEYWORDS = [
    "abdominal wall reconstruction",
    "hernia",
    "laparotomy",
    "appendectomy",
    "reconstruction",
]


def get_text(row):
    parts = [
        row.get("combined_clinical_text", ""),
        row.get("Department", ""),
        row.get("procedure_name", ""),
        row.get("clinicalnotes", ""),
        row.get("vitalremarks", ""),
        row.get("physical_remarks_clean", ""),
    ]

    return " ".join([str(x) for x in parts]).lower()


def contains_any(text, keywords):
    return any(keyword in text for keyword in keywords)


def assign_bed_type(row):
    text = get_text(row)

    department = str(row.get("Department", "")).lower()
    admission_type = str(row.get("admission_type", "")).lower()
    risk_category = str(row.get("patient_risk_category", "")).lower()

    has_icu_signal = contains_any(text, STRICT_ICU_KEYWORDS)
    has_hdu_signal = contains_any(text, HDU_KEYWORDS)
    has_daycare_signal = contains_any(text, DAYCARE_KEYWORDS)
    has_surgery_signal = contains_any(text, SURGERY_KEYWORDS)

    # 1. ICU/HDU for emergency high-risk cases even when classic ICU flags are absent
    if admission_type == "emergency" and risk_category == "critical":
        return (
            "ICU",
            "Critical emergency requiring highest acuity bed"
        )

    if admission_type == "emergency" and risk_category == "high":
        return (
            "HDU",
            "High-risk emergency requiring monitored high-dependency care"
        )

    # 2. ICU only for true instability
    if has_icu_signal and admission_type == "emergency":
        return (
            "ICU",
            "Emergency case with true instability indicators"
        )

    # 3. HDU for emergency cases of moderate to high risk
    if admission_type == "emergency" and risk_category in ["high", "medium"]:
        return (
            "HDU",
            "Emergency admission requiring monitored high-dependency care"
        )

    # 4. HDU for emergency/urgent monitored cases
    if has_hdu_signal and admission_type in ["emergency", "urgent"]:
        return (
            "HDU",
            "High-risk condition requiring monitored care"
        )

    # 3. Daycare only if stable
    if has_daycare_signal and risk_category in ["low", "medium"] and admission_type == "elective":
        return (
            "Daycare Bay",
            "Stable short-duration daycare pathway"
        )

    # 4. Oncology ward
    if "oncology" in department or "onco" in department:
        return (
            "General Oncology Ward",
            "Specialty oncology care pathway"
        )

    # 5. Surgical ward
    if has_surgery_signal:
        return (
            "Post-Surgical General Ward",
            "Surgical pathway requiring inpatient recovery planning"
        )

    # 6. HDU fallback for critical but non-emergency
    if risk_category == "critical" and admission_type != "elective":
        return (
            "HDU",
            "Critical risk patient requiring monitored non-ICU care"
        )

    # 7. Default
    return (
        "General Ward",
        "Stable admission suitable for standard inpatient care"
    )


def generate_operational_note(row):
    return (
        f"Recommended bed allocation: {row['smart_bed_type']}. "
        f"Reason: {row['bed_reasoning']}."
    )


def build_bed_features():
    df = pd.read_csv(INPUT_PATH)

    bed_results = df.apply(assign_bed_type, axis=1)

    df["smart_bed_type"] = bed_results.apply(lambda x: x[0])
    df["bed_reasoning"] = bed_results.apply(lambda x: x[1])

    df["operational_bed_summary"] = df.apply(
        generate_operational_note,
        axis=1
    )

    df.to_csv(OUTPUT_PATH, index=False)

    print("\nImproved smart bed allocation engine completed.")
    print(f"Saved at: {OUTPUT_PATH}")

    print("\nSmart Bed Distribution:")
    print(df["smart_bed_type"].value_counts())

    print("\nSample smart bed output:")
    cols = [
        "Patient_ID",
        "Department",
        "patient_risk_category",
        "admission_type",
        "smart_bed_type",
        "bed_reasoning",
    ]

    print(df[cols].head(15).to_string())


if __name__ == "__main__":
    build_bed_features()