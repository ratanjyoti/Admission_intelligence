import pandas as pd
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]

INPUT_PATH = ROOT_DIR / "data" / "processed" / "patients_with_journey.csv"
OUTPUT_PATH = ROOT_DIR / "data" / "processed" / "patients_with_traceability.csv"


TRACE_KEYWORDS = {
    "respiratory_distress": [
        "retractions",
        "breathlessness",
        "chest ae reduced",
        "asthalin",
        "nebulization",
    ],
    "emergency_signals": [
        "emergency",
        "stat",
        "acute",
        "severe",
        "bleeding",
        "stroke",
        "seizure",
    ],
    "chronic_risk": [
        "hypertension",
        "diabetes",
        "chronic",
        "osa",
        "cpap",
        "heart block",
        "nephropathy",
    ],
    "surgical_indicators": [
        "surgery",
        "reconstruction",
        "hernia",
        "laparotomy",
        "appendix",
        "cataract",
    ],
    "renal_indicators": [
        "creat",
        "tacrolimus",
        "transplant",
        "lrrt",
        "renal",
        "kidney",
    ],
    "oncology_indicators": [
        "oncology",
        "lymphoma",
        "chemotherapy",
        "rituximab",
        "bone marrow",
    ],
}


SOURCE_COLUMNS = {
    "provisionaldiagnosis": "Diagnosis",
    "clinicalnotes": "Clinical Notes",
    "physical_remarks_clean": "Physical Remarks",
    "vitalremarks": "Vital Remarks / History",
    "other_investigation_freetext": "Investigations",
    "otheradvice": "Doctor Advice",
    "medicinedetails": "Medicine Details",
    "other_medication_freetext": "Other Medication",
    "combined_clinical_text": "Combined Clinical Text",
}


def safe_text(value):
    if pd.isna(value):
        return ""
    return str(value).lower()


def find_keyword_evidence(row):
    evidence = []
    seen = set()

    for category, keywords in TRACE_KEYWORDS.items():
        for keyword in keywords:
            if keyword in seen:
                continue
            for col, label in SOURCE_COLUMNS.items():
                text = safe_text(row.get(col, ""))

                if keyword in text:
                    seen.add(keyword)
                    evidence.append(
                        {
                            "category": category,
                            "keyword": keyword,
                            "source_section": label,
                            "evidence_snippet": extract_snippet(text, keyword),
                        }
                    )
                    break

    return evidence


def extract_snippet(text, keyword, window=60):
    idx = text.find(keyword)

    if idx == -1:
        return ""

    start = max(0, idx - window)
    end = min(len(text), idx + len(keyword) + window)

    snippet = text[start:end].strip()
    return snippet


def build_source_sections(row):
    sources = []

    for col, label in SOURCE_COLUMNS.items():
        text = safe_text(row.get(col, ""))

        if text and text != "nan":
            sources.append(label)

    return sources


def generate_trace_summary(row):
    evidence = row["ai_evidence_trace"]

    if not evidence:
        return "No strong traceable clinical trigger found in available notes."

    top_items = evidence[:4]

    parts = []

    for item in top_items:
        parts.append(
            f"{item['keyword']} found in {item['source_section']}"
        )

    return "AI decision supported by: " + "; ".join(parts)


def generate_clinician_warning(row):
    confidence = str(row.get("procedure_confidence", ""))
    risk = str(row.get("patient_risk_category", ""))

    if risk in ["Critical", "High"]:
        return (
            "AI-assisted prioritization. Clinician validation required before final admission decision."
        )

    if confidence in ["0", "50"]:
        return (
            "Low confidence inference. Review clinical note before acting."
        )

    return "AI output should be reviewed as part of standard clinical workflow."


def build_traceability_features():
    df = pd.read_csv(INPUT_PATH)

    df["ai_evidence_trace"] = df.apply(find_keyword_evidence, axis=1)
    df["source_sections_used"] = df.apply(build_source_sections, axis=1)

    df["traceability_summary"] = df.apply(
        generate_trace_summary,
        axis=1
    )

    df["clinical_safety_note"] = df.apply(
        generate_clinician_warning,
        axis=1
    )

    df["evidence_count"] = df["ai_evidence_trace"].apply(len)

    df.to_csv(OUTPUT_PATH, index=False)

    print("\nTraceability engine completed.")
    print(f"Saved at: {OUTPUT_PATH}")

    print("\nEvidence count stats:")
    print(df["evidence_count"].describe())

    print("\nSample traceability output:")
    cols = [
        "Patient_ID",
        "Patient_Name",
        "patient_risk_category",
        "admission_type",
        "smart_bed_type",
        "evidence_count",
        "traceability_summary",
        "clinical_safety_note",
    ]

    print(df[cols].head(15).to_string())


if __name__ == "__main__":
    build_traceability_features()