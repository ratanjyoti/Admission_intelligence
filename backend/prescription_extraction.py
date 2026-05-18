import re
from collections import defaultdict

try:
    import fitz
except Exception:  # pragma: no cover - handled at runtime
    fitz = None

from backend.operational_intelligence import (
    CARDIAC_KEYWORDS,
    INFECTION_KEYWORDS,
    MAJOR_PROCEDURE_KEYWORDS,
    NEURO_KEYWORDS,
    ONCOLOGY_KEYWORDS,
    ORTHOPEDIC_KEYWORDS,
    RENAL_KEYWORDS,
    RESPIRATORY_KEYWORDS,
    SURGICAL_KEYWORDS,
    clean_text,
)


SECTION_ALIASES = {
    "patientName": ["patient name", "name"],
    "doctorName": ["doctor", "consultant", "dr", "dr."],
    "diagnosis": [
        "diagnosis",
        "diagnoses",
        "provisional diagnosis",
        "impression",
        "chief complaint",
        "complaints",
        "complaint",
    ],
    "physicalRemarks": ["examination", "exam", "physical examination", "on examination", "o/e"],
    "vitalRemarks": ["history", "past history", "vitals", "vital signs", "known history", "medical history"],
    "investigations": ["investigations", "investigation", "labs", "lab", "reports", "tests", "workup"],
    "doctorAdvice": ["advice", "plan", "recommendation", "follow up", "follow-up", "next steps"],
    "medicineDetails": ["medicines", "medications", "prescription", "rx", "treatment"],
    "explicitProcedure": ["procedure", "surgery", "operation", "intervention"],
}

FIELD_LABELS = {
    "patientName": "Patient Name",
    "doctorName": "Doctor Name",
    "department": "Department",
    "diagnosis": "Diagnosis",
    "clinicalNotes": "Clinical Notes",
    "physicalRemarks": "Physical Remarks",
    "vitalRemarks": "Vital Remarks / History",
    "investigations": "Investigations",
    "doctorAdvice": "Doctor Advice",
    "medicineDetails": "Medicine Details",
    "explicitProcedure": "Procedure",
}

MEDICATION_PATTERN = re.compile(
    r"\b(?:tab|tablet|cap|capsule|inj|injection|syp|syrup|insulin|drop|drops|spray|cream|ointment|neb)\b",
    re.IGNORECASE,
)
INVESTIGATION_PATTERN = re.compile(
    r"\b(?:cbc|creatinine|urea|ecg|echo|troponin|x-ray|xray|ct|mri|usg|ultrasound|hb|plt|tlc|dlc|lft|rft|electrolyte|potassium|sodium|urine|biopsy|test|report)\b",
    re.IGNORECASE,
)
ADVICE_PATTERN = re.compile(
    r"\b(?:admit|admission|review|follow[- ]?up|monitor|continue|start|stop|urgent|plan|advise|consult|refer|observe|repeat)\b",
    re.IGNORECASE,
)
VITAL_HISTORY_PATTERN = re.compile(
    r"\b(?:bp|pulse|temp|temperature|spo2|history|h/o|k/c/o|known case|dm|diabetes|htn|hypertension|cad|ckd|copd|asthma|seizure|stroke)\b",
    re.IGNORECASE,
)
PHYSICAL_PATTERN = re.compile(
    r"\b(?:o/e|cvs|rs|cns|pa|abdomen|abd|pallor|edema|swelling|tenderness|guarding|wheeze|crepitations|conscious|oriented)\b",
    re.IGNORECASE,
)
PROCEDURE_PATTERN = re.compile(
    r"\b(?:dialysis|biopsy|surgery|operation|angioplasty|avf|transplant|arthroplasty|stenting|catheterization|cath)\b",
    re.IGNORECASE,
)
REPEAT_VISIT_PATTERN = re.compile(
    r"\b(?:follow[- ]?up|review|known case|repeat visit|revisit|since last visit)\b",
    re.IGNORECASE,
)


