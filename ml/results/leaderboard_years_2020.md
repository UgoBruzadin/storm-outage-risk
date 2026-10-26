# Leaderboard: years_2020

Final XGBoost settings trained on 2020–2024, tested on 2025, >= 5% of customers. Ranked by onset PR-AUC.

### >= 5% out · time(train_years=[2020, 2021, 2022, 2023, 2024],test_years=[2025]) · ranked by onset_pr_auc

Event rate: 0.99% of all blocks, 0.53% of onset blocks.

| rank | model | train on | features | params | onset PR-AUC | onset lift | onset prec@top1% | all PR-AUC | all lift | all ROC-AUC |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | xgboost | all | weather+place+recent | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.101 | 18.9x | 13.5% | 0.417 | 42.1x | 0.908 |
| 2 | xgboost | all | weather+place | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.086 | 16.2x | 12.6% | 0.086 | 8.7x | 0.778 |
| 3 | xgboost | all | weather | {'n_estimators': 400, 'learning_rate': 0.03, 'max_depth': 4, 'min_child_weight': 5, 'subsample': 0.8, 'colsample_bytree': 0.8} | 0.070 | 13.3x | 11.5% | 0.063 | 6.3x | 0.722 |
| 4 | climatology | all | - | {} | 0.009 | 1.8x | 1.7% | 0.018 | 1.8x | 0.634 |
