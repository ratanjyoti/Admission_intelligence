import React, { useEffect, useMemo, useRef, useState, memo } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import {
  Activity,
  AlertTriangle,
  Brain,
  Bed,
  ChevronLeft,
  ChevronRight,
  Download,
  HeartPulse,
  IndianRupee,
  Minus,
  Repeat,
  Search,
  ShieldCheck,
  Stethoscope,
  TimerReset,
  TrendingDown,
  TrendingUp,
  Users,
  X,
} from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import EmptyState from "../components/EmptyState";
import ErrorState from "../components/ErrorState";
import LoadingScreen from "../components/LoadingScreen";
import { getAgenticPriorityQueue, getPatients } from "../lib/api";
import { buildDashboardCharts, buildDashboardSummary } from "../lib/patientData";

const COLORS = {
  Critical: "#dc2626",
  High: "#f97316",
  Medium: "#eab308",
  Low: "#16a34a",
  Emergency: "#dc2626",
  Urgent: "#f97316",
  Elective: "#2563eb",
  ICU: "#7f1d1d",
  HDU: "#c2410c",
  "General Ward": "#2563eb",
  "General Oncology Ward": "#7c3aed",
  "Daycare Bay": "#059669",
  "Post-Surgical General Ward": "#9333ea",
};

const PAGE_SIZE_OPTIONS = [10, 25, 50];
const PRIORITY_FILTER_KEYS = [
  "risk",
  "admission",
  "bed",
  "progression",
  "cohort",
  "repeat",
  "revenue",
  "deferred",
  "readmission",
  "caseType",
];

function formatLakhs(value) {
  const numeric = Number(value || 0);
  return `Rs ${numeric.toFixed(1)}L`;
}

const StatCard = memo(function StatCard({
  title,
  value,
  icon: Icon,
  tone = "slate",
  onClick,
  isActive = false,
}) {
  const tones = {
    slate: "bg-slate-100 text-slate-700",
    red: "bg-red-100 text-red-700",
    orange: "bg-orange-100 text-orange-700",
    blue: "bg-blue-100 text-blue-700",
    green: "bg-green-100 text-green-700",
  };

  const cardClassName = `rounded-2xl border bg-white p-5 text-left shadow-sm transition ${onClick
      ? "cursor-pointer hover:-translate-y-0.5 hover:border-slate-300 hover:shadow-md"
      : ""
    } ${isActive
      ? "border-slate-900 ring-2 ring-slate-900/10"
      : "border-slate-200"
    }`;

  const content = (
    <>
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-slate-500">{title}</p>
          <h2 className="mt-3 text-3xl font-bold text-slate-900">{value}</h2>
        </div>
        <div className={`rounded-xl p-3 ${tones[tone]}`}>
          <Icon className="h-6 w-6" />
        </div>
      </div>
      {onClick && (
        <p className="mt-4 text-xs font-medium text-slate-500">
          {isActive ? "Priority view active" : "Click to focus these cases"}
        </p>
      )}
    </>
  );

  if (onClick) {
    return (
      <button type="button" onClick={onClick} className={cardClassName}>
        {content}
      </button>
    );
  }

  return <div className={cardClassName}>{content}</div>;
});

const PortfolioCard = memo(function PortfolioCard({ title, value, caption, tone = "slate" }) {
  const tones = {
    slate: "border-slate-200 bg-white text-slate-900",
    orange: "border-orange-200 bg-orange-50 text-orange-900",
    blue: "border-blue-200 bg-blue-50 text-blue-900",
  };

  return (
    <div className={`rounded-2xl border p-5 shadow-sm ${tones[tone]}`}>
      <p className="text-sm font-semibold uppercase tracking-wide text-slate-500">
        {title}
      </p>
      <p className="mt-3 text-3xl font-bold">{value}</p>
      <p className="mt-2 text-sm text-slate-600">{caption}</p>
    </div>
  );
});

const RiskScoreBar = memo(function RiskScoreBar({ score, risk }) {
  const width = `${Math.max(8, Math.min(100, (Number(score || 0) / 10) * 100))}%`;
  const colors = {
    Critical: "bg-red-600",
    High: "bg-orange-500",
    Medium: "bg-yellow-500",
    Low: "bg-green-500",
  };

  return (
    <div className="mt-2">
      <div className="flex items-center justify-between text-xs font-medium text-slate-500">
        <span>Score {score || 0}/10</span>
        <span>{risk || "Unknown"}</span>
      </div>
      <div className="mt-2 h-2 overflow-hidden rounded-full bg-slate-100">
        <div className={`h-full rounded-full ${colors[risk] || "bg-slate-400"}`} style={{ width }} />
      </div>
    </div>
  );
});

const ProgressionIndicator = memo(function ProgressionIndicator({ trend }) {
  if (trend === "Worsening") {
    return (
      <span className="inline-flex items-center gap-2 rounded-full bg-red-50 px-3 py-1 text-xs font-semibold text-red-700">
        <TrendingDown className="h-3.5 w-3.5" />
        Worsening
      </span>
    );
  }

  if (trend === "Improving") {
    return (
      <span className="inline-flex items-center gap-2 rounded-full bg-green-50 px-3 py-1 text-xs font-semibold text-green-700">
        <TrendingUp className="h-3.5 w-3.5" />
        Improving
      </span>
    );
  }

  return (
    <span className="inline-flex items-center gap-2 rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-700">
      <Minus className="h-3.5 w-3.5" />
      Stable
    </span>
  );
});

function getRowAccentClass(risk) {
  if (risk === "Critical") return "border-l-red-600";
  if (risk === "High") return "border-l-orange-500";
  if (risk === "Medium") return "border-l-yellow-500";
  if (risk === "Low") return "border-l-green-500";
  return "border-l-slate-300";
}

function InlineTooltip({ active, payload, label }) {
  if (!active || !payload?.length) {
    return null;
  }

  return (
    <div className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm shadow-lg">
      <p className="font-semibold text-slate-900">{label}</p>
      {payload.map((entry) => (
        <p key={`${entry.name}-${entry.dataKey}`} className="mt-1 text-slate-600">
          {entry.name || entry.dataKey}: {entry.value}
        </p>
      ))}
    </div>
  );
}

