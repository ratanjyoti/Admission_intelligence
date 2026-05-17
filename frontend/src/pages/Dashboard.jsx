import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import {
  Activity,
  AlertTriangle,
  Bed,
  ChevronLeft,
  ChevronRight,
  Download,
  Repeat,
  Search,
  ShieldCheck,
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
import { getDashboardCharts, getDashboardSummary, getPatients } from "../lib/api";

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

function StatCard({ title, value, icon: Icon, tone = "slate" }) {
  const tones = {
    slate: "bg-slate-100 text-slate-700",
    red: "bg-red-100 text-red-700",
    orange: "bg-orange-100 text-orange-700",
    blue: "bg-blue-100 text-blue-700",
    green: "bg-green-100 text-green-700",
  };

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-slate-500">{title}</p>
          <h2 className="mt-3 text-3xl font-bold text-slate-900">{value}</h2>
        </div>
        <div className={`rounded-xl p-3 ${tones[tone]}`}>
          <Icon className="h-6 w-6" />
        </div>
      </div>
    </div>
  );
}

function RiskBadge({ risk }) {
  const styles = {
    Critical: "border-red-200 bg-red-100 text-red-700",
    High: "border-orange-200 bg-orange-100 text-orange-700",
    Medium: "border-yellow-200 bg-yellow-100 text-yellow-700",
    Low: "border-green-200 bg-green-100 text-green-700",
  };

  return (
    <span
      className={`rounded-full border px-3 py-1 text-xs font-semibold ${
        styles[risk] || "border-slate-200 bg-slate-100 text-slate-700"
      }`}
    >
      {risk}
    </span>
  );
}

function AdmissionBadge({ type }) {
  const styles = {
    Emergency: "border-red-200 bg-red-50 text-red-700",
    Urgent: "border-orange-200 bg-orange-50 text-orange-700",
    Elective: "border-blue-200 bg-blue-50 text-blue-700",
  };

  return (
    <span
      className={`rounded-full border px-3 py-1 text-xs font-semibold ${
        styles[type] || "border-slate-200 bg-slate-100 text-slate-700"
      }`}
    >
      {type}
    </span>
  );
}

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
    "Risk Category",
    "Risk Score",
    "Admission Type",
    "Bed Allocation",
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
    patient.risk?.category,
    patient.risk?.score,
    patient.admission?.type,
    patient.bed?.type,
    patient.journey?.progressionTrend,
    patient.traceability?.evidenceCount,
    getRecommendedAction(patient),
  ]);

  return [headers, ...rows]
    .map((row) => row.map((value) => escapeCsvValue(value)).join(","))
    .join("\n");
}

