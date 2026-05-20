import hashlib
import json

from backend.models import LLMPatientIntelligence


def make_source_hash(patient_payload, workflow_version=None):
    raw_text = json.dumps(patient_payload, sort_keys=True, default=str, ensure_ascii=True)
    digest = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()
    if workflow_version:
        return f"{digest}:{workflow_version}"
    return digest


def get_cached_intelligence(db, patient_id, source_hash):
    return (
        db.query(LLMPatientIntelligence)
        .filter(
            LLMPatientIntelligence.patient_id == patient_id,
            LLMPatientIntelligence.source_hash == source_hash,
        )
        .first()
    )


def save_intelligence(db, patient_id, source_hash, intelligence, provider="openai", model_name=None):
    existing = get_cached_intelligence(db, patient_id, source_hash)

    if existing:
        existing.intelligence_json = intelligence
        existing.llm_provider = provider
        existing.model_name = model_name
        db.commit()
        db.refresh(existing)
        return existing

    record = LLMPatientIntelligence(
        patient_id=patient_id,
        source_hash=source_hash,
        llm_provider=provider,
        model_name=model_name,
        intelligence_json=intelligence,
    )

    db.add(record)
    db.commit()
    db.refresh(record)
    return record
