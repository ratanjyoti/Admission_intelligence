import pandas as pd
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]

INPUT_PATH = ROOT_DIR / "data" / "processed" / "patients_with_risk.csv"
OUTPUT_PATH = ROOT_DIR / "data" / "processed" / "patients_with_procedure.csv"


EXPLICIT_PROCEDURE_KEYWORDS = {
    "abdominal wall reconstruction": "Abdominal Wall Reconstruction",
    "cataract": "Cataract Surgery",
    "cataract surgery": "Cataract Surgery",
    "laparotomy": "Exploratory Laparotomy",
    "renal transplant": "Renal Transplant",
    "lrrt": "Living Related Renal Transplant",
    "bone marrow transplant": "Bone Marrow Transplant",
    "bmt": "Bone Marrow Transplant",
    "angioplasty": "Angioplasty",
    "cabg": "CABG",
    "dialysis": "Dialysis",
    "endoscopy": "Endoscopy",
    "colonoscopy": "Colonoscopy",
    "biopsy": "Biopsy",
    "chemotherapy": "Chemotherapy",
    "radiotherapy": "Radiotherapy",
}


INFERRED_PROCEDURE_RULES = [
    {
        "keywords": ["hernia", "swelling", "surgical gastro"],
        "procedure": "Hernia Repair Surgery",
        "confidence": 75,
    },
    {
        "keywords": ["appendix", "appendicitis"],
        "procedure": "Appendectomy",
        "confidence": 75,
    },
    {
        "keywords": ["gallstone", "cholelithiasis", "gall bladder"],
        "procedure": "Laparoscopic Cholecystectomy",
        "confidence": 75,
    },
    {
        "keywords": ["asthma", "retractions", "asthalin", "nebulization"],
        "procedure": "Respiratory Stabilization / Nebulization",
        "confidence": 70,
    },
    {
        "keywords": ["kidney", "creat", "nephrologist", "tacrolimus"],
        "procedure": "Nephrology Monitoring / Renal Function Management",
        "confidence": 65,
    },
    {
        "keywords": ["cataract", "ophthalmologist"],
        "procedure": "Cataract Surgery",
        "confidence": 85,
    },
    {
        "keywords": ["lymphoma", "rituximab", "oncology"],
        "procedure": "Oncology Treatment / Chemotherapy Pathway",
        "confidence": 70,
    },
]


def normalize_text(row):
    text_parts = [
        row.get("Department", ""),
        row.get("department_name", ""),
        row.get("provisionaldiagnosis", ""),
        row.get("clinicalnotes", ""),
        row.get("physical_remarks_clean", ""),
        row.get("vitalremarks", ""),
        row.get("other_investigation_freetext", ""),
        row.get("combined_clinical_text", ""),
    ]

    return " ".join([str(x) for x in text_parts]).lower()


def extract_explicit_procedure(row):
    """
    Uses PAC and directly mentioned procedure phrases first.
    """
    text = normalize_text(row)

    pac_text = str(row.get("pac", "")).lower()

    if pac_text and pac_text != "nan":
        if "abdominal wall reconstruction" in pac_text:
            return "Abdominal Wall Reconstruction", 95, "Detected directly from PAC field"

        return pac_text.title(), 90, "Detected directly from PAC field"

    for keyword, procedure in EXPLICIT_PROCEDURE_KEYWORDS.items():
        if keyword in text:
            return procedure, 90, f"Detected explicit mention: {keyword}"

    return "Not Explicitly Mentioned", 0, "No explicit procedure found"


def infer_procedure(row):
    text = normalize_text(row)

    for rule in INFERRED_PROCEDURE_RULES:
        if all(keyword in text for keyword in rule["keywords"]):
            return (
                rule["procedure"],
                rule["confidence"],
                "Inferred from diagnosis, symptoms, and department"
            )

    return (
        "Not Available",
        50,
        "Insufficient information for reliable procedure inference"
    )


def build_procedure_features():
    df = pd.read_csv(INPUT_PATH)

    explicit_results = df.apply(extract_explicit_procedure, axis=1)
    df["procedure_name"] = explicit_results.apply(lambda x: x[0])
    df["procedure_confidence"] = explicit_results.apply(lambda x: x[1])
    df["procedure_source"] = explicit_results.apply(lambda x: x[2])

    inferred_results = df.apply(infer_procedure, axis=1)

    df["inferred_procedure_name"] = inferred_results.apply(lambda x: x[0])
    df["inferred_procedure_confidence"] = inferred_results.apply(lambda x: x[1])
    df["inferred_procedure_source"] = inferred_results.apply(lambda x: x[2])

    # If explicit procedure exists, inference is not needed
    explicit_mask = df["procedure_name"] != "Not Explicitly Mentioned"

    df.loc[explicit_mask, "inferred_procedure_name"] = "Not Needed - Explicit Procedure Available"
    df.loc[explicit_mask, "inferred_procedure_confidence"] = df.loc[
        explicit_mask, "procedure_confidence"
    ]
    df.loc[explicit_mask, "inferred_procedure_source"] = "Explicit procedure takes priority"

    df.to_csv(OUTPUT_PATH, index=False)

    print("\nProcedure engine completed successfully.")
    print(f"Saved at: {OUTPUT_PATH}")

    print("\nExplicit Procedure Count:")
    print((df["procedure_name"] != "Not Explicitly Mentioned").sum())

    print("\nInferred Procedure Distribution:")
    print(df["inferred_procedure_name"].value_counts().head(10))

    print("\nSample procedure output:")
    cols = [
        "Patient_ID",
        "Department",
        "procedure_name",
        "procedure_confidence",
        "procedure_source",
        "inferred_procedure_name",
        "inferred_procedure_confidence",
        "inferred_procedure_source",
    ]

    print(df[cols].head(15).to_string())


if __name__ == "__main__":
    build_procedure_features()