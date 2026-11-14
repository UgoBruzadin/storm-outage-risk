# Data dictionary

Every table, every model feature, and the SQL techniques that build them. Row counts are
from the last `pixi run build` (HRRR counts grow as more weather years download).

The current model is the USA hourly model: [Model inputs — the USA hourly model](#model-inputs--the-usa-hourly-model-e55)
lists its 110 inputs. The 6-hour tables and features further down are the Missouri + Illinois model the published
results come from.

```
raw files ──► staging (views)          ──► intermediate (tables)            ──► marts (tables)              ──► ml/
EAGLE-I       stg_eaglei__outages          int_eaglei__blocks_6h (heartbeat)    mart_study__region_6h           features + label
MCC.csv       stg_eaglei__customers        int_study__regions                   mart_study__region_resilience
HRRR          stg_hrrr__hourly             int_study__outages_6h
Storm Events  stg_noaa__storm_events       int_study__weather_6h
zone file     stg_noaa__zone_county        int_study__storm_events_6h
ACS           stg_acs__housing
geo + canopy  stg_geo__regions
KSTL          stg_noaa__kstl_hourly        (legacy St. Louis notebook only)
```

## Where the data comes from

Every raw file, who publishes it, and how it gets here. All public and free; everything
except EAGLE-I is downloaded by a script (`pixi run fetch-<name>`, code in `ingest/`).

| Data | Publisher | What it is | Years / version | Source (URL) | How we get it | Lands in |
|---|---|---|---|---|---|---|
| **Power outages** | U.S. DOE / Oak Ridge National Laboratory (EAGLE-I) | customers out per county every 15 min, scraped from utility outage maps | 2014-11 → 2025 | figshare / ORNL releases — cite DOI [10.13139/ORNLNCCS/1975202](https://doi.org/10.13139/ORNLNCCS/1975202) (data) and [10.13139/ORNLNCCS/1975203](https://doi.org/10.13139/ORNLNCCS/1975203) (documentation); `citation_*.txt` ship with the download | **manual download** (one zip per release) | `data/raw/eaglei/eaglei_outages_*.csv` |
| Customers per county | same (EAGLE-I) | modeled customer count per county (`MCC.csv`) and state coverage over time (`coverage_history.csv`) | ships with the outage data | same download | manual | `data/raw/eaglei/` |
| **Storm ingredients** | NOAA (HRRR model), served by **Open-Meteo** | hourly wind, gusts, winds aloft, CAPE, precipitation, temperature, freezing level at each region's weather point | 2018–2025 (HRRR archive begins 2018-01-01) | `https://historical-forecast-api.open-meteo.com/v1/forecast` with `models=ncep_hrrr_conus` | `fetch-weather` (rate-limited, resumable) | `data/raw/weather/hrrr/<region>_<year>.csv.gz` |
| **Storm reports** | NOAA NCEI Storm Events database | spotter / NWS reports of thunderstorm wind, hail, tornadoes, winter storms… with times and places | 2014–2025 | `https://www.ncei.noaa.gov/pub/data/swdi/stormevents/csvfiles/` | `fetch-storm-events` (newest file per year) | `data/raw/storm_events/` |
| **Official forecasts** | NWS warnings and SPC Day 1 convective outlooks, archived by the Iowa Environmental Mesonet | warnings (severe thunderstorm, tornado, high wind, ice storm, winter storm, blizzard) by county or zone, with issue and expiry; outlook polygons (risk level, wind / tornado / hail probability) joined to each region's interior point | 2014–2025 | `https://mesonet.agron.iastate.edu/cgi-bin/request/gis/` (`watchwarn.py`, `outlooks.py`) | `fetch-nws` | `data/raw/nws/` |
| Zone → county map | NOAA National Weather Service | which counties make up each forecast zone | file `bp16ap26` (16 Apr 2026) | `https://www.weather.gov/gis/ZoneCounty` | `fetch-storm-events` | `data/raw/storm_events/zone_county_*.dbx` |
| **County shapes** | U.S. Census Bureau (TIGER cartographic boundaries) | county polygons and land area, 1:500k | 2023 | `https://www2.census.gov/geo/tiger/GENZ2023/shp/cb_2023_us_county_500k.zip` | `fetch-counties` | `data/raw/geo/regions_study.*` |
| **Tree canopy** | USDA Forest Service, distributed by MRLC (NLCD Tree Canopy Cover) | % tree canopy per 30 m pixel; we request 90 m | 2021 (v2021-4) | MRLC map service `https://www.mrlc.gov/geoserver/ows`, coverage `mrlc_download__nlcd_tcc_conus_2021_v2021-4` | `fetch-tree-canopy` (one cut-out per region, summarized) | `data/raw/geo/tree_canopy_2021.csv` |
| **Housing** | U.S. Census Bureau, American Community Survey | tables B25034 (year built), B25035 (median year built), B01003 (population), B25001 (housing units) | 2020–2024 5-year estimates | `https://www2.census.gov/programs-surveys/acs/summary_file/2024/table-based-SF/data/5YRData/` (the Census API now needs a key; these files don't) | `fetch-acs` | `data/raw/acs/` |
| HRRR forecasts as issued | NOAA HRRR, University of Utah hrrrzarr archive on AWS | each hourly run's forecast at each region's weather point; five-run mean from June 2024 only (E47) | December 2019 → 2025 | `https://hrrrzarr.s3.amazonaws.com/sfc` | `fetch-hrrr-forecast` | `data/raw/weather/hrrr_fcst/` |
| HRRR, whole country | NOAA HRRR GRIB2 archive on AWS | the 11 storm ingredients for every county in the lower 48, read by byte range from each forecast file's index; replaces Open-Meteo and hrrrzarr beyond two states | 2020 → 2025 | `https://noaa-hrrr-bdp-pds.s3.amazonaws.com` | `fetch-hrrr-grib`, then `grib_to_study.py` | `data/raw/weather/hrrr_grib/`, then `hrrr/` and `hrrr_fcst/` |
| Public roads (USA model) | U.S. Census Bureau TIGER/Line | primary, secondary and local roads; drawn onto the canopy tiles for canopy over roads | 2023 (2022 or 2024 where 2023 fails) | `https://www2.census.gov/geo/tiger/TIGER2023/ROADS/` | `fetch_roads.py` | `data/raw/place/roads.csv` |
| Tree type and size (USA model) | USFS TreeMap | forest type, tree size and dead trees per 30 m forest pixel | 2022 (RDS-2025-0032) | Forest Service Research Data Archive | `fetch-treemap` | `data/raw/place/treemap.csv` |
| Stand age (USA model) | USFS Forest Inventory (FIA DataMart) | stand age on field plots | surveys 2014–2019 | FIA DataMart `MO_COND.csv`, `IL_COND.csv` | `fetch-forest-age` | `data/raw/place/forest_age.csv` |
| Soil (USA model) | USDA NRCS SSURGO, Soil Data Access | drainage, flooding, water table and bedrock depth | current version | Soil Data Access | `fetch-soil` | `data/raw/place/soil.csv` |
| Rivers and streams (USA model) | USGS National Hydrography Dataset | rivers mapped as areas, stream lines | current version | The National Map NHD service | `fetch-water` | `data/raw/place/water.csv` |
| Flood zones (USA model) | FEMA National Flood Hazard Layer | 1% annual chance flood zones | current version | NFHL map service | `fetch-flood-zones` | `data/raw/place/flood_zones.csv` |
| Transmission lines (USA model) | HIFLD | high-voltage lines | about 2023 | HIFLD Electric Power Transmission Lines | `fetch-transmission` | `data/raw/place/transmission.csv` |
| Utilities (USA model) | U.S. EIA Form 861 | utilities per county, ownership, reliability | 2015–2019 | EIA-861 archive | `fetch-utilities` | `data/raw/place/utilities.csv` |
| Airport weather (legacy) | NOAA NCEI Global Hourly (ISD), AWS Open Data mirror | observations at St. Louis Lambert (KSTL, station 72434013994) | 2014–2025-08 | `https://noaa-global-hourly-pds.s3.amazonaws.com/<year>/72434013994.csv` | `fetch-noaa` | `data/raw/noaa/` |

Each source's quirks, and what we did about them, are in [data-notes.md](data-notes.md).

Two ideas run through everything:
- **Region** = a county, except St. Louis City (29510) + County (29189), merged into
  `29189+29510` because EAGLE-I files the County's outages under the City in 2020–2024.
  216 regions. Macro: `{{ region_fips('col') }}`.
- **Block** = 6 hours starting 00/06/12/18 UTC. Macro: `{{ block_6h('col') }}`.

---

## Model inputs — the USA hourly model (E55)

The model chosen in E55 ([experiments.md](experiments.md)) has 110 inputs. The live model drops the 4 marked ⛔,
which need outage data a live job can't get (`live.features.OUTAGE_INPUTS`), leaving 106. The exact list is in
`live/model_usa/meta.json`.

```
ingest/fetch_*.py ─► data/raw/ ─► dbt ─► mart_study__region_1h ─┐
                                                                 ├─► ml/data.py load_hourly() + add_derived()
             data/cache/neighbors_1h (ml/data.py) ───────────────┘                │
                                                     ml/usa_ablation.py add_train() / add_inputs()
                                                     ml/place_extra.py add_place()  ─► model rows
```

**A row** is one region at one decision hour `h`. Inputs use only what is known at `h`. The label asks whether a new
outage starts in the window h + 2 … h + 7 (see [Label and rows](#label-and-rows)).

### Past weather: the 6 hours before `h` (15 inputs + 2 calendar)

From `mart_study__region_1h`, over the hourly HRRR weather in `stg_hrrr__hourly`. Each hour is forecast hour 1 of the
run issued the hour before (Open-Meteo, or `fetch_hrrr_grib.py` + `grib_to_study.py hourly` beyond two states). These
hours have already happened, so training, scoring and the live job use the same kind of data. A summary is NULL unless
all 6 hours exist.

| Inputs | Operation |
|---|---|
| `gust_max_ms`, `wind10_max_ms`, `wind850_max_ms`, `cape_max_jkg` | max over the 6 hours |
| `shear_0_6km_max_ms` | per hour √((u500 − u10)² + (v500 − v10)²), then the max |
| `precip_sum_mm`, `precip_max_1h_mm` | sum and max; an hour over 100 mm counts as unknown (an archive artifact) |
| `temp_min_c`, `temp_mean_c`, `freezing_level_min_m` | min, mean, min |
| `icing_hours` | hours with temperature ≤ 0 °C and rain > 0 |
| `hail_hours` | hours with CAPE ≥ 500 J/kg, rain ≥ 2 mm and freezing level ≤ 3,500 m |
| `wind_x_precip`, `wind_squared`, `shear_x_cape` | gust × rain sum, gust², shear × CAPE (`ml/data.py add_derived`) |
| `month`, `block_hour_utc` | calendar month and UTC hour of `h` |

### Window weather: the hours being predicted (15 + 5 inputs)

The same summaries over h + 2 … h + 7, prefixed `win_`, plus five duration / spread inputs. The source depends on use:

- **Training** uses the weather that happened (`ml/forecast_test.py actual_window`, `usa_ablation.duration_actual`).
- **Scoring and the live job** use HRRR forecasts as issued (`ft.window_from_forecast`, `usa_ablation.duration_forecast`):
  the run issued `age` hours before `h`, forecast hours age + 2 … age + 7. The 2025 test and the live job feed each of
  the five runs issued 2–6 hours before `h` through the model and average the chances.

| Inputs | Operation |
|---|---|
| `win_gust_max_ms` … `win_shear_x_cape` (15) | as the past-weather table, over the window |
| `win_gust_hours15`, `win_gust_hours20` | hours with gust ≥ 15 / ≥ 20 m/s |
| `win_gust_mean`, `win_gust_median` | mean and median gust |
| `win_gustiness_max` | max of gust − 10 m wind |

### The place (6 inputs)

From `int_study__regions`.

| Input | Source → script | Operation |
|---|---|---|
| `log_customers` | EAGLE-I modeled customers (`MCC.csv`, manual download) | log10 of customers |
| `housing_per_km2` | ACS B25001 (`fetch_acs.py`), Census land area (`fetch_counties.py`) | housing units ÷ land km² |
| `share_homes_pre1960` | ACS B25034 | homes built before 1960 ÷ all homes |
| `median_year_built` | ACS B25035 | county median; St. Louis City + County housing-weighted |
| `canopy_mean_pct`, `canopy_dense_share` | NLCD Tree Canopy 2021 (`fetch_tree_canopy.py`), ~90 m pixels | mean % canopy; share of pixels ≥ 50% |

### Official forecasts (8 inputs)

From `fetch_nws.py` (Iowa Environmental Mesonet) through `int_study__nws_1h`.

| Inputs | Operation |
|---|---|
| `warn_svr`, `warn_tor`, `warn_wind`, `warn_winter` | 0/1: a warning of that type (SV / TO / HW / IS, WS, BZ) in force at `h`; zone warnings spread to their counties with the NWS zone–county file |
| `spc_cat`, `spc_wind_prob`, `spc_tor_prob`, `spc_hail_prob` | the latest SPC Day 1 outlook issued before `h` and valid at `h` |

### Recent outages (2 inputs, both ⛔)

From EAGLE-I's 15-minute snapshots: `int_study__outages_1h` keeps each hour's worst snapshot, and the mart turns it into
`pct_out`, the share of customers out. `pct_out` is unknown when EAGLE-I was down, or when the count exceeds 1.5× the
customers.

| Input | Operation |
|---|---|
| ⛔ `pct_out_now` | `pct_out` in the hour before `h` |
| ⛔ `max_pct_out_prev_24h` | worst hour in the 24 hours before `h` |

### Neighbours (8 inputs + 2 ⛔)

Built in `ml/data.py _build_neighbor_cache` from the pairs in `int_study__region_neighbors`, a year at a time.
`near_*` are the regions within 100 km. `up_*` are the regions within 200 km at a bearing of 200–290°, the direction
most storms arrive from. Each value is taken across those neighbours at `h`.

| Inputs | Operation |
|---|---|
| `near_gust_max_ms`, `up_gust_max_ms`, `near_cape_max_jkg`, `up_cape_max_jkg` | max over neighbours of their past-6-hour value |
| `near_precip_max_mm`, `up_precip_max_mm` | max over neighbours of their past-6-hour rain sum |
| `near_warn_share`, `up_warn_share` | share of neighbours under a severe thunderstorm or tornado warning |
| ⛔ `near_pct_out_max`, ⛔ `up_pct_out_max` | max over neighbours of `pct_out_now` |

### History (5 inputs)

From `mart_study__region_history_asof`, the 3 years before January 1 of the row's year (a 2024 row sees 2021–2023), so
no row sees its own year. An event is a run of 6-hour blocks with ≥ 1% of customers out.

| Input | Meaning |
|---|---|
| `hist_hours_out_per_customer` | customer-hours lost per customer per year |
| `hist_events_per_year` | events per year observed |
| `hist_storm_hit_rate` | share of blocks with a NOAA storm report (`fetch_storm_events.py`) that became an event |
| `hist_quiet_event_rate` | share of blocks without a storm report that became an event |
| `hist_repeat_7d_share` | share of events followed by another within 7 days |

### Roads and location (5 inputs)

Joined in `ml/usa_ablation.py add_inputs`.

| Input | Source → script | Operation |
|---|---|---|
| `log_road_per_customer` | TIGER 2023 public roads (`fetch_roads.py`) | log10(road km) − log10(customers) |
| `road_treed_share`, `road_canopy_mean_pct` | the roads drawn onto the canopy tiles | share of road pixels with ≥ 50% canopy; mean canopy under the roads |
| `lat`, `lon` | `fetch_counties.py` | the region's representative point (always inside it; also its weather point) |

### E47 place groups (37 inputs)

One CSV per source in `data/raw/place/`, joined in `ml/place_extra.py add_place`. A region missing from a file gets
NaN, which XGBoost handles as its own case.

| Group | Inputs | Source → script |
|---|---|---|
| Tree type | `tm_share_oak_hickory`, `tm_share_elm_ash_cottonwood`, `tm_share_softwood`, `tm_share_oak_pine`, `tm_share_maple_beech`, `tm_share_oak_gum_cypress`: share of forest pixels | USFS TreeMap 2022 (`fetch_treemap.py`) |
| Tree size | `tm_height_ft`, `tm_diameter_in`, `tm_live_per_acre`, `tm_basal_area`: mean over forest pixels | TreeMap |
| Dead trees and ash | `tm_dead_per_acre`, `tm_dead_volume`, `tm_ash_stem_share` | TreeMap and its tree table |
| Tree age | `stand_age_mean`, `stand_age_old` (share of forest ≥ 80 years); blank under 5 plots | FIA plots, surveys 2014–2019 (`fetch_forest_age.py`) |
| Soil | `soil_poor_drain_share`, `soil_group_d_share`, `soil_flood_share`, `soil_water_table_cm`, `soil_bedrock_cm`: acre-weighted; no water table or bedrock within ~2 m = 201 cm | NRCS SSURGO (`fetch_soil.py`) |
| Recent rain | `precip_prev_72h_mm`: rain in the 72 hours before `h` (mart; NULL unless all 72 hours exist); `wind_x_wet_soil` = `gust_max_ms` × that | HRRR, as past weather |
| Wet soil | `poor_drain_x_rain` = poor-drain share × 72-hour rain; `poor_drain_x_wind_rain` = poor-drain share × `wind_x_wet_soil` | computed in `add_place` |
| Rivers and streams | `water_share` (Census water area), `river_near_share` (within 1 km of a river mapped as an area), `stream_km_per_km2` | USGS NHD (`fetch_water.py`) |
| Flood zones | `flood_zone_share`; blank rather than 0 where no digital map exists | FEMA NFHL (`fetch_flood_zones.py`) |
| Utilities | `util_count`; `util_share_iou`, `util_share_coop`, `util_share_public` (a utility's customers split evenly over its counties); `util_saidi`, `util_saifi`, `util_saidi_med` (means 2015–2019) | EIA-861 (`fetch_utilities.py`) |
| Transmission lines | `transmission_km_per_km2`, `transmission_hv_km_per_km2` (≥ 230 kV) | HIFLD (`fetch_transmission.py`) |

### Label and rows

Added in `ml/data.py _hourly_query`, not inputs.

| Column | Meaning |
|---|---|
| `y` | 1 if the worst hour in h + 2 … h + 7 has ≥ 5% of customers out; the window needs ≥ 3 of its 6 hours known |
| rows kept | new outages only: the region was below 5% when the window began and in the hours before it; only region-years EAGLE-I tracked (`mart_study__region_coverage`) |
| `weight` | 10 on the training rows sampled from those not followed by an outage (10% kept, by a hash of region and hour); 1 elsewhere. Scored years are never sampled |

---

## Staging — one view per raw source (rename, cast, decode; nothing else)

| Table | One row = | Rows | What it does |
|---|---|---|---|
| `stg_eaglei__outages` | county × 15-min snapshot with ≥ 1 customer out (all U.S.) | view over ~250M | merges 2023's `sum` column into `customers_out`; adds `snapshot_time` (rounded to 15 min — Sept 2025 has duplicate snapshots) |
| `stg_eaglei__customers` | county | 3,233 | customers per county; FIPS zero-padded; drops `Grand Total` |
| `stg_hrrr__hourly` | region × hour | 5.1M | HRRR storm ingredients; converts wind speed + direction to u/v components so shear can be computed |
| `stg_noaa__storm_events` | storm report (MO + IL) | 48,450 | rebuilds timestamps, converts local standard time → UTC |
| `stg_noaa__zone_county` | NWS zone × county | 221 | maps winter-storm zones to counties |
| `stg_acs__housing` | county (MO + IL) | 217 | population, housing units, homes built before 1960, median year built |
| `stg_geo__regions` | region | 216 | land area, weather point (lat/lon), tree canopy |
| `stg_noaa__kstl_hourly` | hour | 102,035 | airport weather; legacy notebook only |

## Intermediate — reshape and join

| Table | One row = | Rows | Built how |
|---|---|---|---|
| `int_study__regions` | region | 216 | customers summed per region; ACS joined; density = housing ÷ land km² |
| `int_eaglei__blocks_6h` | 6-hour block | 16,316 | **heartbeat**: how many national snapshots exist in the block (max 24). `eaglei_ok` = at least 12 → EAGLE-I was running |
| `int_study__outages_6h` | region × block *with an outage* | 1.33M | per county per slot (max) → **sum** counties into regions per slot → per block: `peak_out` (max), `mean_out` (avg, missing slots = 0) |
| `int_study__weather_6h` | region × block | 632k | HRRR hours summarized per block (max wind, total rain, …) |
| `int_study__storm_events_6h` | region × block with a report | 254k | report counts by type; zone events spread to their counties; multi-block events counted in each block |

## Marts — what the model and the app read

### `mart_study__region_6h` — the modeling table (3.52M rows = 216 regions × 16,316 blocks)

Built as a **grid**: every region `CROSS JOIN` every block, then `LEFT JOIN` outages,
weather and storm reports, so blocks with no outage exist (as 0) instead of being missing.

| Column | Meaning |
|---|---|
| `peak_out` | worst customers-out snapshot in the block. **NULL** if EAGLE-I was down; **0** if it was up and the region had no row; else the value |
| `peak_suspect` | peak > 1.5 × customers (a glitch, or a customer count that's too low) |
| `peak_pct_out` | peak ÷ customers × 100, capped at 100; NULL if unknown or suspect — **the label comes from this** |
| `mean_out` | average customers out over the block |
| `eaglei_snapshots` | heartbeat count for the block |
| `has_weather` | all 6 hours of HRRR weather exist |
| weather, place, calendar columns | see Features below |
| `storm_*` | NOAA storm report counts — **context only, never features** (written after the fact) |

### `mart_study__region_resilience` — the scorecard (216 rows)

From **2020–2023 only** (dbt vars `history_start` / `history_end`), so it can be used as
features for 2024–2025 without leaking. An **event** = consecutive blocks with ≥ 1% out.

| Column | Meaning |
|---|---|
| `hours_out_per_customer` | customer-hours lost ÷ customers ÷ years (a SAIDI-like burden) |
| `events_per_year` | events per year |
| `storm_hit_rate` | share of blocks with a storm report that became an event — closest to "vulnerability" |
| `quiet_event_rate` | share of blocks *without* a storm report that became an event |
| `median_event_hours` | typical event length (6-hour resolution — too coarse to be useful yet) |
| `repeat_7d_share` | share of events followed by another within 7 days |

---

## Features — the Missouri + Illinois 6-hour model (groups in `ml/data.py`)

These are the 6-hour block features behind the published Missouri + Illinois results. The USA model's inputs are in
[Model inputs — the USA hourly model](#model-inputs--the-usa-hourly-model-e55).

Rule for every feature: **would I know this at the start of the block?**

### `weather` — HRRR storm ingredients for the block

| Feature | Definition | Why it matters |
|---|---|---|
| `gust_max_ms` | max 10 m wind gust, m/s | damaging wind at the surface |
| `wind10_max_ms` | max sustained 10 m wind | — |
| `wind850_max_ms` | max wind at 850 hPa (~1.5 km) | low-level jet; can mix down in storms |
| `shear_0_6km_max_ms` | max \|wind at 500 hPa − wind at 10 m\| | organized, severe storms need shear |
| `cape_max_jkg` | max CAPE, J/kg | energy for updrafts (storm strength) |
| `precip_sum_mm`, `precip_max_1h_mm` | total / heaviest hourly rain | saturated soil + wind topples trees |
| `temp_min_c`, `temp_mean_c` | 2 m temperature | cold + wet = ice |
| `freezing_level_min_m` | lowest freezing level | low + unstable = hail |
| `icing_hours` | hours with temp ≤ 0 °C and precipitation | ice on lines and limbs |
| `hail_hours` | hours with CAPE ≥ 500, rain ≥ 2 mm, freezing level ≤ 3.5 km | crude hail proxy |
| `wind_x_precip`, `wind_squared`, `shear_x_cape` | interactions | wind load grows ~ with speed² |
| `month`, `block_hour_utc` | calendar | seasons, time of day |

**Caveat:** HRRR via Open-Meteo is close to observed weather (each run's first hours), so
this is an upper bound for a 24–48 h forecast.

### `place` — fixed per region

| Feature | Definition |
|---|---|
| `log_customers` | log10 of customers (MCC) |
| `housing_per_km2` | housing units ÷ land area |
| `share_homes_pre1960` | homes built before 1960 ÷ all homes (older area ≈ older trees and lines) |
| `median_year_built` | ACS median year built |
| `canopy_mean_pct` | average tree canopy % (USFS/NLCD 2021) |
| `canopy_dense_share` | share of the region with ≥ 50% canopy |

`canopy` = the two canopy features, used for ablations (`weather+place-canopy`).

### `history` — the region's track record as of each year

`hist_hours_out_per_customer`, `hist_events_per_year`, `hist_storm_hit_rate`,
`hist_quiet_event_rate`, `hist_repeat_7d_share` — the scorecard measures above, but from
`mart_study__region_history_asof`: computed from the **3 years before January 1 of the
row's own year** (a 2024 row sees 2021–2023), joined on region and year. No row's history
contains its own year or later, so history features work on any training years;
`data.check_history` enforces it per row. EAGLE-I recorded fewer events before 2020
(~10/year per region vs ~24 after), so early history values run low. On the 2024
validation year, history did not improve the Missouri + Illinois model (`tune.yaml`), and
that model leaves it out. On the whole country it helps (+2.3%, +16% on held-out counties), and the USA model keeps it
(E55).

### `recent` — outages already known at the block's start

| Feature | Definition |
|---|---|
| `prev_block_pct_out` | `peak_pct_out` of the previous block (`lag`) |
| `max_pct_out_prev_24h` | max `peak_pct_out` over the previous 4 blocks (window `4 PRECEDING AND 1 PRECEDING`) |

Computed on the full grid **before** filtering years, so a year's first block still sees
the previous year.

### `warnings` and `outlook` — official forecasts (`int_study__nws_6h`)

| Feature | Definition |
|---|---|
| `warn_svr`, `warn_tor`, `warn_wind`, `warn_winter` | an NWS severe thunderstorm / tornado / high wind / winter (ice storm, winter storm, blizzard) warning was **in force when the block started** (issued before it, not yet expired); zone warnings spread to every county in the zone |
| `spc_cat` | SPC Day 1 categorical risk at the region's interior point: 0 none, 1 TSTM, 2 MRGL, 3 SLGT, 4 ENH, 5 MDT, 6 HIGH |
| `spc_wind_prob`, `spc_tor_prob`, `spc_hail_prob` | that outlook's probability of the hazard within 25 miles |

The outlook is the latest product issued **before** the block starts and valid at its start
(`spc_lead_hours` > 0, tested). Both are known at the block's start: a warning issued during
the block is ignored, because it usually follows the storm's arrival. Used as features
and as the `nws_warnings`, `spc_outlook` and `official` baselines (`ml/models.py`).

### Label and evaluation columns (added in `ml/data.py`, not in dbt)

| Column | Meaning |
|---|---|
| `y` | `peak_pct_out ≥ threshold` (1, 5 or 10) |
| `is_onset` | previous block known and **below** the threshold → a *new* outage. Rows with an unknown previous block are neither |

---

## How the models are evaluated

### The two validation splits — and why both

A model is only as good as the test that judges it, and there are two different
questions a user of this model would ask. Each split answers one:

| Split | Train on | Test on | Question it answers | Why it's set up this way |
|---|---|---|---|---|
| **time** | all of 2024 | all of 2025 | "Trained on the past, does it work next year?" — how it would be used for real | The only years with HRRR weather downloaded so far. The test year is entirely after the training year, so no storm appears in both. Weakness: one year of storms is a small sample — a quiet or wild 2025 moves the score. More years (2020–2023, downloading) will allow 2020–2023 → 2024–2025 |
| **county**, 5 folds | 80% of the regions (2024 + 2025) | the other 20% | "Does it work for a place it has never seen?" — the honest test for *place* features (canopy, housing age) | Regions are split into 5 groups (~43 each). Each group is held out once while the model trains on the other 4, so **every region gets tested exactly once**, by a model that never saw it — all 216 regions contribute to the score, not just one random 20%. 5 is the usual trade-off: each model still trains on 80% of the data, and 5 fits per run keep it fast. More folds = more training data per fit but slower; fewer = noisier |

They answer different questions, so they can disagree — and that's informative:
place features help more on `county` (they're how the model tells an unseen place apart)
than on `time` (where the model already knows every region from training).

A third split, **random** (5 folds by region-day hash), is included for comparison with random-day evaluations such as weathernext-outage-forecasting. One storm hits
neighboring counties on the same day, so it lands on both sides of the split and scores
come out optimistic. It's in the code to *demonstrate* that, not to choose models.

Predictions from all folds are pooled and scored once, so `county` produces one number,
not five. (There are no confidence intervals yet — a bootstrap over storm days is on the
roadmap; until then, treat differences under ~0.005 PR-AUC as possibly noise.)

### Benchmark configs — what each one compares (`ml/benchmarks/`)

| Config | Question | Runs | What varies | Fixed |
|---|---|---|---|---|
| `quick.yaml` | Which **model family** is best, and do features beyond weather help? | 66 | models: prior, climatology, logistic, LightGBM, XGBoost (one setting each); features: weather → +place+history → +recent; outage size 1/5/10% | trained on all blocks |
| `onsets.yaml` | Should a model of **new outages** be **trained** on new outages only? And does **canopy** help? | 72 | `train_on`: all vs onsets; features incl. `weather+place` vs `weather+place-canopy`; outage size 1/5/10% | LightGBM only (+ climatology baseline) |
| `tune.yaml` | Which **XGBoost settings**, and does **as-of history** help? Chosen on a **validation year** | 49 | grid: trees 400/800, learning rate 0.03/0.06, depth 4/6/8, min child weight 5/20; with and without history | train 2020–2023, validate 2024; 2025 not loaded |
| `final_2025.yaml` | The **reported results**: the validation winner, tested once on 2025 | 36 | features: weather → +place → +history / +recent; outage size 1/5/10% | train 2020–2024, test 2025; county split over 2020–2025 |
| `years_2020.yaml`, `years_2024.yaml` | Does **more training history** help? | 4 each | training years only | test 2025, ≥ 5% |
| `ablations.yaml` | With five years, do **canopy** and **antecedent rain** help? | 12 | `-canopy`, `+wet_soil` vs weather+place+recent; XGBoost; outage size 5/10% | train 2020–2023, validate 2024; county split within 2020–2024 |
| `seeds_tune.yaml` | Is the tuning winner real? The leading settings, **5 seeds each** | 30 | three settings × with/without history × seeds 0–4 | validate 2024 |
| `seeds_ablate.yaml` | Are the canopy and rain effects bigger than **seed noise**? | 60 | `-canopy`, `+wet_soil` vs weather+place+recent × seeds 0–4; outage size 5/10% | validate 2024; county split within 2020–2024 |
| `official.yaml` | Does the model beat, and add to, **NWS warnings and SPC outlooks**? | 54 | baselines: climatology, nws_warnings, spc_outlook, official; XGBoost on official forecasts only, on the model's features, and on both; outage size 1/5/10% | final XGBoost settings |
| `weathernext.yaml` | How does **weathernext-outage-forecasting's setup** score on this data, under its split and under ours? | 9 | splits: random (theirs), county, time; their features, class-weighted boosted tree and logistic regression vs the final model | ≥ 5% |
| `splits.yaml` | How much does the **choice of test set** change the score? | 9 | splits: time, county, random | final XGBoost settings, ≥ 5% |
| `wet_soil.yaml` | Does **rain before the block** help? | 64 | `wet_soil` group on/off, LightGBM and XGBoost, train on all vs onsets; outage size 5/10% | — |
| `full.yaml` | What are the **best hyperparameters**? | 264 | grids: LightGBM (trees, learning rate, leaves, class weight), XGBoost (trees, depth, min child weight, class weight), HGB; plus the canopy ablation; outage size 1/5/10% | trained on all blocks |

All configs use the same data, splits and metrics, and **every run is scored twice**: on all
blocks, and on **new outages** (blocks whose previous 6 hours weren't already an event) —
leaderboards rank by the second. `train_on` is about which rows the model *learns* from;
the onset *score* is computed for every run either way.

Results: `ml/results/benchmark_<config>.csv` (every number) and
`ml/results/leaderboard_<config>.md` (ranked). Metrics are defined in `ml/metrics.py`.

---

## SQL techniques — what we used and where

| Technique | What it does | Where |
|---|---|---|
| `read_csv(..., union_by_name = true)` | stack files whose columns differ, matching by name | `_sources.yml` (EAGLE-I, HRRR, Storm Events) |
| `coalesce(a, b)` | first non-NULL value | 2023's `sum` column; storm counts → 0 |
| `{{ source() }}` / `{{ ref() }}` | dbt: read a raw file / another model; builds the dependency graph | every model |
| macros | reusable SQL snippets | `region_fips`, `block_6h` |
| `time_bucket` / `date_trunc` | round timestamps down | 15-min slots; 6-hour blocks |
| `GROUP BY ALL` + `max`/`sum`/`avg` | aggregate snapshots into blocks | `int_study__outages_6h`, `int_study__weather_6h` |
| `count(*) FILTER (WHERE …)` | conditional counts in one pass | weather hours, storm types, scorecard rates |
| `CROSS JOIN` + `LEFT JOIN` | full grid, then attach what exists (missing → NULL) | `mart_study__region_6h` |
| three-way `CASE` | NULL (unknown) vs 0 (none) vs value | `peak_out` |
| heartbeat | judge coverage from the whole country | `int_eaglei__blocks_6h` |
| `generate_series` + `unnest` | make every block / spread a storm over the blocks it spans | blocks, storm events |
| `UNION ALL BY NAME` | stack county and zone events | `int_study__storm_events_6h` |
| window functions `lag`, `lead`, `max … ROWS BETWEEN` | look at neighboring blocks per region | `recent` features, scorecard |
| gaps-and-islands (`lag` + running `sum` of start flags) | group consecutive event blocks into events | `mart_study__region_resilience` |
| `QUALIFY row_number() … = 1` | keep one row per group (filter on a window) | KSTL duplicate reports |
| `arg_max(x, y)` | the x from the row with the largest y | latest county name (legacy MO/IL build) |
| `regexp_matches` | pattern search in text | thunder in METAR (KSTL) |
| `* EXCLUDE (…)` / `* REPLACE (…)` | select all columns but drop / rewrite some | legacy loads |
| singular dbt tests | a query that returns the *bad* rows | `dbt/tests/*.sql` |

**NULL traps to remember:** `least()` / `greatest()` skip NULLs (`least(100, NULL)` = 100);
`WHERE` runs before window functions (filter after computing lags); `count(col)` skips
NULLs while `count(*)` doesn't.
