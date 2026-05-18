# Reasoning and Assumptions

## Purpose

Docstribe is a decision-support demo, not a production clinical decision engine. The goal is to make admission reasoning, operational prioritization, and traceability explicit enough for academic evaluation and hospital workflow demos.

## Why a hybrid approach was used

- The provided dataset is note-heavy and semi-structured.
- Explicit labels such as ICD-10, symptom lists, comorbidity lists, and past-history tables were not consistently present as separate columns.
- A deterministic rules layer was chosen so every derived field can be explained back to source text.
- A predictive ML layer was added so unseen intake patients can be forecast from historical patterns rather than only deterministic rules.

## Core assumptions

- When a keyword strongly maps to a chronic disease context, it can be used to infer a comorbidity panel entry.
- When diagnosis and history text contain clear disease phrases, a best-fit ICD-10 code can be proposed as a structured coding aid.
- Revenue, LOS, deferred time, readmission risk, no-show risk, and admission conversion probability are operational heuristics, not billing outputs.
- The predictive ML models are trained on the available historical sample and bootstrap some targets from the curated dataset plus derived operational labels because true longitudinal outcome labels are limited in the provided data.
- Disease cohorts such as `Renal`, `Oncology`, and `Cardiac` are grouping views for prioritization and reporting, not mutually exclusive diagnoses.
- AI recommendations are always decision-support only and must be clinically validated.

## How the new fields are derived

### ICD-10

- Derived from explicit diagnosis and history keywords.
- Best-fit mappings are intentionally conservative and capped to a short list.
- Source snippet and source section are preserved for review.

### Comorbidities

- Extracted using chronic disease keyword rules across diagnosis, clinical notes, vital remarks, and investigations.
- Each extracted comorbidity keeps source and evidence text.

### Possible symptoms

- Extracted from complaint-oriented language in history, physical remarks, and clinical notes.
- These are presented as `possible symptoms` because the source text is semi-structured.

### Structured history

- Built from:
- past conditions inferred from comorbidity extraction
- past procedures from surgery/procedure keywords
- medication history from medicine instructions
- family history from explicit `family history` phrases when present

### Admission conversion probability

- Heuristic score based on risk, admission type, bed type, worsening trend, readmission risk, no-show risk, deferability, and evidence density.
- It is intended to show operational likelihood, not a true predictive model.

### Predictive ML layer

- New unseen intake patients pass through a TF-IDF plus structured-feature ML pipeline that predicts risk, admission type, bed need, ICU probability, LOS, readmission risk, deferability, and revenue category.
- The training script saves evaluation reports, confusion matrices, LOS regression metrics, model version metadata, and selected-model comparisons under `backend/ml_models/`.
- The ML output is then validated by rules before being shown in the UI.
- LLM reasoning remains an explanation layer, not the primary prediction engine.

## Tradeoffs

- Rules are transparent and easy to defend in an assignment setting.
- They are less flexible than a trained clinical NLP model.
- Some codes and symptom labels are approximate best-fit interpretations of note text.

## Safety stance

- The UI includes a validation banner on the patient profile.
- Evidence is shown alongside AI reasoning wherever possible.
- Structured fields never replace the original clinical text; both are shown together for auditability.
