import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

try:
    import fitz
except ImportError:  # pragma: no cover
    fitz = None

try:
    import pandas as pd
except ImportError:  # pragma: no cover
    pd = None

try:
    import pdfplumber
except ImportError:  # pragma: no cover
    pdfplumber = None

ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "data" / "official_sources"
REFERENCE_DIR = ROOT / "data" / "reference"
REFERENCE_DIR.mkdir(parents=True, exist_ok=True)

PMJAY_PROCEDURE_PATTERN = re.compile(r"^[A-Z]{2}\d{2,4}[A-Z0-9]{0,2}$")
PMJAY_PACKAGE_PATTERN = re.compile(r"^[A-Z]{2}\d{2,4}$")
PMJAY_ROWS_FILENAME = "pmjay_hbp_rows.json"
PMJAY_PACKAGES_FILENAME = "pmjay_hbp_packages.json"
CGHS_PACKAGES_FILENAME = "cghs_packages.json"
NPPA_PRICES_FILENAME = "nppa_medicine_prices.json"
BED_RATES_FILENAME = "bed_rates.json"
INVESTIGATION_RATES_FILENAME = "investigation_rates.json"
NA_VALUES = {"", "-", "--", "na", "n/a", "nil", "none"}


def save_json(filename: str, data: Any) -> None:
    path = REFERENCE_DIR / filename
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Saved: {path}")


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


def normalize_pdf_cell(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).replace("\r", "\n")
    text = re.sub(r"([A-Za-z])-\s*\n\s*([a-z])", r"\1\2", text)

    lines = [normalize_text(line) for line in text.split("\n") if normalize_text(line)]
    if not lines:
        return ""

    merged = lines[0]
    for line in lines[1:]:
        previous_token = merged.split(" ")[-1] if merged else ""
        next_token = line.split(" ")[0] if line else ""

        should_merge_word = (
            previous_token.isalpha()
            and next_token.isalpha()
            and next_token[0].islower()
            and len(previous_token) >= 6
            and len(next_token) <= 4
        )

        merged = f"{merged}{line}" if should_merge_word else f"{merged} {line}"

    return normalize_text(merged)


def is_na(value: Any) -> bool:
    return normalize_pdf_cell(value).lower() in NA_VALUES


def extract_numeric_values(value: Any) -> list[float]:
    text = normalize_pdf_cell(value)
    if not text:
        return []
    matches = re.findall(r"\d[\d,]*(?:\.\d+)?", text)
    numbers: list[float] = []
    for match in matches:
        try:
            numbers.append(float(match.replace(",", "")))
        except ValueError:
            continue
    return numbers


def parse_currency_value(value: Any) -> float | None:
    numbers = extract_numeric_values(value)
    if not numbers:
        return None
    return numbers[0]


def normalize_package_code(raw_code: Any) -> str:
    code = re.sub(r"[^A-Za-z0-9]", "", normalize_pdf_cell(raw_code)).upper()
    if not code:
        return ""
    match = re.match(r"^([A-Z]{2})(\d{2,4})$", code)
    if not match:
        return code
    prefix, digits = match.groups()
    return f"{prefix}{digits.zfill(3)}" if len(digits) < 3 else f"{prefix}{digits}"


def normalize_procedure_code(raw_code: Any, package_code: Any = "") -> str:
    code = re.sub(r"[^A-Za-z0-9]", "", normalize_pdf_cell(raw_code)).upper()
    if not code:
        return ""

    match = re.match(r"^([A-Z]{2})(\d{2,4})([A-Z0-9]{0,2})$", code)
    if not match:
        return code

    prefix, digits, suffix = match.groups()
    normalized_package = normalize_package_code(package_code)
    package_match = re.match(r"^([A-Z]{2})(\d{3,4})$", normalized_package)

    if package_match:
        package_prefix, package_digits = package_match.groups()
        if package_prefix == prefix and len(digits) < len(package_digits):
            digits = package_digits

    if len(digits) < 3:
        digits = digits.zfill(3)

    return f"{prefix}{digits}{suffix}"


def split_specialties(raw_text: Any) -> list[str]:
    specialty_text = normalize_pdf_cell(raw_text)
    if not specialty_text:
        return []

    values: list[str] = []
    seen: set[str] = set()
    for part in re.split(r"[,/;|]+", specialty_text):
        cleaned = normalize_text(part)
        if not cleaned:
            continue
        lowered = cleaned.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        values.append(cleaned)
    return values


def extract_pdf_lines(pdf_path: Path) -> list[str]:
    if fitz is None:
        raise RuntimeError("PyMuPDF is not installed. Install it with `pip install pymupdf`.")

    doc = fitz.open(pdf_path)
    lines: list[str] = []
    for page in doc:
        page_text = page.get_text("text")
        for raw_line in page_text.splitlines():
            line = raw_line.strip()
            if line:
                lines.append(normalize_text(line))
    doc.close()
    return lines


