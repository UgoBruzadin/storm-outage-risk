# Leaderboard: official

NWS warnings and SPC outlooks as baselines, and as features, against the model, at >= 1%, 5% and 10% of customers, on 2024 → 2025 and unseen counties. Ranked by onset PR-AUC.

### >= 1% out · time(train_years=[2024],test_years=[2025]) · ranked by onset_pr_auc

Event rate: 3.29% of all blocks, 1.97% of onset blocks.

| rank | model | train on | features | params | onset PR-AUC | onset lift | onset prec@top1% | all PR-AUC | all lift | all ROC-AUC |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | xgboost | all | weather+place+history+recent+warnings+outlook | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.155 | 7.8x | 29.8% | 0.397 | 12.1x | 0.865 |
| 2 | xgboost | all | weather+place+history+recent | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.139 | 7.1x | 28.5% | 0.385 | 11.7x | 0.863 |
| 3 | xgboost | all | weather+place+history+warnings+outlook | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.139 | 7.0x | 27.7% | 0.184 | 5.6x | 0.763 |
| 4 | xgboost | all | weather+place+history | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.125 | 6.3x | 26.6% | 0.156 | 4.7x | 0.753 |
| 5 | xgboost | all | warnings+outlook | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.068 | 3.4x | 17.6% | 0.099 | 3.0x | 0.651 |
| 6 | official | all | - | {} | 0.062 | 3.2x | 15.0% | 0.091 | 2.8x | 0.648 |
| 7 | spc_outlook | all | - | {} | 0.060 | 3.0x | 19.3% | 0.086 | 2.6x | 0.642 |
| 8 | nws_warnings | all | - | {} | 0.033 | 1.7x | 10.3% | 0.050 | 1.5x | 0.526 |
| 9 | climatology | all | - | {} | 0.029 | 1.4x | 4.5% | 0.048 | 1.5x | 0.606 |

### >= 1% out · county(folds=5) · ranked by onset_pr_auc

Event rate: 3.01% of all blocks, 1.86% of onset blocks.

| rank | model | train on | features | params | onset PR-AUC | onset lift | onset prec@top1% | all PR-AUC | all lift | all ROC-AUC |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | xgboost | all | weather+place+history+recent+warnings+outlook | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.161 | 8.6x | 29.9% | 0.396 | 13.1x | 0.865 |
| 2 | xgboost | all | weather+place+history+warnings+outlook | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.151 | 8.1x | 28.7% | 0.209 | 6.9x | 0.786 |
| 3 | xgboost | all | weather+place+history+recent | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.147 | 7.9x | 28.4% | 0.387 | 12.8x | 0.863 |
| 4 | xgboost | all | weather+place+history | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.141 | 7.6x | 27.6% | 0.182 | 6.1x | 0.781 |
| 5 | xgboost | all | warnings+outlook | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.080 | 4.3x | 18.6% | 0.120 | 4.0x | 0.658 |
| 6 | official | all | - | {} | 0.075 | 4.0x | 18.8% | 0.111 | 3.7x | 0.658 |
| 7 | spc_outlook | all | - | {} | 0.060 | 3.2x | 17.1% | 0.090 | 3.0x | 0.646 |
| 8 | nws_warnings | all | - | {} | 0.034 | 1.9x | 9.1% | 0.053 | 1.8x | 0.513 |
| 9 | climatology | all | - | {} | 0.018 | 1.0x | 1.8% | 0.029 | 1.0x | 0.490 |

### >= 5% out · time(train_years=[2024],test_years=[2025]) · ranked by onset_pr_auc

Event rate: 0.99% of all blocks, 0.53% of onset blocks.

| rank | model | train on | features | params | onset PR-AUC | onset lift | onset prec@top1% | all PR-AUC | all lift | all ROC-AUC |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | xgboost | all | weather+place+history+recent+warnings+outlook | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.115 | 21.6x | 14.2% | 0.403 | 40.6x | 0.908 |
| 2 | xgboost | all | weather+place+history+recent | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.089 | 16.8x | 12.7% | 0.389 | 39.2x | 0.907 |
| 3 | xgboost | all | weather+place+history+warnings+outlook | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.088 | 16.5x | 12.6% | 0.107 | 10.8x | 0.790 |
| 4 | xgboost | all | weather+place+history | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.074 | 13.8x | 11.3% | 0.078 | 7.8x | 0.781 |
| 5 | xgboost | all | warnings+outlook | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.045 | 8.5x | 9.0% | 0.050 | 5.1x | 0.654 |
| 6 | official | all | - | {} | 0.035 | 6.6x | 7.0% | 0.045 | 4.5x | 0.649 |
| 7 | spc_outlook | all | - | {} | 0.032 | 6.0x | 8.6% | 0.040 | 4.1x | 0.653 |
| 8 | nws_warnings | all | - | {} | 0.024 | 4.6x | 5.8% | 0.028 | 2.8x | 0.549 |
| 9 | climatology | all | - | {} | 0.008 | 1.5x | 1.8% | 0.014 | 1.5x | 0.594 |

