# import re
# import pandas as pd
# from pathlib import Path

# ROOT_DIR = Path(__file__).resolve().parents[2]
# PROCESSED_DIR = ROOT_DIR / "data" / "processed"
# CLINICAL_OUTPUT_PATH = PROCESSED_DIR / "clinical_fields.csv"

# SYMPTOM_PATTERNS = [
#     r"chest pain",
#     r"shortness of breath",
#     r"fever",
#     r"abdominal pain",
#     r"weakness",
#     r"dizziness",
#     r"cough",
#     r"vomiting"
# ]

# DIAGNOSIS_PATTERNS = [
#     r"myocardial infarction",
#     r"appendicitis",
#     r"stroke",
#     r"fracture",
#     r"infection",
#     r"hypertension"
# ]


# def extract_tokens(text: str, patterns: list[str]) -> list[str]:
#     values = set()
#     lower = str(text).lower()
#     for pattern in patterns:
#         if re.search(pattern, lower):
#             values.add(pattern)
#     return sorted(values)


# def enrich_clinical_fields(df: pd.DataFrame) -> pd.DataFrame:
#     df = df.copy()
#     df["extracted_symptoms"] = df["clinical_note"].apply(lambda text: ", ".join(extract_tokens(text, SYMPTOM_PATTERNS)))
#     df["extracted_diagnosis"] = df["clinical_note"].apply(lambda text: ", ".join(extract_tokens(text, DIAGNOSIS_PATTERNS)))
#     if "prescription" in df.columns:
#         df["prescription_list"] = df["prescription"].astype(str).str.split(",").apply(lambda items: [item.strip() for item in items if item.strip()])
#     return df


# def extract_fields_from_cleaned():
#     cleaned_path = PROCESSED_DIR / "cleaned_patients.csv"
#     if not cleaned_path.exists():
#         raise FileNotFoundError(f"Cleaned data not found: {cleaned_path}")

#     df = pd.read_csv(cleaned_path)
#     df = enrich_clinical_fields(df)
#     df.to_csv(CLINICAL_OUTPUT_PATH, index=False)
#     print(f"Clinical field extraction complete: {CLINICAL_OUTPUT_PATH}")
#     return df


# if __name__ == "__main__":
#     extract_fields_from_cleaned()


import re
import pandas as pd
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
CLEANED_DATA_PATH = ROOT_DIR / "data" / "processed" / "cleaned_patients.csv"
OUTPUT_PATH = ROOT_DIR / "data" / "processed" / "patients_extracted.csv"


FIELD_NAMES = [
    "Department_Name",
    "otheradvice",
    "followupdatetime",
    "medicinedetails",
    "clinicalnotes",
    "phycicalremarks",
    "physicalremarks",
    "vitalremarks",
    "Other_Investigation_freetext",
    "Prescription_Medicines_fromDropDown",
    "Prescription_Medicine_fromDropDown_with_detail",
    "Other_Medication_freetext",
    "ProvisionalDiagnosis",
    "PAC",
]


def extract_field(text, field_name):
    """
    Extracts value after a field name until the next known field appears.
    """
    if pd.isna(text):
        return ""

    text = str(text)

    # Build pattern for all possible next fields
    next_fields = "|".join([re.escape(f) for f in FIELD_NAMES])

    pattern = rf"{re.escape(field_name)}:\s*(.*?)(?=\s(?:{next_fields}):|$)"

    match = re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)

    if match:
        value = match.group(1).strip()
        value = re.sub(r"\s+", " ", value)
        return value

    return ""


def extract_all_fields():
    df = pd.read_csv(CLEANED_DATA_PATH)

    for field in FIELD_NAMES:
        new_col = field.lower()
        df[new_col] = df["Clinical_Note"].apply(lambda x: extract_field(x, field))

    # Fix physical remarks: combine misspelled and correct version
    df["physical_remarks_clean"] = df["phycicalremarks"].fillna("")
    df.loc[df["physical_remarks_clean"] == "", "physical_remarks_clean"] = df["physicalremarks"]

    # Create useful combined text column for AI logic
    df["combined_clinical_text"] = (
        df["Department"].fillna("") + " " +
        df["department_name"].fillna("") + " " +
        df["provisionaldiagnosis"].fillna("") + " " +
        df["clinicalnotes"].fillna("") + " " +
        df["physical_remarks_clean"].fillna("") + " " +
        df["vitalremarks"].fillna("") + " " +
        df["other_investigation_freetext"].fillna("") + " " +
        df["otheradvice"].fillna("") + " " +
        df["medicinedetails"].fillna("") + " " +
        df["other_medication_freetext"].fillna("")
    )

    df["combined_clinical_text"] = df["combined_clinical_text"].str.replace(
        r"\s+", " ", regex=True
    ).str.strip()

    df.to_csv(OUTPUT_PATH, index=False)

    print("\nClinical fields extracted successfully.")
    print(f"Saved at: {OUTPUT_PATH}")

    print("\nNew columns created:")
    print([
        "department_name",
        "provisionaldiagnosis",
        "clinicalnotes",
        "physical_remarks_clean",
        "vitalremarks",
        "other_investigation_freetext",
        "otheradvice",
        "medicinedetails",
        "other_medication_freetext",
        "combined_clinical_text"
    ])

    print("\nSample extracted output:")
    sample_cols = [
        "Patient_ID",
        "Department",
        "department_name",
        "provisionaldiagnosis",
        "clinicalnotes",
        "physical_remarks_clean",
        "vitalremarks",
        "other_investigation_freetext"
    ]

    print(df[sample_cols].head(3).to_string())


if __name__ == "__main__":
    extract_all_fields()