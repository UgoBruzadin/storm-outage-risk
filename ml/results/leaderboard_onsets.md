# Leaderboard: onsets

LightGBM and XGBoost trained on all blocks vs. onset blocks only, at >= 1%, 5% and 10% of customers, on 2024 → 2025 and unseen counties. Ranked by onset PR-AUC.

### >= 1% out · time(train_years=[2024],test_years=[2025]) · ranked by onset_pr_auc

Event rate: 3.29% of all blocks, 1.97% of onset blocks.

| rank | model | train on | features | params | onset PR-AUC | onset lift | onset prec@top1% | all PR-AUC | all lift | all ROC-AUC |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | xgboost | all | weather+place+history+recent | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.141 | 7.2x | 28.6% | 0.385 | 11.7x | 0.864 |
| 2 | xgboost | onsets | weather+place+history+recent | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.137 | 7.0x | 28.6% | 0.216 | 6.6x | 0.828 |
| 3 | lightgbm | onsets | weather+place+history+recent | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.136 | 6.9x | 28.6% | 0.230 | 7.0x | 0.830 |
| 4 | lightgbm | all | weather+place+history+recent | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.136 | 6.9x | 28.2% | 0.383 | 11.6x | 0.863 |
| 5 | xgboost | onsets | weather+place+history | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.132 | 6.7x | 27.9% | 0.150 | 4.6x | 0.746 |
| 6 | xgboost | onsets | weather+place-canopy | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.130 | 6.6x | 28.6% | 0.145 | 4.4x | 0.738 |
| 7 | xgboost | onsets | weather+place | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.129 | 6.5x | 28.2% | 0.146 | 4.4x | 0.740 |
| 8 | lightgbm | onsets | weather+place+history | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.127 | 6.4x | 28.1% | 0.146 | 4.4x | 0.743 |
| 9 | lightgbm | onsets | weather+place | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.124 | 6.3x | 27.2% | 0.142 | 4.3x | 0.739 |
| 10 | xgboost | all | weather+place+history | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.124 | 6.3x | 26.5% | 0.154 | 4.7x | 0.754 |
| 11 | lightgbm | onsets | weather+place-canopy | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.123 | 6.2x | 26.7% | 0.140 | 4.2x | 0.736 |
| 12 | xgboost | all | weather+place-canopy | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.119 | 6.0x | 25.7% | 0.146 | 4.4x | 0.745 |
| 13 | xgboost | all | weather+place | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.118 | 6.0x | 26.1% | 0.147 | 4.5x | 0.747 |
| 14 | lightgbm | all | weather+place+history | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.116 | 5.9x | 25.5% | 0.148 | 4.5x | 0.749 |
| 15 | lightgbm | all | weather+place-canopy | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.112 | 5.7x | 25.1% | 0.143 | 4.4x | 0.745 |
| 16 | lightgbm | all | weather+place | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.110 | 5.6x | 24.3% | 0.141 | 4.3x | 0.745 |
| 17 | xgboost | onsets | weather | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.106 | 5.4x | 25.6% | 0.117 | 3.5x | 0.693 |
| 18 | lightgbm | onsets | weather | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.102 | 5.2x | 24.0% | 0.113 | 3.4x | 0.691 |
| 19 | xgboost | all | weather | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.098 | 5.0x | 23.9% | 0.119 | 3.6x | 0.704 |
| 20 | lightgbm | all | weather | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.092 | 4.6x | 22.1% | 0.114 | 3.4x | 0.701 |
| 21 | climatology | onsets | - | {} | 0.030 | 1.5x | 5.3% | 0.051 | 1.5x | 0.610 |
| 22 | climatology | all | - | {} | 0.029 | 1.4x | 4.5% | 0.048 | 1.5x | 0.606 |

### >= 1% out · county(folds=5) · ranked by onset_pr_auc

Event rate: 3.01% of all blocks, 1.86% of onset blocks.

