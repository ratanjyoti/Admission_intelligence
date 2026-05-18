const MAJOR_PROCEDURE_KEYWORDS = [
  "transplant",
  "bone marrow",
  "cabg",
  "angioplasty",
  "laparotomy",
  "reconstruction",
  "hernia repair",
  "cholecystectomy",
];

const SURGICAL_KEYWORDS = [
  ...MAJOR_PROCEDURE_KEYWORDS,
  "surgery",
  "appendectomy",
  "biopsy",
  "endoscopy",
  "colonoscopy",
  "stent",
];

const DAYCARE_KEYWORDS = [
  "daycare",
  "day care",
  "phaco",
  "cataract",
  "infusion",
  "transfusion",
  "chemo",
  "chemotherapy",
];

const RENAL_KEYWORDS = [
  "renal",
  "kidney",
  "creat",
  "creatinine",
  "dialysis",
  "nephro",
  "nephropathy",
  "ckd",
  "transplant",
];

const ONCOLOGY_KEYWORDS = [
  "oncology",
  "lymphoma",
  "rituximab",
  "chemotherapy",
  "bone marrow",
  "cancer",
  "metastatic",
];

const RESPIRATORY_KEYWORDS = [
  "asthma",
  "copd",
  "retractions",
  "breathlessness",
  "ventilator",
  "nebulization",
  "respiratory",
];

const ORTHOPEDIC_KEYWORDS = [
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
];

const INFECTION_KEYWORDS = [
  "infection",
  "fever",
  "sepsis",
  "e coli",
  "klebsiella",
  "uti",
  "antibiotic",
];

const CARDIAC_KEYWORDS = [
  "cardiac",
  "heart block",
  "cabg",
  "angioplasty",
  "pacing",
  "arrhythmia",
];

const NEURO_KEYWORDS = [
  "seizure",
  "epile",
  "migraine",
  "encephalopathy",
  "neurolog",
  "gtcs",
];

const ICD10_RULES = [
  { code: "N18.6", label: "End stage renal disease", keywords: ["esrd", "end stage renal", "started on hd", "hemodialysis", "haemodialysis", "dialysis"] },
  { code: "N18.9", label: "Chronic kidney disease, unspecified", keywords: ["ckd", "ckdvd", "renal dysfunction", "kidney disease", "creatinine", "egfr"] },
  { code: "E11.21", label: "Type 2 diabetes mellitus with diabetic nephropathy", keywords: ["diabetic kidney disease", "diabetic nephropathy", "dm nephropathy", "nephropathy"] },
  { code: "E11.9", label: "Type 2 diabetes mellitus without complications", keywords: ["diabetes mellitus", "type ii diabetes", "dm on treatment", "diabetic"] },
  { code: "I10", label: "Essential hypertension", keywords: ["hypertension", "high bp", "htn"] },
  { code: "B18.1", label: "Chronic viral hepatitis B without delta-agent", keywords: ["hbv", "hepatitis b", "chronic hbv"] },
  { code: "D64.9", label: "Anemia, unspecified", keywords: ["anemia", "anaemia", "hb-", "pallor"] },
  { code: "C85.80", label: "Marginal zone lymphoma, unspecified site", keywords: ["marginal zone lymphoma", "marzinal zone lymphoma", "marginal lymphoma"] },
  { code: "C90.00", label: "Multiple myeloma not having achieved remission", keywords: ["multiple myeloma", "myeloma"] },
  { code: "G40.901", label: "Epilepsy, unspecified, not intractable, with status epilepticus", keywords: ["status epilepticus", "gtcs", "seizure"] },
  { code: "G43.901", label: "Migraine, unspecified, not intractable, with status migrainosus", keywords: ["status migraine", "migraine"] },
  { code: "I44.2", label: "Atrioventricular block, complete", keywords: ["complete heart block", "heart block"] },
  { code: "I25.10", label: "Atherosclerotic heart disease of native coronary artery without angina", keywords: ["coronary artery disease", "cad", "ptca"] },
  { code: "I50.9", label: "Heart failure, unspecified", keywords: ["heart failure"] },
  { code: "J44.9", label: "Chronic obstructive pulmonary disease, unspecified", keywords: ["copd"] },
  { code: "J45.909", label: "Unspecified asthma, uncomplicated", keywords: ["asthma"] },
  { code: "G47.33", label: "Obstructive sleep apnea", keywords: ["osa", "sleep apnea", "cpap"] },
  { code: "E03.9", label: "Hypothyroidism, unspecified", keywords: ["hypothyroid", "hypothyroidism"] },
  { code: "Q61.2", label: "Polycystic kidney, adult type", keywords: ["adpkd", "polycystic kidney"] },
  { code: "M45.9", label: "Ankylosing spondylitis of unspecified sites in spine", keywords: ["ankylosing spondylitis"] },
  { code: "N39.0", label: "Urinary tract infection, site not specified", keywords: ["uti", "urine c/s", "e coli", "klebsiella"] },
  { code: "E87.5", label: "Hyperkalemia", keywords: ["hyperkalemia", "high potassium", "k-5", "k -5", "potassium"] },
  { code: "C06.9", label: "Malignant neoplasm of mouth, unspecified", keywords: ["oral cavity", "buccal mucosa", "osmf", "masticator space"] },
  { code: "K64.9", label: "Hemorrhoids, unspecified", keywords: ["haemorrhoids", "hemorrhoids", "pile", "anopexy"] },
  { code: "K85.9", label: "Acute pancreatitis, unspecified", keywords: ["pancreatitis"] },
];

