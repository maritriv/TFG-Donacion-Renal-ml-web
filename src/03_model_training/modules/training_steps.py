"""Funciones de negocio de la fase de modelado."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Tuple

import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import GridSearchCV, StratifiedKFold, train_test_split
from sklearn.ensemble import VotingClassifier

def load_dataset(csv_path: Path) -> pd.DataFrame:
    """Carga un dataset desde CSV."""
    if not csv_path.exists():
        raise FileNotFoundError(f"No existe el archivo: {csv_path}")
    return pd.read_csv(csv_path)


def split_features_target(df: pd.DataFrame, target_column: str) -> Tuple[pd.DataFrame, pd.Series]:
    """Separa variables predictoras y variable objetivo."""
    if target_column not in df.columns:
        raise KeyError(f"No existe la columna target: {target_column}")

    x = df.drop(columns=[target_column]).copy()
    y = df[target_column].copy()
    return x, y


def make_train_test_split(
    x: pd.DataFrame,
    y: pd.Series,
    test_size: float,
    random_state: int,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    """Realiza train/test split estratificado."""
    return train_test_split(
        x,
        y,
        test_size=test_size,
        random_state=random_state,
        stratify=y,
    )


def _compute_basic_metrics(
    y_true: pd.Series,
    y_pred: np.ndarray,
    y_proba: np.ndarray | None = None,
) -> Dict[str, float | None]:
    """Calcula métricas básicas de clasificación."""
    metrics: Dict[str, float | None] = {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "balanced_accuracy": float(balanced_accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
    }

    if y_proba is not None:
        try:
            metrics["roc_auc"] = float(roc_auc_score(y_true, y_proba))
        except ValueError:
            metrics["roc_auc"] = None
    else:
        metrics["roc_auc"] = None

    return metrics


def cross_validate_model(
    model,
    x_train: pd.DataFrame,
    y_train: pd.Series,
    n_splits: int,
    random_state: int,
) -> Dict[str, object]:
    """Evalúa el modelo con validación cruzada estratificada sobre train."""
    cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=random_state)

    fold_metrics = []

    for fold_idx, (train_idx, val_idx) in enumerate(cv.split(x_train, y_train), start=1):
        x_fold_train = x_train.iloc[train_idx]
        x_fold_val = x_train.iloc[val_idx]
        y_fold_train = y_train.iloc[train_idx]
        y_fold_val = y_train.iloc[val_idx]

        model_instance = clone(model)
        model_instance.fit(x_fold_train, y_fold_train)

        y_pred = model_instance.predict(x_fold_val)

        if hasattr(model_instance, "predict_proba"):
            y_proba = model_instance.predict_proba(x_fold_val)[:, 1]
        else:
            y_proba = None

        metrics = _compute_basic_metrics(y_fold_val, y_pred, y_proba)
        metrics["fold"] = fold_idx
        fold_metrics.append(metrics)

    metric_names = ["accuracy", "balanced_accuracy", "precision", "recall", "f1", "roc_auc"]
    summary: Dict[str, object] = {"fold_metrics": fold_metrics}

    for metric_name in metric_names:
        values = [fold[metric_name] for fold in fold_metrics if fold[metric_name] is not None]
        if values:
            summary[f"{metric_name}_mean"] = float(np.mean(values))
            summary[f"{metric_name}_std"] = float(np.std(values))
        else:
            summary[f"{metric_name}_mean"] = None
            summary[f"{metric_name}_std"] = None

    return summary


def tune_model_with_grid_search(
    model,
    param_grid: Dict[str, list],
    x_train: pd.DataFrame,
    y_train: pd.Series,
    n_splits: int,
    scoring: str,
    random_state: int,
) -> GridSearchCV:
    """Ajusta hiperparametros mediante GridSearchCV estratificado."""
    cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=random_state)

    search = GridSearchCV(
        estimator=model,
        param_grid=param_grid,
        scoring=scoring,
        cv=cv,
        refit=True,
        n_jobs=1,
        verbose=0,
    )
    search.fit(x_train, y_train)
    return search


def train_and_evaluate_model(
    model,
    x_train: pd.DataFrame,
    y_train: pd.Series,
    x_test: pd.DataFrame,
    y_test: pd.Series,
) -> Dict[str, object]:
    """Entrena en train y evalúa en test final."""
    model.fit(x_train, y_train)

    y_pred = model.predict(x_test)

    if hasattr(model, "predict_proba"):
        y_proba = model.predict_proba(x_test)[:, 1]
    else:
        y_proba = None

    basic_metrics = _compute_basic_metrics(y_test, y_pred, y_proba)

    metrics: Dict[str, object] = {
        **basic_metrics,
        "confusion_matrix": confusion_matrix(y_test, y_pred).tolist(),
        "test_size": int(len(y_test)),
    }

    return metrics

def build_voting_classifier(best_models: Dict[str, object]):
    """Construye un VotingClassifier a partir de modelos ya tuneados."""
    
    estimators = []

    if "logistic_regression" in best_models:
        estimators.append(("logistic", best_models["logistic_regression"]))

    if "svm" in best_models:
        estimators.append(("svm", best_models["svm"]))

    return VotingClassifier(
        estimators=estimators,
        voting="soft",
        weights=[1, 2],
        n_jobs=1,
    )

def save_metrics(metrics: Dict[str, object], output_path: Path) -> None:
    """Guarda métricas en JSON."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2, ensure_ascii=False)


