# Leaderboard: final_2025

Final XGBoost settings (chosen on 2024) trained on 2020–2024, tested on 2025, and on unseen counties, at >= 1%, 5% and 10% of customers. Ranked by onset PR-AUC.

### >= 1% out · time(train_years=[2020, 2021, 2022, 2023, 2024],test_years=[2025]) · ranked by onset_pr_auc

Event rate: 3.29% of all blocks, 1.84% of onset blocks.

| rank | model | train on | features | params | onset PR-AUC | onset lift | onset prec@top1% | all PR-AUC | all lift | all ROC-AUC |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | xgboost | all | weather+place+history+recent | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.161 | 8.7x | 30.7% | 0.468 | 14.2x | 0.882 |
| 2 | xgboost | all | weather+place+recent+wet_soil | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.158 | 8.6x | 30.8% | 0.468 | 14.2x | 0.880 |
| 3 | xgboost | all | weather+place+recent | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.158 | 8.6x | 30.8% | 0.467 | 14.2x | 0.880 |
| 4 | xgboost | all | weather+place+history | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.144 | 7.8x | 29.0% | 0.182 | 5.5x | 0.768 |
| 5 | xgboost | all | weather+place | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.142 | 7.7x | 28.7% | 0.180 | 5.5x | 0.763 |
| 6 | xgboost | all | weather | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.114 | 6.2x | 25.7% | 0.139 | 4.2x | 0.710 |
| 7 | climatology | all | - | {} | 0.033 | 1.8x | 6.2% | 0.064 | 1.9x | 0.651 |

### >= 1% out · county(folds=5) · ranked by onset_pr_auc

Event rate: 2.85% of all blocks, 1.67% of onset blocks.

| rank | model | train on | features | params | onset PR-AUC | onset lift | onset prec@top1% | all PR-AUC | all lift | all ROC-AUC |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | xgboost | all | weather+place+history+recent | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.142 | 8.5x | 27.1% | 0.426 | 15.0x | 0.870 |
| 2 | xgboost | all | weather+place+history | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.133 | 8.0x | 26.0% | 0.175 | 6.1x | 0.773 |
| 3 | xgboost | all | weather+place+recent+wet_soil | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.131 | 7.9x | 26.0% | 0.420 | 14.8x | 0.863 |
| 4 | xgboost | all | weather+place+recent | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.131 | 7.8x | 25.8% | 0.418 | 14.7x | 0.862 |
| 5 | xgboost | all | weather+place | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.118 | 7.1x | 24.5% | 0.153 | 5.4x | 0.747 |
| 6 | xgboost | all | weather | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.109 | 6.5x | 23.3% | 0.140 | 4.9x | 0.733 |
| 7 | climatology | all | - | {} | 0.016 | 1.0x | 1.7% | 0.028 | 1.0x | 0.492 |

### >= 5% out · time(train_years=[2020, 2021, 2022, 2023, 2024],test_years=[2025]) · ranked by onset_pr_auc

Event rate: 1.05% of all blocks, 0.50% of onset blocks.

| rank | model | train on | features | params | onset PR-AUC | onset lift | onset prec@top1% | all PR-AUC | all lift | all ROC-AUC |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | xgboost | all | weather+place+history+recent | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.130 | 26.0x | 15.0% | 0.518 | 49.3x | 0.930 |
| 2 | xgboost | all | weather+place+recent | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.129 | 25.8x | 14.8% | 0.520 | 49.5x | 0.929 |
| 3 | xgboost | all | weather+place+recent+wet_soil | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.128 | 25.5x | 15.0% | 0.516 | 49.2x | 0.929 |
| 4 | xgboost | all | weather+place+history | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.092 | 18.3x | 13.4% | 0.095 | 9.1x | 0.784 |
| 5 | xgboost | all | weather+place | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.092 | 18.3x | 13.4% | 0.098 | 9.3x | 0.777 |
| 6 | xgboost | all | weather | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.068 | 13.6x | 11.8% | 0.069 | 6.6x | 0.713 |
| 7 | climatology | all | - | {} | 0.010 | 1.9x | 1.8% | 0.021 | 2.0x | 0.659 |

