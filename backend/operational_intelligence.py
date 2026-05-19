import ast
import copy
import os
import re
from datetime import datetime
from urllib.parse import unquote

from backend.agentic.mapper import safe_merge_agentic_into_operational
from backend.agentic.orchestrator import run_agentic_patient_pipeline
from backend.llm_intelligence import (
    maybe_generate_llm_operational,
    merge_operational_payloads,
)

PRIORITY_RISK_POINTS = {"Critical": 50, "High": 32, "Medium": 16, "Low": 6}
PRIORITY_ADMISSION_POINTS = {"Emergency": 28, "Urgent": 18, "Elective": 8}
PRIORITY_BED_POINTS = {"ICU": 24, "HDU": 16, "General Oncology Ward": 12}
PRIORITY_READMISSION_POINTS = {"High": 12, "Medium": 6, "Low": 2}
PRIORITY_DEFERRED_POINTS = {
    "Cannot be safely delayed": 20,
    "24-48 hours only": 12,
    "3-5 days acceptable": 5,
    "1-2 weeks acceptable": 1,
}
PRIORITY_RISK_ORDER = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}
PRIORITY_ADMISSION_ORDER = {"Emergency": 0, "Urgent": 1, "Elective": 2}


def should_use_agentic_risk():
    return os.getenv("AGENTIC_RISK_ENABLED", "false").strip().lower() == "true"


MAJOR_PROCEDURE_KEYWORDS = [
    "transplant",
    "bone marrow",
    "cabg",
    "angioplasty",
    "laparotomy",
    "reconstruction",
    "hernia repair",
    "cholecystectomy",
]

SURGICAL_KEYWORDS = MAJOR_PROCEDURE_KEYWORDS + [
    "surgery",
    "appendectomy",
    "biopsy",
    "endoscopy",
    "colonoscopy",
    "stent",
]

DAYCARE_KEYWORDS = [
    "daycare",
    "day care",
    "phaco",
    "cataract",
    "infusion",
    "transfusion",
    "chemo",
    "chemotherapy",
]

RENAL_KEYWORDS = [
    "renal",
    "kidney",
    "creat",
    "creatinine",
    "dialysis",
    "nephro",
    "nephropathy",
    "ckd",
    "transplant",
]

ONCOLOGY_KEYWORDS = [
    "oncology",
    "lymphoma",
    "rituximab",
    "chemotherapy",
    "bone marrow",
    "cancer",
    "metastatic",
]

RESPIRATORY_KEYWORDS = [
    "asthma",
    "copd",
    "retractions",
    "breathlessness",
    "ventilator",
    "nebulization",
    "respiratory",
]

ORTHOPEDIC_KEYWORDS = [
    "orthopedic",
    "orthopaedic",
    "fracture",
    "tkr",
    "thr",
    "arthroplasty",
    "osteoarthritis",
    "knee replacement",
    "hip replacement",
    "laminectomy",
    "discectomy",
    "lumbar canal stenosis",
    "rotator cuff",
    "tendinopathy",
]

INFECTION_KEYWORDS = [
    "infection",
    "fever",
    "sepsis",
    "e coli",
    "klebsiella",
    "uti",
    "antibiotic",
]

CARDIAC_KEYWORDS = [
    "cardiac",
    "heart block",
    "cabg",
    "angioplasty",
    "pacing",
    "arrhythmia",
]

NEURO_KEYWORDS = [
    "seizure",
    "epile",
    "migraine",
    "encephalopathy",
    "neurolog",
    "gtcs",
]

ICD10_RULES = [
    {"code": "N18.6", "label": "End stage renal disease", "keywords": ["esrd", "end stage renal", "started on hd", "hemodialysis", "haemodialysis", "dialysis"]},
    {"code": "N18.9", "label": "Chronic kidney disease, unspecified", "keywords": ["ckd", "ckdvd", "renal dysfunction", "kidney disease", "creatinine", "egfr"]},
    {"code": "E11.21", "label": "Type 2 diabetes mellitus with diabetic nephropathy", "keywords": ["diabetic kidney disease", "diabetic nephropathy", "dm nephropathy", "nephropathy"]},
    {"code": "E11.9", "label": "Type 2 diabetes mellitus without complications", "keywords": ["diabetes mellitus", "type ii diabetes", "dm on treatment", "diabetic"]},
    {"code": "I10", "label": "Essential hypertension", "keywords": ["hypertension", "high bp", "htn"]},
    {"code": "B18.1", "label": "Chronic viral hepatitis B without delta-agent", "keywords": ["hbv", "hepatitis b", "chronic hbv"]},
    {"code": "D64.9", "label": "Anemia, unspecified", "keywords": ["anemia", "anaemia", "hb-", "pallor"]},
    {"code": "C85.80", "label": "Marginal zone lymphoma, unspecified site", "keywords": ["marginal zone lymphoma", "marzinal zone lymphoma", "marginal lymphoma"]},
    {"code": "C90.00", "label": "Multiple myeloma not having achieved remission", "keywords": ["multiple myeloma", "myeloma"]},
    {"code": "G40.901", "label": "Epilepsy, unspecified, not intractable, with status epilepticus", "keywords": ["status epilepticus", "gtcs", "seizure"]},
    {"code": "G43.901", "label": "Migraine, unspecified, not intractable, with status migrainosus", "keywords": ["status migraine", "migraine"]},
    {"code": "I44.2", "label": "Atrioventricular block, complete", "keywords": ["complete heart block", "heart block"]},
    {"code": "I25.10", "label": "Atherosclerotic heart disease of native coronary artery without angina", "keywords": ["coronary artery disease", "cad", "ptca"]},
    {"code": "I50.9", "label": "Heart failure, unspecified", "keywords": ["heart failure"]},
    {"code": "J44.9", "label": "Chronic obstructive pulmonary disease, unspecified", "keywords": ["copd"]},
    {"code": "J45.909", "label": "Unspecified asthma, uncomplicated", "keywords": ["asthma"]},
    {"code": "G47.33", "label": "Obstructive sleep apnea", "keywords": ["osa", "sleep apnea", "cpap"]},
    {"code": "E03.9", "label": "Hypothyroidism, unspecified", "keywords": ["hypothyroid", "hypothyroidism"]},
    {"code": "Q61.2", "label": "Polycystic kidney, adult type", "keywords": ["adpkd", "polycystic kidney"]},
    {"code": "M45.9", "label": "Ankylosing spondylitis of unspecified sites in spine", "keywords": ["ankylosing spondylitis"]},
    {"code": "N39.0", "label": "Urinary tract infection, site not specified", "keywords": ["uti", "urine c/s", "e coli", "klebsiella"]},
    {"code": "E87.5", "label": "Hyperkalemia", "keywords": ["hyperkalemia", "high potassium", "k-5", "k -5", "potassium"]},
    {"code": "C06.9", "label": "Malignant neoplasm of mouth, unspecified", "keywords": ["oral cavity", "buccal mucosa", "osmf", "masticator space"]},
    {"code": "K64.9", "label": "Hemorrhoids, unspecified", "keywords": ["haemorrhoids", "hemorrhoids", "pile", "anopexy"]},
    {"code": "K85.9", "label": "Acute pancreatitis, unspecified", "keywords": ["pancreatitis"]},
]

