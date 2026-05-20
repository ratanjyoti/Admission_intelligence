import json
import re
from collections import defaultdict
from functools import lru_cache
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
REFERENCE_DIR = ROOT_DIR / "data" / "reference"
PACKAGE_DATA_PATH = REFERENCE_DIR / "hospital_packages.json"
BED_RATES_PATH = REFERENCE_DIR / "bed_rates.json"
INVESTIGATION_RATES_PATH = REFERENCE_DIR / "investigation_rates.json"
NPPA_MEDICINE_PRICES_PATH = REFERENCE_DIR / "nppa_medicine_prices.json"
MEDICINE_PRICES_PATH = REFERENCE_DIR / "medicine_prices.json"

DEFAULT_BED_RATES = {
    "ICU": 25000,
    "HDU": 18000,
    "General Ward": 7500,
    "Daycare": 4500,
    "Emergency Observation": 12000,
}

DEFAULT_INVESTIGATION_RATES = {
    "cbc": 800,
    "renal function test": 1400,
    "liver function test": 1600,
    "electrolytes": 1200,
    "ecg": 900,
    "echocardiogram": 4500,
    "chest x-ray": 1200,
    "ct scan": 8000,
    "mri": 18000,
    "blood culture": 1700,
    "urine culture": 900,
    "dialysis": 4500,
    "ventilator support": 12000,
    "oxygen therapy": 2400,
    "pathology panel": 3500,
    "histopathology": 4800,
    "biopsy": 7500,
}

DEFAULT_MEDICINE_PRICES = [
    {
        "name": "Levera",
        "keywords": ["levera", "levetiracetam"],
        "unitPrice": 90,
        "unit": "tablet",
    },
    {
        "name": "Telma",
        "keywords": ["telma", "telmisartan"],
        "unitPrice": 25,
        "unit": "tablet",
    },
    {
        "name": "Pantoprazole",
        "keywords": ["pantoprazole", "pantoprazole sodium"],
        "unitPrice": 12,
        "unit": "tablet",
    },
    {
        "name": "Ceftriaxone",
        "keywords": ["ceftriaxone", "cephalosporin"],
        "unitPrice": 55,
        "unit": "injection",
    },
    {
        "name": "Insulin",
        "keywords": ["insulin"],
        "unitPrice": 180,
        "unit": "vial",
    },
    {
        "name": "Diltiazem",
        "keywords": ["diltiazem"],
        "unitPrice": 35,
        "unit": "tablet",
    },
]

PACKAGE_KEYWORDS = {
    "Transplant": ["transplant", "renal transplant", "bone marrow"],
    "ICU": ["icu", "ventilator", "intensive care", "critical care"],
    "Emergency": ["emergency", "shock", "sepsis", "acute"],
    "Surgery": ["surgery", "laparotomy", "arthroplasty", "appendectomy"],
}

TOKEN_SPLIT_RE = re.compile(r"[^a-z0-9]+")
TOKEN_STOPWORDS = {
    "with",
    "from",
    "that",
    "this",
    "have",
    "were",
    "been",
    "patient",
    "acute",
    "severe",
    "chronic",
    "required",
    "admission",
    "exacerbation",
    "without",
    "routine",
    "ward",
    "package",
    "care",
    "general",
    "procedure",
    "disease",
}
MEDICINE_WEAK_TOKENS = {
    "acid",
    "tablet",
    "tablets",
    "injection",
    "capsule",
    "capsules",
    "syrup",
    "oral",
    "solution",
    "price",
    "revised",
    "unit",
    "dose",
    "with",
    "without",
    "salt",
    "release",
    "powder",
    "mg",
    "ml",
}


def _load_json_file(path: Path, fallback: Any):
    try:
        if path.exists():
            with path.open("r", encoding="utf-8") as file:
                return json.load(file)
    except (json.JSONDecodeError, OSError):
        pass
    return fallback


def _file_signature(path: Path) -> int:
    try:
        if path.exists():
            return int(path.stat().st_mtime_ns)
    except OSError:
        pass
    return -1


