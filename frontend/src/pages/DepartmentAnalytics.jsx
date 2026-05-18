import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ArrowLeft, BedDouble, Building2, Siren, Stethoscope } from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import EmptyState from "../components/EmptyState";
import ErrorState from "../components/ErrorState";
import LoadingScreen from "../components/LoadingScreen";
import { getDashboardCharts, getDashboardSummary } from "../lib/api";

function SummaryCard({ title, value, icon: Icon, tone, onClick }) {
  const className = `metric-card rounded-2xl border border-slate-200 bg-white p-5 text-left shadow-sm ${
    onClick ? "clickable" : ""
  }`;

  const content = (
    <>
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-slate-500">{title}</p>
          <h2 className="mt-3 text-2xl font-bold text-slate-900">{value}</h2>
        </div>
        <div className={`rounded-xl p-3 ${tone}`}>
          <Icon className="h-6 w-6" />
        </div>
      </div>
    </>
  );

  if (onClick) {
    return (
      <button type="button" onClick={onClick} className={className}>
        {content}
      </button>
    );
  }

  return <div className={className}>{content}</div>;
}

function AnalyticsTooltip({ active, payload, label }) {
  if (!active || !payload?.length) {
    return null;
  }

  return (
    <div className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm shadow-lg">
      <p className="font-semibold text-slate-900">{label}</p>
      {payload.map((entry) => (
        <p key={`${entry.dataKey}-${entry.name}`} className="mt-1 text-slate-600">
          {entry.name || entry.dataKey}: {entry.value}
        </p>
      ))}
    </div>
  );
}

