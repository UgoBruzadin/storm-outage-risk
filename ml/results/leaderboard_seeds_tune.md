# Leaderboard: seeds_tune

Leading XGBoost settings from tune.yaml, with and without as-of history, 5 seeds each, on 2020–2023 → 2024 (validation), >= 5% of customers.

### >= 5% out · time(train_years=[2020, 2021, 2022, 2023],test_years=[2024]) · ranked by onset_pr_auc

Event rate: 0.77% of all blocks, 0.48% of onset blocks.

| rank | model | train on | features | params | onset PR-AUC | onset lift | onset prec@top1% | all PR-AUC | all lift | all ROC-AUC |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | xgboost | all | weather+place+history+recent | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 8, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8, 'random_state': 0} | 0.080 | 16.8x | 11.2% | 0.322 | 42.1x | 0.893 |
| 2 | xgboost | all | weather+place+recent | {'n_estimators': 800, 'learning_rate': 0.06, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8, 'random_state': 4} | 0.080 | 16.7x | 10.9% | 0.321 | 41.9x | 0.891 |
| 3 | xgboost | all | weather+place+recent | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8, 'random_state': 3} | 0.080 | 16.7x | 10.7% | 0.325 | 42.4x | 0.892 |
| 4 | xgboost | all | weather+place+recent | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 8, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8, 'random_state': 4} | 0.080 | 16.7x | 10.8% | 0.325 | 42.4x | 0.894 |
| 5 | xgboost | all | weather+place+recent | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8, 'random_state': 4} | 0.080 | 16.7x | 10.7% | 0.327 | 42.6x | 0.892 |
| 6 | xgboost | all | weather+place+recent | {'n_estimators': 800, 'learning_rate': 0.06, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8, 'random_state': 0} | 0.080 | 16.7x | 10.7% | 0.322 | 42.0x | 0.891 |
| 7 | xgboost | all | weather+place+history+recent | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8, 'random_state': 2} | 0.080 | 16.7x | 10.9% | 0.321 | 41.9x | 0.892 |
| 8 | xgboost | all | weather+place+recent | {'n_estimators': 800, 'learning_rate': 0.06, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8, 'random_state': 1} | 0.079 | 16.7x | 11.1% | 0.322 | 42.0x | 0.892 |
| 9 | xgboost | all | weather+place+history+recent | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8, 'random_state': 3} | 0.079 | 16.7x | 10.9% | 0.321 | 41.9x | 0.892 |
| 10 | xgboost | all | weather+place+recent | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 8, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8, 'random_state': 2} | 0.079 | 16.6x | 11.0% | 0.324 | 42.3x | 0.893 |
| 11 | xgboost | all | weather+place+recent | {'n_estimators': 800, 'learning_rate': 0.06, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8, 'random_state': 3} | 0.079 | 16.6x | 10.9% | 0.319 | 41.6x | 0.890 |
| 12 | xgboost | all | weather+place+history+recent | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 8, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8, 'random_state': 4} | 0.079 | 16.6x | 11.1% | 0.318 | 41.5x | 0.893 |
| 13 | xgboost | all | weather+place+history+recent | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 8, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8, 'random_state': 2} | 0.079 | 16.6x | 11.0% | 0.320 | 41.8x | 0.893 |
| 14 | xgboost | all | weather+place+recent | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 8, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8, 'random_state': 3} | 0.079 | 16.6x | 11.0% | 0.322 | 42.1x | 0.892 |
| 15 | xgboost | all | weather+place+recent | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8, 'random_state': 1} | 0.079 | 16.6x | 10.8% | 0.326 | 42.6x | 0.892 |
| 16 | xgboost | all | weather+place+history+recent | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8, 'random_state': 1} | 0.079 | 16.5x | 11.0% | 0.323 | 42.1x | 0.893 |
| 17 | xgboost | all | weather+place+history+recent | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 8, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8, 'random_state': 3} | 0.079 | 16.5x | 11.0% | 0.318 | 41.5x | 0.893 |
| 18 | xgboost | all | weather+place+recent | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 8, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8, 'random_state': 1} | 0.079 | 16.5x | 11.0% | 0.328 | 42.9x | 0.894 |
| 19 | xgboost | all | weather+place+recent | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8, 'random_state': 0} | 0.079 | 16.5x | 10.6% | 0.324 | 42.2x | 0.891 |
| 20 | xgboost | all | weather+place+history+recent | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 8, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8, 'random_state': 1} | 0.078 | 16.4x | 10.9% | 0.321 | 41.9x | 0.893 |
| 21 | xgboost | all | weather+place+recent | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8, 'random_state': 2} | 0.078 | 16.4x | 10.6% | 0.324 | 42.2x | 0.892 |
| 22 | xgboost | all | weather+place+history+recent | {'n_estimators': 800, 'learning_rate': 0.06, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8, 'random_state': 4} | 0.078 | 16.4x | 10.3% | 0.317 | 41.4x | 0.891 |
| 23 | xgboost | all | weather+place+recent | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 8, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8, 'random_state': 0} | 0.078 | 16.3x | 10.9% | 0.322 | 42.0x | 0.894 |
| 24 | xgboost | all | weather+place+history+recent | {'n_estimators': 800, 'learning_rate': 0.06, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8, 'random_state': 1} | 0.078 | 16.3x | 10.6% | 0.317 | 41.3x | 0.891 |
| 25 | xgboost | all | weather+place+history+recent | {'n_estimators': 800, 'learning_rate': 0.06, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8, 'random_state': 3} | 0.078 | 16.3x | 10.5% | 0.315 | 41.1x | 0.892 |
| 26 | xgboost | all | weather+place+history+recent | {'n_estimators': 800, 'learning_rate': 0.06, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8, 'random_state': 0} | 0.077 | 16.2x | 10.6% | 0.316 | 41.3x | 0.891 |
| 27 | xgboost | all | weather+place+recent | {'n_estimators': 800, 'learning_rate': 0.06, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8, 'random_state': 2} | 0.077 | 16.2x | 10.9% | 0.319 | 41.6x | 0.891 |
| 28 | xgboost | all | weather+place+history+recent | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8, 'random_state': 4} | 0.077 | 16.2x | 10.9% | 0.319 | 41.7x | 0.892 |
| 29 | xgboost | all | weather+place+history+recent | {'n_estimators': 800, 'learning_rate': 0.06, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8, 'random_state': 2} | 0.077 | 16.1x | 10.8% | 0.316 | 41.3x | 0.891 |
| 30 | xgboost | all | weather+place+history+recent | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8, 'random_state': 0} | 0.076 | 16.0x | 11.0% | 0.319 | 41.7x | 0.892 |
