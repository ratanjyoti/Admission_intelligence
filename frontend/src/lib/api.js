import {
  buildDashboardCharts,
  buildDashboardSummary,
  findPatientById,
} from "./patientData";
import { enrichPatientRecord } from "./operationalIntelligence";

const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || ""
).replace(/\/$/, "");
const CLIENT_FALLBACK_ENABLED =
  String(import.meta.env.VITE_ENABLE_CLIENT_FALLBACK || "").toLowerCase() === "true";
const FALLBACK_DATA_URL = `${import.meta.env.BASE_URL}data/dashboard_patients.json`;
let fallbackPatientDataPromise;

function buildApiUrl(path) {
  return API_BASE_URL ? `${API_BASE_URL}${path}` : path;
}

function hasOperationalPayload(patient) {
  return Boolean(
    patient?.operational?.clinicalIntelligence &&
      patient?.operational?.caseType &&
      patient?.operational?.packageIntelligence
  );
}

function ensureOperationalPatient(patient) {
  if (!patient) {
    return null;
  }

  return hasOperationalPayload(patient) ? patient : enrichPatientRecord(patient);
}

function ensureOperationalPatients(patients) {
  if (!Array.isArray(patients)) {
    return [];
  }

  if (patients.every(hasOperationalPayload)) {
    return patients;
  }

  return patients.map((patient) => ensureOperationalPatient(patient));
}

async function loadFallbackPatientData() {
  if (!fallbackPatientDataPromise) {
    fallbackPatientDataPromise = fetch(FALLBACK_DATA_URL).then(async (response) => {
      if (!response.ok) {
        throw new Error(`Fallback dataset request failed with ${response.status}`);
      }

      return response.json();
    });
  }

  return fallbackPatientDataPromise;
}

async function fetchJson(path, options = {}) {
  const {
    fallbackFactory,
    allowFallback = CLIENT_FALLBACK_ENABLED,
    requireBackend = false,
    backendErrorMessage = "",
  } = options;

  try {
    const response = await fetch(buildApiUrl(path));

    if (!response.ok) {
      throw new Error(`Request failed with ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    if (allowFallback && typeof fallbackFactory === "function") {
      const fallback = await fallbackFactory();

      if (fallback !== undefined && fallback !== null) {
        return fallback;
      }
    }

    if (requireBackend) {
      const baseMessage = error?.message || "Backend request failed";
      const detail =
        backendErrorMessage ||
        "Backend API is required for official PDF pricing and local fallback is disabled.";
      throw new Error(`${baseMessage}. ${detail}`);
    }

    throw error;
  }
}

async function buildResponseError(response) {
  let message = `Request failed with ${response.status}`;

  try {
    const payload = await response.json();
    if (typeof payload?.detail === "string") {
      message = payload.detail;
    } else if (Array.isArray(payload?.detail)) {
      message = payload.detail
        .map((item) => item?.msg || JSON.stringify(item))
        .join("; ");
    } else if (typeof payload?.message === "string") {
      message = payload.message;
    }
  } catch {
    try {
      const text = await response.text();
      if (text) {
        message = text;
      }
    } catch {
      // no-op
    }
  }

  return new Error(message);
}

async function postJson(path, payload) {
  const response = await fetch(buildApiUrl(path), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw await buildResponseError(response);
  }

  return response.json();
}

async function postFormData(path, formData) {
  const response = await fetch(buildApiUrl(path), {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    throw await buildResponseError(response);
  }

  return response.json();
}

export function getPatients() {
  return fetchJson("/api/patients", {
    fallbackFactory: async () => ensureOperationalPatients(await loadFallbackPatientData()),
    requireBackend: true,
    backendErrorMessage:
      "Start the backend (port 8000) so revenue uses official extracted package rates.",
  }).then(ensureOperationalPatients);
}

export function getPatientById(patientId) {
  return fetchJson(`/api/patients/${encodeURIComponent(patientId)}`, {
    fallbackFactory: async () => {
      const fallbackPatientData = await loadFallbackPatientData();
      return ensureOperationalPatient(findPatientById(fallbackPatientData, patientId));
    },
    requireBackend: true,
    backendErrorMessage:
      "Patient profile pricing requires backend official-rate inference and cannot use local fallback.",
  }).then(ensureOperationalPatient);
}

export function getDashboardSummary() {
  return fetchJson("/api/dashboard/summary", {
    fallbackFactory: async () => {
      const fallbackPatientData = ensureOperationalPatients(await loadFallbackPatientData());
      return buildDashboardSummary(fallbackPatientData);
    },
    requireBackend: true,
    backendErrorMessage:
      "Dashboard summary is locked to backend data so official PDF rates are preserved.",
  });
}

export function getDashboardCharts() {
  return fetchJson("/api/dashboard/charts", {
    fallbackFactory: async () => {
      const fallbackPatientData = ensureOperationalPatients(await loadFallbackPatientData());
      return buildDashboardCharts(fallbackPatientData);
    },
    requireBackend: true,
    backendErrorMessage:
      "Dashboard charts are locked to backend data so official PDF rates are preserved.",
  });
}

export function getApiHealth() {
  return fetchJson("/api/health", {
    fallbackFactory: async () => {
      const fallbackPatientData = await loadFallbackPatientData();

      return {
        status: "fallback",
        patients_loaded: fallbackPatientData.length,
        source: "fallback",
      };
    },
    allowFallback: CLIENT_FALLBACK_ENABLED,
  });
}

export function predictNewPatient(payload) {
  return postJson("/api/predict/patient", payload);
}

export function createIntakePatient(payload) {
  return postJson("/api/patients/intake", payload);
}

export function analyzeAgenticPatient(payload) {
  return postJson("/api/agentic/analyze", payload);
}

export function getAgenticPriorityQueue(payload) {
  return postJson("/api/agentic/prioritize", payload);
}

export function extractPrescription(file) {
  const formData = new FormData();
  formData.append("file", file);
  return postFormData("/api/prescription/extract", formData);
}
