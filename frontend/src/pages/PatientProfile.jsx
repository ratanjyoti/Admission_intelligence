import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  ArrowLeft,
  BadgePercent,
  BedDouble,
  CalendarRange,
  Coins,
  Download,
  Printer,
  Repeat2,
  Search,
  ShieldCheck,
  Siren,
  TimerReset,
  TriangleAlert,
} from "lucide-react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import EmptyState from "../components/EmptyState";
import ErrorState from "../components/ErrorState";
import LoadingScreen from "../components/LoadingScreen";
import { getPatientById } from "../lib/api";
import {
  formatDate,
  getClinicalNoteSections,
  parseRiskProgression,
  parseTraceabilityString,
} from "../lib/patientData";

function Panel({ title, children, className = "" }) {
  return (
    <div className={`rounded-2xl border border-slate-200 bg-white p-5 shadow-sm ${className}`}>
      <h2 className="mb-3 text-lg font-semibold text-slate-900">{title}</h2>
      {children}
    </div>
  );
}

function Badge({ children, tone = "slate" }) {
  const tones = {
    slate: "bg-slate-100 text-slate-700",
    red: "bg-red-100 text-red-700",
    orange: "bg-orange-100 text-orange-700",
    blue: "bg-blue-100 text-blue-700",
    green: "bg-green-100 text-green-700",
  };

  return (
    <span className={`rounded-full px-3 py-1 text-sm font-medium ${tones[tone]}`}>
      {children}
    </span>
  );
}

function DetailItem({ label, value }) {
  return (
    <div>
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
        {label}
      </p>
      <p className="mt-1 text-sm text-slate-800">{value || "Not available"}</p>
    </div>
  );
}

function MetricCard({
  icon: Icon,
  label,
  value,
  hint,
  tone = "slate",
}) {
  const tones = {
    slate: "border-slate-200 bg-white text-slate-900",
    blue: "border-blue-200 bg-blue-50 text-blue-900",
    green: "border-green-200 bg-green-50 text-green-900",
    orange: "border-orange-200 bg-orange-50 text-orange-900",
    red: "border-red-200 bg-red-50 text-red-900",
    purple: "border-purple-200 bg-purple-50 text-purple-900",
  };

  return (
    <div className={`rounded-2xl border p-4 ${tones[tone] || tones.slate}`}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            {label}
          </p>
          <p className="mt-2 text-base font-semibold leading-6 text-current">
            {value || "Not available"}
          </p>
        </div>
        {Icon ? (
          <div className="rounded-xl bg-white/70 p-2 text-current">
            <Icon className="h-4 w-4" />
          </div>
        ) : null}
      </div>
      {hint ? <p className="mt-2 text-sm leading-6 text-slate-600">{hint}</p> : null}
    </div>
  );
}

function ChipList({ items, emptyLabel = "Not available", tone = "slate" }) {
  const tones = {
    slate: "bg-slate-100 text-slate-700",
    blue: "bg-blue-100 text-blue-700",
    green: "bg-green-100 text-green-700",
    orange: "bg-orange-100 text-orange-700",
    red: "bg-red-100 text-red-700",
  };

  if (!items || items.length === 0) {
    return <p className="text-sm text-slate-500">{emptyLabel}</p>;
  }

  return (
    <div className="flex flex-wrap gap-2">
      {items.map((item) => {
        const label =
          typeof item === "string"
            ? item
            : item.code
              ? `${item.code} ${item.label}`
              : item.label;

        return (
          <span
            key={label}
            className={`rounded-full px-3 py-1 text-xs font-semibold ${tones[tone]}`}
          >
            {label}
          </span>
        );
      })}
    </div>
  );
}

function RiskGauge({ score, category }) {
  const numericScore = Math.max(0, Math.min(10, Number(score || 0)));
  const percentage = numericScore / 10;
  const circumference = 2 * Math.PI * 44;
  const dashOffset = circumference - percentage * circumference;
  const colors = {
    Critical: "#dc2626",
    High: "#f97316",
    Medium: "#eab308",
    Low: "#16a34a",
  };
  const stroke = colors[category] || "#334155";

  return (
    <div className="flex items-center gap-4">
      <div className="relative h-28 w-28">
        <svg viewBox="0 0 120 120" className="h-28 w-28 -rotate-90">
          <circle cx="60" cy="60" r="44" fill="none" stroke="#e2e8f0" strokeWidth="10" />
          <circle
            cx="60"
            cy="60"
            r="44"
            fill="none"
            stroke={stroke}
            strokeWidth="10"
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={dashOffset}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
          <p className="text-3xl font-bold text-slate-900">{numericScore}</p>
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            / 10
          </p>
        </div>
      </div>

      <div>
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          Clinical Urgency
        </p>
        <p className="mt-1 text-lg font-semibold text-slate-900">{category}</p>
        <p className="mt-2 max-w-xs text-sm leading-6 text-slate-600">
          Visualized from the current AI risk score so high-acuity cases stand out immediately.
        </p>
      </div>
    </div>
  );
}

