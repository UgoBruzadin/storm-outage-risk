# The USA site: the app (draft for review)

Branch `site-usa` (worktree `../storm-outage-risk-site`). Nothing here is published or committed. Built overnight
Nov 22–23, 2026, from the brainstorm "start from the live product, not the story".

## What it is

A front door for the public, in `site/usa/`, beside the story deck (`site/index.html`, now "How it was built"):

| Page | What | Data |
|---|---|---|
| `usa/index.html` | **Now.** Search a county or ZIP code; the live map of every county's chance; a county card (chance, range over the five weather runs, level, what's raising it, alert feed); the 10 highest counties; 2025 headline tiles | live `usa/latest.json` (storm-outage-live), `data/counties.json`, `data/map.json`, `data/zip.json`, `data/record.json` |
| `usa/county/<id>.html` | **County pages** (3,089, one per county with an outage record): live card and neighbor map; alert feed link and embed snippet; "what knocks out power here" (7 facts as percentiles); how the alerts would have done there in 2025, each alert and each missed outage | the page's own JSON (built from the template `scripts/usa_county_page.html`) |
| `usa/scorecard.html` | **Scorecard.** Live alerts sent (from `usa/alerts_log.csv`, graded later); 2025 replayed with the live alert rule, per level, vs warnings + outlook at the same alert hours; by month; by state (sortable) | `data/record.json`, live `usa/alerts_log.csv` |
| `usa/replays.html` | **Storm replays.** Five 2025 storms hour by hour: chance fill, counties 5%+ out outlined, warnings hatched (toggle); per storm: new outages, share alerted first, vs warnings + outlook, median warning | `data/replays.json` |
| `usa/outlook.html` | **Outlook.** Counties on alert now, by state; the shareable image link | live `usa/latest.json`, `usa/outlook.svg` |
| `usa/embed.html?county=<id>` | A small card for other sites (iframe) | live |

Until the USA feed runs, every live view falls back to `data/sample_latest.json` and says so in a banner.

## Built by

`scripts/make_usa_site.py` (run from the `usa` checkout's pixi env; reads `data/cache/live_usa/pred_2025.parquet`,
`data/explore/decisions_2025.parquet`, the warehouse (read-only), `live/static_usa/`, storm-outage-live
`alerts/counties.json`, and the Census ZCTA–county file):

```
pixi run python ../storm-outage-risk-site/scripts/make_usa_site.py --zcta tab20_zcta520_county20_natl.txt \
    --outlook ../storm-outage-live/outlook
```

The 2025 numbers are the held-out twin of the live USA model (trained 2020–2024), at the live levels (Elevated 0.10,
High 0.20), counted as `ml/alert_counts.py` counts (one alert per storm: hours above the level 6 or fewer apart are
one alert). Warnings + outlook get the same number of alert hours.

## Changes elsewhere (uncommitted)

- **storm-outage-risk `usa`, `live/usa.py`:** `latest.json` gains `drivers`: for each county at 3% or more, the
  groups adding 0.1 or more to the model's log-odds (XGBoost `pred_contribs` on the newest run's window, summed into
  10 groups: strong gusts, heavy rain, soaked ground, ice or freezing rain, thunderstorms, official warnings, trees,
  past outages here, the local grid, season and place). Tested on 2026-11-23 03Z: 286 s for the whole hour, 12
  counties explained.
- **storm-outage-live:** `alerts/send.py --log` (every alert sent, one CSV row); `outlook/make.py` +
  `outlook/outlook_shapes.json` (the hourly image, standard library only); `hourly-usa.yml` runs both; README
  section for `usa/`.

## Decisions for the user

1. **Front door.** Make `site/usa/` the site's home (and the deck `story/`), or keep the deck at the root and link
   the app from it. The pages link to the deck as `../`; moving it is a few links.
2. **The outlook image needs a public URL that serves SVG as an image.** raw.githubusercontent.com serves it as
   text, so `<img>` won't show it. Turn on GitHub Pages for storm-outage-live (the page assumes
   `https://ugobruzadin.github.io/storm-outage-live/usa/outlook.svg`), or copy it into this site.
3. **Unreliable counties** (17, `hist_quiet_event_rate` > 0.2): the site already leaves them out of the top list and
   the outlook and flags them on their pages and cards; the alerts still go out until `send.py` skips them.
4. **Wording**: every page is new public text. Read before anything ships.
5. **Repo size**: `site/usa/` is 42 MB, 37 MB of it the 3,089 county pages (~12 KB each, mostly each county's
   2025 alert list). Fine for Pages, but it is build output: commit it, or build it in the Pages workflow (needs
   the warehouse, so committing is simpler), or load each county's data from one JSON per state to cut it.
6. **Push notifications**: the card and county page say "coming"; self-hosted ntfy is the plan.

## Findings while building

- **The 17 unreliable counties are the ones where EAGLE-I tracks almost no customers**: Henderson NC 24,
  Jeff Davis TX 44, Terrell TX 70, Presidio TX 131, Brewster TX 222, Alamance NC 925 ... Mecklenburg NC 28,172 (of
  several hundred thousand). A few customers going out reads as 5%+. 44 counties have under 500 tracked customers.
  A cleaner rule than the quiet-event rate may be "tracked customers / ACS households" below some share.
- **Drivers read well.** May 16 2025 21Z (run through the live code): Lyon KY 92%, "strong gusts, official
  warnings, thunderstorms"; Henderson NC on a calm night: "past outages here, the local grid, trees".
- **2025 replay matches `ml/alert_counts.py`**: Elevated 11.5 a county-year, 20% followed by an outage, 28% of
  26,018 outages alerted, median 7 h ahead (warnings + outlook, same alert hours: 13%, 19%, 12 h). In the five
  replay storms 55–76% of new outages had an alert first.
- **The outlook image renders** (checked as PNG); it leaves out the unreliable counties, as the site does.

## Checked

Screenshots (headless Chromium, local server) of every page, light and dark, desktop and 390 px phone: front page
(list and county card), county page (Lyon KY, Henderson NC), scorecard, replays, outlook, embed. Not checked in a
browser: typing in the search box (the ZIP and name lookup were checked on the data), the replay's Play button.
