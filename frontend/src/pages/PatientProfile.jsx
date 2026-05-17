import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  ArrowLeft,
  BedDouble,
  Download,
  Printer,
  Search,
  ShieldCheck,
  Siren,
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

function ReportSection({ title, children }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50 p-5">
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

function buildAiExplanation(patient, evidenceItems, clinicalSections) {
  const combinedText = [
    patient.risk?.reasoning,
    patient.admission?.reasoning,
    patient.admission?.summary,
    patient.bed?.reasoning,
    patient.traceability?.summary,
    ...clinicalSections.map((section) => section.content),
    ...evidenceItems.map(
      (item) =>
        `${item.category || ""} ${item.keyword || ""} ${item.source_section || ""} ${item.evidence_snippet || item.evidence || ""}`
    ),
  ]
    .join(" ")
    .toLowerCase();

  const explanationItems = [];

  if (
    evidenceItems.some((item) => String(item.category || "").toLowerCase().includes("emergency")) ||
    /emergency|urgent|seizure|admit|admission|vomiting/.test(combinedText)
  ) {
    explanationItems.push(
      "Emergency or high-acuity keywords were detected in the evidence trail and source notes."
    );
  }

  if (/diabetes|renal|kidney|creat|creatinine|potassium|nephropathy/.test(combinedText)) {
    explanationItems.push(
      "Renal dysfunction, creatinine abnormalities, nephropathy, or metabolic abnormalities increase monitoring needs."
    );
  }

  if (/oncology|lymphoma|transplant|biopsy|chemo|cancer/.test(combinedText)) {
    explanationItems.push(
      "Oncology, biopsy, or transplant-related context increases the complexity of the admission decision."
    );
  }

  if (/creat|creatinine|potassium|seizure|bleed|hypotension|tachy/.test(combinedText)) {
    explanationItems.push(
      "Symptom severity and laboratory indicators suggest that closer observation may be required."
    );
  }

  if (patient.journey?.progressionTrend === "Worsening") {
    explanationItems.push(
      "The patient journey shows worsening progression across visits, which raises priority."
    );
  }

  if (patient.bed?.type === "ICU") {
    explanationItems.push(
      "The bed allocation engine recommends ICU-level support based on the detected acuity."
    );
  }

  const uniqueExplanationItems = Array.from(new Set(explanationItems));

  return uniqueExplanationItems.length > 0
    ? uniqueExplanationItems
    : [
        "The AI priority was derived from the combined risk score, admission reasoning, and traceable evidence in the source clinical text.",
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

  const normalizedSummaryItems = useMemo(
    () => (patient ? buildNormalizedSummary(patient) : []),
    [patient]
  );

  const aiExplanationItems = useMemo(
    () => (patient ? buildAiExplanation(patient, evidenceItems, clinicalSections) : []),
    [clinicalSections, evidenceItems, patient]
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
            </div>
          </div>
        </div>

        <div className="mt-6 grid grid-cols-1 gap-4 md:grid-cols-2">
          <ReportSection title="Patient Details">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <DetailItem label="Patient ID" value={patient.patientId} />
              <DetailItem label="Visit Date" value={reportDate} />
              <DetailItem label="Department" value={patient.department} />
              <DetailItem label="Doctor" value={patient.doctorName} />
              <DetailItem label="Customer Type" value={patient.customerType} />
              <DetailItem
                label="Repeat Visit"
                value={patient.journey?.repeatVisit || "Not available"}
              />
            </div>
          </ReportSection>

          <ReportSection title="Risk Summary">
            <p>
              <strong>Score:</strong> {patient.risk?.score}/10
            </p>
            <p>
              <strong>Category:</strong> {patient.risk?.category}
            </p>
            <p>{patient.risk?.reasoning}</p>
            <p>
              <strong>Red Flags:</strong> {patient.risk?.redFlags || "Not available"}
            </p>
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
            <p>
              <strong>Explicit Procedure:</strong>{" "}
              {patient.procedure?.explicitProcedure}
            </p>
            <p>
              <strong>Explicit Confidence:</strong>{" "}
              {patient.procedure?.explicitConfidence}%
            </p>
            <p>
              <strong>Explicit Source:</strong> {patient.procedure?.explicitSource}
            </p>
            <p>
              <strong>Inferred Procedure:</strong>{" "}
              {patient.procedure?.inferredProcedure}
            </p>
            <p>
              <strong>Inference Source:</strong> {patient.procedure?.inferredSource}
            </p>
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
            <ul className="list-disc space-y-2 pl-5">
              {aiExplanationItems.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
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