function DepartmentMetricChart({ title, description, data, dataKey, color }) {
  const topDepartments = useMemo(
    () =>
      [...data]
        .sort(
          (a, b) =>
            b[dataKey] - a[dataKey] || a.department.localeCompare(b.department)
        )
        .slice(0, 12),
    [data, dataKey]
  );

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="mb-4">
        <h2 className="text-lg font-semibold text-slate-900">{title}</h2>
        <p className="mt-1 text-sm text-slate-500">{description}</p>
      </div>

      <div className="h-[420px]">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={topDepartments}
            layout="vertical"
            margin={{ top: 8, right: 24, left: 8, bottom: 8 }}
          >
            <defs>
              <linearGradient id={`gradient-${dataKey}`} x1="0" y1="0" x2="1" y2="0">
                <stop offset="0%" stopColor={color} stopOpacity={0.95} />
                <stop offset="100%" stopColor={color} stopOpacity={0.55} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis type="number" allowDecimals={false} />
            <YAxis
              type="category"
              dataKey="department"
              width={180}
              tick={{ fontSize: 12 }}
            />
            <Tooltip content={<AnalyticsTooltip />} />
            <Bar
              dataKey={dataKey}
              fill={`url(#gradient-${dataKey})`}
              radius={[0, 10, 10, 0]}
              animationDuration={900}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

export default function DepartmentAnalytics() {
  const navigate = useNavigate();
  const [summary, setSummary] = useState(null);
  const [departmentMetrics, setDepartmentMetrics] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let isActive = true;

    async function loadAnalytics() {
      setLoading(true);
      setError("");

      try {
        const [summaryData, chartsData] = await Promise.all([
          getDashboardSummary(),
          getDashboardCharts(),
        ]);

        if (!isActive) {
          return;
        }

        setSummary(summaryData);
        setDepartmentMetrics(chartsData.departmentMetrics || []);
      } catch (loadError) {
        if (!isActive) {
          return;
        }

        setError(loadError.message || "Unable to load analytics.");
      } finally {
        if (isActive) {
          setLoading(false);
        }
      }
    }

    loadAnalytics();

    return () => {
      isActive = false;
    };
  }, [reloadKey]);

  const departmentsWithCriticalPatients = departmentMetrics.filter(
    (department) => department.criticalPatients > 0
  ).length;

  const peakIcuDemand = departmentMetrics.reduce(
    (currentMax, department) =>
      department.icuDemand > currentMax.icuDemand ? department : currentMax,
    { department: "None", icuDemand: 0 }
  );

  const peakEmergencyAdmissions = departmentMetrics.reduce(
    (currentMax, department) =>
      department.emergencyAdmissions > currentMax.emergencyAdmissions
        ? department
        : currentMax,
    { department: "None", emergencyAdmissions: 0 }
  );

  if (loading) {
    return (
      <LoadingScreen
        title="Loading department analytics..."
        message="Preparing department-level patient load, ICU pressure, and emergency demand."
      />
    );
  }

  if (error) {
    return (
      <ErrorState
        title="Department analytics unavailable"
        message={error}
        onRetry={() => setReloadKey((currentValue) => currentValue + 1)}
      />
    );
  }

  if (!departmentMetrics || departmentMetrics.length === 0) {
    return (
      <EmptyState
        title="No department analytics available"
        message="Department metrics have not been generated yet."
        linkTo="/dashboard"
        linkLabel="Return to Dashboard"
      />
    );
  }

  return (
    <div className="min-h-screen p-6">
      <div className="mb-6 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <Link
            to="/dashboard"
            className="mb-4 inline-flex items-center gap-2 text-sm font-medium text-blue-600 hover:text-blue-700"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to Dashboard
          </Link>
          <h1 className="text-4xl font-bold tracking-tight text-slate-900">
            Department Analytics
          </h1>
          <p className="mt-2 max-w-3xl text-slate-600">
            Operational demand across departments, with a clear view of critical
            care pressure, ICU needs, and emergency admission volume.
          </p>
        </div>

        <div className="rounded-xl border border-blue-200 bg-blue-50 px-4 py-3 text-sm font-medium text-blue-700">
          Click any department in the table below to open a filtered dashboard.
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
        <SummaryCard
          title="Departments Covered"
          value={summary?.departmentCount ?? departmentMetrics.length}
          icon={Building2}
          tone="bg-slate-100 text-slate-700"
          onClick={() => navigate("/dashboard")}
        />
        <SummaryCard
          title="Critical Hotspots"
          value={departmentsWithCriticalPatients}
          icon={Stethoscope}
          tone="bg-red-100 text-red-700"
          onClick={() => navigate("/dashboard?risk=Critical")}
        />
        <SummaryCard
          title="Peak ICU Demand"
          value={`${peakIcuDemand.department} (${peakIcuDemand.icuDemand})`}
          icon={BedDouble}
          tone="bg-blue-100 text-blue-700"
          onClick={() =>
            navigate(
              `/dashboard?department=${encodeURIComponent(
                peakIcuDemand.department
              )}&bed=ICU`
            )
          }
        />
        <SummaryCard
          title="Peak Emergency Load"
          value={`${peakEmergencyAdmissions.department} (${peakEmergencyAdmissions.emergencyAdmissions})`}
          icon={Siren}
          tone="bg-orange-100 text-orange-700"
          onClick={() =>
            navigate(
              `/dashboard?department=${encodeURIComponent(
                peakEmergencyAdmissions.department
              )}&admission=Emergency`
            )
          }
        />
      </div>

      <div className="mt-6 grid grid-cols-1 gap-6 xl:grid-cols-2">
        <DepartmentMetricChart
          title="Patients by Department"
          description="Top departments ranked by total active patient profiles."
          data={departmentMetrics}
          dataKey="totalPatients"
          color="#0f172a"
        />
        <DepartmentMetricChart
          title="Critical Patients by Department"
          description="Departments carrying the highest concentration of critical-risk cases."
          data={departmentMetrics}
          dataKey="criticalPatients"
          color="#dc2626"
        />
        <DepartmentMetricChart
          title="ICU Demand by Department"
          description="Departments currently driving the most ICU bed pressure."
          data={departmentMetrics}
          dataKey="icuDemand"
          color="#2563eb"
        />
        <DepartmentMetricChart
          title="Emergency Admissions by Department"
          description="Departments with the strongest emergency admission load."
          data={departmentMetrics}
          dataKey="emergencyAdmissions"
          color="#ea580c"
        />
      </div>

      <div className="mt-6 rounded-2xl border border-slate-200 bg-white shadow-sm">
        <div className="border-b border-slate-200 p-5">
          <h2 className="text-xl font-semibold text-slate-900">
            Department Operations Table
          </h2>
          <p className="mt-1 text-sm text-slate-500">
            Complete department-level metrics for patient volume, criticality,
            ICU demand, and emergency admissions.
          </p>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 text-slate-600">
              <tr>
                <th className="p-4">Department</th>
                <th className="p-4">Patients</th>
                <th className="p-4">Critical Patients</th>
                <th className="p-4">ICU Demand</th>
                <th className="p-4">Emergency Admissions</th>
                <th className="p-4">Open</th>
              </tr>
            </thead>
            <tbody>
              {departmentMetrics.map((department) => (
                <tr
                  key={department.department}
                  className="border-t border-slate-100"
                >
                  <td className="p-4 font-medium text-slate-900">
                    <Link
                      to={`/dashboard?department=${encodeURIComponent(department.department)}`}
                      className="text-blue-600 hover:underline"
                    >
                      {department.department}
                    </Link>
                  </td>
                  <td className="p-4 text-slate-700">{department.totalPatients}</td>
                  <td className="p-4 text-slate-700">{department.criticalPatients}</td>
                  <td className="p-4 text-slate-700">{department.icuDemand}</td>
                  <td className="p-4 text-slate-700">
                    {department.emergencyAdmissions}
                  </td>
                  <td className="p-4">
                    <Link
                      to={`/dashboard?department=${encodeURIComponent(department.department)}`}
                      className="rounded-lg bg-slate-900 px-3 py-2 text-xs font-semibold text-white hover:bg-slate-700"
                    >
                      View in Dashboard
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
