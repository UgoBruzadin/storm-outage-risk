"""Model registry: a name in a benchmark config -> a fitted-able sklearn-style classifier.

Every model gets the same treatment: fit(X, y) on the training rows,
predict_proba(X)[:, 1] on the test rows. Add a model by adding a builder here.

Baselines come first — a model is only interesting if it beats them:
  prior        the training event rate for everyone (scores = the event rate)
  climatology  each region's own training event rate x month (no weather at all)
"""
import numpy as np
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


class RateBaseline(BaseEstimator, ClassifierMixin):
    """Predicts the training event rate within groups of `by` columns (falls back to the overall rate)."""

    def __init__(self, by=()):
        self.by = by

    def fit(self, X, y):
        self.overall_ = float(np.mean(y))
        if self.by:
            frame = X[list(self.by)].assign(_y=np.asarray(y))
            self.rates_ = frame.groupby(list(self.by))["_y"].mean()
        self.classes_ = np.array([0, 1])
        return self

    def predict_proba(self, X):
        if self.by:
            # a left merge keeps X's row order; unseen groups get the overall rate
            rates = self.rates_.rename("_p").reset_index()
            p = X[list(self.by)].merge(rates, on=list(self.by), how="left")["_p"].fillna(self.overall_).to_numpy()
        else:
            p = np.full(len(X), self.overall_)
        return np.column_stack([1 - p, p])


def _logistic(**params):
    return make_pipeline(SimpleImputer(strategy="median"), StandardScaler(),
                         LogisticRegression(max_iter=3000, **params))


def _hgb(**params):
    return HistGradientBoostingClassifier(random_state=0, **params)


def _random_forest(**params):
    # sklearn forests handle NaN natively since 1.4
    return RandomForestClassifier(random_state=0, n_jobs=-1, **params)


def _lightgbm(**params):
    from lightgbm import LGBMClassifier
    return LGBMClassifier(random_state=0, verbose=-1, n_jobs=-1, **params)


def _xgboost(**params):
    from xgboost import XGBClassifier
    return XGBClassifier(random_state=0, n_jobs=-1, tree_method="hist", eval_metric="aucpr", **params)


REGISTRY = {
    "prior": lambda **p: RateBaseline(by=()),
    "climatology": lambda **p: RateBaseline(by=p.get("by", ("region_fips", "month"))),
    "logistic": _logistic,
    "hgb": _hgb,
    "random_forest": _random_forest,
    "lightgbm": _lightgbm,
    "xgboost": _xgboost,
}

# baselines need columns the feature list may not include (region id, month)
NEEDS_COLUMNS = {"climatology": ["region_fips", "month"]}


def build(name, params=None):
    if name not in REGISTRY:
        raise ValueError(f"unknown model {name!r}; choose from {sorted(REGISTRY)}")
    return REGISTRY[name](**(params or {}))
