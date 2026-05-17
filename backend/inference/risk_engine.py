import pandas as pd
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
INPUT_PATH = ROOT_DIR / "data" / "processed" / "patients_extracted.csv"
OUTPUT_PATH = ROOT_DIR / "data" / "processed" / "patients_with_risk.csv"


CURRENT_DANGER_KEYWORDS = {
    "retractions": 3,
    "chest ae reduced": 3,
    "breathlessness": 3,
    "shortness of breath": 3,
    "spo2": 2,
    "stat": 2,
    "emergency": 4,
    "severe pain": 3,
    "acute": 2,
    "bleeding": 3,
    "fever": 2,
    "vomiting": 1,
    "swelling": 1,
    "unconscious": 4,
    "seizure": 4,
    "stroke": 4,
    "infection": 2,
    "acute renal injury": 3,
}

CHRONIC_RISK_KEYWORDS = {
    "hypertension": 1,
    "diabetes": 1,
    "chronic": 1,
    "osa": 1,
    "cpap": 1,
    "heart block": 2,
    "nephropathy": 1,
    "liver disease": 1,
    "hypothyroidism": 1,
    "osteoporosis": 1,
}

PAST_HISTORY_KEYWORDS = {
    "post lrrt": 1,
    "transplant": 1,
    "operated": 1,
    "previous laparotomy": 1,
    "past": 1,
    "history": 1,
    "perforated appendix": 1,
    "intestinal obstruction": 1,
}

SURGICAL_OPPORTUNITY_KEYWORDS = {
    "surgery": 1,
    "reconstruction": 1,
    "hernia": 1,
    "laparotomy": 1,
    "appendix": 1,
    "cataract": 1,
}


def get_text(row):
    return str(row.get("combined_clinical_text", "")).lower()


def detect_keywords(text, keyword_dict):
    detected = []

    for keyword in keyword_dict:
        if keyword in text:
            detected.append(keyword)

    return detected


def calculate_risk_score(row):
    text = get_text(row)

    current_flags = detect_keywords(text, CURRENT_DANGER_KEYWORDS)
    chronic_flags = detect_keywords(text, CHRONIC_RISK_KEYWORDS)
    past_flags = detect_keywords(text, PAST_HISTORY_KEYWORDS)
    surgical_flags = detect_keywords(text, SURGICAL_OPPORTUNITY_KEYWORDS)

    score = 2

    for flag in current_flags:
        score += CURRENT_DANGER_KEYWORDS[flag]

    for flag in chronic_flags:
        score += CHRONIC_RISK_KEYWORDS[flag]

    for flag in past_flags:
        score += PAST_HISTORY_KEYWORDS[flag]

    for flag in surgical_flags:
        score += SURGICAL_OPPORTUNITY_KEYWORDS[flag]

    # Safety cap
    score = min(score, 10)

    return score


def assign_risk_category(score):
    if score >= 9:
        return "Critical"
    elif score >= 7:
        return "High"
    elif score >= 4:
        return "Medium"
    return "Low"


def detect_all_flags(row):
    text = get_text(row)

    return {
        "current_red_flags": detect_keywords(text, CURRENT_DANGER_KEYWORDS),
        "chronic_risk_factors": detect_keywords(text, CHRONIC_RISK_KEYWORDS),
        "past_history_factors": detect_keywords(text, PAST_HISTORY_KEYWORDS),
        "surgical_opportunity_factors": detect_keywords(text, SURGICAL_OPPORTUNITY_KEYWORDS),
    }


def generate_risk_reasoning(row):
    flags = row["risk_factor_breakdown"]
    score = row["patient_risk_score"]
    category = row["patient_risk_category"]

    current_flags = flags["current_red_flags"]
    chronic_flags = flags["chronic_risk_factors"]
    past_flags = flags["past_history_factors"]

    reasons = []

    if current_flags:
        reasons.append(
            "current red flags: " + ", ".join(current_flags[:4])
        )

    if chronic_flags:
        reasons.append(
            "chronic risk factors: " + ", ".join(chronic_flags[:4])
        )

    if past_flags:
        reasons.append(
            "past history factors: " + ", ".join(past_flags[:4])
        )

    if not reasons:
        return f"Risk score is {score}/10 and category is {category} because no major red flags were detected."

    return (
        f"Risk score is {score}/10 and category is {category}. "
        f"Reasoning based on " + " | ".join(reasons)
    )


def build_risk_features():
    df = pd.read_csv(INPUT_PATH)

    df["risk_factor_breakdown"] = df.apply(detect_all_flags, axis=1)

    df["current_red_flags"] = df["risk_factor_breakdown"].apply(
        lambda x: x["current_red_flags"]
    )

    df["chronic_risk_factors"] = df["risk_factor_breakdown"].apply(
        lambda x: x["chronic_risk_factors"]
    )

    df["past_history_factors"] = df["risk_factor_breakdown"].apply(
        lambda x: x["past_history_factors"]
    )

    df["surgical_opportunity_factors"] = df["risk_factor_breakdown"].apply(
        lambda x: x["surgical_opportunity_factors"]
    )

    df["patient_risk_score"] = df.apply(calculate_risk_score, axis=1)

    df["patient_risk_category"] = df["patient_risk_score"].apply(
        assign_risk_category
    )

    df["risk_reasoning"] = df.apply(generate_risk_reasoning, axis=1)

    df.to_csv(OUTPUT_PATH, index=False)

    print("\nImproved risk engine completed successfully.")
    print(f"Saved at: {OUTPUT_PATH}")

    print("\nRisk category distribution:")
    print(df["patient_risk_category"].value_counts())

    print("\nSample improved risk output:")
    cols = [
        "Patient_ID",
        "Department",
        "provisionaldiagnosis",
        "current_red_flags",
        "chronic_risk_factors",
        "past_history_factors",
        "patient_risk_score",
        "patient_risk_category",
        "risk_reasoning",
    ]

    print(df[cols].head(10).to_string())


if __name__ == "__main__":
    build_risk_features()