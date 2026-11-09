# Smart money structures

`src/core/smc.py` detects the basic smart money concept (SMC) structures on one
ordered bar window, and the dashboard draws them over the daily candlestick
chart (`/api/smc/<key>?months=N`, `src/features/web/smc_view.py`).

The rules and the event shapes are ported from the SMC pattern discovery system
v0.1 reference implementation (`smc/detectors.py`). That reference read a CSV
with pandas and wrote `smc_events.csv`; this project keeps the standard library
only (`OPEN-2`, `CODE-6`), so the frame became the daily bar dictionaries that
`features/web/price_view.py` already produces and the numpy comparisons became
plain Python. The detection rules are unchanged, and the two implementations
give the same events for the same bars.

## Detected structures

| Pattern | Direction | How it is defined here |
| ------- | --------- | ---------------------- |
| `SWING_HIGH` | `bearish_reference` | Bar holding the highest high of `left_bars + right_bars + 1` bars, and the only bar holding it |
| `SWING_LOW` | `bullish_reference` | The same rule on the lows |
| `BOS` | `bullish` / `bearish` | Close beyond the active confirmed swing in the direction of the current trend (or before any trend exists) |
| `CHOCH` | `bullish` / `bearish` | Close beyond the active confirmed swing against the current trend |
| `LIQUIDITY_SWEEP` | `buy_side_taken` / `sell_side_taken` | Wick through a confirmed level with the close back on the other side |
| `ORDER_BLOCK` | `bullish` / `bearish` | Last opposite-colour bar before the structure break (`ob_lookback` bars at most) |
| `FVG` | `bullish` / `bearish` | Classic three-candle gap: third low above the first high, or third high below the first low |

The terms have no single universal definition; these are explicit, adjustable
starting rules, not evidence of an edge. A flat top or bottom (the extreme
repeated inside the window) is never a pivot, so a range does not invent swings.

## Look-ahead

* `pattern_at` is the bar that formed the structure, `detected_at` is the first
  bar whose close made it knowable, and every event carries both.
* A pivot is reported only at its confirming bar (`confirmed_index`), which is
  exactly `right_bars` bars after the pivot.
* Structure breaks and gaps are known at their own close, so their two dates
  match; an order block is known at the break that followed it.
* A caller must use `detected_at`; trading on `pattern_at` would act on
  information the bar did not yet hold.

## Parameters

`src/core/smc_params.py` holds the only copy of the windows:

| Field | Default | Meaning |
| ----- | ------- | ------- |
| `left_bars` | 3 | Bars to the left a pivot must dominate |
| `right_bars` | 3 | Bars to the right a pivot must dominate, and the confirmation delay |
| `ob_lookback` | 12 | How far back the order block search goes before a break |
| `sweep_tolerance` | 0.0 | Extra distance a wick must exceed a level before it counts |

The API reports the parameters it used, so a stored result can always be
reproduced.


## Zone lifetime

An order block and a fair value gap are price zones, so each one also reports
how long it lived (`src/core/smc_zones.py`):

| Field | Meaning |
| ----- | ------- |
| `touched_at` | First later bar that traded back into the zone, or `null` |
| `filled_at` | First later bar that traded through the whole zone, or `null` |
| `is_filled` | `true` when the zone was traded through |
| `end_index` | Last bar the chart may draw the zone over: the fill bar, or the newest bar while the zone is open |

A bullish zone is support below the price (a low entering it is a touch, a low
through it is a fill); a bearish zone is mirrored. Filled zones are drawn
fainter, which is what keeps a year of structures readable.

## The panel and the overlay

The page draws the structures over the candle chart it already builds
(`src/features/web/static/chart_smc.js`):

| Group | Drawn as |
| ----- | -------- |
| Zones (FVG, order block) | Translucent rectangle from the pattern bar to `end_index` |
| Structure breaks (BOS, CHoCH) | Dashed horizontal level from the break bar to the right edge, labelled |
| Sweeps | Small triangle at the wick extreme |
| Swings | Small dot at the pivot |

`smc_panel.js` adds the numbers behind the drawing: the window, the bar count,
one line per group, the parameters, the newest structures with their state, and
four toggles that hide or show a group without refetching anything.

## API

`GET /api/smc/<key>?months=N` answers the usual envelope with:

| Field | Content |
| ----- | ------- |
| `key`, `instrument` | Series of the window |
| `timeframe` | `1d`: the detector runs on the same daily bars the chart draws |
| `months`, `months_requested` | Stored files used, oldest first |
| `parameters` | Windows of this run |
| `bars` | `count`, `first_day`, `last_day` of the window |
| `summary` | Pattern -> direction -> count |
| `events` | Every structure, oldest detection first, with `bar_index` into the same bars `/api/series/<key>` returns for that window |

`months` is clamped to 24 like the price endpoint, `0` means every stored file,
and an unknown key answers 400. The response goes through the same caches as the
price panel, so a second request in the same window costs milliseconds.

## Files

| Path | Responsibility |
| ---- | -------------- |
| `src/core/smc_params.py` | The only copy of the windows |
| `src/core/smc_events.py` | Pattern and direction names, one event row shape |
| `src/core/smc_swings.py` | Confirmed pivots and their confirmation index |
| `src/core/smc_zones.py` | Gaps, order blocks and zone lifetime |
| `src/core/smc.py` | The single oldest-first walk that produces every event |
| `src/features/web/smc_view.py` | Window selection, bar indices, counts, payload |
| `src/features/web/static/chart_smc.js` | Overlay drawing (SVG, no dependency) |
| `src/features/web/static/smc_panel.js` | Summary, toggles and the newest events |
| `src/features/web/static/smc.css` | Overlay and table styles |

Nothing is written to disk: the structures are computed from the stored bars on
every request, so `data_report.py` and the series registry (`FLOW-10`) are not
affected.

## Limits

* One timeframe only: the detector runs on the daily bars of the window, because
  that is what the chart draws. Multi-timeframe matching (4h, 1h from the stored
  minutes) is the next step, and the payload already carries `timeframe`.
* Daily bars are UTC calendar days, so a market session that crosses midnight is
  split and the session break is not treated as a gap. Intraday structures will
  differ from the daily ones.
* No pattern statistics yet: no MFE/MAE, no continuation probability, no
  walk-forward backtest and no transaction costs.
* The rules are the v0.1 definitions; changing them changes every result, which
  is why the parameters travel with the payload.

## Verification

```sh
python -m pytest tests/core/test_smc.py tests/core/test_smc_zones.py \
    tests/core/test_smc_swings.py tests/features/web/test_smc_view.py
python serve_dashboard.py --no-pid --port 8765
curl -s 'http://127.0.0.1:8765/api/smc/xauusd?months=3'
```

A three month window on the stored gold data holds 58 daily bars and answers 29
structures in about 3 ms of detection cost; a full year holds 311 bars and 195
structures. The price is the same file aggregation the price panel pays, and it
is shared through the cache.

