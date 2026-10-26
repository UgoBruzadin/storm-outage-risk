#!/usr/bin/env bash
# Runs weather downloads one after another (they share Open-Meteo's free daily quota,
# so running them in parallel would only make each slower).
#   nohup scripts/queue_weather.sh 2018 2019 > data/raw/weather/queue.log 2>&1 &
# HRRR on Open-Meteo starts 2018-01-01, so 2018 is the earliest year available.
set -u
cd "$(dirname "$0")/.."
while pgrep -f "ingest/fetch_weather.py" > /dev/null; do sleep 300; done   # let a running download finish
echo "$(date) start: $*"
pixi run fetch-weather "$@"
echo "$(date) done"
