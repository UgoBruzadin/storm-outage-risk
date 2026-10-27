# Leaderboard: final_2025

Final XGBoost settings (chosen on 2024) trained on 2020–2024, tested on 2025, and on unseen counties, at >= 1%, 5% and 10% of customers. Ranked by onset PR-AUC.

### >= 1% out · time(train_years=[2020, 2021, 2022, 2023, 2024],test_years=[2025]) · ranked by onset_pr_auc

Event rate: 3.29% of all blocks, 1.97% of onset blocks.

| rank | model | train on | features | params | onset PR-AUC | onset lift | onset prec@top1% | all PR-AUC | all lift | all ROC-AUC |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | xgboost | all | weather+place+recent+wet_soil | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.155 | 7.8x | 30.3% | 0.405 | 12.3x | 0.866 |
| 2 | xgboost | all | weather+place+history+recent | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.154 | 7.8x | 30.3% | 0.403 | 12.2x | 0.866 |
| 3 | xgboost | all | weather+place+recent | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.153 | 7.8x | 30.6% | 0.407 | 12.4x | 0.866 |
| 4 | xgboost | all | weather+place+history | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.145 | 7.4x | 29.4% | 0.171 | 5.2x | 0.755 |
| 5 | xgboost | all | weather+place | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.145 | 7.3x | 30.0% | 0.170 | 5.2x | 0.754 |
| 6 | xgboost | all | weather | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.116 | 5.9x | 26.4% | 0.132 | 4.0x | 0.708 |
| 7 | climatology | all | - | {} | 0.032 | 1.6x | 4.7% | 0.054 | 1.6x | 0.628 |

### >= 1% out · county(folds=5) · ranked by onset_pr_auc

Event rate: 2.73% of all blocks, 1.73% of onset blocks.

| rank | model | train on | features | params | onset PR-AUC | onset lift | onset prec@top1% | all PR-AUC | all lift | all ROC-AUC |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | xgboost | all | weather+place+history+recent | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.132 | 7.7x | 25.8% | 0.359 | 13.1x | 0.855 |
| 2 | xgboost | all | weather+place+history | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.124 | 7.2x | 25.1% | 0.150 | 5.5x | 0.764 |
| 3 | xgboost | all | weather+place+recent+wet_soil | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.122 | 7.1x | 24.9% | 0.355 | 13.0x | 0.845 |
| 4 | xgboost | all | weather+place+recent | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.122 | 7.1x | 24.9% | 0.353 | 12.9x | 0.845 |
| 5 | xgboost | all | weather+place | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.110 | 6.4x | 23.6% | 0.134 | 4.9x | 0.741 |
| 6 | xgboost | all | weather | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.109 | 6.3x | 23.6% | 0.133 | 4.8x | 0.734 |
| 7 | climatology | all | - | {} | 0.016 | 0.9x | 1.5% | 0.026 | 0.9x | 0.472 |

### >= 5% out · time(train_years=[2020, 2021, 2022, 2023, 2024],test_years=[2025]) · ranked by onset_pr_auc

Event rate: 0.99% of all blocks, 0.53% of onset blocks.

| rank | model | train on | features | params | onset PR-AUC | onset lift | onset prec@top1% | all PR-AUC | all lift | all ROC-AUC |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | xgboost | all | weather+place+history+recent | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.108 | 20.4x | 14.2% | 0.418 | 42.1x | 0.910 |
| 2 | xgboost | all | weather+place+recent+wet_soil | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.108 | 20.3x | 13.9% | 0.414 | 41.7x | 0.909 |
| 3 | xgboost | all | weather+place+recent | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.106 | 19.9x | 13.9% | 0.420 | 42.3x | 0.910 |
| 4 | xgboost | all | weather+place | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.091 | 17.0x | 12.9% | 0.090 | 9.1x | 0.785 |
| 5 | xgboost | all | weather+place+history | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.090 | 16.9x | 12.8% | 0.091 | 9.2x | 0.788 |
| 6 | xgboost | all | weather | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.068 | 12.8x | 11.8% | 0.062 | 6.3x | 0.719 |
| 7 | climatology | all | - | {} | 0.009 | 1.8x | 1.7% | 0.018 | 1.8x | 0.634 |

