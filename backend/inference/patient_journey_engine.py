import pandas as pd
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]

INPUT_PATH = ROOT_DIR / "data" / "processed" / "patients_with_bed_logic.csv"
OUTPUT_PATH = ROOT_DIR / "data" / "processed" / "patients_with_journey.csv"


def build_risk_progression(group):
    group = group.sort_values("Visit_Date")

    progression = []

    for _, row in group.iterrows():
        progression.append(
            {
                "visit_date": str(row["Visit_Date"]),
                "risk_score": int(row["patient_risk_score"]),
                "risk_category": row["patient_risk_category"],
                "admission_type": row["admission_type"],
            }
        )

    return progression


def detect_progression_trend(group):
    group = group.sort_values("Visit_Date")

    scores = group["patient_risk_score"].tolist()

    if len(scores) == 1:
        return "Single Visit"

    if scores[-1] > scores[0]:
        return "Worsening"

    if scores[-1] < scores[0]:
        return "Improving"

    return "Stable"


def build_timeline_summary(group):
    group = group.sort_values("Visit_Date")

    first = group.iloc[0]
    latest = group.iloc[-1]

    return (
        f"Patient had {len(group)} visit(s). First visit was on {first['Visit_Date']} "
        f"with risk score {first['patient_risk_score']}. Latest visit was on "
        f"{latest['Visit_Date']} with risk score {latest['patient_risk_score']}."
    )


def build_patient_journey_features():
    df = pd.read_csv(INPUT_PATH)

    df["Visit_Date"] = pd.to_datetime(df["Visit_Date"], errors="coerce")

    journey_rows = []

    for patient_id, group in df.groupby("Patient_ID"):
        group = group.sort_values("Visit_Date")

        latest_row = group.iloc[-1].copy()

        latest_row["visit_count"] = len(group)
        latest_row["first_visit_date"] = group["Visit_Date"].min()
        latest_row["latest_visit_date"] = group["Visit_Date"].max()
        latest_row["repeat_visit_flag"] = "Yes" if len(group) > 1 else "No"
        latest_row["risk_progression"] = build_risk_progression(group)
        latest_row["progression_trend"] = detect_progression_trend(group)
        latest_row["timeline_summary"] = build_timeline_summary(group)

        journey_rows.append(latest_row)

    journey_df = pd.DataFrame(journey_rows)

    journey_df = journey_df.sort_values(
        by=["patient_risk_score", "visit_count"],
        ascending=False
    )

    journey_df.to_csv(OUTPUT_PATH, index=False)

    print("\nPatient journey engine completed.")
    print(f"Saved at: {OUTPUT_PATH}")

    print("\nOriginal rows:")
    print(df.shape[0])

    print("\nUnique patient profiles:")
    print(journey_df.shape[0])

    print("\nProgression trend distribution:")
    print(journey_df["progression_trend"].value_counts())

    print("\nSample journey output:")
    cols = [
        "Patient_ID",
        "Patient_Name",
        "visit_count",
        "first_visit_date",
        "latest_visit_date",
        "repeat_visit_flag",
        "patient_risk_score",
        "patient_risk_category",
        "progression_trend",
        "timeline_summary",
    ]

    print(journey_df[cols].head(15).to_string())


if __name__ == "__main__":
    build_patient_journey_features()