def _load_first_available_json(paths: list[Path], fallback: Any) -> tuple[Any, Path | None]:
    for path in paths:
        loaded = _load_json_file(path, None)
        if loaded not in (None, [], {}):
            return loaded, path
    return fallback, None


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        value = str(value)
    return re.sub(r"\s+", " ", value.strip().lower())


def extract_text_tokens(text: str, min_length: int = 4) -> set[str]:
    if not text:
        return set()

    tokens = {
        token
        for token in TOKEN_SPLIT_RE.split(text)
        if len(token) >= min_length and token and token not in TOKEN_STOPWORDS
    }
    return tokens


@lru_cache(maxsize=1)
def load_hospital_packages():
    return _load_json_file(PACKAGE_DATA_PATH, [])


@lru_cache(maxsize=1)
def load_bed_rates():
    return _load_json_file(BED_RATES_PATH, DEFAULT_BED_RATES)


@lru_cache(maxsize=1)
def load_investigation_rates():
    return _load_json_file(INVESTIGATION_RATES_PATH, DEFAULT_INVESTIGATION_RATES)


def _medicine_reference_paths() -> list[Path]:
    # Prefer NPPA extraction output directly. Keep legacy mirror as fallback.
    return [NPPA_MEDICINE_PRICES_PATH, MEDICINE_PRICES_PATH]


@lru_cache(maxsize=8)
def _load_medicine_prices_cached(nppa_signature: int, mirror_signature: int):
    medicines, _ = _load_first_available_json(_medicine_reference_paths(), DEFAULT_MEDICINE_PRICES)
    return medicines


def load_medicine_prices():
    return _load_medicine_prices_cached(
        _file_signature(NPPA_MEDICINE_PRICES_PATH),
        _file_signature(MEDICINE_PRICES_PATH),
    )


def get_reference_data_signature() -> tuple[int, int, int, int, int]:
    return (
        _file_signature(PACKAGE_DATA_PATH),
        _file_signature(BED_RATES_PATH),
        _file_signature(INVESTIGATION_RATES_PATH),
        _file_signature(NPPA_MEDICINE_PRICES_PATH),
        _file_signature(MEDICINE_PRICES_PATH),
    )


def get_reference_data_status() -> dict[str, Any]:
    packages = load_hospital_packages()
    bed_rates = load_bed_rates()
    investigation_rates = load_investigation_rates()
    medicine_prices = load_medicine_prices()
    _, active_medicine_path = _load_first_available_json(_medicine_reference_paths(), DEFAULT_MEDICINE_PRICES)
    active_medicine_path = active_medicine_path or MEDICINE_PRICES_PATH

    return {
        "hospitalPackages": {
            "path": str(PACKAGE_DATA_PATH),
            "exists": PACKAGE_DATA_PATH.exists(),
            "count": len(packages) if isinstance(packages, list) else 0,
            "sourceMode": "official" if PACKAGE_DATA_PATH.exists() and bool(packages) else "fallback",
        },
        "bedRates": {
            "path": str(BED_RATES_PATH),
            "exists": BED_RATES_PATH.exists(),
            "count": len(bed_rates) if isinstance(bed_rates, dict) else 0,
            "sourceMode": (
                "official"
                if BED_RATES_PATH.exists() and bed_rates != DEFAULT_BED_RATES
                else "fallback"
            ),
        },
        "investigationRates": {
            "path": str(INVESTIGATION_RATES_PATH),
            "exists": INVESTIGATION_RATES_PATH.exists(),
            "count": len(investigation_rates) if isinstance(investigation_rates, dict) else 0,
            "sourceMode": (
                "official"
                if INVESTIGATION_RATES_PATH.exists()
                and investigation_rates != DEFAULT_INVESTIGATION_RATES
                else "fallback"
            ),
        },
        "medicinePrices": {
            "path": str(active_medicine_path),
            "exists": active_medicine_path.exists(),
            "count": len(medicine_prices) if isinstance(medicine_prices, list) else 0,
            "sourceMode": (
                "official"
                if active_medicine_path.exists() and medicine_prices != DEFAULT_MEDICINE_PRICES
                else "fallback"
            ),
            "nppaPath": str(NPPA_MEDICINE_PRICES_PATH),
            "nppaExists": NPPA_MEDICINE_PRICES_PATH.exists(),
            "mirrorPath": str(MEDICINE_PRICES_PATH),
            "mirrorExists": MEDICINE_PRICES_PATH.exists(),
        },
    }


