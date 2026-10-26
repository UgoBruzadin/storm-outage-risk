# Leaderboard: onsets

LightGBM trained on all blocks vs. onset blocks only, at >= 1%, 5% and 10% of customers, on 2024 → 2025 and unseen counties. Ranked by onset PR-AUC.

### >= 1% out · time(train_years=[2024],test_years=[2025]) · ranked by onset_pr_auc

Event rate: 3.29% of all blocks, 1.97% of onset blocks.

| rank | model | train on | features | params | onset PR-AUC | onset lift | onset prec@top1% | all PR-AUC | all lift | all ROC-AUC |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | lightgbm | onsets | weather+place+history+recent | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.136 | 6.9x | 28.6% | 0.230 | 7.0x | 0.830 |
| 2 | lightgbm | all | weather+place+history+recent | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.136 | 6.9x | 28.2% | 0.383 | 11.6x | 0.863 |
| 3 | lightgbm | onsets | weather+place+history | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.127 | 6.4x | 28.1% | 0.146 | 4.4x | 0.743 |
| 4 | lightgbm | onsets | weather+place | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.124 | 6.3x | 27.2% | 0.142 | 4.3x | 0.739 |
| 5 | lightgbm | onsets | weather+place-canopy | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.123 | 6.2x | 26.7% | 0.140 | 4.2x | 0.736 |
| 6 | lightgbm | all | weather+place+history | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.116 | 5.9x | 25.5% | 0.148 | 4.5x | 0.749 |
| 7 | lightgbm | all | weather+place-canopy | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.112 | 5.7x | 25.1% | 0.143 | 4.4x | 0.745 |
| 8 | lightgbm | all | weather+place | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.110 | 5.6x | 24.3% | 0.141 | 4.3x | 0.745 |
| 9 | lightgbm | onsets | weather | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.102 | 5.2x | 24.0% | 0.113 | 3.4x | 0.691 |
| 10 | lightgbm | all | weather | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.092 | 4.6x | 22.1% | 0.114 | 3.4x | 0.701 |
| 11 | climatology | onsets | - | {} | 0.030 | 1.5x | 5.3% | 0.051 | 1.5x | 0.610 |
| 12 | climatology | all | - | {} | 0.029 | 1.4x | 4.5% | 0.048 | 1.5x | 0.606 |

### >= 1% out · county(folds=5) · ranked by onset_pr_auc

Event rate: 3.01% of all blocks, 1.86% of onset blocks.

| rank | model | train on | features | params | onset PR-AUC | onset lift | onset prec@top1% | all PR-AUC | all lift | all ROC-AUC |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | lightgbm | all | weather+place+history+recent | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.154 | 8.3x | 29.6% | 0.395 | 13.1x | 0.865 |
| 2 | lightgbm | onsets | weather+place+history+recent | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.152 | 8.2x | 29.6% | 0.249 | 8.3x | 0.846 |
| 3 | lightgbm | onsets | weather+place+history | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.151 | 8.1x | 29.1% | 0.168 | 5.6x | 0.764 |
| 4 | lightgbm | all | weather+place+history | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.146 | 7.8x | 28.3% | 0.200 | 6.7x | 0.788 |
| 5 | lightgbm | onsets | weather+place | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.137 | 7.3x | 28.1% | 0.152 | 5.0x | 0.741 |
| 6 | lightgbm | onsets | weather+place-canopy | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.132 | 7.1x | 27.3% | 0.147 | 4.9x | 0.736 |
| 7 | lightgbm | onsets | weather | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.131 | 7.0x | 27.4% | 0.141 | 4.7x | 0.722 |
| 8 | lightgbm | all | weather+place | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.130 | 7.0x | 26.9% | 0.183 | 6.1x | 0.766 |
| 9 | lightgbm | all | weather+place-canopy | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.128 | 6.9x | 26.5% | 0.174 | 5.8x | 0.763 |
| 10 | lightgbm | all | weather | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.124 | 6.6x | 26.3% | 0.175 | 5.8x | 0.755 |
| 11 | climatology | all | - | {} | 0.018 | 1.0x | 1.8% | 0.029 | 1.0x | 0.490 |
| 12 | climatology | onsets | - | {} | 0.018 | 1.0x | 1.8% | 0.030 | 1.0x | 0.491 |