| rank | model | train on | features | params | onset PR-AUC | onset lift | onset prec@top1% | all PR-AUC | all lift | all ROC-AUC |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | lightgbm | all | weather+place+history+recent | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.154 | 8.3x | 29.6% | 0.395 | 13.1x | 0.865 |
| 2 | lightgbm | onsets | weather+place+history+recent | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.152 | 8.2x | 29.6% | 0.249 | 8.3x | 0.846 |
| 3 | lightgbm | onsets | weather+place+history | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.151 | 8.1x | 29.1% | 0.168 | 5.6x | 0.764 |
| 4 | xgboost | onsets | weather+place+history+recent | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.150 | 8.0x | 28.9% | 0.237 | 7.9x | 0.845 |
| 5 | xgboost | all | weather+place+history+recent | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.147 | 7.9x | 28.4% | 0.387 | 12.8x | 0.863 |
| 6 | xgboost | onsets | weather+place+history | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.147 | 7.9x | 28.3% | 0.163 | 5.4x | 0.763 |
| 7 | lightgbm | all | weather+place+history | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.146 | 7.8x | 28.3% | 0.200 | 6.7x | 0.788 |
| 8 | xgboost | all | weather+place+history | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.142 | 7.6x | 27.6% | 0.183 | 6.1x | 0.781 |
| 9 | lightgbm | onsets | weather+place | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.137 | 7.3x | 28.1% | 0.152 | 5.0x | 0.741 |
| 10 | lightgbm | onsets | weather+place-canopy | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.132 | 7.1x | 27.3% | 0.147 | 4.9x | 0.736 |
| 11 | xgboost | onsets | weather+place | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.132 | 7.1x | 26.9% | 0.146 | 4.9x | 0.739 |
| 12 | lightgbm | onsets | weather | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.131 | 7.0x | 27.4% | 0.141 | 4.7x | 0.722 |
| 13 | lightgbm | all | weather+place | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.130 | 7.0x | 26.9% | 0.183 | 6.1x | 0.766 |
| 14 | lightgbm | all | weather+place-canopy | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.128 | 6.9x | 26.5% | 0.174 | 5.8x | 0.763 |
| 15 | xgboost | all | weather+place | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.127 | 6.8x | 26.7% | 0.166 | 5.5x | 0.760 |
| 16 | xgboost | onsets | weather+place-canopy | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.127 | 6.8x | 26.3% | 0.141 | 4.7x | 0.736 |
| 17 | xgboost | onsets | weather | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.126 | 6.8x | 26.6% | 0.137 | 4.5x | 0.720 |
| 18 | xgboost | all | weather+place-canopy | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.125 | 6.7x | 26.2% | 0.160 | 5.3x | 0.758 |
| 19 | lightgbm | all | weather | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.124 | 6.6x | 26.3% | 0.175 | 5.8x | 0.755 |
| 20 | xgboost | all | weather | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.120 | 6.5x | 26.0% | 0.155 | 5.2x | 0.745 |
| 21 | climatology | all | - | {} | 0.018 | 1.0x | 1.8% | 0.029 | 1.0x | 0.490 |
| 22 | climatology | onsets | - | {} | 0.018 | 1.0x | 1.8% | 0.030 | 1.0x | 0.491 |

### >= 5% out · time(train_years=[2024],test_years=[2025]) · ranked by onset_pr_auc

Event rate: 0.99% of all blocks, 0.53% of onset blocks.