def _contains_keyword(text: str, keywords: list[str]) -> bool:
    return any(normalize_text(keyword) in text for keyword in keywords)


@lru_cache(maxsize=1)
def load_package_search_index():
    packages = load_hospital_packages()
    entries: list[dict[str, Any]] = []
    token_index: dict[str, list[int]] = defaultdict(list)
    case_type_index: dict[str, list[int]] = defaultdict(list)
    bed_type_index: dict[str, list[int]] = defaultdict(list)
    admission_type_index: dict[str, list[int]] = defaultdict(list)
    specialty_index: dict[str, list[int]] = defaultdict(list)
    category_index: dict[str, list[int]] = defaultdict(list)

    for index, package in enumerate(packages):
        package_name_text = normalize_text(package.get("packageName", ""))
        package_description_text = normalize_text(package.get("description", ""))
        package_text = f"{package_name_text} {package_description_text}".strip()
        package_code = normalize_text(package.get("packageCode", ""))
        package_category = normalize_text(package.get("category", ""))

        case_types = {normalize_text(value) for value in package.get("caseTypes", []) if normalize_text(value)}
        bed_types = {normalize_text(value) for value in package.get("bedTypes", []) if normalize_text(value)}
        admission_types = {
            normalize_text(value)
            for value in package.get("admissionTypes", [])
            if normalize_text(value)
        }
        specialties = {normalize_text(value) for value in package.get("specialties", []) if normalize_text(value)}

        name_tokens = extract_text_tokens(package_name_text)
        description_tokens = extract_text_tokens(package_description_text)
        package_tokens = name_tokens | description_tokens

        index_tokens = set(name_tokens)
        if len(index_tokens) < 6:
            for token in description_tokens:
                index_tokens.add(token)
                if len(index_tokens) >= 6:
                    break

        for token in index_tokens:
            token_index[token].append(index)

        for value in case_types:
            case_type_index[value].append(index)
        for value in bed_types:
            bed_type_index[value].append(index)
        for value in admission_types:
            admission_type_index[value].append(index)
        for value in specialties:
            specialty_index[value].append(index)
        if package_category:
            category_index[package_category].append(index)

        entries.append(
            {
                "package": package,
                "package_name_text": package_name_text,
                "package_text": package_text,
                "package_code": package_code,
                "package_category": package_category,
                "case_types": case_types,
                "bed_types": bed_types,
                "admission_types": admission_types,
                "specialties": specialties,
                "name_tokens": name_tokens,
                "package_tokens": package_tokens,
                "is_health_check": "health check" in package_text or package_code.startswith("cghs-hc"),
                "is_lab_or_radio": package_code.startswith(("cghs-lb", "cghs-ri")),
            }
        )

    return {
        "entries": entries,
        "token_index": dict(token_index),
        "case_type_index": dict(case_type_index),
        "bed_type_index": dict(bed_type_index),
        "admission_type_index": dict(admission_type_index),
        "specialty_index": dict(specialty_index),
        "category_index": dict(category_index),
    }


