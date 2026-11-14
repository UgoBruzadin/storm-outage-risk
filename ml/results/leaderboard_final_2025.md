# Leaderboard: final_2025

Final XGBoost settings (chosen on 2024) trained on 2020–2024, tested on 2025, and on unseen counties, at >= 1%, 5% and 10% of customers. Ranked by onset PR-AUC.

### >= 1% out · time(train_years=[2020, 2021, 2022, 2023, 2024],test_years=[2025]) · ranked by onset_pr_auc

Event rate: 3.86% of all blocks, 2.26% of onset blocks.

| rank | model | train on | features | params | onset PR-AUC | onset lift | onset prec@top1% | all PR-AUC | all lift | all ROC-AUC |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | xgboost | all | weather+place+history+recent | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.162 | 7.2x | 32.0% | 0.437 | 11.3x | 0.879 |
| 2 | xgboost | all | weather+place+recent | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.151 | 6.7x | 30.8% | 0.429 | 11.1x | 0.870 |
| 3 | xgboost | all | weather+place+recent+wet_soil | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.151 | 6.7x | 30.8% | 0.433 | 11.2x | 0.870 |
| 4 | xgboost | all | weather+place+history | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.147 | 6.5x | 30.0% | 0.224 | 5.8x | 0.800 |
| 5 | xgboost | all | weather+place | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.134 | 5.9x | 28.6% | 0.201 | 5.2x | 0.776 |
| 6 | xgboost | all | weather | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.107 | 4.7x | 24.6% | 0.140 | 3.6x | 0.713 |
| 7 | climatology | all | - | {} | 0.050 | 2.2x | 9.5% | 0.111 | 2.9x | 0.705 |

### >= 1% out · county(folds=5) · ranked by onset_pr_auc

Event rate: 3.55% of all blocks, 2.08% of onset blocks.

| rank | model | train on | features | params | onset PR-AUC | onset lift | onset prec@top1% | all PR-AUC | all lift | all ROC-AUC |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | xgboost | all | weather+place+history+recent | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.159 | 7.6x | 31.1% | 0.437 | 12.3x | 0.881 |
| 2 | xgboost | all | weather+place+history | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.145 | 7.0x | 29.0% | 0.206 | 5.8x | 0.795 |
| 3 | xgboost | all | weather+place+recent+wet_soil | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.140 | 6.7x | 28.5% | 0.425 | 12.0x | 0.868 |
| 4 | xgboost | all | weather+place+recent | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.140 | 6.7x | 28.4% | 0.422 | 11.9x | 0.868 |
| 5 | xgboost | all | weather+place | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.116 | 5.6x | 25.4% | 0.160 | 4.5x | 0.744 |
| 6 | xgboost | all | weather | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.106 | 5.1x | 24.0% | 0.142 | 4.0x | 0.717 |
| 7 | climatology | all | - | {} | 0.020 | 1.0x | 2.0% | 0.035 | 1.0x | 0.487 |

### >= 5% out · time(train_years=[2020, 2021, 2022, 2023, 2024],test_years=[2025]) · ranked by onset_pr_auc

Event rate: 1.11% of all blocks, 0.64% of onset blocks.

| rank | model | train on | features | params | onset PR-AUC | onset lift | onset prec@top1% | all PR-AUC | all lift | all ROC-AUC |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | xgboost | all | weather+place+history+recent | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.105 | 16.3x | 15.3% | 0.391 | 35.3x | 0.912 |
| 2 | xgboost | all | weather+place+recent | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.099 | 15.4x | 14.7% | 0.387 | 35.0x | 0.905 |
| 3 | xgboost | all | weather+place+recent+wet_soil | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.099 | 15.4x | 14.6% | 0.391 | 35.3x | 0.905 |
| 4 | xgboost | all | weather+place+history | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.092 | 14.3x | 14.0% | 0.130 | 11.7x | 0.830 |
| 5 | xgboost | all | weather+place | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.085 | 13.2x | 13.5% | 0.120 | 10.8x | 0.814 |
| 6 | xgboost | all | weather | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.055 | 8.5x | 10.6% | 0.064 | 5.8x | 0.729 |
| 7 | climatology | all | - | {} | 0.022 | 3.4x | 4.2% | 0.054 | 4.9x | 0.719 |

