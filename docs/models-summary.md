# Every model tested on the whole USA (lower 48)

Onset PR-AUC: 2024 = selection year (newest HRRR run), 2025 = test year, scored once (five-run mean).
"vs E55" is the gain over E55's XGBoost on the same rows in that experiment, with a 95% storm-day range;
**bold** = passes E55's rule (range above zero, at least 2 of 3 seeds better). Two-state experiments
(E1–E54) are in `experiments.md`. Updated 2026-11-28.

## Baselines and the tree models

| Model | 2024 | 2025 | Notes | Source |
|---|---|---|---|---|
| Gust bins, one national table | 0.0211 | | rule on forecast gust only | E55, `usa_ablation_2024.csv` |
| Warnings + outlook (NWS + SPC) | 0.0183 | 0.0216 | the official-forecast benchmark | E55, `usa_final_2025.csv` |
| Gust bins per county | 0.0539 | | each county's rate at each gust level | E55 |
| XGBoost, weather inputs only | 0.0668 | | no place, history, outages or warnings | E55 |
| XGBoost, old settings (depth 4) | 0.0946 | | | E55 |
| Current headline (previous model) | | 0.0868 | | E55, `usa_final_2025.csv` |
| **E55 XGBoost** (depth 8, 1,600 trees, 110 inputs) | **0.1154** | **0.1021** (3 seeds: 0.1033) | **the model**: 4.7× warnings + outlook on 2025 | E55 |
| E55 live model (no outage data, 106 inputs) | | 0.0975 | 96% of E55; what the site ships | E55, `live_usa_2025.csv` |

## Other learners on E55's inputs

| Model | 2024 | 2025 | vs E55, 2024 | vs E55, 2025 | Verdict | Source |
|---|---|---|---|---|---|---|
| E57a network (MLP, hand-made neighbours) | 0.1146 | 0.0963 | −0.8% (−3.0 to +0.9) | −6.5% (−9.6 to −3.9) | rejected | `nn_2024.csv`, `nn_2025.csv` |
| E57a network + XGBoost | 0.1188 | 0.1028 | **+2.8% (1.9–3.7)** | −0.1% (−1.5 to +1.1) | passed 2024, failed 2025 | same |
| E57b none (network, no neighbours) | 0.1149 | 0.0974 | −0.6% (−2.9 to +1.0) | −5.4% (−8.8 to −2.5) | reference | `gnn_2024.csv`, `gnn_2025.csv` |
| E57b mean (GraphSAGE-mean) | 0.1157 | | +0.2% (−2.0 to +2.0) | | not refitted | same |
| E57b gated (GatedGCN-style) | 0.1160 | | +0.4% (−1.6 to +2.2) | | not refitted | same |
| E57b max-pool (GraphSAGE-pool) | 0.1163 | 0.1008 | +0.6% (−1.3 to +2.3) | −2.1% (−4.9 to +0.6) | beats hand-made both years, not XGBoost | same |
| E57b attention (GATv2, edge inputs) | 0.1165 | 0.1006 | +0.8% (−1.4 to +2.7) | −2.3% (−4.8 to +0.3) | beats hand-made both years, not XGBoost | same |
| **E57b attention + XGBoost** | **0.1196** | **0.1047** | **+3.5% (2.5–4.6)** | **+1.7% (0.5–2.9)** | **passes both years: headline candidate** | same |
| E58 Kumo Tabular (pretrained, 50,000-row context)* | 0.0987 | 0.0891 | −15.7% (−20.1 to −10.8) | −15.0% (−20.5 to −9.5) | rejected | `kumo_usa_2024.csv`, `kumo_usa_2025.csv` (kumo branch) |
| E58 Kumo + XGBoost* | 0.1174 | 0.1041 | +0.2% (−1.1 to +1.9) | −0.5% (−2.9 to +1.6) | no gain | same |

\* E58 scores every outage and 5% of the other decisions (weighted), so its PR-AUCs sit on slightly different rows:
its E55 XGBoost scores 0.1171 (2024) and 0.1047 (2025). Compare its gains, not its PR-AUCs. Kumo-Anomaly (unsupervised)
was not run: about 1 window per second on the 8 GB GPU, ~35 hours for two states hourly.

## What it adds up to
- **Trees win on this table.** Nothing beats E55's XGBoost on its own: a plain network (−6.5% on 2025), graph networks
  (−2%), a pretrained tabular foundation model (−15%).
- **Structure helps where trees can't reach.** Learned spreading between counties (E57b) beats the hand-made
  neighbour inputs by about 4.5% on 2025, and averaged with XGBoost it is the only network result that passes on both
  years (+1.7% on 2025).
- **Averages are easy to fool on the selection year.** E57a's and E58's averages looked good on 2024 and vanished on
  2025; E57b's held. The 2026 blind live test is the clean check for any change of headline.
