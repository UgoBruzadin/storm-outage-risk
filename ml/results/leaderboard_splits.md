# Leaderboard: splits

Final XGBoost settings on next year, unseen counties and random region-days, at >= 5% of customers. Ranked by onset PR-AUC.

### >= 5% out · time(train_years=[2024],test_years=[2025]) · ranked by onset_pr_auc

Event rate: 0.99% of all blocks, 0.53% of onset blocks.

| rank | model | train on | features | params | onset PR-AUC | onset lift | onset prec@top1% | all PR-AUC | all lift | all ROC-AUC |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | xgboost | all | weather+place+history+recent | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.093 | 17.5x | 13.2% | 0.391 | 39.4x | 0.906 |
| 2 | xgboost | all | weather | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.056 | 10.5x | 10.4% | 0.056 | 5.7x | 0.720 |
| 3 | climatology | all | - | {} | 0.008 | 1.5x | 1.8% | 0.014 | 1.5x | 0.594 |

### >= 5% out · county(folds=5) · ranked by onset_pr_auc

Event rate: 0.87% of all blocks, 0.50% of onset blocks.

| rank | model | train on | features | params | onset PR-AUC | onset lift | onset prec@top1% | all PR-AUC | all lift | all ROC-AUC |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | xgboost | all | weather+place+history+recent | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.104 | 20.6x | 12.8% | 0.392 | 44.9x | 0.899 |
| 2 | xgboost | all | weather | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.083 | 16.6x | 11.2% | 0.106 | 12.1x | 0.782 |
| 3 | climatology | all | - | {} | 0.005 | 1.0x | 0.5% | 0.008 | 1.0x | 0.488 |

### >= 5% out · random(folds=5) · ranked by onset_pr_auc

Event rate: 0.87% of all blocks, 0.50% of onset blocks.

| rank | model | train on | features | params | onset PR-AUC | onset lift | onset prec@top1% | all PR-AUC | all lift | all ROC-AUC |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | xgboost | all | weather+place+history+recent | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.103 | 20.5x | 13.0% | 0.406 | 46.4x | 0.902 |
| 2 | xgboost | all | weather | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.084 | 16.8x | 11.1% | 0.105 | 12.0x | 0.783 |
| 3 | climatology | all | - | {} | 0.010 | 1.9x | 1.9% | 0.032 | 3.7x | 0.712 |
