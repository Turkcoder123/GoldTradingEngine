# Dashboard

`serve_dashboard.py` shows what the three updaters stored: the 1-minute price
history, the weekly CFTC positioning and the FRED macro series. It is a local,
read-only web page served by the standard library `http.server` (OPEN-2), so
there is no build step, no package manager and no third-party chart library.

```sh
python serve_dashboard.py                      # http://127.0.0.1:8765/
python serve_dashboard.py --port 9000          # another port
python serve_dashboard.py --data-dir /path     # another data directory
python serve_dashboard.py --ttl 30             # shorter response cache
python serve_dashboard.py --pid-file /tmp/d.pid # another PID file
python serve_dashboard.py --no-pid             # no PID file, no check
python serve_dashboard.py --version
```

Stop it with Ctrl-C. Apart from its PID file, nothing is written: the page only
reads the CSV files under the data directory, so it can run next to
`update_1m.py --loop`.

## Running it twice

A PID file keeps a second start from happening by accident:
`<data dir>/dashboard-<port>.pid` (`--pid-file` picks another path, `--no-pid`
skips both the file and the check). The record holds the pid, the host, the
port, the URL, the start time and the project version, and the file is *also*
locked with `flock` (`core/lock.py`), so the operating system releases it even
when the process dies without cleaning up.

| Situation | Behaviour |
| --------- | --------- |
| Start on an address that already runs a dashboard | Refused, exit code 1, message with the pid and the URL of the running instance |
| Start on another port or another data directory | Allowed: each address has its own PID file |
| Port taken by a different program | Refused with the socket error; no PID file is left behind |
| Ctrl-C or `kill` (SIGTERM) | Server closes, PID file is cleared, exit code 130 |
| Crash or `kill -9` | The stale record stays, but its lock is gone, so the next start overwrites it |

The check never kills or restarts anything by itself: it reports who holds the
address and lets the operator decide.

## What the page shows

| Section | Content |
| ------- | ------- |
| Overview | Totals (series, files, stored size, coverage, newest bar) and one card per price series: last close, day change, files, size, stored range |
| Price history | Price chart with a **timeframe row** (1m, 5m, 15m, 30m, 1h, 4h, 1D) and a **range row** (1D, 1W, 1M, 3M, 1Y, All; **All is the default**, so the chart opens on every stored bar), candlesticks with a volume strip, the window summary (open, high, low, close, change, bars, gaps, minutes without bars) and the live overlay of the running stream (`docs/live.md`) |
| Smart money structures | Swings, BOS/CHoCH, liquidity sweeps, order blocks and fair value gaps of the same window, drawn over the candles (zones, dashed levels, markers) with a summary, four group toggles and the newest structures (`docs/smc.md`) |
| COT positioning | Both stored reports side by side (net position, share of open interest, weekly change, open interest, long and short) and the weekly net as grouped bars |
| Macro series | One sparkline card per FRED series (latest value, change, observation count) and a detail line chart for the selected series |
| Alternative sources | ETF tonnage (GLD and IAU), the Cboe gold volatility index and the newest Federal Reserve documents, with a table that links to each document |

Hovering a chart shows the values behind the point; the ranges and cards are
buttons, so a series can be inspected without leaving the page.

## API

Every endpoint answers `{"ok": true, "section": ..., "version": ...,
"generated_at": ..., "data": {...}}`, or `{"ok": false, "error": "..."}` when a
request cannot be built.

| Endpoint | Data |
| -------- | ---- |
| `GET /api/overview` | Series cards, totals, COT summaries, macro summaries and the alternative sources (ETF tonnage windows, GVZ, newest documents) |
| `GET /api/series/<key>?interval=I&days=N` | OHLC bars of one series: timeframe `I` (1m, 5m, 15m, 30m, 1h, 4h, 1d) and the newest `N` days (`0` means everything stored; the legacy `months=N` still works) |
| `GET /api/smc/<key>?months=N` | Detected SMC structures of the same window, each with the index of its bar, plus the pattern counts and the parameters used |
| `GET /api/cot?year=YYYY` | Weekly net, open interest, long and short of both reports |
| `GET /api/macro?years=N` | Stored FRED series with the last N years of observations |
| `GET /api/live` | Live overlay: the newest published 1-minute bars per series, the age of the document and whether it is stale |
| `GET /api/refresh` | Drops the in-process caches; the next request reads the files again |

