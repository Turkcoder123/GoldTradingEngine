# x

Project workspace repository, versioned with git and governed by a written rule set.

## Status

Initialized, with one application that has seven parts, all Python 3 and
standard library only: a 1-minute price keeper for the gold complex and the
dollar index, a weekly CFTC COT export, a FRED macro export, the alternative
context sources (ETF gold, GVZ, Fed documents), the derived real interest
rates, a text inventory of everything stored, and a local web dashboard that
shows the data. The project
version lives in the `VERSION` file (see `VER-3` in `rules.md`).

## Repository layout

| Path | Purpose |
| --------------- | ------------------------------------------------------------------------ |
| `rules.md` | Project rule set. Single source of truth for conventions and decisions. |
| `VERSION` | Single source of truth for the project version (`VER-3`). |
| `CHANGELOG.md` | Release history in Keep a Changelog format (`VER-6`, `VER-7`). |
| `.gitignore` | Ignored files and folders (`GIT-6`). |
| `update_1m.py` | Entry point of the 1-minute keeper (`--help` lists every option). |
| `update_cot.py` | Entry point of the CFTC COT export (weekly gold positioning). |
| `update_fred.py` | Entry point of the FRED macro export. |
| `update_alt.py` | Entry point of the alternative sources (ETF gold, GVZ, Fed documents). |
| `update_rates.py` | Entry point of the derived real interest rates (per country). |
| `serve_dashboard.py` | Entry point of the local web dashboard (read-only). |
| `stream_live.py` | Entry point of the temporary live layer (memory only). |
| `data_report.py` | Entry point of the text data inventory (`data_report.txt`). |
| `src/shared/` | Constants, series registry, UTC time helpers, `VERSION` reader. |
| `src/core/` | Domain layer: prices, COT, FRED, ETF gold, GVZ, Fed documents, SMC structures. |
| `src/features/cli/` | Command line surfaces: parsers, report writers, wiring. |
| `src/features/web/` | Dashboard: payload builders, HTTP server, labels, static assets. |
| `src/features/report/` | Plain text inventory of everything stored (`data_report.txt`). |
| `tests/` | Test suite mirroring `src/` (`MOD-9`); run with `python -m pytest`. |
| `docs/` | `data.md`, `cot.md`, `macro.md`, `alternative.md`, `rates.md`, `smc.md`, `web.md`, `live.md`. |

Dependency direction is one way (`MOD-6`): `features` uses `core`, `core` uses
`shared`, and `shared` imports nothing from the other two layers.

## Data keeper

`update_1m.py` keeps one CSV per calendar month of Dukascopy 1-minute bars:

```
<data dir>/xauusd_1m_YYYY-MM.csv          # gold, bid prices (default series)
<data dir>/dxy_1m_YYYY-MM.csv             # US Dollar Index, bid prices
timestamp,open,high,low,close,volume
2026-11-06 21:59:00,4069.79,4071.357,4069.375,4069.545,0.02946
```

Series (`--series`), all stored in the same CSV format and time frame:

| Key | Dukascopy instrument | What it is | Files |
| --- | -------------------- | ---------- | ----- |
| `xauusd` (default) | `XAU/USD` | spot gold | `xauusd_1m_*.csv` |
| `xagusd` | `XAG/USD` | spot silver (the gold/silver ratio) | `xagusd_1m_*.csv` |
| `xaueur` | `XAU/EUR` | gold in euro | `xaueur_1m_*.csv` |
| `xaugbp` | `XAU/GBP` | gold in sterling | `xaugbp_1m_*.csv` |
| `xauchf` | `XAU/CHF` | gold in francs | `xauchf_1m_*.csv` |
| `xauaud` | `XAU/AUD` | gold in Australian dollars | `xauaud_1m_*.csv` |
| `xaujpy` | `XAU/JPY` | gold in yen | `xaujpy_1m_*.csv` |
| `dxy` | `DOLLAR.IDX/USD` | US Dollar Index | `dxy_1m_*.csv` |
| `eurusd` | `EUR/USD` | euro in dollars | `eurusd_1m_*.csv` |

Not offered by the Dukascopy chart service: platinum, palladium, gold miner and
gold ETF contracts (they answer with null prices, which the keeper rejects).

* `timestamp` is UTC, formatted `YYYY-MM-DD HH:MM:SS`, one header line per file,
  CRLF line endings, strictly increasing minutes.
* `--offer-side A` stores ask prices in separate `*_ask_YYYY-MM.csv` files, so
  two price series are never mixed.
* Only missing minutes are appended: stored rows are never rewritten, and a
  minute that is already present is skipped, so a retry cannot duplicate a bar.
* A run stops instead of writing beyond an unexplained stretch of empty bars
  (`--empty-allowance-hours`, default 72) so a feed failure cannot leave a hole
  that later runs could no longer fill.

Usage:

