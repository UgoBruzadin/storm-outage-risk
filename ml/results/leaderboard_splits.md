# Leaderboard: splits

Final XGBoost settings on next year, unseen counties and random region-days, at >= 5% of customers. Ranked by onset PR-AUC.

### >= 5% out · time(train_years=[2020, 2021, 2022, 2023, 2024],test_years=[2025]) · ranked by onset_pr_auc

Event rate: 0.99% of all blocks, 0.53% of onset blocks.

| rank | model | train on | features | params | onset PR-AUC | onset lift | onset prec@top1% | all PR-AUC | all lift | all ROC-AUC |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | xgboost | all | weather+place+recent | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.106 | 19.9x | 13.9% | 0.420 | 42.3x | 0.910 |
| 2 | xgboost | all | weather | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.068 | 12.8x | 11.8% | 0.062 | 6.3x | 0.719 |
| 3 | climatology | all | - | {} | 0.009 | 1.8x | 1.7% | 0.018 | 1.8x | 0.634 |

### >= 5% out · county(folds=5) · ranked by onset_pr_auc

Event rate: 0.77% of all blocks, 0.47% of onset blocks.

| rank | model | train on | features | params | onset PR-AUC | onset lift | onset prec@top1% | all PR-AUC | all lift | all ROC-AUC |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | xgboost | all | weather+place+recent | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.086 | 18.4x | 11.2% | 0.351 | 45.6x | 0.886 |
| 2 | xgboost | all | weather | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.070 | 14.9x | 9.9% | 0.076 | 9.9x | 0.767 |
| 3 | climatology | all | - | {} | 0.004 | 1.0x | 0.4% | 0.007 | 1.0x | 0.480 |

### >= 5% out · random(folds=5) · ranked by onset_pr_auc

Event rate: 0.77% of all blocks, 0.47% of onset blocks.

| rank | model | train on | features | params | onset PR-AUC | onset lift | onset prec@top1% | all PR-AUC | all lift | all ROC-AUC |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | xgboost | all | weather+place+recent | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.093 | 19.9x | 11.7% | 0.362 | 46.9x | 0.896 |
| 2 | xgboost | all | weather | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.069 | 14.9x | 9.8% | 0.077 | 9.9x | 0.769 |
| 3 | climatology | all | - | {} | 0.009 | 1.9x | 1.4% | 0.019 | 2.5x | 0.702 |
