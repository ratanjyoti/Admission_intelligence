from typing import Any

from backend.revenue_knowledge import (
    estimate_bed_rate,
    estimate_consumables_cost,
    estimate_investigation_cost,
    estimate_length_of_stay,
    estimate_medicine_cost,
    infer_treatment_bundle,
)


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).lower().split())


def _choose_dynamic_package_rate(
    bundle: dict[str, Any],
    bed_type: str,
    patient: dict[str, Any],
    signals: dict[str, bool],
) -> tuple[float | None, str | None]:
    rate_options = {
        "routineWardRate": bundle.get("routineWardRate"),
        "hduRate": bundle.get("hduRate"),
        "icuRate": bundle.get("icuRate"),
        "icuVentilatorRate": bundle.get("icuVentilatorRate"),
    }
    parsed_options = {
        key: float(value)
        for key, value in rate_options.items()
        if isinstance(value, (int, float)) and float(value) > 0
    }
    if not parsed_options:
        return None, None

    bed_text = _normalize_text(bed_type)
    clinical_text = _normalize_text(
        " ".join(
            [
                patient.get("clinical", {}).get("clinicalNotes", ""),
                patient.get("clinical", {}).get("vitalRemarks", ""),
                patient.get("clinical", {}).get("physicalRemarks", ""),
                patient.get("clinical", {}).get("diagnosis", ""),
            ]
        )
    )

    combined_text = f"{bed_text} {clinical_text}".strip()
    positive_ventilator_signals = [
        "icu with ventilator",
        "with ventilator",
        "on ventilator",
        "ventilator support",
        "mechanical ventilation",
        "ventilatory support",
        "intubated",
    ]
    negative_ventilator_signals = [
        "no ventilator",
        "without ventilator",
        "not on ventilator",
        "off ventilator",
        "no need for ventilator",
        "no ventilator required",
    ]

    if any(signal in combined_text for signal in positive_ventilator_signals):
        ventilator_needed = True
    elif any(signal in combined_text for signal in negative_ventilator_signals):
        ventilator_needed = False
    else:
        ventilator_needed = "ventilator" in combined_text

    preferred_keys: list[str] = []
    if "hdu" in bed_text:
        preferred_keys.append("hduRate")
    elif "icu" in bed_text or signals.get("icu"):
        if ventilator_needed:
            preferred_keys.append("icuVentilatorRate")
        preferred_keys.append("icuRate")
        preferred_keys.append("hduRate")
    else:
        if signals.get("major_procedure"):
            preferred_keys.append("hduRate")
            preferred_keys.append("routineWardRate")
        else:
            preferred_keys.append("routineWardRate")
            preferred_keys.append("hduRate")
        preferred_keys.append("icuRate")

    if ventilator_needed:
        preferred_keys.insert(0, "icuVentilatorRate")

    preferred_keys.extend(["routineWardRate", "hduRate", "icuRate", "icuVentilatorRate"])

    for key in preferred_keys:
        value = parsed_options.get(key)
        if isinstance(value, (int, float)) and value > 0:
            return float(value), key

    return None, None


def _format_inr(amount: float) -> str:
    rounded = int(round(amount))
    if rounded < 100000:
        return f"Rs {rounded:,}".replace(",", ",")

    lakhs = rounded / 100000
    if lakhs.is_integer():
        return f"Rs {int(lakhs)}L"
    return f"Rs {lakhs:.1f}L"


def _format_price_range(min_amount: float, max_amount: float) -> str:
    return f"{_format_inr(min_amount)} - {_format_inr(max_amount)}"


def _derive_revenue_category(mid_lakhs: float) -> str:
    if mid_lakhs < 0.6:
        return "Standard Value"
    if mid_lakhs < 1.5:
        return "Moderate Value"
    if mid_lakhs < 2.5:
        return "Significant Value"
    if mid_lakhs < 4.0:
        return "High Value"
    return "Strategic Value"


