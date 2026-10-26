# Leaderboard: official

NWS warnings and SPC outlooks as baselines, and as features, against the model, at >= 1%, 5% and 10% of customers, on 2024 → 2025 and unseen counties. Ranked by onset PR-AUC.

### >= 1% out · time(train_years=[2024],test_years=[2025]) · ranked by onset_pr_auc

Event rate: 3.29% of all blocks, 1.97% of onset blocks.

| rank | model | train on | features | params | onset PR-AUC | onset lift | onset prec@top1% | all PR-AUC | all lift | all ROC-AUC |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | xgboost | all | weather+place+history+recent+warnings+outlook | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.173 | 8.8x | 33.3% | 0.404 | 12.3x | 0.867 |
| 2 | xgboost | all | weather+place+history+warnings+outlook | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.156 | 7.9x | 31.0% | 0.192 | 5.8x | 0.765 |
| 3 | xgboost | all | weather+place+history+recent | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.140 | 7.1x | 28.4% | 0.385 | 11.7x | 0.863 |
| 4 | xgboost | all | weather+place+history | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.126 | 6.4x | 26.1% | 0.156 | 4.7x | 0.753 |
| 5 | xgboost | all | warnings+outlook | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.090 | 4.6x | 20.7% | 0.111 | 3.4x | 0.651 |
| 6 | official | all | - | {} | 0.083 | 4.2x | 22.2% | 0.105 | 3.2x | 0.652 |
| 7 | nws_warnings | all | - | {} | 0.069 | 3.5x | 26.9% | 0.077 | 2.3x | 0.562 |
| 8 | spc_outlook | all | - | {} | 0.060 | 3.0x | 19.0% | 0.086 | 2.6x | 0.642 |
| 9 | climatology | all | - | {} | 0.029 | 1.4x | 4.5% | 0.048 | 1.5x | 0.606 |

### >= 1% out · county(folds=5) · ranked by onset_pr_auc

Event rate: 3.01% of all blocks, 1.86% of onset blocks.

| rank | model | train on | features | params | onset PR-AUC | onset lift | onset prec@top1% | all PR-AUC | all lift | all ROC-AUC |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | xgboost | all | weather+place+history+recent+warnings+outlook | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.177 | 9.5x | 33.4% | 0.404 | 13.4x | 0.867 |
| 2 | xgboost | all | weather+place+history+warnings+outlook | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.165 | 8.9x | 32.1% | 0.216 | 7.2x | 0.788 |
| 3 | xgboost | all | weather+place+history+recent | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.147 | 7.9x | 28.5% | 0.387 | 12.8x | 0.863 |
| 4 | xgboost | all | weather+place+history | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.141 | 7.6x | 27.6% | 0.182 | 6.0x | 0.780 |
| 5 | xgboost | all | warnings+outlook | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.107 | 5.7x | 27.5% | 0.132 | 4.4x | 0.660 |
| 6 | official | all | - | {} | 0.101 | 5.4x | 27.2% | 0.126 | 4.2x | 0.660 |
| 7 | nws_warnings | all | - | {} | 0.076 | 4.1x | 27.8% | 0.083 | 2.8x | 0.552 |
| 8 | spc_outlook | all | - | {} | 0.060 | 3.2x | 17.1% | 0.090 | 3.0x | 0.646 |
| 9 | climatology | all | - | {} | 0.018 | 1.0x | 1.8% | 0.029 | 1.0x | 0.490 |

### >= 5% out · time(train_years=[2024],test_years=[2025]) · ranked by onset_pr_auc

Event rate: 0.99% of all blocks, 0.53% of onset blocks.

| rank | model | train on | features | params | onset PR-AUC | onset lift | onset prec@top1% | all PR-AUC | all lift | all ROC-AUC |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | xgboost | all | weather+place+history+recent+warnings+outlook | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.132 | 24.8x | 15.8% | 0.408 | 41.2x | 0.910 |
| 2 | xgboost | all | weather+place+history+warnings+outlook | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.102 | 19.1x | 14.2% | 0.112 | 11.3x | 0.790 |
| 3 | xgboost | all | weather+place+history+recent | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.091 | 17.0x | 13.3% | 0.393 | 39.6x | 0.906 |
| 4 | xgboost | all | weather+place+history | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.073 | 13.7x | 11.3% | 0.077 | 7.8x | 0.778 |
| 5 | xgboost | all | warnings+outlook | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.063 | 11.8x | 11.9% | 0.058 | 5.8x | 0.655 |
| 6 | official | all | - | {} | 0.051 | 9.7x | 7.6% | 0.053 | 5.3x | 0.653 |
| 7 | nws_warnings | all | - | {} | 0.044 | 8.3x | 8.5% | 0.040 | 4.0x | 0.598 |
| 8 | spc_outlook | all | - | {} | 0.032 | 6.0x | 8.7% | 0.040 | 4.1x | 0.653 |
| 9 | climatology | all | - | {} | 0.008 | 1.5x | 1.7% | 0.014 | 1.5x | 0.594 |

