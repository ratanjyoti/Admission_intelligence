# Docstribe Admission Intelligence

Docstribe is a hospital intelligence demo that combines predictive admission forecasting, clinical explainability, operational bed planning, and department-level analytics in a single workflow. The project is designed to show how a clinical data pipeline can support both doctors and hospital operations teams through a modern React frontend and a FastAPI backend.

## Live Demo

*   **Frontend UI:** [admission-intelligence.vercel.app]([https://admission-intelligence.vercel.app/])
*   **Health Check API:** [admission-intelligence.vercel.app/api/health](https://vercel.app/api/health)


## Project Overview

The platform helps staff answer a few critical questions quickly:

- Which patients need the most urgent attention?
- Which admissions are likely to require ICU coordination?
- What evidence supports the AI recommendation?
- Which departments are generating the highest emergency and ICU demand?

## Problem Statement

Hospital teams often work across fragmented systems where risk, admission urgency, bed planning, and clinical notes are separated across multiple screens or spreadsheets. Docstribe brings those signals together into one interface so a care team can review:

- patient-level admission intelligence
- AI-supported evidence and validation
- operational bed demand
- department-level clinical pressure

## Architecture

```text
React + Vite frontend
        |
        v
FastAPI backend
        |
        v
Predictive ML layer
        |
        v
Operational intelligence and rule-validation layer
        |
        v
PostgreSQL LLM cache or local fallback cache
        |
        v
dashboard_patients.json + AI-generated patient intelligence
```

## Backend AI Engines

The backend pipeline and inference utilities are organized in `backend/inference/` and `backend/pipeline/`.

- `risk_engine.py`: patient risk scoring and severity classification
- `admission_engine.py`: admission urgency classification
- `bed_engine.py`: bed allocation recommendation logic
- `procedure_engine.py`: explicit and inferred procedure intelligence
- `patient_journey_engine.py`: visit history and progression tracking
- `traceability_engine.py`: AI evidence extraction and explainability
- `consistency_validation_engine.py`: validation and consistency checks
- `enhanced_intelligence_engine.py`: higher-level derived intelligence
- `ml_predictor.py`: predictive ML training, evaluation, model selection, confidence scoring, and live intake forecasting

## Features Implemented

- Dashboard with risk, admission, and bed distribution charts
- Operational command-center cards for high revenue cases, cannot-delay cases, high readmission risk, and surgical opportunities
- Worsening-patient quick view, disease cohort views for renal, oncology, cardiac, orthopedic, neurology, and respiratory groups, and revenue portfolio visibility
- Search, filters, pagination, CSV export, mini risk trends, revenue color coding, emergency pulse indicators, and procedure-confidence chips for the patient worklist
- Dashboard filters for risk, admission, bed, progression, department, cohort, revenue category, readmission risk, deferred time, and case type
- API-backed patient profile with printable and downloadable AI admission reports
- Clinical note search with preserved original text, AI-normalized summary, ICD-10 extraction, comorbidity extraction, symptom extraction, and structured history panels
- Explainable AI evidence, validation status, and clinician safety messaging
- Visual risk gauge, structured timeline, and traced AI priority drivers
- Department analytics with drill-down navigation back into the dashboard
- New-patient predictive intake page with ML forecasting and optional save-to-worklist flow
- Prescription PDF ingestion that auto-fills the intake form before predictive generation
- Global navbar with backend API health status and fallback awareness
- Graceful loading, error, and empty states across major pages

## Tech Stack

- Frontend: React, Vite, React Router, Tailwind utility classes, Recharts
- Backend: FastAPI, Uvicorn, Python data-service layer, and scikit-learn predictive models
- Persistent cache: PostgreSQL via SQLAlchemy
- Reporting: jsPDF and html2canvas for printable/downloadable admission reports
- Data: JSON-based patient intelligence dataset used through FastAPI endpoints
- Deployment targets: Vercel for frontend, Render for backend

## API Endpoints

Base URL in development is proxied through Vite to `http://127.0.0.1:8000`.

```http
GET /api/health
GET /api/patients
GET /api/patients/{patient_id}
GET /api/dashboard/summary
GET /api/dashboard/charts
POST /api/predict/patient
POST /api/patients/intake
POST /api/prescription/extract
```

Predictive model reports are generated at:

```text
backend/ml_models/metrics.json
backend/ml_models/metadata.json
```

Sample health response:

```json
{
  "status": "ok",
  "patients_loaded": 422,
  "llm_enabled": true,
  "ml_enabled": true,
  "ml_models_ready": true,
  "cache_backend": "postgres",
  "database_connected": true
}
```

## Screenshots

Dashboard

![Dashboard Preview](documentation/screenshots/dashboard-preview.svg)

Patient Profile

![Patient Profile Preview](documentation/screenshots/patient-profile-preview.svg)

Department Analytics

![Department Analytics Preview](documentation/screenshots/department-analytics-preview.svg)

## How to Run Locally

### 1. Backend

Create or activate the Python virtual environment, then install dependencies:

```bash
pip install -r requirements.txt
```

Run the FastAPI server:

```bash
uvicorn backend.main:app --reload
```

The backend will start on `http://127.0.0.1:8000`.

Optional LLM intelligence:

Create `backend/.env` from [backend/.env.example](backend/.env.example) and add:

```env
LLM_PROVIDER=groq
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile
ENABLE_LLM_INTELLIGENCE=true
DATABASE_URL=postgresql://postgres:password@localhost:5432/docstribe
LLM_CACHE_LIMIT=5
ENABLE_ML_PREDICTIONS=true
```

If you prefer OpenAI instead of Groq, switch `LLM_PROVIDER=openai` and use `OPENAI_API_KEY` plus `OPENAI_MODEL`.

If `DATABASE_URL` is set, cached LLM intelligence is stored in PostgreSQL and reused across restarts and redeploys. If it is not set, the backend falls back to the local JSON cache file.

By default, Docstribe uses rule-based intelligence for the full 422-patient dataset and reserves LLM enrichment for the top `10` priority patients only. You can change that cohort size with:

```env
LLM_PRIORITY_LIMIT=10
```

If you want to precompute cached LLM enrichment for the full dataset:

```bash
python backend/generate_llm_cache.py
```

If you want to pre-train the predictive models before serving live intake requests:

```bash
python backend/train_ml_models.py
```

This command now:

- trains the predictive models on the 422-patient historical dataset
- compares Logistic Regression, Random Forest, XGBoost, and LightGBM where available
- combines TF-IDF text features with structured clinical features
- saves evaluation metrics, confusion matrices, and model metadata for the demo

### 2. Frontend

Install frontend dependencies:

```bash
cd frontend
npm install
```

Start the Vite app:

```bash
npm run dev
```

The frontend will start on `http://127.0.0.1:5173`.

### 3. Local API Configuration

For local development, the frontend reads `frontend/.env`:

```env
VITE_API_BASE_URL=http://localhost:8000
```

If the backend is down, the dashboard and patient pages can still render from the public fallback JSON file. In that case, the navbar shows `Using Local Fallback` instead of `API Connected`.

The `New Patient Intake` page depends on the live backend because it uses the predictive ML endpoints and live POST requests.

## Deployment Steps

### 1. Deploy the backend on Render

- Create a new Render web service pointing to this repository
- Create a Render PostgreSQL database and copy its internal database URL
- Use `pip install -r requirements.txt` as the build command
- Use `uvicorn backend.main:app --host 0.0.0.0 --port $PORT` as the start command
- Set the health check path to `/api/health`
- Set backend environment variables:
- `LLM_PROVIDER=groq`
- `GROQ_API_KEY=...`
- `GROQ_MODEL=llama-3.3-70b-versatile`
- `ENABLE_LLM_INTELLIGENCE=true`
- `ENABLE_ML_PREDICTIONS=true`
- `DATABASE_URL=<render-postgres-internal-url>`
- `LLM_PRIORITY_LIMIT=10`
- Optionally set `LLM_CACHE_LIMIT=5` for a short trial run before caching all 422 patients
- Optionally run `python backend/train_ml_models.py` once during setup to avoid first-request training latency on the intake route
- Confirm `/api/health`, `/api/patients`, `/api/dashboard/summary`, and `/api/dashboard/charts` respond correctly after deploy
- Confirm `/api/health` shows `cache_backend: "postgres"`, `database_connected: true`, and the ML status fields

### 2. Deploy the frontend on Vercel

Set the environment variable before deploy:

```text
VITE_API_BASE_URL=https://your-render-backend-url
```

- Import the repository into Vercel and set:
- Root Directory: `frontend`
- Build Command: `npm run build`
- Output Directory: `dist`
- Keep `frontend/vercel.json` for SPA routing support
- After deploy, verify the navbar shows `API Connected` against the Render backend
- Verify `/intake/new-patient` can predict a new patient and optionally save that patient into the live worklist

If Vercel accidentally imports the repository root instead of the `frontend/` app, the root [vercel.json](C:/Users/LENOVO/Downloads/Docstribe/vercel.json:1) now points the build back to `frontend/`. The recommended setup is still to deploy the `frontend` directory directly.

## Verification

Frontend build:

```bash
cd frontend
npm run build
```

Backend smoke test:

```bash
python backend/smoke_test.py
```

## Reasoning and Assumptions

- [Reasoning and assumptions document](documentation/reasoning-assumptions.md)
- The project uses a hybrid architecture: ML for prediction, rules for validation and safety, and LLMs for explainability.
- The project still uses transparent heuristics for ICD-10 support, symptom extraction, comorbidity extraction, operational forecasting, and admission conversion scoring.
- All AI outputs are positioned as clinician-facing decision support rather than autonomous decision-making.

## Final Submission Checklist

- Frontend build passes with `npm run build`
- Backend smoke test passes with `python backend/smoke_test.py`
- Render backend responds to `/api/health`, `/api/patients`, `/api/dashboard/summary`, and `/api/dashboard/charts`
- Vercel frontend is configured with `VITE_API_BASE_URL=https://your-render-backend-url`
- Navbar shows `API Connected` against the deployed backend
- Dashboard, patient profile, PDF export, and analytics pages are all demo-tested

## Demo Walkthrough

- Dashboard
- Search and filter the patient worklist
- Highlight high revenue, cannot-delay, readmission-risk, and surgical-opportunity cards
- Export CSV
- Department Analytics
- Open a patient profile
- Show Why AI Gave This Priority
- Show Evidence and traceability
- Download PDF

## Demo Flows

### 1. Priority Command Center

- Open `/dashboard`
- Click `Critical Patients`, `Emergency Admissions`, `ICU Required`, or `High Revenue Cases`
- Show the focused worklist with urgency colors, emergency pulse, progression sparkline, revenue badges, and `View Profile`

### 2. Patient Decision Support

- Open a top-priority patient profile
- Show `AI Mode`, risk gauge, procedure confidence, operational forecast cards, timeline, and structured evidence
- Explain the difference between rule-based and selective LLM enrichment

### 3. Department Intelligence

- Open `/analytics/departments`
- Drill into a department to return to `/dashboard?department=...`
- Show ICU demand, critical load, and emergency admissions by specialty

### 4. Predictive Intake Workflow

- Open `/intake/new-patient`
- Optionally upload a prescription or discharge-note PDF to auto-fill diagnosis, history, investigations, medicines, advice, and procedure fields
- Enter a new unseen patient with diagnosis, clinical notes, history, investigations, and doctor advice
- Show ML-predicted risk, admission type, ICU probability, LOS, deferability, and revenue signal
- Highlight prediction confidence, LOS ranges, top contributing signals, and any rule-based validation overrides
- Save the predicted patient into the live worklist and open the generated patient profile

### 5. AI Architecture and Traceability

- Open `/architecture`
- Walk through the EMR -> predictive ML -> rule validation -> selective LLM enrichment -> API -> dashboard pipeline
- Show output mapping, risk factor breakdown, and how AI decisions are grounded in source evidence

## Known Limitations

- The demo uses a JSON dataset rather than a production database
- The patient source dataset is still JSON-backed; PostgreSQL is currently used for persistent LLM cache storage rather than as the primary patient system of record
- The predictive ML layer is trained on the available historical sample and uses the current dataset labels plus derived operational targets as a practical bootstrap, not a production-grade outcomes dataset
- Fallback JSON rendering is helpful for demos, but it is not a substitute for live backend monitoring
- Authentication, user roles, and audit trails are not yet implemented
- ICD-10 and structured clinical fields are heuristic extractions from semi-structured notes and should be clinician-validated
- If a configured LLM provider is available, patient-level clinical intelligence can be generated through the backend and cached
- The AI reasoning should remain clinician decision support only

## Future Improvements

- Move the primary patient source from JSON files into a transactional database service
- Add authentication and role-based views for clinicians and operations staff
- Expand exports into scheduled cohort reports and longitudinal department trend history
- Connect live EMR or HIS ingestion pipelines
- Add model monitoring, audit logs, and clinician feedback loops
