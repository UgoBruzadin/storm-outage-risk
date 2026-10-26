"""Scores for rare-event probabilities. Every run reports all of them.

  pr_auc          area under precision-recall: the headline. No skill = the event rate.
  pr_auc_lift     pr_auc / event rate: comparable across thresholds and splits
  roc_auc         ranking quality, 0.5 = random (flattering for rare events)
  brier, log_loss calibration: are the probabilities themselves right?
  precision_top1  of the 1% highest-risk blocks, the share that were real events
  recall_top1     of the real events, the share inside that top 1%
"""
import numpy as np
from sklearn.metrics import average_precision_score, brier_score_loss, log_loss, roc_auc_score


def score(y, p, top=0.01):
    y, p = np.asarray(y), np.clip(np.asarray(p, dtype=float), 1e-6, 1 - 1e-6)
    if len(y) == 0 or y.min() == y.max():
        # no events (or nothing but events) in this slice: ranking metrics are undefined
        nan = float("nan")
        return {"pr_auc": nan, "pr_auc_lift": nan, "roc_auc": nan, "brier": nan, "log_loss": nan,
                "precision_top1": nan, "recall_top1": nan, "event_rate": float(y.mean()) if len(y) else nan,
                "n_test": int(len(y)), "n_events": int(y.sum())}
    cutoff = np.quantile(p, 1 - top)
    alert = p >= cutoff
    event_rate = y.mean()
    pr_auc = average_precision_score(y, p)
    return {
        "pr_auc": pr_auc,
        "pr_auc_lift": pr_auc / event_rate if event_rate else np.nan,
        "roc_auc": roc_auc_score(y, p),
        "brier": brier_score_loss(y, p),
        "log_loss": log_loss(y, p, labels=[0, 1]),
        "precision_top1": y[alert].mean() if alert.any() else np.nan,
        "recall_top1": alert[y == 1].mean() if (y == 1).any() else np.nan,
        "event_rate": event_rate,
        "n_test": int(len(y)),
        "n_events": int(y.sum()),
    }
