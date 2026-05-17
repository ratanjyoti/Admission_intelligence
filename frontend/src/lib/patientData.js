const RISK_ORDER = ["Critical", "High", "Medium", "Low"];
const ADMISSION_ORDER = ["Emergency", "Urgent", "Elective"];

function safeDecode(value) {
  try {
    return decodeURIComponent(String(value || "").trim());
  } catch {
    return String(value || "").trim();
  }
}

function normalizeText(value) {
  return safeDecode(value).toLowerCase();
}

function sortByValueDescending(a, b, key = "name") {
  return b.value - a.value || String(a[key]).localeCompare(String(b[key]));
}

function sortByPreset(values, preset) {
  const order = new Map(preset.map((entry, index) => [entry, index]));

  return [...values].sort((a, b) => {
    const aIndex = order.get(a.name);
    const bIndex = order.get(b.name);

    if (aIndex !== undefined || bIndex !== undefined) {
      return (
        (aIndex ?? Number.MAX_SAFE_INTEGER) -
          (bIndex ?? Number.MAX_SAFE_INTEGER) ||
        b.value - a.value
      );
    }

    return sortByValueDescending(a, b);
  });
}

export function formatDate(value, options = { dateStyle: "medium" }) {
  if (!value) return "Not available";

  const normalizedValue = String(value).split(" ")[0];
  const parsedDate = new Date(normalizedValue);

  if (Number.isNaN(parsedDate.getTime())) {
    return String(value);
  }

  return new Intl.DateTimeFormat("en-IN", options).format(parsedDate);
}

export function findPatientById(patients, patientId) {
  const target = normalizeText(patientId);

  if (!target) {
    return null;
  }

  return (
    patients.find((patient) => {
      const candidates = [
        patient.patientId,
        patient.Patient_ID,
        patient.patient_id,
        patient.id,
      ]
        .map(normalizeText)
        .filter(Boolean);

      return candidates.some(
        (candidate) =>
          candidate === target ||
          candidate.includes(target) ||
          target.includes(candidate)
      );
    }) || null
  );
}

export function countBy(items, selector) {
  const counts = new Map();

  items.forEach((item) => {
    const value = selector(item) || "Unknown";
    counts.set(value, (counts.get(value) || 0) + 1);
  });

  return Array.from(counts.entries()).map(([name, value]) => ({ name, value }));
}

export function buildDashboardSummary(patients) {
  return {
    totalPatients: patients.length,
    criticalPatients: patients.filter((patient) => patient.risk?.category === "Critical").length,
    emergencyPatients: patients.filter((patient) => patient.admission?.type === "Emergency").length,
    icuPatients: patients.filter((patient) => patient.bed?.type === "ICU").length,
    repeatPatients: patients.filter((patient) => patient.journey?.repeatVisit === "Yes").length,
    validatedPatients: patients.filter((patient) => patient.validation?.status === "Validated").length,
    departmentCount: new Set(patients.map((patient) => patient.department || "Unknown")).size,
  };
}

export function buildDashboardCharts(patients) {
  const departmentMetrics = new Map();

  patients.forEach((patient) => {
    const department = patient.department || "Unknown";

    if (!departmentMetrics.has(department)) {
      departmentMetrics.set(department, {
        department,
        totalPatients: 0,
        criticalPatients: 0,
        icuDemand: 0,
        emergencyAdmissions: 0,
      });
    }

    const entry = departmentMetrics.get(department);
    entry.totalPatients += 1;

    if (patient.risk?.category === "Critical") {
      entry.criticalPatients += 1;
    }

    if (patient.bed?.type === "ICU") {
      entry.icuDemand += 1;
    }

    if (patient.admission?.type === "Emergency") {
      entry.emergencyAdmissions += 1;
    }
  });

  return {
    riskDistribution: sortByPreset(
      countBy(patients, (patient) => patient.risk?.category),
      RISK_ORDER
    ),
    admissionDistribution: sortByPreset(
      countBy(patients, (patient) => patient.admission?.type),
      ADMISSION_ORDER
    ),
    bedDistribution: countBy(patients, (patient) => patient.bed?.type).sort(sortByValueDescending),
    departmentMetrics: Array.from(departmentMetrics.values()).sort(
      (a, b) => b.totalPatients - a.totalPatients || a.department.localeCompare(b.department)
    ),
  };
}