SPECIALTY_RULES = [
    ("Cardiology", CARDIAC_KEYWORDS + ["cardiology", "cardiac"]),
    ("Nephrology", RENAL_KEYWORDS + ["nephrology", "kidney", "renal"]),
    ("Neurology", NEURO_KEYWORDS + ["neurology", "neuro"]),
    ("Oncology", ONCOLOGY_KEYWORDS + ["oncology", "oncologist"]),
    ("Pulmonology", RESPIRATORY_KEYWORDS + ["pulmonology", "respiratory"]),
    ("Orthopedics", ORTHOPEDIC_KEYWORDS + ["orthopedic", "orthopaedic"]),
    ("Infectious Disease", INFECTION_KEYWORDS + ["infection", "infectious"]),
    ("Surgical Gastroenterology", SURGICAL_KEYWORDS + ["surgery", "surgical"]),
]

DIAGNOSIS_HINTS = [
    "pain",
    "fracture",
    "fever",
    "infection",
    "failure",
    "disease",
    "syndrome",
    "diabetes",
    "hypertension",
    "nephropathy",
    "seizure",
    "stroke",
    "asthma",
    "copd",
    "lymphoma",
    "malignancy",
]


def pdf_extraction_enabled():
    return fitz is not None


def heading_key(value):
    return re.sub(r"[^a-z0-9]+", " ", clean_text(value).lower()).strip()


def clean_lines(text):
    lines = []
    for raw_line in str(text or "").splitlines():
        normalized = re.sub(r"\s+", " ", raw_line.replace("\u00a0", " ")).strip(" :|-")
        if normalized:
            lines.append(normalized)
    return lines


def extract_text_from_pdf_bytes(file_bytes):
    if fitz is None:
        raise RuntimeError("PyMuPDF is not installed. Install PyMuPDF to enable prescription PDF upload.")

    if not file_bytes:
        raise ValueError("Uploaded PDF is empty.")

    with fitz.open(stream=file_bytes, filetype="pdf") as document:
        page_count = document.page_count
        pages = [page.get_text("text") for page in document]

    extracted_text = "\n".join(page for page in pages if clean_text(page))
    if not clean_text(extracted_text):
        raise ValueError(
            "No selectable text was found in this PDF. It may be a scanned image and would need OCR before intake auto-fill."
        )

    return extracted_text, page_count


def detect_heading_field(line):
    normalized_line = heading_key(line)
    for field, aliases in SECTION_ALIASES.items():
        for alias in aliases:
            alias_key = heading_key(alias)
            if normalized_line == alias_key:
                return field, ""
            if normalized_line.startswith(f"{alias_key} "):
                remainder = clean_text(line)[len(alias) :].lstrip(" :-")
                return field, remainder
            if normalized_line.startswith(f"{alias_key}:") or normalized_line.startswith(f"{alias_key}-"):
                remainder = re.split(r"[:\-]", clean_text(line), maxsplit=1)
                return field, clean_text(remainder[1]) if len(remainder) > 1 else ""
    return None, ""


def score_line(line):
    normalized = clean_text(line)
    lowered = normalized.lower()
    scores = defaultdict(int)

    if MEDICATION_PATTERN.search(normalized):
        scores["medicineDetails"] += 4
    if INVESTIGATION_PATTERN.search(normalized) or re.search(r"\b\d+(\.\d+)?\b", normalized):
        scores["investigations"] += 3
    if ADVICE_PATTERN.search(normalized):
        scores["doctorAdvice"] += 3
    if VITAL_HISTORY_PATTERN.search(normalized):
        scores["vitalRemarks"] += 3
    if PHYSICAL_PATTERN.search(normalized):
        scores["physicalRemarks"] += 3
    if PROCEDURE_PATTERN.search(normalized):
        scores["explicitProcedure"] += 4
    if any(hint in lowered for hint in DIAGNOSIS_HINTS):
        scores["diagnosis"] += 2

    if "diagnosis" in lowered or "impression" in lowered:
        scores["diagnosis"] += 4

    best_field = None
    best_score = 0
    for field, value in scores.items():
        if value > best_score:
            best_field = field
            best_score = value
    return best_field, best_score


def append_unique(mapping, field, value):
    cleaned = clean_text(value)
    if not cleaned:
        return
    if cleaned not in mapping[field]:
        mapping[field].append(cleaned)


def extract_labeled_value(lines, fields):
    aliases = []
    for field in fields:
        aliases.extend(SECTION_ALIASES.get(field, []))

    for line in lines:
        normalized = clean_text(line)
        for alias in aliases:
            pattern = re.compile(rf"^{re.escape(alias)}\s*[:\-]\s*(.+)$", re.IGNORECASE)
            match = pattern.search(normalized)
            if match:
                return clean_text(match.group(1))
    return ""


