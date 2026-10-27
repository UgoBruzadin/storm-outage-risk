# Leaderboard: ablations

Canopy removed and antecedent rain added, against weather+place+recent, with XGBoost, at >= 5% and 10% of customers, on 2020–2023 → 2024 and unseen counties (2020–2024). Ranked by onset PR-AUC.

### >= 5% out · time(train_years=[2020, 2021, 2022, 2023],test_years=[2024]) · ranked by onset_pr_auc

Event rate: 0.77% of all blocks, 0.48% of onset blocks.

| rank | model | train on | features | params | onset PR-AUC | onset lift | onset prec@top1% | all PR-AUC | all lift | all ROC-AUC |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | xgboost | all | weather+place+recent+wet_soil | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.079 | 16.6x | 10.7% | 0.331 | 43.2x | 0.891 |
| 2 | xgboost | all | weather+place+recent-canopy | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.079 | 16.6x | 10.5% | 0.321 | 41.9x | 0.890 |
| 3 | xgboost | all | weather+place+recent | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.079 | 16.5x | 10.6% | 0.324 | 42.2x | 0.891 |

### >= 5% out · county(folds=5) · ranked by onset_pr_auc

Event rate: 0.73% of all blocks, 0.45% of onset blocks.

| rank | model | train on | features | params | onset PR-AUC | onset lift | onset prec@top1% | all PR-AUC | all lift | all ROC-AUC |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | xgboost | all | weather+place+recent+wet_soil | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.081 | 17.8x | 10.7% | 0.334 | 45.8x | 0.882 |
| 2 | xgboost | all | weather+place+recent | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.078 | 17.2x | 10.6% | 0.330 | 45.2x | 0.881 |
| 3 | xgboost | all | weather+place+recent-canopy | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.076 | 16.7x | 10.4% | 0.327 | 44.8x | 0.880 |

### >= 10% out · time(train_years=[2020, 2021, 2022, 2023],test_years=[2024]) · ranked by onset_pr_auc

Event rate: 0.38% of all blocks, 0.23% of onset blocks.

| rank | model | train on | features | params | onset PR-AUC | onset lift | onset prec@top1% | all PR-AUC | all lift | all ROC-AUC |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | xgboost | all | weather+place+recent | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.068 | 29.5x | 7.2% | 0.299 | 78.7x | 0.910 |
| 2 | xgboost | all | weather+place+recent-canopy | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.066 | 28.7x | 7.1% | 0.295 | 77.7x | 0.909 |
| 3 | xgboost | all | weather+place+recent+wet_soil | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.066 | 28.5x | 6.9% | 0.301 | 79.5x | 0.909 |

### >= 10% out · county(folds=5) · ranked by onset_pr_auc

Event rate: 0.36% of all blocks, 0.22% of onset blocks.

| rank | model | train on | features | params | onset PR-AUC | onset lift | onset prec@top1% | all PR-AUC | all lift | all ROC-AUC |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | xgboost | all | weather+place+recent+wet_soil | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.063 | 28.9x | 6.4% | 0.322 | 90.2x | 0.898 |
| 2 | xgboost | all | weather+place+recent | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.063 | 28.7x | 6.4% | 0.319 | 89.4x | 0.898 |
| 3 | xgboost | all | weather+place+recent-canopy | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.061 | 27.9x | 6.3% | 0.311 | 87.3x | 0.898 |
