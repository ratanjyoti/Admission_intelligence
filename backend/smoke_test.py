from pathlib import Path
import sys


ROOT_DIR = Path(__file__).resolve().parents[1]

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


from backend.main import api_health_check, get_dashboard_charts, get_dashboard_summary, get_patients


def main():
    health = api_health_check()
    patients = get_patients()
    summary = get_dashboard_summary()
    charts = get_dashboard_charts()

    assert health["status"] in {"ok", "fallback"}
    assert health["patients_loaded"] > 0
    assert isinstance(patients, list) and len(patients) > 0
    assert summary["totalPatients"] == len(patients)
    assert "riskDistribution" in charts
    assert "departmentMetrics" in charts

    print("Smoke test passed.")
    print(
        {
            "health": health,
            "patient_count": len(patients),
            "summary_total": summary["totalPatients"],
            "risk_buckets": len(charts["riskDistribution"]),
            "departments": len(charts["departmentMetrics"]),
        }
    )


if __name__ == "__main__":
    main()
