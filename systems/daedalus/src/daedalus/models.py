from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from sklearn.base import BaseEstimator
from sklearn.ensemble import ExtraTreesClassifier, HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


@dataclass(frozen=True)
class ModelSpec:
    name: str
    factory: Callable[[int], BaseEstimator]


def _logistic(seed: int) -> BaseEstimator:
    return Pipeline([
        ("imputer", SimpleImputer(strategy="median", add_indicator=True, keep_empty_features=True)),
        ("scale", StandardScaler()),
        ("model", LogisticRegression(max_iter=2000, class_weight="balanced", random_state=seed)),
    ])


def _forest(seed: int) -> BaseEstimator:
    return Pipeline([
        ("imputer", SimpleImputer(strategy="median", add_indicator=True, keep_empty_features=True)),
        ("model", RandomForestClassifier(
            n_estimators=300, max_depth=8, min_samples_leaf=12, max_features="sqrt",
            class_weight="balanced_subsample", n_jobs=-1, random_state=seed,
        )),
    ])


def _extra_trees(seed: int) -> BaseEstimator:
    return Pipeline([
        ("imputer", SimpleImputer(strategy="median", add_indicator=True, keep_empty_features=True)),
        ("model", ExtraTreesClassifier(
            n_estimators=300, max_depth=10, min_samples_leaf=10, max_features="sqrt",
            class_weight="balanced", n_jobs=-1, random_state=seed,
        )),
    ])


def _hgb(seed: int) -> BaseEstimator:
    return Pipeline([
        ("imputer", SimpleImputer(strategy="median", add_indicator=True, keep_empty_features=True)),
        ("model", HistGradientBoostingClassifier(
            learning_rate=0.05, max_iter=250, max_leaf_nodes=31,
            l2_regularization=1.0, random_state=seed,
        )),
    ])


def default_model_specs() -> list[ModelSpec]:
    # Deliberately heterogeneous inductive biases. Complexity earns its place through development evidence.
    return [
        ModelSpec("logistic", _logistic),
        ModelSpec("random_forest", _forest),
        ModelSpec("extra_trees", _extra_trees),
        ModelSpec("hist_gradient_boosting", _hgb),
    ]