### >= 5% out · county(folds=5) · ranked by onset_pr_auc

Event rate: 0.87% of all blocks, 0.50% of onset blocks.

| rank | model | train on | features | params | onset PR-AUC | onset lift | onset prec@top1% | all PR-AUC | all lift | all ROC-AUC |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | xgboost | all | weather+place+history+recent+warnings+outlook | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.119 | 23.7x | 13.4% | 0.397 | 45.4x | 0.900 |
| 2 | xgboost | all | weather+place+history+warnings+outlook | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.108 | 21.6x | 12.4% | 0.153 | 17.4x | 0.826 |
| 3 | xgboost | all | weather+place+history+recent | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.104 | 20.8x | 12.7% | 0.391 | 44.7x | 0.898 |
| 4 | xgboost | all | weather+place+history | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.097 | 19.2x | 12.1% | 0.124 | 14.2x | 0.820 |
| 5 | xgboost | all | warnings+outlook | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.057 | 11.4x | 8.9% | 0.078 | 8.9x | 0.688 |
| 6 | official | all | - | {} | 0.050 | 10.0x | 8.2% | 0.067 | 7.7x | 0.687 |
| 7 | spc_outlook | all | - | {} | 0.031 | 6.1x | 7.6% | 0.044 | 5.1x | 0.663 |
| 8 | nws_warnings | all | - | {} | 0.027 | 5.5x | 4.7% | 0.033 | 3.8x | 0.528 |
| 9 | climatology | all | - | {} | 0.005 | 1.0x | 0.3% | 0.008 | 1.0x | 0.488 |

### >= 10% out · time(train_years=[2024],test_years=[2025]) · ranked by onset_pr_auc

Event rate: 0.51% of all blocks, 0.26% of onset blocks.

| rank | model | train on | features | params | onset PR-AUC | onset lift | onset prec@top1% | all PR-AUC | all lift | all ROC-AUC |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | xgboost | all | weather+place+history+recent+warnings+outlook | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.088 | 33.4x | 8.8% | 0.370 | 73.2x | 0.925 |
| 2 | xgboost | all | weather+place+history+recent | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.068 | 25.6x | 7.9% | 0.353 | 69.8x | 0.922 |
| 3 | xgboost | all | weather+place+history+warnings+outlook | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.063 | 24.0x | 7.2% | 0.070 | 13.7x | 0.813 |
| 4 | xgboost | all | weather+place+history | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.046 | 17.3x | 6.3% | 0.048 | 9.5x | 0.800 |
| 5 | xgboost | all | warnings+outlook | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.036 | 13.9x | 5.8% | 0.035 | 7.0x | 0.656 |
| 6 | official | all | - | {} | 0.029 | 11.0x | 4.6% | 0.032 | 6.4x | 0.649 |
| 7 | nws_warnings | all | - | {} | 0.023 | 8.8x | 4.2% | 0.020 | 4.0x | 0.560 |
| 8 | spc_outlook | all | - | {} | 0.023 | 8.6x | 5.4% | 0.027 | 5.3x | 0.656 |
| 9 | climatology | all | - | {} | 0.004 | 1.5x | 0.9% | 0.007 | 1.4x | 0.567 |

### >= 10% out · county(folds=5) · ranked by onset_pr_auc

Event rate: 0.44% of all blocks, 0.25% of onset blocks.

| rank | model | train on | features | params | onset PR-AUC | onset lift | onset prec@top1% | all PR-AUC | all lift | all ROC-AUC |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | xgboost | all | weather+place+history+recent+warnings+outlook | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.099 | 40.1x | 8.6% | 0.378 | 85.9x | 0.921 |
| 2 | xgboost | all | weather+place+history+warnings+outlook | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.086 | 34.8x | 7.5% | 0.115 | 26.1x | 0.852 |
| 3 | xgboost | all | weather+place+history+recent | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.082 | 33.5x | 8.0% | 0.374 | 85.0x | 0.918 |
| 4 | xgboost | all | weather+place+history | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.074 | 30.0x | 7.4% | 0.089 | 20.2x | 0.846 |
| 5 | xgboost | all | warnings+outlook | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.046 | 18.8x | 5.6% | 0.057 | 12.9x | 0.701 |
| 6 | official | all | - | {} | 0.040 | 16.1x | 5.2% | 0.049 | 11.1x | 0.697 |
| 7 | nws_warnings | all | - | {} | 0.024 | 9.9x | 3.3% | 0.024 | 5.5x | 0.533 |
| 8 | spc_outlook | all | - | {} | 0.022 | 9.0x | 4.7% | 0.030 | 6.9x | 0.672 |
| 9 | climatology | all | - | {} | 0.002 | 1.0x | 0.3% | 0.004 | 1.0x | 0.482 |