@lru_cache(maxsize=8)
def _load_medicine_match_index_cached(nppa_signature: int, mirror_signature: int):
    medicines = load_medicine_prices()
    entries: list[dict[str, Any]] = []
    keyword_index: dict[str, list[int]] = defaultdict(list)

    for medicine in medicines:
        unit_price = medicine.get("unitPrice")
        if unit_price is None:
            unit_price = medicine.get("ceilingPrice", 0)
        try:
            parsed_price = float(unit_price or 0)
        except (TypeError, ValueError):
            continue

        if parsed_price <= 0:
            continue

        name = normalize_text(medicine.get("medicineName") or medicine.get("name") or "")
        keywords = {
            normalize_text(keyword)
            for keyword in medicine.get("keywords", [])
            if normalize_text(keyword)
            and len(normalize_text(keyword)) >= 4
            and normalize_text(keyword) not in MEDICINE_WEAK_TOKENS
        }

        if not name and not keywords:
            continue

        entry_index = len(entries)
        entries.append(
            {
                "name": name,
                "keywords": keywords,
                "price": parsed_price,
            }
        )

        for keyword in keywords:
            keyword_index[keyword].append(entry_index)

    return {"entries": entries, "keyword_index": dict(keyword_index)}


def load_medicine_match_index():
    return _load_medicine_match_index_cached(
        _file_signature(NPPA_MEDICINE_PRICES_PATH),
        _file_signature(MEDICINE_PRICES_PATH),
    )


def find_candidate_packages(patient: dict[str, Any], signals: dict[str, bool], case_type: str) -> list[dict[str, Any]]:
    text_fields = " ".join(
        [
            str(patient.get("department", "")),
            str(patient.get("doctorName", "")),
            str(patient.get("clinical", {}).get("diagnosis", "")),
            str(patient.get("clinical", {}).get("clinicalNotes", "")),
            str(patient.get("clinical", {}).get("physicalRemarks", "")),
            str(patient.get("clinical", {}).get("medicineDetails", "")),
            str(patient.get("admission", {}).get("type", "")),
            str(patient.get("bed", {}).get("type", "")),
        ]
    )
    text = normalize_text(text_fields)
    clinical_text = normalize_text(
        " ".join(
            [
                str(patient.get("clinical", {}).get("diagnosis", "")),
                str(patient.get("clinical", {}).get("clinicalNotes", "")),
                str(patient.get("clinical", {}).get("physicalRemarks", "")),
                str(patient.get("clinical", {}).get("investigations", "")),
                str(patient.get("clinical", {}).get("medicineDetails", "")),
            ]
        )
    )
    diagnosis_tokens = extract_text_tokens(clinical_text)

    package_index = load_package_search_index()
    entries = package_index["entries"]
    token_index = package_index["token_index"]
    case_type_index = package_index["case_type_index"]
    bed_type_index = package_index["bed_type_index"]
    admission_type_index = package_index["admission_type_index"]
    specialty_index = package_index["specialty_index"]
    category_index = package_index["category_index"]

    normalized_case_type = normalize_text(case_type)
    bed_type = normalize_text(patient.get("bed", {}).get("type", ""))
    admission_type = normalize_text(patient.get("admission", {}).get("type", ""))

    has_major_keyword_match = False
    if signals.get("major_procedure"):
        has_major_keyword_match = any(_contains_keyword(text, keywords) for keywords in PACKAGE_KEYWORDS.values())

    has_transplant = "transplant" in text
    has_icu_keyword = any(keyword in text for keyword in ("ventilator", "iccu", "icu"))
    has_surgery_keyword = any(keyword in text for keyword in ("surgery", "laparotomy", "arthroplasty", "appendectomy"))

    candidate_indices: set[int] = set()
    if normalized_case_type:
        candidate_indices.update(case_type_index.get(normalized_case_type, []))
    if bed_type:
        candidate_indices.update(bed_type_index.get(bed_type, []))
    if admission_type:
        candidate_indices.update(admission_type_index.get(admission_type, []))

    for token in diagnosis_tokens:
        candidate_indices.update(token_index.get(token, []))

    if signals.get("renal"):
        candidate_indices.update(specialty_index.get("renal", []))
    if signals.get("oncology"):
        candidate_indices.update(specialty_index.get("oncology", []))
    if signals.get("cardiac"):
        candidate_indices.update(specialty_index.get("cardiac", []))
    if signals.get("respiratory"):
        candidate_indices.update(specialty_index.get("critical care", []))

    if len(candidate_indices) < 200:
        candidate_indices.update(category_index.get("pm-jay/hbp", []))

    if not candidate_indices:
        candidate_indices = set(range(len(entries)))

    matches: list[tuple[int, dict[str, Any]]] = []

    for package_index_value in candidate_indices:
        entry = entries[package_index_value]
        package = entry["package"]
        score = 0
        package_case_types = entry["case_types"]
        package_bed_types = entry["bed_types"]
        package_admission_types = entry["admission_types"]
        package_specialties = entry["specialties"]
        package_name_text = entry["package_name_text"]
        package_tokens = entry["package_tokens"]
        package_code = entry["package_code"]
        package_category = entry["package_category"]

        if normalized_case_type in package_case_types:
            score += 5

        if bed_type and bed_type in package_bed_types:
            score += 3

        if admission_type and admission_type in package_admission_types:
            score += 2

        if has_major_keyword_match:
            score += 3

        if signals.get("renal") and "renal" in package_specialties:
            score += 2
        if signals.get("oncology") and "oncology" in package_specialties:
            score += 2
        if signals.get("cardiac") and "cardiac" in package_specialties:
            score += 2
        if signals.get("respiratory") and "critical care" in package_specialties:
            score += 1

        if has_transplant:
            if "transplant" in package_specialties:
                score += 5
            else:
                score -= 2

        if has_icu_keyword:
            if "icu" in package_bed_types or "icu" in package_name_text:
                score += 4

        if has_surgery_keyword:
            if "surgical" in package_case_types or "surgery" in package_name_text:
                score += 4

        name_token_hits = len(diagnosis_tokens & entry["name_tokens"])
        desc_token_hits = len(diagnosis_tokens & package_tokens)

        if name_token_hits > 0:
            score += min(16, name_token_hits * 5)
        elif desc_token_hits > 0:
            score += min(8, desc_token_hits * 2)

        if package_code and package_code in text:
            score += 8

        if package_category == "pm-jay/hbp":
            score += 2

        if entry["is_health_check"]:
            score -= 12

        if entry["is_lab_or_radio"] and name_token_hits == 0 and not signals.get("major_procedure"):
            score -= 3

        matches.append((score, package))

    ranked = sorted(matches, key=lambda item: (-item[0], float(item[1].get("basePrice", 0) or 0)))
    if not ranked:
        return []

    non_negative_ranked = [item[1] for item in ranked if item[0] >= 0]
    if non_negative_ranked:
        return non_negative_ranked

    # If heuristic scoring is strict for a specific narrative, still use the top
    # official package candidate rather than dropping to a synthetic fallback row.
    return [ranked[0][1]]