def extract_pdf_block_rows(pdf_path: Path) -> list[tuple[float, float, str]]:
    if fitz is None:
        raise RuntimeError("PyMuPDF is not installed. Install it with `pip install pymupdf`.")

    doc = fitz.open(pdf_path)
    rows = []
    for page in doc:
        blocks = page.get_text("blocks")
        for block in blocks:
            if len(block) < 5:
                continue
            x0, y0, *_rest, text = block[:5]
            cleaned = normalize_text(text)
            if cleaned:
                rows.append((x0, y0, cleaned))
    doc.close()
    return rows


def parse_cghs_packages() -> list[dict[str, Any]]:
    pdf_path = SOURCE_DIR / "cghs_rates.pdf"
    if not pdf_path.exists():
        raise FileNotFoundError(pdf_path)

    lines = extract_pdf_lines(pdf_path)
    packages = []
    current = None

    code_pattern = re.compile(r"^(?:\d+\s+)?([A-Z]{2,4}\d{3})(?:\s+(.+))?$")
    price_pattern = re.compile(r"^\d{1,6}(?:\.\d+)?$")

    for line in lines:
        if line.startswith("CGHS rates") or line.startswith("Sr.") or line.startswith("Page"):
            continue

        match = code_pattern.match(line)
        if match:
            code = match.group(1).strip()
            name = match.group(2) or ""
            if current and current.get("packageCode"):
                packages.append(current)

            current = {
                "packageCode": f"CGHS-{code}",
                "packageName": normalize_text(name) if name else "",
                "specialties": [],
                "caseTypes": [],
                "admissionTypes": [],
                "bedTypes": [],
                "basePrice": None,
                "rateTiers": [],
                "typicalLengthOfStayDays": 1,
                "category": "CGHS",
                "description": "",
                "source": "CGHS official package PDF",
            }
            continue

        if current is None:
            continue

        if price_pattern.match(line):
            current["rateTiers"].append(float(line))
            continue

        if line.upper() in {"NA", "N/A", "NA."}:
            current["rateTiers"].append(None)
            continue

        if not current.get("packageName") and not re.search(r"\d", line):
            if not current["packageName"]:
                current["packageName"] = line
                continue

        classification_line = re.sub(r"[^A-Za-z &/\-]", "", line)
        if classification_line and len(classification_line.split()) <= 5 and not re.search(r"\d", classification_line):
            current["description"] = (current["description"] + " " + line).strip()
            continue

        current["description"] = (current["description"] + " " + line).strip()

    if current and current.get("packageCode"):
        packages.append(current)

    for package in packages:
        if package["basePrice"] is None:
            tiers = [price for price in package["rateTiers"] if isinstance(price, (int, float))]
            package["basePrice"] = tiers[1] if len(tiers) >= 2 else tiers[0] if tiers else 0.0
        if not package["description"]:
            package["description"] = package["packageName"]
        if not package["packageName"]:
            package["packageName"] = package["description"]

    consolidated = consolidate_cghs_packages(packages)
    print(f"Parsed {len(consolidated)} CGHS packages")
    return consolidated


