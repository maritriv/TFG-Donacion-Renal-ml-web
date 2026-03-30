"""Factory de modelos para la fase de entrenamiento."""

from __future__ import annotations

from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from xgboost import XGBClassifier


def get_model(name: str, random_state: int):
    """Devuelve una instancia del modelo solicitado."""
    if name == "dummy":
        return DummyClassifier(strategy="most_frequent")

    if name == "logistic_regression":
        return Pipeline(
            steps=[
                ("scaler", StandardScaler()),
                (
                    "model",
                    LogisticRegression(
                        random_state=random_state,
                        max_iter=2000,
                        class_weight="balanced",
                    ),
                ),
            ]
        )

    if name == "random_forest":
        return RandomForestClassifier(
            n_estimators=300,
            max_depth=None,
            min_samples_split=2,
            min_samples_leaf=1,
            random_state=random_state,
            class_weight="balanced",
        )

    if name == "svm":
        return Pipeline(
            steps=[
                ("scaler", StandardScaler()),
                (
                    "model",
                    SVC(
                        kernel="rbf",
                        probability=True,
                        class_weight="balanced",
                        random_state=random_state,
                    ),
                ),
            ]
        )

    if name == "xgboost":
        return XGBClassifier(
            n_estimators=500,
            max_depth=4,
            learning_rate=0.05,
            subsample=0.9,
            colsample_bytree=0.9,
            random_state=random_state,
            eval_metric="logloss",
            scale_pos_weight=1.5,
        )

    raise ValueError(f"Modelo no soportado: {name}")