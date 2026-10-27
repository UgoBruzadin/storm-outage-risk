# Leaderboard: weathernext

weathernext-outage-forecasting's features, models and class weighting on MO/IL data, scored on random region-days (their split), unseen counties and next year, next to the final model. >= 5% of customers.

### >= 5% out · random(folds=5) · ranked by onset_pr_auc

Event rate: 0.77% of all blocks, 0.47% of onset blocks.

| rank | model | train on | features | params | onset PR-AUC | onset lift | onset prec@top1% | all PR-AUC | all lift | all ROC-AUC |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | xgboost | all | weather+place+recent | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.093 | 19.9x | 11.7% | 0.362 | 46.9x | 0.896 |
| 2 | xgboost | all | weathernext | {'n_estimators': 50, 'learning_rate': 0.1, 'max_depth': 6, 'min_child_weight': 5, 'subsample': 0.8, 'class_weight': 'balanced'} | 0.059 | 12.8x | 9.3% | 0.063 | 8.2x | 0.765 |
| 3 | logistic | all | weathernext | {'class_weight': 'balanced'} | 0.031 | 6.8x | 7.1% | 0.035 | 4.5x | 0.703 |

### >= 5% out · county(folds=5) · ranked by onset_pr_auc

Event rate: 0.77% of all blocks, 0.47% of onset blocks.

| rank | model | train on | features | params | onset PR-AUC | onset lift | onset prec@top1% | all PR-AUC | all lift | all ROC-AUC |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | xgboost | all | weather+place+recent | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.086 | 18.4x | 11.2% | 0.351 | 45.6x | 0.886 |
| 2 | xgboost | all | weathernext | {'n_estimators': 50, 'learning_rate': 0.1, 'max_depth': 6, 'min_child_weight': 5, 'subsample': 0.8, 'class_weight': 'balanced'} | 0.058 | 12.4x | 9.2% | 0.062 | 8.0x | 0.763 |
| 3 | logistic | all | weathernext | {'class_weight': 'balanced'} | 0.031 | 6.8x | 7.1% | 0.034 | 4.5x | 0.702 |

### >= 5% out · time(train_years=[2020, 2021, 2022, 2023, 2024],test_years=[2025]) · ranked by onset_pr_auc

Event rate: 0.99% of all blocks, 0.53% of onset blocks.

| rank | model | train on | features | params | onset PR-AUC | onset lift | onset prec@top1% | all PR-AUC | all lift | all ROC-AUC |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | xgboost | all | weather+place+recent | {'n_estimators': 800, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 20, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.106 | 19.9x | 13.9% | 0.420 | 42.3x | 0.910 |
| 2 | xgboost | all | weathernext | {'n_estimators': 50, 'learning_rate': 0.1, 'max_depth': 6, 'min_child_weight': 5, 'subsample': 0.8, 'class_weight': 'balanced'} | 0.053 | 10.0x | 9.6% | 0.049 | 4.9x | 0.696 |
| 3 | logistic | all | weathernext | {'class_weight': 'balanced'} | 0.046 | 8.7x | 10.0% | 0.041 | 4.1x | 0.674 |
