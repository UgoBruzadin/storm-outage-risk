# Leaderboard: wet_soil

Antecedent rain (72 h and 7 days before the block, and gust x 72 h rain) on and off, LightGBM and XGBoost, at >= 5% and 10% of customers, on 2024 → 2025 and unseen counties. Ranked by onset PR-AUC.

### >= 5% out · time(train_years=[2024],test_years=[2025]) · ranked by onset_pr_auc

Event rate: 0.99% of all blocks, 0.53% of onset blocks.

| rank | model | train on | features | params | onset PR-AUC | onset lift | onset prec@top1% | all PR-AUC | all lift | all ROC-AUC |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | xgboost | all | weather+place+history+recent+wet_soil | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.095 | 17.9x | 13.1% | 0.391 | 39.4x | 0.906 |
| 2 | xgboost | onsets | weather+place+history+recent+wet_soil | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.094 | 17.8x | 13.0% | 0.154 | 15.5x | 0.883 |
| 3 | xgboost | all | weather+place+history+recent | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.092 | 17.4x | 13.3% | 0.387 | 39.0x | 0.906 |
| 4 | xgboost | onsets | weather+place+history+recent | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.092 | 17.3x | 13.0% | 0.150 | 15.1x | 0.883 |
| 5 | lightgbm | all | weather+place+history+recent+wet_soil | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.085 | 15.9x | 12.2% | 0.378 | 38.1x | 0.902 |
| 6 | lightgbm | all | weather+place+history+recent | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.083 | 15.6x | 12.7% | 0.370 | 37.3x | 0.902 |
| 7 | lightgbm | onsets | weather+place+history+recent | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.079 | 14.9x | 11.5% | 0.162 | 16.3x | 0.884 |
| 8 | xgboost | onsets | weather+place+wet_soil | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.079 | 14.8x | 12.3% | 0.077 | 7.7x | 0.757 |
| 9 | lightgbm | onsets | weather+place+history+recent+wet_soil | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.077 | 14.6x | 11.9% | 0.158 | 15.9x | 0.885 |
| 10 | xgboost | onsets | weather+place | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.076 | 14.4x | 12.1% | 0.073 | 7.3x | 0.750 |
| 11 | lightgbm | onsets | weather+place+wet_soil | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.074 | 14.0x | 11.4% | 0.073 | 7.4x | 0.753 |
| 12 | xgboost | all | weather+place | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.068 | 12.9x | 11.1% | 0.074 | 7.5x | 0.766 |
| 13 | xgboost | all | weather+place+wet_soil | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.068 | 12.8x | 11.1% | 0.082 | 8.2x | 0.783 |
| 14 | lightgbm | onsets | weather+place | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.067 | 12.7x | 11.1% | 0.066 | 6.6x | 0.751 |
| 15 | lightgbm | all | weather+place+wet_soil | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.057 | 10.7x | 9.9% | 0.074 | 7.5x | 0.779 |
| 16 | lightgbm | all | weather+place | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.052 | 9.8x | 9.9% | 0.059 | 6.0x | 0.760 |

### >= 5% out · county(folds=5) · ranked by onset_pr_auc

Event rate: 0.87% of all blocks, 0.50% of onset blocks.

| rank | model | train on | features | params | onset PR-AUC | onset lift | onset prec@top1% | all PR-AUC | all lift | all ROC-AUC |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | lightgbm | all | weather+place+history+recent | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.109 | 21.8x | 12.7% | 0.392 | 44.8x | 0.899 |
| 2 | lightgbm | all | weather+place+history+recent+wet_soil | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.108 | 21.6x | 12.6% | 0.389 | 44.5x | 0.898 |
| 3 | xgboost | onsets | weather+place+history+recent | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.108 | 21.5x | 12.6% | 0.174 | 20.0x | 0.887 |
| 4 | xgboost | onsets | weather+place+history+recent+wet_soil | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.108 | 21.4x | 12.6% | 0.174 | 19.9x | 0.886 |
| 5 | xgboost | all | weather+place+history+recent | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.104 | 20.7x | 12.7% | 0.390 | 44.6x | 0.898 |
| 6 | xgboost | all | weather+place+history+recent+wet_soil | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.103 | 20.5x | 12.7% | 0.389 | 44.5x | 0.898 |
| 7 | lightgbm | onsets | weather+place+history+recent | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.103 | 20.4x | 12.4% | 0.188 | 21.5x | 0.887 |
| 8 | lightgbm | onsets | weather+place+history+recent+wet_soil | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.099 | 19.7x | 12.5% | 0.179 | 20.5x | 0.886 |
| 9 | xgboost | onsets | weather+place+wet_soil | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.095 | 18.8x | 12.3% | 0.091 | 10.4x | 0.777 |
| 10 | xgboost | onsets | weather+place | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.093 | 18.6x | 12.3% | 0.089 | 10.2x | 0.772 |
| 11 | xgboost | all | weather+place | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.087 | 17.4x | 11.4% | 0.114 | 13.0x | 0.805 |
| 12 | lightgbm | onsets | weather+place+wet_soil | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.087 | 17.3x | 11.9% | 0.087 | 9.9x | 0.773 |
| 13 | lightgbm | onsets | weather+place | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.087 | 17.3x | 12.0% | 0.085 | 9.7x | 0.769 |
| 14 | lightgbm | all | weather+place | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.085 | 16.9x | 11.1% | 0.127 | 14.5x | 0.809 |
| 15 | xgboost | all | weather+place+wet_soil | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.085 | 16.9x | 11.2% | 0.123 | 14.0x | 0.809 |
| 16 | lightgbm | all | weather+place+wet_soil | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.079 | 15.8x | 11.2% | 0.131 | 15.0x | 0.812 |

