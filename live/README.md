# Live forecast

Every hour, the chance of a new outage (≥ 5% of a county's customers, after a day with none) in each Missouri and
Illinois county, in the 6 hours starting 2 hours later. Experimental research forecast: not from any utility or the
National Weather Service; don't use it for safety decisions.

## The model

The headline model without live outage data (docs/experiments.md, E43: 2.2× warnings + outlook on 2025, against
2.4× with outage data), trained on 2020–2025 by `ml/train_live.py` and frozen in `model/`. It is fed the five HRRR
runs issued 2–6 hours before each decision; the forecast is their mean and the range their lowest and highest.

## The feeds

The same sources as the training data, read as they are issued (`sources.py`):

| Input | Source |
|---|---|
| Weather in the past 6 hours, own county and neighbours | HRRR via Open-Meteo (identical values to the archive training used) |
| NWS warnings in force | Iowa Environmental Mesonet |
| SPC Day 1 outlook | Iowa Environmental Mesonet |
| Weather in the window ahead | HRRR runs as issued, hrrrzarr archive on AWS |
| County size, housing, tree canopy, neighbours | `static/`, exported once from the warehouse (`static.py`) |

## Same inputs as training

`features.py` rewrites the warehouse's SQL for these inputs in pandas. `parity.py` feeds it the warehouse's own raw
files and compares every input with the training table on 56 hours of 2025 (12,096 county-hours, including the
four worst storm days): all 39 identical.

## Run it

    pixi run python -m live.predict              # the current hour; writes live/out/
    pixi run python -m live.parity               # needs the warehouse
    pixi run python -m ml.train_live             # retrain (changes the frozen model)
