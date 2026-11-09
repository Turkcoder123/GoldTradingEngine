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
| Price history | Daily candlesticks with a volume strip for the selected series, 1M/3M/6M/1Y/All switch, window summary (open, high, low, close, change, bars, days, gaps, minutes without bars) |
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
| `GET /api/series/<key>?months=N` | Daily bars of one series (`xauusd`, `dxy`, ...), `months=0` means the whole history |
| `GET /api/smc/<key>?months=N` | Detected SMC structures of the same window, each with the index of its bar, plus the pattern counts and the parameters used |
| `GET /api/cot?year=YYYY` | Weekly net, open interest, long and short of both reports |
| `GET /api/macro?years=N` | Stored FRED series with the last N years of observations |
| `GET /api/refresh` | Drops the in-process caches; the next request reads the files again |

`months` is clamped to 24, `years` to 20, and an unknown series key answers 400.

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