| rank | model | train on | features | params | onset PR-AUC | onset lift | onset prec@top1% | all PR-AUC | all lift | all ROC-AUC |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | xgboost | all | weather+place+history+recent | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.095 | 17.9x | 13.0% | 0.393 | 39.6x | 0.906 |
| 2 | xgboost | onsets | weather+place+history+recent | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.093 | 17.6x | 12.8% | 0.148 | 14.9x | 0.881 |
| 3 | xgboost | onsets | weather+place+history | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.087 | 16.4x | 12.6% | 0.082 | 8.2x | 0.763 |
| 4 | lightgbm | all | weather+place+history+recent | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.084 | 15.8x | 12.3% | 0.370 | 37.3x | 0.903 |
| 5 | xgboost | onsets | weather+place | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.079 | 14.9x | 12.5% | 0.074 | 7.5x | 0.752 |
| 6 | xgboost | onsets | weather+place-canopy | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.078 | 14.8x | 12.1% | 0.072 | 7.3x | 0.745 |
| 7 | lightgbm | onsets | weather+place+history+recent | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.078 | 14.7x | 11.7% | 0.158 | 15.9x | 0.881 |
| 8 | lightgbm | onsets | weather+place+history | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.074 | 13.9x | 11.5% | 0.070 | 7.0x | 0.759 |
| 9 | xgboost | all | weather+place-canopy | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.071 | 13.4x | 11.3% | 0.076 | 7.7x | 0.769 |
| 10 | xgboost | all | weather+place+history | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.071 | 13.3x | 11.1% | 0.076 | 7.7x | 0.780 |
| 11 | lightgbm | onsets | weather+place-canopy | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.069 | 13.0x | 11.1% | 0.066 | 6.6x | 0.745 |
| 12 | lightgbm | onsets | weather+place | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.068 | 12.8x | 10.9% | 0.068 | 6.9x | 0.751 |
| 13 | xgboost | all | weather+place | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.066 | 12.5x | 11.0% | 0.072 | 7.3x | 0.767 |
| 14 | lightgbm | all | weather+place+history | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.061 | 11.4x | 9.9% | 0.070 | 7.1x | 0.770 |
| 15 | xgboost | onsets | weather | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.061 | 11.4x | 11.0% | 0.055 | 5.5x | 0.688 |
| 16 | lightgbm | all | weather+place | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.057 | 10.8x | 10.0% | 0.064 | 6.5x | 0.756 |
| 17 | lightgbm | all | weather+place-canopy | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.056 | 10.6x | 10.1% | 0.065 | 6.5x | 0.759 |
| 18 | xgboost | all | weather | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.056 | 10.5x | 10.4% | 0.056 | 5.7x | 0.720 |
| 19 | lightgbm | onsets | weather | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.052 | 9.8x | 10.0% | 0.050 | 5.1x | 0.684 |
| 20 | lightgbm | all | weather | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.043 | 8.1x | 8.9% | 0.049 | 4.9x | 0.713 |
| 21 | climatology | onsets | - | {} | 0.008 | 1.6x | 1.5% | 0.015 | 1.5x | 0.593 |
| 22 | climatology | all | - | {} | 0.008 | 1.5x | 1.8% | 0.014 | 1.5x | 0.594 |

### >= 5% out · county(folds=5) · ranked by onset_pr_auc

Event rate: 0.87% of all blocks, 0.50% of onset blocks.

| rank | model | train on | features | params | onset PR-AUC | onset lift | onset prec@top1% | all PR-AUC | all lift | all ROC-AUC |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | xgboost | onsets | weather+place+history+recent | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.108 | 21.4x | 12.7% | 0.174 | 19.9x | 0.887 |
| 2 | lightgbm | all | weather+place+history+recent | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.106 | 21.2x | 12.7% | 0.391 | 44.8x | 0.897 |
| 3 | xgboost | all | weather+place+history+recent | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.103 | 20.6x | 12.6% | 0.390 | 44.6x | 0.898 |
| 4 | xgboost | onsets | weather+place+history | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.102 | 20.3x | 12.3% | 0.096 | 11.0x | 0.790 |
| 5 | lightgbm | onsets | weather+place+history+recent | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.101 | 20.2x | 12.6% | 0.186 | 21.3x | 0.888 |
| 6 | xgboost | all | weather+place+history | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.096 | 19.1x | 11.9% | 0.123 | 14.0x | 0.819 |
| 7 | xgboost | onsets | weather+place | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.094 | 18.7x | 12.2% | 0.089 | 10.1x | 0.773 |
| 8 | lightgbm | onsets | weather+place+history | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.094 | 18.6x | 12.2% | 0.091 | 10.5x | 0.786 |
| 9 | lightgbm | all | weather+place+history | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.093 | 18.4x | 11.9% | 0.136 | 15.6x | 0.825 |
| 10 | lightgbm | onsets | weather+place | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.091 | 18.2x | 12.0% | 0.088 | 10.0x | 0.770 |
| 11 | lightgbm | onsets | weather+place-canopy | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.091 | 18.2x | 11.6% | 0.085 | 9.7x | 0.765 |
| 12 | xgboost | onsets | weather+place-canopy | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.091 | 18.2x | 12.3% | 0.086 | 9.8x | 0.768 |
| 13 | xgboost | onsets | weather | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.089 | 17.7x | 11.7% | 0.081 | 9.3x | 0.737 |
| 14 | xgboost | all | weather+place | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.088 | 17.6x | 11.6% | 0.115 | 13.2x | 0.805 |
| 15 | lightgbm | onsets | weather | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.086 | 17.1x | 11.2% | 0.080 | 9.1x | 0.737 |
| 16 | lightgbm | all | weather+place | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.086 | 17.1x | 11.4% | 0.131 | 15.0x | 0.810 |
| 17 | xgboost | all | weather+place-canopy | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.084 | 16.8x | 11.6% | 0.105 | 12.0x | 0.800 |
| 18 | xgboost | all | weather | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.084 | 16.8x | 11.3% | 0.105 | 12.1x | 0.782 |
| 19 | lightgbm | all | weather+place-canopy | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.082 | 16.4x | 11.4% | 0.118 | 13.4x | 0.807 |
| 20 | lightgbm | all | weather | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.079 | 15.8x | 10.9% | 0.124 | 14.2x | 0.790 |
| 21 | climatology | all | - | {} | 0.005 | 1.0x | 0.5% | 0.008 | 1.0x | 0.488 |
| 22 | climatology | onsets | - | {} | 0.005 | 1.0x | 0.5% | 0.009 | 1.0x | 0.492 |