### >= 5% out · county(folds=5) · ranked by onset_pr_auc

Event rate: 0.87% of all blocks, 0.50% of onset blocks.

| rank | model | train on | features | params | onset PR-AUC | onset lift | onset prec@top1% | all PR-AUC | all lift | all ROC-AUC |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | xgboost | all | weather+place+history+recent+warnings+outlook | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.133 | 26.6x | 14.7% | 0.406 | 46.5x | 0.902 |
| 2 | xgboost | all | weather+place+history+warnings+outlook | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.119 | 23.7x | 13.8% | 0.157 | 17.9x | 0.828 |
| 3 | xgboost | all | weather+place+history+recent | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.103 | 20.5x | 12.6% | 0.391 | 44.7x | 0.898 |
| 4 | xgboost | all | weather+place+history | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.096 | 19.1x | 12.0% | 0.122 | 14.0x | 0.819 |
| 5 | xgboost | all | warnings+outlook | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.078 | 15.5x | 11.8% | 0.086 | 9.8x | 0.690 |
| 6 | official | all | - | {} | 0.074 | 14.8x | 11.9% | 0.080 | 9.2x | 0.689 |
| 7 | nws_warnings | all | - | {} | 0.057 | 11.4x | 11.9% | 0.052 | 5.9x | 0.583 |
| 8 | spc_outlook | all | - | {} | 0.031 | 6.1x | 7.6% | 0.044 | 5.1x | 0.663 |
| 9 | climatology | all | - | {} | 0.005 | 1.0x | 0.5% | 0.008 | 1.0x | 0.488 |

### >= 10% out · time(train_years=[2024],test_years=[2025]) · ranked by onset_pr_auc

Event rate: 0.51% of all blocks, 0.26% of onset blocks.

| rank | model | train on | features | params | onset PR-AUC | onset lift | onset prec@top1% | all PR-AUC | all lift | all ROC-AUC |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | xgboost | all | weather+place+history+recent+warnings+outlook | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.101 | 38.4x | 9.8% | 0.367 | 72.5x | 0.928 |
| 2 | xgboost | all | weather+place+history+warnings+outlook | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.078 | 29.7x | 7.8% | 0.079 | 15.5x | 0.815 |
| 3 | xgboost | all | weather+place+history+recent | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.069 | 26.1x | 7.8% | 0.360 | 71.1x | 0.922 |
| 4 | xgboost | all | warnings+outlook | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.046 | 17.5x | 7.0% | 0.039 | 7.7x | 0.658 |
| 5 | xgboost | all | weather+place+history | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.045 | 17.1x | 6.3% | 0.047 | 9.4x | 0.802 |
| 6 | official | all | - | {} | 0.039 | 14.7x | 4.8% | 0.037 | 7.2x | 0.648 |
| 7 | nws_warnings | all | - | {} | 0.034 | 12.8x | 5.2% | 0.027 | 5.2x | 0.612 |
| 8 | spc_outlook | all | - | {} | 0.023 | 8.6x | 5.4% | 0.027 | 5.3x | 0.656 |
| 9 | climatology | all | - | {} | 0.004 | 1.5x | 0.9% | 0.007 | 1.4x | 0.567 |

### >= 10% out · county(folds=5) · ranked by onset_pr_auc

Event rate: 0.44% of all blocks, 0.25% of onset blocks.

| rank | model | train on | features | params | onset PR-AUC | onset lift | onset prec@top1% | all PR-AUC | all lift | all ROC-AUC |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | xgboost | all | weather+place+history+recent+warnings+outlook | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.110 | 44.7x | 9.4% | 0.385 | 87.5x | 0.922 |
| 2 | xgboost | all | weather+place+history+warnings+outlook | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.095 | 38.8x | 8.6% | 0.121 | 27.4x | 0.853 |
| 3 | xgboost | all | weather+place+history+recent | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.083 | 33.6x | 8.0% | 0.373 | 84.9x | 0.919 |
| 4 | xgboost | all | weather+place+history | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.072 | 29.2x | 7.5% | 0.087 | 19.7x | 0.846 |
| 5 | xgboost | all | warnings+outlook | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.058 | 23.5x | 7.4% | 0.061 | 13.8x | 0.702 |
| 6 | official | all | - | {} | 0.056 | 22.8x | 7.2% | 0.057 | 13.0x | 0.698 |
| 7 | nws_warnings | all | - | {} | 0.044 | 18.0x | 7.1% | 0.036 | 8.2x | 0.595 |
| 8 | spc_outlook | all | - | {} | 0.022 | 9.0x | 4.8% | 0.030 | 6.9x | 0.672 |
| 9 | climatology | all | - | {} | 0.002 | 1.0x | 0.2% | 0.004 | 1.0x | 0.482 |