### >= 10% out · time(train_years=[2024],test_years=[2025]) · ranked by onset_pr_auc

Event rate: 0.51% of all blocks, 0.26% of onset blocks.

| rank | model | train on | features | params | onset PR-AUC | onset lift | onset prec@top1% | all PR-AUC | all lift | all ROC-AUC |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | xgboost | onsets | weather+place+history+recent+wet_soil | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.071 | 26.8x | 7.9% | 0.120 | 23.7x | 0.899 |
| 2 | xgboost | onsets | weather+place+history+recent | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.069 | 26.3x | 8.2% | 0.120 | 23.7x | 0.901 |
| 3 | xgboost | all | weather+place+history+recent | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.067 | 25.5x | 7.8% | 0.353 | 69.7x | 0.923 |
| 4 | xgboost | all | weather+place+history+recent+wet_soil | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.066 | 25.0x | 7.7% | 0.350 | 69.1x | 0.923 |
| 5 | xgboost | onsets | weather+place | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.057 | 21.6x | 7.4% | 0.050 | 9.8x | 0.760 |
| 6 | xgboost | onsets | weather+place+wet_soil | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.056 | 21.2x | 7.5% | 0.051 | 10.0x | 0.765 |
| 7 | lightgbm | all | weather+place+history+recent | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.053 | 20.3x | 7.2% | 0.333 | 65.8x | 0.918 |
| 8 | lightgbm | onsets | weather+place+history+recent | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.052 | 19.8x | 6.6% | 0.103 | 20.3x | 0.884 |
| 9 | lightgbm | onsets | weather+place+history+recent+wet_soil | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.052 | 19.8x | 6.6% | 0.093 | 18.4x | 0.869 |
| 10 | lightgbm | all | weather+place+history+recent+wet_soil | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.052 | 19.7x | 7.4% | 0.322 | 63.6x | 0.916 |
| 11 | xgboost | all | weather+place+wet_soil | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.046 | 17.4x | 6.2% | 0.053 | 10.5x | 0.799 |
| 12 | xgboost | all | weather+place | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.043 | 16.5x | 6.2% | 0.044 | 8.7x | 0.781 |
| 13 | lightgbm | onsets | weather+place+wet_soil | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.037 | 14.0x | 5.8% | 0.036 | 7.1x | 0.755 |
| 14 | lightgbm | onsets | weather+place | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.037 | 14.0x | 5.5% | 0.036 | 7.1x | 0.754 |
| 15 | lightgbm | all | weather+place+wet_soil | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.036 | 13.6x | 5.3% | 0.046 | 9.1x | 0.791 |
| 16 | lightgbm | all | weather+place | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.029 | 11.1x | 4.8% | 0.033 | 6.5x | 0.770 |

### >= 10% out · county(folds=5) · ranked by onset_pr_auc

Event rate: 0.44% of all blocks, 0.25% of onset blocks.

| rank | model | train on | features | params | onset PR-AUC | onset lift | onset prec@top1% | all PR-AUC | all lift | all ROC-AUC |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | xgboost | onsets | weather+place+history+recent | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.086 | 34.9x | 8.2% | 0.141 | 31.9x | 0.910 |
| 2 | xgboost | onsets | weather+place+history+recent+wet_soil | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.085 | 34.4x | 8.2% | 0.141 | 32.0x | 0.909 |
| 3 | xgboost | all | weather+place+history+recent | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.083 | 33.8x | 8.0% | 0.372 | 84.6x | 0.918 |
| 4 | xgboost | all | weather+place+history+recent+wet_soil | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.083 | 33.7x | 8.0% | 0.373 | 84.8x | 0.918 |
| 5 | lightgbm | all | weather+place+history+recent+wet_soil | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.081 | 33.1x | 8.2% | 0.363 | 82.6x | 0.915 |
| 6 | lightgbm | all | weather+place+history+recent | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.078 | 31.7x | 8.0% | 0.346 | 78.7x | 0.915 |
| 7 | xgboost | onsets | weather+place | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.074 | 30.0x | 7.5% | 0.063 | 14.4x | 0.795 |
| 8 | xgboost | onsets | weather+place+wet_soil | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.072 | 29.3x | 7.5% | 0.065 | 14.7x | 0.803 |
| 9 | lightgbm | onsets | weather+place+history+recent | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.070 | 28.3x | 7.9% | 0.140 | 31.8x | 0.907 |
| 10 | lightgbm | onsets | weather+place+history+recent+wet_soil | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.069 | 28.1x | 7.7% | 0.134 | 30.5x | 0.906 |
| 11 | xgboost | all | weather+place | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.064 | 26.2x | 7.0% | 0.081 | 18.5x | 0.824 |
| 12 | lightgbm | onsets | weather+place | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.063 | 25.7x | 7.2% | 0.057 | 13.0x | 0.790 |
| 13 | lightgbm | all | weather+place | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.061 | 24.8x | 6.8% | 0.090 | 20.5x | 0.828 |
| 14 | lightgbm | onsets | weather+place+wet_soil | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.060 | 24.3x | 6.9% | 0.055 | 12.4x | 0.792 |
| 15 | xgboost | all | weather+place+wet_soil | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.059 | 23.9x | 6.6% | 0.085 | 19.3x | 0.826 |
| 16 | lightgbm | all | weather+place+wet_soil | {'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 31, 'min_child_samples': 50, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.8} | 0.058 | 23.4x | 6.8% | 0.089 | 20.2x | 0.830 |
