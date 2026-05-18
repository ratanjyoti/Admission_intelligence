import functools
import json
import math
import os
import uuid
import warnings
from copy import deepcopy
from datetime import datetime, timedelta
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import (
    RandomForestClassifier,
    RandomForestRegressor,
)
from sklearn.exceptions import ConvergenceWarning
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    r2_score,
    recall_score,
)
from sklearn.model_selection import (
    KFold,
    StratifiedKFold,
    cross_val_score,
    train_test_split,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder, MaxAbsScaler, OneHotEncoder
from sklearn.feature_extraction.text import TfidfVectorizer

try:
    from xgboost import XGBClassifier, XGBRegressor
except Exception:  # pragma: no cover - optional dependency
    XGBClassifier = None
    XGBRegressor = None

try:
    from lightgbm import LGBMClassifier, LGBMRegressor
except Exception:  # pragma: no cover - optional dependency
    LGBMClassifier = None
    LGBMRegressor = None

from backend.data_service import load_base_patients, save_live_patient
from backend.operational_intelligence import (
    CARDIAC_KEYWORDS,
    COMORBIDITY_RULES,
    INFECTION_KEYWORDS,
    MAJOR_PROCEDURE_KEYWORDS,
    NEURO_KEYWORDS,
    ONCOLOGY_KEYWORDS,
    ORTHOPEDIC_KEYWORDS,
    RENAL_KEYWORDS,
    RESPIRATORY_KEYWORDS,
    SURGICAL_KEYWORDS,
    SYMPTOM_RULES,
    build_rule_based_operational_payload,
    clean_text,
    collect_rule_matches,
    combine_patient_text,
    detect_signals,
    get_active_procedure,
    get_patient_identifier,
    lower_text,
    parse_progression_entries,
    patient_source_sections,
)


ROOT_DIR = Path(__file__).resolve().parent
MODEL_DIR = ROOT_DIR / "ml_models"
METADATA_PATH = MODEL_DIR / "metadata.json"
METRICS_PATH = MODEL_DIR / "metrics.json"

MODEL_VERSION = os.getenv("ML_MODEL_VERSION", "v2.0")
RANDOM_STATE = 42

TEXT_COLUMN = "clinical_text"
CATEGORICAL_COLUMNS = [
    "department",
    "customer_type",
    "primary_cohort",
    "procedure_bucket",
    "repeat_visit",
]
NUMERIC_COLUMNS = [
    "visit_count",
    "first_visit_risk_score",
    "red_flag_count",
    "symptom_count",
    "comorbidity_count",
    "medication_count",
    "history_surgery_count",
    "history_condition_count",
    "history_family_count",
    "investigation_count",
    "doctor_advice_length",
    "clinical_note_length",
    "text_length",
    "procedure_detected",
    "risk_score_rule",
    "risk_score_delta",
    "evidence_count",
    "has_emergency_keyword",
    "has_renal_keyword",
    "has_oncology_keyword",
    "has_neuro_keyword",
    "has_cardiac_keyword",
    "has_respiratory_keyword",
    "has_orthopedic_keyword",
    "has_infection_keyword",
    "has_major_procedure",
    "has_surgical_keyword",
    "has_refusal_keyword",
    "emergency_keyword_count",
    "renal_keyword_count",
    "oncology_keyword_count",
    "neuro_keyword_count",
    "cardiac_keyword_count",
    "respiratory_keyword_count",
    "orthopedic_keyword_count",
    "infection_keyword_count",
]

TARGET_PATHS = {
    "risk_category": MODEL_DIR / "risk_model.joblib",
    "admission_type": MODEL_DIR / "admission_model.joblib",
    "bed_type": MODEL_DIR / "bed_model.joblib",
    "icu_requirement": MODEL_DIR / "icu_model.joblib",
    "readmission_risk": MODEL_DIR / "readmission_model.joblib",
    "length_of_stay": MODEL_DIR / "los_model.joblib",
    "deferred_time": MODEL_DIR / "deferred_model.joblib",
    "revenue_category": MODEL_DIR / "revenue_model.joblib",
}

RISK_SCORE_BASE = {"Low": 2, "Medium": 5, "High": 7, "Critical": 9}
BED_RISK_BONUS = {"General": 0, "Suite": 0, "Daycare Bay": -1, "HDU": 1, "ICU": 2}
ADMISSION_RISK_BONUS = {"Elective": 0, "Urgent": 1, "Emergency": 2}

EMERGENCY_KEYWORDS = [
    "seizure",
    "status epilepticus",
    "shock",
    "unstable",
    "critical",
    "acute",
    "emergency",
    "breathlessness",
    "respiratory distress",
    "chest pain",
    "altered sensorium",
    "giddiness",
    "syncope",
    "bleeding",
    "hematemesis",
    "melena",
    "hypotension",
    "tachycardia",
    "desaturation",
    "vomiting",
]


def ml_feature_enabled():
    return os.getenv("ENABLE_ML_PREDICTIONS", "true").strip().lower() not in {
        "0",
        "false",
        "no",
        "off",
    }


def build_source_text(patient):
    clinical = patient.get("clinical", {})
    parts = [
        patient.get("department"),
        patient.get("doctorName"),
        patient.get("customerType"),
        get_active_procedure(patient),
        clinical.get("diagnosis"),
        clinical.get("clinicalNotes"),
        clinical.get("physicalRemarks"),
        clinical.get("vitalRemarks"),
        clinical.get("investigations"),
        clinical.get("doctorAdvice"),
        clinical.get("medicineDetails"),
    ]
    return clean_text(" ".join(clean_text(part) for part in parts if clean_text(part)))


def count_keyword_matches(text, keywords):
    normalized = lower_text(text)
    return sum(1 for keyword in keywords if keyword in normalized)


def get_first_visit_risk_score(patient):
    journey = patient.get("journey", {})
    direct_value = journey.get("firstVisitRiskScore")
    if direct_value not in {None, ""}:
        try:
            return float(direct_value)
        except (TypeError, ValueError):
            pass

    progression = parse_progression_entries(journey.get("riskProgression"))
    if progression:
        try:
            return float(progression[0].get("risk_score") or 0)
        except (TypeError, ValueError):
            return 0.0

    try:
        return float(patient.get("risk", {}).get("score") or 0)
    except (TypeError, ValueError):
        return 0.0


def derive_source_risk_score(patient, signals, clinical_intelligence):
    text = build_source_text(patient)
    visit_count = int(patient.get("journey", {}).get("visitCount") or 1)
    repeat_visit = clean_text(patient.get("journey", {}).get("repeatVisit"))
    symptoms = clinical_intelligence.get("possibleSymptoms") or []
    comorbidities = clinical_intelligence.get("comorbidities") or []
    score = 2

    emergency_hits = count_keyword_matches(text, EMERGENCY_KEYWORDS)
    score += min(3, emergency_hits)
    score += 1 if visit_count >= 3 else 0
    score += 1 if repeat_visit == "Yes" else 0
    score += 1 if len(symptoms) >= 3 else 0
    score += 1 if len(comorbidities) >= 3 else 0
    score += 1 if signals["renal"] or signals["cardiac"] or signals["neuro"] else 0
    score += 1 if signals["oncology"] or signals["major_procedure"] else 0

    return max(1, min(10, score))


def build_feature_row(patient, signals=None, rule_payload=None):
    signals = signals or detect_signals(patient)
    rule_payload = rule_payload or build_rule_based_operational_payload(patient, signals)
    clinical_intelligence = rule_payload.get("clinicalIntelligence", {})
    structured_history = clinical_intelligence.get("structuredHistory") or {}
    source_sections = patient_source_sections(patient)
    source_text = build_source_text(patient)
    combined_text = combine_patient_text(patient)
    first_visit_risk_score = get_first_visit_risk_score(patient)
    risk_score_rule = derive_source_risk_score(patient, signals, clinical_intelligence)
    visit_count = int(patient.get("journey", {}).get("visitCount") or 1)
    repeat_visit = "Yes" if clean_text(patient.get("journey", {}).get("repeatVisit")) == "Yes" else "No"
    symptoms = clinical_intelligence.get("possibleSymptoms") or []
    comorbidities = clinical_intelligence.get("comorbidities") or []
    medications = structured_history.get("medications") or []
    past_conditions = structured_history.get("pastConditions") or []
    past_surgeries = structured_history.get("pastSurgeries") or []
    family_history = structured_history.get("familyHistory") or []
    procedure_name = get_active_procedure(patient)
    investigations = clean_text(patient.get("clinical", {}).get("investigations"))
    doctor_advice = clean_text(patient.get("clinical", {}).get("doctorAdvice"))

    emergency_keyword_count = count_keyword_matches(source_text, EMERGENCY_KEYWORDS)
    renal_keyword_count = count_keyword_matches(source_text, RENAL_KEYWORDS)
    oncology_keyword_count = count_keyword_matches(source_text, ONCOLOGY_KEYWORDS)
    neuro_keyword_count = count_keyword_matches(source_text, NEURO_KEYWORDS)
    cardiac_keyword_count = count_keyword_matches(source_text, CARDIAC_KEYWORDS)
    respiratory_keyword_count = count_keyword_matches(source_text, RESPIRATORY_KEYWORDS)
    orthopedic_keyword_count = count_keyword_matches(source_text, ORTHOPEDIC_KEYWORDS)
    infection_keyword_count = count_keyword_matches(source_text, INFECTION_KEYWORDS)
    evidence_count = (
        len(symptoms)
        + len(comorbidities)
        + min(3, emergency_keyword_count)
        + sum(1 for flag in signals.values() if isinstance(flag, bool) and flag)
    )

    return {
        TEXT_COLUMN: source_text or combined_text,
        "department": clean_text(patient.get("department")) or "General Medicine",
        "customer_type": clean_text(patient.get("customerType")) or "Incoming",
        "primary_cohort": clinical_intelligence.get("primaryCohort") or "General Medicine",
        "procedure_bucket": procedure_name or "None documented",
        "repeat_visit": repeat_visit,
        "visit_count": visit_count,
        "first_visit_risk_score": round(first_visit_risk_score, 2),
        "red_flag_count": emergency_keyword_count,
        "symptom_count": len(symptoms),
        "comorbidity_count": len(comorbidities),
        "medication_count": len(medications),
        "history_surgery_count": len(past_surgeries),
        "history_condition_count": len(past_conditions),
        "history_family_count": len(family_history),
        "investigation_count": sum(1 for section in source_sections if section["title"] == "Investigations" and section["content"]),
        "doctor_advice_length": len(doctor_advice.split()),
        "clinical_note_length": len(clean_text(patient.get("clinical", {}).get("clinicalNotes")).split()),
        "text_length": len(source_text.split()),
        "procedure_detected": 1 if procedure_name else 0,
        "risk_score_rule": risk_score_rule,
        "risk_score_delta": round(max(0.0, risk_score_rule - first_visit_risk_score), 2),
        "evidence_count": evidence_count,
        "has_emergency_keyword": int(emergency_keyword_count > 0),
        "has_renal_keyword": int(signals["renal"]),
        "has_oncology_keyword": int(signals["oncology"]),
        "has_neuro_keyword": int(signals["neuro"]),
        "has_cardiac_keyword": int(signals["cardiac"]),
        "has_respiratory_keyword": int(signals["respiratory"]),
        "has_orthopedic_keyword": int(signals["orthopedic"]),
        "has_infection_keyword": int(signals["infection"]),
        "has_major_procedure": int(signals["major_procedure"]),
        "has_surgical_keyword": int(signals["surgical"]),
        "has_refusal_keyword": int(signals["refusal"]),
        "emergency_keyword_count": emergency_keyword_count,
        "renal_keyword_count": renal_keyword_count,
        "oncology_keyword_count": oncology_keyword_count,
        "neuro_keyword_count": neuro_keyword_count,
        "cardiac_keyword_count": cardiac_keyword_count,
        "respiratory_keyword_count": respiratory_keyword_count,
        "orthopedic_keyword_count": orthopedic_keyword_count,
        "infection_keyword_count": infection_keyword_count,
    }


def extract_targets(patient, rule_payload):
    los_payload = rule_payload.get("lengthOfStay") or {}
    min_days = float(los_payload.get("minDays") or 0)
    max_days = float(los_payload.get("maxDays") or 0)
    los_midpoint = 0.0 if max_days == 0 else round((min_days + max_days) / 2, 2)
    return {
        "risk_category": clean_text(patient.get("risk", {}).get("category")) or "Medium",
        "admission_type": clean_text(patient.get("admission", {}).get("type")) or "Elective",
        "bed_type": clean_text(patient.get("bed", {}).get("type")) or "General",
        "icu_requirement": "ICU" if clean_text(patient.get("bed", {}).get("type")) == "ICU" else "Not ICU",
        "readmission_risk": clean_text(rule_payload.get("readmissionRisk", {}).get("label")) or "Low",
        "length_of_stay": los_midpoint,
        "deferred_time": clean_text(rule_payload.get("deferredTime", {}).get("label")) or "1-2 weeks acceptable",
        "revenue_category": clean_text(rule_payload.get("packageIntelligence", {}).get("revenueCategory")) or "Standard Value",
    }


def prepare_training_frame():
    rows = []
    targets = {name: [] for name in TARGET_PATHS}

    for patient in load_base_patients():
        signals = detect_signals(patient)
        rule_payload = build_rule_based_operational_payload(patient, signals)
        rows.append(build_feature_row(patient, signals=signals, rule_payload=rule_payload))
        extracted_targets = extract_targets(patient, rule_payload)
        for target_name, target_value in extracted_targets.items():
            targets[target_name].append(target_value)

    return pd.DataFrame(rows), targets


def build_preprocessor():
    return ColumnTransformer(
        transformers=[
            (
                "text",
                TfidfVectorizer(
                    max_features=1800,
                    ngram_range=(1, 2),
                    min_df=2,
                    sublinear_tf=True,
                ),
                TEXT_COLUMN,
            ),
            (
                "categorical",
                Pipeline(
                    steps=[
                        ("imputer", SimpleImputer(strategy="constant", fill_value="Unknown")),
                        ("onehot", OneHotEncoder(handle_unknown="ignore")),
                    ]
                ),
                CATEGORICAL_COLUMNS,
            ),
            (
                "numeric",
                Pipeline(
                    steps=[
                        ("imputer", SimpleImputer(strategy="constant", fill_value=0)),
                        ("scaler", MaxAbsScaler()),
                    ]
                ),
                NUMERIC_COLUMNS,
            ),
        ],
        sparse_threshold=0.3,
    )


def build_classifier_candidates(class_count):
    candidates = {
        "logistic_regression": LogisticRegression(
            max_iter=2400,
            class_weight="balanced",
            random_state=RANDOM_STATE,
        ),
        "random_forest": RandomForestClassifier(
            n_estimators=220,
            class_weight="balanced_subsample",
            random_state=RANDOM_STATE,
            n_jobs=-1,
        ),
    }

    if XGBClassifier is not None:
        xgb_kwargs = {
            "n_estimators": 180,
            "max_depth": 5,
            "learning_rate": 0.08,
            "subsample": 0.9,
            "colsample_bytree": 0.9,
            "random_state": RANDOM_STATE,
            "n_jobs": 4,
            "eval_metric": "mlogloss" if class_count > 2 else "logloss",
        }
        if class_count > 2:
            xgb_kwargs.update({"objective": "multi:softprob", "num_class": class_count})
        else:
            xgb_kwargs.update({"objective": "binary:logistic"})
        candidates["xgboost"] = XGBClassifier(**xgb_kwargs)

    if LGBMClassifier is not None:
        objective = "multiclass" if class_count > 2 else "binary"
        candidates["lightgbm"] = LGBMClassifier(
            n_estimators=220,
            learning_rate=0.08,
            num_leaves=31,
            class_weight="balanced",
            objective=objective,
            random_state=RANDOM_STATE,
            verbosity=-1,
        )

    return candidates


def build_regressor_candidates():
    candidates = {
        "ridge": Ridge(alpha=1.0),
        "random_forest": RandomForestRegressor(
            n_estimators=220,
            random_state=RANDOM_STATE,
            n_jobs=-1,
        ),
    }

    if XGBRegressor is not None:
        candidates["xgboost"] = XGBRegressor(
            n_estimators=180,
            max_depth=5,
            learning_rate=0.08,
            subsample=0.9,
            colsample_bytree=0.9,
            random_state=RANDOM_STATE,
            n_jobs=4,
            objective="reg:squarederror",
            eval_metric="mae",
        )

    if LGBMRegressor is not None:
        candidates["lightgbm"] = LGBMRegressor(
            n_estimators=220,
            learning_rate=0.08,
            num_leaves=31,
            random_state=RANDOM_STATE,
            verbosity=-1,
        )

    return candidates


def safe_float(value):
    try:
        return round(float(value), 4)
    except (TypeError, ValueError):
        return 0.0


def can_stratify(labels):
    unique_labels, counts = np.unique(labels, return_counts=True)
    return len(unique_labels) > 1 and counts.min() >= 2


def classification_cv_splits(labels):
    if len(labels) < 6:
        return None
    _, counts = np.unique(labels, return_counts=True)
    split_count = min(5, counts.min())
    if split_count < 2:
        return None
    return StratifiedKFold(n_splits=split_count, shuffle=True, random_state=RANDOM_STATE)


def regression_cv_splits(size):
    split_count = min(5, size)
    if split_count < 2:
        return None
    return KFold(n_splits=split_count, shuffle=True, random_state=RANDOM_STATE)


def fit_pipeline(pipeline, X_train, y_train):
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=ConvergenceWarning)
        warnings.filterwarnings("ignore", category=UserWarning)
        pipeline.fit(X_train, y_train)


