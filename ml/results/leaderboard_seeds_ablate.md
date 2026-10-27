# Leaderboard: seeds_ablate

Canopy removed and antecedent rain added, against weather+place+recent, 5 seeds each, at >= 5% and 10% of customers, on 2020–2023 → 2024 and unseen counties (2020–2024).

### >= 5% out · time(train_years=[2020, 2021, 2022, 2023],test_years=[2024]) · ranked by onset_pr_auc

Event rate: 0.77% of all blocks, 0.48% of onset blocks.

| rank | model | train on | features | params | onset PR-AUC | onset lift | onset prec@top1% | all PR-AUC | all lift | all ROC-AUC |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | xgboost | all | weather+place+recent | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8, 'random_state': 3} | 0.080 | 16.7x | 10.7% | 0.325 | 42.4x | 0.892 |
| 2 | xgboost | all | weather+place+recent-canopy | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8, 'random_state': 1} | 0.080 | 16.7x | 10.8% | 0.320 | 41.8x | 0.890 |
| 3 | xgboost | all | weather+place+recent | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8, 'random_state': 4} | 0.080 | 16.7x | 10.7% | 0.327 | 42.6x | 0.892 |
| 4 | xgboost | all | weather+place+recent+wet_soil | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8, 'random_state': 1} | 0.079 | 16.7x | 10.7% | 0.331 | 43.3x | 0.891 |
| 5 | xgboost | all | weather+place+recent+wet_soil | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8, 'random_state': 0} | 0.079 | 16.6x | 10.7% | 0.331 | 43.2x | 0.891 |
| 6 | xgboost | all | weather+place+recent-canopy | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8, 'random_state': 2} | 0.079 | 16.6x | 10.6% | 0.322 | 42.0x | 0.891 |
| 7 | xgboost | all | weather+place+recent-canopy | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8, 'random_state': 0} | 0.079 | 16.6x | 10.5% | 0.321 | 41.9x | 0.890 |
| 8 | xgboost | all | weather+place+recent | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8, 'random_state': 1} | 0.079 | 16.6x | 10.8% | 0.326 | 42.6x | 0.892 |
| 9 | xgboost | all | weather+place+recent-canopy | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8, 'random_state': 3} | 0.079 | 16.5x | 10.7% | 0.321 | 41.9x | 0.891 |
| 10 | xgboost | all | weather+place+recent+wet_soil | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8, 'random_state': 2} | 0.079 | 16.5x | 10.8% | 0.331 | 43.2x | 0.891 |
| 11 | xgboost | all | weather+place+recent+wet_soil | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8, 'random_state': 3} | 0.079 | 16.5x | 10.6% | 0.331 | 43.2x | 0.892 |
| 12 | xgboost | all | weather+place+recent | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8, 'random_state': 0} | 0.079 | 16.5x | 10.6% | 0.324 | 42.2x | 0.891 |
| 13 | xgboost | all | weather+place+recent | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8, 'random_state': 2} | 0.078 | 16.4x | 10.6% | 0.324 | 42.2x | 0.892 |
| 14 | xgboost | all | weather+place+recent-canopy | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8, 'random_state': 4} | 0.078 | 16.4x | 10.5% | 0.321 | 41.9x | 0.891 |
| 15 | xgboost | all | weather+place+recent+wet_soil | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8, 'random_state': 4} | 0.077 | 16.2x | 10.5% | 0.330 | 43.1x | 0.891 |

### >= 5% out · county(folds=5) · ranked by onset_pr_auc

Event rate: 0.73% of all blocks, 0.45% of onset blocks.

