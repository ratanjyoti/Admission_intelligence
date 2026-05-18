import { useState } from "react";
import { Link } from "react-router-dom";
import {
  Activity,
  AlertTriangle,
  ArrowLeft,
  BedDouble,
  Brain,
  ClipboardPlus,
  FileText,
  FileUp,
  IndianRupee,
  Loader2,
  ShieldAlert,
  Stethoscope,
  TimerReset,
  TrendingUp,
} from "lucide-react";
import ErrorState from "../components/ErrorState";
import {
  createIntakePatient,
  extractPrescription,
  predictNewPatient,
} from "../lib/api";

const DEFAULT_FORM = {
  patientName: "",
  department: "General Medicine",
  doctorName: "",
  customerType: "Incoming",
  diagnosis: "",
  clinicalNotes: "",
  physicalRemarks: "",
  vitalRemarks: "",
  investigations: "",
  doctorAdvice: "",
  medicineDetails: "",
  explicitProcedure: "",
  repeatVisit: false,
  visitCount: 1,
  firstVisitRiskScore: 0,
};

function SectionCard({ title, description, children }) {
  return (
    <section className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="mb-4">
        <h2 className="text-lg font-semibold text-slate-900">{title}</h2>
        {description ? (
          <p className="mt-1 text-sm text-slate-500">{description}</p>
        ) : null}
      </div>
      {children}
    </section>
  );
}

function InputField({
  label,
  name,
  value,
  onChange,
  placeholder,
  type = "text",
  min,
  max,
}) {
  return (
    <label className="block">
      <span className="mb-2 block text-xs font-semibold uppercase tracking-wide text-slate-500">
        {label}
      </span>
      <input
        type={type}
        name={name}
        value={value}
        min={min}
        max={max}
        onChange={onChange}
        placeholder={placeholder}
        className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm outline-none focus:border-slate-400"
      />
    </label>
  );
}

function TextAreaField({ label, name, value, onChange, placeholder, rows = 4 }) {
  return (
    <label className="block">
      <span className="mb-2 block text-xs font-semibold uppercase tracking-wide text-slate-500">
        {label}
      </span>
      <textarea
        name={name}
        rows={rows}
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm outline-none focus:border-slate-400"
      />
    </label>
  );
}

function MetricTile({ icon: Icon, title, value, detail, tone = "slate" }) {
  const tones = {
    slate: "bg-slate-100 text-slate-700",
    red: "bg-red-100 text-red-700",
    blue: "bg-blue-100 text-blue-700",
    orange: "bg-orange-100 text-orange-700",
    green: "bg-green-100 text-green-700",
    purple: "bg-purple-100 text-purple-700",
  };

  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-sm font-medium text-slate-500">{title}</p>
          <p className="mt-2 text-xl font-bold text-slate-900">{value}</p>
          {detail ? <p className="mt-1 text-sm text-slate-500">{detail}</p> : null}
        </div>
        <div className={`rounded-xl p-3 ${tones[tone]}`}>
          <Icon className="h-5 w-5" />
        </div>
      </div>
    </div>
  );
}

function ProbabilityBar({ label, probability }) {
  const percentage = Math.round((Number(probability || 0) * 100));

  return (
    <div>
      <div className="mb-2 flex items-center justify-between text-xs font-semibold uppercase tracking-wide text-slate-500">
        <span>{label}</span>
        <span>{percentage}%</span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-slate-100">
        <div
          className="h-full rounded-full bg-slate-900"
          style={{ width: `${Math.max(4, percentage)}%` }}
        />
      </div>
    </div>
  );
}

function formatProbability(probability) {
  return `${Math.round(Number(probability || 0) * 100)}%`;
}

function formatConfidence(confidence) {
  return `${Math.round(Number(confidence || 0) * 100)}% confidence`;
}

function describeValidatedPrediction(prediction, fallbackText) {
  if (!prediction) {
    return fallbackText;
  }

  if (prediction.modelLabel && prediction.modelLabel !== prediction.label) {
    return `Model predicted ${prediction.modelLabel} (${formatProbability(
      prediction.modelConfidence
    )}); rules validated to ${prediction.label} (${formatConfidence(
      prediction.confidence
    )}).`;
  }

  return `${prediction.label} with ${formatConfidence(prediction.confidence)}.`;
}

