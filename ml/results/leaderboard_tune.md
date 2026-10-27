# Leaderboard: tune

XGBoost grid on 2020–2023 → 2024 (validation), with and without as-of history, >= 5% of customers. Ranked by onset PR-AUC.

### >= 5% out · time(train_years=[2020, 2021, 2022, 2023],test_years=[2024]) · ranked by onset_pr_auc

Event rate: 0.77% of all blocks, 0.48% of onset blocks.

| rank | model | train on | features | params | onset PR-AUC | onset lift | onset prec@top1% | all PR-AUC | all lift | all ROC-AUC |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | xgboost | all | weather+place+history+recent | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 8, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.080 | 16.8x | 11.2% | 0.322 | 42.1x | 0.893 |
| 2 | xgboost | all | weather+place+history+recent | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 6, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.080 | 16.8x | 11.0% | 0.324 | 42.3x | 0.892 |
| 3 | xgboost | all | weather+place+recent | {'n_estimators': 800, 'learning_rate': 0.06, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.080 | 16.7x | 10.7% | 0.322 | 42.0x | 0.891 |
| 4 | xgboost | all | weather+place+history+recent | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 8, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.079 | 16.7x | 10.9% | 0.322 | 42.0x | 0.893 |
| 5 | xgboost | all | weather+place+recent | {'n_estimators': 400, 'learning_rate': 0.06, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.079 | 16.7x | 10.9% | 0.324 | 42.3x | 0.891 |
| 6 | xgboost | all | weather+place+history+recent | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 6, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.079 | 16.6x | 10.9% | 0.318 | 41.6x | 0.892 |
| 7 | xgboost | all | weather+place+recent | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.079 | 16.6x | 10.6% | 0.325 | 42.4x | 0.892 |
| 8 | xgboost | all | weather+place+recent | {'n_estimators': 800, 'learning_rate': 0.06, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.079 | 16.5x | 10.6% | 0.323 | 42.1x | 0.891 |
| 9 | xgboost | all | weather+place+recent | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.079 | 16.5x | 10.6% | 0.324 | 42.2x | 0.891 |
| 10 | xgboost | all | weather+place+recent | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 6, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.078 | 16.5x | 10.6% | 0.323 | 42.2x | 0.892 |
| 11 | xgboost | all | weather+place+recent | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 6, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.078 | 16.4x | 11.0% | 0.328 | 42.8x | 0.893 |
| 12 | xgboost | all | weather+place+history+recent | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 8, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.078 | 16.4x | 11.0% | 0.314 | 41.0x | 0.892 |
| 13 | xgboost | all | weather+place+history+recent | {'n_estimators': 400, 'learning_rate': 0.06, 'max_depth': 6, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.078 | 16.4x | 10.9% | 0.318 | 41.5x | 0.893 |
| 14 | xgboost | all | weather+place+recent | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 8, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.078 | 16.3x | 11.0% | 0.322 | 42.0x | 0.892 |
| 15 | xgboost | all | weather+place+recent | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 8, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.078 | 16.3x | 10.9% | 0.322 | 42.0x | 0.894 |
| 16 | xgboost | all | weather+place+history+recent | {'n_estimators': 400, 'learning_rate': 0.06, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.077 | 16.2x | 11.0% | 0.318 | 41.5x | 0.891 |
| 17 | xgboost | all | weather+place+recent | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 8, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.077 | 16.2x | 10.7% | 0.317 | 41.3x | 0.892 |
| 18 | xgboost | all | weather+place+recent | {'n_estimators': 400, 'learning_rate': 0.06, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.077 | 16.2x | 10.7% | 0.324 | 42.4x | 0.891 |
| 19 | xgboost | all | weather+place+history+recent | {'n_estimators': 800, 'learning_rate': 0.06, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.077 | 16.2x | 10.6% | 0.316 | 41.3x | 0.891 |
| 20 | xgboost | all | weather+place+recent | {'n_estimators': 400, 'learning_rate': 0.06, 'max_depth': 6, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.077 | 16.1x | 10.8% | 0.324 | 42.3x | 0.892 |
| 21 | xgboost | all | weather+place+history+recent | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.076 | 16.0x | 11.0% | 0.319 | 41.7x | 0.892 |
| 22 | xgboost | all | weather+place+recent | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 6, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.076 | 16.0x | 10.6% | 0.322 | 42.1x | 0.892 |
| 23 | xgboost | all | weather+place+history+recent | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 8, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.076 | 15.9x | 10.5% | 0.313 | 40.9x | 0.890 |
| 24 | xgboost | all | weather+place+history+recent | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.076 | 15.9x | 10.7% | 0.318 | 41.5x | 0.892 |
| 25 | xgboost | all | weather+place+history+recent | {'n_estimators': 800, 'learning_rate': 0.06, 'max_depth': 6, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.076 | 15.9x | 10.5% | 0.309 | 40.3x | 0.890 |
| 26 | xgboost | all | weather+place+recent | {'n_estimators': 800, 'learning_rate': 0.06, 'max_depth': 6, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.076 | 15.9x | 10.4% | 0.317 | 41.4x | 0.891 |
| 27 | xgboost | all | weather+place+history+recent | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 6, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.075 | 15.8x | 11.0% | 0.318 | 41.4x | 0.891 |
| 28 | xgboost | all | weather+place+history+recent | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 6, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.075 | 15.8x | 10.8% | 0.323 | 42.1x | 0.892 |
| 29 | xgboost | all | weather+place+recent | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 8, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.075 | 15.8x | 10.5% | 0.314 | 41.0x | 0.889 |
| 30 | xgboost | all | weather+place+recent | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 6, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.075 | 15.8x | 10.7% | 0.326 | 42.5x | 0.893 |
| 31 | xgboost | all | weather+place+recent | {'n_estimators': 400, 'learning_rate': 0.06, 'max_depth': 6, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.075 | 15.8x | 10.9% | 0.320 | 41.8x | 0.890 |
| 32 | xgboost | all | weather+place+history+recent | {'n_estimators': 400, 'learning_rate': 0.06, 'max_depth': 6, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.075 | 15.7x | 10.7% | 0.313 | 40.9x | 0.892 |
| 33 | xgboost | all | weather+place+recent | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.075 | 15.7x | 10.7% | 0.323 | 42.2x | 0.889 |
| 34 | xgboost | all | weather+place+history+recent | {'n_estimators': 400, 'learning_rate': 0.06, 'max_depth': 8, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.075 | 15.7x | 10.6% | 0.311 | 40.7x | 0.890 |
| 35 | xgboost | all | weather+place+recent | {'n_estimators': 400, 'learning_rate': 0.06, 'max_depth': 8, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.075 | 15.6x | 10.4% | 0.315 | 41.2x | 0.892 |
| 36 | xgboost | all | weather+place+history+recent | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.074 | 15.6x | 11.0% | 0.320 | 41.8x | 0.890 |
| 37 | xgboost | all | weather+place+history+recent | {'n_estimators': 400, 'learning_rate': 0.06, 'max_depth': 8, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.074 | 15.5x | 10.6% | 0.306 | 39.9x | 0.888 |
| 38 | xgboost | all | weather+place+recent | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.074 | 15.5x | 10.3% | 0.323 | 42.2x | 0.889 |
| 39 | xgboost | all | weather+place+recent | {'n_estimators': 400, 'learning_rate': 0.06, 'max_depth': 8, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.073 | 15.4x | 10.2% | 0.315 | 41.1x | 0.888 |
| 40 | xgboost | all | weather+place+history+recent | {'n_estimators': 800, 'learning_rate': 0.06, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.073 | 15.4x | 10.3% | 0.312 | 40.8x | 0.890 |
| 41 | xgboost | all | weather+place+history+recent | {'n_estimators': 400, 'learning_rate': 0.06, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.073 | 15.3x | 10.5% | 0.313 | 40.8x | 0.890 |
| 42 | xgboost | all | weather+place+history+recent | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.073 | 15.3x | 10.8% | 0.317 | 41.4x | 0.890 |
| 43 | xgboost | all | weather+place+recent | {'n_estimators': 800, 'learning_rate': 0.06, 'max_depth': 6, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.072 | 15.2x | 10.3% | 0.311 | 40.6x | 0.887 |
| 44 | xgboost | all | weather+place+history+recent | {'n_estimators': 800, 'learning_rate': 0.06, 'max_depth': 6, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.071 | 15.0x | 10.5% | 0.303 | 39.6x | 0.888 |
| 45 | xgboost | all | weather+place+history+recent | {'n_estimators': 800, 'learning_rate': 0.06, 'max_depth': 8, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.070 | 14.7x | 10.1% | 0.301 | 39.3x | 0.885 |
| 46 | xgboost | all | weather+place+recent | {'n_estimators': 800, 'learning_rate': 0.06, 'max_depth': 8, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.070 | 14.7x | 10.3% | 0.305 | 39.9x | 0.887 |
| 47 | xgboost | all | weather+place+history+recent | {'n_estimators': 800, 'learning_rate': 0.06, 'max_depth': 8, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.067 | 14.1x | 9.8% | 0.293 | 38.2x | 0.882 |
| 48 | xgboost | all | weather+place+recent | {'n_estimators': 800, 'learning_rate': 0.06, 'max_depth': 8, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.067 | 14.1x | 9.5% | 0.302 | 39.4x | 0.882 |
| 49 | climatology | all | - | {} | 0.008 | 1.6x | 0.9% | 0.013 | 1.6x | 0.647 |
