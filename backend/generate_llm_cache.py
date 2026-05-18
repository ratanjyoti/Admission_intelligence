from pathlib import Path
import sys
import os


ROOT_DIR = Path(__file__).resolve().parents[1]

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


from backend.data_service import get_llm_priority_limit, get_llm_priority_patients, load_raw_patients
from backend.llm_intelligence import (
    cache_backend,
    get_cached_llm_operational,
    get_last_llm_error,
    get_model_name,
    get_provider_name,
    llm_feature_enabled,
)
from backend.operational_intelligence import enrich_patient_record


def main():
    if not llm_feature_enabled():
        print(
            "LLM intelligence is not enabled. "
            "Set the provider API key and ENABLE_LLM_INTELLIGENCE=true first."
        )
        return

    all_patients = load_raw_patients()
    patients = get_llm_priority_patients()
    cache_limit = int(os.getenv("LLM_CACHE_LIMIT", "0") or "0")
    if cache_limit > 0:
        patients = patients[:cache_limit]
    total = len(patients)

    print(
        f"Generating cached LLM intelligence for {total} patients "
        f"out of {len(all_patients)} total patients..."
    )
    print(f"Cache backend: {cache_backend()}")
    print(f"LLM provider: {get_provider_name()} | model: {get_model_name()}")
    print(f"Rule-based intelligence remains active for all patients. LLM is limited to top {get_llm_priority_limit()} priority patients.")
    cache_hits = 0
    generated = 0
    missing = 0

    for index, patient in enumerate(patients, start=1):
        had_cache = bool(get_cached_llm_operational(patient))
        enrich_patient_record(patient, llm_allowed=True, allow_live_llm=True)
        has_cache_now = bool(get_cached_llm_operational(patient))
        patient_id = patient.get("patientId") or f"patient-{index}"
        if had_cache:
            cache_hits += 1
            status = "cache hit"
        elif has_cache_now:
            generated += 1
            status = "generated"
        else:
            missing += 1
            llm_error = get_last_llm_error()
            status = f"no cache written ({llm_error or 'unknown reason'})"
        print(f"[{index}/{total}] {status}: {patient_id}")

    print(
        "LLM cache generation completed. "
        f"Hits: {cache_hits}, Generated: {generated}, Missing: {missing}"
    )


if __name__ == "__main__":
    main()