def evaluate_classification_task(task_name, frame, labels):
    encoder = LabelEncoder()
    y = encoder.fit_transform(labels)
    stratify_labels = y if can_stratify(y) else None
    X_train, X_test, y_train, y_test = train_test_split(
        frame,
        y,
        test_size=0.2,
        random_state=RANDOM_STATE,
        stratify=stratify_labels,
    )

    candidate_results = []
    best_result = None

    for model_name, estimator in build_classifier_candidates(len(encoder.classes_)).items():
        pipeline = Pipeline(
            steps=[
                ("preprocessor", build_preprocessor()),
                ("model", clone(estimator)),
            ]
        )
        fit_pipeline(pipeline, X_train, y_train)
        predictions = pipeline.predict(X_test)
        result = {
            "model": model_name,
            "accuracy": safe_float(accuracy_score(y_test, predictions)),
            "precision_macro": safe_float(
                precision_score(y_test, predictions, average="macro", zero_division=0)
            ),
            "recall_macro": safe_float(
                recall_score(y_test, predictions, average="macro", zero_division=0)
            ),
            "f1_macro": safe_float(
                f1_score(y_test, predictions, average="macro", zero_division=0)
            ),
        }
        candidate_results.append(result)
        if best_result is None or result["f1_macro"] > best_result["metrics"]["f1_macro"]:
            best_result = {"model_name": model_name, "pipeline": pipeline, "metrics": result}

    best_pipeline = best_result["pipeline"]
    y_pred = best_pipeline.predict(X_test)
    labels_raw = encoder.inverse_transform(np.arange(len(encoder.classes_)))
    y_test_raw = encoder.inverse_transform(y_test)
    y_pred_raw = encoder.inverse_transform(y_pred)
    cv = classification_cv_splits(y)
    cv_scores = []
    if cv is not None:
        cv_scores = cross_val_score(
            best_pipeline,
            frame,
            y,
            cv=cv,
            scoring="f1_macro",
            n_jobs=1,
        ).tolist()

    report = classification_report(
        y_test_raw,
        y_pred_raw,
        labels=list(labels_raw),
        zero_division=0,
        output_dict=True,
    )

    metrics = {
        "task_type": "classification",
        "selected_model": best_result["model_name"],
        "holdout_metrics": {
            "accuracy": safe_float(accuracy_score(y_test_raw, y_pred_raw)),
            "precision_macro": safe_float(
                precision_score(y_test_raw, y_pred_raw, average="macro", zero_division=0)
            ),
            "recall_macro": safe_float(
                recall_score(y_test_raw, y_pred_raw, average="macro", zero_division=0)
            ),
            "f1_macro": safe_float(
                f1_score(y_test_raw, y_pred_raw, average="macro", zero_division=0)
            ),
            "precision_weighted": safe_float(
                precision_score(y_test_raw, y_pred_raw, average="weighted", zero_division=0)
            ),
            "recall_weighted": safe_float(
                recall_score(y_test_raw, y_pred_raw, average="weighted", zero_division=0)
            ),
            "f1_weighted": safe_float(
                f1_score(y_test_raw, y_pred_raw, average="weighted", zero_division=0)
            ),
        },
        "confusion_matrix": {
            "labels": list(labels_raw),
            "matrix": confusion_matrix(
                y_test_raw,
                y_pred_raw,
                labels=list(labels_raw),
            ).tolist(),
        },
        "classification_report": report,
        "cross_validation": {
            "folds": [safe_float(score) for score in cv_scores],
            "f1_macro_mean": safe_float(np.mean(cv_scores)) if cv_scores else 0.0,
            "f1_macro_std": safe_float(np.std(cv_scores)) if cv_scores else 0.0,
        },
        "candidate_results": candidate_results,
        "split": {"train_rows": int(len(X_train)), "test_rows": int(len(X_test))},
    }

    artifact = {
        "task_name": task_name,
        "task_type": "classification",
        "pipeline": best_pipeline,
        "label_encoder": encoder,
        "selected_model": best_result["model_name"],
        "labels": list(labels_raw),
    }
    return artifact, metrics