const COMORBIDITY_RULES = [
  { label: "Diabetes mellitus", keywords: ["diabetes mellitus", "diabetes", "dm "] },
  { label: "Hypertension", keywords: ["hypertension", "htn", "high bp"] },
  { label: "Chronic kidney disease", keywords: ["ckd", "renal dysfunction", "kidney disease", "creatinine"] },
  { label: "Diabetic nephropathy", keywords: ["diabetic kidney disease", "diabetic nephropathy", "nephropathy"] },
  { label: "Chronic hepatitis B", keywords: ["hbv", "hepatitis b", "chronic hbv"] },
  { label: "Anemia", keywords: ["anemia", "anaemia", "pallor"] },
  { label: "Coronary artery disease", keywords: ["coronary artery disease", "cad", "ptca"] },
  { label: "Complete heart block", keywords: ["complete heart block", "heart block"] },
  { label: "Obstructive sleep apnea", keywords: ["osa", "cpap", "sleep apnea"] },
  { label: "Hypothyroidism", keywords: ["hypothyroid", "hypothyroidism"] },
  { label: "Renal transplant status", keywords: ["renal transplant", "transplant", "lrtt"] },
  { label: "Lymphoma", keywords: ["lymphoma", "rituximab"] },
  { label: "Epilepsy / seizure disorder", keywords: ["seizure", "status epilepticus", "gtcs", "keppra", "levera"] },
  { label: "Migraine disorder", keywords: ["migraine"] },
  { label: "Chronic obstructive airway disease", keywords: ["copd", "asthma"] },
  { label: "Recurrent urinary tract infection", keywords: ["urine c/s", "e coli", "klebsiella", "uti"] },
  { label: "Hyperkalemia", keywords: ["high potassium", "hyperkalemia", "k-5", "k -5"] },
  { label: "Ankylosing spondylitis", keywords: ["ankylosing spondylitis"] },
];

const SYMPTOM_RULES = [
  { label: "Vomiting", keywords: ["vomiting", "vomitings", "emesis"] },
  { label: "Seizure activity", keywords: ["seizure", "status epilepticus", "gtcs"] },
  { label: "Headache / migraine", keywords: ["migraine", "headache"] },
  { label: "Breathlessness", keywords: ["breathlessness", "decrease breath sound", "spo2", "shortness of breath"] },
  { label: "Abdominal pain / surgical swelling", keywords: ["abdominal", "swelling", "hernia", "cough impulse"] },
  { label: "Oliguria / low urine output", keywords: ["urine output", "oliguria", "residual urine"] },
  { label: "Edema / fluid overload", keywords: ["edema", "oedema", "fluid overload"] },
  { label: "Fever / infection concern", keywords: ["fever", "infection", "uti"] },
  { label: "Weakness / anemia symptoms", keywords: ["pallor", "anemia", "anaemia"] },
  { label: "Bleeding / blood loss concern", keywords: ["bleed", "rbc", "hematuria", "blood"] },
];

const SURGERY_HISTORY_RULES = [
  { label: "Renal transplant", keywords: ["renal transplant", "lrtt", "transplant"] },
  { label: "PTCA / coronary intervention", keywords: ["ptca", "angioplasty"] },
  { label: "Total knee replacement", keywords: ["tkr"] },
  { label: "Total hip replacement", keywords: ["thr"] },
  { label: "Laparotomy", keywords: ["laparotomy"] },
  { label: "Appendix surgery", keywords: ["appendix", "appendectomy"] },
  { label: "Bone marrow transplant", keywords: ["bone marrow transplant", "stem cell transplant"] },
  { label: "AV fistula procedure", keywords: ["avf", "av fistula", "rc avf"] },
];

const REFUSAL_KEYWORDS = [
  "refused",
  "declined",
  "did not return",
  "non compliant",
  "non-compliant",
  "not willing",
];

const NOT_AVAILABLE_VALUES = new Set([
  "",
  "-",
  "not available",
  "not explicitly mentioned",
  "not needed - explicit procedure available",
]);

function cleanText(value) {
  if (value === null || value === undefined) {
    return "";
  }

  try {
    return decodeURIComponent(String(value))
      .replace(/\u00a0/g, " ")
      .replace(/\s+/g, " ")
      .trim();
  } catch {
    return String(value)
      .replace(/\u00a0/g, " ")
      .replace(/\s+/g, " ")
      .trim();
  }
}

function lowerText(value) {
  return cleanText(value).toLowerCase();
}

function combinePatientText(patient) {
  const clinical = patient.clinical || {};
  const traceability = patient.traceability || {};
  const procedure = patient.procedure || {};

  return lowerText(
    [
      patient.department,
      patient.doctorName,
      patient.customerType,
      patient.risk?.reasoning,
      patient.admission?.reasoning,
      patient.bed?.reasoning,
      procedure.explicitProcedure,
      procedure.inferredProcedure,
      procedure.explicitSource,
      clinical.diagnosis,
      clinical.clinicalNotes,
      clinical.physicalRemarks,
      clinical.vitalRemarks,
      clinical.investigations,
      clinical.doctorAdvice,
      clinical.medicineDetails,
      traceability.summary,
      traceability.evidenceTrace,
    ]
      .map(cleanText)
      .filter(Boolean)
      .join(" ")
  );
}

function isMeaningfulValue(value) {
  return !NOT_AVAILABLE_VALUES.has(lowerText(value));
}

function getActiveProcedure(patient) {
  const explicitProcedure = cleanText(patient.procedure?.explicitProcedure);

  if (explicitProcedure && isMeaningfulValue(explicitProcedure)) {
    return explicitProcedure;
  }

  const inferredProcedure = cleanText(patient.procedure?.inferredProcedure);

  if (inferredProcedure && isMeaningfulValue(inferredProcedure)) {
    return inferredProcedure;
  }

  return "";
}