### >= 5% out · time(train_years=[2024],test_years=[2025]) · ranked by onset_pr_auc

Event rate: 0.99% of all blocks, 0.53% of onset blocks.

| rank | model | train on | features | params | onset PR-AUC | onset lift | onset prec@top1% | all PR-AUC | all lift | all ROC-AUC |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | lightgbm | all | weather+place+history+recent | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.084 | 15.8x | 12.3% | 0.370 | 37.3x | 0.903 |
| 2 | lightgbm | onsets | weather+place+history+recent | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.078 | 14.7x | 11.7% | 0.158 | 15.9x | 0.881 |
| 3 | lightgbm | onsets | weather+place+history | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.074 | 13.9x | 11.5% | 0.070 | 7.0x | 0.759 |
| 4 | lightgbm | onsets | weather+place-canopy | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.069 | 13.0x | 11.1% | 0.066 | 6.6x | 0.745 |
| 5 | lightgbm | onsets | weather+place | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.068 | 12.8x | 10.9% | 0.068 | 6.9x | 0.751 |
| 6 | lightgbm | all | weather+place+history | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.061 | 11.4x | 9.9% | 0.070 | 7.1x | 0.770 |
| 7 | lightgbm | all | weather+place | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.057 | 10.8x | 10.0% | 0.064 | 6.5x | 0.756 |
| 8 | lightgbm | all | weather+place-canopy | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.056 | 10.6x | 10.1% | 0.065 | 6.5x | 0.759 |
| 9 | lightgbm | onsets | weather | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.052 | 9.8x | 10.0% | 0.050 | 5.1x | 0.684 |
| 10 | lightgbm | all | weather | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.043 | 8.1x | 8.9% | 0.049 | 4.9x | 0.713 |
| 11 | climatology | onsets | - | {} | 0.008 | 1.6x | 1.5% | 0.015 | 1.5x | 0.593 |
| 12 | climatology | all | - | {} | 0.008 | 1.5x | 1.8% | 0.014 | 1.5x | 0.594 |

### >= 5% out · county(folds=5) · ranked by onset_pr_auc

Event rate: 0.87% of all blocks, 0.50% of onset blocks.

| rank | model | train on | features | params | onset PR-AUC | onset lift | onset prec@top1% | all PR-AUC | all lift | all ROC-AUC |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | lightgbm | all | weather+place+history+recent | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.106 | 21.2x | 12.7% | 0.391 | 44.8x | 0.897 |
| 2 | lightgbm | onsets | weather+place+history+recent | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.101 | 20.2x | 12.6% | 0.186 | 21.3x | 0.888 |
| 3 | lightgbm | onsets | weather+place+history | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.094 | 18.6x | 12.2% | 0.091 | 10.5x | 0.786 |
| 4 | lightgbm | all | weather+place+history | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.093 | 18.4x | 11.9% | 0.136 | 15.6x | 0.825 |
| 5 | lightgbm | onsets | weather+place | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.091 | 18.2x | 12.0% | 0.088 | 10.0x | 0.770 |
| 6 | lightgbm | onsets | weather+place-canopy | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.091 | 18.2x | 11.6% | 0.085 | 9.7x | 0.765 |
| 7 | lightgbm | onsets | weather | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.086 | 17.1x | 11.2% | 0.080 | 9.1x | 0.737 |
| 8 | lightgbm | all | weather+place | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.086 | 17.1x | 11.4% | 0.131 | 15.0x | 0.810 |
| 9 | lightgbm | all | weather+place-canopy | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.082 | 16.4x | 11.4% | 0.118 | 13.4x | 0.807 |
| 10 | lightgbm | all | weather | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.079 | 15.8x | 10.9% | 0.124 | 14.2x | 0.790 |
| 11 | climatology | all | - | {} | 0.005 | 1.0x | 0.5% | 0.008 | 1.0x | 0.488 |
| 12 | climatology | onsets | - | {} | 0.005 | 1.0x | 0.5% | 0.009 | 1.0x | 0.492 |

