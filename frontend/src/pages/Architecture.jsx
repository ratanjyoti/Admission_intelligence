import { Link } from "react-router-dom";
import {
  ArrowLeft,
  Brain,
  Cpu,
  Database,
  Layers3,
  ShieldCheck,
  Workflow,
} from "lucide-react";

const PIPELINE_STEPS = [
  {
    icon: Database,
    title: "EMR / Source Data",
    detail:
      "Patient identifiers, diagnosis, clinical notes, medications, vitals, investigations, department, and visit history.",
    tone: "bg-slate-900 text-white",
  },
  {
    icon: Layers3,
    title: "Preprocessing Layer",
    detail:
      "Field normalization, URL decoding, text cleanup, column mapping, and safe defaults for missing values.",
    tone: "bg-blue-700 text-white",
  },
  {
    icon: Brain,
    title: "Predictive ML Layer",
    detail:
      "Historical patient patterns train predictive models for risk, admission type, bed need, ICU probability, LOS, readmission, deferability, and revenue category.",
    tone: "bg-purple-700 text-white",
  },
  {
    icon: Cpu,
    title: "Rule Validation + Selective LLM",
    detail:
      "Rules validate safety-critical escalations, then LLM enrichment adds explanation, coding depth, history structuring, and treatment planning for selected cases.",
    tone: "bg-orange-600 text-white",
  },
  {
    icon: Workflow,
    title: "Cache + Traceability",
    detail:
      "LLM output is cached and merged with rule-based output so the frontend receives one explainable patient intelligence payload.",
    tone: "bg-emerald-700 text-white",
  },
  {
    icon: ShieldCheck,
    title: "Dashboard + Patient Profile",
    detail:
      "AI-prioritized worklist, analytics, PDF reports, evidence traces, and clinician-facing decision support.",
    tone: "bg-rose-700 text-white",
  },
];

const OUTPUT_MAPPING = [
  {
    field: "Risk Score / Category",
    source: "Clinical notes, journey trend, red flags, visit history",
    logic:
      "Predicted from historical patterns in notes, department, repeat visits, and structured feature flags, then validated by rules.",
    confidence: "High",
  },
  {
    field: "Admission Type",
    source: "Risk, urgency wording, doctor advice, symptom severity",
    logic:
      "Predicted from historical admission patterns, then safety rules prevent under-triage when urgent keywords are present.",
    confidence: "High",
  },
  {
    field: "Bed Allocation",
    source: "Risk, admission type, specialty cohort, severity",
    logic:
      "ML predicts bed pathway and ICU likelihood; rules can upgrade to HDU or ICU when monitoring signals cross safety thresholds.",
    confidence: "High",
  },
  {
    field: "Procedure Intelligence",
    source: "Diagnosis, department, notes, inferred procedure rules",
    logic:
      "Explicit procedure if recorded. Inferred procedure confidence generated when operative context is detectable.",
    confidence: "Medium",
  },
  {
    field: "Revenue Forecast",
    source: "Case type, bed type, urgency, procedure burden, cohort",
    logic:
      "Revenue category is predicted from historical case complexity and then contextualized with operational case-intensity logic.",
    confidence: "Medium",
  },
  {
    field: "LOS / Readmission / Deferred Time",
    source: "Bed type, visit history, progression, chronic disease burden",
    logic:
      "ML predicts LOS and readmission risk, while rule logic converts them into operational deferability guidance.",
    confidence: "Medium",
  },
  {
    field: "ICD-10 / Comorbidities / Symptoms",
    source: "Diagnosis, notes, medications, history, remarks",
    logic:
      "Structured extraction from semi-structured text, with optional on-demand LLM-first review for one selected patient when deeper reasoning is needed.",
    confidence: "Medium",
  },
];

const RISK_BREAKDOWN = [
  ["Historical note-text patterns", "ML feature", "Prediction"],
  ["Department and explicit procedure", "ML feature", "Context"],
  ["Repeat-visit pattern", "ML feature", "Continuity"],
  ["Renal / oncology / neuro flags", "ML feature", "Specialty"],
  ["Emergency keywords in notes", "Rule override", "Escalation"],
  ["ICU probability above threshold", "Rule override", "Safety"],
  ["High-risk progression language", "Rule override", "Validation"],
  ["LLM rationale and source mapping", "Explanation", "Transparency"],
];

const AGENTIC_STEPS = [
  "Clinical Analyst",
  "Risk Scorer",
  "Pathway Planner",
  "Operational Summarizer",
];

const ARCHITECTURE_COMPARISON = [
  {
    title: "Old",
    detail:
      "Rules calculated risk, ML forecast operational signals, and LLM mainly explained or enriched selected cases.",
    tone: "bg-slate-50 border-slate-200",
  },
  {
    title: "New",
    detail:
      "An on-demand LLM-first review calculates contextual risk for one selected patient, while ML baseline and rules validate, backstop, and cache the final payload.",
    tone: "bg-blue-50 border-blue-200",
  },
];