def save_confusion_matrix_plot(
    confusion_matrix_values,
    output_path: Path,
    title: str,
) -> None:
    """Guarda una matriz de confusión como figura."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    plt.figure(figsize=(5, 4))
    plt.imshow(confusion_matrix_values, aspect="auto")
    plt.colorbar()
    plt.xticks([0, 1], ["Pred 0", "Pred 1"])
    plt.yticks([0, 1], ["Real 0", "Real 1"])
    plt.title(title)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()


def save_model(model, output_path: Path) -> None:
    """Guarda el modelo entrenado."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, output_path)


def save_grid_search_results(search: GridSearchCV, output_path: Path) -> None:
    """Guarda los resultados completos del grid search."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(search.cv_results_).to_csv(output_path, index=False)


def build_comparison_row(
    dataset_name: str,
    model_name: str,
    cv_metrics: Dict[str, object],
    test_metrics: Dict[str, object],
    best_params: Dict[str, object] | None = None,
    best_cv_score: float | None = None,
) -> Dict[str, object]:
    """Construye una fila de comparación entre modelos."""
    return {
        "dataset": dataset_name,
        "model": model_name,
        "cv_accuracy_mean": cv_metrics["accuracy_mean"],
        "cv_accuracy_std": cv_metrics["accuracy_std"],
        "cv_balanced_accuracy_mean": cv_metrics["balanced_accuracy_mean"],
        "cv_balanced_accuracy_std": cv_metrics["balanced_accuracy_std"],
        "cv_precision_mean": cv_metrics["precision_mean"],
        "cv_precision_std": cv_metrics["precision_std"],
        "cv_recall_mean": cv_metrics["recall_mean"],
        "cv_recall_std": cv_metrics["recall_std"],
        "cv_f1_mean": cv_metrics["f1_mean"],
        "cv_f1_std": cv_metrics["f1_std"],
        "cv_roc_auc_mean": cv_metrics["roc_auc_mean"],
        "cv_roc_auc_std": cv_metrics["roc_auc_std"],
        "test_accuracy": test_metrics["accuracy"],
        "test_balanced_accuracy": test_metrics["balanced_accuracy"],
        "test_precision": test_metrics["precision"],
        "test_recall": test_metrics["recall"],
        "test_f1": test_metrics["f1"],
        "test_roc_auc": test_metrics["roc_auc"],
        "best_cv_score": best_cv_score,
        "best_params": str(best_params) if best_params is not None else "",
    }


def save_comparison_table(rows: list[Dict[str, object]], output_path: Path) -> None:
    """Guarda tabla comparativa de modelos en CSV."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows)
    df.to_csv(output_path, index=False)