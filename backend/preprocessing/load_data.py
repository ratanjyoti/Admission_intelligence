import pandas as pd
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
RAW_DATA_PATH = ROOT_DIR / "data" / "raw" / "ipd_data_May_12_new_1.xlsx - Sheet1.csv"


def load_patient_data():
    if not RAW_DATA_PATH.exists():
        raise FileNotFoundError(f"File not found: {RAW_DATA_PATH}")

    df = pd.read_csv(RAW_DATA_PATH)

    print("\nDataset Loaded Successfully")
    print("-" * 50)

    print("\nShape of dataset:")
    print(df.shape)

    print("\nColumns:")
    print(df.columns.tolist())

    print("\nFirst 5 rows:")
    print(df.head())

    print("\nDataset info:")
    print(df.info())

    print("\nMissing values:")
    print(df.isnull().sum())

    return df


if __name__ == "__main__":
    load_patient_data()