function HistoryGroup({ title, items, emptyLabel }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4">
      <p className="text-sm font-semibold text-slate-900">{title}</p>
      {items && items.length > 0 ? (
        <ul className="mt-3 space-y-2 text-sm text-slate-700">
          {items.map((item) => (
            <li key={`${title}-${item.label}`} className="rounded-lg bg-slate-50 px-3 py-2">
              <p className="font-medium text-slate-800">{item.label}</p>
              {item.source && (
                <p className="mt-1 text-xs uppercase tracking-wide text-slate-400">
                  Source: {item.source}
                </p>
              )}
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-3 text-sm text-slate-500">{emptyLabel}</p>
      )}
    </div>
  );
}

function ReportSection({ title, children, className = "" }) {
  return (
    <div className={`rounded-2xl border border-slate-200 bg-slate-50 p-5 ${className}`}>
      <h3 className="text-base font-semibold text-slate-900">{title}</h3>
      <div className="mt-3 space-y-3 text-sm leading-6 text-slate-700">
        {children}
      </div>
    </div>
  );
}

function getEvidenceColor(category) {
  if (!category) return "bg-slate-100 text-slate-700";

  const normalized = String(category).toLowerCase();

  if (normalized.includes("emergency")) return "bg-red-100 text-red-700";
  if (normalized.includes("chronic")) return "bg-orange-100 text-orange-700";
  if (normalized.includes("renal")) return "bg-blue-100 text-blue-700";

  return "bg-slate-100 text-slate-700";
}

function escapeRegExp(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function highlightMatches(text, query) {
  if (!query) {
    return text;
  }

  const pattern = new RegExp(`(${escapeRegExp(query)})`, "gi");

  return String(text)
    .split(pattern)
    .map((part, index) =>
      part.toLowerCase() === query.toLowerCase() ? (
        <mark key={`${part}-${index}`} className="rounded bg-yellow-200 px-1">
          {part}
        </mark>
      ) : (
        <span key={`${part}-${index}`}>{part}</span>
      )
    );
}

function countMatches(text, query) {
  if (!query) {
    return 0;
  }

  const matches = String(text).match(new RegExp(escapeRegExp(query), "gi"));
  return matches ? matches.length : 0;
}

const DISPLAY_REPLACEMENTS = [
  [/\bmarzinal\b/gi, "Marginal"],
  [/\brecieved\b/gi, "received"],
  [/\breveiw\b/gi, "review"],
  [/\bincase\b/gi, "in case"],
  [/\bPaneCBC\b/g, "Panel CBC"],
];

function normalizeDisplayText(text) {
  if (!text) {
    return "Not available";
  }

  let normalized = String(text).replace(/\s+/g, " ").trim();

  DISPLAY_REPLACEMENTS.forEach(([pattern, replacement]) => {
    normalized = normalized.replace(pattern, replacement);
  });

  return normalized || "Not available";
}

function hasKeyword(text, pattern) {
  return pattern.test(text);
}

function pushUnique(items, value) {
  if (value && !items.includes(value)) {
    items.push(value);
  }
}

function getAdmissionTypeLabel(type) {
  if (type === "Elective") {
    return "Elective / Planned";
  }

  return type || "Not available";
}

function getClinicalPriorityReason(patient) {
  const admissionType = patient.admission?.type;
  const riskCategory = patient.risk?.category;

  if (riskCategory === "Critical" && admissionType === "Elective") {
    return "High-risk patient requiring close monitoring despite planned admission pathway.";
  }

  if (riskCategory === "Critical" && admissionType === "Urgent") {
    return "High-risk patient requiring accelerated admission coordination and close monitoring.";
  }

  if (admissionType === "Emergency") {
    return "Acute clinical signals support immediate attention and rapid admission coordination.";
  }

  if (riskCategory === "High") {
    return "High-risk factors support closer observation during the current admission pathway.";
  }

  return patient.admission?.reasoning || patient.risk?.reasoning || "Clinician review is recommended.";
}

function getAiModeTone(profile) {
  if (profile?.llmApplied) {
    return "green";
  }

  if (profile?.llmEligible) {
    return "blue";
  }

  return "slate";
}

function getAiModeDescription(profile) {
  if (profile?.llmApplied) {
    return "This patient is in the top-priority cohort and includes LLM-assisted enrichment layered on top of the rule-based engine.";
  }

  if (profile?.llmEligible) {
    return "This patient is in the top-priority cohort and is eligible for LLM enrichment when live or cached model output is available.";
  }

  return "This patient is currently using the rule-based intelligence engine. LLM enrichment is reserved for the top-priority cohort.";
}

function getConfidenceTone(confidence) {
  const numericConfidence = Number(confidence || 0);

  if (numericConfidence >= 80) {
    return "green";
  }

  if (numericConfidence >= 60) {
    return "orange";
  }

  return "red";
}

function buildNormalizedSummary(patient) {
  const diagnosisText = normalizeDisplayText(patient.clinical?.diagnosis);
  const notesText = normalizeDisplayText(patient.clinical?.clinicalNotes);
  const historyText = normalizeDisplayText(patient.clinical?.vitalRemarks);
  const adviceText = normalizeDisplayText(patient.clinical?.doctorAdvice);
  const combinedText = `${diagnosisText} ${notesText} ${historyText} ${adviceText}`.toLowerCase();
  const summaryItems = [];

  if (
    hasKeyword(combinedText, /\bmarginal\b|\blymphoma\b/) &&
    hasKeyword(combinedText, /\brituximab\b/)
  ) {
    pushUnique(summaryItems, "Marginal zone lymphoma on maintenance Rituximab.");
  } else if (hasKeyword(combinedText, /\blymphoma\b/)) {
    pushUnique(summaryItems, "Lymphoma history remains part of the active hematology context.");
  }

  if (hasKeyword(combinedText, /\b(anemia|anaemia)\b.*\brecovered\b|\brecovered\b.*\b(anemia|anaemia)\b/)) {
    pushUnique(summaryItems, "Anemia recovered.");
  } else if (hasKeyword(combinedText, /\b(anemia|anaemia)\b|\bhaemolytic\b|\bhemolytic\b|\bcold agglutinin\b/)) {
    pushUnique(summaryItems, "Anemia and hematology markers remain under follow-up.");
  }

  if (hasKeyword(combinedText, /\bdiabetes mellitus\b|\bdm\b|\bdiabetes\b/)) {
    if (hasKeyword(combinedText, /\bnephropathy\b/)) {
      pushUnique(summaryItems, "Diabetes mellitus with nephropathy.");
    } else {
      pushUnique(summaryItems, "Diabetes mellitus noted in the clinical history.");
    }
  }

  if (hasKeyword(combinedText, /\bhbv\b|\bhepatitis b\b/)) {
    pushUnique(summaryItems, "Chronic HBV carrier.");
  }

  if (
    summaryItems.length < 4 &&
    hasKeyword(combinedText, /\brenal dysfunction\b|\bcreat\b|\bcreatinine\b|\bkidney\b|\brenal\b/)
  ) {
    pushUnique(summaryItems, "Renal dysfunction and creatinine abnormalities require monitoring.");
  }

  if (
    summaryItems.length < 4 &&
    hasKeyword(combinedText, /\bpotassium\b|\bk -\d|\bk-\d|\bkft\b|\bmetabolic\b/)
  ) {
    pushUnique(summaryItems, "Metabolic abnormalities support close inpatient monitoring.");
  }

  if (summaryItems.length > 0) {
    return summaryItems.slice(0, 4);
  }

  return ["Clinical source text is available below in the original form."];
}

function buildPriorityInsights(patient, evidenceItems, clinicalIntelligence) {
  const insights = [];

  function pushInsight(title, explanation, source, evidence) {
    if (!title || insights.some((item) => item.title === title)) {
      return;
    }

    insights.push({
      title,
      explanation,
      source,
      evidence,
    });
  }

  const emergencyEvidence = evidenceItems.find((item) =>
    String(item.category || "").toLowerCase().includes("emergency")
  );
  const renalEvidence = clinicalIntelligence?.comorbidities?.find((item) =>
    /renal|kidney|nephro|creatinine|hyperkalemia/i.test(item.label)
  );
  const oncologyEvidence = clinicalIntelligence?.comorbidities?.find((item) =>
    /lymphoma|oncology|transplant|myeloma/i.test(item.label)
  );
  const symptomEvidence = clinicalIntelligence?.possibleSymptoms?.[0];
  const primaryCode = clinicalIntelligence?.primaryIcd10;

  if (emergencyEvidence || patient.admission?.type === "Emergency") {
    pushInsight(
      "Acute escalation signal detected",
      "Admission urgency increased because the source notes contain direct escalation or emergency language.",
      emergencyEvidence?.source_section || emergencyEvidence?.source || "Admission reasoning",
      emergencyEvidence?.evidence_snippet ||
        emergencyEvidence?.evidence ||
        patient.admission?.reasoning
    );
  }

  if (renalEvidence) {
    pushInsight(
      "Renal instability contributes to priority",
      "Renal dysfunction, creatinine abnormalities, nephropathy, or metabolic derangement increase monitoring needs.",
      renalEvidence.source,
      renalEvidence.evidence
    );
  }

  if (oncologyEvidence) {
    pushInsight(
      "Complex oncology / transplant context",
      "Oncology, lymphoma, or transplant-related history raises admission complexity and the need for closer review.",
      oncologyEvidence.source,
      oncologyEvidence.evidence
    );
  }

  if (patient.journey?.progressionTrend === "Worsening") {
    pushInsight(
      "Longitudinal deterioration detected",
      "The patient journey shows worsening progression across visits, which increases operational priority.",
      "Journey history",
      patient.journey?.timelineSummary
    );
  }

  if (patient.bed?.type === "ICU" || patient.operational?.deferredTime?.label === "Cannot be safely delayed") {
    pushInsight(
      "Resource-intensive admission pathway",
      "ICU-level support or unsafe-to-delay status indicates this case needs immediate operational coordination.",
      "Bed allocation / deferred time",
      patient.bed?.reasoning || patient.operational?.deferredTime?.reasoning
    );
  }

  if (primaryCode) {
    pushInsight(
      "Structured clinical coding confidence",
      `The extracted ICD-10 code ${primaryCode.code} (${primaryCode.label}) strengthens interpretability of the recommendation.`,
      primaryCode.source,
      primaryCode.evidence
    );
  }

  if (insights.length < 4 && symptomEvidence) {
    pushInsight(
      "Symptom burden supports observation",
      "The extracted symptom pattern contributes to why the AI recommends closer review or admission planning.",
      symptomEvidence.source,
      symptomEvidence.evidence
    );
  }

  return insights.length > 0
    ? insights
    : [
        {
          title: "Combined clinical reasoning",
          explanation:
            "The AI priority was derived from the combined risk score, admission reasoning, and traceable evidence in the source clinical text.",
          source: "AI operational summary",
          evidence: patient.traceability?.summary || patient.risk?.reasoning,
        },
      ];
}

export default function PatientProfile() {
  const params = useParams();
  const patientId = decodeURIComponent((params.id || params.patientId || "").toString()).trim();
  const reportRef = useRef(null);

  const [patient, setPatient] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [noteSearch, setNoteSearch] = useState("");
  const [isDownloading, setIsDownloading] = useState(false);
  const [actionError, setActionError] = useState("");
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let isActive = true;

    async function loadPatient() {
      setLoading(true);
      setError("");

      try {
        const patientData = await getPatientById(patientId);

        if (!isActive) {
          return;
        }

        setPatient(patientData);
      } catch (loadError) {
        if (!isActive) {
          return;
        }

        setError(loadError.message || "Unable to load the patient profile.");
      } finally {
        if (isActive) {
          setLoading(false);
        }
      }
    }

    if (patientId) {
      loadPatient();
    } else {
      setError("Patient not found.");
      setLoading(false);
    }

    return () => {
      isActive = false;
    };
  }, [patientId, reloadKey]);

  const evidenceItems = useMemo(() => {
    if (!patient) {
      return [];
    }

    if (Array.isArray(patient.evidence_snippets)) {
      return patient.evidence_snippets;
    }

    if (patient.traceability?.evidenceTrace) {
      return parseTraceabilityString(String(patient.traceability.evidenceTrace));
    }

    if (patient.traceability?.summary) {
      return [{ evidence_snippet: patient.traceability.summary }];
    }

    return [];
  }, [patient]);

  const riskTrendData = useMemo(
    () => (patient ? parseRiskProgression(patient) : []),
    [patient]
  );

  const clinicalSections = useMemo(
    () => (patient ? getClinicalNoteSections(patient) : []),
    [patient]
  );

  const filteredClinicalSections = useMemo(() => {
    if (!noteSearch.trim()) {
      return clinicalSections;
    }

    const searchValue = noteSearch.toLowerCase();

    return clinicalSections.filter((section) =>
      section.content.toLowerCase().includes(searchValue)
    );
  }, [clinicalSections, noteSearch]);

  const totalSearchMatches = useMemo(
    () =>
      clinicalSections.reduce(
        (total, section) => total + countMatches(section.content, noteSearch),
        0
      ),
    [clinicalSections, noteSearch]
  );

  async function handleDownloadPdf() {
    if (!reportRef.current || !patient) {
      return;
    }

    setIsDownloading(true);
    setActionError("");

    try {
      const [{ jsPDF }, { default: html2canvas }] = await Promise.all([
        import("jspdf"),
        import("html2canvas"),
      ]);

      const canvas = await html2canvas(reportRef.current, {
        scale: 2,
        useCORS: true,
        backgroundColor: "#f8fafc",
        windowWidth: reportRef.current.scrollWidth,
      });

      const imageData = canvas.toDataURL("image/png");
      const pdf = new jsPDF("p", "pt", "a4");
      const margin = 24;
      const pdfWidth = pdf.internal.pageSize.getWidth();
      const pdfHeight = pdf.internal.pageSize.getHeight();
      const imageWidth = pdfWidth - margin * 2;
      const imageHeight = (canvas.height * imageWidth) / canvas.width;
      const printableHeight = pdfHeight - margin * 2;

      let remainingHeight = imageHeight;
      let position = margin;

      pdf.addImage(imageData, "PNG", margin, position, imageWidth, imageHeight);
      remainingHeight -= printableHeight;

      while (remainingHeight > 0) {
        pdf.addPage();
        position = margin - (imageHeight - remainingHeight);
        pdf.addImage(imageData, "PNG", margin, position, imageWidth, imageHeight);
        remainingHeight -= printableHeight;
      }

      pdf.save(`${patient.patientId}-admission-report.pdf`);
    } catch {
      setActionError("Unable to generate the PDF report right now.");
    } finally {
      setIsDownloading(false);
    }
  }

  function handlePrint() {
    setActionError("");
    window.print();
  }

  if (loading) {
    return (
      <LoadingScreen
        title="Loading patient profile..."
        message="Building the latest patient admission report and clinical traceability."
      />
    );
  }

  if (error) {
    return (
      <ErrorState
        title="Patient profile unavailable"
        message={error}
        onRetry={() => setReloadKey((currentValue) => currentValue + 1)}
        linkTo="/dashboard"
        linkLabel="Back to Dashboard"
      />
    );
  }

  if (!patient) {
    return (
      <EmptyState
        title="Patient profile not found"
        message="This patient could not be located in the current dataset."
        linkTo="/dashboard"
        linkLabel="Back to Dashboard"
      />
    );
  }

  const reportDate = formatDate(patient.visitDate);
  const admissionTypeLabel = getAdmissionTypeLabel(patient.admission?.type);
  const clinicalPriorityReason = getClinicalPriorityReason(patient);
  const criticalPriorityAlert =
    patient.risk?.category === "Critical" && patient.admission?.type === "Elective";
  const operational = patient.operational || {};
  const intelligenceProfile = operational.intelligenceProfile || {};
  const caseType = operational.caseType || {};
  const packageIntelligence = operational.packageIntelligence || {};
  const lengthOfStay = operational.lengthOfStay || {};
  const readmissionRisk = operational.readmissionRisk || {};
  const noShowRisk = operational.noShowRisk || {};
  const deferredTime = operational.deferredTime || {};
  const admissionConversionProbability =
    operational.admissionConversionProbability || {};
  const treatmentPlan = operational.treatmentPlan || {};
  const clinicalTimeline = operational.clinicalTimeline || {};
  const clinicalTimelineStages = clinicalTimeline.stages || [];
  const clinicalIntelligence = operational.clinicalIntelligence || {};
  const explicitConfidence = Number(patient.procedure?.explicitConfidence || 0);
  const inferredConfidence = Number(patient.procedure?.inferredConfidence || 0);
  const icd10Codes = clinicalIntelligence.icd10Codes || [];
  const comorbidities = clinicalIntelligence.comorbidities || [];
  const symptoms = clinicalIntelligence.possibleSymptoms || [];
  const structuredHistory = clinicalIntelligence.structuredHistory || {};
  const diseaseCohorts = clinicalIntelligence.diseaseCohorts || [];
  const normalizedSummaryItems =
    operational.normalizedSummary?.length > 0
      ? operational.normalizedSummary
      : buildNormalizedSummary(patient);
  const priorityInsights =
    operational.priorityInsights?.length > 0
      ? operational.priorityInsights
      : buildPriorityInsights(patient, evidenceItems, clinicalIntelligence);
  const aiModeLabel = intelligenceProfile.primaryEngine || "Rule-based";
  const aiModeTone = getAiModeTone(intelligenceProfile);
  const aiModeDescription = getAiModeDescription(intelligenceProfile);

  return (
    <div className="min-h-screen p-6">
      <div className="mb-4 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm font-medium text-amber-900">
        AI recommendation is decision-support only. Final admission decision must
        be validated by a clinician.
      </div>

      <div className="mb-6 flex flex-col gap-4 print:hidden lg:flex-row lg:items-center lg:justify-between">
        <div>
          <Link
            to="/dashboard"
            className="mb-4 inline-flex items-center gap-2 text-sm font-medium text-blue-600 hover:text-blue-700"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to Dashboard
          </Link>
          <h1 className="text-3xl font-bold text-slate-900">
            {patient.patientName}
          </h1>
          <p className="mt-2 text-slate-600">
            {patient.department} | {patient.doctorName}
          </p>
          <div className="mt-4 flex flex-wrap items-center gap-2">
            <Badge tone={aiModeTone}>AI Mode: {aiModeLabel}</Badge>
            {intelligenceProfile.priorityScore ? (
              <Badge tone="orange">
                Priority Score: {intelligenceProfile.priorityScore}
              </Badge>
            ) : null}
          </div>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-600">
            {aiModeDescription}
          </p>
        </div>

        <div className="flex flex-wrap gap-3">
          <button
            type="button"
            onClick={handlePrint}
            className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm font-semibold text-slate-700 shadow-sm hover:border-slate-300 hover:text-slate-900"
          >
            <Printer className="h-4 w-4" />
            Print Report
          </button>
          <button
            type="button"
            onClick={handleDownloadPdf}
            disabled={isDownloading}
            aria-label="Download PDF"
            className="inline-flex items-center gap-2 rounded-xl bg-slate-900 px-4 py-3 text-sm font-semibold text-white shadow-sm hover:bg-slate-700 disabled:cursor-not-allowed disabled:bg-slate-400"
          >
            <Download className="h-4 w-4" />
            {isDownloading ? "Preparing PDF..." : "Download AI Admission Report"}
          </button>
        </div>
      </div>

      {actionError && (
        <div className="mb-4 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 print:hidden">
          {actionError}
        </div>
      )}

      <div
        ref={reportRef}
        className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm print:border-none print:p-0 print:shadow-none"
      >
        <div className="border-b border-slate-200 pb-6">
          <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
            <div>
              <p className="text-sm font-semibold uppercase tracking-[0.25em] text-slate-500">
                AI Admission Report
              </p>
              <h2 className="mt-2 text-3xl font-bold text-slate-900">
                {patient.patientName}
              </h2>
              <p className="mt-2 text-slate-600">
                Prepared for admission review on {reportDate}
              </p>
            </div>

            <div className="flex flex-wrap gap-2">
              <Badge tone="red">Risk: {patient.risk?.category}</Badge>
              <Badge tone="orange">{admissionTypeLabel}</Badge>
              <Badge tone="blue">{patient.bed?.type}</Badge>
              <Badge tone="green">{patient.validation?.status}</Badge>
              <Badge tone={aiModeTone}>AI Mode: {aiModeLabel}</Badge>
            </div>
          </div>
          <p className="mt-4 max-w-3xl text-sm leading-6 text-slate-600">
            {aiModeDescription}
          </p>
        </div>

        <div className="mt-6 grid grid-cols-1 gap-4 md:grid-cols-2">
          <ReportSection title="Patient Details">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <DetailItem label="Patient ID" value={patient.patientId} />
              <DetailItem label="Visit Date" value={reportDate} />
              <DetailItem label="Department" value={patient.department} />
              <DetailItem label="Doctor" value={patient.doctorName} />
              <DetailItem label="Customer Type" value={patient.customerType} />
              <DetailItem label="Case Type" value={caseType.label} />
              <DetailItem label="AI Mode" value={aiModeLabel} />
              <DetailItem
                label="Priority Score"
                value={
                  intelligenceProfile.priorityScore
                    ? String(intelligenceProfile.priorityScore)
                    : "Not available"
                }
              />
              <DetailItem
                label="Primary Cohort"
                value={clinicalIntelligence.primaryCohort}
              />
              <DetailItem
                label="Primary ICD-10"
                value={
                  clinicalIntelligence.primaryIcd10
                    ? `${clinicalIntelligence.primaryIcd10.code} ${clinicalIntelligence.primaryIcd10.label}`
                    : "Not available"
                }
              />
              <DetailItem
                label="Repeat Visit"
                value={patient.journey?.repeatVisit || "Not available"}
              />
            </div>
          </ReportSection>

          <ReportSection title="Risk Summary">
            <RiskGauge
              score={patient.risk?.score}
              category={patient.risk?.category}
            />
            <div className="pt-1">
              <p>
                <strong>Category:</strong> {patient.risk?.category}
              </p>
              <p className="mt-2">
                <strong>Red Flags:</strong>{" "}
                {patient.risk?.redFlags || "Not available"}
              </p>
            </div>
            <p>{patient.risk?.reasoning}</p>
          </ReportSection>

          <ReportSection title="Clinical Coding & Cohorts">
            <div>
              <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
                ICD-10 Codes
              </p>
              <ChipList
                items={icd10Codes}
                emptyLabel="No structured coding match found."
                tone="blue"
              />
            </div>
            <div className="pt-3">
              <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
                Disease Cohorts
              </p>
              <ChipList
                items={diseaseCohorts}
                emptyLabel="No disease cohort assigned."
                tone="orange"
              />
            </div>
          </ReportSection>

          <ReportSection title="Comorbidities & Symptoms">
            <div>
              <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
                Comorbidities
              </p>
              <ChipList
                items={comorbidities}
                emptyLabel="No structured comorbidity extracted."
                tone="red"
              />
            </div>
            <div className="pt-3">
              <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
                Possible Symptoms
              </p>
              <ChipList
                items={symptoms}
                emptyLabel="No symptom keywords extracted."
                tone="green"
              />
            </div>
          </ReportSection>

          <ReportSection title="Admission Decision">
            <p>
              <strong>Admission Type:</strong> {admissionTypeLabel}
            </p>
            <p>
              <strong>Clinical Priority:</strong> {patient.risk?.category}
            </p>
            <p>
              <strong>Reason:</strong> {clinicalPriorityReason}
            </p>
            <p>{patient.admission?.reasoning}</p>
            <p>{patient.admission?.summary}</p>
          </ReportSection>

          <ReportSection title="Bed Allocation">
            <p>
              <strong>Recommended Bed:</strong> {patient.bed?.type}
            </p>
            <p>{patient.bed?.reasoning}</p>
            <p>{patient.bed?.summary}</p>
          </ReportSection>

          <ReportSection title="Procedure Intelligence">
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <MetricCard
                icon={BedDouble}
                label="Explicit Procedure"
                value={patient.procedure?.explicitProcedure}
                hint={patient.procedure?.explicitSource || "No explicit source captured."}
                tone="blue"
              />
              <MetricCard
                icon={Search}
                label="Inferred Procedure"
                value={patient.procedure?.inferredProcedure}
                hint={patient.procedure?.inferredSource || "No inferred source captured."}
                tone="orange"
              />
            </div>
            <div className="flex flex-wrap gap-2 pt-1">
              {explicitConfidence > 0 ? (
                <Badge tone={getConfidenceTone(explicitConfidence)}>
                  Explicit Confidence: {explicitConfidence}%
                </Badge>
              ) : null}
              {inferredConfidence > 0 ? (
                <Badge tone={getConfidenceTone(inferredConfidence)}>
                  Inferred Confidence: {inferredConfidence}%
                </Badge>
              ) : null}
              {explicitConfidence === 0 && inferredConfidence === 0 ? (
                <Badge tone="slate">Confidence score not available</Badge>
              ) : null}
            </div>
          </ReportSection>

          <ReportSection title="Operational Forecast">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
              <MetricCard
                icon={Coins}
                label="Expected Revenue"
                value={packageIntelligence.expectedRevenue}
                hint={packageIntelligence.revenueCategory}
                tone={
                  ["High Value", "Strategic Value"].includes(
                    packageIntelligence.revenueCategory
                  )
                    ? "purple"
                    : "slate"
                }
              />
              <MetricCard
                icon={CalendarRange}
                label="Estimated LOS"
                value={lengthOfStay.label}
                hint={lengthOfStay.reasoning}
                tone="blue"
              />
              <MetricCard
                icon={Repeat2}
                label="Readmission Risk"
                value={readmissionRisk.label}
                hint={readmissionRisk.reasoning}
                tone="orange"
              />
              <MetricCard
                icon={Search}
                label="No-show / Dropout Risk"
                value={noShowRisk.label}
                hint={noShowRisk.reasoning}
                tone="slate"
              />
              <MetricCard
                icon={TimerReset}
                label="Deferred Time"
                value={deferredTime.label}
                hint={deferredTime.reasoning}
                tone="red"
              />
              <MetricCard
                icon={BadgePercent}
                label="Admission Conversion"
                value={
                  admissionConversionProbability.percentage
                    ? `${admissionConversionProbability.percentage}% (${admissionConversionProbability.label})`
                    : "Not available"
                }
                hint={admissionConversionProbability.reasoning}
                tone="green"
              />
            </div>
          </ReportSection>

          <ReportSection title="Treatment Planning">
            <p>
              <strong>Primary Treatment:</strong> {treatmentPlan.primary}
            </p>
            <p>
              <strong>Secondary Treatment:</strong> {treatmentPlan.secondary}
            </p>
            <p>{treatmentPlan.reasoning}</p>
          </ReportSection>

          <ReportSection title="Validation Status">
            <p>
              <strong>Status:</strong> {patient.validation?.status}
            </p>
            <p>
              <strong>Issues:</strong> {patient.validation?.issueCount}
            </p>
            <p>{patient.validation?.summary}</p>
            <p>{patient.traceability?.safetyNote}</p>
          </ReportSection>

          <ReportSection title="Evidence">
            <p>
              <strong>Evidence Count:</strong> {patient.traceability?.evidenceCount}
            </p>
            <p>{patient.traceability?.summary}</p>

            <div className="space-y-3">
              {evidenceItems.length > 0 ? (
                evidenceItems.map((item, index) => (
                  <div
                    key={`${item.keyword || "evidence"}-${index}`}
                    className="rounded-xl border border-slate-200 bg-white p-3"
                  >
                    <div className="mb-2 flex items-center justify-between gap-3">
                      <p className="font-semibold text-slate-800">
                        Evidence #{index + 1}
                      </p>
                      <span
                        className={`rounded-full px-3 py-1 text-xs font-semibold ${getEvidenceColor(item.category)}`}
                      >
                        {item.category || "clinical"}
                      </span>
                    </div>
                    <p>
                      <strong>Keyword:</strong> {item.keyword || "Not available"}
                    </p>
                    <p>
                      <strong>Source:</strong>{" "}
                      {item.source_section || item.source || "Not available"}
                    </p>
                    <p>{item.evidence_snippet || item.evidence || "Not available"}</p>
                  </div>
                ))
              ) : (
                <p>No evidence available.</p>
              )}
            </div>
          </ReportSection>

          <ReportSection title="AI Normalized Summary">
            <ul className="list-disc space-y-2 pl-5">
              {normalizedSummaryItems.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </ReportSection>

          <ReportSection title="Why AI Gave This Priority">
            <div className="space-y-3">
              {priorityInsights.map((item) => (
                <div
                  key={item.title}
                  className="rounded-xl border border-slate-200 bg-white p-4"
                >
                  <p className="font-semibold text-slate-900">{item.title}</p>
                  <p className="mt-2 text-sm leading-6 text-slate-700">
                    {item.explanation}
                  </p>
                  <p className="mt-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
                    Source: {item.source}
                  </p>
                  <p className="mt-2 rounded-lg bg-slate-50 px-3 py-2 text-sm text-slate-600">
                    {item.evidence}
                  </p>
                </div>
              ))}
            </div>
          </ReportSection>

          <ReportSection title="Structured History" className="md:col-span-2">
            <p>{structuredHistory.summary}</p>
            <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
              <HistoryGroup
                title="Past Conditions"
                items={structuredHistory.pastConditions}
                emptyLabel="No past-condition summary extracted."
              />
              <HistoryGroup
                title="Past Surgeries / Procedures"
                items={structuredHistory.surgeries}
                emptyLabel="No prior surgery signal extracted."
              />
              <HistoryGroup
                title="Medication History"
                items={structuredHistory.medications}
                emptyLabel="No medication list parsed."
              />
              <HistoryGroup
                title="Family History"
                items={structuredHistory.familyHistory}
                emptyLabel="No family history phrase extracted."
              />
            </div>
          </ReportSection>

          <ReportSection
            title="Structured Clinical Timeline"
            className="md:col-span-2"
          >
            <p>{clinicalTimeline.summary}</p>
            <div className="mt-4 space-y-0">
              {clinicalTimelineStages.map((stage, index) => (
                <div
                  key={`${stage.stage}-${stage.date}`}
                  className="relative flex gap-4 pb-6 last:pb-0"
                >
                  <div className="flex w-10 flex-col items-center">
                    <div className="z-10 flex h-10 w-10 items-center justify-center rounded-full bg-slate-900 text-sm font-bold text-white">
                      {index + 1}
                    </div>
                    {index < clinicalTimelineStages.length - 1 && (
                      <div className="mt-2 h-full w-px bg-slate-300" />
                    )}
                  </div>

                  <div className="flex-1 rounded-xl border border-slate-200 bg-white p-4">
                    <div className="flex flex-col gap-1 md:flex-row md:items-center md:justify-between">
                      <p className="font-semibold text-slate-900">{stage.stage}</p>
                      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                        {stage.date}
                      </p>
                    </div>
                    <p className="mt-2 text-sm leading-6 text-slate-700">
                      {stage.summary}
                    </p>
                    <p className="mt-2 text-xs uppercase tracking-wide text-slate-400">
                      Source: {stage.source}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </ReportSection>
        </div>
      </div>

      <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-2 print:hidden">
        <Panel title="Operational Alerts">
          <div className="space-y-3">
            {patient.risk?.category === "Critical" && (
              <div className="flex items-start gap-3 rounded-xl border border-red-200 bg-red-50 p-4 text-red-700">
                <TriangleAlert className="mt-0.5 h-5 w-5" />
                <div>
                  <p className="font-medium">
                    {criticalPriorityAlert
                      ? "Critical clinical priority despite planned admission"
                      : "Immediate clinical escalation required"}
                  </p>
                  <p className="mt-1 text-sm">
                    {criticalPriorityAlert
                      ? "High-risk patient requiring close monitoring despite planned admission pathway."
                      : "Critical-risk classification indicates high-acuity monitoring."}
                  </p>
                </div>
              </div>
            )}

            {patient.bed?.type === "ICU" && (
              <div className="flex items-start gap-3 rounded-xl border border-blue-200 bg-blue-50 p-4 text-blue-700">
                <BedDouble className="mt-0.5 h-5 w-5" />
                <div>
                  <p className="font-medium">ICU bed coordination required</p>
                  <p className="mt-1 text-sm">
                    The bed engine recommends ICU-level support for this admission.
                  </p>
                </div>
              </div>
            )}

            {patient.admission?.type === "Emergency" && (
              <div className="flex items-start gap-3 rounded-xl border border-orange-200 bg-orange-50 p-4 text-orange-700">
                <Siren className="mt-0.5 h-5 w-5" />
                <div>
                  <p className="font-medium">Emergency admission workflow activated</p>
                  <p className="mt-1 text-sm">
                    Emergency routing should stay prioritized through bed placement.
                  </p>
                </div>
              </div>
            )}

            {patient.validation?.status === "Validated" && (
              <div className="flex items-start gap-3 rounded-xl border border-green-200 bg-green-50 p-4 text-green-700">
                <ShieldCheck className="mt-0.5 h-5 w-5" />
                <div>
                  <p className="font-medium">Profile passed validation checks</p>
                  <p className="mt-1 text-sm">{patient.validation?.summary}</p>
                </div>
              </div>
            )}
          </div>
        </Panel>

        <Panel title="Patient Journey">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <DetailItem label="Visit Count" value={patient.journey?.visitCount} />
            <DetailItem
              label="Progression"
              value={patient.journey?.progressionTrend}
            />
            <DetailItem
              label="First Visit"
              value={formatDate(patient.journey?.firstVisitDate)}
            />
            <DetailItem
              label="Latest Visit"
              value={formatDate(patient.journey?.latestVisitDate)}
            />
          </div>
          <p className="mt-4 text-sm leading-6 text-slate-700">
            {patient.journey?.timelineSummary}
          </p>
        </Panel>

        <Panel title="Risk Trend">
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={riskTrendData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="visit" />
                <YAxis domain={[0, 10]} />
                <Tooltip />
                <Line
                  type="monotone"
                  dataKey="risk"
                  stroke="#0f172a"
                  strokeWidth={3}
                  dot={{ r: 5 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Panel>

        <Panel title="AI Evidence & Traceability">
          <p className="text-sm leading-6 text-slate-700">
            {patient.traceability?.summary}
          </p>
          <div className="mt-4 space-y-3">
            {evidenceItems.length > 0 ? (
              evidenceItems.map((item, index) => (
                <div
                  key={`${item.keyword || "trace"}-${index}`}
                  className="rounded-xl border border-slate-200 bg-slate-50 p-4"
                >
                  <div className="mb-2 flex items-center justify-between gap-3">
                    <p className="font-semibold text-slate-800">
                      Evidence #{index + 1}
                    </p>
                    <span
                      className={`rounded-full px-3 py-1 text-xs font-semibold ${getEvidenceColor(item.category)}`}
                    >
                      {item.category || "clinical"}
                    </span>
                  </div>
                  <p className="text-sm text-slate-500">
                    <strong>Keyword:</strong> {item.keyword || "Not available"}
                  </p>
                  <p className="mt-1 text-sm text-slate-500">
                    <strong>Source:</strong>{" "}
                    {item.source_section || item.source || "Not available"}
                  </p>
                  <p className="mt-2 text-sm leading-6 text-slate-700">
                    {item.evidence_snippet || item.evidence || "Not available"}
                  </p>
                </div>
              ))
            ) : (
              <p className="text-slate-500">No evidence available.</p>
            )}
          </div>
        </Panel>

        <Panel title="Treatment Pathway">
          <p className="text-sm leading-6 text-slate-700">
            <strong>Primary Treatment:</strong> {treatmentPlan.primary}
          </p>
          <p className="mt-3 text-sm leading-6 text-slate-700">
            <strong>Secondary Treatment:</strong> {treatmentPlan.secondary}
          </p>
          <p className="mt-3 text-sm leading-6 text-slate-700">
            {treatmentPlan.reasoning}
          </p>
        </Panel>

        <Panel title="Clinical Intelligence Snapshot" className="lg:col-span-2">
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <div>
              <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
                ICD-10 Codes
              </p>
              <ChipList
                items={icd10Codes}
                emptyLabel="No structured coding match found."
                tone="blue"
              />
              <p className="mb-2 mt-4 text-xs font-semibold uppercase tracking-wide text-slate-500">
                Disease Cohorts
              </p>
              <ChipList
                items={diseaseCohorts}
                emptyLabel="No disease cohort assigned."
                tone="orange"
              />
            </div>

            <div>
              <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
                Comorbidities
              </p>
              <ChipList
                items={comorbidities}
                emptyLabel="No structured comorbidity extracted."
                tone="red"
              />
              <p className="mb-2 mt-4 text-xs font-semibold uppercase tracking-wide text-slate-500">
                Possible Symptoms
              </p>
              <ChipList
                items={symptoms}
                emptyLabel="No symptom keywords extracted."
                tone="green"
              />
            </div>
          </div>

          <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-2">
            <HistoryGroup
              title="Past Conditions"
              items={structuredHistory.pastConditions}
              emptyLabel="No past-condition summary extracted."
            />
            <HistoryGroup
              title="Past Surgeries / Procedures"
              items={structuredHistory.surgeries}
              emptyLabel="No prior surgery signal extracted."
            />
            <HistoryGroup
              title="Medication History"
              items={structuredHistory.medications}
              emptyLabel="No medication list parsed."
            />
            <HistoryGroup
              title="Family History"
              items={structuredHistory.familyHistory}
              emptyLabel="No family history phrase extracted."
            />
          </div>
        </Panel>
      </div>

      <div className="mt-6 print:hidden">
        <Panel title="Original Clinical Text">
          <p className="mb-4 text-sm text-slate-500">
            Exact source wording is preserved below for auditability. The normalized
            summary above improves readability without changing the original record.
          </p>
          <div className="mb-4 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <div className="relative w-full md:max-w-md">
              <Search className="absolute left-3 top-3 h-4 w-4 text-slate-400" />
              <input
                value={noteSearch}
                onChange={(event) => setNoteSearch(event.target.value)}
                placeholder="Search within clinical notes..."
                className="w-full rounded-xl border border-slate-200 py-2 pl-9 pr-3 text-sm outline-none focus:border-slate-400"
              />
            </div>
            {noteSearch.trim() ? (
              <p className="text-sm text-slate-500">
                {totalSearchMatches} match{totalSearchMatches === 1 ? "" : "es"} found
              </p>
            ) : (
              <p className="text-sm text-slate-500">
                Search terms like dialysis, seizure, creatinine, or transplant.
              </p>
            )}
          </div>

          <div className="space-y-4">
            {filteredClinicalSections.length > 0 ? (
              filteredClinicalSections.map((section) => (
                <details
                  key={section.title}
                  className="rounded-xl border border-slate-200 bg-slate-50 p-4"
                  open={Boolean(noteSearch.trim())}
                >
                  <summary className="cursor-pointer font-semibold text-slate-900">
                    {section.title}
                  </summary>
                  <p className="mt-3 whitespace-pre-wrap text-sm leading-6 text-slate-700">
                    {highlightMatches(section.content, noteSearch)}
                  </p>
                </details>
              ))
            ) : (
              <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 p-6 text-center text-slate-500">
                No clinical notes matched "{noteSearch}".
              </div>
            )}
          </div>
        </Panel>
      </div>
    </div>
  );
}
