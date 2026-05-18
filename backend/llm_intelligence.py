import json
import os
from pathlib import Path
from threading import Lock

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover
    OpenAI = None

from backend.database import SessionLocal, database_connected, database_enabled
from backend.llm_cache import get_cached_intelligence, make_source_hash, save_intelligence


ROOT_DIR = Path(__file__).resolve().parents[1]
CACHE_PATH = ROOT_DIR / "data" / "processed" / "llm_intelligence_cache.json"
_CACHE_LOCK = Lock()
_CACHE_DATA = None
_CLIENT = None
_LAST_LLM_ERROR = None
_DATABASE_CACHE_USABLE = None
GROQ_BASE_URL = "https://api.groq.com/openai/v1"

if load_dotenv:
    load_dotenv(ROOT_DIR / ".env")
    load_dotenv(ROOT_DIR / "backend" / ".env")


LLM_OUTPUT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "clinicalIntelligence": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "icd10Codes": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "code": {"type": "string"},
                            "label": {"type": "string"},
                            "matchedKeyword": {"type": "string"},
                            "source": {"type": "string"},
                            "evidence": {"type": "string"},
                        },
                        "required": ["code", "label", "matchedKeyword", "source", "evidence"],
                    },
                },
                "primaryIcd10": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "code": {"type": "string"},
                        "label": {"type": "string"},
                        "matchedKeyword": {"type": "string"},
                        "source": {"type": "string"},
                        "evidence": {"type": "string"},
                    },
                    "required": ["code", "label", "matchedKeyword", "source", "evidence"],
                },
                "comorbidities": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "label": {"type": "string"},
                            "source": {"type": "string"},
                            "evidence": {"type": "string"},
                        },
                        "required": ["label", "source", "evidence"],
                    },
                },
                "possibleSymptoms": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "label": {"type": "string"},
                            "source": {"type": "string"},
                            "evidence": {"type": "string"},
                        },
                        "required": ["label", "source", "evidence"],
                    },
                },
                "structuredHistory": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "pastConditions": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "additionalProperties": False,
                                "properties": {
                                    "label": {"type": "string"},
                                    "source": {"type": "string"},
                                    "evidence": {"type": "string"},
                                },
                                "required": ["label", "source", "evidence"],
                            },
                        },
                        "surgeries": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "additionalProperties": False,
                                "properties": {
                                    "label": {"type": "string"},
                                    "source": {"type": "string"},
                                    "evidence": {"type": "string"},
                                },
                                "required": ["label", "source", "evidence"],
                            },
                        },
                        "medications": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "additionalProperties": False,
                                "properties": {
                                    "label": {"type": "string"},
                                    "source": {"type": "string"},
                                },
                                "required": ["label", "source"],
                            },
                        },
                        "familyHistory": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "additionalProperties": False,
                                "properties": {
                                    "label": {"type": "string"},
                                    "source": {"type": "string"},
                                },
                                "required": ["label", "source"],
                            },
                        },
                        "summary": {"type": "string"},
                    },
                    "required": [
                        "pastConditions",
                        "surgeries",
                        "medications",
                        "familyHistory",
                        "summary",
                    ],
                },
                "diseaseCohorts": {"type": "array", "items": {"type": "string"}},
                "primaryCohort": {"type": "string"},
            },
            "required": [
                "icd10Codes",
                "primaryIcd10",
                "comorbidities",
                "possibleSymptoms",
                "structuredHistory",
                "diseaseCohorts",
                "primaryCohort",
            ],
        },
        "caseType": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "label": {"type": "string"},
                "reasoning": {"type": "string"},
            },
            "required": ["label", "reasoning"],
        },
        "packageIntelligence": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "expectedRevenue": {"type": "string"},
                "revenueCategory": {"type": "string"},
                "minLakhs": {"type": "number"},
                "maxLakhs": {"type": "number"},
                "midLakhs": {"type": "number"},
                "score": {"type": "number"},
                "drivers": {"type": "array", "items": {"type": "string"}},
                "reasoning": {"type": "string"},
            },
            "required": [
                "expectedRevenue",
                "revenueCategory",
                "minLakhs",
                "maxLakhs",
                "midLakhs",
                "score",
                "drivers",
                "reasoning",
            ],
        },
        "lengthOfStay": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "label": {"type": "string"},
                "minDays": {"type": "number"},
                "maxDays": {"type": "number"},
                "drivers": {"type": "array", "items": {"type": "string"}},
                "reasoning": {"type": "string"},
            },
            "required": ["label", "minDays", "maxDays", "drivers", "reasoning"],
        },
        "readmissionRisk": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "label": {"type": "string"},
                "score": {"type": "number"},
                "drivers": {"type": "array", "items": {"type": "string"}},
                "reasoning": {"type": "string"},
            },
            "required": ["label", "score", "drivers", "reasoning"],
        },
        "noShowRisk": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "label": {"type": "string"},
                "score": {"type": "number"},
                "drivers": {"type": "array", "items": {"type": "string"}},
                "reasoning": {"type": "string"},
            },
            "required": ["label", "score", "drivers", "reasoning"],
        },
        "deferredTime": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "label": {"type": "string"},
                "drivers": {"type": "array", "items": {"type": "string"}},
                "reasoning": {"type": "string"},
            },
            "required": ["label", "drivers", "reasoning"],
        },
        "admissionConversionProbability": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "label": {"type": "string"},
                "percentage": {"type": "number"},
                "drivers": {"type": "array", "items": {"type": "string"}},
                "reasoning": {"type": "string"},
            },
            "required": ["label", "percentage", "drivers", "reasoning"],
        },
        "treatmentPlan": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "primary": {"type": "string"},
                "secondary": {"type": "string"},
                "reasoning": {"type": "string"},
            },
            "required": ["primary", "secondary", "reasoning"],
        },
        "clinicalTimeline": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "summary": {"type": "string"},
                "stages": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "stage": {"type": "string"},
                            "date": {"type": "string"},
                            "summary": {"type": "string"},
                            "source": {"type": "string"},
                        },
                        "required": ["stage", "date", "summary", "source"],
                    },
                },
            },
            "required": ["summary", "stages"],
        },
        "normalizedSummary": {"type": "array", "items": {"type": "string"}},
        "priorityInsights": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "title": {"type": "string"},
                    "explanation": {"type": "string"},
                    "source": {"type": "string"},
                    "evidence": {"type": "string"},
                },
                "required": ["title", "explanation", "source", "evidence"],
            },
        },
    },
    "required": [
        "clinicalIntelligence",
        "caseType",
        "packageIntelligence",
        "lengthOfStay",
        "readmissionRisk",
        "noShowRisk",
        "deferredTime",
        "admissionConversionProbability",
        "treatmentPlan",
        "clinicalTimeline",
        "normalizedSummary",
        "priorityInsights",
    ],
}