function extractQuotedValue(text, key) {
  const match = text.match(new RegExp(`['"]?${key}['"]?\\s*:\\s*['"]([^'"]+)['"]`));
  return match ? match[1] : "";
}

function extractNumberValue(text, key) {
  const match = text.match(new RegExp(`['"]?${key}['"]?\\s*:\\s*(\\d+)`));
  return match ? Number(match[1]) : null;
}

export function parseTraceabilityString(text) {
  if (!text || typeof text !== "string") {
    return [];
  }

  const chunks = text.match(/\{[^{}]+\}/g) || [];

  return chunks
    .map((chunk) => ({
      category:
        extractQuotedValue(chunk, "category") ||
        extractQuotedValue(chunk, "cat") ||
        extractQuotedValue(chunk, "category_name"),
      keyword: extractQuotedValue(chunk, "keyword"),
      source_section:
        extractQuotedValue(chunk, "source_section") ||
        extractQuotedValue(chunk, "source") ||
        extractQuotedValue(chunk, "sourceSection"),
      evidence_snippet:
        extractQuotedValue(chunk, "evidence_snippet") ||
        extractQuotedValue(chunk, "evidence") ||
        extractQuotedValue(chunk, "snippet"),
    }))
    .filter(
      (item) =>
        item.category || item.keyword || item.source_section || item.evidence_snippet
    );
}

export function parseRiskProgression(patient) {
  const fallbackPoints = [
    {
      visit: patient.journey?.firstVisitDate
        ? formatDate(patient.journey.firstVisitDate, { day: "numeric", month: "short" })
        : "First Visit",
      risk:
        Number(patient.journey?.firstVisitRiskScore) ||
        Number(patient.risk?.score) ||
        0,
      date: patient.journey?.firstVisitDate || patient.visitDate,
    },
    {
      visit: patient.journey?.latestVisitDate
        ? formatDate(patient.journey.latestVisitDate, { day: "numeric", month: "short" })
        : "Latest Visit",
      risk: Number(patient.risk?.score) || 0,
      date: patient.journey?.latestVisitDate || patient.visitDate,
    },
  ];

  const rawProgression = patient.journey?.riskProgression;

  if (!rawProgression || typeof rawProgression !== "string") {
    return fallbackPoints;
  }

  const visits = (rawProgression.match(/\{[^{}]+\}/g) || [])
    .map((chunk, index) => {
      const visitDate = extractQuotedValue(chunk, "visit_date");
      const score = extractNumberValue(chunk, "risk_score");

      return {
        visit:
          formatDate(visitDate, { day: "numeric", month: "short" }) ||
          `Visit ${index + 1}`,
        risk: score ?? Number(patient.risk?.score) ?? 0,
        date: visitDate,
      };
    })
    .filter((entry) => entry.visit && !Number.isNaN(entry.risk));

  return visits.length > 0 ? visits : fallbackPoints;
}

export function getClinicalNoteSections(patient) {
  const clinical = patient.clinical || {};

  return [
    {
      title: "Diagnosis",
      content: clinical.diagnosis || patient.provisionaldiagnosis || "Not available",
    },
    {
      title: "Clinical Notes",
      content: clinical.clinicalNotes || patient.clinicalnotes || "Not available",
    },
    {
      title: "Physical Remarks",
      content: clinical.physicalRemarks || "Not available",
    },
    {
      title: "Vital Remarks",
      content: clinical.vitalRemarks || "Not available",
    },
    {
      title: "Doctor Advice",
      content: clinical.doctorAdvice || "Not available",
    },
    {
      title: "Medicine Details",
      content: clinical.medicineDetails || patient.medicinedetails || "Not available",
    },
    {
      title: "Investigations",
      content: clinical.investigations || patient.investigations || "Not available",
    },
  ];
}