`months` is clamped to 24, `days` to 3650, `years` to 20, and an unknown series
key or timeframe answers 400.

## Timeframes and windows

The chart reads the same stored 1-minute files at six intraday resolutions plus
the daily one, so nothing is re-downloaded and nothing is persisted twice:

| Timeframe | Bars per response (cap) | Typical window with All |
| --------- | ----------------------- | ----------------------- |
| `1m` | 1,500 | the newest 25 hours |
| `5m` / `15m` / `30m` | 1,500 | between five days and a month |
| `1h` | 2,000 | about two and a half months |
| `4h` | 2,000 | the whole stored year |
| `1d` | 3,000 | the whole stored history |

* The page opens on **1D + All**, so the first chart shows every stored bar
  (a year of history becomes about 315 candles).
* A response never exceeds the cap of its timeframe; the body carries
  `bars_total` and `truncated`, and the line under the chart says when the
  window had to be cut (`window cut to the newest bars`).
* Only the monthly files that can hold the requested span are read, so a `1m`
  chart does not re-aggregate the whole year.
* The time axis prints the time of day for intraday bars and the date for daily
  bars; the live overlay merges into the bucket of the selected timeframe.
* The SMC overlay is a daily structure set, so it is drawn only on the `1d`
  timeframe and left out of the intraday views.

## How the numbers are built

* A monthly file is aggregated in one pass into daily OHLC bars: the first open
  and the last close of the day, the highest high, the lowest low, the summed
  volume and the number of stored minutes (`src/features/web/price_view.py`).
  One year of minute bars is never sent to the browser.
* The structure overlay runs on exactly those daily bars (`core/smc.py`: about
  3 ms for a quarter and 20 ms for a year), so every zone and level sits on the
  candle it was detected on; a repeated request of the same window is answered
  from the response cache like any other section.
* The gap counts use the same rules as `update_1m.py --status`, so market
  closures are counted there too: a non-zero value is expected.
* The overview cards only read the file list and the tail of the newest file
  (`quotes.py`), which keeps the first page load to a couple of seconds.
* Aggregation costs about a third of a second per monthly file on a phone, so
  the server keeps two caches: one file aggregate per (path, size, mtime) and one
  built response per endpoint for `--ttl` seconds (default 120). The Refresh
  button clears both.
* The alternative sources read their stored CSVs (a few hundred kilobytes) and
  send only the windows the page draws: one year of ETF tonnage, two years of
  GVZ and the ten newest documents, so the payload stays around 20 KB.

## Live overlay and the chart frame

`GET /api/live` returns the buffers the live layer publishes
(`docs/live.md`, `<data dir>/live/last.json`), and the price chart merges the
newest live minutes of the selected series into one partial bar:

* the partial bar is drawn hollow, dashed and amber, and its volume strip is
  faded, so a live day never looks like a stored one;
* the tooltip of that bar carries a `LIVE` row, and a pulsing badge above the
  chart names the last live price, its minute and the number of buffered
  minutes;
* the badge turns grey (`live stream idle`) when the published document is
  older than ten minutes, and disappears when there is none;
* the page polls the endpoint every twenty seconds while the tab is visible, so
  the overlay follows the stream without reloading the page.

The chart itself is still hand-written SVG with no dependency: horizontal grid
lines with a right-hand price axis, five day ticks on the time axis, a dashed
last-price line with a price tag, and a two-axis crosshair (vertical guide on the
bar, horizontal guide plus a price tag) that drives the hover tooltip. SMC
zones and levels sit under the candles and above the grid, so the overlay never
hides a structure's fill state.

## Limits worth knowing

* Read-only: the dashboard cannot start an update. Use `update_1m.py`,
  `update_cot.py` and `update_fred.py` for that.
* No authentication: it listens on `127.0.0.1` by default, so only this machine
  can reach it. `--host 0.0.0.0` exposes it to the network, which is a decision
  the operator makes.
* The charts are hand-written SVG (`src/features/web/static/chart_*.js`), which
  keeps the page dependency-free but limits it to lines, candles and bars.
* All user-facing text lives in `src/features/web/locale.py` (LANG-4); the HTML
  shell carries placeholders only, and the labels reach the page as JSON.