def consolidate_cghs_packages(packages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}

    for package in packages:
        code = normalize_text(str(package.get("packageCode", ""))).upper()
        if not code:
            continue

        bucket = grouped.setdefault(
            code,
            {
                "packageCode": package.get("packageCode"),
                "packageNameOptions": [],
                "descriptionOptions": [],
                "rates": [],
                "specialties": [],
                "caseTypes": [],
                "admissionTypes": [],
                "bedTypes": [],
                "source": package.get("source", "CGHS official package PDF"),
            },
        )

        package_name = normalize_pdf_cell(package.get("packageName", ""))
        if package_name:
            bucket["packageNameOptions"].append(package_name)

        description = normalize_pdf_cell(package.get("description", ""))
        if description:
            bucket["descriptionOptions"].append(description)

        base_price = package.get("basePrice")
        if isinstance(base_price, (int, float)) and base_price > 0:
            bucket["rates"].append(float(base_price))

        for rate in package.get("rateTiers", []):
            if isinstance(rate, (int, float)) and rate > 0:
                bucket["rates"].append(float(rate))

        for key in ("specialties", "caseTypes", "admissionTypes", "bedTypes"):
            values = [normalize_pdf_cell(value) for value in package.get(key, []) if normalize_pdf_cell(value)]
            bucket[key].extend(values)

    consolidated: list[dict[str, Any]] = []
    for code, bucket in sorted(grouped.items(), key=lambda item: item[0]):
        unique_rates = sorted({round(rate, 2) for rate in bucket["rates"] if rate > 0})
        if not unique_rates:
            unique_rates = [0.0]

        if len(unique_rates) == 1:
            rate_tiers = [unique_rates[0], unique_rates[0], unique_rates[0]]
            base_price = unique_rates[0]
        elif len(unique_rates) == 2:
            rate_tiers = [unique_rates[0], unique_rates[1], unique_rates[1]]
            base_price = unique_rates[1]
        else:
            rate_tiers = [unique_rates[0], unique_rates[len(unique_rates) // 2], unique_rates[-1]]
            base_price = rate_tiers[1]

        package_name = choose_name(bucket["packageNameOptions"]) or code
        description = choose_name(bucket["descriptionOptions"]) or package_name

        consolidated.append(
            {
                "packageCode": bucket["packageCode"] or code,
                "packageName": package_name,
                "specialties": sorted({value for value in bucket["specialties"] if value}),
                "caseTypes": sorted({value for value in bucket["caseTypes"] if value}),
                "admissionTypes": sorted({value for value in bucket["admissionTypes"] if value}),
                "bedTypes": sorted({value for value in bucket["bedTypes"] if value}),
                "basePrice": float(base_price),
                "rateTiers": [float(rate) if isinstance(rate, (int, float)) else None for rate in rate_tiers],
                "typicalLengthOfStayDays": 1,
                "category": "CGHS",
                "description": description,
                "source": bucket["source"],
            }
        )

    return consolidated


def parse_pmjay_table_row(raw_row: list[Any], page_number: int) -> dict[str, Any] | None:
    row = list(raw_row or [])
    if len(row) < 12:
        row.extend([""] * (12 - len(row)))
    row = row[:12]
    cells = [normalize_pdf_cell(cell) for cell in row]

    if not any(cells):
        return None

    if cells[0].lower() == "specialty" or "procedure code" in cells[4].lower():
        return None

    if "package master - hbp-2022" in cells[0].lower():
        return None

    package_code = normalize_package_code(cells[2])
    procedure_code = normalize_procedure_code(cells[4], package_code)

    if not procedure_code or not PMJAY_PROCEDURE_PATTERN.match(procedure_code):
        return None

    if not package_code:
        match = re.match(r"^([A-Z]{2}\d{2,4})", procedure_code)
        package_code = match.group(1) if match else ""

    return {
        "sourcePage": int(page_number),
        "specialty": cells[0],
        "specialtyCode": re.sub(r"[^A-Za-z0-9]", "", cells[1]).upper(),
        "hbpPackageCode": package_code,
        "abPmjayPackageName": cells[3],
        "hbpProcedureCode": procedure_code,
        "procedureName2022": cells[5],
        "tier3Z": cells[6],
        "tier2Y": cells[7],
        "tier1X": cells[8],
        "implantMapped": cells[9],
        "implantCost": cells[10],
        "stratificationRemarks": cells[11],
    }


def extract_pmjay_rows(
    pdf_path: Path,
    page_chunk_size: int = 5,
    page_start: int = 1,
    page_end: int | None = None,
) -> list[dict[str, Any]]:
    if pdfplumber is None:
        raise RuntimeError("pdfplumber is not installed. Install it with `pip install pdfplumber`.")
    if page_chunk_size <= 0:
        raise ValueError("page_chunk_size must be greater than 0.")

    rows: list[dict[str, Any]] = []
    with pdfplumber.open(pdf_path) as document:
        total_pages = len(document.pages)
        start = max(1, int(page_start))
        end = total_pages if page_end is None else min(total_pages, max(start, int(page_end)))

        for chunk_start in range(start, end + 1, page_chunk_size):
            chunk_end = min(chunk_start + page_chunk_size - 1, end)
            print(f"Extracting PM-JAY pages {chunk_start}-{chunk_end}...")

            for page_number in range(chunk_start, chunk_end + 1):
                page = document.pages[page_number - 1]
                tables = page.extract_tables() or []
                for table in tables:
                    for raw_row in table:
                        parsed_row = parse_pmjay_table_row(raw_row, page_number)
                        if parsed_row:
                            rows.append(parsed_row)

    print(f"Extracted {len(rows)} PM-JAY table rows from pages {start}-{end}")
    return rows


def pmjay_rows_to_dataframe(rows: list[dict[str, Any]]):
    if pd is None:
        raise RuntimeError("pandas is not installed. Install it with `pip install pandas`.")

    dataframe = pd.DataFrame(rows)
    if dataframe.empty:
        return dataframe

    for col in ["tier3Z", "tier2Y", "tier1X", "implantCost"]:
        dataframe[col] = dataframe[col].map(parse_currency_value)

    return dataframe


def choose_name(candidates: list[str]) -> str:
    values = [normalize_pdf_cell(item) for item in candidates if normalize_pdf_cell(item)]
    if not values:
        return ""

    frequency = Counter(value.lower() for value in values)
    top_count = max(frequency.values())
    top_candidates = [value for value in values if frequency[value.lower()] == top_count]
    return max(top_candidates, key=len)


def choose_rate(values: list[float | None]) -> float | None:
    numeric_values = [float(value) for value in values if isinstance(value, (int, float))]
    positive_values = [value for value in numeric_values if value > 0]
    if positive_values:
        return float(max(positive_values))
    if any(value == 0 for value in numeric_values):
        return 0.0
    return None


def choose_median_rate(values: list[float | None]) -> float | None:
    numeric_values = sorted([float(value) for value in values if isinstance(value, (int, float)) and value > 0])
    if not numeric_values:
        return None

    mid = len(numeric_values) // 2
    if len(numeric_values) % 2 == 1:
        return float(numeric_values[mid])
    return float((numeric_values[mid - 1] + numeric_values[mid]) / 2.0)


def _parse_named_rate(text: str, pattern: str) -> float | None:
    match = re.search(pattern, text, flags=re.IGNORECASE)
    if not match:
        return None

    value = match.group(1)
    numbers = extract_numeric_values(value)
    if not numbers:
        return None
    return float(numbers[0])


def parse_pmjay_stratification_bed_rates(note: str) -> dict[str, float]:
    normalized = normalize_pdf_cell(note)
    if not normalized:
        return {}

    rates = {
        "routineWardRate": _parse_named_rate(normalized, r"routine\s*ward\s*[-:]\s*([\d,]+(?:\.\d+)?)"),
        "hduRate": _parse_named_rate(normalized, r"hdu\s*[-:]\s*([\d,]+(?:\.\d+)?)"),
        "icuRate": _parse_named_rate(
            normalized,
            r"icu\s*(?:\(\s*without\s*ventilator\s*\))?\s*[-:]\s*([\d,]+(?:\.\d+)?)",
        ),
        "icuVentilatorRate": _parse_named_rate(
            normalized,
            r"icu\s*\(\s*with\s*ventilator\s*\)\s*[-:]\s*([\d,]+(?:\.\d+)?)",
        ),
    }

    return {key: float(value) for key, value in rates.items() if isinstance(value, (int, float)) and value > 0}


def derive_base_price(
    tier3_value: float | None,
    tier2_value: float | None,
    tier1_value: float | None,
    stratification_notes: list[str],
    implant_cost_value: float | None,
) -> float:
    if isinstance(tier2_value, (int, float)) and tier2_value > 0:
        return float(tier2_value)
    if isinstance(tier1_value, (int, float)) and tier1_value > 0:
        return float(tier1_value)
    if isinstance(tier3_value, (int, float)) and tier3_value > 0:
        return float(tier3_value)

    fallback_values: list[float] = []
    for note in stratification_notes:
        fallback_values.extend([value for value in extract_numeric_values(note) if value > 0])

    if fallback_values:
        return float(max(fallback_values))

    if isinstance(implant_cost_value, (int, float)) and implant_cost_value > 0:
        return float(implant_cost_value)

    return 0.0


def merge_text_parts(values: list[str], max_parts: int = 2) -> str:
    merged: list[str] = []
    seen: set[str] = set()
    for value in values:
        cleaned = normalize_pdf_cell(value)
        if not cleaned:
            continue
        lowered = cleaned.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        merged.append(cleaned)
        if len(merged) >= max_parts:
            break
    return " | ".join(merged)


def build_pmjay_packages_from_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}

    for row in rows:
        procedure_code = normalize_procedure_code(row.get("hbpProcedureCode", ""), row.get("hbpPackageCode", ""))
        if not procedure_code or not PMJAY_PROCEDURE_PATTERN.match(procedure_code):
            continue

        package_code = normalize_package_code(row.get("hbpPackageCode", ""))
        if not package_code:
            match = re.match(r"^([A-Z]{2}\d{2,4})", procedure_code)
            package_code = match.group(1) if match else ""

        if package_code and not PMJAY_PACKAGE_PATTERN.match(package_code):
            package_code = ""

        bucket = grouped.setdefault(
            procedure_code,
            {
                "procedureCode": procedure_code,
                "packageCode": package_code,
                "specialties": [],
                "specialtySeen": set(),
                "abNames": [],
                "procedureNames": [],
                "tier3Values": [],
                "tier2Values": [],
                "tier1Values": [],
                "implantCostValues": [],
                "implantNotes": [],
                "stratificationNotes": [],
                "sourcePages": [],
                "routineWardRates": [],
                "hduRates": [],
                "icuRates": [],
                "icuVentilatorRates": [],
            },
        )

        if not bucket["packageCode"] and package_code:
            bucket["packageCode"] = package_code

        for specialty in split_specialties(row.get("specialty", "")):
            lowered = specialty.lower()
            if lowered not in bucket["specialtySeen"]:
                bucket["specialtySeen"].add(lowered)
                bucket["specialties"].append(specialty)

        ab_name = normalize_pdf_cell(row.get("abPmjayPackageName", ""))
        if ab_name:
            bucket["abNames"].append(ab_name)

        procedure_name = normalize_pdf_cell(row.get("procedureName2022", ""))
        if procedure_name:
            bucket["procedureNames"].append(procedure_name)

        bucket["tier3Values"].append(parse_currency_value(row.get("tier3Z")))
        bucket["tier2Values"].append(parse_currency_value(row.get("tier2Y")))
        bucket["tier1Values"].append(parse_currency_value(row.get("tier1X")))
        bucket["implantCostValues"].append(parse_currency_value(row.get("implantCost")))

        implant_note = normalize_pdf_cell(row.get("implantMapped", ""))
        if implant_note and not is_na(implant_note):
            bucket["implantNotes"].append(implant_note)

        stratification_note = normalize_pdf_cell(row.get("stratificationRemarks", ""))
        if stratification_note and not is_na(stratification_note):
            bucket["stratificationNotes"].append(stratification_note)
            bed_rates = parse_pmjay_stratification_bed_rates(stratification_note)
            if "routineWardRate" in bed_rates:
                bucket["routineWardRates"].append(bed_rates["routineWardRate"])
            if "hduRate" in bed_rates:
                bucket["hduRates"].append(bed_rates["hduRate"])
            if "icuRate" in bed_rates:
                bucket["icuRates"].append(bed_rates["icuRate"])
            if "icuVentilatorRate" in bed_rates:
                bucket["icuVentilatorRates"].append(bed_rates["icuVentilatorRate"])

        source_page = row.get("sourcePage")
        if isinstance(source_page, int):
            bucket["sourcePages"].append(source_page)

    packages: list[dict[str, Any]] = []
    for procedure_code, bucket in sorted(grouped.items(), key=lambda item: item[0]):
        tier3_value = choose_rate(bucket["tier3Values"])
        tier2_value = choose_rate(bucket["tier2Values"])
        tier1_value = choose_rate(bucket["tier1Values"])
        implant_cost_value = choose_rate(bucket["implantCostValues"])
        routine_ward_rate = choose_median_rate(bucket["routineWardRates"])
        hdu_rate = choose_median_rate(bucket["hduRates"])
        icu_rate = choose_median_rate(bucket["icuRates"])
        icu_ventilator_rate = choose_median_rate(bucket["icuVentilatorRates"])

        rate_tiers: list[float | None] = [tier3_value, tier2_value, tier1_value]
        base_price = derive_base_price(
            tier3_value,
            tier2_value,
            tier1_value,
            bucket["stratificationNotes"],
            implant_cost_value,
        )

        procedure_name = choose_name(bucket["procedureNames"])
        ab_name = choose_name(bucket["abNames"])
        package_name = ab_name or procedure_name or procedure_code

        description_candidates = [package_name]
        if procedure_name and procedure_name.lower() != package_name.lower():
            description_candidates.append(procedure_name)
        if ab_name and ab_name.lower() != package_name.lower():
            description_candidates.append(ab_name)
        if bucket["stratificationNotes"]:
            description_candidates.append(merge_text_parts(bucket["stratificationNotes"], max_parts=1))

        description_parts: list[str] = []
        seen_parts: set[str] = set()
        for candidate in description_candidates:
            cleaned = normalize_pdf_cell(candidate)
            if not cleaned:
                continue
            lowered = cleaned.lower()
            if lowered in seen_parts:
                continue
            seen_parts.add(lowered)
            description_parts.append(cleaned)

        description = " ".join(description_parts).strip() or package_name
        has_dynamic_bed_pricing = any(
            isinstance(rate, (int, float)) and rate > 0
            for rate in [routine_ward_rate, hdu_rate, icu_rate, icu_ventilator_rate]
        )

        pricing_model = "bed_daily_rate" if has_dynamic_bed_pricing else "tier_package"
        matched_procedures = [procedure_code]
        source_pages = sorted({int(page) for page in bucket["sourcePages"] if isinstance(page, int)})

        packages.append(
            {
                "packageCode": f"PMJAY-{procedure_code}",
                "packageName": package_name,
                "specialties": bucket["specialties"],
                "caseTypes": [],
                "admissionTypes": [],
                "bedTypes": [],
                "basePrice": float(base_price),
                "rateTiers": rate_tiers,
                "typicalLengthOfStayDays": 1,
                "category": "PM-JAY/HBP",
                "description": description,
                "source": "PM-JAY HBP official package PDF (pdfplumber local extraction)",
                "pricingModel": pricing_model,
                "routineWardRate": routine_ward_rate,
                "hduRate": hdu_rate,
                "icuRate": icu_rate,
                "icuVentilatorRate": icu_ventilator_rate,
                "officialRateBreakdown": {
                    "tier3ZRate": tier3_value,
                    "tier2YRate": tier2_value,
                    "tier1XRate": tier1_value,
                    "routineWardRate": routine_ward_rate,
                    "hduRate": hdu_rate,
                    "icuRate": icu_rate,
                    "icuVentilatorRate": icu_ventilator_rate,
                },
                "matchedProcedures": matched_procedures,
                "sourcePages": source_pages,
            }
        )

    print(f"Parsed {len(packages)} PM-JAY packages")
    return packages


def parse_pmjay_packages(
    page_chunk_size: int = 5,
    page_start: int = 1,
    page_end: int | None = None,
) -> list[dict[str, Any]]:
    pdf_path = SOURCE_DIR / "pmjay_hbp.pdf"
    if not pdf_path.exists():
        raise FileNotFoundError(pdf_path)

    rows = extract_pmjay_rows(
        pdf_path,
        page_chunk_size=page_chunk_size,
        page_start=page_start,
        page_end=page_end,
    )

    if pd is None:
        raise RuntimeError("pandas is not installed. Install it with `pip install pandas`.")

    dataframe = pmjay_rows_to_dataframe(rows)
    row_records = json.loads(dataframe.to_json(orient="records", force_ascii=False))
    save_json(PMJAY_ROWS_FILENAME, row_records)

    packages = build_pmjay_packages_from_rows(row_records)
    save_json(PMJAY_PACKAGES_FILENAME, packages)
    return packages


def parse_nppa_prices() -> list[dict[str, Any]]:
    pdf_path = SOURCE_DIR / "nppa_prices.pdf"
    if not pdf_path.exists():
        raise FileNotFoundError(pdf_path)

    lines = extract_pdf_lines(pdf_path)
    medicines = []
    current = None

    start_pattern = re.compile(r"^(\d+)\.\s+(.+)$")
    price_pattern = re.compile(r"^(\d+(?:\.\d+)?)$")

    for line in lines:
        start_match = start_pattern.match(line)
        if start_match:
            if current and current.get("medicineName"):
                medicines.append(current)
            current = {
                "medicineName": normalize_text(start_match.group(2)),
                "keywords": [word.lower() for word in re.split(r"[^a-zA-Z0-9]+", start_match.group(2)) if len(word) > 2],
                "ceilingPrice": None,
                "unitPrice": None,
                "unit": "unit",
                "source": "NPPA official price list",
            }
            continue

        if current is None:
            continue

        price_match = price_pattern.match(line)
        if price_match and current["ceilingPrice"] is None:
            current["ceilingPrice"] = float(price_match.group(1))
            continue

        if line.startswith("S.O") or line.startswith("Price revised") or line.startswith("vide") or line.startswith("dated"):
            continue

        if line.upper().startswith("TABLET") or line.upper().startswith("INJECTION") or line.upper().startswith("SUPPOSITORY"):
            current["unit"] = line.split()[0].title()
            continue

        if current["ceilingPrice"] is None and re.search(r"\d+\.?\d*$", line):
            num_match = re.search(r"(\d+(?:\.\d+)?)$", line)
            if num_match:
                current["ceilingPrice"] = float(num_match.group(1))
                continue

        if line and not re.search(r"\d", line):
            current["keywords"].extend([word.lower() for word in re.split(r"[^a-zA-Z0-9]+", line) if len(word) > 2])

    if current and current.get("medicineName"):
        medicines.append(current)

    cleaned_medicines: list[dict[str, Any]] = []
    for item in medicines:
        ceiling_price = item.get("ceilingPrice")
        if ceiling_price is None:
            continue

        keyword_values = [
            normalize_text(keyword).lower()
            for keyword in item.get("keywords", [])
            if normalize_text(keyword)
        ]
        deduped_keywords = sorted(dict.fromkeys(keyword_values))

        cleaned_medicines.append(
            {
                "medicineName": item.get("medicineName"),
                "keywords": deduped_keywords,
                "ceilingPrice": float(ceiling_price),
                "unitPrice": float(ceiling_price),
                "unit": normalize_text(item.get("unit", "unit")) or "unit",
                "source": item.get("source", "NPPA official price list"),
            }
        )

    medicines = cleaned_medicines
    print(f"Parsed {len(medicines)} NPPA medicine prices")
    return medicines


def _search_cghs_prices(
    cghs_packages: list[dict[str, Any]],
    include_patterns: list[str],
    exclude_patterns: list[str] | None = None,
) -> list[float]:
    excludes = [re.compile(pattern, re.IGNORECASE) for pattern in (exclude_patterns or [])]
    includes = [re.compile(pattern, re.IGNORECASE) for pattern in include_patterns]

    values: list[float] = []
    for package in cghs_packages:
        text = normalize_pdf_cell(f"{package.get('packageName', '')} {package.get('description', '')}")
        if not text:
            continue

        if any(ex.search(text) for ex in excludes):
            continue

        if not any(pattern.search(text) for pattern in includes):
            continue

        price = package.get("basePrice")
        if isinstance(price, (int, float)) and price > 0:
            values.append(float(price))

    return values


def _median_or_fallback(values: list[float], fallback: float) -> int:
    if not values:
        return int(round(fallback))

    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2 == 1:
        return int(round(ordered[mid]))
    return int(round((ordered[mid - 1] + ordered[mid]) / 2.0))


def derive_bed_rates(
    cghs_packages: list[dict[str, Any]],
    pmjay_packages: list[dict[str, Any]],
) -> dict[str, int]:
    pmjay_routine = [
        float(package.get("routineWardRate"))
        for package in pmjay_packages
        if isinstance(package.get("routineWardRate"), (int, float)) and float(package.get("routineWardRate")) > 0
    ]
    pmjay_hdu = [
        float(package.get("hduRate"))
        for package in pmjay_packages
        if isinstance(package.get("hduRate"), (int, float)) and float(package.get("hduRate")) > 0
    ]
    pmjay_icu = [
        float(package.get("icuRate"))
        for package in pmjay_packages
        if isinstance(package.get("icuRate"), (int, float)) and float(package.get("icuRate")) > 0
    ]
    pmjay_icu_vent = [
        float(package.get("icuVentilatorRate"))
        for package in pmjay_packages
        if isinstance(package.get("icuVentilatorRate"), (int, float)) and float(package.get("icuVentilatorRate")) > 0
    ]

    cghs_icu = _search_cghs_prices(cghs_packages, [r"\bicu\b|\bccu\b|\bpicu\b|\bmicu\b|\bhdu\b"])
    cghs_ventilator = _search_cghs_prices(
        cghs_packages,
        [r"\bventilator\b"],
        exclude_patterns=[r"\bnon\s*invasive\b"],
    )
    cghs_daycare = _search_cghs_prices(cghs_packages, [r"day\s*care|daycare"])

    general_ward_rate = _median_or_fallback(pmjay_routine, 3000)
    hdu_rate = _median_or_fallback(pmjay_hdu, max(general_ward_rate * 1.5, 3600))
    icu_rate = _median_or_fallback(pmjay_icu + cghs_icu, max(hdu_rate * 1.6, 5400))
    icu_ventilator_rate = _median_or_fallback(
        pmjay_icu_vent + [rate + _median_or_fallback(cghs_ventilator, 2700) for rate in pmjay_icu],
        max(icu_rate + 1200, 6500),
    )
    daycare_rate = max(
        _median_or_fallback(cghs_daycare, max(int(round(general_ward_rate * 0.85)), 2200)),
        min(general_ward_rate, 2200),
    )
    emergency_observation = max(
        _median_or_fallback([general_ward_rate * 1.1, hdu_rate * 0.8], max(general_ward_rate, 2800)),
        general_ward_rate,
    )

    return {
        "ICU": int(icu_rate),
        "HDU": int(hdu_rate),
        "General Ward": int(general_ward_rate),
        "Daycare": int(daycare_rate),
        "Emergency Observation": int(emergency_observation),
        "ICU with Ventilator": int(icu_ventilator_rate),
    }


def derive_investigation_rates(cghs_packages: list[dict[str, Any]]) -> dict[str, int]:
    code_lookup: dict[str, list[float]] = {}
    for package in cghs_packages:
        code = normalize_pdf_cell(package.get("packageCode", "")).upper()
        price = package.get("basePrice")
        if not code or not isinstance(price, (int, float)) or float(price) <= 0:
            continue
        code_lookup.setdefault(code, []).append(float(price))

    def _rates_for_codes(codes: list[str]) -> list[float]:
        values: list[float] = []
        for code in codes:
            values.extend(code_lookup.get(code.upper(), []))
        return values

    investigation_patterns: dict[str, list[str]] = {
        "cbc": [r"\bcbc\b", r"complete\s+haemogram", r"complete\s+blood\s+count"],
        "renal function test": [r"\bkft\b", r"kidney\s+function\s+test", r"renal\s+function"],
        "liver function test": [r"\blft\b", r"liver\s+function\s+test"],
        "electrolytes": [r"electrolyte"],
        "ecg": [r"\becg\b", r"electrocardiogram"],
        "echocardiogram": [r"echocardiography", r"echocardiogram", r"\btee\b"],
        "chest x-ray": [r"x[\s-]?ray\s+chest"],
        "ct scan": [r"\bct\s*scan\b", r"computed\s+tomography"],
        "mri": [r"\bmri\b"],
        "blood culture": [r"blood\s+culture"],
        "urine culture": [r"urine\s+culture"],
        "dialysis": [r"\bdialysis\b", r"haemodialysis", r"hemodialysis"],
        "ventilator support": [r"\bventilator\b"],
        "oxygen therapy": [r"oxygen"],
        "pathology panel": [r"\bprofile\b", r"panel"],
        "histopathology": [r"histopathology", r"\bhpe\b"],
        "biopsy": [r"\bbiopsy\b"],
        "consultation charges": [r"consultation\s+opd", r"consultation\s+for\s+inpatients"],
        "icu investigations": [r"critical\s+care", r"\bicu\b|\bhdu\b"],
    }

    exclusions: dict[str, list[str]] = {
        "dialysis": [r"iridodialysis"],
        "biopsy": [r"biopsy\s+gun"],
    }

    fallback_rates: dict[str, float] = {
        "cbc": 300,
        "renal function test": 500,
        "liver function test": 500,
        "electrolytes": 800,
        "ecg": 175,
        "echocardiogram": 1500,
        "chest x-ray": 230,
        "ct scan": 3000,
        "mri": 4000,
        "blood culture": 650,
        "urine culture": 350,
        "dialysis": 6000,
        "ventilator support": 3000,
        "oxygen therapy": 100,
        "pathology panel": 1500,
        "histopathology": 850,
        "biopsy": 3000,
        "consultation charges": 350,
        "icu investigations": 5400,
    }
    code_overrides: dict[str, list[str]] = {
        "cbc": ["CGHS-LB012"],
        "renal function test": ["CGHS-LB123"],
        "liver function test": ["CGHS-LB124"],
        "electrolytes": ["CGHS-LB120"],
        "ecg": ["CGHS-CI001"],
        "echocardiogram": ["CGHS-RI001"],
        "chest x-ray": ["CGHS-RI034", "CGHS-RI035"],
        "ventilator support": ["CGHS-CC003"],
        "oxygen therapy": ["CGHS-CC002"],
        "histopathology": ["CGHS-LB050", "CGHS-LB051"],
        "consultation charges": ["CGHS-CN001", "CGHS-CN002", "CGHS-CN003"],
        "icu investigations": ["CGHS-CC001"],
    }

    rates: dict[str, int] = {}
    for key, patterns in investigation_patterns.items():
        override_values = _rates_for_codes(code_overrides.get(key, []))
        values = override_values or _search_cghs_prices(cghs_packages, patterns, exclude_patterns=exclusions.get(key))
        rates[key] = _median_or_fallback(values, fallback_rates[key])

    return rates


def build_reference_files(
    pmjay_page_chunk_size: int = 5,
    pmjay_page_start: int = 1,
    pmjay_page_end: int | None = None,
) -> None:
    cghs = parse_cghs_packages()
    pmjay = parse_pmjay_packages(
        page_chunk_size=pmjay_page_chunk_size,
        page_start=pmjay_page_start,
        page_end=pmjay_page_end,
    )
    nppa = parse_nppa_prices()
    bed_rates = derive_bed_rates(cghs, pmjay)
    investigation_rates = derive_investigation_rates(cghs)

    save_json(CGHS_PACKAGES_FILENAME, cghs)
    save_json(PMJAY_PACKAGES_FILENAME, pmjay)
    save_json(NPPA_PRICES_FILENAME, nppa)
    save_json(BED_RATES_FILENAME, bed_rates)
    save_json(INVESTIGATION_RATES_FILENAME, investigation_rates)

    save_json("hospital_packages.json", cghs + pmjay)
    save_json("medicine_prices.json", nppa)

    print("Completed ingestion of official source files.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest official source PDFs into JSON reference files.")
    parser.add_argument(
        "--pmjay-page-chunk-size",
        type=int,
        default=5,
        help="Number of PM-JAY PDF pages to process per extraction chunk.",
    )
    parser.add_argument(
        "--pmjay-page-start",
        type=int,
        default=1,
        help="Start page for PM-JAY extraction (1-indexed).",
    )
    parser.add_argument(
        "--pmjay-page-end",
        type=int,
        default=None,
        help="End page for PM-JAY extraction (1-indexed, inclusive).",
    )
    parser.add_argument(
        "--only-pmjay",
        action="store_true",
        help="Run only PM-JAY extraction and save pmjay_hbp_rows.json + pmjay_hbp_packages.json.",
    )
    parser.add_argument(
        "--only-cghs",
        action="store_true",
        help="Run only CGHS extraction and save cghs_packages.json.",
    )
    parser.add_argument(
        "--only-nppa",
        action="store_true",
        help="Run only NPPA extraction and save nppa_medicine_prices.json + medicine_prices.json.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.only_pmjay:
        parse_pmjay_packages(
            page_chunk_size=args.pmjay_page_chunk_size,
            page_start=args.pmjay_page_start,
            page_end=args.pmjay_page_end,
        )
        return

    if args.only_cghs:
        cghs = parse_cghs_packages()
        save_json(CGHS_PACKAGES_FILENAME, cghs)
        return

    if args.only_nppa:
        nppa = parse_nppa_prices()
        save_json(NPPA_PRICES_FILENAME, nppa)
        save_json("medicine_prices.json", nppa)
        return

    build_reference_files(
        pmjay_page_chunk_size=args.pmjay_page_chunk_size,
        pmjay_page_start=args.pmjay_page_start,
        pmjay_page_end=args.pmjay_page_end,
    )


if __name__ == "__main__":
    main()