def get_provider_name():
    return os.getenv("LLM_PROVIDER", "openai").strip().lower()


def get_api_key():
    provider = get_provider_name()

    if provider == "groq":
        return os.getenv("GROQ_API_KEY")

    return os.getenv("OPENAI_API_KEY")


def llm_feature_enabled():
    feature_flag = os.getenv("ENABLE_LLM_INTELLIGENCE", "true").strip().lower()
    return (
        feature_flag not in {"0", "false", "no", "off"}
        and bool(get_api_key())
        and OpenAI is not None
    )


def _set_last_llm_error(message):
    global _LAST_LLM_ERROR
    _LAST_LLM_ERROR = message


def get_last_llm_error():
    return _LAST_LLM_ERROR


def _database_cache_usable(force_refresh=False):
    global _DATABASE_CACHE_USABLE

    if not database_enabled():
        _DATABASE_CACHE_USABLE = False
        return False

    if force_refresh or _DATABASE_CACHE_USABLE is None:
        _DATABASE_CACHE_USABLE = database_connected()

    return _DATABASE_CACHE_USABLE


def get_model_name():
    provider = get_provider_name()

    if provider == "groq":
        return os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile").strip().strip("'\"")

    return os.getenv("OPENAI_MODEL", "gpt-4.1-mini").strip().strip("'\"")