### >= 10% out · time(train_years=[2024],test_years=[2025]) · ranked by onset_pr_auc

Event rate: 0.51% of all blocks, 0.26% of onset blocks.

| rank | model | train on | features | params | onset PR-AUC | onset lift | onset prec@top1% | all PR-AUC | all lift | all ROC-AUC |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | xgboost | onsets | weather+place+history+recent | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.069 | 26.1x | 8.1% | 0.118 | 23.4x | 0.902 |
| 2 | xgboost | all | weather+place+history+recent | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.065 | 24.6x | 7.7% | 0.348 | 68.8x | 0.922 |
| 3 | xgboost | onsets | weather+place+history | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.059 | 22.4x | 7.6% | 0.055 | 10.8x | 0.782 |
| 4 | xgboost | onsets | weather+place | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.058 | 21.8x | 7.5% | 0.051 | 10.1x | 0.768 |
| 5 | xgboost | onsets | weather+place-canopy | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.057 | 21.6x | 7.5% | 0.049 | 9.6x | 0.760 |
| 6 | lightgbm | all | weather+place+history+recent | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.055 | 21.0x | 7.3% | 0.312 | 61.6x | 0.919 |
| 7 | lightgbm | onsets | weather+place+history+recent | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.048 | 18.2x | 6.4% | 0.097 | 19.1x | 0.877 |
| 8 | xgboost | all | weather+place+history | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.046 | 17.4x | 6.3% | 0.048 | 9.4x | 0.798 |
| 9 | xgboost | all | weather+place-canopy | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.045 | 17.2x | 6.4% | 0.046 | 9.2x | 0.784 |
| 10 | xgboost | all | weather+place | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.041 | 15.7x | 6.2% | 0.042 | 8.3x | 0.786 |
| 11 | xgboost | onsets | weather | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.041 | 15.6x | 6.5% | 0.036 | 7.1x | 0.702 |
| 12 | lightgbm | onsets | weather+place | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.041 | 15.4x | 6.0% | 0.036 | 7.2x | 0.754 |
| 13 | lightgbm | onsets | weather+place+history | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.039 | 14.9x | 6.0% | 0.039 | 7.8x | 0.772 |
| 14 | lightgbm | onsets | weather+place-canopy | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.038 | 14.5x | 5.9% | 0.036 | 7.1x | 0.754 |
| 15 | lightgbm | all | weather+place-canopy | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.035 | 13.3x | 5.4% | 0.035 | 7.0x | 0.768 |
| 16 | xgboost | all | weather | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.034 | 12.9x | 5.7% | 0.033 | 6.4x | 0.736 |
| 17 | lightgbm | all | weather+place+history | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.033 | 12.5x | 5.0% | 0.036 | 7.1x | 0.785 |
| 18 | lightgbm | all | weather+place | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.030 | 11.3x | 5.0% | 0.033 | 6.5x | 0.765 |
| 19 | lightgbm | onsets | weather | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.028 | 10.5x | 5.0% | 0.026 | 5.2x | 0.699 |
| 20 | lightgbm | all | weather | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.025 | 9.5x | 4.6% | 0.026 | 5.0x | 0.721 |
| 21 | climatology | all | - | {} | 0.004 | 1.5x | 0.9% | 0.007 | 1.4x | 0.567 |
| 22 | climatology | onsets | - | {} | 0.004 | 1.5x | 0.8% | 0.007 | 1.4x | 0.567 |

