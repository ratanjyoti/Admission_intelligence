import {
  buildDashboardCharts,
  buildDashboardSummary,
  findPatientById,
} from "./patientData";
import { enrichPatientRecord } from "./operationalIntelligence";

const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL ||
  (import.meta.env.DEV ? "http://localhost:8000" : "")
).replace(/\/$/, "");
const FALLBACK_DATA_URL = `${import.meta.env.BASE_URL}data/dashboard_patients.json`;
let fallbackPatientDataPromise;

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
  const response = await fetch(`${API_BASE_URL}${path}`, {
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
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    throw await buildResponseError(response);
  }

  return response.json();
}

export function getPatients() {
  return fetchJson("/api/patients", async () =>
    ensureOperationalPatients(await loadFallbackPatientData())
  ).then(ensureOperationalPatients);
}

export function getPatientById(patientId) {
  return fetchJson(`/api/patients/${encodeURIComponent(patientId)}`, async () => {
    const fallbackPatientData = await loadFallbackPatientData();
    return ensureOperationalPatient(findPatientById(fallbackPatientData, patientId));
  }).then(ensureOperationalPatient);
}

export function getDashboardSummary() {
  return fetchJson("/api/dashboard/summary", async () => {
    const fallbackPatientData = ensureOperationalPatients(await loadFallbackPatientData());
    return buildDashboardSummary(fallbackPatientData);
  });
}

export function getDashboardCharts() {
  return fetchJson("/api/dashboard/charts", async () => {
    const fallbackPatientData = ensureOperationalPatients(await loadFallbackPatientData());
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

export function predictNewPatient(payload) {
  return postJson("/api/predict/patient", payload);
}

export function createIntakePatient(payload) {
  return postJson("/api/patients/intake", payload);
}

export function extractPrescription(file) {
  const formData = new FormData();
  formData.append("file", file);
  return postFormData("/api/prescription/extract", formData);
}