def get_temperature():
    try:
        return float(os.getenv("LLM_TEMPERATURE", "0.2"))
    except ValueError:
        return 0.2


def get_max_tokens():
    try:
        return int(os.getenv("LLM_MAX_TOKENS", "2400"))
    except ValueError:
        return 2400


def _get_client():
    global _CLIENT

    if _CLIENT is None and llm_feature_enabled():
        provider = get_provider_name()
        api_key = get_api_key()

        if provider == "groq":
            _CLIENT = OpenAI(api_key=api_key, base_url=GROQ_BASE_URL)
        else:
            _CLIENT = OpenAI(api_key=api_key)

    return _CLIENT


def _load_cache():
    global _CACHE_DATA

    if _CACHE_DATA is None:
        if CACHE_PATH.exists():
            try:
                _CACHE_DATA = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                _CACHE_DATA = {}
        else:
            _CACHE_DATA = {}

    return _CACHE_DATA


def _save_cache(cache_data):
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(
        json.dumps(cache_data, ensure_ascii=True, indent=2),
        encoding="utf-8",
    )


def _patient_cache_payload(patient):
    return {
        "patientId": patient.get("patientId"),
        "patientName": patient.get("patientName"),
        "visitDate": patient.get("visitDate"),
        "doctorName": patient.get("doctorName"),
        "department": patient.get("department"),
        "customerType": patient.get("customerType"),
        "risk": patient.get("risk"),
        "admission": patient.get("admission"),
        "bed": patient.get("bed"),
        "procedure": patient.get("procedure"),
        "journey": patient.get("journey"),
        "traceability": patient.get("traceability"),
        "validation": patient.get("validation"),
        "clinical": patient.get("clinical"),
    }


def _cache_key(patient):
    return str(patient.get("patientId") or "").strip()


def _patient_fingerprint(patient):
    return make_source_hash(_patient_cache_payload(patient))


def cache_backend():
    return "postgres" if _database_cache_usable() else "file"


def _get_cached_from_database(patient):
    if not _database_cache_usable():
        return None

    patient_id = _cache_key(patient)

    if not patient_id:
        return None

    db = SessionLocal()

    try:
        cached = get_cached_intelligence(db, patient_id, _patient_fingerprint(patient))
        if cached:
            return cached.intelligence_json
    except Exception:
        global _DATABASE_CACHE_USABLE
        _DATABASE_CACHE_USABLE = False
        return None
    finally:
        db.close()

    return None


def _save_cached_to_database(patient, payload):
    if not _database_cache_usable():
        return False

    patient_id = _cache_key(patient)

    if not patient_id:
        return False

    db = SessionLocal()

    try:
        save_intelligence(
            db=db,
            patient_id=patient_id,
            source_hash=_patient_fingerprint(patient),
            intelligence=payload,
            provider=get_provider_name(),
            model_name=get_model_name(),
        )
        return True
    except Exception:
        global _DATABASE_CACHE_USABLE
        _DATABASE_CACHE_USABLE = False
        return False
    finally:
        db.close()


def get_cached_llm_operational(patient):
    database_payload = _get_cached_from_database(patient)

    if database_payload:
        return database_payload

    cache_key = _cache_key(patient)

    if not cache_key:
        return None

    cache_entry = _load_cache().get(cache_key)

    if not cache_entry:
        return None

    if cache_entry.get("fingerprint") != _patient_fingerprint(patient):
        return None

    file_payload = cache_entry.get("payload")

    if file_payload and database_enabled():
        _save_cached_to_database(patient, file_payload)

    return file_payload