const RiskBadge = memo(function RiskBadge({ risk }) {
  const styles = {
    Critical: "border-red-200 bg-red-100 text-red-700",
    High: "border-orange-200 bg-orange-100 text-orange-700",
    Medium: "border-yellow-200 bg-yellow-100 text-yellow-700",
    Low: "border-green-200 bg-green-100 text-green-700",
  };

  return (
    <span
      className={`rounded-full border px-3 py-1 text-xs font-semibold ${styles[risk] || "border-slate-200 bg-slate-100 text-slate-700"
        }`}
    >
      {risk}
    </span>
  );
});

const AdmissionBadge = memo(function AdmissionBadge({ type }) {
  const styles = {
    Emergency: "border-red-200 bg-red-50 text-red-700",
    Urgent: "border-orange-200 bg-orange-50 text-orange-700",
    Elective: "border-blue-200 bg-blue-50 text-blue-700",
  };

  return (
    <span
      className={`inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-semibold ${styles[type] || "border-slate-200 bg-slate-100 text-slate-700"}`}
    >
      {type === "Emergency" && (
        <span className="relative flex h-2 w-2">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-red-400 opacity-75" />
          <span className="relative inline-flex h-2 w-2 rounded-full bg-red-500" />
        </span>
      )}
      {type}
    </span>
  );
});

function getRecommendedAction(patient) {
  if (patient.admission?.type === "Emergency") {
    return "Immediate clinical escalation";
  }

  if (patient.bed?.type === "ICU") {
    return "Coordinate ICU bed";
  }

  if (patient.journey?.progressionTrend === "Worsening") {
    return "Priority follow-up";
  }

  if (patient.procedure?.explicitProcedure !== "Not Explicitly Mentioned") {
    return "Plan admission/procedure";
  }

  return "Routine follow-up";
}

function escapeCsvValue(value) {
  const normalized = String(value ?? "")
    .replace(/\s+/g, " ")
    .trim();

  return `"${normalized.replace(/"/g, '""')}"`;
}

function buildPatientsCsv(patients) {
  const headers = [
    "Patient ID",
    "Patient Name",
    "Department",
    "Doctor",
    "Diagnosis",
    "Case Type",
    "Risk Category",
    "Risk Score",
    "Admission Type",
    "Bed Allocation",
    "Estimated LOS",
    "Expected Revenue",
    "Revenue Category",
    "Readmission Risk",
    "No-show Risk",
    "Deferred Time",
    "Progression",
    "Evidence Count",
    "AI Action",
  ];

  const rows = patients.map((patient) => [
    patient.patientId,
    patient.patientName,
    patient.department,
    patient.doctorName,
    patient.clinical?.diagnosis,
    patient.operational?.caseType?.label,
    patient.risk?.category,
    patient.risk?.score,
    patient.admission?.type,
    patient.bed?.type,
    patient.operational?.lengthOfStay?.label,
    patient.operational?.packageIntelligence?.expectedRevenue,
    patient.operational?.packageIntelligence?.revenueCategory,
    patient.operational?.readmissionRisk?.label,
    patient.operational?.noShowRisk?.label,
    patient.operational?.deferredTime?.label,
    patient.journey?.progressionTrend,
    patient.traceability?.evidenceCount,
    getRecommendedAction(patient),
  ]);

  return [headers, ...rows]
    .map((row) => row.map((value) => escapeCsvValue(value)).join(","))
    .join("\n");
}