function parseProgressionEntries(rawProgression) {
  if (!rawProgression) {
    return [];
  }

  if (Array.isArray(rawProgression)) {
    return rawProgression;
  }

  const chunks = String(rawProgression).match(/\{[^{}]+\}/g) || [];

  return chunks.map((chunk) => {
    const visitDateMatch = chunk.match(/['"]?visit_date['"]?\s*:\s*['"]([^'"]+)['"]/);
    const riskScoreMatch = chunk.match(/['"]?risk_score['"]?\s*:\s*(\d+)/);
    const riskCategoryMatch = chunk.match(/['"]?risk_category['"]?\s*:\s*['"]([^'"]+)['"]/);
    const admissionTypeMatch = chunk.match(/['"]?admission_type['"]?\s*:\s*['"]([^'"]+)['"]/);

    return {
      visit_date: visitDateMatch ? visitDateMatch[1] : "",
      risk_score: riskScoreMatch ? Number(riskScoreMatch[1]) : null,
      risk_category: riskCategoryMatch ? riskCategoryMatch[1] : "",
      admission_type: admissionTypeMatch ? admissionTypeMatch[1] : "",
    };
  });
}

function parseDate(value) {
  const rawValue = cleanText(value).split(" ")[0];

  if (!rawValue) {
    return null;
  }

  const parsedDate = new Date(rawValue);
  return Number.isNaN(parsedDate.getTime()) ? null : parsedDate;
}

function formatDateLabel(value) {
  const parsedDate = parseDate(value);

  if (!parsedDate) {
    return cleanText(value) || "Not available";
  }

  return new Intl.DateTimeFormat("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(parsedDate);
}

function averageGapDays(patient) {
  const entries = parseProgressionEntries(patient.journey?.riskProgression);
  const dates = entries
    .map((entry) => parseDate(entry.visit_date))
    .filter(Boolean)
    .sort((a, b) => a - b);

  if (dates.length >= 2) {
    const gaps = [];

    for (let index = 0; index < dates.length - 1; index += 1) {
      gaps.push((dates[index + 1] - dates[index]) / (1000 * 60 * 60 * 24));
    }

    return Math.round((gaps.reduce((total, gap) => total + gap, 0) / gaps.length) * 10) / 10;
  }

  const firstVisit = parseDate(patient.journey?.firstVisitDate);
  const latestVisit = parseDate(patient.journey?.latestVisitDate);

  if (firstVisit && latestVisit && latestVisit > firstVisit) {
    return (latestVisit - firstVisit) / (1000 * 60 * 60 * 24);
  }

  return null;
}

function summarizeText(value, maxLength = 150) {
  const text = cleanText(value);

  if (!text || !isMeaningfulValue(text)) {
    return "Not available";
  }

  if (text.length <= maxLength) {
    return text;
  }

  return `${text.slice(0, maxLength).trim()}...`;
}

function uniqueDrivers(items) {
  return [...new Set(items.filter(Boolean))];
}

function patientSourceSections(patient) {
  const clinical = patient.clinical || {};

  return [
    { title: "Diagnosis", content: cleanText(clinical.diagnosis) },
    { title: "Clinical Notes", content: cleanText(clinical.clinicalNotes) },
    { title: "Physical Remarks", content: cleanText(clinical.physicalRemarks) },
    { title: "Vital Remarks / History", content: cleanText(clinical.vitalRemarks) },
    { title: "Investigations", content: cleanText(clinical.investigations) },
    { title: "Doctor Advice", content: cleanText(clinical.doctorAdvice) },
    { title: "Medicine Details", content: cleanText(clinical.medicineDetails) },
  ];
}

function extractExcerpt(text, keyword, radius = 84) {
  const normalizedText = cleanText(text);

  if (!normalizedText) {
    return "Not available";
  }

  const match = normalizedText.match(new RegExp(keyword.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "i"));

  if (!match || match.index === undefined) {
    return summarizeText(normalizedText, Math.min(radius * 2, 180));
  }

  const start = Math.max(0, match.index - radius);
  const end = Math.min(normalizedText.length, match.index + match[0].length + radius);
  let snippet = normalizedText.slice(start, end).trim();

  if (start > 0) {
    snippet = `...${snippet}`;
  }

  if (end < normalizedText.length) {
    snippet = `${snippet}...`;
  }

  return snippet;
}

function findRuleMatch(sections, keywords) {
  for (const section of sections) {
    const content = cleanText(section.content);

    if (!content) {
      continue;
    }

    for (const keyword of keywords) {
      if (new RegExp(keyword.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "i").test(content)) {
        return {
          keyword,
          source: section.title,
          evidence: extractExcerpt(content, keyword),
        };
      }
    }
  }

  return null;
}

function collectRuleMatches(sections, rules, limit = 6) {
  const items = [];

  for (const rule of rules) {
    const match = findRuleMatch(sections, rule.keywords);

    if (!match) {
      continue;
    }

    items.push({
      label: rule.label,
      keyword: match.keyword,
      source: match.source,
      evidence: match.evidence,
    });

    if (items.length >= limit) {
      break;
    }
  }

  return items;
}

function parseMedications(patient, limit = 8) {
  const clinical = patient.clinical || {};
  const medicationText = [cleanText(clinical.medicineDetails), cleanText(clinical.doctorAdvice)]
    .filter(Boolean)
    .join(" ");
  const pattern =
    /\b(?:TAB|CAP|INJ|SYP|POWDER|INSULIN|SPRAY|SACHET)\.?\s*([A-Z0-9\-+/]+(?:\s+[A-Z0-9\-+/]+){0,2})/gi;
  const medications = [];
  let match = pattern.exec(medicationText);

  while (match) {
    const normalized = cleanText(match[1]).replace(/\s+/g, " ").toUpperCase();

    if (normalized && !medications.includes(normalized)) {
      medications.push(normalized);
    }

    if (medications.length >= limit) {
      break;
    }

    match = pattern.exec(medicationText);
  }

  return medications;
}

function parseFamilyHistory(patient) {
  for (const section of patientSourceSections(patient)) {
    const content = cleanText(section.content);
    const match = content.match(/family\s*history\s*:?\s*(.+)/i);

    if (match) {
      return [
        {
          label: summarizeText(match[1], 120),
          source: section.title,
        },
      ];
    }
  }

  return [];
}

function deriveIcd10Codes(patient) {
  const sections = patientSourceSections(patient);
  const codes = [];

  for (const rule of ICD10_RULES) {
    const match = findRuleMatch(sections, rule.keywords);

    if (!match) {
      continue;
    }

    codes.push({
      code: rule.code,
      label: rule.label,
      matchedKeyword: match.keyword,
      source: match.source,
      evidence: match.evidence,
    });

    if (codes.length >= 4) {
      break;
    }
  }

  return codes;
}

function deriveStructuredHistory(patient, comorbidities) {
  const sections = patientSourceSections(patient);

  return {
    pastConditions: comorbidities.slice(0, 6).map((item) => ({
      label: item.label,
      source: item.source,
      evidence: item.evidence,
    })),
    surgeries: collectRuleMatches(sections, SURGERY_HISTORY_RULES, 6),
    medications: parseMedications(patient).map((label) => ({
      label,
      source: "Medicine Details / Doctor Advice",
    })),
    familyHistory: parseFamilyHistory(patient),
    summary:
      "Derived from diagnosis, clinical notes, history remarks, and medication instructions.",
  };
}

function detectSignals(patient) {
  const text = combinePatientText(patient);
  const department = lowerText(patient.department);
  const activeProcedure = lowerText(getActiveProcedure(patient));

  const matches = (keywords) =>
    keywords.some(
      (keyword) =>
        text.includes(keyword) ||
        department.includes(keyword) ||
        activeProcedure.includes(keyword)
    );

  return {
    text,
    daycare: matches(DAYCARE_KEYWORDS),
    renal: matches(RENAL_KEYWORDS),
    oncology: matches(ONCOLOGY_KEYWORDS),
    respiratory: matches(RESPIRATORY_KEYWORDS),
    orthopedic: matches(ORTHOPEDIC_KEYWORDS),
    infection: matches(INFECTION_KEYWORDS),
    cardiac: matches(CARDIAC_KEYWORDS),
    neuro: matches(NEURO_KEYWORDS),
    surgical: matches(SURGICAL_KEYWORDS),
    majorProcedure: matches(MAJOR_PROCEDURE_KEYWORDS),
    refusal: matches(REFUSAL_KEYWORDS),
  };
}

function deriveDiseaseCohorts(signals) {
  const cohorts = [];

  if (signals.renal) cohorts.push("Renal");
  if (signals.oncology) cohorts.push("Oncology");
  if (signals.cardiac) cohorts.push("Cardiac");
  if (signals.respiratory) cohorts.push("Respiratory");
  if (signals.orthopedic) cohorts.push("Orthopedic");
  if (signals.infection) cohorts.push("Infectious");
  if (signals.neuro) cohorts.push("Neurology");

  if (cohorts.length === 0) {
    cohorts.push("General Medicine");
  }

  return cohorts;
}

function deriveClinicalIntelligence(patient, signals) {
  const sections = patientSourceSections(patient);
  const icd10Codes = deriveIcd10Codes(patient);
  const comorbidities = collectRuleMatches(sections, COMORBIDITY_RULES, 8);
  const possibleSymptoms = collectRuleMatches(sections, SYMPTOM_RULES, 8);
  const structuredHistory = deriveStructuredHistory(patient, comorbidities);
  const diseaseCohorts = deriveDiseaseCohorts(signals);

  return {
    icd10Codes,
    primaryIcd10: icd10Codes[0] || null,
    comorbidities,
    possibleSymptoms,
    structuredHistory,
    diseaseCohorts,
    primaryCohort: diseaseCohorts[0],
  };
}

function deriveCaseType(patient, signals) {
  const admissionType = cleanText(patient.admission?.type);
  const bedType = lowerText(patient.bed?.type);
  const activeProcedure = getActiveProcedure(patient);
  const department = lowerText(patient.department);

  if (bedType.includes("daycare") || (signals.daycare && admissionType !== "Emergency")) {
    return {
      label: "Daycare",
      reasoning: "Short-stay procedure or infusion indicators support a daycare pathway.",
    };
  }

  if (
    signals.surgical ||
    signals.majorProcedure ||
    department.includes("surgical") ||
    lowerText(activeProcedure).includes("transplant")
  ) {
    return {
      label: "Surgical",
      reasoning: "Procedure-led or operative planning indicators support a surgical case type.",
    };
  }

  return {
    label: "Medication Management",
    reasoning:
      "The current record is dominated by monitoring, medication optimization, and specialty medical care.",
  };
}

function deriveRevenuePackage(patient, signals, caseType) {
  const bedType = cleanText(patient.bed?.type);
  const admissionType = cleanText(patient.admission?.type);
  const riskCategory = cleanText(patient.risk?.category);
  const activeProcedure = getActiveProcedure(patient);
  let score = 0;
  const drivers = [];

  if (caseType === "Daycare") {
    score += 1;
    drivers.push("Daycare pathway keeps the package relatively short-stay.");
  } else if (caseType === "Surgical") {
    score += 4;
    drivers.push("Procedure-led care increases package complexity and consumable use.");
  } else {
    score += 2;
    drivers.push("Medical admission still carries monitoring and pharmacy costs.");
  }

  if (bedType.includes("ICU")) {
    score += 3;
    drivers.push("ICU bed allocation materially increases expected package value.");
  } else if (bedType.includes("HDU") || bedType.includes("Oncology")) {
    score += 2;
    drivers.push("High-dependency or specialty ward allocation raises inpatient cost.");
  } else if (bedType.includes("General")) {
    score += 1;
  }

  if (admissionType === "Emergency") {
    score += 2;
    drivers.push("Emergency coordination increases early investigation and stabilization spend.");
  } else if (admissionType === "Urgent") {
    score += 1;
  }

  if (signals.majorProcedure) {
    score += 3;
    drivers.push("A major procedure or transplant-scale intervention is present.");
  } else if (activeProcedure) {
    score += 1;
    drivers.push("A defined procedure contributes to package value.");
  }

  if (signals.renal || signals.oncology) {
    score += 1;
    drivers.push("Renal or oncology complexity usually adds laboratory, drug, and review burden.");
  }

  if (riskCategory === "Critical") {
    score += 1;
    drivers.push("Critical-risk monitoring increases expected utilization.");
  } else if (riskCategory === "High") {
    score += 1;
  }

  let expectedRevenue = "Rs 20K - Rs 60K";
  let revenueCategory = "Standard Value";
  let minLakhs = 0.2;
  let maxLakhs = 0.6;

  if (score <= 2) {
    expectedRevenue = "Rs 20K - Rs 60K";
    revenueCategory = "Standard Value";
    minLakhs = 0.2;
    maxLakhs = 0.6;
  } else if (score <= 4) {
    expectedRevenue = "Rs 60K - Rs 1.5L";
    revenueCategory = "Moderate Value";
    minLakhs = 0.6;
    maxLakhs = 1.5;
  } else if (score <= 6) {
    expectedRevenue = "Rs 1.5L - Rs 2.5L";
    revenueCategory = "Significant Value";
    minLakhs = 1.5;
    maxLakhs = 2.5;
  } else if (score <= 8) {
    expectedRevenue = "Rs 2.5L - Rs 4L";
    revenueCategory = "High Value";
    minLakhs = 2.5;
    maxLakhs = 4.0;
  } else {
    expectedRevenue = "Rs 4L - Rs 7L";
    revenueCategory = "Strategic Value";
    minLakhs = 4.0;
    maxLakhs = 7.0;
  }

  return {
    expectedRevenue,
    revenueCategory,
    minLakhs,
    maxLakhs,
    midLakhs: Math.round(((minLakhs + maxLakhs) / 2) * 100) / 100,
    score,
    drivers: uniqueDrivers(drivers),
    reasoning: uniqueDrivers(drivers).slice(0, 3).join(" "),
  };
}

function deriveLengthOfStay(patient, signals, caseType) {
  const admissionType = cleanText(patient.admission?.type);
  const bedType = cleanText(patient.bed?.type);
  const riskCategory = cleanText(patient.risk?.category);
  const progressionTrend = cleanText(patient.journey?.progressionTrend);
  const visitCount = Number(patient.journey?.visitCount || 1);
  const drivers = [];

  if (caseType === "Daycare" && !admissionType.includes("Emergency")) {
    return {
      label: "Not applicable - Daycare / Same-day",
      minDays: 0,
      maxDays: 0,
      drivers: ["Short-stay daycare planning does not require a traditional inpatient LOS."],
      reasoning: "Short-stay daycare planning does not require a traditional inpatient LOS.",
    };
  }

  let minDays = 1;
  let maxDays = 3;

  if (bedType.includes("ICU")) {
    minDays = 5;
    maxDays = 7;
    drivers.push("ICU-level care typically extends inpatient stay.");
  } else if (bedType.includes("HDU") || bedType.includes("Oncology")) {
    minDays = 4;
    maxDays = 6;
    drivers.push("Monitored or specialty ward care usually needs a longer admission.");
  } else if (caseType === "Surgical") {
    minDays = 3;
    maxDays = 5;
    drivers.push("Procedure-based recovery increases expected length of stay.");
  }

  if (admissionType === "Emergency" && maxDays < 4) {
    minDays = 2;
    maxDays = 4;
    drivers.push("Emergency stabilization adds at least short inpatient observation.");
  }

  if (signals.majorProcedure) {
    minDays = Math.max(minDays, 5);
    maxDays = Math.max(maxDays, 8);
    drivers.push("Major procedures or transplant-scale care extend post-procedure monitoring.");
  }

  if (signals.renal && admissionType === "Emergency") {
    minDays = Math.max(minDays, 4);
    maxDays = Math.max(maxDays, 6);
    drivers.push("Renal instability often needs serial labs and monitored correction.");
  }

  if (signals.oncology && riskCategory === "Critical") {
    minDays = Math.max(minDays, 5);
    maxDays = Math.max(maxDays, 7);
    drivers.push("Critical oncology context increases monitoring and treatment coordination time.");
  }

  if (progressionTrend === "Worsening" || visitCount >= 3) {
    maxDays += 1;
    drivers.push("Worsening or repeated visits suggest a slower discharge trajectory.");
  }

  return {
    label: `${minDays} - ${maxDays} days`,
    minDays,
    maxDays,
    drivers: uniqueDrivers(drivers),
    reasoning:
      uniqueDrivers(drivers).slice(0, 3).join(" ") ||
      "Estimated from acuity, bed requirement, and treatment complexity.",
  };
}

function deriveReadmissionRisk(patient, signals) {
  const visitCount = Number(patient.journey?.visitCount || 1);
  const repeatVisit = cleanText(patient.journey?.repeatVisit);
  const progressionTrend = cleanText(patient.journey?.progressionTrend);
  const riskCategory = cleanText(patient.risk?.category);
  const admissionType = cleanText(patient.admission?.type);
  const bedType = cleanText(patient.bed?.type);
  const evidenceCount = Number(patient.traceability?.evidenceCount || 0);
  let score = 0;
  const drivers = [];

  if (repeatVisit === "Yes") {
    score += 2;
    drivers.push("Repeat visits indicate prior need for re-evaluation.");
  }

  if (visitCount >= 3) {
    score += 1;
    drivers.push("Multiple visits increase the chance of return utilization.");
  }

  if (progressionTrend === "Worsening") {
    score += 2;
    drivers.push("Worsening progression trend raises near-term readmission risk.");
  }

  if (riskCategory === "Critical") {
    score += 2;
    drivers.push("Critical-risk status suggests high post-discharge instability.");
  } else if (riskCategory === "High") {
    score += 1;
  }

  if (admissionType === "Emergency" || admissionType === "Urgent") {
    score += 1;
    drivers.push("Emergency or urgent admission pathways are more likely to bounce back.");
  }

  if (bedType === "ICU" || bedType === "HDU") {
    score += 1;
    drivers.push("High-dependency bed need implies closer follow-up after discharge.");
  }

  if (signals.renal) {
    score += 2;
    drivers.push("Renal dysfunction, creatinine abnormalities, or transplant context increase recurrence risk.");
  }

  if (signals.oncology) {
    score += 1;
    drivers.push("Oncology treatment burden can trigger early re-presentation.");
  }

  if (evidenceCount >= 8) {
    score += 1;
    drivers.push("A dense evidence trail suggests multi-factor complexity.");
  }

  const label = score >= 7 ? "High" : score >= 4 ? "Moderate" : "Low";

  return {
    label,
    score,
    drivers: uniqueDrivers(drivers),
    reasoning:
      uniqueDrivers(drivers).slice(0, 3).join(" ") ||
      "Estimated from visit pattern, acuity, and chronic disease burden.",
  };
}

function deriveNoShowRisk(patient, signals, caseType) {
  const repeatVisit = cleanText(patient.journey?.repeatVisit);
  const progressionTrend = cleanText(patient.journey?.progressionTrend);
  const admissionType = cleanText(patient.admission?.type);
  const riskCategory = cleanText(patient.risk?.category);
  const bedType = cleanText(patient.bed?.type);
  const gapDays = averageGapDays(patient);
  let score = 0;
  const drivers = [];

  if (admissionType === "Elective") {
    score += 2;
    drivers.push("Elective pathways are more vulnerable to scheduling drop-off.");
  }

  if (caseType === "Daycare") {
    score += 1;
    drivers.push("Short-stay procedures can be postponed when symptoms feel manageable.");
  }

  if (riskCategory === "Low") {
    score += 2;
    drivers.push("Lower acuity often reduces urgency from the patient's perspective.");
  } else if (riskCategory === "Medium") {
    score += 1;
  } else if (riskCategory === "Critical") {
    score -= 2;
    drivers.push("Critical acuity usually lowers the chance of a missed admission.");
  }

  if (repeatVisit === "No") {
    score += 1;
    drivers.push("A single documented visit means follow-through behavior is less established.");
  } else {
    score -= 1;
    drivers.push("Completed follow-up visits suggest better adherence to review plans.");
  }

  if (gapDays !== null && gapDays > 45) {
    score += 2;
    drivers.push("Long gaps between documented visits suggest weaker follow-up continuity.");
  } else if (gapDays !== null && gapDays > 21) {
    score += 1;
  }

  if (progressionTrend === "Improving") {
    score += 1;
    drivers.push("Improving symptoms can reduce perceived need for attendance.");
  } else if (progressionTrend === "Worsening") {
    score -= 1;
    drivers.push("Worsening trajectory usually keeps patients engaged with care.");
  }

  if (signals.refusal) {
    score += 2;
    drivers.push("Refusal or decline language is a strong dropout signal.");
  }

  if (admissionType === "Emergency" || bedType === "ICU") {
    score -= 2;
  }

  const label = score >= 5 ? "High" : score >= 3 ? "Moderate" : "Low";

  return {
    label,
    score: Math.max(score, 0),
    drivers: uniqueDrivers(drivers),
    reasoning:
      uniqueDrivers(drivers).slice(0, 3).join(" ") ||
      "Estimated from elective intent, acuity, and observed follow-up pattern.",
  };
}

function deriveDeferredTime(patient, readmissionRisk, caseType) {
  const riskCategory = cleanText(patient.risk?.category);
  const admissionType = cleanText(patient.admission?.type);
  const bedType = cleanText(patient.bed?.type);
  const progressionTrend = cleanText(patient.journey?.progressionTrend);

  if (
    admissionType === "Emergency" ||
    bedType === "ICU" ||
    (riskCategory === "Critical" && progressionTrend === "Worsening")
  ) {
    return {
      label: "Cannot be safely delayed",
      drivers: ["Emergency or unstable critical features make delay unsafe."],
      reasoning: "Emergency or unstable critical features make delay unsafe.",
    };
  }

  if (riskCategory === "Critical" || bedType === "HDU" || bedType === "General Oncology Ward") {
    return {
      label: "24-48 hours only",
      drivers: ["Critical specialty care needs should be reviewed within 24-48 hours."],
      reasoning: "Critical specialty care needs should be reviewed within 24-48 hours.",
    };
  }

  if (admissionType === "Urgent" || readmissionRisk.label === "High" || caseType === "Surgical") {
    return {
      label: "3-5 days acceptable",
      drivers: ["Near-term admission is advisable because delay increases coordination risk."],
      reasoning: "Near-term admission is advisable because delay increases coordination risk.",
    };
  }

  if (caseType === "Daycare" || riskCategory === "Low" || riskCategory === "Medium") {
    return {
      label: "1-2 weeks acceptable",
      drivers: ["The current profile supports short deferral if symptoms remain stable."],
      reasoning: "The current profile supports short deferral if symptoms remain stable.",
    };
  }

  return {
    label: "Can be safely deferred",
    drivers: ["No high-acuity inpatient trigger is currently active."],
    reasoning: "No high-acuity inpatient trigger is currently active.",
  };
}

function deriveAdmissionConversionProbability(
  patient,
  signals,
  caseType,
  readmissionRisk,
  noShowRisk,
  deferredTime,
  clinicalIntelligence
) {
  const riskCategory = cleanText(patient.risk?.category);
  const admissionType = cleanText(patient.admission?.type);
  const bedType = cleanText(patient.bed?.type);
  const progressionTrend = cleanText(patient.journey?.progressionTrend);
  const evidenceCount = Number(patient.traceability?.evidenceCount || 0);
  let score = 42;
  const drivers = [];

  if (admissionType === "Emergency") {
    score += 28;
    drivers.push("Emergency pathway strongly increases conversion likelihood.");
  } else if (admissionType === "Urgent") {
    score += 18;
    drivers.push("Urgent admission advice supports near-term conversion.");
  } else if (admissionType === "Elective") {
    score += 8;
    drivers.push("Planned admission intent is already documented.");
  }

  if (riskCategory === "Critical") {
    score += 18;
    drivers.push("Critical risk signals make inpatient conversion more likely.");
  } else if (riskCategory === "High") {
    score += 10;
    drivers.push("High clinical risk increases admission conversion pressure.");
  }

  if (["ICU", "HDU", "General Oncology Ward"].includes(bedType)) {
    score += 10;
    drivers.push("Specialty bed planning indicates a strong chance of admission.");
  }

  if (progressionTrend === "Worsening") {
    score += 8;
    drivers.push("Worsening progression increases the chance of admission follow-through.");
  }

  if (readmissionRisk.label === "High") {
    score += 5;
    drivers.push("High readmission risk indicates unstable disease burden.");
  }

  if (noShowRisk.label === "High") {
    score -= 12;
    drivers.push("High no-show risk reduces expected conversion despite clinical need.");
  } else if (noShowRisk.label === "Moderate") {
    score -= 5;
  }

  if (deferredTime.label === "Cannot be safely delayed") {
    score += 10;
    drivers.push("Unsafe-to-delay cases usually convert quickly to admission.");
  }

  if (caseType === "Surgical") {
    score += 6;
    drivers.push("Procedure-led care typically has a clearer admission endpoint.");
  }

  if (evidenceCount >= 8) {
    score += 4;
    drivers.push("Dense traceable evidence supports a stronger admission recommendation.");
  }

  if (clinicalIntelligence.primaryIcd10) {
    score += 2;
    drivers.push("Structured coding confidence improves decision certainty.");
  }

  const percentage = Math.max(18, Math.min(96, score));
  const label =
    percentage >= 80 ? "Very High" : percentage >= 65 ? "High" : percentage >= 45 ? "Moderate" : "Low";

  return {
    label,
    percentage,
    drivers: uniqueDrivers(drivers),
    reasoning:
      uniqueDrivers(drivers).slice(0, 3).join(" ") ||
      "Estimated from urgency, acuity, and follow-through risk.",
  };
}

function deriveTreatmentPlan(patient, signals, caseType, clinicalIntelligence) {
  const activeProcedure = getActiveProcedure(patient);
  const diagnosis = cleanText(patient.clinical?.diagnosis);
  const diagnosisFocus = summarizeText(
    diagnosis ||
      activeProcedure ||
      clinicalIntelligence.possibleSymptoms.slice(0, 2).map((item) => item.label).join(", "),
    80
  );
  const topComorbidity = clinicalIntelligence.comorbidities[0]?.label || "the active chronic disease burden";
  let primary = `Medication optimization for ${diagnosisFocus} with specialty monitoring and repeat clinical review`;
  let secondary = `Observation with planned follow-up escalation if ${topComorbidity.toLowerCase()} or biomarkers worsen`;

  if (lowerText(activeProcedure).includes("dialysis") || (signals.renal && signals.text.includes("dialysis"))) {
    primary = `Dialysis-led admission for ${diagnosisFocus} with nephrology monitoring and electrolyte surveillance`;
    secondary = "Medical stabilization with transplant review once creatinine and potassium trends are safer";
  } else if (lowerText(activeProcedure).includes("transplant") || signals.text.includes("transplant")) {
    primary = `Transplant-focused inpatient monitoring for ${diagnosisFocus} with renal function and immunosuppression review`;
    secondary = "Medical stabilization with close transplant follow-up if admission can remain planned";
  } else if (signals.oncology) {
    primary = `Oncology-directed admission for ${diagnosisFocus} with hematology monitoring and therapy review`;
    secondary =
      "Daycare therapy, transfusion, or planned oncology follow-up if the patient remains clinically stable";
  } else if (caseType === "Surgical" && activeProcedure) {
    primary = `${activeProcedure} with peri-procedural monitoring and inpatient recovery planning`;
    secondary = `Conservative stabilization with scheduled elective intervention while monitoring ${topComorbidity.toLowerCase()}`;
  } else if (signals.respiratory) {
    primary = `Respiratory stabilization for ${diagnosisFocus} with bronchodilator or steroid therapy under monitored observation`;
    secondary = "Ward observation with inhaled therapy optimization and early review if symptoms settle";
  } else if (signals.infection) {
    primary = `Medical stabilization for ${diagnosisFocus} with culture-guided therapy and repeat laboratory monitoring`;
    secondary = "Observation with repeat labs and outpatient reassessment if response remains stable";
  } else if (signals.cardiac) {
    primary = `Cardiac monitoring for ${diagnosisFocus} with medication optimization and rhythm or ischemia evaluation`;
    secondary = "Short-interval follow-up with planned procedure escalation if symptoms worsen";
  } else if (signals.renal) {
    primary = `Renal stabilization for ${diagnosisFocus} with nephrology monitoring and serial metabolic review`;
    secondary = "Outpatient monitoring with planned procedure or transplant escalation if risk increases";
  }

  return {
    primary,
    secondary,
    reasoning:
      `Treatment options are inferred from the active procedure, disease cohort, and diagnosis cues such as ${diagnosisFocus}, while accounting for ${topComorbidity.toLowerCase()}.`,
  };
}

function deriveTimeline(patient, clinicalIntelligence) {
  const clinical = patient.clinical || {};
  const firstVisit = patient.journey?.firstVisitDate || patient.visitDate;
  const latestVisit = patient.journey?.latestVisitDate || patient.visitDate;
  const symptomLabels = clinicalIntelligence.possibleSymptoms.slice(0, 3).map((item) => item.label).join(", ");
  const pastConditions = clinicalIntelligence.structuredHistory.pastConditions
    .slice(0, 3)
    .map((item) => item.label)
    .join(", ");

  const symptomSummary = summarizeText(
    symptomLabels || clinical.vitalRemarks || clinical.physicalRemarks || clinical.clinicalNotes,
    160
  );
  const diagnosisSummary = summarizeText(
    clinicalIntelligence.icd10Codes
      .slice(0, 2)
      .map((item) => `${item.code} ${item.label}`)
      .join(", ") ||
      clinical.diagnosis ||
      getActiveProcedure(patient) ||
      clinical.investigations,
    160
  );
  const adviceSummary = summarizeText(
    clinical.doctorAdvice || patient.admission?.summary,
    160
  );
  const currentStatus = `${cleanText(patient.risk?.category)} risk, ${cleanText(
    patient.admission?.type
  )} pathway, ${cleanText(patient.bed?.type)} bed recommendation, trend: ${
    cleanText(patient.journey?.progressionTrend) || "Not available"
  }.`;

  return {
    stages: [
      {
        stage: "First Symptom / History",
        date: formatDateLabel(firstVisit),
        summary: summarizeText([symptomSummary, pastConditions].filter(Boolean).join(" | "), 160),
        source: "Symptoms and history extraction",
      },
      {
        stage: "OPD Evaluation",
        date: formatDateLabel(firstVisit),
        summary: `Initial documented review under ${
          cleanText(patient.department) || "the current department"
        } with ${cleanText(patient.doctorName) || "the assigned clinician"}.`,
        source: "Journey and visit history",
      },
      {
        stage: "Diagnosis / Workup",
        date: formatDateLabel(patient.visitDate || latestVisit),
        summary: diagnosisSummary,
        source: "Diagnosis, investigations, or procedure intelligence",
      },
      {
        stage: "Admission Advice",
        date: formatDateLabel(patient.visitDate || latestVisit),
        summary: adviceSummary,
        source: "Doctor advice and admission reasoning",
      },
      {
        stage: "Current Status",
        date: formatDateLabel(latestVisit),
        summary: currentStatus,
        source: "Current risk, bed, and journey profile",
      },
    ],
    summary:
      "Structured from symptom context, documented visits, diagnosis cues, admission advice, and the latest operational status.",
  };
}

function deriveOperationalIntelligence(patient) {
  const signals = detectSignals(patient);
  const clinicalIntelligence = deriveClinicalIntelligence(patient, signals);
  const caseType = deriveCaseType(patient, signals);
  const readmissionRisk = deriveReadmissionRisk(patient, signals);
  const noShowRisk = deriveNoShowRisk(patient, signals, caseType.label);
  const deferredTime = deriveDeferredTime(patient, readmissionRisk, caseType.label);
  const admissionConversionProbability = deriveAdmissionConversionProbability(
    patient,
    signals,
    caseType.label,
    readmissionRisk,
    noShowRisk,
    deferredTime,
    clinicalIntelligence
  );

  return {
    clinicalIntelligence,
    caseType,
    packageIntelligence: deriveRevenuePackage(patient, signals, caseType.label),
    lengthOfStay: deriveLengthOfStay(patient, signals, caseType.label),
    readmissionRisk,
    noShowRisk,
    deferredTime,
    admissionConversionProbability,
    treatmentPlan: deriveTreatmentPlan(patient, signals, caseType.label, clinicalIntelligence),
    clinicalTimeline: deriveTimeline(patient, clinicalIntelligence),
  };
}

export function enrichPatientRecord(patient) {
  if (!patient) {
    return patient;
  }

  return {
    ...patient,
    operational: deriveOperationalIntelligence(patient),
  };
}

export function enrichPatients(patients) {
  return Array.isArray(patients)
    ? patients.map((patient) => enrichPatientRecord(patient))
    : [];
}
