# Leaderboard: weathernext

weathernext-outage-forecasting's features, models and class weighting on MO/IL data, scored on random region-days (their split), unseen counties and next year, next to the final model. >= 5% of customers.

### >= 5% out · random(folds=5) · ranked by onset_pr_auc

Event rate: 0.87% of all blocks, 0.50% of onset blocks.

| rank | model | train on | features | params | onset PR-AUC | onset lift | onset prec@top1% | all PR-AUC | all lift | all ROC-AUC |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | xgboost | all | weather+place+history+recent | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.105 | 20.8x | 13.0% | 0.407 | 46.5x | 0.903 |
| 2 | xgboost | all | weathernext | {'n_estimators': 50, 'learning_rate': 0.1, 'max_depth': 6, 'min_child_weight': 5, 'subsample': 0.8, 'class_weight': 'balanced'} | 0.072 | 14.3x | 10.7% | 0.091 | 10.5x | 0.782 |
| 3 | logistic | all | weathernext | {'class_weight': 'balanced'} | 0.040 | 7.9x | 8.7% | 0.043 | 4.9x | 0.722 |

### >= 5% out · county(folds=5) · ranked by onset_pr_auc

Event rate: 0.87% of all blocks, 0.50% of onset blocks.

| rank | model | train on | features | params | onset PR-AUC | onset lift | onset prec@top1% | all PR-AUC | all lift | all ROC-AUC |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | xgboost | all | weather+place+history+recent | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.103 | 20.6x | 12.7% | 0.389 | 44.5x | 0.898 |
| 2 | xgboost | all | weathernext | {'n_estimators': 50, 'learning_rate': 0.1, 'max_depth': 6, 'min_child_weight': 5, 'subsample': 0.8, 'class_weight': 'balanced'} | 0.072 | 14.3x | 10.8% | 0.089 | 10.2x | 0.780 |
| 3 | logistic | all | weathernext | {'class_weight': 'balanced'} | 0.040 | 7.9x | 8.6% | 0.043 | 4.9x | 0.721 |

### >= 5% out · time(train_years=[2024],test_years=[2025]) · ranked by onset_pr_auc

Event rate: 0.99% of all blocks, 0.53% of onset blocks.

| rank | model | train on | features | params | onset PR-AUC | onset lift | onset prec@top1% | all PR-AUC | all lift | all ROC-AUC |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | xgboost | all | weather+place+history+recent | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.093 | 17.5x | 13.2% | 0.392 | 39.5x | 0.906 |
| 2 | logistic | all | weathernext | {'class_weight': 'balanced'} | 0.045 | 8.5x | 9.8% | 0.042 | 4.2x | 0.687 |
| 3 | xgboost | all | weathernext | {'n_estimators': 50, 'learning_rate': 0.1, 'max_depth': 6, 'min_child_weight': 5, 'subsample': 0.8, 'class_weight': 'balanced'} | 0.032 | 6.1x | 6.9% | 0.034 | 3.4x | 0.677 |