def detect_department(text):
    lowered = clean_text(text).lower()
    ranked = []
    for label, keywords in SPECIALTY_RULES:
        score = sum(1 for keyword in keywords if keyword in lowered)
        if score:
            ranked.append((score, label))
    ranked.sort(reverse=True)
    return ranked[0][1] if ranked else ""


def summarize_preview(value, length=180):
    text = clean_text(value)
    if len(text) <= length:
        return text
    return f"{text[:length].rstrip()}..."


def structure_prescription_text(extracted_text):
    lines = clean_lines(extracted_text)
    bucketed = defaultdict(list)
    unmatched = []
    current_field = None

    for line in lines:
        field, remainder = detect_heading_field(line)
        if field:
            current_field = field
            initial_value = remainder or (line if field in {"diagnosis", "doctorAdvice"} else "")
            append_unique(bucketed, field, initial_value)
            continue

        if current_field:
            append_unique(bucketed, current_field, line)
            continue

        unmatched.append(line)

    for line in unmatched:
        field, score = score_line(line)
        if field and score >= 2:
            append_unique(bucketed, field, line)
        else:
            append_unique(bucketed, "clinicalNotes", line)

    if not bucketed["clinicalNotes"]:
        fallback_lines = [line for line in lines if line not in bucketed["medicineDetails"]][:8]
        for line in fallback_lines:
            append_unique(bucketed, "clinicalNotes", line)

    if not bucketed["diagnosis"]:
        for line in bucketed["clinicalNotes"][:4]:
            if any(hint in line.lower() for hint in DIAGNOSIS_HINTS):
                append_unique(bucketed, "diagnosis", line)

    explicit_procedure = ""
    procedure_lines = (
        bucketed["explicitProcedure"] + bucketed["doctorAdvice"] + bucketed["clinicalNotes"]
    )
    for line in procedure_lines:
        match = PROCEDURE_PATTERN.search(line)
        if match:
            explicit_procedure = clean_text(match.group(0)).title()
            break

    auto_fill = {
        "patientName": extract_labeled_value(lines, ["patientName"]),
        "doctorName": extract_labeled_value(lines, ["doctorName"]),
        "department": detect_department(extracted_text),
        "diagnosis": "\n".join(bucketed["diagnosis"][:4]),
        "clinicalNotes": "\n".join(bucketed["clinicalNotes"][:10]),
        "physicalRemarks": "\n".join(bucketed["physicalRemarks"][:6]),
        "vitalRemarks": "\n".join(bucketed["vitalRemarks"][:6]),
        "investigations": "\n".join(bucketed["investigations"][:8]),
        "doctorAdvice": "\n".join(bucketed["doctorAdvice"][:6]),
        "medicineDetails": "\n".join(bucketed["medicineDetails"][:8]),
        "explicitProcedure": explicit_procedure,
        "repeatVisit": bool(REPEAT_VISIT_PATTERN.search(extracted_text)),
    }

    detected_fields = []
    field_evidence = {}
    for field, value in auto_fill.items():
        if field == "repeatVisit":
            if value:
                detected_fields.append(
                    {
                        "field": field,
                        "label": "Repeat Visit Indicator",
                        "preview": "Follow-up or review language detected in the prescription.",
                    }
                )
            continue

        cleaned = clean_text(value)
        if cleaned:
            preview = summarize_preview(cleaned)
            detected_fields.append(
                {"field": field, "label": FIELD_LABELS.get(field, field), "preview": preview}
            )
            field_evidence[field] = preview

    warnings = []
    if len(lines) < 5:
        warnings.append(
            "Only a small amount of text was extracted. If the document is a scan, OCR may be needed for better auto-fill quality."
        )
    if not auto_fill["diagnosis"]:
        warnings.append("Diagnosis could not be confidently isolated. Please review the auto-filled form.")

    return {
        "autoFill": auto_fill,
        "detectedFields": detected_fields,
        "fieldEvidence": field_evidence,
        "warnings": warnings,
    }


def extract_prescription_payload(file_bytes, filename="prescription.pdf"):
    extracted_text, page_count = extract_text_from_pdf_bytes(file_bytes)
    structured = structure_prescription_text(extracted_text)
    return {
        "filename": filename,
        "pageCount": page_count,
        "extractedText": extracted_text,
        **structured,
    }