COMORBIDITY_RULES = [
    {"label": "Diabetes mellitus", "keywords": ["diabetes mellitus", "diabetes", "dm "]},
    {"label": "Hypertension", "keywords": ["hypertension", "htn", "high bp"]},
    {"label": "Chronic kidney disease", "keywords": ["ckd", "renal dysfunction", "kidney disease", "creatinine"]},
    {"label": "Diabetic nephropathy", "keywords": ["diabetic kidney disease", "diabetic nephropathy", "nephropathy"]},
    {"label": "Chronic hepatitis B", "keywords": ["hbv", "hepatitis b", "chronic hbv"]},
    {"label": "Anemia", "keywords": ["anemia", "anaemia", "pallor"]},
    {"label": "Coronary artery disease", "keywords": ["coronary artery disease", "cad", "ptca"]},
    {"label": "Complete heart block", "keywords": ["complete heart block", "heart block"]},
    {"label": "Obstructive sleep apnea", "keywords": ["osa", "cpap", "sleep apnea"]},
    {"label": "Hypothyroidism", "keywords": ["hypothyroid", "hypothyroidism"]},
    {"label": "Renal transplant status", "keywords": ["renal transplant", "transplant", "lrtt"]},
    {"label": "Lymphoma", "keywords": ["lymphoma", "rituximab"]},
    {"label": "Epilepsy / seizure disorder", "keywords": ["seizure", "status epilepticus", "gtcs", "keppra", "levera"]},
    {"label": "Migraine disorder", "keywords": ["migraine"]},
    {"label": "Chronic obstructive airway disease", "keywords": ["copd", "asthma"]},
    {"label": "Recurrent urinary tract infection", "keywords": ["urine c/s", "e coli", "klebsiella", "uti"]},
    {"label": "Hyperkalemia", "keywords": ["high potassium", "hyperkalemia", "k-5", "k -5"]},
    {"label": "Ankylosing spondylitis", "keywords": ["ankylosing spondylitis"]},
]

SYMPTOM_RULES = [
    {"label": "Vomiting", "keywords": ["vomiting", "vomitings", "emesis"]},
    {"label": "Seizure activity", "keywords": ["seizure", "status epilepticus", "gtcs"]},
    {"label": "Headache / migraine", "keywords": ["migraine", "headache"]},
    {"label": "Breathlessness", "keywords": ["breathlessness", "decrease breath sound", "spo2", "shortness of breath"]},
    {"label": "Abdominal pain / surgical swelling", "keywords": ["abdominal", "swelling", "hernia", "cough impulse"]},
    {"label": "Oliguria / low urine output", "keywords": ["urine output", "oliguria", "residual urine"]},
    {"label": "Edema / fluid overload", "keywords": ["edema", "oedema", "fluid overload"]},
    {"label": "Fever / infection concern", "keywords": ["fever", "infection", "uti"]},
    {"label": "Weakness / anemia symptoms", "keywords": ["pallor", "anemia", "anaemia"]},
    {"label": "Bleeding / blood loss concern", "keywords": ["bleed", "rbc", "hematuria", "blood"]},
]

SURGERY_HISTORY_RULES = [
    {"label": "Renal transplant", "keywords": ["renal transplant", "lrtt", "transplant"]},
    {"label": "PTCA / coronary intervention", "keywords": ["ptca", "angioplasty"]},
    {"label": "Total knee replacement", "keywords": ["tkr"]},
    {"label": "Total hip replacement", "keywords": ["thr"]},
    {"label": "Laparotomy", "keywords": ["laparotomy"]},
    {"label": "Appendix surgery", "keywords": ["appendix", "appendectomy"]},
    {"label": "Bone marrow transplant", "keywords": ["bone marrow transplant", "stem cell transplant"]},
    {"label": "AV fistula procedure", "keywords": ["avf", "av fistula", "rc avf"]},
]

REFUSAL_KEYWORDS = [
    "refused",
    "declined",
    "did not return",
    "non compliant",
    "non-compliant",
    "not willing",
]

NOT_AVAILABLE_VALUES = {
    "",
    "-",
    "not available",
    "not explicitly mentioned",
    "not needed - explicit procedure available",
}


