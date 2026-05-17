# from pathlib import Path
# from backend.preprocessing.normalize_data import normalize_patient_data

# ROOT_DIR = Path(__file__).resolve().parents[2]
# PROCESSED_DIR = ROOT_DIR / "data" / "processed"


# def clean_patient_data():
#     PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
#     df = normalize_patient_data()

#     print("\nCleaned dataset shape:")
#     print(df.shape)

#     print("\nMissing values after normalization:")
#     print(df.isnull().sum())

#     return df


# if __name__ == "__main__":
#     clean_patient_data()'
# 
# 
import pandas as pd
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
RAW_DATA_PATH = ROOT_DIR / "data" / "raw" / "patient_data.csv"
PROCESSED_DIR = ROOT_DIR / "data" / "processed"
CLEANED_OUTPUT_PATH = PROCESSED_DIR / "cleaned_patients.csv"


def clean_patient_data():
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(RAW_DATA_PATH)

    print("\nOriginal Dataset Shape:")
    print(df.shape)

    df.columns = df.columns.str.strip()

    text_columns = [
        "Patient_ID",
        "Patient_Name",
        "Doctor_Name",
        "Department",
        "Clinical_Note",
        "Customer_Type",
    ]

    for col in text_columns:
        df[col] = df[col].astype(str).str.strip()
        df[col] = df[col].str.replace(r"\s+", " ", regex=True)

    df["Visit_Date"] = pd.to_datetime(
        df["Visit_Date"],
        errors="coerce",
        dayfirst=True
    )

    before_duplicates = df.shape[0]
    df = df.drop_duplicates()
    after_duplicates = df.shape[0]

    print("\nDuplicate rows removed:")
    print(before_duplicates - after_duplicates)

    print("\nCleaned Dataset Shape:")
    print(df.shape)

    print("\nDate conversion check:")
    print(df["Visit_Date"].head())

    print("\nMissing values after cleaning:")
    print(df.isnull().sum())

    df.to_csv(CLEANED_OUTPUT_PATH, index=False)

    print(f"\nCleaned data saved at: {CLEANED_OUTPUT_PATH}")

    return df


if __name__ == "__main__":
    clean_patient_data()