### >= 10% out · county(folds=5) · ranked by onset_pr_auc

Event rate: 0.44% of all blocks, 0.25% of onset blocks.

| rank | model | train on | features | params | onset PR-AUC | onset lift | onset prec@top1% | all PR-AUC | all lift | all ROC-AUC |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | xgboost | onsets | weather+place+history+recent | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.086 | 34.8x | 8.2% | 0.140 | 31.9x | 0.911 |
| 2 | xgboost | all | weather+place+history+recent | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.084 | 34.0x | 8.0% | 0.373 | 84.7x | 0.918 |
| 3 | xgboost | onsets | weather+place+history | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.077 | 31.5x | 7.6% | 0.069 | 15.7x | 0.818 |
| 4 | xgboost | all | weather+place+history | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.075 | 30.6x | 7.3% | 0.090 | 20.4x | 0.846 |
| 5 | xgboost | onsets | weather+place | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.075 | 30.4x | 7.5% | 0.065 | 14.7x | 0.793 |
| 6 | lightgbm | all | weather+place+history+recent | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.075 | 30.3x | 7.9% | 0.346 | 78.6x | 0.918 |
| 7 | xgboost | onsets | weather+place-canopy | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.071 | 28.8x | 7.4% | 0.062 | 14.0x | 0.788 |
| 8 | lightgbm | onsets | weather+place+history+recent | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.071 | 28.7x | 7.8% | 0.139 | 31.7x | 0.905 |
| 9 | xgboost | onsets | weather | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.069 | 28.1x | 7.4% | 0.058 | 13.2x | 0.758 |
| 10 | lightgbm | all | weather+place+history | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.067 | 27.3x | 7.2% | 0.092 | 20.9x | 0.847 |
| 11 | lightgbm | onsets | weather+place | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.067 | 27.3x | 6.9% | 0.059 | 13.4x | 0.787 |
| 12 | lightgbm | onsets | weather+place+history | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.067 | 27.1x | 7.4% | 0.063 | 14.2x | 0.813 |
| 13 | xgboost | all | weather | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.063 | 25.8x | 6.7% | 0.076 | 17.2x | 0.796 |
| 14 | xgboost | all | weather+place | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.063 | 25.8x | 6.9% | 0.080 | 18.2x | 0.824 |
| 15 | xgboost | all | weather+place-canopy | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.063 | 25.5x | 6.9% | 0.075 | 17.0x | 0.818 |
| 16 | lightgbm | onsets | weather+place-canopy | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.060 | 24.2x | 6.9% | 0.054 | 12.2x | 0.783 |
| 17 | lightgbm | onsets | weather | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.060 | 24.2x | 7.0% | 0.052 | 11.9x | 0.754 |
| 18 | lightgbm | all | weather+place | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.059 | 24.0x | 6.7% | 0.086 | 19.4x | 0.827 |
| 19 | lightgbm | all | weather | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.058 | 23.7x | 6.7% | 0.092 | 20.8x | 0.803 |
| 20 | lightgbm | all | weather+place-canopy | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.054 | 21.8x | 6.7% | 0.080 | 18.2x | 0.822 |
| 21 | climatology | all | - | {} | 0.002 | 1.0x | 0.2% | 0.004 | 1.0x | 0.482 |
| 22 | climatology | onsets | - | {} | 0.002 | 1.0x | 0.2% | 0.004 | 1.0x | 0.506 |
