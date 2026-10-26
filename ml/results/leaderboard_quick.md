# Leaderboard: quick

Baselines vs. default model families on 2024 → 2025 and unseen counties, for outages of >= 1%, 5% and 10% of customers in a 6-hour block. Ranked by onset PR-AUC: how well the model predicts NEW outages (the previous block wasn't already an event).

### >= 1% out · time(train_years=[2024],test_years=[2025]) · ranked by onset_pr_auc

Event rate: 3.29% of all blocks, 1.97% of onset blocks.

| rank | model | train on | features | params | onset PR-AUC | onset lift | onset prec@top1% | all PR-AUC | all lift | all ROC-AUC |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | lightgbm | all | weather+place+history+recent | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.138 | 7.0x | 28.2% | 0.385 | 11.7x | 0.863 |
| 2 | lightgbm | all | weather+place+history | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.114 | 5.8x | 24.8% | 0.146 | 4.4x | 0.749 |
| 3 | logistic | all | weather+place+history+recent | {'class_weight': 'balanced'} | 0.111 | 5.6x | 25.9% | 0.335 | 10.2x | 0.845 |
| 4 | logistic | all | weather+place+history | {'class_weight': 'balanced'} | 0.103 | 5.2x | 24.2% | 0.125 | 3.8x | 0.732 |
| 5 | lightgbm | all | weather | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.094 | 4.8x | 22.1% | 0.115 | 3.5x | 0.702 |
| 6 | logistic | all | weather | {'class_weight': 'balanced'} | 0.086 | 4.4x | 22.6% | 0.102 | 3.1x | 0.676 |
| 7 | climatology | all | - | {} | 0.029 | 1.4x | 4.5% | 0.048 | 1.5x | 0.606 |
| 8 | prior | all | - | {} | 0.020 | 1.0x | 2.0% | 0.033 | 1.0x | 0.500 |

### >= 1% out · county(folds=5) · ranked by onset_pr_auc

Event rate: 3.01% of all blocks, 1.86% of onset blocks.

| rank | model | train on | features | params | onset PR-AUC | onset lift | onset prec@top1% | all PR-AUC | all lift | all ROC-AUC |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | lightgbm | all | weather+place+history+recent | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.155 | 8.3x | 29.7% | 0.395 | 13.1x | 0.865 |
| 2 | lightgbm | all | weather+place+history | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.145 | 7.8x | 28.1% | 0.200 | 6.6x | 0.788 |
| 3 | lightgbm | all | weather | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.123 | 6.6x | 26.3% | 0.174 | 5.8x | 0.755 |
| 4 | logistic | all | weather+place+history+recent | {'class_weight': 'balanced'} | 0.102 | 5.5x | 23.1% | 0.307 | 10.2x | 0.844 |
| 5 | logistic | all | weather+place+history | {'class_weight': 'balanced'} | 0.098 | 5.3x | 22.6% | 0.124 | 4.1x | 0.743 |
| 6 | logistic | all | weather | {'class_weight': 'balanced'} | 0.081 | 4.3x | 20.3% | 0.101 | 3.3x | 0.701 |
| 7 | prior | all | - | {} | 0.018 | 1.0x | 1.8% | 0.029 | 1.0x | 0.490 |
| 8 | climatology | all | - | {} | 0.018 | 1.0x | 1.8% | 0.029 | 1.0x | 0.490 |

### >= 5% out · time(train_years=[2024],test_years=[2025]) · ranked by onset_pr_auc

Event rate: 0.99% of all blocks, 0.53% of onset blocks.

| rank | model | train on | features | params | onset PR-AUC | onset lift | onset prec@top1% | all PR-AUC | all lift | all ROC-AUC |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | lightgbm | all | weather+place+history+recent | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.087 | 16.3x | 12.4% | 0.380 | 38.3x | 0.902 |
| 2 | logistic | all | weather+place+history+recent | {'class_weight': 'balanced'} | 0.066 | 12.5x | 12.1% | 0.350 | 35.2x | 0.896 |
| 3 | lightgbm | all | weather+place+history | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.057 | 10.7x | 9.9% | 0.065 | 6.6x | 0.770 |
| 4 | lightgbm | all | weather | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.055 | 10.4x | 9.8% | 0.057 | 5.7x | 0.713 |
| 5 | logistic | all | weather+place+history | {'class_weight': 'balanced'} | 0.054 | 10.1x | 10.9% | 0.056 | 5.6x | 0.753 |
| 6 | logistic | all | weather | {'class_weight': 'balanced'} | 0.046 | 8.6x | 10.0% | 0.045 | 4.5x | 0.687 |
| 7 | climatology | all | - | {} | 0.008 | 1.5x | 1.8% | 0.014 | 1.5x | 0.594 |
| 8 | prior | all | - | {} | 0.005 | 1.0x | 0.5% | 0.010 | 1.0x | 0.500 |

### >= 5% out · county(folds=5) · ranked by onset_pr_auc

Event rate: 0.87% of all blocks, 0.50% of onset blocks.

| rank | model | train on | features | params | onset PR-AUC | onset lift | onset prec@top1% | all PR-AUC | all lift | all ROC-AUC |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | lightgbm | all | weather+place+history+recent | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.110 | 21.8x | 12.8% | 0.390 | 44.6x | 0.898 |
| 2 | lightgbm | all | weather+place+history | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.091 | 18.0x | 11.8% | 0.135 | 15.4x | 0.824 |
| 3 | lightgbm | all | weather | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.080 | 16.0x | 10.9% | 0.124 | 14.1x | 0.790 |
| 4 | logistic | all | weather+place+history+recent | {'class_weight': 'balanced'} | 0.058 | 11.5x | 10.2% | 0.313 | 35.8x | 0.890 |
| 5 | logistic | all | weather+place+history | {'class_weight': 'balanced'} | 0.052 | 10.4x | 10.1% | 0.061 | 7.0x | 0.775 |
| 6 | logistic | all | weather | {'class_weight': 'balanced'} | 0.042 | 8.3x | 8.8% | 0.047 | 5.3x | 0.725 |
| 7 | prior | all | - | {} | 0.005 | 1.0x | 0.5% | 0.008 | 1.0x | 0.488 |
| 8 | climatology | all | - | {} | 0.005 | 1.0x | 0.5% | 0.008 | 1.0x | 0.488 |

### >= 10% out · time(train_years=[2024],test_years=[2025]) · ranked by onset_pr_auc

Event rate: 0.51% of all blocks, 0.26% of onset blocks.

| rank | model | train on | features | params | onset PR-AUC | onset lift | onset prec@top1% | all PR-AUC | all lift | all ROC-AUC |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | lightgbm | all | weather+place+history+recent | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.053 | 19.9x | 7.3% | 0.307 | 60.6x | 0.917 |
| 2 | logistic | all | weather+place+history+recent | {'class_weight': 'balanced'} | 0.049 | 18.5x | 7.5% | 0.339 | 67.0x | 0.913 |
| 3 | logistic | all | weather+place+history | {'class_weight': 'balanced'} | 0.037 | 14.2x | 6.5% | 0.036 | 7.1x | 0.768 |
| 4 | lightgbm | all | weather+place+history | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.036 | 13.8x | 5.4% | 0.038 | 7.5x | 0.782 |
| 5 | logistic | all | weather | {'class_weight': 'balanced'} | 0.031 | 11.9x | 5.9% | 0.029 | 5.7x | 0.689 |
| 6 | lightgbm | all | weather | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.027 | 10.1x | 5.0% | 0.026 | 5.2x | 0.721 |
| 7 | climatology | all | - | {} | 0.004 | 1.5x | 0.9% | 0.007 | 1.4x | 0.567 |
| 8 | prior | all | - | {} | 0.003 | 1.0x | 0.3% | 0.005 | 1.0x | 0.500 |

### >= 10% out · county(folds=5) · ranked by onset_pr_auc

Event rate: 0.44% of all blocks, 0.25% of onset blocks.

| rank | model | train on | features | params | onset PR-AUC | onset lift | onset prec@top1% | all PR-AUC | all lift | all ROC-AUC |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | lightgbm | all | weather+place+history+recent | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.079 | 32.2x | 8.0% | 0.351 | 79.8x | 0.917 |
| 2 | lightgbm | all | weather+place+history | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.068 | 27.6x | 7.1% | 0.092 | 20.9x | 0.848 |
| 3 | lightgbm | all | weather | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.058 | 23.5x | 6.5% | 0.089 | 20.1x | 0.802 |
| 4 | logistic | all | weather+place+history+recent | {'class_weight': 'balanced'} | 0.046 | 18.6x | 6.7% | 0.307 | 69.8x | 0.912 |
| 5 | logistic | all | weather+place+history | {'class_weight': 'balanced'} | 0.040 | 16.2x | 6.1% | 0.042 | 9.6x | 0.794 |
| 6 | logistic | all | weather | {'class_weight': 'balanced'} | 0.031 | 12.5x | 5.5% | 0.031 | 7.1x | 0.737 |
| 7 | prior | all | - | {} | 0.002 | 1.0x | 0.2% | 0.004 | 1.0x | 0.482 |
| 8 | climatology | all | - | {} | 0.002 | 1.0x | 0.2% | 0.004 | 1.0x | 0.482 |
