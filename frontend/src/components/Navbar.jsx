import { useEffect, useState } from "react";
import {
  Activity,
  BarChart3,
  ClipboardPlus,
  Cpu,
  LayoutDashboard,
  Stethoscope,
} from "lucide-react";
import { NavLink } from "react-router-dom";
import { getApiHealth } from "../lib/api";

function navLinkClassName({ isActive }) {
  return `inline-flex items-center gap-2 rounded-xl px-3 py-2 text-sm font-semibold transition-colors ${
    isActive
      ? "bg-slate-900 text-white"
      : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
  }`;
}

function ApiHealthBadge() {
  const [healthState, setHealthState] = useState({
    loading: true,
    error: "",
    data: null,
  });

  useEffect(() => {
    let isActive = true;

    async function checkHealth() {
      try {
        const data = await getApiHealth();

        if (!isActive) {
          return;
        }

        setHealthState({
          loading: false,
          error: "",
          data,
        });
      } catch (error) {
        if (!isActive) {
          return;
        }

        setHealthState({
          loading: false,
          error: error.message || "Backend unavailable",
          data: null,
        });
      }
    }

    checkHealth();
    const intervalId = window.setInterval(checkHealth, 60000);

    return () => {
      isActive = false;
      window.clearInterval(intervalId);
    };
  }, []);

  if (healthState.loading) {
    return (
      <div className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-500 shadow-sm">
        <Activity className="h-3.5 w-3.5 animate-pulse" />
        Checking API...
      </div>
    );
  }

  if (healthState.error) {
    return (
      <div className="inline-flex items-center gap-2 rounded-full border border-red-200 bg-red-50 px-3 py-2 text-xs font-semibold text-red-700 shadow-sm">
        <Activity className="h-3.5 w-3.5" />
        API Offline
      </div>
    );
  }

  if (healthState.data?.source === "fallback" || healthState.data?.status === "fallback") {
    return (
      <div className="inline-flex items-center gap-2 rounded-full border border-amber-200 bg-amber-50 px-3 py-2 text-xs font-semibold text-amber-700 shadow-sm">
        <Activity className="h-3.5 w-3.5" />
        Using Local Fallback
        <span className="rounded-full bg-white/80 px-2 py-0.5 text-[11px] text-amber-700">
          {healthState.data?.patients_loaded ?? 0} loaded
        </span>
      </div>
    );
  }

  return (
    <div className="inline-flex items-center gap-2 rounded-full border border-green-200 bg-green-50 px-3 py-2 text-xs font-semibold text-green-700 shadow-sm">
        <Activity className="h-3.5 w-3.5" />
      API Connected
      <span className="rounded-full bg-white/80 px-2 py-0.5 text-[11px] text-green-700">
        {healthState.data?.patients_loaded ?? 0} loaded
      </span>
    </div>
  );
}

export default function Navbar() {
  return (
    <header className="sticky top-0 z-30 border-b border-slate-200 bg-white/90 backdrop-blur print:hidden">
      <div className="mx-auto flex max-w-7xl flex-col gap-4 px-4 py-4 sm:px-6 lg:flex-row lg:items-center lg:justify-between lg:px-8">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center">
          <NavLink
            to="/dashboard"
            className="inline-flex items-center gap-3 text-slate-900"
          >
            <div className="rounded-2xl bg-slate-900 p-2 text-white shadow-sm">
              <Stethoscope className="h-5 w-5" />
            </div>
            <div>
              <p className="text-lg font-bold tracking-tight">
                Docstribe Admission Intelligence
              </p>
              <p className="text-sm text-slate-500">
                Hospital prioritization, analytics, and AI reporting
              </p>
            </div>
          </NavLink>

          <nav className="flex flex-wrap gap-2 lg:ml-6">
            <NavLink to="/dashboard" className={navLinkClassName}>
              <LayoutDashboard className="h-4 w-4" />
              Dashboard
            </NavLink>
            <NavLink to="/analytics/departments" className={navLinkClassName}>
              <BarChart3 className="h-4 w-4" />
              Department Analytics
            </NavLink>
            <NavLink to="/architecture" className={navLinkClassName}>
              <Cpu className="h-4 w-4" />
              AI Architecture
            </NavLink>
            <NavLink to="/intake/new-patient" className={navLinkClassName}>
              <ClipboardPlus className="h-4 w-4" />
              New Patient Intake
            </NavLink>
          </nav>
        </div>

        <ApiHealthBadge />
      </div>
    </header>
  );
}
