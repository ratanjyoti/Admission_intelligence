import {
  buildDashboardCharts,
  buildDashboardSummary,
  findPatientById,
} from "./patientData";

const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL ||
  (import.meta.env.DEV ? "http://localhost:8000" : "")
).replace(/\/$/, "");
let fallbackPatientDataPromise;

async function loadFallbackPatientData() {
  if (!fallbackPatientDataPromise) {
    fallbackPatientDataPromise = import("../data/dashboard_patients.json").then(
      (module) => module.default
    );
  }

  return fallbackPatientDataPromise;
}

async function fetchJson(path, fallbackFactory) {
  try {
    const response = await fetch(`${API_BASE_URL}${path}`);

    if (!response.ok) {
      throw new Error(`Request failed with ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    if (typeof fallbackFactory === "function") {
      const fallback = await fallbackFactory();

      if (fallback !== undefined && fallback !== null) {
        return fallback;
      }
    }

    throw error;
  }
}

export function getPatients() {
  return fetchJson("/api/patients", () => loadFallbackPatientData());
}

export function getPatientById(patientId) {
  return fetchJson(`/api/patients/${encodeURIComponent(patientId)}`, async () => {
    const fallbackPatientData = await loadFallbackPatientData();
    return findPatientById(fallbackPatientData, patientId);
  });
}

export function getDashboardSummary() {
  return fetchJson("/api/dashboard/summary", async () => {
    const fallbackPatientData = await loadFallbackPatientData();
    return buildDashboardSummary(fallbackPatientData);
  });
}

export function getDashboardCharts() {
  return fetchJson("/api/dashboard/charts", async () => {
    const fallbackPatientData = await loadFallbackPatientData();
    return buildDashboardCharts(fallbackPatientData);
  });
}

export function getApiHealth() {
  return fetchJson("/api/health", async () => {
    const fallbackPatientData = await loadFallbackPatientData();

    return {
      status: "fallback",
      patients_loaded: fallbackPatientData.length,
      source: "fallback",
    };
  });
}
