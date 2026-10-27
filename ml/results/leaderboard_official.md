# Leaderboard: official

NWS warnings and SPC outlooks as baselines, and as features, against the model, at >= 1%, 5% and 10% of customers, on 2020–2024 → 2025 and unseen counties. Ranked by onset PR-AUC.

### >= 1% out · time(train_years=[2020, 2021, 2022, 2023, 2024],test_years=[2025]) · ranked by onset_pr_auc

Event rate: 3.29% of all blocks, 1.97% of onset blocks.

| rank | model | train on | features | params | onset PR-AUC | onset lift | onset prec@top1% | all PR-AUC | all lift | all ROC-AUC |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | xgboost | all | weather+place+recent+warnings+outlook | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.161 | 8.2x | 31.5% | 0.412 | 12.5x | 0.868 |
| 2 | xgboost | all | weather+place+warnings+outlook | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.154 | 7.8x | 31.1% | 0.197 | 6.0x | 0.762 |
| 3 | xgboost | all | weather+place+recent | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.153 | 7.8x | 30.6% | 0.407 | 12.4x | 0.866 |
| 4 | xgboost | all | weather+place | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.145 | 7.3x | 30.0% | 0.170 | 5.2x | 0.754 |
| 5 | official | all | - | {} | 0.074 | 3.8x | 20.7% | 0.104 | 3.2x | 0.654 |
| 6 | xgboost | all | warnings+outlook | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.073 | 3.7x | 20.7% | 0.103 | 3.1x | 0.651 |
| 7 | spc_outlook | all | - | {} | 0.061 | 3.1x | 19.4% | 0.086 | 2.6x | 0.642 |
| 8 | nws_warnings | all | - | {} | 0.035 | 1.8x | 10.2% | 0.055 | 1.7x | 0.527 |
| 9 | climatology | all | - | {} | 0.032 | 1.6x | 4.7% | 0.054 | 1.6x | 0.628 |

### >= 1% out · county(folds=5) · ranked by onset_pr_auc

Event rate: 2.73% of all blocks, 1.73% of onset blocks.

| rank | model | train on | features | params | onset PR-AUC | onset lift | onset prec@top1% | all PR-AUC | all lift | all ROC-AUC |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | xgboost | all | weather+place+recent+warnings+outlook | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.132 | 7.6x | 26.2% | 0.360 | 13.2x | 0.846 |
| 2 | xgboost | all | weather+place+recent | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.122 | 7.1x | 24.9% | 0.353 | 12.9x | 0.845 |
| 3 | xgboost | all | weather+place+warnings+outlook | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.118 | 6.9x | 24.5% | 0.156 | 5.7x | 0.748 |
| 4 | xgboost | all | weather+place | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.110 | 6.4x | 23.6% | 0.134 | 4.9x | 0.741 |
| 5 | xgboost | all | warnings+outlook | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.065 | 3.8x | 15.3% | 0.097 | 3.5x | 0.651 |
| 6 | official | all | - | {} | 0.061 | 3.6x | 14.7% | 0.091 | 3.3x | 0.651 |
| 7 | spc_outlook | all | - | {} | 0.048 | 2.8x | 12.7% | 0.075 | 2.7x | 0.641 |
| 8 | nws_warnings | all | - | {} | 0.028 | 1.6x | 7.2% | 0.042 | 1.5x | 0.490 |
| 9 | climatology | all | - | {} | 0.016 | 0.9x | 1.5% | 0.026 | 0.9x | 0.472 |

### >= 5% out · time(train_years=[2020, 2021, 2022, 2023, 2024],test_years=[2025]) · ranked by onset_pr_auc

Event rate: 0.99% of all blocks, 0.53% of onset blocks.

| rank | model | train on | features | params | onset PR-AUC | onset lift | onset prec@top1% | all PR-AUC | all lift | all ROC-AUC |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | xgboost | all | weather+place+recent+warnings+outlook | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.122 | 23.0x | 14.5% | 0.420 | 42.3x | 0.911 |
| 2 | xgboost | all | weather+place+recent | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.106 | 19.9x | 13.9% | 0.420 | 42.3x | 0.910 |
| 3 | xgboost | all | weather+place+warnings+outlook | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.100 | 18.8x | 13.6% | 0.115 | 11.6x | 0.794 |
| 4 | xgboost | all | weather+place | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.091 | 17.0x | 12.9% | 0.090 | 9.1x | 0.785 |
| 5 | official | all | - | {} | 0.044 | 8.3x | 9.2% | 0.052 | 5.2x | 0.672 |
| 6 | xgboost | all | warnings+outlook | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.041 | 7.8x | 8.1% | 0.052 | 5.2x | 0.675 |
| 7 | spc_outlook | all | - | {} | 0.033 | 6.2x | 8.6% | 0.041 | 4.1x | 0.653 |
| 8 | nws_warnings | all | - | {} | 0.024 | 4.5x | 5.9% | 0.029 | 3.0x | 0.549 |
| 9 | climatology | all | - | {} | 0.009 | 1.8x | 1.7% | 0.018 | 1.8x | 0.634 |

