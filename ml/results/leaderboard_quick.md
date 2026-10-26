# Leaderboard: quick

Baselines vs. default model families on 2024 → 2025 and unseen counties, for outages of >= 1%, 5% and 10% of customers in a 6-hour block. Ranked by onset PR-AUC: how well the model predicts NEW outages (the previous block wasn't already an event).

### >= 1% out · time(train_years=[2024],test_years=[2025]) · ranked by onset_pr_auc

Event rate: 3.29% of all blocks, 1.97% of onset blocks.

| rank | model | train on | features | params | onset PR-AUC | onset lift | onset prec@top1% | all PR-AUC | all lift | all ROC-AUC |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | lightgbm | all | weather+place+history+recent | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.135 | 6.9x | 28.1% | 0.384 | 11.7x | 0.863 |
| 2 | xgboost | all | weather+place+history+recent | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 6, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.134 | 6.8x | 28.1% | 0.379 | 11.5x | 0.862 |
| 3 | xgboost | all | weather+place+history | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 6, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.118 | 6.0x | 25.3% | 0.149 | 4.5x | 0.750 |
| 4 | lightgbm | all | weather+place+history | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.115 | 5.8x | 25.0% | 0.147 | 4.5x | 0.750 |
| 5 | logistic | all | weather+place+history+recent | {'class_weight': 'balanced'} | 0.111 | 5.6x | 25.9% | 0.335 | 10.2x | 0.845 |
| 6 | logistic | all | weather+place+history | {'class_weight': 'balanced'} | 0.103 | 5.2x | 24.2% | 0.125 | 3.8x | 0.732 |
| 7 | lightgbm | all | weather | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.095 | 4.8x | 22.7% | 0.116 | 3.5x | 0.704 |
| 8 | xgboost | all | weather | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 6, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.094 | 4.7x | 22.3% | 0.114 | 3.5x | 0.701 |
| 9 | logistic | all | weather | {'class_weight': 'balanced'} | 0.086 | 4.4x | 22.6% | 0.102 | 3.1x | 0.676 |
| 10 | climatology | all | - | {} | 0.029 | 1.4x | 4.5% | 0.048 | 1.5x | 0.606 |
| 11 | prior | all | - | {} | 0.020 | 1.0x | 2.0% | 0.033 | 1.0x | 0.500 |

### >= 1% out · county(folds=5) · ranked by onset_pr_auc

Event rate: 3.01% of all blocks, 1.86% of onset blocks.

| rank | model | train on | features | params | onset PR-AUC | onset lift | onset prec@top1% | all PR-AUC | all lift | all ROC-AUC |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | xgboost | all | weather+place+history+recent | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 6, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.156 | 8.4x | 29.5% | 0.397 | 13.2x | 0.865 |
| 2 | lightgbm | all | weather+place+history+recent | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.154 | 8.3x | 29.4% | 0.394 | 13.1x | 0.865 |
| 3 | xgboost | all | weather+place+history | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 6, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.148 | 8.0x | 28.6% | 0.200 | 6.6x | 0.788 |
| 4 | lightgbm | all | weather+place+history | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.145 | 7.8x | 28.4% | 0.200 | 6.6x | 0.788 |
| 5 | xgboost | all | weather | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 6, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.125 | 6.7x | 26.4% | 0.173 | 5.7x | 0.754 |
| 6 | lightgbm | all | weather | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.124 | 6.7x | 25.9% | 0.175 | 5.8x | 0.755 |
| 7 | logistic | all | weather+place+history+recent | {'class_weight': 'balanced'} | 0.102 | 5.5x | 23.1% | 0.307 | 10.2x | 0.844 |
| 8 | logistic | all | weather+place+history | {'class_weight': 'balanced'} | 0.098 | 5.3x | 22.6% | 0.124 | 4.1x | 0.743 |
| 9 | logistic | all | weather | {'class_weight': 'balanced'} | 0.081 | 4.3x | 20.3% | 0.101 | 3.3x | 0.701 |
| 10 | prior | all | - | {} | 0.018 | 1.0x | 1.8% | 0.029 | 1.0x | 0.490 |
| 11 | climatology | all | - | {} | 0.018 | 1.0x | 1.8% | 0.029 | 1.0x | 0.490 |

### >= 5% out · time(train_years=[2024],test_years=[2025]) · ranked by onset_pr_auc

Event rate: 0.99% of all blocks, 0.53% of onset blocks.

| rank | model | train on | features | params | onset PR-AUC | onset lift | onset prec@top1% | all PR-AUC | all lift | all ROC-AUC |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | xgboost | all | weather+place+history+recent | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 6, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.087 | 16.4x | 12.3% | 0.390 | 39.3x | 0.904 |
| 2 | lightgbm | all | weather+place+history+recent | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.085 | 16.0x | 12.5% | 0.375 | 37.8x | 0.902 |
| 3 | logistic | all | weather+place+history+recent | {'class_weight': 'balanced'} | 0.066 | 12.5x | 12.1% | 0.350 | 35.2x | 0.896 |
| 4 | lightgbm | all | weather+place+history | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.062 | 11.6x | 10.5% | 0.070 | 7.1x | 0.771 |
| 5 | xgboost | all | weather+place+history | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 6, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.061 | 11.5x | 10.9% | 0.069 | 6.9x | 0.773 |
| 6 | logistic | all | weather+place+history | {'class_weight': 'balanced'} | 0.054 | 10.1x | 10.9% | 0.056 | 5.6x | 0.753 |
| 7 | xgboost | all | weather | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 6, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.051 | 9.6x | 9.7% | 0.052 | 5.3x | 0.711 |
| 8 | lightgbm | all | weather | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.048 | 9.0x | 9.7% | 0.052 | 5.3x | 0.713 |
| 9 | logistic | all | weather | {'class_weight': 'balanced'} | 0.046 | 8.6x | 10.0% | 0.045 | 4.5x | 0.687 |
| 10 | climatology | all | - | {} | 0.008 | 1.5x | 1.8% | 0.014 | 1.5x | 0.594 |
| 11 | prior | all | - | {} | 0.005 | 1.0x | 0.5% | 0.010 | 1.0x | 0.500 |

### >= 5% out · county(folds=5) · ranked by onset_pr_auc

Event rate: 0.87% of all blocks, 0.50% of onset blocks.

| rank | model | train on | features | params | onset PR-AUC | onset lift | onset prec@top1% | all PR-AUC | all lift | all ROC-AUC |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | xgboost | all | weather+place+history+recent | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 6, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.111 | 22.2x | 12.6% | 0.400 | 45.7x | 0.900 |
| 2 | lightgbm | all | weather+place+history+recent | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.105 | 20.9x | 12.8% | 0.387 | 44.2x | 0.898 |
| 3 | xgboost | all | weather+place+history | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 6, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.101 | 20.0x | 12.0% | 0.140 | 16.1x | 0.827 |
| 4 | lightgbm | all | weather+place+history | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.094 | 18.7x | 11.9% | 0.137 | 15.6x | 0.825 |
| 5 | xgboost | all | weather | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 6, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.086 | 17.2x | 11.2% | 0.122 | 13.9x | 0.789 |
| 6 | lightgbm | all | weather | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.084 | 16.6x | 10.8% | 0.125 | 14.3x | 0.790 |
| 7 | logistic | all | weather+place+history+recent | {'class_weight': 'balanced'} | 0.058 | 11.5x | 10.2% | 0.313 | 35.8x | 0.890 |
| 8 | logistic | all | weather+place+history | {'class_weight': 'balanced'} | 0.052 | 10.4x | 10.1% | 0.061 | 7.0x | 0.775 |
| 9 | logistic | all | weather | {'class_weight': 'balanced'} | 0.042 | 8.3x | 8.8% | 0.047 | 5.3x | 0.725 |
| 10 | prior | all | - | {} | 0.005 | 1.0x | 0.5% | 0.008 | 1.0x | 0.488 |
| 11 | climatology | all | - | {} | 0.005 | 1.0x | 0.5% | 0.008 | 1.0x | 0.488 |

### >= 10% out · time(train_years=[2024],test_years=[2025]) · ranked by onset_pr_auc

Event rate: 0.51% of all blocks, 0.26% of onset blocks.

| rank | model | train on | features | params | onset PR-AUC | onset lift | onset prec@top1% | all PR-AUC | all lift | all ROC-AUC |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | xgboost | all | weather+place+history+recent | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 6, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.062 | 23.6x | 7.6% | 0.345 | 68.2x | 0.919 |
| 2 | lightgbm | all | weather+place+history+recent | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.055 | 20.9x | 7.5% | 0.330 | 65.3x | 0.916 |
| 3 | logistic | all | weather+place+history+recent | {'class_weight': 'balanced'} | 0.049 | 18.5x | 7.5% | 0.339 | 67.0x | 0.913 |
| 4 | xgboost | all | weather+place+history | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 6, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.041 | 15.4x | 5.7% | 0.045 | 8.9x | 0.788 |
| 5 | logistic | all | weather+place+history | {'class_weight': 'balanced'} | 0.037 | 14.2x | 6.5% | 0.036 | 7.1x | 0.768 |
| 6 | lightgbm | all | weather+place+history | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.036 | 13.5x | 4.9% | 0.037 | 7.4x | 0.780 |
| 7 | logistic | all | weather | {'class_weight': 'balanced'} | 0.031 | 11.9x | 5.9% | 0.029 | 5.7x | 0.689 |
| 8 | xgboost | all | weather | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 6, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.030 | 11.3x | 4.9% | 0.029 | 5.7x | 0.726 |
| 9 | lightgbm | all | weather | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.028 | 10.8x | 4.6% | 0.028 | 5.5x | 0.726 |
| 10 | climatology | all | - | {} | 0.004 | 1.5x | 0.9% | 0.007 | 1.4x | 0.567 |
| 11 | prior | all | - | {} | 0.003 | 1.0x | 0.3% | 0.005 | 1.0x | 0.500 |

### >= 10% out · county(folds=5) · ranked by onset_pr_auc

Event rate: 0.44% of all blocks, 0.25% of onset blocks.

| rank | model | train on | features | params | onset PR-AUC | onset lift | onset prec@top1% | all PR-AUC | all lift | all ROC-AUC |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | xgboost | all | weather+place+history+recent | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 6, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.091 | 36.9x | 8.3% | 0.384 | 87.3x | 0.920 |
| 2 | lightgbm | all | weather+place+history+recent | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.079 | 31.9x | 8.3% | 0.348 | 79.0x | 0.916 |
| 3 | xgboost | all | weather+place+history | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 6, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.077 | 31.3x | 7.5% | 0.102 | 23.1x | 0.851 |
| 4 | xgboost | all | weather | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 6, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.064 | 26.2x | 6.7% | 0.088 | 20.1x | 0.800 |
| 5 | lightgbm | all | weather+place+history | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.064 | 25.9x | 7.2% | 0.092 | 20.9x | 0.849 |
| 6 | lightgbm | all | weather | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.056 | 22.7x | 6.4% | 0.087 | 19.9x | 0.804 |
| 7 | logistic | all | weather+place+history+recent | {'class_weight': 'balanced'} | 0.046 | 18.6x | 6.7% | 0.307 | 69.8x | 0.912 |
| 8 | logistic | all | weather+place+history | {'class_weight': 'balanced'} | 0.040 | 16.2x | 6.1% | 0.042 | 9.6x | 0.794 |
| 9 | logistic | all | weather | {'class_weight': 'balanced'} | 0.031 | 12.5x | 5.5% | 0.031 | 7.1x | 0.737 |
| 10 | prior | all | - | {} | 0.002 | 1.0x | 0.2% | 0.004 | 1.0x | 0.482 |
| 11 | climatology | all | - | {} | 0.002 | 1.0x | 0.2% | 0.004 | 1.0x | 0.482 |