def infer_treatment_bundle(patient: dict[str, Any], signals: dict[str, bool], case_type: str) -> dict[str, Any]:
    candidates = find_candidate_packages(patient, signals, case_type)
    if candidates:
        selected = candidates[0]
    else:
        fallback = next((pkg for pkg in load_hospital_packages() if pkg.get("category") == "Standard Value"), None)
        selected = fallback or {
            "packageCode": "CGHS-UNKNOWN",
            "packageName": "General Admission Package",
            "specialties": ["General Medicine"],
            "caseTypes": [case_type],
            "admissionTypes": ["Elective", "Urgent", "Emergency"],
            "bedTypes": ["General Ward"],
            "basePrice": 90000,
            "typicalLengthOfStayDays": 3,
            "category": "Standard Value",
            "description": "Fallback general admission package.",
            "source": "Fallback generated package",
            "matchedProcedures": ["CGHS-UNKNOWN"],
        }

    return {
        "packageCode": selected.get("packageCode"),
        "packageName": selected.get("packageName"),
        "category": selected.get("category"),
        "caseTypes": selected.get("caseTypes", []),
        "admissionTypes": selected.get("admissionTypes", []),
        "bedTypes": selected.get("bedTypes", []),
        "specialties": selected.get("specialties", []),
        "basePrice": selected.get("basePrice", 0),
        "description": selected.get("description", ""),
        "typicalLengthOfStayDays": selected.get("typicalLengthOfStayDays", 3),
        "source": selected.get("source", "Official package references"),
        "matchedProcedures": selected.get("matchedProcedures", [selected.get("packageCode")]),
        "pricingModel": selected.get("pricingModel", "tier_package"),
        "officialRateBreakdown": selected.get("officialRateBreakdown", {}),
        "routineWardRate": selected.get("routineWardRate"),
        "hduRate": selected.get("hduRate"),
        "icuRate": selected.get("icuRate"),
        "icuVentilatorRate": selected.get("icuVentilatorRate"),
    }