def evaluate_regression_task(task_name, frame, values):
    target = np.asarray(values, dtype=float)
    X_train, X_test, y_train, y_test = train_test_split(
        frame,
        target,
        test_size=0.2,
        random_state=RANDOM_STATE,
    )

    candidate_results = []
    best_result = None

    for model_name, estimator in build_regressor_candidates().items():
        pipeline = Pipeline(
            steps=[
                ("preprocessor", build_preprocessor()),
                ("model", clone(estimator)),
            ]
        )
        fit_pipeline(pipeline, X_train, y_train)
        predictions = pipeline.predict(X_test)
        result = {
            "model": model_name,
            "mae": safe_float(mean_absolute_error(y_test, predictions)),
            "r2": safe_float(r2_score(y_test, predictions)),
            "rmse": safe_float(math.sqrt(mean_squared_error(y_test, predictions))),
        }
        candidate_results.append(result)
        if best_result is None or result["mae"] < best_result["metrics"]["mae"]:
            best_result = {"model_name": model_name, "pipeline": pipeline, "metrics": result}

    best_pipeline = best_result["pipeline"]
    y_pred = best_pipeline.predict(X_test)
    cv = regression_cv_splits(len(frame))
    cv_scores = []
    if cv is not None:
        cv_scores = (-cross_val_score(
            best_pipeline,
            frame,
            target,
            cv=cv,
            scoring="neg_mean_absolute_error",
            n_jobs=1,
        )).tolist()

    metrics = {
        "task_type": "regression",
        "selected_model": best_result["model_name"],
        "holdout_metrics": {
            "mae": safe_float(mean_absolute_error(y_test, y_pred)),
            "r2": safe_float(r2_score(y_test, y_pred)),
            "rmse": safe_float(math.sqrt(mean_squared_error(y_test, y_pred))),
        },
        "cross_validation": {
            "folds_mae": [safe_float(score) for score in cv_scores],
            "mae_mean": safe_float(np.mean(cv_scores)) if cv_scores else 0.0,
            "mae_std": safe_float(np.std(cv_scores)) if cv_scores else 0.0,
        },
        "candidate_results": candidate_results,
        "split": {"train_rows": int(len(X_train)), "test_rows": int(len(X_test))},
    }

    artifact = {
        "task_name": task_name,
        "task_type": "regression",
        "pipeline": best_pipeline,
        "selected_model": best_result["model_name"],
    }
    return artifact, metrics


