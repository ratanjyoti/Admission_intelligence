from pathlib import Path
import sys
import json


ROOT_DIR = Path(__file__).resolve().parents[1]

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


from backend.main import (
    IntakePatientPayload,
    api_health_check,
    get_dashboard_charts,
    get_dashboard_summary,
    get_patients,
    predict_patient,
)
from backend.ml_predictor import METADATA_PATH, METRICS_PATH, load_metrics
from backend.prescription_extraction import extract_prescription_payload, pdf_extraction_enabled


def main():
    health = api_health_check()
    patients = get_patients()
    summary = get_dashboard_summary()
    charts = get_dashboard_charts()
    intake_prediction = predict_patient(
        IntakePatientPayload(
            patientName="Predictive Intake Demo",
            department="Cardiology",
            diagnosis="Chest pain with diabetes and rising creatinine",
            clinicalNotes="Patient reports acute chest pain, breathlessness, diabetes history, and renal dysfunction.",
            vitalRemarks="Known diabetes mellitus and hypertension with repeat visit history.",
            investigations="Creatinine 2.1, ECG changes, elevated troponin under evaluation.",
            doctorAdvice="Urgent review and monitored admission if symptoms persist.",
            visitCount=2,
            repeatVisit=True,
            firstVisitRiskScore=4,
        )
    )
    predictive = intake_prediction["operational"]["predictiveModeling"]
    metrics = load_metrics()

    assert health["status"] in {"ok", "fallback"}
    assert health["patients_loaded"] > 0
    assert "llm_priority_limit" in health
    assert "llm_priority_patients" in health
    assert "agentic_provider" in health
    assert "agentic_model" in health
    assert "ml_enabled" in health
    assert "ml_models_ready" in health
    assert health["ml_model_version"]
    assert isinstance(patients, list) and len(patients) > 0
    assert summary["totalPatients"] == len(patients)
    assert "highRevenueCases" in summary
    assert "cannotBeDelayedCases" in summary
    assert "highReadmissionRiskCases" in summary
    assert "worseningPatients" in summary
    assert "totalAddressableRevenueLakhs" in summary
    assert "surgicalOpportunities" in summary
    assert "riskDistribution" in charts
    assert "cohortDistribution" in charts
    assert "departmentMetrics" in charts
    assert "operational" in patients[0]
    assert "clinicalIntelligence" in patients[0]["operational"]
    assert "packageIntelligence" in patients[0]["operational"]
    assert "lengthOfStay" in patients[0]["operational"]
    assert "readmissionRisk" in patients[0]["operational"]
    assert "admissionConversionProbability" in patients[0]["operational"]
    assert "clinicalTimeline" in patients[0]["operational"]
    assert "intelligenceProfile" in patients[0]["operational"]
    assert "predictiveModeling" in intake_prediction["operational"]
    assert METADATA_PATH.exists()
    assert METRICS_PATH.exists()
    assert "targets" in metrics
    assert "risk_category" in metrics["targets"]
    assert "holdout_metrics" in metrics["targets"]["risk_category"]
    assert intake_prediction["risk"]["category"] in {"Low", "Medium", "High", "Critical"}
    assert intake_prediction["admission"]["type"] in {"Elective", "Urgent", "Emergency"}
    assert intake_prediction["bed"]["type"]
    assert predictive["riskCategory"]["confidence"] >= 0
    assert predictive["admissionType"]["confidence"] >= 0
    assert predictive["bedType"]["confidence"] >= 0
    assert predictive["readmissionRisk"]["confidence"] >= 0
    assert predictive["revenueCategory"]["confidence"] >= 0
    assert predictive["lengthOfStay"]["highDays"] >= predictive["lengthOfStay"]["lowDays"]
    assert isinstance(predictive["topSignals"], list) and predictive["topSignals"]

    if pdf_extraction_enabled():
        import fitz

        pdf_document = fitz.open()
        page = pdf_document.new_page()
        page.insert_text(
            (36, 48),
            "\n".join(
                [
                    "Patient Name: Demo Patient",
                    "Doctor: Dr House",
                    "Diagnosis: Seizure disorder with chronic kidney disease",
                    "History: Known diabetes mellitus and hypertension. Follow-up review.",
                    "Investigations: CBC, Creatinine 2.3, ECG reviewed",
                    "Advice: Urgent admission and monitored review",
                    "Rx: TAB Levera 500 mg, TAB Telma 40",
                    "Procedure: Dialysis",
                ]
            ),
        )
        pdf_bytes = pdf_document.tobytes()
        pdf_document.close()

        extraction = extract_prescription_payload(pdf_bytes, filename="demo.pdf")
        assert extraction["autoFill"]["diagnosis"]
        assert extraction["autoFill"]["investigations"]
        assert extraction["autoFill"]["doctorAdvice"]
        assert extraction["autoFill"]["medicineDetails"]
        assert extraction["autoFill"]["repeatVisit"] is True

    print("Smoke test passed.")
    print(
        json.dumps(
            {
                "health": health,
                "patient_count": len(patients),
                "summary_total": summary["totalPatients"],
                "risk_buckets": len(charts["riskDistribution"]),
                "departments": len(charts["departmentMetrics"]),
                "high_revenue_cases": summary["highRevenueCases"],
                "cannot_be_delayed_cases": summary["cannotBeDelayedCases"],
                "high_readmission_cases": summary["highReadmissionRiskCases"],
                "worsening_patients": summary["worseningPatients"],
                "surgical_opportunities": summary["surgicalOpportunities"],
                "revenue_lakhs": summary["totalAddressableRevenueLakhs"],
                "sample_case_type": patients[0]["operational"]["caseType"]["label"],
                "sample_revenue": patients[0]["operational"]["packageIntelligence"]["expectedRevenue"],
                "intake_prediction_risk": intake_prediction["risk"]["category"],
                "intake_prediction_admission": intake_prediction["admission"]["type"],
                "risk_model": metrics["targets"]["risk_category"]["selected_model"],
                "risk_f1": metrics["targets"]["risk_category"]["holdout_metrics"]["f1_macro"],
                "los_mae": metrics["targets"]["length_of_stay"]["holdout_metrics"]["mae"],
            },
            ensure_ascii=True,
        )
    )


if __name__ == "__main__":
    main()