### >= 5% out · county(folds=5) · ranked by onset_pr_auc

Event rate: 0.84% of all blocks, 0.45% of onset blocks.

| rank | model | train on | features | params | onset PR-AUC | onset lift | onset prec@top1% | all PR-AUC | all lift | all ROC-AUC |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | xgboost | all | weather+place+history+recent | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.107 | 23.7x | 12.2% | 0.452 | 53.6x | 0.912 |
| 2 | xgboost | all | weather+place+recent+wet_soil | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.099 | 21.8x | 11.8% | 0.450 | 53.4x | 0.907 |
| 3 | xgboost | all | weather+place+recent | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.098 | 21.7x | 11.8% | 0.447 | 53.1x | 0.907 |
| 4 | xgboost | all | weather+place+history | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.093 | 20.5x | 11.3% | 0.109 | 13.0x | 0.815 |
| 5 | xgboost | all | weather+place | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.083 | 18.3x | 10.9% | 0.096 | 11.4x | 0.794 |
| 6 | xgboost | all | weather | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.073 | 16.0x | 10.1% | 0.083 | 9.9x | 0.769 |
| 7 | climatology | all | - | {} | 0.004 | 1.0x | 0.4% | 0.008 | 1.0x | 0.491 |

### >= 10% out · time(train_years=[2020, 2021, 2022, 2023, 2024],test_years=[2025]) · ranked by onset_pr_auc

Event rate: 0.56% of all blocks, 0.25% of onset blocks.

| rank | model | train on | features | params | onset PR-AUC | onset lift | onset prec@top1% | all PR-AUC | all lift | all ROC-AUC |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | xgboost | all | weather+place+recent+wet_soil | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.110 | 44.7x | 9.3% | 0.529 | 93.9x | 0.950 |
| 2 | xgboost | all | weather+place+history+recent | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.106 | 43.0x | 9.2% | 0.521 | 92.5x | 0.950 |
| 3 | xgboost | all | weather+place+recent | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.103 | 41.6x | 9.2% | 0.522 | 92.6x | 0.950 |
| 4 | xgboost | all | weather+place+history | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.061 | 24.6x | 7.6% | 0.059 | 10.5x | 0.794 |
| 5 | xgboost | all | weather+place | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.060 | 24.3x | 7.8% | 0.061 | 10.8x | 0.781 |
| 6 | xgboost | all | weather | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.043 | 17.5x | 6.4% | 0.041 | 7.3x | 0.717 |
| 7 | climatology | all | - | {} | 0.005 | 1.9x | 0.6% | 0.011 | 2.0x | 0.661 |

### >= 10% out · county(folds=5) · ranked by onset_pr_auc

Event rate: 0.42% of all blocks, 0.21% of onset blocks.

| rank | model | train on | features | params | onset PR-AUC | onset lift | onset prec@top1% | all PR-AUC | all lift | all ROC-AUC |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | xgboost | all | weather+place+history+recent | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.094 | 44.4x | 7.4% | 0.475 | 112.3x | 0.933 |
| 2 | xgboost | all | weather+place+recent+wet_soil | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.090 | 42.4x | 7.1% | 0.474 | 112.1x | 0.929 |
| 3 | xgboost | all | weather+place+recent | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.088 | 41.5x | 7.2% | 0.472 | 111.6x | 0.929 |
| 4 | xgboost | all | weather+place+history | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.075 | 35.3x | 6.6% | 0.084 | 19.8x | 0.840 |
| 5 | xgboost | all | weather+place | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.068 | 32.1x | 6.4% | 0.075 | 17.7x | 0.820 |
| 6 | xgboost | all | weather | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.059 | 27.7x | 5.8% | 0.064 | 15.1x | 0.791 |
| 7 | climatology | all | - | {} | 0.002 | 1.0x | 0.2% | 0.004 | 1.0x | 0.484 |