def train_and_save_models():
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    frame, targets = prepare_training_frame()
    metrics_payload = {
        "model_version": MODEL_VERSION,
        "trained_on": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "training_rows": int(len(frame)),
        "targets": {},
    }

    metadata_payload = {
        "model_version": MODEL_VERSION,
        "trained_on": metrics_payload["trained_on"],
        "training_rows": int(len(frame)),
        "features": {
            "text": [TEXT_COLUMN],
            "categorical": CATEGORICAL_COLUMNS,
            "numeric": NUMERIC_COLUMNS,
        },
        "targets": list(TARGET_PATHS.keys()),
        "selected_models": {},
    }

    for target_name, path in TARGET_PATHS.items():
        if target_name == "length_of_stay":
            artifact, metrics = evaluate_regression_task(target_name, frame, targets[target_name])
        else:
            artifact, metrics = evaluate_classification_task(target_name, frame, targets[target_name])

        joblib.dump(artifact, path)
        metrics_payload["targets"][target_name] = metrics
        metadata_payload["selected_models"][target_name] = metrics["selected_model"]

    METADATA_PATH.write_text(
        json.dumps(metadata_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    METRICS_PATH.write_text(
        json.dumps(metrics_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    _load_artifact.cache_clear()
    _load_json.cache_clear()
    return metadata_payload


def ml_models_ready():
    return METADATA_PATH.exists() and METRICS_PATH.exists() and all(
        path.exists() for path in TARGET_PATHS.values()
    )


def ensure_models_ready(force_retrain=False):
    if force_retrain or not ml_models_ready():
        train_and_save_models()


@functools.lru_cache(maxsize=2)
def _load_json(path_string):
    path = Path(path_string)
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


@functools.lru_cache(maxsize=len(TARGET_PATHS))
def _load_artifact(task_name):
    return joblib.load(TARGET_PATHS[task_name])


def load_metadata():
    return _load_json(str(METADATA_PATH))


def load_metrics():
    return _load_json(str(METRICS_PATH))


def explain_feature_signals(patient, feature_row, rule_payload=None):
    rule_payload = rule_payload or build_rule_based_operational_payload(patient, detect_signals(patient))
    department = feature_row["department"]
    signals = []

    if feature_row["has_emergency_keyword"]:
        signals.append("Emergency or acute-deterioration language was found in the clinical narrative.")
    if feature_row["has_renal_keyword"]:
        signals.append("Renal dysfunction and creatinine-related signals raise acuity and monitoring needs.")
    if feature_row["has_cardiac_keyword"]:
        signals.append("Cardiac symptoms or department context increase monitored-admission probability.")
    if feature_row["has_neuro_keyword"]:
        signals.append("Neurology or seizure-related evidence points toward escalation risk.")
    if feature_row["has_oncology_keyword"]:
        signals.append("Oncology burden increases complexity, readmission pressure, and package value.")
    if feature_row["repeat_visit"] == "Yes":
        signals.append("Repeat-visit history suggests unresolved disease progression.")
    if feature_row["visit_count"] >= 3:
        signals.append("Multiple documented encounters indicate a persistent clinical pathway.")
    if feature_row["procedure_detected"]:
        signals.append("A documented procedure increases conversion, revenue, and length-of-stay expectations.")
    if feature_row["comorbidity_count"] >= 3:
        signals.append("A higher comorbidity burden increases risk, LOS, and readmission pressure.")
    if feature_row["symptom_count"] >= 3:
        signals.append("Multiple symptoms increase urgency and admission likelihood.")
    if department:
        signals.append(f"Department context ({department}) contributes specialty-specific prior patterns.")
    if rule_payload.get("clinicalIntelligence", {}).get("primaryIcd10"):
        primary_icd = rule_payload["clinicalIntelligence"]["primaryIcd10"]
        signals.append(f"Primary disease mapping suggests {primary_icd.get('label', 'specialty complexity')}.")

    deduped = []
    for signal in signals:
        if signal not in deduped:
            deduped.append(signal)
    return deduped[:8]


def task_signals(feature_row, all_signals):
    mappings = {
        "risk_category": [
            "Emergency or acute-deterioration language was found in the clinical narrative.",
            "Renal dysfunction and creatinine-related signals raise acuity and monitoring needs.",
            "Neurology or seizure-related evidence points toward escalation risk.",
            "Repeat-visit history suggests unresolved disease progression.",
            "Multiple symptoms increase urgency and admission likelihood.",
        ],
        "admission_type": [
            "Emergency or acute-deterioration language was found in the clinical narrative.",
            "Multiple symptoms increase urgency and admission likelihood.",
            "A documented procedure increases conversion, revenue, and length-of-stay expectations.",
            "Repeat-visit history suggests unresolved disease progression.",
        ],
        "bed_type": [
            "Emergency or acute-deterioration language was found in the clinical narrative.",
            "Renal dysfunction and creatinine-related signals raise acuity and monitoring needs.",
            "A documented procedure increases conversion, revenue, and length-of-stay expectations.",
        ],
        "icu_requirement": [
            "Emergency or acute-deterioration language was found in the clinical narrative.",
            "Renal dysfunction and creatinine-related signals raise acuity and monitoring needs.",
            "Neurology or seizure-related evidence points toward escalation risk.",
        ],
        "readmission_risk": [
            "Repeat-visit history suggests unresolved disease progression.",
            "A higher comorbidity burden increases risk, LOS, and readmission pressure.",
            "Multiple documented encounters indicate a persistent clinical pathway.",
        ],
        "deferred_time": [
            "Emergency or acute-deterioration language was found in the clinical narrative.",
            "Repeat-visit history suggests unresolved disease progression.",
            "Renal dysfunction and creatinine-related signals raise acuity and monitoring needs.",
        ],
        "revenue_category": [
            "A documented procedure increases conversion, revenue, and length-of-stay expectations.",
            "Oncology burden increases complexity, readmission pressure, and package value.",
            "Renal dysfunction and creatinine-related signals raise acuity and monitoring needs.",
        ],
    }
    preferred = mappings.get(feature_row.get("_task_name"), [])
    ranked = [signal for signal in preferred if signal in all_signals]
    if len(ranked) < 4:
        ranked.extend(signal for signal in all_signals if signal not in ranked)
    return ranked[:4]


def predict_classification(artifact, frame):
    pipeline = artifact["pipeline"]
    encoder = artifact["label_encoder"]
    estimator = pipeline.named_steps["model"]
    class_ids = getattr(estimator, "classes_", np.arange(len(encoder.classes_)))
    probabilities = pipeline.predict_proba(frame)[0]
    predicted_encoded = int(pipeline.predict(frame)[0])
    predicted_label = encoder.inverse_transform([predicted_encoded])[0]
    probability_map = {
        encoder.inverse_transform([int(class_id)])[0]: safe_float(probability)
        for class_id, probability in zip(class_ids, probabilities)
    }
    return {
        "label": predicted_label,
        "confidence": safe_float(probability_map[predicted_label]),
        "probabilities": probability_map,
    }


def predict_regression(artifact, frame):
    prediction = float(artifact["pipeline"].predict(frame)[0])
    prediction = max(0.0, prediction)
    regression_metrics = load_metrics().get("targets", {}).get("length_of_stay", {})
    mae = regression_metrics.get("holdout_metrics", {}).get("mae") or 1.0
    low_days = max(0, int(math.floor(max(0.0, prediction - mae))))
    high_days = max(low_days, int(math.ceil(prediction + mae)))
    if prediction < 0.5:
        label = "Not applicable - Daycare / Same-day"
    else:
        label = f"{low_days} - {high_days} days"
    return {
        "predictedDays": round(prediction, 1),
        "lowDays": low_days,
        "expectedDays": max(low_days, int(round(prediction))),
        "highDays": high_days,
        "label": label,
        "mae": safe_float(mae),
    }


def validate_predictive_payload(patient, predictive_payload, feature_row):
    validation_summary = []
    risk = predictive_payload["riskCategory"]
    admission = predictive_payload["admissionType"]
    bed = predictive_payload["bedType"]
    icu = predictive_payload["icuRequirement"]
    risk_score_rule = feature_row["risk_score_rule"]

    for prediction in (risk, admission, bed):
        prediction.setdefault("modelLabel", prediction.get("label"))
        prediction.setdefault("modelConfidence", prediction.get("confidence"))

    if feature_row["has_emergency_keyword"] and admission["label"] == "Elective":
        admission["label"] = "Urgent"
        admission["confidence"] = 0.68
        if "admissionLikelihood" in predictive_payload:
            predictive_payload["admissionLikelihood"]["probability"] = 0.68
            predictive_payload["admissionLikelihood"]["confidence"] = 0.68
            predictive_payload["admissionLikelihood"]["label"] = "Moderate likelihood"
        validation_summary.append(
            "Admission pathway escalated from Elective to Urgent because emergency language was detected."
        )

    if feature_row["has_neuro_keyword"] and "seizure" in build_source_text(patient) and bed["label"] not in {"ICU", "HDU"}:
        bed["label"] = "ICU"
        bed["confidence"] = 0.78
        icu["label"] = "ICU"
        icu["probability"] = max(icu["probability"], 0.72)
        if "emergencyEscalation" in predictive_payload:
            predictive_payload["emergencyEscalation"]["probability"] = max(
                predictive_payload["emergencyEscalation"].get("probability") or 0.0,
                0.72,
            )
            predictive_payload["emergencyEscalation"]["confidence"] = predictive_payload["emergencyEscalation"]["probability"]
            predictive_payload["emergencyEscalation"]["label"] = "Escalation likely"
        validation_summary.append(
            "Bed requirement escalated to ICU because seizure/neurology evidence suggests monitored care."
        )

    if risk_score_rule >= 8 and risk["label"] in {"Low", "Medium"}:
        risk["label"] = "High"
        risk["confidence"] = 0.72
        validation_summary.append(
            "Risk category was raised because the structured rule score detected high-acuity source signals."
        )

    if feature_row["has_emergency_keyword"] and risk["label"] != "Critical" and feature_row["red_flag_count"] >= 2:
        risk["label"] = "Critical"
        risk["confidence"] = 0.8
        if "emergencyEscalation" in predictive_payload:
            predictive_payload["emergencyEscalation"]["probability"] = max(
                predictive_payload["emergencyEscalation"].get("probability") or 0.0,
                0.8,
            )
            predictive_payload["emergencyEscalation"]["confidence"] = predictive_payload["emergencyEscalation"]["probability"]
            predictive_payload["emergencyEscalation"]["label"] = "Escalation likely"
        validation_summary.append(
            "Risk category was escalated to Critical because multiple emergency red flags were present."
        )

    if bed["label"] == "ICU":
        icu["probability"] = max(icu["probability"], 0.85)

    predictive_payload["validationSummary"] = validation_summary
    return predictive_payload


def build_predictive_payload(patient):
    ensure_models_ready()
    feature_row = build_feature_row(patient)
    frame = pd.DataFrame([feature_row])
    metadata = load_metadata()
    rule_payload = build_rule_based_operational_payload(patient, detect_signals(patient))
    explanation_signals = explain_feature_signals(patient, feature_row, rule_payload=rule_payload)

    predictions = {}
    for task_name in TARGET_PATHS:
        artifact = _load_artifact(task_name)
        if artifact["task_type"] == "classification":
            prediction = predict_classification(artifact, frame)
        else:
            prediction = predict_regression(artifact, frame)

        feature_row["_task_name"] = task_name
        prediction["topSignals"] = task_signals(feature_row, explanation_signals)
        predictions[task_name] = prediction

    admission_probabilities = predictions["admission_type"]["probabilities"]
    admission_likelihood = max(
        admission_probabilities.get("Emergency", 0.0),
        admission_probabilities.get("Urgent", 0.0),
    )
    emergency_escalation = max(
        admission_probabilities.get("Emergency", 0.0),
        predictions["icu_requirement"]["probabilities"].get("ICU", 0.0),
        predictions["risk_category"]["probabilities"].get("Critical", 0.0),
    )

    predictive_payload = {
        "enabled": True,
        "modelVersion": metadata.get("model_version", MODEL_VERSION),
        "trainedOn": metadata.get("trained_on"),
        "riskCategory": predictions["risk_category"],
        "admissionType": predictions["admission_type"],
        "bedType": predictions["bed_type"],
        "icuRequirement": {
            "label": predictions["icu_requirement"]["label"],
            "confidence": predictions["icu_requirement"]["confidence"],
            "probability": predictions["icu_requirement"]["probabilities"].get("ICU", 0.0),
            "probabilities": predictions["icu_requirement"]["probabilities"],
            "topSignals": predictions["icu_requirement"]["topSignals"],
        },
        "readmissionRisk": predictions["readmission_risk"],
        "lengthOfStay": predictions["length_of_stay"],
        "deferredTime": predictions["deferred_time"],
        "revenueCategory": predictions["revenue_category"],
        "admissionLikelihood": {
            "label": "High likelihood" if admission_likelihood >= 0.75 else "Moderate likelihood" if admission_likelihood >= 0.5 else "Lower likelihood",
            "confidence": safe_float(admission_likelihood),
            "probability": safe_float(admission_likelihood),
            "topSignals": predictions["admission_type"]["topSignals"],
        },
        "emergencyEscalation": {
            "label": "Escalation likely" if emergency_escalation >= 0.7 else "Watch closely" if emergency_escalation >= 0.45 else "Lower escalation risk",
            "confidence": safe_float(emergency_escalation),
            "probability": safe_float(emergency_escalation),
            "topSignals": predictions["risk_category"]["topSignals"],
        },
        "topSignals": explanation_signals[:6],
        "featureSummary": {
            "department": feature_row["department"],
            "repeatVisit": feature_row["repeat_visit"],
            "visitCount": feature_row["visit_count"],
            "ruleRiskScore": feature_row["risk_score_rule"],
            "comorbidityCount": feature_row["comorbidity_count"],
            "symptomCount": feature_row["symptom_count"],
            "evidenceCount": feature_row["evidence_count"],
        },
        "selectedModels": metadata.get("selected_models", {}),
        "validationSummary": [],
    }
    return validate_predictive_payload(patient, predictive_payload, feature_row)


def maybe_predict_patient_ml(patient):
    if not ml_feature_enabled():
        return {"enabled": False, "reason": "Predictive ML disabled"}
    try:
        return build_predictive_payload(patient)
    except Exception as exc:  # pragma: no cover - graceful runtime fallback
        return {"enabled": False, "reason": f"Predictive ML unavailable: {exc}"}


def derive_predicted_risk_score(predictive_payload, patient):
    risk_label = predictive_payload["riskCategory"]["label"]
    confidence = predictive_payload["riskCategory"].get("confidence") or 0.5
    base_score = RISK_SCORE_BASE.get(risk_label, 5)
    source_rule_score = build_feature_row(patient)["risk_score_rule"]
    score = max(base_score, round(source_rule_score * 0.6 + base_score * 0.4 + confidence))
    return int(max(1, min(10, score)))


def apply_ml_predictions_to_patient(patient, predictive_payload):
    patient = deepcopy(patient)
    predicted_risk_score = derive_predicted_risk_score(predictive_payload, patient)
    risk_label = predictive_payload["riskCategory"]["label"]
    admission_label = predictive_payload["admissionType"]["label"]
    bed_label = predictive_payload["bedType"]["label"]
    top_signals = predictive_payload.get("topSignals") or []
    journey = patient.setdefault("journey", {})

    patient["predictiveModeling"] = predictive_payload
    patient["risk"] = {
        "score": predicted_risk_score,
        "category": risk_label,
        "reasoning": (
            f"ML predicted {risk_label} risk with {round((predictive_payload['riskCategory'].get('confidence') or 0) * 100)}% confidence. "
            f"Top signals: {'; '.join(top_signals[:3]) or 'source clinical context.'}"
        ),
        "redFlags": str(top_signals[:3]),
    }
    patient["admission"] = {
        "type": admission_label,
        "reasoning": (
            f"Predicted through the ML admission classifier with {round((predictive_payload['admissionType'].get('confidence') or 0) * 100)}% confidence."
        ),
        "summary": f"Predicted admission pathway: {admission_label}.",
    }
    patient["bed"] = {
        "type": bed_label,
        "reasoning": (
            f"Predicted bed type from combined text and structured features with {round((predictive_payload['bedType'].get('confidence') or 0) * 100)}% confidence."
        ),
        "summary": f"Predicted bed planning: {bed_label}.",
    }

    first_visit_score = float(journey.get("firstVisitRiskScore") or 0)
    if first_visit_score:
        if predicted_risk_score > first_visit_score:
            progression_trend = "Worsening"
        elif predicted_risk_score < first_visit_score:
            progression_trend = "Improving"
        else:
            progression_trend = "Stable"
    else:
        progression_trend = "New intake"

    journey["progressionTrend"] = progression_trend
    journey["repeatVisit"] = "Yes" if clean_text(journey.get("repeatVisit")) == "Yes" else "No"

    evidence_count = build_feature_row(patient)["evidence_count"]
    patient["traceability"] = {
        "evidenceCount": evidence_count,
        "summary": "Predictive ML used text plus structured clinical features for this intake preview.",
        "safetyNote": "AI-assisted prediction. Final admission decision requires clinician validation.",
        "sourceSections": str([section["title"] for section in patient_source_sections(patient) if section["content"]]),
        "evidenceTrace": str(top_signals),
    }
    patient["validation"] = {
        "status": "Validated" if predictive_payload.get("validationSummary") else "ML Preview",
        "issueCount": len(predictive_payload.get("validationSummary") or []),
        "summary": (
            "Rule validation adjusted one or more predictions."
            if predictive_payload.get("validationSummary")
            else "ML predictions passed rule-based validation checks."
        ),
    }
    return patient


def build_patient_from_intake(payload):
    today = datetime.now().date()
    visit_count = max(1, int(payload.get("visitCount") or 1))
    first_visit_date = clean_text(payload.get("firstVisitDate"))
    if not first_visit_date:
        first_visit_date = (today - timedelta(days=max(0, visit_count - 1) * 7)).isoformat()

    explicit_procedure = clean_text(payload.get("explicitProcedure"))
    patient_id = clean_text(payload.get("patientId")) or f"INTAKE-{today:%Y%m%d}-{uuid.uuid4().hex[:6].upper()}"
    first_visit_risk_score = float(payload.get("firstVisitRiskScore") or 0)

    return {
        "patientId": patient_id,
        "patientName": clean_text(payload.get("patientName")) or "Incoming patient",
        "visitDate": today.isoformat(),
        "doctorName": clean_text(payload.get("doctorName")) or "Triage desk",
        "department": clean_text(payload.get("department")) or "General Medicine",
        "customerType": clean_text(payload.get("customerType")) or "Incoming",
        "risk": {
            "score": max(1, int(round(first_visit_risk_score)) if first_visit_risk_score else 3),
            "category": "Medium",
            "reasoning": "Awaiting predictive ML estimation.",
            "redFlags": "[]",
        },
        "admission": {
            "type": "Urgent" if clean_text(payload.get("repeatVisit")).lower() == "true" else "Elective",
            "reasoning": "Initial intake placeholder before predictive scoring.",
            "summary": "Pending predictive intake analysis.",
        },
        "bed": {
            "type": "General",
            "reasoning": "Initial intake placeholder before predictive scoring.",
            "summary": "Pending predictive intake analysis.",
        },
        "procedure": {
            "explicitProcedure": explicit_procedure or "-",
            "explicitConfidence": 90 if explicit_procedure else 0,
            "explicitSource": "Captured from intake form" if explicit_procedure else "No explicit procedure entered",
            "inferredProcedure": "-" if explicit_procedure else "Procedure inference pending operational enrichment",
            "inferredConfidence": 0,
            "inferredSource": "Pending enrichment",
        },
        "journey": {
            "visitCount": visit_count,
            "firstVisitDate": first_visit_date,
            "latestVisitDate": today.isoformat(),
            "repeatVisit": "Yes" if payload.get("repeatVisit") else "No",
            "progressionTrend": "New intake",
            "timelineSummary": "Incoming intake patient awaiting predictive profiling.",
            "riskProgression": "[]",
            "firstVisitRiskScore": first_visit_risk_score,
        },
        "traceability": {
            "evidenceCount": 0,
            "summary": "Intake payload received. Predictive enrichment pending.",
            "safetyNote": "AI-assisted prediction. Clinician validation required.",
            "sourceSections": "[]",
            "evidenceTrace": "[]",
        },
        "validation": {
            "status": "Pending",
            "issueCount": 0,
            "summary": "Predictive intake analysis pending.",
        },
        "clinical": {
            "diagnosis": clean_text(payload.get("diagnosis")),
            "clinicalNotes": clean_text(payload.get("clinicalNotes")),
            "physicalRemarks": clean_text(payload.get("physicalRemarks")),
            "vitalRemarks": clean_text(payload.get("vitalRemarks")),
            "investigations": clean_text(payload.get("investigations")),
            "doctorAdvice": clean_text(payload.get("doctorAdvice")),
            "medicineDetails": clean_text(payload.get("medicineDetails")),
        },
    }


def predict_new_patient(payload, persist=False):
    patient = build_patient_from_intake(payload)
    predictive_payload = build_predictive_payload(patient)
    patient = apply_ml_predictions_to_patient(patient, predictive_payload)

    from backend.operational_intelligence import enrich_patient_record

    enriched_patient = enrich_patient_record(
        patient,
        allow_live_llm=False,
        include_predictive_modeling=True,
    )

    if persist:
        save_live_patient(enriched_patient)

    return enriched_patient