### >= 5% out · county(folds=5) · ranked by onset_pr_auc

Event rate: 0.77% of all blocks, 0.47% of onset blocks.

| rank | model | train on | features | params | onset PR-AUC | onset lift | onset prec@top1% | all PR-AUC | all lift | all ROC-AUC |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | xgboost | all | weather+place+history+recent | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.090 | 19.4x | 11.5% | 0.354 | 45.8x | 0.892 |
| 2 | xgboost | all | weather+place+recent+wet_soil | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.087 | 18.7x | 11.2% | 0.354 | 46.0x | 0.886 |
| 3 | xgboost | all | weather+place+recent | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.086 | 18.4x | 11.2% | 0.351 | 45.6x | 0.886 |
| 4 | xgboost | all | weather+place+history | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.081 | 17.3x | 10.5% | 0.090 | 11.6x | 0.808 |
| 5 | xgboost | all | weather+place | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.071 | 15.3x | 10.0% | 0.082 | 10.6x | 0.792 |
| 6 | xgboost | all | weather | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.070 | 14.9x | 9.9% | 0.076 | 9.9x | 0.767 |
| 7 | climatology | all | - | {} | 0.004 | 1.0x | 0.4% | 0.007 | 1.0x | 0.480 |

### >= 10% out · time(train_years=[2020, 2021, 2022, 2023, 2024],test_years=[2025]) · ranked by onset_pr_auc

Event rate: 0.51% of all blocks, 0.26% of onset blocks.

| rank | model | train on | features | params | onset PR-AUC | onset lift | onset prec@top1% | all PR-AUC | all lift | all ROC-AUC |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | xgboost | all | weather+place+recent+wet_soil | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.086 | 32.7x | 8.9% | 0.376 | 74.4x | 0.931 |
| 2 | xgboost | all | weather+place+history+recent | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.085 | 32.2x | 8.8% | 0.375 | 74.0x | 0.931 |
| 3 | xgboost | all | weather+place+recent | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.083 | 31.5x | 8.7% | 0.378 | 74.7x | 0.930 |
| 4 | xgboost | all | weather+place | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.062 | 23.7x | 7.5% | 0.058 | 11.5x | 0.796 |
| 5 | xgboost | all | weather+place+history | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.061 | 23.1x | 7.1% | 0.058 | 11.5x | 0.806 |
| 6 | xgboost | all | weather | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.047 | 17.7x | 6.9% | 0.039 | 7.7x | 0.734 |
| 7 | climatology | all | - | {} | 0.005 | 1.7x | 1.1% | 0.009 | 1.8x | 0.637 |

### >= 10% out · county(folds=5) · ranked by onset_pr_auc

Event rate: 0.38% of all blocks, 0.23% of onset blocks.

| rank | model | train on | features | params | onset PR-AUC | onset lift | onset prec@top1% | all PR-AUC | all lift | all ROC-AUC |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | xgboost | all | weather+place+history+recent | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.071 | 31.6x | 7.0% | 0.335 | 87.9x | 0.912 |
| 2 | xgboost | all | weather+place+recent+wet_soil | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.069 | 30.7x | 6.9% | 0.337 | 88.6x | 0.905 |
| 3 | xgboost | all | weather+place+recent | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.068 | 30.1x | 6.8% | 0.333 | 87.6x | 0.905 |
| 4 | xgboost | all | weather+place+history | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.060 | 26.5x | 6.0% | 0.061 | 16.1x | 0.828 |
| 5 | xgboost | all | weather+place | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.054 | 23.8x | 6.0% | 0.058 | 15.3x | 0.811 |
| 6 | xgboost | all | weather | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.054 | 23.8x | 5.7% | 0.055 | 14.5x | 0.780 |
| 7 | climatology | all | - | {} | 0.002 | 0.9x | 0.2% | 0.004 | 0.9x | 0.471 |