def clean_text(value):
    if value is None:
        return ""

    text = unquote(str(value)).replace("\u00a0", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def lower_text(value):
    return clean_text(value).lower()


def non_empty_text(value):
    normalized = lower_text(value)
    return normalized not in NOT_AVAILABLE_VALUES


def combine_patient_text(patient):
    clinical = patient.get("clinical", {})
    traceability = patient.get("traceability", {})
    procedure = patient.get("procedure", {})

    parts = [
        patient.get("department"),
        patient.get("doctorName"),
        patient.get("customerType"),
        patient.get("risk", {}).get("reasoning"),
        patient.get("admission", {}).get("reasoning"),
        patient.get("bed", {}).get("reasoning"),
        procedure.get("explicitProcedure"),
        procedure.get("inferredProcedure"),
        procedure.get("explicitSource"),
        clinical.get("diagnosis"),
        clinical.get("clinicalNotes"),
        clinical.get("physicalRemarks"),
        clinical.get("vitalRemarks"),
        clinical.get("investigations"),
        clinical.get("doctorAdvice"),
        clinical.get("medicineDetails"),
        traceability.get("summary"),
        traceability.get("evidenceTrace"),
    ]

    return lower_text(" ".join(clean_text(part) for part in parts if clean_text(part)))


def get_active_procedure(patient):
    procedure = patient.get("procedure", {})
    explicit_procedure = clean_text(procedure.get("explicitProcedure"))

    if explicit_procedure and lower_text(explicit_procedure) not in NOT_AVAILABLE_VALUES:
        return explicit_procedure

    inferred_procedure = clean_text(procedure.get("inferredProcedure"))

    if inferred_procedure and lower_text(inferred_procedure) not in NOT_AVAILABLE_VALUES:
        return inferred_procedure

    return ""


def get_patient_identifier(patient):
    return clean_text(
        patient.get("patientId")
        or patient.get("Patient_ID")
        or patient.get("patient_id")
        or patient.get("id")
    )


def parse_progression_entries(raw_progression):
    if not raw_progression:
        return []

    if isinstance(raw_progression, list):
        return raw_progression

    try:
        parsed = ast.literal_eval(str(raw_progression))
    except (ValueError, SyntaxError):
        return []

    return parsed if isinstance(parsed, list) else []


def parse_date(value):
    raw_value = clean_text(value).split(" ")[0]

    if not raw_value:
        return None

    for pattern in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(raw_value, pattern)
        except ValueError:
            continue

    return None


def average_gap_days(patient):
    entries = parse_progression_entries(patient.get("journey", {}).get("riskProgression"))
    dates = []

    for entry in entries:
        parsed_date = parse_date(entry.get("visit_date"))
        if parsed_date:
            dates.append(parsed_date)

    dates = sorted(dates)

    if len(dates) >= 2:
        gaps = [
            (dates[index + 1] - dates[index]).days
            for index in range(len(dates) - 1)
        ]
        return round(sum(gaps) / len(gaps), 1)

    first_visit = parse_date(patient.get("journey", {}).get("firstVisitDate"))
    latest_visit = parse_date(patient.get("journey", {}).get("latestVisitDate"))

    if first_visit and latest_visit and latest_visit > first_visit:
        return float((latest_visit - first_visit).days)

    return None


def summarize_text(value, max_length=150):
    text = clean_text(value)

    if not text or lower_text(text) in NOT_AVAILABLE_VALUES:
        return "Not available"

    if len(text) <= max_length:
        return text

    return f"{text[:max_length].rstrip()}..."


def format_date_label(value):
    parsed_date = parse_date(value)

    if not parsed_date:
        return clean_text(value) or "Not available"

    return parsed_date.strftime("%d %b %Y")


def unique_drivers(items):
    return list(dict.fromkeys(item for item in items if item))


def patient_source_sections(patient):
    clinical = patient.get("clinical", {})
    return [
        {"title": "Diagnosis", "content": clean_text(clinical.get("diagnosis"))},
        {"title": "Clinical Notes", "content": clean_text(clinical.get("clinicalNotes"))},
        {"title": "Physical Remarks", "content": clean_text(clinical.get("physicalRemarks"))},
        {"title": "Vital Remarks / History", "content": clean_text(clinical.get("vitalRemarks"))},
        {"title": "Investigations", "content": clean_text(clinical.get("investigations"))},
        {"title": "Doctor Advice", "content": clean_text(clinical.get("doctorAdvice"))},
        {"title": "Medicine Details", "content": clean_text(clinical.get("medicineDetails"))},
    ]


def extract_excerpt(text, keyword, radius=84):
    normalized_text = clean_text(text)

    if not normalized_text:
        return "Not available"

    match = re.search(re.escape(keyword), normalized_text, re.IGNORECASE)

    if not match:
        return summarize_text(normalized_text, min(radius * 2, 180))

    start = max(0, match.start() - radius)
    end = min(len(normalized_text), match.end() + radius)
    snippet = normalized_text[start:end].strip()

    if start > 0:
        snippet = f"...{snippet}"

    if end < len(normalized_text):
        snippet = f"{snippet}..."

    return snippet


def find_rule_match(sections, keywords):
    for section in sections:
        content = clean_text(section["content"])

        if not content:
            continue

        for keyword in keywords:
            if re.search(re.escape(keyword), content, re.IGNORECASE):
                return {
                    "keyword": keyword,
                    "source": section["title"],
                    "evidence": extract_excerpt(content, keyword),
                }

    return None


def collect_rule_matches(sections, rules, limit=6):
    items = []

    for rule in rules:
        match = find_rule_match(sections, rule["keywords"])

        if not match:
            continue

        items.append(
            {
                "label": rule["label"],
                "keyword": match["keyword"],
                "source": match["source"],
                "evidence": match["evidence"],
            }
        )

        if len(items) >= limit:
            break

    return items


def parse_medications(patient, limit=8):
    clinical = patient.get("clinical", {})
    medication_text = " ".join(
        [
            clean_text(clinical.get("medicineDetails")),
            clean_text(clinical.get("doctorAdvice")),
        ]
    )

    pattern = re.compile(
        r"\b(?:TAB|CAP|INJ|SYP|POWDER|INSULIN|SPRAY|SACHET)\.?\s*([A-Z0-9\-+/]+(?:\s+[A-Z0-9\-+/]+){0,2})",
        re.IGNORECASE,
    )
    medications = []

    for match in pattern.findall(medication_text):
        normalized = re.sub(r"\s+", " ", clean_text(match)).upper()

        if not normalized or normalized in medications:
            continue

        medications.append(normalized)

        if len(medications) >= limit:
            break

    return medications


def parse_family_history(patient):
    sections = patient_source_sections(patient)

    for section in sections:
        content = clean_text(section["content"])
        match = re.search(r"family\s*history\s*:?\s*(.+)", content, re.IGNORECASE)

        if match:
            family_text = summarize_text(match.group(1), 120)
            return [
                {
                    "label": family_text,
                    "source": section["title"],
                }
            ]

    return []


def derive_icd10_codes(patient):
    sections = patient_source_sections(patient)
    codes = []

    for rule in ICD10_RULES:
        match = find_rule_match(sections, rule["keywords"])

        if not match:
            continue

        codes.append(
            {
                "code": rule["code"],
                "label": rule["label"],
                "matchedKeyword": match["keyword"],
                "source": match["source"],
                "evidence": match["evidence"],
            }
        )

        if len(codes) >= 4:
            break

    return codes


def derive_structured_history(patient, comorbidities):
    sections = patient_source_sections(patient)
    past_conditions = [
        {
            "label": item["label"],
            "source": item["source"],
            "evidence": item["evidence"],
        }
        for item in comorbidities[:6]
    ]
    surgeries = collect_rule_matches(sections, SURGERY_HISTORY_RULES, limit=6)
    medications = [
        {
            "label": medication,
            "source": "Medicine Details / Doctor Advice",
        }
        for medication in parse_medications(patient)
    ]
    family_history = parse_family_history(patient)

    return {
        "pastConditions": past_conditions,
        "surgeries": surgeries,
        "medications": medications,
        "familyHistory": family_history,
        "summary": "Derived from diagnosis, clinical notes, history remarks, and medication instructions.",
    }


def detect_signals(patient):
    text = combine_patient_text(patient)
    department = lower_text(patient.get("department"))
    active_procedure = lower_text(get_active_procedure(patient))

    def matches(keywords):
        return any(keyword in text or keyword in department or keyword in active_procedure for keyword in keywords)

    return {
        "text": text,
        "daycare": matches(DAYCARE_KEYWORDS),
        "renal": matches(RENAL_KEYWORDS),
        "oncology": matches(ONCOLOGY_KEYWORDS),
        "respiratory": matches(RESPIRATORY_KEYWORDS),
        "orthopedic": matches(ORTHOPEDIC_KEYWORDS),
        "infection": matches(INFECTION_KEYWORDS),
        "cardiac": matches(CARDIAC_KEYWORDS),
        "neuro": matches(NEURO_KEYWORDS),
        "surgical": matches(SURGICAL_KEYWORDS),
        "major_procedure": matches(MAJOR_PROCEDURE_KEYWORDS),
        "refusal": matches(REFUSAL_KEYWORDS),
    }


def derive_disease_cohorts(signals):
    cohorts = []

    if signals["renal"]:
        cohorts.append("Renal")
    if signals["oncology"]:
        cohorts.append("Oncology")
    if signals["cardiac"]:
        cohorts.append("Cardiac")
    if signals["respiratory"]:
        cohorts.append("Respiratory")
    if signals["orthopedic"]:
        cohorts.append("Orthopedic")
    if signals["infection"]:
        cohorts.append("Infectious")
    if signals["neuro"]:
        cohorts.append("Neurology")

    if not cohorts:
        cohorts.append("General Medicine")

    return cohorts


def derive_clinical_intelligence(patient, signals):
    sections = patient_source_sections(patient)
    icd10_codes = derive_icd10_codes(patient)
    comorbidities = collect_rule_matches(sections, COMORBIDITY_RULES, limit=8)
    symptoms = collect_rule_matches(sections, SYMPTOM_RULES, limit=8)
    structured_history = derive_structured_history(patient, comorbidities)
    cohorts = derive_disease_cohorts(signals)

    return {
        "icd10Codes": icd10_codes,
        "primaryIcd10": icd10_codes[0] if icd10_codes else None,
        "comorbidities": comorbidities,
        "possibleSymptoms": symptoms,
        "structuredHistory": structured_history,
        "diseaseCohorts": cohorts,
        "primaryCohort": cohorts[0],
    }


def derive_case_type(patient, signals):
    admission_type = clean_text(patient.get("admission", {}).get("type"))
    bed_type = lower_text(patient.get("bed", {}).get("type"))
    active_procedure = get_active_procedure(patient)
    department = lower_text(patient.get("department"))

    if (
        "daycare" in bed_type
        or (signals["daycare"] and admission_type != "Emergency")
    ):
        return {
            "label": "Daycare",
            "reasoning": "Short-stay procedure or infusion indicators support a daycare pathway.",
        }

    if (
        signals["surgical"]
        or signals["major_procedure"]
        or "surgical" in department
        or "transplant" in lower_text(active_procedure)
    ):
        return {
            "label": "Surgical",
            "reasoning": "Procedure-led or operative planning indicators support a surgical case type.",
        }

    return {
        "label": "Medication Management",
        "reasoning": "The current record is dominated by monitoring, medication optimization, and specialty medical care.",
    }


def derive_revenue_package(patient, signals, case_type):
    bed_type = clean_text(patient.get("bed", {}).get("type"))
    admission_type = clean_text(patient.get("admission", {}).get("type"))
    risk_category = clean_text(patient.get("risk", {}).get("category"))
    active_procedure = get_active_procedure(patient)
    score = 0
    drivers = []

    if case_type == "Daycare":
        score += 1
        drivers.append("Daycare pathway keeps the package relatively short-stay.")
    elif case_type == "Surgical":
        score += 4
        drivers.append("Procedure-led care increases package complexity and consumable use.")
    else:
        score += 2
        drivers.append("Medical admission still carries monitoring and pharmacy costs.")

    if "ICU" in bed_type:
        score += 3
        drivers.append("ICU bed allocation materially increases expected package value.")
    elif "HDU" in bed_type or "Oncology" in bed_type:
        score += 2
        drivers.append("High-dependency or specialty ward allocation raises inpatient cost.")
    elif "General" in bed_type:
        score += 1

    if admission_type == "Emergency":
        score += 2
        drivers.append("Emergency coordination increases early investigation and stabilization spend.")
    elif admission_type == "Urgent":
        score += 1

    if signals["major_procedure"]:
        score += 3
        drivers.append("A major procedure or transplant-scale intervention is present.")
    elif active_procedure:
        score += 1
        drivers.append("A defined procedure contributes to package value.")

    if signals["renal"] or signals["oncology"]:
        score += 1
        drivers.append("Renal or oncology complexity usually adds laboratory, drug, and review burden.")

    if risk_category == "Critical":
        score += 1
        drivers.append("Critical-risk monitoring increases expected utilization.")
    elif risk_category == "High":
        score += 1

    if score <= 2:
        revenue_range = "Rs 20K - Rs 60K"
        category = "Standard Value"
        min_lakhs, max_lakhs = 0.2, 0.6
    elif score <= 4:
        revenue_range = "Rs 60K - Rs 1.5L"
        category = "Moderate Value"
        min_lakhs, max_lakhs = 0.6, 1.5
    elif score <= 6:
        revenue_range = "Rs 1.5L - Rs 2.5L"
        category = "Significant Value"
        min_lakhs, max_lakhs = 1.5, 2.5
    elif score <= 8:
        revenue_range = "Rs 2.5L - Rs 4L"
        category = "High Value"
        min_lakhs, max_lakhs = 2.5, 4.0
    else:
        revenue_range = "Rs 4L - Rs 7L"
        category = "Strategic Value"
        min_lakhs, max_lakhs = 4.0, 7.0

    return {
        "expectedRevenue": revenue_range,
        "revenueCategory": category,
        "minLakhs": min_lakhs,
        "maxLakhs": max_lakhs,
        "midLakhs": round((min_lakhs + max_lakhs) / 2, 2),
        "score": score,
        "drivers": unique_drivers(drivers),
        "reasoning": " ".join(unique_drivers(drivers[:3])),
    }


def derive_length_of_stay(patient, signals, case_type):
    admission_type = clean_text(patient.get("admission", {}).get("type"))
    bed_type = clean_text(patient.get("bed", {}).get("type"))
    risk_category = clean_text(patient.get("risk", {}).get("category"))
    progression_trend = clean_text(patient.get("journey", {}).get("progressionTrend"))
    visit_count = int(patient.get("journey", {}).get("visitCount") or 1)
    active_procedure = lower_text(get_active_procedure(patient))
    drivers = []

    if case_type == "Daycare" and "Emergency" not in admission_type:
        return {
            "label": "Not applicable - Daycare / Same-day",
            "minDays": 0,
            "maxDays": 0,
            "drivers": ["Short-stay daycare planning does not require a traditional inpatient LOS."],
            "reasoning": "Short-stay daycare planning does not require a traditional inpatient LOS.",
        }

    min_days, max_days = 1, 3

    if "ICU" in bed_type:
        min_days, max_days = 5, 7
        drivers.append("ICU-level care typically extends inpatient stay.")
    elif "HDU" in bed_type or "Oncology" in bed_type:
        min_days, max_days = 4, 6
        drivers.append("Monitored or specialty ward care usually needs a longer admission.")
    elif case_type == "Surgical":
        min_days, max_days = 3, 5
        drivers.append("Procedure-based recovery increases expected length of stay.")

    if admission_type == "Emergency" and max_days < 4:
        min_days, max_days = 2, 4
        drivers.append("Emergency stabilization adds at least short inpatient observation.")

    if signals["major_procedure"]:
        min_days = max(min_days, 5)
        max_days = max(max_days, 8)
        drivers.append("Major procedures or transplant-scale care extend post-procedure monitoring.")

    if signals["renal"] and admission_type == "Emergency":
        min_days = max(min_days, 4)
        max_days = max(max_days, 6)
        drivers.append("Renal instability often needs serial labs and monitored correction.")

    if signals["oncology"] and risk_category == "Critical":
        min_days = max(min_days, 5)
        max_days = max(max_days, 7)
        drivers.append("Critical oncology context increases monitoring and treatment coordination time.")

    if progression_trend == "Worsening" or visit_count >= 3:
        max_days += 1
        drivers.append("Worsening or repeated visits suggest a slower discharge trajectory.")

    if max_days < min_days:
        max_days = min_days

    return {
        "label": f"{min_days} - {max_days} days",
        "minDays": min_days,
        "maxDays": max_days,
        "drivers": unique_drivers(drivers),
        "reasoning": " ".join(unique_drivers(drivers[:3])) or "Estimated from acuity, bed requirement, and treatment complexity.",
    }


def derive_readmission_risk(patient, signals):
    journey = patient.get("journey", {})
    risk = patient.get("risk", {})
    bed = patient.get("bed", {})
    traceability = patient.get("traceability", {})
    score = 0
    drivers = []
    visit_count = int(journey.get("visitCount") or 1)
    repeat_visit = clean_text(journey.get("repeatVisit"))
    progression_trend = clean_text(journey.get("progressionTrend"))
    risk_category = clean_text(risk.get("category"))
    admission_type = clean_text(patient.get("admission", {}).get("type"))

    if repeat_visit == "Yes":
        score += 2
        drivers.append("Repeat visits indicate prior need for re-evaluation.")

    if visit_count >= 3:
        score += 1
        drivers.append("Multiple visits increase the chance of return utilization.")

    if progression_trend == "Worsening":
        score += 2
        drivers.append("Worsening progression trend raises near-term readmission risk.")

    if risk_category == "Critical":
        score += 2
        drivers.append("Critical-risk status suggests high post-discharge instability.")
    elif risk_category == "High":
        score += 1

    if admission_type in {"Emergency", "Urgent"}:
        score += 1
        drivers.append("Emergency or urgent admission pathways are more likely to bounce back.")

    if clean_text(bed.get("type")) in {"ICU", "HDU"}:
        score += 1
        drivers.append("High-dependency bed need implies closer follow-up after discharge.")

    if signals["renal"]:
        score += 2
        drivers.append("Renal dysfunction, creatinine abnormalities, or transplant context increase recurrence risk.")

    if signals["oncology"]:
        score += 1
        drivers.append("Oncology treatment burden can trigger early re-presentation.")

    if int(traceability.get("evidenceCount") or 0) >= 8:
        score += 1
        drivers.append("A dense evidence trail suggests multi-factor complexity.")

    if score >= 7:
        category = "High"
    elif score >= 4:
        category = "Moderate"
    else:
        category = "Low"

    return {
        "label": category,
        "score": score,
        "drivers": unique_drivers(drivers),
        "reasoning": " ".join(unique_drivers(drivers[:3])) or "Estimated from visit pattern, acuity, and chronic disease burden.",
    }


def derive_no_show_risk(patient, signals, case_type):
    journey = patient.get("journey", {})
    risk = patient.get("risk", {})
    admission_type = clean_text(patient.get("admission", {}).get("type"))
    risk_category = clean_text(risk.get("category"))
    progression_trend = clean_text(journey.get("progressionTrend"))
    repeat_visit = clean_text(journey.get("repeatVisit"))
    score = 0
    drivers = []
    gap_days = average_gap_days(patient)

    if admission_type == "Elective":
        score += 2
        drivers.append("Elective pathways are more vulnerable to scheduling drop-off.")

    if case_type == "Daycare":
        score += 1
        drivers.append("Short-stay procedures can be postponed when symptoms feel manageable.")

    if risk_category == "Low":
        score += 2
        drivers.append("Lower acuity often reduces urgency from the patient's perspective.")
    elif risk_category == "Medium":
        score += 1
    elif risk_category == "Critical":
        score -= 2
        drivers.append("Critical acuity usually lowers the chance of a missed admission.")

    if repeat_visit == "No":
        score += 1
        drivers.append("A single documented visit means follow-through behavior is less established.")
    else:
        score -= 1
        drivers.append("Completed follow-up visits suggest better adherence to review plans.")

    if gap_days is not None and gap_days > 45:
        score += 2
        drivers.append("Long gaps between documented visits suggest weaker follow-up continuity.")
    elif gap_days is not None and gap_days > 21:
        score += 1

    if progression_trend == "Improving":
        score += 1
        drivers.append("Improving symptoms can reduce perceived need for attendance.")
    elif progression_trend == "Worsening":
        score -= 1
        drivers.append("Worsening trajectory usually keeps patients engaged with care.")

    if signals["refusal"]:
        score += 2
        drivers.append("Refusal or decline language is a strong dropout signal.")

    if admission_type == "Emergency" or clean_text(patient.get("bed", {}).get("type")) == "ICU":
        score -= 2

    if score >= 5:
        category = "High"
    elif score >= 3:
        category = "Moderate"
    else:
        category = "Low"

    return {
        "label": category,
        "score": max(score, 0),
        "drivers": unique_drivers(drivers),
        "reasoning": " ".join(unique_drivers(drivers[:3])) or "Estimated from elective intent, acuity, and observed follow-up pattern.",
    }


def derive_deferred_time(patient, readmission_risk, case_type):
    risk_category = clean_text(patient.get("risk", {}).get("category"))
    admission_type = clean_text(patient.get("admission", {}).get("type"))
    bed_type = clean_text(patient.get("bed", {}).get("type"))
    progression_trend = clean_text(patient.get("journey", {}).get("progressionTrend"))
    drivers = []

    if (
        admission_type == "Emergency"
        or bed_type == "ICU"
        or (risk_category == "Critical" and progression_trend == "Worsening")
    ):
        drivers.append("Emergency or unstable critical features make delay unsafe.")
        return {
            "label": "Cannot be safely delayed",
            "drivers": drivers,
            "reasoning": drivers[0],
        }

    if risk_category == "Critical" or bed_type in {"HDU", "General Oncology Ward"}:
        drivers.append("Critical specialty care needs should be reviewed within 24-48 hours.")
        return {
            "label": "24-48 hours only",
            "drivers": drivers,
            "reasoning": drivers[0],
        }

    if admission_type == "Urgent" or readmission_risk["label"] == "High" or case_type == "Surgical":
        drivers.append("Near-term admission is advisable because delay increases coordination risk.")
        return {
            "label": "3-5 days acceptable",
            "drivers": drivers,
            "reasoning": drivers[0],
        }

    if case_type == "Daycare" or risk_category in {"Low", "Medium"}:
        drivers.append("The current profile supports short deferral if symptoms remain stable.")
        return {
            "label": "1-2 weeks acceptable",
            "drivers": drivers,
            "reasoning": drivers[0],
        }

    return {
        "label": "Can be safely deferred",
        "drivers": ["No high-acuity inpatient trigger is currently active."],
        "reasoning": "No high-acuity inpatient trigger is currently active.",
    }


def derive_admission_conversion_probability(
    patient,
    signals,
    case_type,
    readmission_risk,
    no_show_risk,
    deferred_time,
    clinical_intelligence,
):
    score = 42
    drivers = []
    risk_category = clean_text(patient.get("risk", {}).get("category"))
    admission_type = clean_text(patient.get("admission", {}).get("type"))
    bed_type = clean_text(patient.get("bed", {}).get("type"))
    progression_trend = clean_text(patient.get("journey", {}).get("progressionTrend"))
    evidence_count = int(patient.get("traceability", {}).get("evidenceCount") or 0)

    if admission_type == "Emergency":
        score += 28
        drivers.append("Emergency pathway strongly increases conversion likelihood.")
    elif admission_type == "Urgent":
        score += 18
        drivers.append("Urgent admission advice supports near-term conversion.")
    elif admission_type == "Elective":
        score += 8
        drivers.append("Planned admission intent is already documented.")

    if risk_category == "Critical":
        score += 18
        drivers.append("Critical risk signals make inpatient conversion more likely.")
    elif risk_category == "High":
        score += 10
        drivers.append("High clinical risk increases admission conversion pressure.")

    if bed_type in {"ICU", "HDU", "General Oncology Ward"}:
        score += 10
        drivers.append("Specialty bed planning indicates a strong chance of admission.")

    if progression_trend == "Worsening":
        score += 8
        drivers.append("Worsening progression increases the chance of admission follow-through.")

    if readmission_risk["label"] == "High":
        score += 5
        drivers.append("High readmission risk indicates unstable disease burden.")

    if no_show_risk["label"] == "High":
        score -= 12
        drivers.append("High no-show risk reduces expected conversion despite clinical need.")
    elif no_show_risk["label"] == "Moderate":
        score -= 5

    if deferred_time["label"] == "Cannot be safely delayed":
        score += 10
        drivers.append("Unsafe-to-delay cases usually convert quickly to admission.")

    if case_type == "Surgical":
        score += 6
        drivers.append("Procedure-led care typically has a clearer admission endpoint.")

    if evidence_count >= 8:
        score += 4
        drivers.append("Dense traceable evidence supports a stronger admission recommendation.")

    if clinical_intelligence["primaryIcd10"]:
        score += 2
        drivers.append("Structured coding confidence improves decision certainty.")

    percentage = max(18, min(96, score))

    if percentage >= 80:
        label = "Very High"
    elif percentage >= 65:
        label = "High"
    elif percentage >= 45:
        label = "Moderate"
    else:
        label = "Low"

    return {
        "label": label,
        "percentage": percentage,
        "drivers": unique_drivers(drivers),
        "reasoning": " ".join(unique_drivers(drivers[:3])) or "Estimated from urgency, acuity, and follow-through risk.",
    }


def derive_treatment_plan(patient, signals, case_type, clinical_intelligence):
    active_procedure = get_active_procedure(patient)
    diagnosis = clean_text(patient.get("clinical", {}).get("diagnosis"))
    diagnosis_focus = summarize_text(
        diagnosis
        or active_procedure
        or ", ".join(item["label"] for item in clinical_intelligence["possibleSymptoms"][:2]),
        80,
    )
    top_comorbidity = (
        clinical_intelligence["comorbidities"][0]["label"]
        if clinical_intelligence["comorbidities"]
        else "the active chronic disease burden"
    )

    if "dialysis" in lower_text(active_procedure) or (
        signals["renal"] and "dialysis" in signals["text"]
    ):
        primary = f"Dialysis-led admission for {diagnosis_focus} with nephrology monitoring and electrolyte surveillance"
        secondary = "Medical stabilization with transplant review once creatinine and potassium trends are safer"
    elif "transplant" in lower_text(active_procedure) or "transplant" in signals["text"]:
        primary = f"Transplant-focused inpatient monitoring for {diagnosis_focus} with renal function and immunosuppression review"
        secondary = "Medical stabilization with close transplant follow-up if admission can remain planned"
    elif signals["oncology"]:
        primary = f"Oncology-directed admission for {diagnosis_focus} with hematology monitoring and therapy review"
        secondary = "Daycare therapy, transfusion, or planned oncology follow-up if the patient remains clinically stable"
    elif case_type == "Surgical" and active_procedure:
        primary = f"{active_procedure} with peri-procedural monitoring and inpatient recovery planning"
        secondary = f"Conservative stabilization with scheduled elective intervention while monitoring {top_comorbidity.lower()}"
    elif signals["respiratory"]:
        primary = f"Respiratory stabilization for {diagnosis_focus} with bronchodilator or steroid therapy under monitored observation"
        secondary = "Ward observation with inhaled therapy optimization and early review if symptoms settle"
    elif signals["infection"]:
        primary = f"Medical stabilization for {diagnosis_focus} with culture-guided therapy and repeat laboratory monitoring"
        secondary = "Observation with repeat labs and outpatient reassessment if response remains stable"
    elif signals["cardiac"]:
        primary = f"Cardiac monitoring for {diagnosis_focus} with medication optimization and rhythm or ischemia evaluation"
        secondary = "Short-interval follow-up with planned procedure escalation if symptoms worsen"
    elif signals["renal"]:
        primary = f"Renal stabilization for {diagnosis_focus} with nephrology monitoring and serial metabolic review"
        secondary = "Outpatient monitoring with planned procedure or transplant escalation if risk increases"
    else:
        primary = f"Medication optimization for {diagnosis_focus} with specialty monitoring and repeat clinical review"
        secondary = f"Observation with planned follow-up escalation if {top_comorbidity.lower()} or biomarkers worsen"

    reasoning = (
        f"Treatment options are inferred from the active procedure, disease cohort, and diagnosis cues such as "
        f"{diagnosis_focus}, while accounting for {top_comorbidity.lower()}."
    )

    return {
        "primary": primary,
        "secondary": secondary,
        "reasoning": reasoning,
    }


def derive_timeline(patient, clinical_intelligence):
    clinical = patient.get("clinical", {})
    journey = patient.get("journey", {})
    first_visit = journey.get("firstVisitDate") or patient.get("visitDate")
    latest_visit = journey.get("latestVisitDate") or patient.get("visitDate")
    symptom_labels = ", ".join(
        item["label"] for item in clinical_intelligence["possibleSymptoms"][:3]
    )
    past_conditions = ", ".join(
        item["label"] for item in clinical_intelligence["structuredHistory"]["pastConditions"][:3]
    )

    symptom_summary = summarize_text(
        symptom_labels
        or clinical.get("vitalRemarks")
        or clinical.get("physicalRemarks")
        or clinical.get("clinicalNotes"),
        160,
    )
    diagnosis_summary = summarize_text(
        (
            ", ".join(
                f"{item['code']} {item['label']}"
                for item in clinical_intelligence["icd10Codes"][:2]
            )
        )
        or clinical.get("diagnosis")
        or get_active_procedure(patient)
        or clinical.get("investigations"),
        160,
    )
    advice_summary = summarize_text(
        clinical.get("doctorAdvice")
        or patient.get("admission", {}).get("summary"),
        160,
    )

    current_status = (
        f"{clean_text(patient.get('risk', {}).get('category'))} risk, "
        f"{clean_text(patient.get('admission', {}).get('type'))} pathway, "
        f"{clean_text(patient.get('bed', {}).get('type'))} bed recommendation, "
        f"trend: {clean_text(journey.get('progressionTrend')) or 'Not available'}."
    )

    stages = [
        {
            "stage": "First Symptom / History",
            "date": format_date_label(first_visit),
            "summary": summarize_text(
                " | ".join(part for part in [symptom_summary, past_conditions] if part),
                160,
            ),
            "source": "Symptoms and history extraction",
        },
        {
            "stage": "OPD Evaluation",
            "date": format_date_label(first_visit),
            "summary": (
                f"Initial documented review under {clean_text(patient.get('department')) or 'the current department'} "
                f"with {clean_text(patient.get('doctorName')) or 'the assigned clinician'}."
            ),
            "source": "Journey and visit history",
        },
        {
            "stage": "Diagnosis / Workup",
            "date": format_date_label(patient.get("visitDate") or latest_visit),
            "summary": diagnosis_summary,
            "source": "Diagnosis, investigations, or procedure intelligence",
        },
        {
            "stage": "Admission Advice",
            "date": format_date_label(patient.get("visitDate") or latest_visit),
            "summary": advice_summary,
            "source": "Doctor advice and admission reasoning",
        },
        {
            "stage": "Current Status",
            "date": format_date_label(latest_visit),
            "summary": current_status,
            "source": "Current risk, bed, and journey profile",
        },
    ]

    return {
        "stages": stages,
        "summary": "Structured from symptom context, documented visits, diagnosis cues, admission advice, and the latest operational status.",
    }


def build_rule_based_operational_payload(patient, signals=None):
    signals = signals or detect_signals(patient)
    clinical_intelligence = derive_clinical_intelligence(patient, signals)
    case_type = derive_case_type(patient, signals)
    readmission_risk = derive_readmission_risk(patient, signals)
    no_show_risk = derive_no_show_risk(patient, signals, case_type["label"])
    deferred_time = derive_deferred_time(patient, readmission_risk, case_type["label"])
    conversion_probability = derive_admission_conversion_probability(
        patient,
        signals,
        case_type["label"],
        readmission_risk,
        no_show_risk,
        deferred_time,
        clinical_intelligence,
    )

    return {
        "clinicalIntelligence": clinical_intelligence,
        "caseType": case_type,
        "packageIntelligence": derive_revenue_package(patient, signals, case_type["label"]),
        "lengthOfStay": derive_length_of_stay(patient, signals, case_type["label"]),
        "readmissionRisk": readmission_risk,
        "noShowRisk": no_show_risk,
        "deferredTime": deferred_time,
        "admissionConversionProbability": conversion_probability,
        "treatmentPlan": derive_treatment_plan(
            patient,
            signals,
            case_type["label"],
            clinical_intelligence,
        ),
        "clinicalTimeline": derive_timeline(patient, clinical_intelligence),
    }


def derive_llm_priority_score(patient, base_payload=None, signals=None):
    signals = signals or detect_signals(patient)
    base_payload = base_payload or build_rule_based_operational_payload(patient, signals)
    risk_category = clean_text(patient.get("risk", {}).get("category"))
    admission_type = clean_text(patient.get("admission", {}).get("type"))
    bed_type = clean_text(patient.get("bed", {}).get("type"))
    progression_trend = clean_text(patient.get("journey", {}).get("progressionTrend"))
    repeat_visit = clean_text(patient.get("journey", {}).get("repeatVisit"))
    readmission_label = clean_text(base_payload.get("readmissionRisk", {}).get("label"))
    deferred_label = clean_text(base_payload.get("deferredTime", {}).get("label"))
    conversion_percentage = int(
        base_payload.get("admissionConversionProbability", {}).get("percentage") or 0
    )
    evidence_count = int(patient.get("traceability", {}).get("evidenceCount") or 0)
    score = 0
    reasons = []

    score += PRIORITY_RISK_POINTS.get(risk_category, 0)
    if risk_category:
        reasons.append(f"{risk_category} risk status raises urgency.")

    score += PRIORITY_ADMISSION_POINTS.get(admission_type, 0)
    if admission_type in {"Emergency", "Urgent"}:
        reasons.append(f"{admission_type} admission intent requires faster review.")

    score += PRIORITY_BED_POINTS.get(bed_type, 0)
    if bed_type in {"ICU", "HDU", "General Oncology Ward"}:
        reasons.append(f"{bed_type} bed planning indicates higher operational priority.")

    score += PRIORITY_READMISSION_POINTS.get(readmission_label, 0)
    if readmission_label == "High":
        reasons.append("High readmission risk increases short-term care pressure.")

    score += PRIORITY_DEFERRED_POINTS.get(deferred_label, 0)
    if deferred_label == "Cannot be safely delayed":
        reasons.append("Delay is unsafe based on current clinical trajectory.")

    if progression_trend == "Worsening":
        score += 14
        reasons.append("Worsening progression trend increases triage priority.")

    if repeat_visit == "Yes":
        score += 8
        reasons.append("Repeat visits suggest unresolved or escalating clinical need.")

    if signals["renal"] or signals["oncology"]:
        score += 6
        reasons.append("Renal or oncology complexity raises monitoring needs.")

    if signals["major_procedure"]:
        score += 5
        reasons.append("Major procedure burden raises coordination priority.")

    if conversion_percentage >= 90:
        score += 10
    elif conversion_percentage >= 75:
        score += 7
    elif conversion_percentage >= 60:
        score += 4

    if evidence_count >= 4:
        score += 3

    return {
        "score": score,
        "reasons": reasons[:5],
        "riskCategory": risk_category,
        "admissionType": admission_type,
        "bedType": bed_type,
    }


def rank_patients_for_llm(patients, limit=10):
    ranked_patients = []

    for patient in patients:
        signals = detect_signals(patient)
        base_payload = build_rule_based_operational_payload(patient, signals)
        priority = derive_llm_priority_score(patient, base_payload=base_payload, signals=signals)
        ranked_patients.append(
            {
                "patientId": get_patient_identifier(patient),
                "score": priority["score"],
                "reasons": priority["reasons"],
                "riskCategory": priority["riskCategory"],
                "admissionType": priority["admissionType"],
                "bedType": priority["bedType"],
            }
        )

    ranked_patients.sort(
        key=lambda item: (
            -item["score"],
            PRIORITY_RISK_ORDER.get(item["riskCategory"], 99),
            PRIORITY_ADMISSION_ORDER.get(item["admissionType"], 99),
            item["patientId"],
        )
    )

    return ranked_patients[: max(0, limit)]


def derive_operational_intelligence(
    patient,
    llm_allowed=False,
    allow_live_llm=False,
    include_predictive_modeling=False,
):
    signals = detect_signals(patient)
    base_payload = build_rule_based_operational_payload(patient, signals)
    priority_profile = derive_llm_priority_score(patient, base_payload=base_payload, signals=signals)
    predictive_modeling = patient.get("predictiveModeling")

    if include_predictive_modeling and predictive_modeling is None:
        try:
            from backend.ml_predictor import maybe_predict_patient_ml

            predictive_modeling = maybe_predict_patient_ml(patient)
        except Exception:  # pragma: no cover - graceful fallback if ML layer is unavailable
            predictive_modeling = {
                "enabled": False,
                "reason": "Predictive ML layer unavailable",
            }
    elif predictive_modeling is None:
        predictive_modeling = {
            "enabled": False,
            "reason": "Predictive ML not requested for this payload",
        }

    llm_payload = maybe_generate_llm_operational(
        patient,
        llm_allowed=llm_allowed,
        allow_live_generation=allow_live_llm,
    )

    merged_payload = merge_operational_payloads(base_payload, llm_payload)
    merged_payload["risk_source"] = "fallback_ml_rules"
    merged_payload["predictiveModeling"] = predictive_modeling

    if should_use_agentic_risk():
        try:
            agentic_result = run_agentic_patient_pipeline(
                patient,
                baseline_operational=merged_payload,
            )
            merged_payload = safe_merge_agentic_into_operational(
                merged_payload,
                agentic_result,
            )
        except Exception as exc:
            merged_payload["agentic_error"] = str(exc)
            merged_payload["risk_source"] = "fallback_ml_rules"

    agentic_applied = str(merged_payload.get("risk_source") or "").startswith("agentic_llm")
    merged_payload["intelligenceProfile"] = {
        "llmEligible": llm_allowed,
        "llmApplied": bool(llm_payload),
        "agenticEnabled": should_use_agentic_risk(),
        "agenticApplied": agentic_applied,
        "primaryEngine": (
            "Agentic LLM + ML + Rule-based"
            if agentic_applied and predictive_modeling.get("enabled")
            else "Agentic LLM + Rule-based"
            if agentic_applied
            else "ML + LLM + Rule-based"
            if predictive_modeling.get("enabled") and llm_payload
            else "ML + Rule-based"
            if predictive_modeling.get("enabled")
            else "LLM + Rule-based"
            if llm_payload
            else "Rule-based"
        ),
        "priorityScore": priority_profile["score"],
        "priorityReasons": priority_profile["reasons"],
    }
    return merged_payload


def enrich_patient_record(
    patient,
    llm_allowed=False,
    allow_live_llm=False,
    include_predictive_modeling=False,
):
    enriched_patient = copy.deepcopy(patient)
    enriched_patient["operational"] = derive_operational_intelligence(
        enriched_patient,
        llm_allowed=llm_allowed,
        allow_live_llm=allow_live_llm,
        include_predictive_modeling=include_predictive_modeling,
    )
    return enriched_patient


def enrich_patients(
    patients,
    llm_allowed=False,
    allow_live_llm=False,
    include_predictive_modeling=False,
):
    return [
        enrich_patient_record(
            patient,
            llm_allowed=llm_allowed,
            allow_live_llm=allow_live_llm,
            include_predictive_modeling=include_predictive_modeling,
        )
        for patient in patients
    ]