| rank | model | train on | features | params | onset PR-AUC | onset lift | onset prec@top1% | all PR-AUC | all lift | all ROC-AUC |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | xgboost | all | weather+place+recent+wet_soil | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8, 'random_state': 0} | 0.081 | 17.8x | 10.7% | 0.334 | 45.8x | 0.882 |
| 2 | xgboost | all | weather+place+recent+wet_soil | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8, 'random_state': 2} | 0.080 | 17.7x | 10.6% | 0.333 | 45.7x | 0.881 |
| 3 | xgboost | all | weather+place+recent+wet_soil | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8, 'random_state': 3} | 0.080 | 17.6x | 10.6% | 0.334 | 45.8x | 0.882 |
| 4 | xgboost | all | weather+place+recent+wet_soil | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8, 'random_state': 1} | 0.080 | 17.6x | 10.6% | 0.334 | 45.9x | 0.882 |
| 5 | xgboost | all | weather+place+recent | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8, 'random_state': 3} | 0.079 | 17.4x | 10.6% | 0.329 | 45.2x | 0.881 |
| 6 | xgboost | all | weather+place+recent+wet_soil | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8, 'random_state': 4} | 0.078 | 17.3x | 10.6% | 0.333 | 45.7x | 0.881 |
| 7 | xgboost | all | weather+place+recent | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8, 'random_state': 4} | 0.078 | 17.3x | 10.7% | 0.329 | 45.1x | 0.881 |
| 8 | xgboost | all | weather+place+recent | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8, 'random_state': 2} | 0.078 | 17.2x | 10.6% | 0.331 | 45.4x | 0.881 |
| 9 | xgboost | all | weather+place+recent | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8, 'random_state': 1} | 0.078 | 17.2x | 10.5% | 0.329 | 45.2x | 0.881 |
| 10 | xgboost | all | weather+place+recent | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8, 'random_state': 0} | 0.078 | 17.2x | 10.6% | 0.330 | 45.2x | 0.881 |
| 11 | xgboost | all | weather+place+recent-canopy | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8, 'random_state': 2} | 0.076 | 16.8x | 10.4% | 0.326 | 44.7x | 0.879 |
| 12 | xgboost | all | weather+place+recent-canopy | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8, 'random_state': 3} | 0.076 | 16.8x | 10.4% | 0.326 | 44.7x | 0.880 |
| 13 | xgboost | all | weather+place+recent-canopy | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8, 'random_state': 4} | 0.076 | 16.8x | 10.3% | 0.325 | 44.6x | 0.880 |
| 14 | xgboost | all | weather+place+recent-canopy | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8, 'random_state': 1} | 0.076 | 16.8x | 10.4% | 0.326 | 44.8x | 0.880 |
| 15 | xgboost | all | weather+place+recent-canopy | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8, 'random_state': 0} | 0.076 | 16.7x | 10.4% | 0.327 | 44.8x | 0.880 |

### >= 10% out · time(train_years=[2020, 2021, 2022, 2023],test_years=[2024]) · ranked by onset_pr_auc

Event rate: 0.38% of all blocks, 0.23% of onset blocks.

| rank | model | train on | features | params | onset PR-AUC | onset lift | onset prec@top1% | all PR-AUC | all lift | all ROC-AUC |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | xgboost | all | weather+place+recent+wet_soil | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8, 'random_state': 3} | 0.069 | 29.9x | 6.9% | 0.304 | 80.0x | 0.910 |
| 2 | xgboost | all | weather+place+recent | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8, 'random_state': 3} | 0.069 | 29.7x | 7.2% | 0.293 | 77.4x | 0.910 |
| 3 | xgboost | all | weather+place+recent | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8, 'random_state': 2} | 0.069 | 29.7x | 7.0% | 0.298 | 78.5x | 0.910 |
| 4 | xgboost | all | weather+place+recent | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8, 'random_state': 1} | 0.068 | 29.5x | 7.0% | 0.297 | 78.2x | 0.910 |
| 5 | xgboost | all | weather+place+recent | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8, 'random_state': 0} | 0.068 | 29.5x | 7.2% | 0.299 | 78.7x | 0.910 |
| 6 | xgboost | all | weather+place+recent | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8, 'random_state': 4} | 0.067 | 29.1x | 7.0% | 0.297 | 78.4x | 0.910 |
| 7 | xgboost | all | weather+place+recent-canopy | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8, 'random_state': 1} | 0.067 | 29.1x | 7.0% | 0.297 | 78.2x | 0.909 |
| 8 | xgboost | all | weather+place+recent-canopy | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8, 'random_state': 3} | 0.067 | 29.0x | 7.2% | 0.293 | 77.3x | 0.909 |
| 9 | xgboost | all | weather+place+recent-canopy | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8, 'random_state': 4} | 0.067 | 29.0x | 7.0% | 0.295 | 77.8x | 0.910 |
| 10 | xgboost | all | weather+place+recent+wet_soil | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8, 'random_state': 4} | 0.067 | 28.8x | 7.2% | 0.298 | 78.5x | 0.910 |
| 11 | xgboost | all | weather+place+recent+wet_soil | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8, 'random_state': 1} | 0.067 | 28.8x | 6.8% | 0.300 | 79.0x | 0.910 |
| 12 | xgboost | all | weather+place+recent-canopy | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8, 'random_state': 0} | 0.066 | 28.7x | 7.1% | 0.295 | 77.7x | 0.909 |
| 13 | xgboost | all | weather+place+recent-canopy | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8, 'random_state': 2} | 0.066 | 28.6x | 7.0% | 0.293 | 77.2x | 0.909 |
| 14 | xgboost | all | weather+place+recent+wet_soil | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8, 'random_state': 0} | 0.066 | 28.5x | 6.9% | 0.301 | 79.5x | 0.909 |
| 15 | xgboost | all | weather+place+recent+wet_soil | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8, 'random_state': 2} | 0.065 | 28.1x | 6.9% | 0.302 | 79.7x | 0.910 |