export default function Dashboard() {
  const [searchParams, setSearchParams] = useSearchParams();
  const departmentFilter = searchParams.get("department") || "All";

  const [patients, setPatients] = useState([]);
  const [summary, setSummary] = useState(null);
  const [charts, setCharts] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [riskFilter, setRiskFilter] = useState("All");
  const [admissionFilter, setAdmissionFilter] = useState("All");
  const [bedFilter, setBedFilter] = useState("All");
  const [currentPage, setCurrentPage] = useState(1);
  const [rowsPerPage, setRowsPerPage] = useState(25);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let isActive = true;

    async function loadDashboard() {
      setLoading(true);
      setError("");

      try {
        const [patientsData, summaryData, chartsData] = await Promise.all([
          getPatients(),
          getDashboardSummary(),
          getDashboardCharts(),
        ]);

        if (!isActive) {
          return;
        }

        setPatients(patientsData || []);
        setSummary(summaryData);
        setCharts(chartsData);
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

  const filteredPatients = useMemo(() => {
    return patients.filter((patient) => {
      const searchText = `${patient.patientName} ${patient.patientId} ${patient.department} ${patient.doctorName || ""} ${patient.clinical?.diagnosis || ""} ${patient.clinical?.clinicalNotes || ""}`.toLowerCase();
      const matchesSearch = searchText.includes(search.toLowerCase());
      const matchesRisk =
        riskFilter === "All" || patient.risk?.category === riskFilter;
      const matchesAdmission =
        admissionFilter === "All" || patient.admission?.type === admissionFilter;
      const matchesBed = bedFilter === "All" || patient.bed?.type === bedFilter;
      const matchesDepartment =
        departmentFilter === "All" || patient.department === departmentFilter;

      return (
        matchesSearch &&
        matchesRisk &&
        matchesAdmission &&
        matchesBed &&
        matchesDepartment
      );
    });
  }, [
    admissionFilter,
    bedFilter,
    departmentFilter,
    patients,
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

  const departmentOptions = useMemo(
    () => [
      "All",
      ...new Set(
        patients.map((patient) => patient.department).filter(Boolean)
      ),
    ],
    [patients]
  );

  const riskData = charts?.riskDistribution || [];
  const admissionData = charts?.admissionDistribution || [];
  const bedData = charts?.bedDistribution || [];

  const riskOptions = ["All", "Critical", "High", "Medium", "Low"];
  const admissionOptions = ["All", "Emergency", "Urgent", "Elective"];
  const bedOptions = [
    "All",
    ...new Set(patients.map((patient) => patient.bed?.type).filter(Boolean)),
  ];

  const totalPages = Math.max(
    1,
    Math.ceil(sortedPatients.length / rowsPerPage)
  );
  const pageStartIndex = (currentPage - 1) * rowsPerPage;
  const pageEndIndex = pageStartIndex + rowsPerPage;
  const paginatedPatients = sortedPatients.slice(pageStartIndex, pageEndIndex);
  const rangeStart = sortedPatients.length === 0 ? 0 : pageStartIndex + 1;
  const rangeEnd = Math.min(pageEndIndex, sortedPatients.length);

  useEffect(() => {
    setCurrentPage(1);
  }, [search, riskFilter, admissionFilter, bedFilter, departmentFilter, rowsPerPage]);

  useEffect(() => {
    if (currentPage > totalPages) {
      setCurrentPage(totalPages);
    }
  }, [currentPage, totalPages]);

  function updateDepartmentFilter(value) {
    const nextSearchParams = new URLSearchParams(searchParams);

    if (value === "All") {
      nextSearchParams.delete("department");
    } else {
      nextSearchParams.set("department", value);
    }

    setSearchParams(nextSearchParams);
  }

  function exportFilteredPatientsCsv() {
    if (sortedPatients.length === 0) {
      return;
    }

    const csvContent = buildPatientsCsv(sortedPatients);
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

      <div className="grid grid-cols-1 gap-4 md:grid-cols-5">
        <StatCard
          title="Total Patients"
          value={summary?.totalPatients ?? patients.length}
          icon={Users}
        />
        <StatCard
          title="Critical Patients"
          value={summary?.criticalPatients ?? 0}
          icon={AlertTriangle}
          tone="red"
        />
        <StatCard
          title="Emergency Admissions"
          value={summary?.emergencyPatients ?? 0}
          icon={Activity}
          tone="orange"
        />
        <StatCard
          title="ICU Required"
          value={summary?.icuPatients ?? 0}
          icon={Bed}
          tone="blue"
        />
        <StatCard
          title="Repeat Visits"
          value={summary?.repeatPatients ?? 0}
          icon={Repeat}
          tone="green"
        />
      </div>

      <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="mb-4 text-lg font-semibold text-slate-900">
            Risk Distribution
          </h2>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={riskData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis allowDecimals={false} />
              <Tooltip />
              <Bar dataKey="value">
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
              <Pie
                data={admissionData}
                dataKey="value"
                nameKey="name"
                outerRadius={95}
                label
              >
                {admissionData.map((entry) => (
                  <Cell key={entry.name} fill={COLORS[entry.name] || "#334155"} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="mb-4 text-lg font-semibold text-slate-900">
            Bed Allocation
          </h2>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={bedData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" hide />
              <YAxis allowDecimals={false} />
              <Tooltip />
              <Bar dataKey="value">
                {bedData.map((entry) => (
                  <Cell key={entry.name} fill={COLORS[entry.name] || "#334155"} />
                ))}
              </Bar>
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
              or department.
            </p>
          </div>

          {departmentFilter !== "All" && (
            <div className="flex items-center gap-2 rounded-full border border-blue-200 bg-blue-50 px-3 py-2 text-sm font-medium text-blue-700">
              <span>Department: {departmentFilter}</span>
              <button
                type="button"
                onClick={() => updateDepartmentFilter("All")}
                className="rounded-full p-1 hover:bg-blue-100"
                aria-label="Clear department filter"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          )}
        </div>

        <div className="grid grid-cols-1 gap-4 lg:grid-cols-5">
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
              onChange={(event) => setRiskFilter(event.target.value)}
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
              onChange={(event) => setAdmissionFilter(event.target.value)}
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
              onChange={(event) => setBedFilter(event.target.value)}
              className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm outline-none"
            >
              {bedOptions.map((option) => (
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
              onChange={(event) => updateDepartmentFilter(event.target.value)}
              className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm outline-none"
            >
              {departmentOptions.map((option) => (
                <option key={option}>{option}</option>
              ))}
            </select>
          </label>
        </div>
      </div>

      <div className="mt-6 rounded-2xl border border-slate-200 bg-white shadow-sm">
        <div className="flex flex-col gap-4 border-b border-slate-200 p-5 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h2 className="text-xl font-semibold text-slate-900">
              AI-Prioritized Patient Worklist
            </h2>
            <p className="text-sm text-slate-500">
              Showing {rangeStart}-{rangeEnd} of {sortedPatients.length} matching
              patients.
            </p>
          </div>

          <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
            <button
              type="button"
              onClick={exportFilteredPatientsCsv}
              disabled={sortedPatients.length === 0}
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

        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 text-slate-600">
              <tr>
                <th className="p-4">Patient</th>
                <th className="p-4">Department</th>
                <th className="p-4">Risk</th>
                <th className="p-4">Admission</th>
                <th className="p-4">Bed</th>
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
                  className="border-t border-slate-100 hover:bg-slate-50"
                >
                  <td className="p-4">
                    <Link
                      to={`/patient/${encodeURIComponent(patient.patientId)}`}
                      className="font-semibold text-blue-600 hover:underline"
                    >
                      {patient.patientName}
                    </Link>
                    <p className="text-xs text-slate-500">{patient.patientId}</p>
                  </td>
                  <td className="max-w-[220px] p-4 text-slate-700">
                    {patient.department}
                  </td>
                  <td className="p-4">
                    <RiskBadge risk={patient.risk?.category} />
                    <p className="mt-1 text-xs text-slate-500">
                      Score {patient.risk?.score}/10
                    </p>
                  </td>
                  <td className="p-4">
                    <AdmissionBadge type={patient.admission?.type} />
                  </td>
                  <td className="p-4 text-slate-700">{patient.bed?.type}</td>
                  <td className="p-4 text-slate-700">
                    {patient.journey?.progressionTrend}
                  </td>
                  <td className="p-4 font-medium text-slate-800">
                    {getRecommendedAction(patient)}
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