```sh
python update_1m.py                        # fill the gap once
python update_1m.py --loop                 # keep it current every 15 minutes
python update_1m.py --status               # freshness report, no network
python update_1m.py --since 2020-01-01     # bootstrap when there is no data
python update_1m.py --data-dir /sdcard/gold
python update_1m.py --version              # the same value as VERSION (VER-8)
```

Bootstrap a long history quickly (one week per request, roughly fifty requests
for a full year) instead of forty runs of the default eight days:

```sh
python update_1m.py --since 2025-11-08 --segment-hours 168 --segments 60
```

Cron alternative without a long running process:

```sh
*/15 * * * * cd /path/to/repo && python update_1m.py --quiet
```

The data directory defaults to `$XAUUSD_DATA_DIR` or `<project>/xauusd_data`,
which is ignored by git. The single-instance lock lives in the data directory
unless `$XAUUSD_LOCK_DIR` or `--lock-dir` says otherwise.

## COT export (CFTC, weekly)

`update_cot.py` downloads the yearly Commitments of Traders archives and keeps
the COMEX gold positioning as CSV under `<data dir>/cot/`:

```sh
python update_cot.py                # current year, COMEX gold only
python update_cot.py --year 2025    # an older archive
python update_cot.py --all-gold     # every market whose name contains GOLD
python update_cot.py --json         # machine-readable result
```

Files: `cot_legacy_gold_YYYY.csv` (non-commercial long/short, spreading, open
interest, trader counts) and `cot_disagg_gold_YYYY.csv` (managed money,
producer/merchant, swap dealer). Both are sorted oldest report first and carry a
`net` column (long minus short). The report is measured on Tuesday and published
on Friday, so align it with price data by the publication day.

```sh
python update_cot.py --status       # summarize what is stored, no network
python update_cot.py --status --json
```

Keep it current with cron (the report is published on Friday):

```sh
0 16 * * 5 cd /path/to/repo && python update_cot.py --quiet
```

Each run prints one line per report with the numbers that matter:

```
 +2026 COT gold: cot_disagg_gold_2026.csv (44 rows), cot_legacy_gold_2026.csv (44 rows)
   disagg   2026-11-03 | OI 399,169 | net +103,614 (26.0% of OI) | week -1,948 | 6w -23,775
   legacy   2026-11-03 | OI 399,169 | net +179,548 (45.0% of OI) | week -6,903 | 6w -46,305
```

## Macro export (FRED)

`update_fred.py` downloads keyless FRED series (real yields, Treasury curve,
breakevens, dollar index, Fed balance sheet, CPI, fed funds, VIX) and keeps them
as `date,value` CSV under `<data dir>/fred/`:

```sh
python update_fred.py                    # the registered series
python update_fred.py --series DGS10,DFII10
python update_fred.py --status           # latest value + short and 1y change
```

No API key is required and none is stored. See `docs/macro.md`.

## Dashboard (local web page)

`serve_dashboard.py` serves the stored data as one local page: totals and a card
per price series, daily candlesticks with a volume strip, the weekly COT net
position, one sparkline card per macro series, and an alternative sources panel
(ETF tonnage, GVZ and the newest Fed documents). Read-only, standard library
only, no external chart library and no build step:

```sh
python serve_dashboard.py                 # http://127.0.0.1:8765/
python serve_dashboard.py --port 9000 --ttl 30
```

A PID file in the data directory (`dashboard-<port>.pid`) refuses a second start
on the same address with the pid and the URL of the running instance;
`--pid-file` moves it and `--no-pid` skips the check. Ctrl-C and `kill` clear it,
and a killed run never blocks the next start.

The JSON behind the page is available on the same server
(`/api/overview`, `/api/series/xauusd?months=3`, `/api/smc/xauusd?months=3`,
`/api/cot`, `/api/macro`), so a script can read the aggregates without parsing
minute bars. See `docs/web.md`.

## Smart money structures

`src/core/smc.py` detects the basic smart money concept structures on the stored
bars: confirmed swing highs and lows, BOS and CHoCH, liquidity sweeps, order
blocks and fair value gaps. The page draws them over the daily candle chart as
translucent zones, dashed levels and markers, and a panel below adds the counts,
the parameters and the newest structures with four group toggles.

```sh
python serve_dashboard.py                        # the panel is part of the page
curl -s 'http://127.0.0.1:8765/api/smc/xauusd?months=3'   # the same data as JSON
```

Every structure carries `pattern_at` (the bar that formed it) and `detected_at`
(the first bar whose close made it knowable), so nothing is read before it was
known, and every zone reports where it was touched and filled. The rules are
ported from the SMC pattern discovery system v0.1 to the standard library, so no
dependency is added. See `docs/smc.md`.

## Data report (text inventory)

`data_report.py` writes one plain text file with what is stored right now: per
price series the resolution, the covered range, the row and file counts, the
size, the last close and the two changes, plus both stored COT reports and every
macro series with its unit, frequency, coverage and last value.