### >= 5% out · county(folds=5) · ranked by onset_pr_auc

Event rate: 0.77% of all blocks, 0.47% of onset blocks.

| rank | model | train on | features | params | onset PR-AUC | onset lift | onset prec@top1% | all PR-AUC | all lift | all ROC-AUC |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | xgboost | all | weather+place+recent+warnings+outlook | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.100 | 21.6x | 12.0% | 0.361 | 46.9x | 0.888 |
| 2 | xgboost | all | weather+place+recent | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.086 | 18.4x | 11.2% | 0.351 | 45.6x | 0.886 |
| 3 | xgboost | all | weather+place+warnings+outlook | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.084 | 17.9x | 10.8% | 0.109 | 14.1x | 0.801 |
| 4 | xgboost | all | weather+place | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.071 | 15.3x | 10.0% | 0.082 | 10.6x | 0.792 |
| 5 | xgboost | all | warnings+outlook | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.042 | 8.9x | 6.8% | 0.056 | 7.3x | 0.688 |
| 6 | official | all | - | {} | 0.039 | 8.4x | 7.0% | 0.052 | 6.7x | 0.689 |
| 7 | spc_outlook | all | - | {} | 0.023 | 4.9x | 5.7% | 0.035 | 4.5x | 0.669 |
| 8 | nws_warnings | all | - | {} | 0.020 | 4.2x | 3.8% | 0.024 | 3.1x | 0.515 |
| 9 | climatology | all | - | {} | 0.004 | 1.0x | 0.4% | 0.007 | 1.0x | 0.480 |

### >= 10% out · time(train_years=[2020, 2021, 2022, 2023, 2024],test_years=[2025]) · ranked by onset_pr_auc

Event rate: 0.51% of all blocks, 0.26% of onset blocks.

| rank | model | train on | features | params | onset PR-AUC | onset lift | onset prec@top1% | all PR-AUC | all lift | all ROC-AUC |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | xgboost | all | weather+place+recent+warnings+outlook | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.102 | 38.8x | 9.2% | 0.377 | 74.5x | 0.932 |
| 2 | xgboost | all | weather+place+recent | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.083 | 31.5x | 8.7% | 0.378 | 74.7x | 0.930 |
| 3 | xgboost | all | weather+place+warnings+outlook | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.077 | 29.3x | 8.3% | 0.078 | 15.5x | 0.810 |
| 4 | xgboost | all | weather+place | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.062 | 23.7x | 7.5% | 0.058 | 11.5x | 0.796 |
| 5 | official | all | - | {} | 0.034 | 13.0x | 4.8% | 0.037 | 7.4x | 0.680 |
| 6 | xgboost | all | warnings+outlook | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.029 | 11.0x | 5.4% | 0.031 | 6.0x | 0.656 |
| 7 | spc_outlook | all | - | {} | 0.024 | 9.1x | 5.5% | 0.027 | 5.4x | 0.656 |
| 8 | nws_warnings | all | - | {} | 0.024 | 8.9x | 4.2% | 0.021 | 4.2x | 0.560 |
| 9 | climatology | all | - | {} | 0.005 | 1.7x | 1.1% | 0.009 | 1.8x | 0.637 |

### >= 10% out · county(folds=5) · ranked by onset_pr_auc

Event rate: 0.38% of all blocks, 0.23% of onset blocks.

| rank | model | train on | features | params | onset PR-AUC | onset lift | onset prec@top1% | all PR-AUC | all lift | all ROC-AUC |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | xgboost | all | weather+place+recent+warnings+outlook | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.081 | 36.0x | 7.3% | 0.346 | 90.9x | 0.907 |
| 2 | xgboost | all | weather+place+recent | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.068 | 30.1x | 6.8% | 0.333 | 87.6x | 0.905 |
| 3 | xgboost | all | weather+place+warnings+outlook | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.065 | 28.7x | 6.4% | 0.081 | 21.4x | 0.820 |
| 4 | xgboost | all | weather+place | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.054 | 23.8x | 6.0% | 0.058 | 15.3x | 0.811 |
| 5 | xgboost | all | warnings+outlook | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.030 | 13.4x | 3.8% | 0.038 | 9.9x | 0.678 |
| 6 | official | all | - | {} | 0.029 | 12.9x | 4.1% | 0.037 | 9.6x | 0.703 |
| 7 | nws_warnings | all | - | {} | 0.016 | 6.9x | 2.5% | 0.017 | 4.4x | 0.515 |
| 8 | spc_outlook | all | - | {} | 0.015 | 6.7x | 3.4% | 0.022 | 5.9x | 0.677 |
| 9 | climatology | all | - | {} | 0.002 | 0.9x | 0.2% | 0.004 | 0.9x | 0.471 |