### >= 10% out · time(train_years=[2024],test_years=[2025]) · ranked by onset_pr_auc

Event rate: 0.51% of all blocks, 0.26% of onset blocks.

| rank | model | train on | features | params | onset PR-AUC | onset lift | onset prec@top1% | all PR-AUC | all lift | all ROC-AUC |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | lightgbm | all | weather+place+history+recent | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.055 | 21.0x | 7.3% | 0.312 | 61.6x | 0.919 |
| 2 | lightgbm | onsets | weather+place+history+recent | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.048 | 18.2x | 6.4% | 0.097 | 19.1x | 0.877 |
| 3 | lightgbm | onsets | weather+place | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.041 | 15.4x | 6.0% | 0.036 | 7.2x | 0.754 |
| 4 | lightgbm | onsets | weather+place+history | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.039 | 14.9x | 6.0% | 0.039 | 7.8x | 0.772 |
| 5 | lightgbm | onsets | weather+place-canopy | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.038 | 14.5x | 5.9% | 0.036 | 7.1x | 0.754 |
| 6 | lightgbm | all | weather+place-canopy | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.035 | 13.3x | 5.4% | 0.035 | 7.0x | 0.768 |
| 7 | lightgbm | all | weather+place+history | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.033 | 12.5x | 5.0% | 0.036 | 7.1x | 0.785 |
| 8 | lightgbm | all | weather+place | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.030 | 11.3x | 5.0% | 0.033 | 6.5x | 0.765 |
| 9 | lightgbm | onsets | weather | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.028 | 10.5x | 5.0% | 0.026 | 5.2x | 0.699 |
| 10 | lightgbm | all | weather | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.025 | 9.5x | 4.6% | 0.026 | 5.0x | 0.721 |
| 11 | climatology | all | - | {} | 0.004 | 1.5x | 0.9% | 0.007 | 1.4x | 0.567 |
| 12 | climatology | onsets | - | {} | 0.004 | 1.5x | 0.8% | 0.007 | 1.4x | 0.567 |

### >= 10% out · county(folds=5) · ranked by onset_pr_auc

Event rate: 0.44% of all blocks, 0.25% of onset blocks.

| rank | model | train on | features | params | onset PR-AUC | onset lift | onset prec@top1% | all PR-AUC | all lift | all ROC-AUC |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | lightgbm | all | weather+place+history+recent | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.075 | 30.3x | 7.9% | 0.346 | 78.6x | 0.918 |
| 2 | lightgbm | onsets | weather+place+history+recent | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.071 | 28.7x | 7.8% | 0.139 | 31.7x | 0.905 |
| 3 | lightgbm | all | weather+place+history | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.067 | 27.3x | 7.2% | 0.092 | 20.9x | 0.847 |
| 4 | lightgbm | onsets | weather+place | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.067 | 27.3x | 6.9% | 0.059 | 13.4x | 0.787 |
| 5 | lightgbm | onsets | weather+place+history | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.067 | 27.1x | 7.4% | 0.063 | 14.2x | 0.813 |
| 6 | lightgbm | onsets | weather+place-canopy | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.060 | 24.2x | 6.9% | 0.054 | 12.2x | 0.783 |
| 7 | lightgbm | onsets | weather | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.060 | 24.2x | 7.0% | 0.052 | 11.9x | 0.754 |
| 8 | lightgbm | all | weather+place | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.059 | 24.0x | 6.7% | 0.086 | 19.4x | 0.827 |
| 9 | lightgbm | all | weather | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.058 | 23.7x | 6.7% | 0.092 | 20.8x | 0.803 |
| 10 | lightgbm | all | weather+place-canopy | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.054 | 21.8x | 6.7% | 0.080 | 18.2x | 0.822 |
| 11 | climatology | all | - | {} | 0.002 | 1.0x | 0.2% | 0.004 | 1.0x | 0.482 |
| 12 | climatology | onsets | - | {} | 0.002 | 1.0x | 0.2% | 0.004 | 1.0x | 0.506 |