function ToneBadge({ children, tone = "slate" }) {
  const tones = {
    slate: "bg-slate-100 text-slate-700",
    blue: "bg-blue-100 text-blue-700",
    green: "bg-green-100 text-green-700",
    orange: "bg-orange-100 text-orange-700",
    red: "bg-red-100 text-red-700",
  };

  return (
    <span className={`rounded-full px-3 py-1 text-xs font-semibold ${tones[tone]}`}>
      {children}
    </span>
  );
}

export default function Architecture() {
  return (
    <div className="min-h-screen p-6">
      <div className="mb-6">
        <Link
          to="/dashboard"
          className="mb-4 inline-flex items-center gap-2 text-sm font-medium text-blue-600 hover:text-blue-700"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Dashboard
        </Link>
        <h1 className="text-4xl font-bold tracking-tight text-slate-900">
          System Architecture Diagram
        </h1>
        <p className="mt-2 max-w-3xl text-slate-600">
          This page explains how Docstribe moves from raw EMR-style records to
          predictive patient forecasts, AI-prioritized queues, explainable profiles, and operational
          dashboards.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-[1.2fr_0.8fr]">
        <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-xl font-semibold text-slate-900">
            Visual Pipeline
          </h2>
          <p className="mt-1 text-sm text-slate-500">
            Mermaid-style overview of the full data and AI flow.
          </p>

          <div className="mt-5 rounded-2xl border border-slate-200 bg-slate-950 p-5 text-sm text-slate-100">
            <pre className="overflow-x-auto whitespace-pre-wrap font-mono leading-7 text-slate-200">
{`graph TD
  A[EMR / Source Dataset]
  B[Preprocessing + Text Cleanup]
  C[Predictive ML Models]
  D[Rule Validation Layer]
  E[On-demand LLM Review]
  F[Cache + Merged Intelligence Payload]
  G[FastAPI API Layer]
  H[Dashboard / Patient Profile / PDF / Intake]

  A --> B --> C --> D
  D --> E --> F
  C --> F
  F --> G --> H`}
            </pre>
          </div>

          <div className="mt-6 space-y-4">
            {PIPELINE_STEPS.map((step, index) => {
              const Icon = step.icon;

              return (
                <div key={step.title} className="flex gap-4">
                  <div className="flex w-14 flex-col items-center">
                    <div className={`flex h-12 w-12 items-center justify-center rounded-2xl ${step.tone}`}>
                      <Icon className="h-5 w-5" />
                    </div>
                    {index < PIPELINE_STEPS.length - 1 ? (
                      <div className="mt-2 h-full w-px bg-slate-300" />
                    ) : null}
                  </div>
                  <div className="pb-6">
                    <p className="font-semibold text-slate-900">{step.title}</p>
                    <p className="mt-1 text-sm leading-6 text-slate-600">
                      {step.detail}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
        </section>

        <section className="rounded-3xl border border-slate-200 bg-slate-900 p-6 text-white shadow-sm">
          <h2 className="text-xl font-semibold">Hybrid AI Strategy</h2>
          <p className="mt-2 text-sm leading-6 text-slate-300">
            Predictive ML and rules handle the fast default path for the full
            patient list. When a team member needs deeper reasoning for one case,
            the patient profile can trigger an on-demand LLM-first review and
            then reuse the saved result from cache.
          </p>

          <div className="mt-5 space-y-4">
            <div className="rounded-2xl bg-white/10 p-4">
              <p className="font-semibold">All Patients</p>
              <p className="mt-2 text-sm text-slate-300">
                Risk, admission, bed, ICU, LOS, readmission, deferability, and
                revenue signals stay fast through the predictive ML and rule-based
                layer.
              </p>
            </div>
            <div className="rounded-2xl bg-white/10 p-4">
              <p className="font-semibold">One-patient LLM Review</p>
              <p className="mt-2 text-sm text-slate-300">
                The LLM becomes the main reasoning layer for a selected patient,
                then backend safety rules validate the output and cache the
                result for reuse.
              </p>
            </div>
            <div className="rounded-2xl bg-white/10 p-4">
              <p className="font-semibold">Operational Benefit</p>
              <p className="mt-2 text-sm text-slate-300">
                This keeps the whole system interactive for live intake prediction
                while reserving the most expensive explanation layer for the
                patients who matter most.
              </p>
            </div>
          </div>
        </section>
      </div>

      <section className="mt-6 rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-xl font-semibold text-slate-900">
          New Agentic Risk Workflow
        </h2>
        <p className="mt-1 text-sm text-slate-500">
          The new backend branch introduces a staged agent pipeline that separates
          extraction, risk scoring, pathway planning, and operational synthesis.
        </p>

        <div className="mt-5 grid grid-cols-1 gap-4 lg:grid-cols-4">
          {AGENTIC_STEPS.map((step, index) => (
            <div
              key={step}
              className="rounded-2xl border border-slate-200 bg-slate-50 p-4"
            >
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                Step {index + 1}
              </p>
              <p className="mt-2 font-semibold text-slate-900">{step}</p>
            </div>
          ))}
        </div>

        <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-2">
          {ARCHITECTURE_COMPARISON.map((item) => (
            <div
              key={item.title}
              className={`rounded-2xl border p-5 ${item.tone}`}
            >
              <p className="text-sm font-semibold uppercase tracking-wide text-slate-500">
                {item.title}
              </p>
              <p className="mt-2 text-sm leading-6 text-slate-700">{item.detail}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="mt-6 rounded-3xl border border-slate-200 bg-white shadow-sm">
        <div className="border-b border-slate-200 p-6">
          <h2 className="text-xl font-semibold text-slate-900">
            AI Output Mapping
          </h2>
          <p className="mt-1 text-sm text-slate-500">
            What each output means, where it comes from, and how the logic is
            derived.
          </p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="p-4">Field</th>
                <th className="p-4">Source</th>
                <th className="p-4">Logic</th>
                <th className="p-4">Confidence</th>
              </tr>
            </thead>
            <tbody>
              {OUTPUT_MAPPING.map((row) => (
                <tr key={row.field} className="border-t border-slate-100 hover:bg-slate-50">
                  <td className="p-4 font-semibold text-slate-900">{row.field}</td>
                  <td className="p-4 text-slate-600">{row.source}</td>
                  <td className="p-4 text-slate-700">{row.logic}</td>
                  <td className="p-4">
                    <ToneBadge
                      tone={
                        row.confidence === "High"
                          ? "green"
                          : row.confidence === "Medium"
                            ? "orange"
                            : "red"
                      }
                    >
                      {row.confidence}
                    </ToneBadge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <div className="mt-6 grid grid-cols-1 gap-6 xl:grid-cols-2">
        <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-xl font-semibold text-slate-900">
            Risk Scoring Factors
          </h2>
          <p className="mt-1 text-sm text-slate-500">
            High-acuity signals are weighted more strongly so the worklist stays
            clinically meaningful.
          </p>

          <div className="mt-5 space-y-3">
            {RISK_BREAKDOWN.map(([factor, score, category]) => (
              <div
                key={factor}
                className="flex items-center justify-between rounded-2xl border border-slate-100 bg-slate-50 px-4 py-3"
              >
                <div className="flex items-center gap-3">
                  <ToneBadge tone="blue">{category}</ToneBadge>
                  <p className="text-sm text-slate-800">{factor}</p>
                </div>
                <span className="rounded-full bg-slate-900 px-3 py-1 text-xs font-bold text-white">
                  {score}
                </span>
              </div>
            ))}
          </div>

          <div className="mt-5 grid grid-cols-2 gap-3">
            <div className="rounded-2xl bg-green-50 p-4 text-sm font-semibold text-green-700">
              0-3 to Low
            </div>
            <div className="rounded-2xl bg-yellow-50 p-4 text-sm font-semibold text-yellow-700">
              4-6 to Medium
            </div>
            <div className="rounded-2xl bg-orange-50 p-4 text-sm font-semibold text-orange-700">
              7-8 to High
            </div>
            <div className="rounded-2xl bg-red-50 p-4 text-sm font-semibold text-red-700">
              9-10 to Critical
            </div>
          </div>
        </section>

        <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-xl font-semibold text-slate-900">
            Demo Flow Alignment
          </h2>
          <p className="mt-1 text-sm text-slate-500">
            The architecture supports the four main demonstration flows in the
            assignment.
          </p>

          <div className="mt-5 space-y-4">
            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
              <p className="font-semibold text-slate-900">
                1. Dashboard Priority Review
              </p>
              <p className="mt-2 text-sm text-slate-600">
                Summary cards, quick filters, progression signals, revenue
                visibility, and cohort cards help staff identify whom to review
                first.
              </p>
            </div>
            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
              <p className="font-semibold text-slate-900">
                2. Patient Profile Decision Support
              </p>
              <p className="mt-2 text-sm text-slate-600">
                Risk, admission, procedure, evidence, history, timeline, and
                treatment plan are merged into one explainable patient view.
              </p>
            </div>
            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
              <p className="font-semibold text-slate-900">
                3. Department Analytics
              </p>
              <p className="mt-2 text-sm text-slate-600">
                Specialty pressure, ICU demand, emergency load, and departmental
                cohort mix can be reviewed at the command-center level.
              </p>
            </div>
            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
              <p className="font-semibold text-slate-900">
                4. PDF / Reporting / Traceability
              </p>
              <p className="mt-2 text-sm text-slate-600">
                Downloadable reports preserve evidence, validation, and AI
                recommendations for presentation and review.
              </p>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