### >= 10% out · county(folds=5) · ranked by onset_pr_auc

Event rate: 0.36% of all blocks, 0.22% of onset blocks.

| rank | model | train on | features | params | onset PR-AUC | onset lift | onset prec@top1% | all PR-AUC | all lift | all ROC-AUC |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | xgboost | all | weather+place+recent+wet_soil | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8, 'random_state': 1} | 0.064 | 29.2x | 6.4% | 0.321 | 90.1x | 0.899 |
| 2 | xgboost | all | weather+place+recent+wet_soil | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8, 'random_state': 3} | 0.063 | 29.0x | 6.3% | 0.320 | 89.8x | 0.898 |
| 3 | xgboost | all | weather+place+recent | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8, 'random_state': 3} | 0.063 | 29.0x | 6.3% | 0.318 | 89.3x | 0.899 |
| 4 | xgboost | all | weather+place+recent | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8, 'random_state': 4} | 0.063 | 29.0x | 6.4% | 0.318 | 89.1x | 0.898 |
| 5 | xgboost | all | weather+place+recent+wet_soil | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8, 'random_state': 0} | 0.063 | 28.9x | 6.4% | 0.322 | 90.2x | 0.898 |
| 6 | xgboost | all | weather+place+recent+wet_soil | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8, 'random_state': 2} | 0.063 | 28.8x | 6.2% | 0.322 | 90.3x | 0.898 |
| 7 | xgboost | all | weather+place+recent+wet_soil | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8, 'random_state': 4} | 0.063 | 28.7x | 6.3% | 0.322 | 90.4x | 0.898 |
| 8 | xgboost | all | weather+place+recent | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8, 'random_state': 0} | 0.063 | 28.7x | 6.4% | 0.319 | 89.4x | 0.898 |
| 9 | xgboost | all | weather+place+recent | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8, 'random_state': 1} | 0.062 | 28.5x | 6.3% | 0.315 | 88.5x | 0.898 |
| 10 | xgboost | all | weather+place+recent | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8, 'random_state': 2} | 0.062 | 28.4x | 6.3% | 0.317 | 89.0x | 0.898 |
| 11 | xgboost | all | weather+place+recent-canopy | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8, 'random_state': 1} | 0.062 | 28.3x | 6.3% | 0.312 | 87.5x | 0.899 |
| 12 | xgboost | all | weather+place+recent-canopy | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8, 'random_state': 2} | 0.061 | 28.2x | 6.3% | 0.311 | 87.3x | 0.899 |
| 13 | xgboost | all | weather+place+recent-canopy | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8, 'random_state': 4} | 0.061 | 28.0x | 6.3% | 0.311 | 87.3x | 0.898 |
| 14 | xgboost | all | weather+place+recent-canopy | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8, 'random_state': 0} | 0.061 | 27.9x | 6.3% | 0.311 | 87.3x | 0.898 |
| 15 | xgboost | all | weather+place+recent-canopy | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8, 'random_state': 3} | 0.060 | 27.7x | 6.2% | 0.311 | 87.2x | 0.899 |
