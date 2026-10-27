# Leaderboard: years_2024

Final XGBoost settings trained on 2024, tested on 2025, >= 5% of customers. Ranked by onset PR-AUC.

### >= 5% out · time(train_years=[2024],test_years=[2025]) · ranked by onset_pr_auc

Event rate: 0.99% of all blocks, 0.53% of onset blocks.

| rank | model | train on | features | params | onset PR-AUC | onset lift | onset prec@top1% | all PR-AUC | all lift | all ROC-AUC |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | xgboost | all | weather+place+recent | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.086 | 16.1x | 12.6% | 0.389 | 39.1x | 0.904 |
| 2 | xgboost | all | weather+place | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.068 | 12.8x | 11.3% | 0.074 | 7.5x | 0.768 |
| 3 | xgboost | all | weather | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.057 | 10.6x | 10.5% | 0.057 | 5.8x | 0.723 |
| 4 | climatology | all | - | {} | 0.008 | 1.5x | 1.7% | 0.014 | 1.5x | 0.594 |