export default function Dashboard() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const departmentFilter = searchParams.get("department") || "All";
  const riskFilter = searchParams.get("risk") || "All";
  const admissionFilter = searchParams.get("admission") || "All";
  const bedFilter = searchParams.get("bed") || "All";
  const progressionFilter = searchParams.get("progression") || "All";
  const cohortFilter = searchParams.get("cohort") || "All";
  const repeatFilter = searchParams.get("repeat") || "false";
  const revenueCategoryFilter = searchParams.get("revenue") || "All";
  const readmissionRiskFilter = searchParams.get("readmission") || "All";
  const deferredTimeFilter = searchParams.get("deferred") || "All";
  const caseTypeFilter = searchParams.get("caseType") || "All";
  const worklistRef = useRef(null);

  const [patients, setPatients] = useState([]);
  const [charts, setCharts] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [currentPage, setCurrentPage] = useState(1);
  const [rowsPerPage, setRowsPerPage] = useState(25);
  const [reloadKey, setReloadKey] = useState(0);
  const [priorityQueue, setPriorityQueue] = useState([]);
  const [priorityQueueLoading, setPriorityQueueLoading] = useState(false);
  const [priorityQueueError, setPriorityQueueError] = useState("");
  const [priorityQueueActive, setPriorityQueueActive] = useState(false);

  useEffect(() => {
    let isActive = true;

    async function loadDashboard() {
      setLoading(true);
      setError("");

      try {
        const patientsData = await getPatients();

        if (!isActive) {
          return;
        }

        const normalizedPatients = patientsData || [];
        setPatients(normalizedPatients);
        setCharts(buildDashboardCharts(normalizedPatients));
      } catch (loadError) {
        if (!isActive) {
          return;
        }

        setError(loadError.message || "Unable to load the dashboard.");
      } finally {
        if (isActive) {
          setLoading(false);
        }
      }
    }

    loadDashboard();

    return () => {
      isActive = false;
    };
  }, [reloadKey]);

  const activePriorityView = useMemo(() => {
    if (repeatFilter === "true") {
      return {
        label: "Repeat-Visit Patients",
        description:
          "Showing only patients with repeat-visit history that may need faster continuity review.",
      };
    }

    if (riskFilter !== "All") {
      return {
        label: `${riskFilter} Patients`,
        description: `Showing only patients marked with ${riskFilter} clinical priority.`,
      };
    }

    if (admissionFilter !== "All") {
      return {
        label: `${admissionFilter} Admissions`,
        description: `Showing only patients in the ${admissionFilter.toLowerCase()} admission pathway.`,
      };
    }

    if (bedFilter !== "All") {
      return {
        label: `${bedFilter} Bed Queue`,
        description: `Showing only patients currently mapped to ${bedFilter} bed planning.`,
      };
    }

    if (progressionFilter !== "All") {
      return {
        label: `${progressionFilter} Journey Trend`,
        description: `Showing only patients whose longitudinal journey is marked as ${progressionFilter.toLowerCase()}.`,
      };
    }

    if (cohortFilter !== "All") {
      return {
        label: `${cohortFilter} Cohort`,
        description: `Showing only patients grouped into the ${cohortFilter.toLowerCase()} disease cohort.`,
      };
    }

    if (revenueCategoryFilter !== "All") {
      const revenueLabel =
        revenueCategoryFilter === "High"
          ? "High Revenue Cases"
          : `${revenueCategoryFilter} Revenue Cases`;

      return {
        label: revenueLabel,
        description:
          revenueCategoryFilter === "High"
            ? "Showing only patients with high or strategic package value."
            : `Showing only patients in the ${revenueCategoryFilter.toLowerCase()} revenue category.`,
      };
    }

    if (deferredTimeFilter !== "All") {
      return {
        label: "Deferred-Time Focus",
        description: `Showing only patients with deferred time marked as ${deferredTimeFilter}.`,
      };
    }

    if (readmissionRiskFilter !== "All") {
      return {
        label: `${readmissionRiskFilter} Readmission Risk`,
        description: `Showing only patients with ${readmissionRiskFilter.toLowerCase()} readmission risk.`,
      };
    }

    if (caseTypeFilter !== "All") {
      return {
        label: `${caseTypeFilter} Cases`,
        description: `Showing only patients classified as ${caseTypeFilter.toLowerCase()} cases.`,
      };
    }

    return null;
  }, [
    admissionFilter,
    bedFilter,
    caseTypeFilter,
    deferredTimeFilter,
    progressionFilter,
    cohortFilter,
    readmissionRiskFilter,
    repeatFilter,
    revenueCategoryFilter,
    riskFilter,
  ]);

  const hasActivePriorityView = Boolean(activePriorityView);

  const filteredPatients = useMemo(() => {
    return patients.filter((patient) => {
      const searchText = `${patient.patientName} ${patient.patientId} ${patient.department} ${patient.doctorName || ""} ${patient.clinical?.diagnosis || ""} ${patient.clinical?.clinicalNotes || ""}`.toLowerCase();
      const matchesSearch = searchText.includes(search.toLowerCase());
      const matchesRisk =
        riskFilter === "All" || patient.risk?.category === riskFilter;
      const matchesAdmission =
        admissionFilter === "All" || patient.admission?.type === admissionFilter;
      const matchesBed = bedFilter === "All" || patient.bed?.type === bedFilter;
      const matchesProgression =
        progressionFilter === "All" ||
        patient.journey?.progressionTrend === progressionFilter;
      const matchesRepeat =
        repeatFilter !== "true" || patient.journey?.repeatVisit === "Yes";
      const matchesDepartment =
        departmentFilter === "All" || patient.department === departmentFilter;
      const matchesCohort =
        cohortFilter === "All" ||
        patient.operational?.clinicalIntelligence?.diseaseCohorts?.includes(
          cohortFilter
        );
      const matchesRevenueCategory =
        revenueCategoryFilter === "All" ||
        (revenueCategoryFilter === "High" &&
          ["High Value", "Strategic Value"].includes(
            patient.operational?.packageIntelligence?.revenueCategory
          )) ||
        patient.operational?.packageIntelligence?.revenueCategory === revenueCategoryFilter;
      const matchesReadmissionRisk =
        readmissionRiskFilter === "All" ||
        patient.operational?.readmissionRisk?.label === readmissionRiskFilter;
      const matchesDeferredTime =
        deferredTimeFilter === "All" ||
        patient.operational?.deferredTime?.label === deferredTimeFilter;
      const matchesCaseType =
        caseTypeFilter === "All" ||
        patient.operational?.caseType?.label === caseTypeFilter;

      return (
        matchesSearch &&
        matchesRisk &&
        matchesAdmission &&
        matchesBed &&
        matchesProgression &&
        matchesRepeat &&
        matchesDepartment &&
        matchesCohort &&
        matchesRevenueCategory &&
        matchesReadmissionRisk &&
        matchesDeferredTime &&
        matchesCaseType
      );
    });
  }, [
    admissionFilter,
    bedFilter,
    caseTypeFilter,
    cohortFilter,
    deferredTimeFilter,
    departmentFilter,
    patients,
    progressionFilter,
    readmissionRiskFilter,
    repeatFilter,
    revenueCategoryFilter,
    riskFilter,
    search,
  ]);

  const sortedPatients = useMemo(
    () =>
      [...filteredPatients].sort(
        (a, b) =>
          (b.risk?.score || 0) - (a.risk?.score || 0) ||
          (b.journey?.visitCount || 0) - (a.journey?.visitCount || 0) ||
          (b.traceability?.evidenceCount || 0) -
          (a.traceability?.evidenceCount || 0)
      ),
    [filteredPatients]
  );

  const priorityQueuePatients = useMemo(() => {
    if (!priorityQueue?.length) {
      return [];
    }

    const patientMap = new Map(
      patients
        .filter((patient) => patient.patientId)
        .map((patient) => [patient.patientId, patient])
    );

    return priorityQueue.map((item) => {
      const patient = patientMap.get(item.patientId) || {};
      return {
        ...patient,
        llmPriorityRank: item.priorityRank,
        llmPriorityScore: item.priorityScore,
        llmPriorityReason: item.reason,
        llmPrioritySuggestedAction: item.suggestedAction,
        llmPriorityValidationStatus: item.validationStatus,
        llmPriorityUsedCache: item.usedCache,
      };
    });
  }, [priorityQueue, patients]);

  const displayPatients = priorityQueueActive ? priorityQueuePatients : sortedPatients;

  const departmentOptions = useMemo(
    () => [
      "All",
      ...new Set(
        patients.map((patient) => patient.department).filter(Boolean)
      ),
    ],
    [patients]
  );
  const summary = useMemo(() => buildDashboardSummary(patients), [patients]);

  const riskData = charts?.riskDistribution || [];
  const admissionData = charts?.admissionDistribution || [];
  const bedData = charts?.bedDistribution || [];
  const cohortData = charts?.cohortDistribution || [];

  const riskOptions = ["All", "Critical", "High", "Medium", "Low"];
  const admissionOptions = ["All", "Emergency", "Urgent", "Elective"];
  const bedOptions = [
    "All",
    ...new Set(patients.map((patient) => patient.bed?.type).filter(Boolean)),
  ];
  const progressionOptions = ["All", "Worsening", "Stable", "Improving"];
  const cohortOptions = useMemo(
    () => [
      "All",
      ...new Set(
        patients
          .map(
            (patient) =>
              patient.operational?.clinicalIntelligence?.primaryCohort
          )
          .filter(Boolean)
      ),
    ],
    [patients]
  );
  const revenueCategoryOptions = useMemo(
    () => [
      "All",
      "High",
      ...new Set(
        patients
          .map((patient) => patient.operational?.packageIntelligence?.revenueCategory)
          .filter(Boolean)
      ),
    ],
    [patients]
  );
  const readmissionRiskOptions = useMemo(
    () => [
      "All",
      ...new Set(
        patients
          .map((patient) => patient.operational?.readmissionRisk?.label)
          .filter(Boolean)
      ),
    ],
    [patients]
  );
  const deferredTimeOptions = useMemo(
    () => [
      "All",
      ...new Set(
        patients
          .map((patient) => patient.operational?.deferredTime?.label)
          .filter(Boolean)
      ),
    ],
    [patients]
  );
  const caseTypeOptions = useMemo(
    () => [
      "All",
      ...new Set(
        patients
          .map((patient) => patient.operational?.caseType?.label)
          .filter(Boolean)
      ),
    ],
    [patients]
  );

  const totalPages = Math.max(
    1,
    Math.ceil(displayPatients.length / rowsPerPage)
  );
  const pageStartIndex = (currentPage - 1) * rowsPerPage;
  const pageEndIndex = pageStartIndex + rowsPerPage;
  const paginatedPatients = displayPatients.slice(pageStartIndex, pageEndIndex);
  const rangeStart = displayPatients.length === 0 ? 0 : pageStartIndex + 1;
  const rangeEnd = Math.min(pageEndIndex, displayPatients.length);

  useEffect(() => {
    setCurrentPage(1);
  }, [
    search,
    riskFilter,
    admissionFilter,
    bedFilter,
    progressionFilter,
    departmentFilter,
    revenueCategoryFilter,
    readmissionRiskFilter,
    deferredTimeFilter,
    caseTypeFilter,
    cohortFilter,
    repeatFilter,
    rowsPerPage,
  ]);

  useEffect(() => {
    if (currentPage > totalPages) {
      setCurrentPage(totalPages);
    }
  }, [currentPage, totalPages]);

  useEffect(() => {
    if (priorityQueueActive) {
      setPriorityQueueActive(false);
      setPriorityQueue([]);
      setPriorityQueueError("");
    }
  }, [filteredPatients]);

  function navigateWithFilters(updates, { clearPriorityFilters = false } = {}) {
    const nextSearchParams = new URLSearchParams(searchParams);

    if (clearPriorityFilters) {
      PRIORITY_FILTER_KEYS.forEach((key) => nextSearchParams.delete(key));
    }

    Object.entries(updates).forEach(([key, value]) => {
      if (!value || value === "All" || value === "false") {
        nextSearchParams.delete(key);
        return;
      }

      nextSearchParams.set(key, value);
    });

    const nextQuery = nextSearchParams.toString();
    navigate(nextQuery ? `/dashboard?${nextQuery}` : "/dashboard");
  }

  function updateFilterParam(key, value) {
    navigateWithFilters({ [key]: value });
  }

  function exportFilteredPatientsCsv() {
    if (displayPatients.length === 0) {
      return;
    }

    const csvContent = buildPatientsCsv(displayPatients);
    const fileSuffix =
      departmentFilter === "All"
        ? "all-departments"
        : departmentFilter.toLowerCase().replace(/[^a-z0-9]+/g, "-");
    const blob = new Blob([`\uFEFF${csvContent}`], {
      type: "text/csv;charset=utf-8;",
    });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement("a");

    link.href = url;
    link.download = `docstribe-patients-${fileSuffix}.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  }

  function clearPriorityView() {
    navigateWithFilters({}, { clearPriorityFilters: true });
    setCurrentPage(1);
  }

  async function runAgenticPriorityQueue() {
    setPriorityQueueError("");
    setPriorityQueueLoading(true);

    try {
      const patientIds = filteredPatients
        .map((patient) => patient.patientId)
        .filter(Boolean);

      if (patientIds.length === 0) {
        setPriorityQueueError("There are no patients available for LLM queue prioritization.");
        setPriorityQueueActive(false);
        setPriorityQueue([]);
        return;
      }

      const result = await getAgenticPriorityQueue({
        limit: 10,
        patientIds,
        useCache: true,
      });

      setPriorityQueue(result.prioritizedPatients || []);
      setPriorityQueueActive(true);
      setCurrentPage(1);
    } catch (error) {
      setPriorityQueueError(error?.message || "LLM priority queue failed. Please try again.");
      setPriorityQueueActive(false);
      setPriorityQueue([]);
    } finally {
      setPriorityQueueLoading(false);
    }
  }

  function handlePriorityViewClick(viewKey) {
    setCurrentPage(1);

    if (viewKey === "all") {
      clearPriorityView();
      return;
    }

    const quickFilterMap = {
      critical: { risk: "Critical" },
      emergency: { admission: "Emergency" },
      icu: { bed: "ICU" },
      repeatVisits: { repeat: "true" },
      worsening: { progression: "Worsening" },
      highRevenue: { revenue: "High" },
      cannotDelay: { deferred: "Cannot be safely delayed" },
      readmissionHigh: { readmission: "High" },
      surgical: { caseType: "Surgical" },
      renalCohort: { cohort: "Renal" },
      oncologyCohort: { cohort: "Oncology" },
      cardiacCohort: { cohort: "Cardiac" },
      neurologyCohort: { cohort: "Neurology" },
      respiratoryCohort: { cohort: "Respiratory" },
    };

    navigateWithFilters(quickFilterMap[viewKey] || {}, {
      clearPriorityFilters: true,
    });

    window.requestAnimationFrame(() => {
      worklistRef.current?.scrollIntoView({
        behavior: "smooth",
        block: "start",
      });
    });
  }

  if (loading) {
    return (
      <LoadingScreen
        title="Loading dashboard..."
        message="Pulling patient queue, risk signals, and operational analytics."
      />
    );
  }

  if (error) {
    return (
      <ErrorState
        title="Dashboard unavailable"
        message={error}
        onRetry={() => setReloadKey((currentValue) => currentValue + 1)}
      />
    );
  }

  if (!patients || patients.length === 0) {
    return (
      <EmptyState
        title="No patients loaded"
        message="The dashboard is connected, but there are no patient records to display yet."
      />
    );
  }

  return (
    <div className="min-h-screen p-6">
      <div className="mb-6 flex flex-col justify-between gap-4 lg:flex-row lg:items-end">
        <div>
          <h1 className="text-4xl font-bold tracking-tight text-slate-900">
            Admission Intelligence Dashboard
          </h1>
          <p className="mt-2 max-w-3xl text-slate-600">
            AI-powered patient prioritization, admission planning, clinical
            risk visibility and operational workflow intelligence.
          </p>
        </div>

        <div className="rounded-xl border border-green-200 bg-green-50 px-4 py-3 text-sm font-medium text-green-700">
          <div className="flex items-center gap-2">
            <ShieldCheck className="h-4 w-4" />
            {summary?.validatedPatients ?? patients.length} profiles validated
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-5">
        <StatCard
          title="Total Patients"
          value={summary?.totalPatients ?? patients.length}
          icon={Users}
          isActive={!hasActivePriorityView}
          onClick={() => handlePriorityViewClick("all")}
        />
        <StatCard
          title="Critical Patients"
          value={summary?.criticalPatients ?? 0}
          icon={AlertTriangle}
          tone="red"
          isActive={riskFilter === "Critical"}
          onClick={() => handlePriorityViewClick("critical")}
        />
        <StatCard
          title="Emergency Admissions"
          value={summary?.emergencyPatients ?? 0}
          icon={Activity}
          tone="orange"
          isActive={admissionFilter === "Emergency"}
          onClick={() => handlePriorityViewClick("emergency")}
        />
        <StatCard
          title="ICU Required"
          value={summary?.icuPatients ?? 0}
          icon={Bed}
          tone="blue"
          isActive={bedFilter === "ICU"}
          onClick={() => handlePriorityViewClick("icu")}
        />
        <StatCard
          title="Repeat Visits"
          value={summary?.repeatPatients ?? 0}
          icon={Repeat}
          tone="green"
          isActive={repeatFilter === "true"}
          onClick={() => handlePriorityViewClick("repeatVisits")}
        />
        <StatCard
          title="Worsening Patients"
          value={summary?.worseningPatients ?? 0}
          icon={TrendingDown}
          tone="red"
          isActive={progressionFilter === "Worsening"}
          onClick={() => handlePriorityViewClick("worsening")}
        />
        <StatCard
          title="High Revenue Cases"
          value={summary?.highRevenueCases ?? 0}
          icon={IndianRupee}
          tone="orange"
          isActive={revenueCategoryFilter === "High"}
          onClick={() => handlePriorityViewClick("highRevenue")}
        />
        <StatCard
          title="Cannot Be Delayed"
          value={summary?.cannotBeDelayedCases ?? 0}
          icon={TimerReset}
          tone="red"
          isActive={deferredTimeFilter === "Cannot be safely delayed"}
          onClick={() => handlePriorityViewClick("cannotDelay")}
        />
        <StatCard
          title="High Readmission Risk"
          value={summary?.highReadmissionRiskCases ?? 0}
          icon={Repeat}
          tone="blue"
          isActive={readmissionRiskFilter === "High"}
          onClick={() => handlePriorityViewClick("readmissionHigh")}
        />
        <StatCard
          title="Surgical Opportunities"
          value={summary?.surgicalOpportunities ?? 0}
          icon={Stethoscope}
          tone="green"
          isActive={caseTypeFilter === "Surgical"}
          onClick={() => handlePriorityViewClick("surgical")}
        />
      </div>

      <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-2">
        <PortfolioCard
          title="Total Addressable Revenue"
          value={formatLakhs(summary?.totalAddressableRevenueLakhs)}
          caption="Midpoint estimate across the currently loaded patient portfolio."
          tone="orange"
        />
        <PortfolioCard
          title="Revenue At Risk"
          value={formatLakhs(summary?.revenueAtRiskLakhs)}
          caption="High-value cases with high no-show risk that may need tighter follow-up."
          tone="blue"
        />
      </div>

      <div className="mt-6 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="mb-4">
          <h2 className="text-lg font-semibold text-slate-900">Disease Cohorts</h2>
          <p className="mt-1 text-sm text-slate-500">
            Quick operational slices for the major specialty groups highlighted in the assignment brief.
          </p>
        </div>

        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          <StatCard
            title="Renal Cohort"
            value={summary?.renalCohortPatients ?? 0}
            icon={Stethoscope}
            tone="blue"
            isActive={cohortFilter === "Renal"}
            onClick={() => handlePriorityViewClick("renalCohort")}
          />
          <StatCard
            title="Oncology Cohort"
            value={summary?.oncologyCohortPatients ?? 0}
            icon={Brain}
            tone="orange"
            isActive={cohortFilter === "Oncology"}
            onClick={() => handlePriorityViewClick("oncologyCohort")}
          />
          <StatCard
            title="Cardiac Cohort"
            value={summary?.cardiacCohortPatients ?? 0}
            icon={HeartPulse}
            tone="red"
            isActive={cohortFilter === "Cardiac"}
            onClick={() => handlePriorityViewClick("cardiacCohort")}
          />
        </div>
      </div>

      {hasActivePriorityView && (
        <div className="mt-4 flex flex-col gap-3 rounded-2xl border border-blue-200 bg-blue-50 px-5 py-4 text-blue-900 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-blue-700">
              Priority view active
            </p>
            <h2 className="mt-1 text-lg font-semibold">
              {activePriorityView.label}
            </h2>
            <p className="mt-1 text-sm text-blue-800">
              {activePriorityView.description} {displayPatients.length} matching
              patients are currently in view after the active filters.
            </p>
          </div>

          <button
            type="button"
            onClick={clearPriorityView}
            className="inline-flex items-center justify-center rounded-xl border border-blue-200 bg-white px-3 py-2 text-sm font-semibold text-blue-700 hover:border-blue-300 hover:text-blue-900"
          >
            Clear priority view
          </button>
        </div>
      )}

      <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-2 2xl:grid-cols-4">
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="mb-4 text-lg font-semibold text-slate-900">
            Risk Distribution
          </h2>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={riskData}>
              <defs>
                <linearGradient id="riskGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#ef4444" stopOpacity={0.95} />
                  <stop offset="95%" stopColor="#f97316" stopOpacity={0.65} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis allowDecimals={false} />
              <Tooltip content={<InlineTooltip />} />
              <Bar dataKey="value" fill="url(#riskGradient)" radius={[10, 10, 0, 0]} animationDuration={900}>
                {riskData.map((entry) => (
                  <Cell key={entry.name} fill={COLORS[entry.name] || "#334155"} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="mb-4 text-lg font-semibold text-slate-900">
            Admission Type
          </h2>
          <ResponsiveContainer width="100%" height={260}>
            <PieChart>
              <defs>
                <linearGradient id="admissionGradient" x1="0" y1="0" x2="1" y2="1">
                  <stop offset="5%" stopColor="#f97316" stopOpacity={0.95} />
                  <stop offset="95%" stopColor="#2563eb" stopOpacity={0.7} />
                </linearGradient>
              </defs>
              <Pie
                data={admissionData}
                dataKey="value"
                nameKey="name"
                outerRadius={95}
                label
                animationDuration={900}
              >
                {admissionData.map((entry) => (
                  <Cell key={entry.name} fill={COLORS[entry.name] || "#334155"} />
                ))}
              </Pie>
              <Tooltip content={<InlineTooltip />} />
            </PieChart>
          </ResponsiveContainer>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="mb-4 text-lg font-semibold text-slate-900">
            Bed Allocation
          </h2>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={bedData}>
              <defs>
                <linearGradient id="bedGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#2563eb" stopOpacity={0.95} />
                  <stop offset="100%" stopColor="#7c3aed" stopOpacity={0.65} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" hide />
              <YAxis allowDecimals={false} />
              <Tooltip content={<InlineTooltip />} />
              <Bar dataKey="value" fill="url(#bedGradient)" radius={[10, 10, 0, 0]} animationDuration={900}>
                {bedData.map((entry) => (
                  <Cell key={entry.name} fill={COLORS[entry.name] || "#334155"} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="mb-4 text-lg font-semibold text-slate-900">
            Disease Cohort Mix
          </h2>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={cohortData}>
              <defs>
                <linearGradient id="cohortGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#0f172a" stopOpacity={0.95} />
                  <stop offset="100%" stopColor="#14b8a6" stopOpacity={0.7} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis allowDecimals={false} />
              <Tooltip content={<InlineTooltip />} />
              <Bar dataKey="value" fill="url(#cohortGradient)" radius={[10, 10, 0, 0]} animationDuration={900} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="mt-6 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="mb-4 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">
              Filters & Search
            </h2>
            <p className="mt-1 text-sm text-slate-500">
              Narrow the worklist by clinical risk, admission pathway, bed type,
              business value, continuity risk, deferral tolerance, or case type.
            </p>
          </div>

          {departmentFilter !== "All" && (
            <div className="flex items-center gap-2 rounded-full border border-blue-200 bg-blue-50 px-3 py-2 text-sm font-medium text-blue-700">
              <span>Department: {departmentFilter}</span>
              <button
                type="button"
                onClick={() => updateFilterParam("department", "All")}
                className="rounded-full p-1 hover:bg-blue-100"
                aria-label="Clear department filter"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          )}
        </div>

        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-6">
          <label className="block">
            <span className="mb-2 block text-xs font-semibold uppercase tracking-wide text-slate-500">
              Search by Patient ID / Doctor / Diagnosis
            </span>
            <div className="relative">
              <Search className="absolute left-3 top-3 h-4 w-4 text-slate-400" />
              <input
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Search patient ID, doctor, diagnosis..."
                className="w-full rounded-xl border border-slate-200 py-2 pl-9 pr-3 text-sm outline-none focus:border-slate-400"
              />
            </div>
          </label>

          <label className="block">
            <span className="mb-2 block text-xs font-semibold uppercase tracking-wide text-slate-500">
              Risk Filter
            </span>
            <select
              value={riskFilter}
              onChange={(event) => updateFilterParam("risk", event.target.value)}
              className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm outline-none"
            >
              {riskOptions.map((option) => (
                <option key={option}>{option}</option>
              ))}
            </select>
          </label>

          <label className="block">
            <span className="mb-2 block text-xs font-semibold uppercase tracking-wide text-slate-500">
              Admission Type Filter
            </span>
            <select
              value={admissionFilter}
              onChange={(event) =>
                updateFilterParam("admission", event.target.value)
              }
              className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm outline-none"
            >
              {admissionOptions.map((option) => (
                <option key={option}>{option}</option>
              ))}
            </select>
          </label>

          <label className="block">
            <span className="mb-2 block text-xs font-semibold uppercase tracking-wide text-slate-500">
              Bed Filter
            </span>
            <select
              value={bedFilter}
              onChange={(event) => updateFilterParam("bed", event.target.value)}
              className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm outline-none"
            >
              {bedOptions.map((option) => (
                <option key={option}>{option}</option>
              ))}
            </select>
          </label>

          <label className="block">
            <span className="mb-2 block text-xs font-semibold uppercase tracking-wide text-slate-500">
              Progression Filter
            </span>
            <select
              value={progressionFilter}
              onChange={(event) =>
                updateFilterParam("progression", event.target.value)
              }
              className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm outline-none"
            >
              {progressionOptions.map((option) => (
                <option key={option}>{option}</option>
              ))}
            </select>
          </label>

          <label className="block">
            <span className="mb-2 block text-xs font-semibold uppercase tracking-wide text-slate-500">
              Department Filter
            </span>
            <select
              value={departmentFilter}
              onChange={(event) =>
                updateFilterParam("department", event.target.value)
              }
              className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm outline-none"
            >
              {departmentOptions.map((option) => (
                <option key={option}>{option}</option>
              ))}
            </select>
          </label>

          <label className="block">
            <span className="mb-2 block text-xs font-semibold uppercase tracking-wide text-slate-500">
              Revenue Category Filter
            </span>
            <select
              value={revenueCategoryFilter}
              onChange={(event) =>
                updateFilterParam("revenue", event.target.value)
              }
              className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm outline-none"
            >
              {revenueCategoryOptions.map((option) => (
                <option key={option} value={option}>
                  {option === "High" ? "High / Strategic" : option}
                </option>
              ))}
            </select>
          </label>

          <label className="block">
            <span className="mb-2 block text-xs font-semibold uppercase tracking-wide text-slate-500">
              Disease Cohort
            </span>
            <select
              value={cohortFilter}
              onChange={(event) => updateFilterParam("cohort", event.target.value)}
              className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm outline-none"
            >
              {cohortOptions.map((option) => (
                <option key={option}>{option}</option>
              ))}
            </select>
          </label>

          <label className="block">
            <span className="mb-2 block text-xs font-semibold uppercase tracking-wide text-slate-500">
              Readmission Risk Filter
            </span>
            <select
              value={readmissionRiskFilter}
              onChange={(event) =>
                updateFilterParam("readmission", event.target.value)
              }
              className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm outline-none"
            >
              {readmissionRiskOptions.map((option) => (
                <option key={option}>{option}</option>
              ))}
            </select>
          </label>

          <label className="block">
            <span className="mb-2 block text-xs font-semibold uppercase tracking-wide text-slate-500">
              Deferred Time Filter
            </span>
            <select
              value={deferredTimeFilter}
              onChange={(event) =>
                updateFilterParam("deferred", event.target.value)
              }
              className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm outline-none"
            >
              {deferredTimeOptions.map((option) => (
                <option key={option}>{option}</option>
              ))}
            </select>
          </label>

          <label className="block">
            <span className="mb-2 block text-xs font-semibold uppercase tracking-wide text-slate-500">
              Case Type Filter
            </span>
            <select
              value={caseTypeFilter}
              onChange={(event) =>
                updateFilterParam("caseType", event.target.value)
              }
              className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm outline-none"
            >
              {caseTypeOptions.map((option) => (
                <option key={option}>{option}</option>
              ))}
            </select>
          </label>
        </div>
      </div>

      <div
        ref={worklistRef}
        className="mt-6 rounded-2xl border border-slate-200 bg-white shadow-sm"
      >
        <div className="flex flex-col gap-4 border-b border-slate-200 p-5 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h2 className="text-xl font-semibold text-slate-900">
              AI-Prioritized Patient Worklist
            </h2>
            <p className="text-sm text-slate-500">
              Showing {rangeStart}-{rangeEnd} of {displayPatients.length} matching
              patients
              {hasActivePriorityView
                ? ` in ${activePriorityView.label}.`
                : "."}
            </p>
            {priorityQueueActive && (
              <p className="mt-1 text-sm text-blue-700">
                Showing the top {priorityQueue.length} cases ranked by LLM review.
              </p>
            )}
          </div>

          <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
            <button
              type="button"
              onClick={runAgenticPriorityQueue}
              disabled={priorityQueueLoading || filteredPatients.length === 0}
              className="inline-flex items-center justify-center gap-2 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm font-semibold text-slate-700 hover:border-slate-300 hover:bg-slate-100 hover:text-slate-900 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <Brain className="h-4 w-4" />
              {priorityQueueLoading ? "Running LLM queue…" : "Run LLM priority queue"}
            </button>
            {priorityQueueActive && (
              <button
                type="button"
                onClick={() => {
                  setPriorityQueueActive(false);
                  setPriorityQueue([]);
                  setPriorityQueueError("");
                  setCurrentPage(1);
                }}
                className="inline-flex items-center justify-center gap-2 rounded-xl border border-blue-200 bg-white px-3 py-2 text-sm font-semibold text-blue-700 hover:border-blue-300 hover:text-blue-900"
              >
                Clear LLM queue
              </button>
            )}
            <button
              type="button"
              onClick={exportFilteredPatientsCsv}
              disabled={displayPatients.length === 0}
              className="inline-flex items-center justify-center gap-2 rounded-xl border border-slate-200 px-3 py-2 text-sm font-semibold text-slate-700 hover:border-slate-300 hover:text-slate-900 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <Download className="h-4 w-4" />
              Export CSV
            </button>
            <label className="flex items-center gap-2 text-sm text-slate-600">
              <span>Rows per page</span>
              <select
                value={rowsPerPage}
                onChange={(event) => setRowsPerPage(Number(event.target.value))}
                className="rounded-xl border border-slate-200 px-3 py-2 text-sm outline-none"
              >
                {PAGE_SIZE_OPTIONS.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
            </label>

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setCurrentPage((page) => Math.max(1, page - 1))}
                disabled={currentPage === 1}
                className="inline-flex items-center gap-1 rounded-xl border border-slate-200 px-3 py-2 text-sm font-semibold text-slate-700 hover:border-slate-300 hover:text-slate-900 disabled:cursor-not-allowed disabled:opacity-50"
              >
                <ChevronLeft className="h-4 w-4" />
                Previous
              </button>
              <span className="text-sm text-slate-500">
                Page {currentPage} of {totalPages}
              </span>
              <button
                type="button"
                onClick={() =>
                  setCurrentPage((page) => Math.min(totalPages, page + 1))
                }
                disabled={currentPage === totalPages}
                className="inline-flex items-center gap-1 rounded-xl border border-slate-200 px-3 py-2 text-sm font-semibold text-slate-700 hover:border-slate-300 hover:text-slate-900 disabled:cursor-not-allowed disabled:opacity-50"
              >
                Next
                <ChevronRight className="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>

        {priorityQueueError ? (
          <div className="mx-5 mb-4 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {priorityQueueError}
          </div>
        ) : null}

        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 text-slate-600">
              <tr>
                <th className="p-4">Patient</th>
                <th className="p-4">Doctor</th>
                <th className="p-4">Department</th>
                {priorityQueueActive && <th className="p-4">LLM Rank</th>}
                <th className="p-4">Case Type</th>
                <th className="p-4">Risk</th>
                <th className="p-4">Admission</th>
                <th className="p-4">Bed</th>
                <th className="p-4">Revenue</th>
                <th className="p-4">Deferred Time</th>
                <th className="p-4">Readmission Risk</th>
                <th className="p-4">Progression</th>
                <th className="p-4">AI Action</th>
                <th className="p-4">Evidence</th>
                <th className="p-4">Open</th>
              </tr>
            </thead>
            <tbody>
              {paginatedPatients.map((patient) => (
                <tr
                  key={patient.patientId}
                  className={`border-l-4 border-t border-slate-100 hover:bg-slate-50 ${getRowAccentClass(
                    patient.risk?.category
                  )}`}
                >
                  <td className="p-4">
                    <Link
                      to={`/patient/${encodeURIComponent(patient.patientId)}`}
                      className="font-semibold text-blue-600 hover:underline"
                    >
                      {patient.patientName}
                    </Link>
                    <p className="text-xs text-slate-500">{patient.patientId}</p>
                    <div className="mt-2 flex flex-wrap gap-2">
                      {patient.operational?.clinicalIntelligence?.primaryIcd10 && (
                        <span className="rounded-full bg-slate-100 px-2 py-1 text-[11px] font-semibold text-slate-700">
                          {patient.operational.clinicalIntelligence.primaryIcd10.code}
                        </span>
                      )}
                      {patient.operational?.clinicalIntelligence?.primaryCohort && (
                        <span className="rounded-full bg-blue-50 px-2 py-1 text-[11px] font-semibold text-blue-700">
                          {patient.operational.clinicalIntelligence.primaryCohort}
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="max-w-[220px] p-4 text-slate-700">
                    {patient.doctorName || "Not assigned"}
                  </td>
                  <td className="max-w-[220px] p-4 text-slate-700">
                    {patient.department}
                  </td>
                  {priorityQueueActive && (
                    <td className="p-4 text-slate-700">
                      <p className="font-semibold text-slate-800">
                        {patient.llmPriorityRank != null ? `#${patient.llmPriorityRank}` : "—"}
                      </p>
                      <p className="mt-1 text-xs text-slate-500">
                        {patient.llmPriorityScore != null
                          ? `Score ${patient.llmPriorityScore}`
                          : "Score unavailable"}
                      </p>
                    </td>
                  )}
                  <td className="p-4 text-slate-700">
                    <p className="font-medium text-slate-800">
                      {patient.operational?.caseType?.label || "Not classified"}
                    </p>
                    <p className="mt-1 text-xs text-slate-500">
                      LOS {patient.operational?.lengthOfStay?.label || "TBD"}
                    </p>
                  </td>
                  <td className="p-4">
                    <RiskBadge risk={patient.risk?.category} />
                    <RiskScoreBar
                      score={patient.risk?.score}
                      risk={patient.risk?.category}
                    />
                  </td>
                  <td className="p-4">
                    <AdmissionBadge type={patient.admission?.type} />
                    <p className="mt-2 text-xs text-slate-500">
                      Conversion{" "}
                      {patient.operational?.admissionConversionProbability
                        ?.percentage || 0}
                      %
                    </p>
                  </td>
                  <td className="p-4 text-slate-700">{patient.bed?.type}</td>
                  <td className="p-4 text-slate-700">
                    <p className="font-medium text-slate-800">
                      {patient.operational?.packageIntelligence
                        ?.expectedRevenue || "Not estimated"}
                    </p>
                    <p className="mt-1 text-xs text-slate-500">
                      {patient.operational?.packageIntelligence
                        ?.revenueCategory || "Category pending"}
                    </p>
                  </td>
                  <td className="p-4 text-slate-700">
                    {patient.operational?.deferredTime?.label || "Needs review"}
                  </td>
                  <td className="p-4 text-slate-700">
                    <p className="font-medium text-slate-800">
                      {patient.operational?.readmissionRisk?.label || "Unknown"}
                    </p>
                    <p className="mt-1 text-xs text-slate-500">
                      No-show {patient.operational?.noShowRisk?.label || "Unknown"}
                    </p>
                  </td>
                  <td className="p-4 text-slate-700">
                    <ProgressionIndicator
                      trend={patient.journey?.progressionTrend}
                    />
                    <p className="mt-2 text-xs text-slate-500">
                      {patient.journey?.visitCount || 1} visit
                      {Number(patient.journey?.visitCount || 1) === 1 ? "" : "s"}
                    </p>
                  </td>
                  <td className="p-4 font-medium text-slate-800">
                    {getRecommendedAction(patient)}
                    <div className="mt-2 flex flex-wrap gap-2">
                      {patient.operational?.clinicalIntelligence?.possibleSymptoms
                        ?.slice(0, 2)
                        .map((item) => (
                          <span
                            key={`${patient.patientId}-${item.label}`}
                            className="rounded-full bg-slate-100 px-2 py-1 text-[11px] font-semibold text-slate-700"
                          >
                            {item.label}
                          </span>
                        ))}
                    </div>
                  </td>
                  <td className="p-4 text-slate-700">
                    {patient.traceability?.evidenceCount}
                  </td>
                  <td className="p-4">
                    <Link
                      to={`/patient/${encodeURIComponent(patient.patientId)}`}
                      className="rounded-lg bg-slate-900 px-3 py-2 text-xs font-semibold text-white hover:bg-slate-700"
                    >
                      View Profile
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {paginatedPatients.length === 0 && (
            <div className="p-6">
              <EmptyState
                compact
                title="No matching patients"
                message="Try adjusting the active filters or clear the department drill-down to widen the worklist."
              />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