def _set_cached_llm_operational(patient, payload):
    if _save_cached_to_database(patient, payload):
        return

    cache_key = _cache_key(patient)

    if not cache_key:
        return

    with _CACHE_LOCK:
        cache_data = _load_cache()
        cache_data[cache_key] = {
            "fingerprint": _patient_fingerprint(patient),
            "payload": payload,
        }
        _save_cache(cache_data)


def _prompt_payload(patient):
    return _patient_cache_payload(patient)


def _build_messages(patient):
    prompt_payload = json.dumps(_prompt_payload(patient), ensure_ascii=True, indent=2)
    schema_text = json.dumps(LLM_OUTPUT_SCHEMA, ensure_ascii=True, separators=(",", ":"))

    system_text = (
        "You are a hospital admission intelligence assistant. "
        "Return only valid JSON with no markdown fences or extra prose. "
        "The JSON must follow the requested schema exactly. "
        "Infer fields from the patient record itself, not generic templates. "
        "Be conservative, evidence-based, and traceable. "
        "For every extracted diagnosis, symptom, or history item, cite a source section and short evidence snippet. "
        "For financial and operational fields, make a best-effort estimate from the case complexity, urgency, and treatment burden. "
        "Do not mention that you are using a rule-based or fallback system."
    )

    user_text = (
        "Generate hospital admission intelligence for this patient record.\n\n"
        "Important expectations:\n"
        "- Use source-aware extraction for ICD-10, comorbidities, symptoms, and history.\n"
        "- Provide practical operational outputs such as revenue, LOS, readmission risk, deferability, and admission conversion probability.\n"
        "- Keep normalized summaries concise and professional.\n"
        "- Keep timeline stages chronological and specific.\n"
        "- Use only information reasonably supported by the record.\n"
        "- If a field is unknown, return an empty list, empty string, or best conservative estimate that matches the schema.\n\n"
        f"Required JSON schema:\n{schema_text}\n\n"
        f"Patient record:\n{prompt_payload}"
    )

    return [
        {"role": "system", "content": system_text},
        {"role": "user", "content": user_text},
    ]


def _parse_json_content(content):
    cleaned = (content or "").strip()

    if not cleaned:
        raise ValueError("LLM response content was empty.")

    if cleaned.startswith("```"):
        cleaned = cleaned.replace("```json", "", 1).replace("```", "").strip()

    if "{" in cleaned and "}" in cleaned:
        cleaned = cleaned[cleaned.find("{") : cleaned.rfind("}") + 1]

    return json.loads(cleaned)


def generate_llm_operational(patient):
    client = _get_client()
    provider = get_provider_name()

    if client is None:
        _set_last_llm_error(
            "LLM client could not be initialized. Check provider env vars and package installation."
        )
        return None

    response = client.chat.completions.create(
        model=get_model_name(),
        messages=_build_messages(patient),
        temperature=get_temperature(),
        max_tokens=get_max_tokens(),
        response_format={"type": "json_object"},
    )

    if not getattr(response, "choices", None):
        _set_last_llm_error(f"{provider} response did not contain choices.")
        return None

    content = response.choices[0].message.content if response.choices[0].message else ""

    if not content:
        _set_last_llm_error(f"{provider} response did not contain message content.")
        return None

    payload = _parse_json_content(content)
    _set_last_llm_error(None)
    _set_cached_llm_operational(patient, payload)
    return payload


def maybe_generate_llm_operational(patient, llm_allowed=False, allow_live_generation=False):
    if not llm_feature_enabled() or not llm_allowed:
        return None

    cached_payload = get_cached_llm_operational(patient)

    if cached_payload:
        return cached_payload

    if not allow_live_generation:
        return None

    try:
        return generate_llm_operational(patient)
    except Exception as exc:
        _set_last_llm_error(f"{type(exc).__name__}: {exc}")
        return None


def merge_operational_payloads(base_payload, llm_payload):
    if not llm_payload:
        return base_payload

    merged = dict(base_payload)

    for key, value in llm_payload.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = {**merged[key], **value}
        else:
            merged[key] = value

    return merged