```sh
python data_report.py                    # <data dir>/data_report.txt
python data_report.py --output -         # print it instead
python data_report.py --output report.txt --quiet
```

Adding a data type is one change that also updates its inventory (`FLOW-10`):
the registry, the guides and this report move together, and the dashboard picks
the new type up without code changes. See `docs/data.md`.

## Alternative sources (ETF gold, GVZ, Fed documents)

`update_alt.py` adds three context sources, all fetched with the standard library
only: the physical gold held by the GLD and IAU ETFs, the Cboe gold volatility
index and the Federal Reserve speeches and FOMC documents.

```sh
python update_alt.py                    # all three sources
python update_alt.py --source etf --etf gld
python update_alt.py --status --json
```

* GLD: the official SPDR archive (XLSX) with close, volume, ounces, tonnes and
  NAV since 2004-11-18; IAU: the tonnage snapshot of the iShares product page.
* GVZ: the Cboe history CSV, 2009-09-18 onwards.
* Fed: both Board RSS feeds, with the text of every new document stored next to
  the index (`alt/fed_text/`), ready for a keyword or sentiment pass.

Sources, columns, the endpoints that were tested and rejected (CME warehouse
stocks, IMF IFS, WGC downloads, Yahoo) and the licensing notes are in
`docs/alternative.md`.

## Real interest rates

`update_rates.py` derives an ex-post real rate per country,
`long term government yield - consumer price inflation`, from the FRED series the
project already downloads, and stores one `real_<cc>.csv` per country:

```sh
python update_rates.py                 # five countries, monthly
python update_rates.py --country US,DE --status --json
python update_rates.py --offline       # rebuild from the stored series only
```

The page shows the per-country rates and the equal weighted median next to the
macro panel, and `python data_report.py` prints the same table. A series older
than six months is marked `STALE` instead of pretending to be current. The
formula, the series ids and the limits are in `docs/rates.md`.

## Temporary live layer (SiftingIO, plus the polled dollar index)

`stream_live.py` keeps a live window of XAU/USD, EUR/USD and the dollar index in
memory and prints every bar that closes. Gold and EUR/USD come from the
SiftingIO WebSocket (bid/ask ticks, about a hundred milliseconds apart); the
dollar index has no tick provider, so its 1-minute bars are polled from the
Dukascopy feed once a minute. It is an overlay only: the keeper stays the
authority, nothing is appended to the stored CSVs, and every live bar the
keeper later covers is dropped from the buffer.

```sh
cp .env.example .env        # fill in SIFTING_API_KEY, keep it out of git
python stream_live.py                       # all three series
python stream_live.py --series dxy           # no API key needed
python stream_live.py --json --seconds 120
```

The layer needs the one approved third-party dependency
(`python -m pip install websocket-client`, `OPEN-6`), imported lazily so every
other command and the whole test suite stay standard library only. One SiftingIO
socket carries both streamed symbols (free tier: 1 connection, 5 subscriptions).
See `docs/live.md` for the protocol, the precedence rules and the limits.

## Documentation

| Document | Content |
| -------- | ------- |
| `docs/data.md` | All datasets: paths, schemas, coverage, quality guarantees, how to join them |
| `docs/cot.md` | What the COT report means, column dictionary, how to read it, pitfalls |
| `docs/macro.md` | FRED series registry, units, frequencies and how each one relates to gold |
| `docs/alternative.md` | ETF gold holdings, GVZ and Fed documents: sources, columns, rejected endpoints |
| `docs/rates.md` | Real interest rates: formula, country registry, limits |
| `docs/smc.md` | Smart money structures: rules, look-ahead, zones, overlay, API, limits |
| `docs/web.md` | Dashboard: what it shows, its API, how the aggregates are built |
| `docs/live.md` | Temporary live layer: SiftingIO protocol, DXY poll, precedence, limits |
| `rules.md` | Project rule set: language, versioning, git, modularity, workflow |

## Development

```sh
python -m pytest          # full test suite, no network access
```

No third-party dependency is required or allowed without approval (`CODE-6`).
The single exception is `websocket-client` for the optional live layer
(`OPEN-6`); it is imported lazily, so the tests and every other entry point run
without it.

## Version

The version is stored in the `VERSION` file and is bumped only after the user
decides the new number (`VER-2`, `VER-3`). Released versions are tagged in git
as `vX.Y.Z` and documented in `CHANGELOG.md` (`VER-6`).

Current version:

```sh
cat VERSION
```

## License

The project is released under GPL-3.0; the license text is the `LICENSE` file
at the repository root (`OPEN-5` in `rules.md`).

## Contributing

Read `rules.md` before writing any code. All files, comments, commit messages,
and branch names are in English; conversation is in Turkish (`LANG-1`, `LANG-2`).