def build_revenue_package_payload(
    patient: dict[str, Any],
    signals: dict[str, bool],
    case_type: str,
    length_of_stay: dict[str, Any] | None = None,
    clinical_plan: dict[str, Any] | None = None,
) -> dict[str, Any]:
    bundle = infer_treatment_bundle(patient, signals, case_type)
    bed_type = (
        clinical_plan.get("likelyBedType")
        if clinical_plan and clinical_plan.get("likelyBedType")
        else patient.get("bed", {}).get("type", "General Ward")
    )
    days = (
        int(clinical_plan.get("estimatedLOS"))
        if clinical_plan and clinical_plan.get("estimatedLOS")
        else estimate_length_of_stay(patient, length_of_stay)
    )
    bed_rate = estimate_bed_rate(bed_type)

    dynamic_rate, dynamic_rate_key = _choose_dynamic_package_rate(bundle, bed_type, patient, signals)

    bed_cost = bed_rate * max(1, days)
    investigation_cost = estimate_investigation_cost(patient)
    medicine_cost = estimate_medicine_cost(patient)
    consumables_cost = estimate_consumables_cost(patient, signals)

    base_price = float(bundle.get("basePrice", 0) or 0)
    package_cost = max(base_price, 0.0)
    pricing_model = "fixed_package_plus_bed"
    selected_official_rate = None

    if dynamic_rate is not None:
        package_cost = max(dynamic_rate * max(1, days), 0.0)
        bed_cost = 0.0
        selected_official_rate = float(dynamic_rate)
        pricing_model = "official_dynamic_bed_daily_rate"

    additional_cost = bed_cost + investigation_cost + medicine_cost + consumables_cost

    min_total = max(0.0, package_cost + additional_cost * 0.85)
    max_total = max(0.0, package_cost + additional_cost * 1.25)
    mid_total = (min_total + max_total) / 2.0

    min_lakhs = round(min_total / 100000, 2)
    max_lakhs = round(max_total / 100000, 2)
    mid_lakhs = round(mid_total / 100000, 2)

    score = 1
    if mid_lakhs >= 4.0:
        score = 10
    elif mid_lakhs >= 2.5:
        score = 8
    elif mid_lakhs >= 1.5:
        score = 6
    elif mid_lakhs >= 0.6:
        score = 4
    else:
        score = 2

    drivers = [
        "Package base price is selected from the hospital rate knowledge base.",
        f"Estimated {days} day(s) of bed support at {bed_rate}/day.",
        f"Investigation spend is estimated from documented tests and clinical notes.",
        "Medicine prices are approximated using standard drug price references.",
    ]
    if selected_official_rate is not None:
        drivers[0] = (
            f"Package uses official bed-linked PM-JAY rate ({selected_official_rate:.0f}/day) "
            f"based on bed type and clinical context."
        )
        drivers[1] = "Bed support is already represented in the official per-day package rate."
    if consumables_cost > 0:
        drivers.append("Consumables and intensive care add-ons raise the upper revenue band.")

    matched_procedures = bundle.get("matchedProcedures") or [bundle.get("packageCode")]

    return {
        "expectedRevenue": _format_price_range(min_total, max_total),
        "revenueCategory": _derive_revenue_category(mid_lakhs),
        "minLakhs": min_lakhs,
        "maxLakhs": max_lakhs,
        "midLakhs": mid_lakhs,
        "score": score,
        "bundle": {
            "packageCode": bundle.get("packageCode"),
            "packageName": bundle.get("packageName"),
            "category": bundle.get("category"),
            "description": bundle.get("description"),
            "basePrice": bundle.get("basePrice"),
            "pricingModel": pricing_model,
            "officialRateBreakdown": bundle.get("officialRateBreakdown", {}),
            "selectedDynamicRate": selected_official_rate,
            "selectedDynamicRateKey": dynamic_rate_key,
            "estimatedBedDays": days,
            "estimatedBedRate": bed_rate,
        },
        "components": {
            "basePrice": package_cost,
            "bedCost": bed_cost,
            "investigationCost": investigation_cost,
            "medicineCost": medicine_cost,
            "consumablesCost": consumables_cost,
            "totalMin": min_total,
            "totalMid": mid_total,
            "totalMax": max_total,
        },
        "revenueExplanation": {
            "selectedPackage": f"{bundle.get('packageCode')} - {bundle.get('packageName')}",
            "bedTypeUsed": bed_type,
            "officialSource": bundle.get("source", "Official package references"),
            "matchedProcedures": matched_procedures,
        },
        "drivers": drivers,
        "reasoning": " ".join(drivers[:3]),
    }


__all__ = ["build_revenue_package_payload"]