def estimate_bed_rate(bed_type: str) -> int:
    rates = load_bed_rates()
    normalized = normalize_text(bed_type)
    for key, value in rates.items():
        if normalize_text(key) == normalized:
            return int(value)
    return int(rates.get("General Ward", 7500))


def estimate_medicine_cost(patient: dict[str, Any]) -> int:
    text = normalize_text(
        " ".join(
            [
                patient.get("clinical", {}).get("medicineDetails", ""),
                patient.get("clinical", {}).get("diagnosis", ""),
                patient.get("clinical", {}).get("clinicalNotes", ""),
            ]
        )
    )
    medicine_index = load_medicine_match_index()
    medicine_entries = medicine_index["entries"]
    keyword_index = medicine_index["keyword_index"]
    patient_tokens = extract_text_tokens(text)

    candidate_indices: set[int] = set()
    for token in patient_tokens:
        candidate_indices.update(keyword_index.get(token, []))

    if not candidate_indices:
        return 1200

    matched_unit_prices: list[float] = []
    for entry_index in candidate_indices:
        entry = medicine_entries[entry_index]
        medicine_name = entry["name"]
        keyword_hits = len(entry["keywords"] & patient_tokens)
        if (medicine_name and medicine_name in text) or keyword_hits >= 2:
            matched_unit_prices.append(entry["price"])

    if matched_unit_prices:
        top_prices = sorted(matched_unit_prices, reverse=True)[:6]
        # Use NPPA unit prices directly for matched medicines so official PDF
        # updates immediately influence revenue estimation.
        cost = int(round(sum(price * 5 for price in top_prices)))
        return max(cost, 0)

    return 1200


def estimate_investigation_cost(patient: dict[str, Any]) -> int:
    text = normalize_text(
        " ".join(
            [
                patient.get("clinical", {}).get("investigations", ""),
                patient.get("clinical", {}).get("clinicalNotes", ""),
                patient.get("clinical", {}).get("diagnosis", ""),
            ]
        )
    )
    rates = load_investigation_rates()
    cost = 0
    for key, price in rates.items():
        if normalize_text(key) in text:
            cost += int(price)
    if cost == 0:
        return 4500
    return max(cost, 1200)


def estimate_consumables_cost(patient: dict[str, Any], signals: dict[str, bool]) -> int:
    text = normalize_text(
        " ".join(
            [
                patient.get("clinical", {}).get("physicalRemarks", ""),
                patient.get("clinical", {}).get("vitalRemarks", ""),
                patient.get("clinical", {}).get("clinicalNotes", ""),
            ]
        )
    )
    consumables = 0
    if "ventilator" in text or signals.get("icu"):
        consumables += 25000
    if signals.get("infection"):
        consumables += 8000
    if "transplant" in text:
        consumables += 45000
    return consumables


def estimate_length_of_stay(patient: dict[str, Any], length_of_stay_payload: dict[str, Any] | None = None) -> int:
    if length_of_stay_payload:
        high_days = length_of_stay_payload.get("highDays")
        if isinstance(high_days, (int, float)) and high_days > 0:
            return int(high_days)
    journey_visits = patient.get("journey", {}).get("visitCount")
    try:
        return max(1, int(journey_visits or 3))
    except (TypeError, ValueError):
        return 3


__all__ = [
    "infer_treatment_bundle",
    "estimate_bed_rate",
    "estimate_medicine_cost",
    "estimate_investigation_cost",
    "estimate_consumables_cost",
    "estimate_length_of_stay",
    "get_reference_data_status",
    "get_reference_data_signature",
]