### >= 5% out · county(folds=5) · ranked by onset_pr_auc

Event rate: 1.08% of all blocks, 0.59% of onset blocks.

| rank | model | train on | features | params | onset PR-AUC | onset lift | onset prec@top1% | all PR-AUC | all lift | all ROC-AUC |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | xgboost | all | weather+place+history+recent | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.108 | 18.2x | 14.6% | 0.437 | 40.5x | 0.916 |
| 2 | xgboost | all | weather+place+recent | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.096 | 16.1x | 13.6% | 0.429 | 39.8x | 0.907 |
| 3 | xgboost | all | weather+place+recent+wet_soil | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.096 | 16.1x | 13.6% | 0.433 | 40.2x | 0.907 |
| 4 | xgboost | all | weather+place+history | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.096 | 16.1x | 13.4% | 0.125 | 11.6x | 0.829 |
| 5 | xgboost | all | weather+place | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.078 | 13.1x | 11.9% | 0.101 | 9.4x | 0.790 |
| 6 | xgboost | all | weather | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.063 | 10.6x | 10.5% | 0.079 | 7.3x | 0.739 |
| 7 | climatology | all | - | {} | 0.006 | 1.0x | 0.5% | 0.010 | 1.0x | 0.487 |

### >= 10% out · time(train_years=[2020, 2021, 2022, 2023, 2024],test_years=[2025]) · ranked by onset_pr_auc

Event rate: 0.55% of all blocks, 0.32% of onset blocks.

| rank | model | train on | features | params | onset PR-AUC | onset lift | onset prec@top1% | all PR-AUC | all lift | all ROC-AUC |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | xgboost | all | weather+place+history+recent | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.086 | 27.2x | 9.5% | 0.373 | 67.5x | 0.932 |
| 2 | xgboost | all | weather+place+recent+wet_soil | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.081 | 25.7x | 9.2% | 0.376 | 67.9x | 0.926 |
| 3 | xgboost | all | weather+place+recent | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.080 | 25.4x | 9.2% | 0.370 | 67.0x | 0.926 |
| 4 | xgboost | all | weather+place+history | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.070 | 22.2x | 8.4% | 0.098 | 17.7x | 0.849 |
| 5 | xgboost | all | weather+place | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.067 | 21.2x | 8.2% | 0.094 | 17.0x | 0.835 |
| 6 | xgboost | all | weather | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.034 | 10.7x | 5.9% | 0.038 | 6.8x | 0.730 |
| 7 | climatology | all | - | {} | 0.017 | 5.5x | 2.7% | 0.039 | 7.1x | 0.731 |

### >= 10% out · county(folds=5) · ranked by onset_pr_auc

Event rate: 0.56% of all blocks, 0.29% of onset blocks.

| rank | model | train on | features | params | onset PR-AUC | onset lift | onset prec@top1% | all PR-AUC | all lift | all ROC-AUC |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | xgboost | all | weather+place+history+recent | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.089 | 30.6x | 9.1% | 0.455 | 80.8x | 0.937 |
| 2 | xgboost | all | weather+place+recent+wet_soil | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.080 | 27.3x | 8.5% | 0.452 | 80.2x | 0.929 |
| 3 | xgboost | all | weather+place+recent | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.079 | 27.3x | 8.5% | 0.448 | 79.5x | 0.929 |
| 4 | xgboost | all | weather+place+history | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.077 | 26.3x | 8.0% | 0.099 | 17.6x | 0.852 |
| 5 | xgboost | all | weather+place | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.062 | 21.3x | 7.1% | 0.082 | 14.5x | 0.816 |
| 6 | xgboost | all | weather | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.047 | 16.1x | 6.1% | 0.060 | 10.6x | 0.751 |
| 7 | climatology | all | - | {} | 0.003 | 1.0x | 0.3% | 0.005 | 1.0x | 0.484 |
