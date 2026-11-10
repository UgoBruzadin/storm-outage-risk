# Seven states (IL, IN, IA, MI, MN, MO, WI; 649 counties), headline steps only

Run overnight 2026-11-07 on the seven-state warehouse: `forecast_test`, `forecast_ensemble`, `significance` and
`states` (ml/midwest_test.py), then the lean training check (ml/lean_headline.py) on five and seven states.
Not reviewed. See docs/experiments.md, E53 and E54.

The files here have the same names as the five-state ones in `ml/results/` and replaced them during the run; they
were moved here so `ml/results/` holds one consistent five-state run (E52). `summary.md` mixes the two runs: its
headline and by-state rows are seven-state, the rest five-state.

- `seven_states_stage1.log`   downloads and the warehouse build
- `seven_states_stage2.log`   the four steps and the lean runs, with peak memory
- `seven_states_memory.log`   swap use every 5 minutes