export default function NewPatientIntake() {
  const [form, setForm] = useState(DEFAULT_FORM);
  const [prediction, setPrediction] = useState(null);
  const [savedPatient, setSavedPatient] = useState(null);
  const [extraction, setExtraction] = useState(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [extracting, setExtracting] = useState(false);
  const [error, setError] = useState("");

  function handleChange(event) {
    const { name, value, type, checked } = event.target;

    setForm((currentForm) => ({
      ...currentForm,
      [name]:
        type === "checkbox"
          ? checked
          : type === "number"
          ? Number(value)
          : value,
    }));
  }

  async function handlePredict(event) {
    event.preventDefault();
    setLoading(true);
    setError("");
    setSavedPatient(null);

    try {
      const result = await predictNewPatient(form);
      setPrediction(result);
    } catch (requestError) {
      setError(requestError.message || "Prediction request failed.");
    } finally {
      setLoading(false);
    }
  }

  async function handleSaveToWorklist() {
    setSaving(true);
    setError("");

    try {
      const result = await createIntakePatient(form);
      setPrediction(result);
      setSavedPatient(result);
    } catch (requestError) {
      setError(requestError.message || "Unable to add patient to worklist.");
    } finally {
      setSaving(false);
    }
  }

  function applyAutoFill(autoFill) {
    setForm((currentForm) => {
      const nextForm = { ...currentForm };

      Object.entries(autoFill || {}).forEach(([field, value]) => {
        if (typeof value === "boolean") {
          nextForm[field] = value;
          return;
        }

        if (typeof value === "number" && Number.isFinite(value)) {
          nextForm[field] = value;
          return;
        }

        if (typeof value === "string" && value.trim()) {
          nextForm[field] = value;
        }
      });

      return nextForm;
    });
  }

  async function handlePrescriptionUpload(event) {
    const file = event.target.files?.[0];

    if (!file) {
      return;
    }

    setExtracting(true);
    setError("");
    setPrediction(null);
    setSavedPatient(null);

    try {
      const result = await extractPrescription(file);
      setExtraction(result);
      applyAutoFill(result.autoFill);
    } catch (requestError) {
      setError(requestError.message || "Prescription extraction failed.");
    } finally {
      setExtracting(false);
      event.target.value = "";
    }
  }

  const operational = prediction?.operational || {};
  const predictive = operational.predictiveModeling || {};
  const intelligenceProfile = operational.intelligenceProfile || {};
  const packageIntelligence = operational.packageIntelligence || {};
  const readmissionRisk = operational.readmissionRisk || {};
  const deferredTime = operational.deferredTime || {};
  const noShowRisk = operational.noShowRisk || {};
  const lengthOfStay = operational.lengthOfStay || {};
  const treatmentPlan = operational.treatmentPlan || {};
  const admissionConversion = operational.admissionConversionProbability || {};
  const topSignals = predictive.topSignals || [];
  const selectedModels = predictive.selectedModels || {};

  return (
    <div className="min-h-screen p-6">
      <div className="mb-6 flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
        <div>
          <Link
            to="/dashboard"
            className="mb-4 inline-flex items-center gap-2 text-sm font-medium text-blue-600 hover:text-blue-700"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to Dashboard
          </Link>
          <h1 className="text-4xl font-bold tracking-tight text-slate-900">
            New Patient Predictive Intake
          </h1>
          <p className="mt-2 max-w-4xl text-slate-600">
            Enter a new incoming patient and let the predictive ML layer estimate
            risk, admission pathway, ICU need, readmission risk, LOS, deferability,
            and revenue potential. Rules then validate the prediction, and the LLM
            can explain the result when enabled.
          </p>
        </div>

        <div className="rounded-2xl border border-blue-200 bg-blue-50 px-4 py-3 text-sm font-medium text-blue-700">
          ML = prediction, rules = safety validation, LLM = explanation.
        </div>
      </div>

      {error ? (
        <div className="mb-6">
          <ErrorState
            compact
            title="Prediction unavailable"
            message={error}
          />
        </div>
      ) : null}

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-[1.05fr_0.95fr]">
        <SectionCard
          title="Incoming Patient Form"
          description="Use this intake form for unseen patients. The backend will convert it into predictive admission intelligence."
        >
          <form onSubmit={handlePredict} className="space-y-5">
            <div className="rounded-3xl border border-dashed border-blue-200 bg-blue-50/70 p-5">
              <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                <div className="max-w-2xl">
                  <div className="flex items-center gap-3">
                    <div className="rounded-2xl bg-blue-100 p-3 text-blue-700">
                      <FileText className="h-5 w-5" />
                    </div>
                    <div>
                      <h3 className="text-base font-semibold text-slate-900">
                        Upload Prescription & Auto-Fill Intake
                      </h3>
                      <p className="mt-1 text-sm text-slate-600">
                        Upload a prescription or discharge-note PDF. The backend
                        extracts text, maps it into diagnosis, history,
                        investigations, medicines, advice, and procedure
                        fields, then auto-fills the form for review.
                      </p>
                    </div>
                  </div>
                </div>

                <label className="inline-flex cursor-pointer items-center justify-center gap-2 rounded-xl bg-slate-900 px-4 py-3 text-sm font-semibold text-white hover:bg-slate-700">
                  {extracting ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <FileUp className="h-4 w-4" />
                  )}
                  {extracting ? "Extracting PDF..." : "Upload PDF"}
                  <input
                    type="file"
                    accept="application/pdf,.pdf"
                    className="hidden"
                    onChange={handlePrescriptionUpload}
                    disabled={extracting}
                  />
                </label>
              </div>

              {extraction ? (
                <div className="mt-5 space-y-4 rounded-2xl border border-blue-200 bg-white p-4">
                  <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                    <div>
                      <p className="text-sm font-semibold text-slate-900">
                        Extracted from {extraction.filename}
                      </p>
                      <p className="text-sm text-slate-500">
                        {extraction.pageCount} page(s). The form fields below
                        were auto-filled and can still be edited before
                        prediction.
                      </p>
                    </div>
                    <div className="rounded-xl bg-emerald-50 px-3 py-2 text-sm font-medium text-emerald-700">
                      {extraction.detectedFields?.length || 0} field(s) detected
                    </div>
                  </div>

                  {extraction.warnings?.length ? (
                    <div className="rounded-2xl border border-amber-200 bg-amber-50 p-3">
                      <ul className="space-y-2 text-sm text-amber-800">
                        {extraction.warnings.map((warning) => (
                          <li key={warning} className="flex items-start gap-2">
                            <AlertTriangle className="mt-0.5 h-4 w-4" />
                            <span>{warning}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  ) : null}

                  <div className="grid grid-cols-1 gap-4 xl:grid-cols-[0.9fr_1.1fr]">
                    <div>
                      <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
                        Auto-filled Fields
                      </p>
                      <div className="space-y-2">
                        {(extraction.detectedFields || []).map((item) => (
                          <div
                            key={item.field}
                            className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2"
                          >
                            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                              {item.label}
                            </p>
                            <p className="mt-1 text-sm text-slate-700">
                              {item.preview}
                            </p>
                          </div>
                        ))}
                      </div>
                    </div>

                    <div>
                      <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
                        Extracted Text Preview
                      </p>
                      <pre className="max-h-72 overflow-auto whitespace-pre-wrap rounded-2xl border border-slate-200 bg-slate-950/95 p-4 text-xs leading-6 text-slate-100">
                        {extraction.extractedText}
                      </pre>
                    </div>
                  </div>
                </div>
              ) : null}
            </div>

            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <InputField
                label="Patient Name"
                name="patientName"
                value={form.patientName}
                onChange={handleChange}
                placeholder="Enter patient name"
              />
              <InputField
                label="Department"
                name="department"
                value={form.department}
                onChange={handleChange}
                placeholder="Neurology / Cardiology / Nephrology..."
              />
              <InputField
                label="Doctor Name"
                name="doctorName"
                value={form.doctorName}
                onChange={handleChange}
                placeholder="Consulting clinician"
              />
              <InputField
                label="Customer Type"
                name="customerType"
                value={form.customerType}
                onChange={handleChange}
                placeholder="Incoming / OPD / Corporate..."
              />
              <InputField
                label="Visit Count"
                name="visitCount"
                type="number"
                min={1}
                max={20}
                value={form.visitCount}
                onChange={handleChange}
              />
              <InputField
                label="First Visit Risk Score"
                name="firstVisitRiskScore"
                type="number"
                min={0}
                max={10}
                value={form.firstVisitRiskScore}
                onChange={handleChange}
              />
            </div>

            <label className="flex items-center gap-3 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm font-medium text-slate-700">
              <input
                type="checkbox"
                name="repeatVisit"
                checked={form.repeatVisit}
                onChange={handleChange}
                className="h-4 w-4 rounded border-slate-300"
              />
              Repeat visit / prior consultation already exists
            </label>

            <TextAreaField
              label="Diagnosis"
              name="diagnosis"
              value={form.diagnosis}
              onChange={handleChange}
              placeholder="Chest pain with diabetes and high creatinine..."
              rows={3}
            />
            <TextAreaField
              label="Clinical Notes"
              name="clinicalNotes"
              value={form.clinicalNotes}
              onChange={handleChange}
              placeholder="Presenting complaint, history of present illness, concerning narrative..."
              rows={5}
            />

            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <TextAreaField
                label="Physical Remarks"
                name="physicalRemarks"
                value={form.physicalRemarks}
                onChange={handleChange}
                placeholder="Exam findings..."
                rows={4}
              />
              <TextAreaField
                label="Vital Remarks / History"
                name="vitalRemarks"
                value={form.vitalRemarks}
                onChange={handleChange}
                placeholder="Past conditions, surgeries, longitudinal history..."
                rows={4}
              />
            </div>

            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <TextAreaField
                label="Investigations"
                name="investigations"
                value={form.investigations}
                onChange={handleChange}
                placeholder="CBC, creatinine, imaging, ECG..."
                rows={4}
              />
              <TextAreaField
                label="Doctor Advice"
                name="doctorAdvice"
                value={form.doctorAdvice}
                onChange={handleChange}
                placeholder="Admission advice, escalation, follow-up plan..."
                rows={4}
              />
            </div>

            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <TextAreaField
                label="Medicine Details"
                name="medicineDetails"
                value={form.medicineDetails}
                onChange={handleChange}
                placeholder="Current medications or treatments..."
                rows={4}
              />
              <TextAreaField
                label="Explicit Procedure"
                name="explicitProcedure"
                value={form.explicitProcedure}
                onChange={handleChange}
                placeholder="Optional explicit procedure if already known..."
                rows={4}
              />
            </div>

            <div className="flex flex-col gap-3 sm:flex-row">
              <button
                type="submit"
                disabled={loading || extracting}
                className="inline-flex items-center justify-center gap-2 rounded-xl bg-slate-900 px-4 py-3 text-sm font-semibold text-white hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {loading ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Brain className="h-4 w-4" />
                )}
                Generate Predictive Intelligence
              </button>

              <button
                type="button"
                disabled={!prediction || saving}
                onClick={handleSaveToWorklist}
                className="inline-flex items-center justify-center gap-2 rounded-xl border border-slate-300 px-4 py-3 text-sm font-semibold text-slate-700 hover:border-slate-400 hover:text-slate-900 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {saving ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <ClipboardPlus className="h-4 w-4" />
                )}
                Add to Live Worklist
              </button>
            </div>
          </form>
        </SectionCard>

        <div className="space-y-6">
          <SectionCard
            title="Prediction Output"
            description="This preview combines predictive ML forecasting, rule validation, and optional LLM explanation."
          >
            {!prediction ? (
              <div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50 p-6 text-sm text-slate-500">
                Submit the intake form to see the predicted patient profile.
              </div>
            ) : (
              <div className="space-y-5">
                <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                  <MetricTile
                    icon={ShieldAlert}
                    title="Risk Category"
                    value={`${prediction.risk?.category || "Unknown"} (${prediction.risk?.score || 0}/10)`}
                    detail={describeValidatedPrediction(
                      predictive.riskCategory,
                      prediction.risk?.reasoning
                    )}
                    tone="red"
                  />
                  <MetricTile
                    icon={TrendingUp}
                    title="Admission Pathway"
                    value={prediction.admission?.type || "Unknown"}
                    detail={`${describeValidatedPrediction(
                      predictive.admissionType,
                      "Prediction pending."
                    )} Admission likelihood ${formatProbability(
                      predictive.admissionLikelihood?.probability
                    )}.`}
                    tone="orange"
                  />
                  <MetricTile
                    icon={BedDouble}
                    title="Bed Planning"
                    value={prediction.bed?.type || "Unknown"}
                    detail={`${describeValidatedPrediction(
                      predictive.bedType,
                      "Prediction pending."
                    )} ICU probability ${formatProbability(
                      predictive.icuRequirement?.probability
                    )}.`}
                    tone="blue"
                  />
                  <MetricTile
                    icon={Activity}
                    title="Length Of Stay"
                    value={lengthOfStay.label || predictive.lengthOfStay?.label || "Pending"}
                    detail={`Expected ${predictive.lengthOfStay?.expectedDays ?? 0} days | range ${
                      predictive.lengthOfStay?.lowDays ?? 0
                    }-${predictive.lengthOfStay?.highDays ?? 0} days`}
                    tone="green"
                  />
                  <MetricTile
                    icon={TimerReset}
                    title="Deferred Time"
                    value={deferredTime.label || predictive.deferredTime?.label || "Pending"}
                    detail={describeValidatedPrediction(
                      predictive.deferredTime,
                      deferredTime.reasoning
                    )}
                    tone="slate"
                  />
                  <MetricTile
                    icon={IndianRupee}
                    title="Revenue Potential"
                    value={packageIntelligence.expectedRevenue || predictive.revenueCategory?.label || "Pending"}
                    detail={`${predictive.revenueCategory?.label || packageIntelligence.revenueCategory || "Category pending"} | ${formatConfidence(
                      predictive.revenueCategory?.confidence
                    )}`}
                    tone="purple"
                  />
                </div>

                <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                  <p className="text-sm font-semibold text-slate-900">
                    Engine Mode: {intelligenceProfile.primaryEngine || "Predictive ML + Rule-based"}
                  </p>
                  <p className="mt-1 text-sm text-slate-600">
                    {prediction.patientName} was evaluated as a new intake case.
                    The model predicted the likely pathway first, then rule-based
                    safety logic validated the outcome before the final profile was produced.
                  </p>
                  <p className="mt-2 text-sm text-slate-500">
                    Model version {predictive.modelVersion || "v2.0"} | trained{" "}
                    {predictive.trainedOn
                      ? new Date(predictive.trainedOn).toLocaleString()
                      : "recently"}
                  </p>
                </div>

                <div className="space-y-4">
                  <ProbabilityBar
                    label="Admission likelihood"
                    probability={predictive.admissionLikelihood?.probability}
                  />
                  <ProbabilityBar
                    label="Emergency escalation"
                    probability={predictive.emergencyEscalation?.probability}
                  />
                  <ProbabilityBar
                    label="ICU requirement"
                    probability={predictive.icuRequirement?.probability}
                  />
                </div>

                <div className="rounded-2xl border border-slate-200 bg-white p-4">
                  <p className="text-sm font-semibold text-slate-900">
                    Top Contributing Signals
                  </p>
                  {topSignals.length ? (
                    <ul className="mt-3 space-y-2 text-sm text-slate-700">
                      {topSignals.map((signal) => (
                        <li key={signal} className="flex items-start gap-2">
                          <Brain className="mt-0.5 h-4 w-4 text-blue-500" />
                          <span>{signal}</span>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="mt-2 text-sm text-slate-600">
                      Signal extraction is pending for this intake.
                    </p>
                  )}
                </div>

                <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                  <div className="rounded-2xl border border-slate-200 bg-white p-4">
                    <p className="text-sm font-semibold text-slate-900">
                      Readmission / No-show
                    </p>
                    <p className="mt-2 text-sm text-slate-700">
                      Readmission Risk:{" "}
                      <strong>{readmissionRisk.label || predictive.readmissionRisk?.label}</strong>{" "}
                      {predictive.readmissionRisk?.confidence ? (
                        <span className="text-slate-500">
                          ({formatConfidence(predictive.readmissionRisk?.confidence)})
                        </span>
                      ) : null}
                    </p>
                    <p className="mt-1 text-sm text-slate-700">
                      No-show Risk: <strong>{noShowRisk.label || "Pending"}</strong>
                    </p>
                  </div>

                  <div className="rounded-2xl border border-slate-200 bg-white p-4">
                    <p className="text-sm font-semibold text-slate-900">
                      Treatment Pathway
                    </p>
                    <p className="mt-2 text-sm text-slate-700">
                      <strong>Primary:</strong> {treatmentPlan.primary || "Pending"}
                    </p>
                    <p className="mt-2 text-sm text-slate-700">
                      <strong>Secondary:</strong> {treatmentPlan.secondary || "Pending"}
                    </p>
                  </div>
                </div>

                <div className="rounded-2xl border border-slate-200 bg-white p-4">
                  <p className="text-sm font-semibold text-slate-900">
                    Validation Summary
                  </p>
                  {predictive.validationSummary?.length ? (
                    <ul className="mt-3 space-y-2 text-sm text-slate-700">
                      {predictive.validationSummary.map((item) => (
                        <li key={item} className="flex items-start gap-2">
                          <AlertTriangle className="mt-0.5 h-4 w-4 text-amber-500" />
                          <span>{item}</span>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="mt-2 text-sm text-slate-600">
                      No rule-based overrides were needed for this prediction.
                    </p>
                  )}
                </div>

                <div className="rounded-2xl border border-slate-200 bg-white p-4">
                  <p className="text-sm font-semibold text-slate-900">
                    Selected Models
                  </p>
                  <div className="mt-3 grid grid-cols-1 gap-2 md:grid-cols-2">
                    {Object.entries(selectedModels).map(([target, modelName]) => (
                      <div
                        key={target}
                        className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700"
                      >
                        <span className="font-medium text-slate-900">
                          {target.replaceAll("_", " ")}
                        </span>
                        : {modelName}
                      </div>
                    ))}
                  </div>
                </div>

                <div className="rounded-2xl border border-slate-200 bg-white p-4">
                  <p className="text-sm font-semibold text-slate-900">
                    Conversion Signal
                  </p>
                  <p className="mt-2 text-sm text-slate-700">
                    Admission conversion probability:{" "}
                    <strong>{admissionConversion.percentage || 0}%</strong>
                  </p>
                  <p className="mt-1 text-sm text-slate-600">
                    {admissionConversion.reasoning}
                  </p>
                </div>
              </div>
            )}
          </SectionCard>

          {savedPatient ? (
            <SectionCard
              title="Saved To Worklist"
              description="This predicted patient was persisted into the live intake dataset and is now part of the dashboard API feed."
            >
              <div className="flex flex-col gap-3 sm:flex-row">
                <Link
                  to={`/patient/${encodeURIComponent(savedPatient.patientId)}`}
                  className="inline-flex items-center justify-center gap-2 rounded-xl bg-slate-900 px-4 py-3 text-sm font-semibold text-white hover:bg-slate-700"
                >
                  <Stethoscope className="h-4 w-4" />
                  Open Full Patient Profile
                </Link>
                <Link
                  to="/dashboard"
                  className="inline-flex items-center justify-center gap-2 rounded-xl border border-slate-300 px-4 py-3 text-sm font-semibold text-slate-700 hover:border-slate-400 hover:text-slate-900"
                >
                  <ClipboardPlus className="h-4 w-4" />
                  Return To Dashboard
                </Link>
              </div>
            </SectionCard>
          ) : null}
        </div>
      </div>
    </div>
  );
}
