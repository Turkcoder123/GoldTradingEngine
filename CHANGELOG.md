# Changelog

All notable changes to this project are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the
project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
Entries are written in English, from the user's point of view, and every released
version is tagged in git as `vX.Y.Z`.

## [Unreleased]

### Added

- `stream_live.py` plus `src/core/live_*.py`: a temporary XAU/USD live stream
  from Twelve Data. Ticks are aggregated into 1-minute bars in memory, a bar is
  printed as soon as the next minute starts, and nothing is appended to the
  stored CSV history: Dukascopy stays the authoritative source. A tick at or
  before the newest stored minute is refused, and every live bar the keeper
  later covers is dropped from the buffer.
- `src/shared/envfile.py` and `.env.example`: a minimal `.env` reader, so the
  provider key comes from the process environment or a local `.env` file. The
  environment always wins and `.env` stays out of git (`GIT-6`).
- `docs/live.md`: setup, the WebSocket protocol, the data precedence rules and
  the limits of the live layer.
- `OPEN-6` records the approved `websocket-client` dependency: the live feed is
  its only user and it is imported lazily, so every other command and the whole
  test suite keep running with the standard library only.

## [1.5.0] - 2026-11-09

### Added

- Smart money structures over the price chart: `src/core/smc*.py` detects
  confirmed swing highs and lows, BOS and CHoCH, liquidity sweeps, order blocks
  and fair value gaps on the stored bars, ported from the SMC pattern discovery
  system v0.1 reference implementation to the standard library, so the pandas
  dependency of the reference is not needed. Every structure reports
  `pattern_at` and `detected_at`, so a pivot is never read before the bars to its
  right had closed, and every zone reports where it was touched and filled.
- `GET /api/smc/<key>?months=N`: the structures of one price window, each with
  the index of its bar, plus the pattern counts and the parameters used.
- The dashboard draws them over the daily candles (translucent zones, dashed
  levels, sweep and swing markers) and adds a panel with the window summary, four
  group toggles and the newest structures.
- `docs/smc.md`: the rules, the look-ahead guarantee, the zone lifetime, the
  overlay, the API and the limits of the detection.

### Changed

- `src/features/web/static/app.js` keeps only the data flow: the element handles
  and the shell labels moved to `static/layout.js`, so both files stay under the
  `MOD-2` soft limit.

## [1.4.0] - 2026-11-08

### Added

- `update_rates.py` plus `src/core/rates.py`: real interest rates derived from
  the stored FRED series (`long term government yield - CPI inflation`, joined
  on the month) for five countries (US, DE, FR, IT, GB), stored as
  `rates/real_<cc>.csv` with an equal weighted world median, and shown in the
  macro panel and the text report. Inflation is computed from the CPI index
  series because the OECD growth series are no longer updated, and a series
  older than six months is marked `STALE` instead of pretending to be current.
  Japan and Turkey are not registered: FRED has no current Japan CPI and no
  long term rate for Turkey.
- `docs/rates.md`: the formula, the country registry, the output shape and the
  limits of the derived measure.

## [1.3.0] - 2026-11-08

### Added

- `data_report.py` writes a plain text inventory of everything stored: per price
  series the resolution, covered range, row and file counts, size, last close and
  the two changes, both stored COT reports, and every macro series with its unit,
  frequency, coverage and last value. `--output -` prints it instead of writing
  `<data dir>/data_report.txt`.
- A rule (`FLOW-10`) that a new data type is one change: registry, documentation
  and a fresh report run move together, and the tests that compare the guides
  with the registry fail when they drift apart.
- `update_alt.py` plus `src/core/{etf,gvz,fedtext}*.py`: three alternative data
  types stored under `<data dir>/alt/`, fetched with the standard library only.
- Gold ETF holdings: the official SPDR archive (XLSX, close, volume, ounces,
  tonnes and NAV since 2004-11-18) for GLD and the iShares tonnage snapshot for
  IAU, merged by date into `etf_<fund>_daily.csv`.
- The Cboe gold volatility index (GVZ) from the official Cboe CSV, stored as
  `gvz_daily.csv` from 2009-09-18 onwards.
- Federal Reserve speeches, FOMC statements and minutes from the two Board RSS
  feeds, with the body text of every new document stored in `alt/fed_text/` and
  indexed in `fed_documents.csv` (`--limit` caps a run).
- `--status`, `--json`, `--quiet` and `--source`/`--etf` options on the new
  command, and the alternative sources in `python data_report.py` (ETF tonnage,
  GVZ and the stored document counts).
- `docs/alternative.md`: sources, columns, the endpoints that were tested and
  rejected (CME warehouse stocks, IMF IFS, WGC downloads, Yahoo) and the
  licensing notes.
- The dashboard still runs from the registry, and a new data type reaches the
  inventory report without code changes (`FLOW-10`).
- The alternative sources also reach the dashboard: the overview payload carries
  the ETF tonnage windows, the GVZ window and the newest documents, and the page
  draws them in a new panel with a table that links to each document.

### Changed

- The facts of the alternative sources moved to `src/core/altstatus.py`, so the
  text report and the dashboard describe them from one place instead of two
  copies.
- The page runtime (labels, fetch, status line) lives in `static/runtime.js`, so
  the dashboard script stays within the file size limit (`MOD-2`).

### Fixed

- A stored series whose newest row holds no value (for example an IAU row with a
  price but no tonnage) no longer reports "no value": the latest readable row is
  used for the summary and the dashboard.

## [1.2.0] - 2026-11-08

### Added

- Local web dashboard: `serve_dashboard.py` plus `src/features/web/` serve the
  stored price, COT and macro data as one read-only page, with the standard
  library HTTP server and hand-written SVG charts (no third-party dependency).
- The page shows totals, one card per price series with the latest close and the
  stored range, daily candlesticks with a volume strip for a selectable series
  and 1M/3M/6M/1Y/All window, both stored COT reports as summary and grouped
  weekly bars, and one sparkline card per FRED series with a detail chart.
- JSON endpoints `/api/overview`, `/api/series/<key>`, `/api/cot`, `/api/macro`
  and `/api/refresh` expose the same aggregates to scripts.
- Daily aggregation of the monthly files in one pass, including the minute-gap
  counts the `--status` report uses, with two in-process caches so a page load
  never re-reads a year of minute bars.
- Every user-facing text of the page lives in `src/features/web/locale.py` and
  reaches the browser as JSON (`LANG-4`).
- Test suite for the dashboard under `tests/features/web/`, including a real
  HTTP server on an ephemeral port; it runs offline.
- A PID file per address (`<data dir>/dashboard-<port>.pid`) with `--pid-file`
  and `--no-pid`: a second start on the same port is refused with the pid and
  the URL of the running instance instead of a raw socket error.
- Ctrl-C and `kill` (SIGTERM) clear the PID file and stop with exit code 130; a
  killed run leaves a stale record whose lock is gone, so the next start simply
  overwrites it.
- `docs/web.md`: what the page shows, its API, how the aggregates are built and
  what the dashboard deliberately does not do.

## [1.1.0] - 2026-11-08

### Added

- XAU/USD 1-minute data keeper, laid out as a package under `src/`: `shared`
  (configuration, UTC helpers, version reader), `core` (feed client, CSV write,
  CSV read, lock, refresh, status) and `features/cli` (parser, report, wiring).
- `update_1m.py` entry point exposing `--status`, `--json`, `--quiet`, `--loop`,
  `--interval`, `--since`, `--segments`, `--segment-hours`,
  `--empty-allowance-hours`, `--timeout`, `--offer-side`, `--data-dir`,
  `--lock-dir`, `--no-lock` and `--version` (`VER-8`).
- Test suite under `tests/`, mirroring `src/` (`MOD-9`); it runs offline.
- `update_cot.py` plus `src/core/cot.py`: the yearly CFTC Commitments of Traders
  archives are downloaded (the site blocks the default user agent) and the COMEX
  gold rows are stored as `cot_legacy_gold_YYYY.csv` and
  `cot_disagg_gold_YYYY.csv` under `<data dir>/cot/`, with a computed `net`
  column and a loud failure when a mapped CFTC column disappears.
- Every COT run and `--status` print the three numbers that make the report
  readable: net position, its share of open interest, and the one-week and
  six-week change (`src/core/cot.py:CotSummary`).
- `docs/data.md` and `docs/cot.md`: data inventory with schemas and quality
  guarantees, plus a plain-language guide to the COT report.
- FRED macro data: `update_fred.py` plus `src/core/fred.py` and
  `src/core/fred_feed.py` store ten keyless macro series (`DFII10`, `DGS10`,
  `DGS2`, `T10Y2Y`, `T10YIE`, `DTWEXBGS`, `WALCL`, `CPIAUCSL`, `FEDFUNDS`,
  `VIXCLS`) as `date,value` CSV under `<data dir>/fred/`, with `--status`
  reporting the latest value and the short and yearly change.
- `docs/macro.md`: the macro registry, its units and how each series relates to
  gold.
- FRED API key support: with `$FRED_API_KEY` or `secrets/fred_api_key` the
  official JSON API is used, otherwise the keyless CSV endpoint. The key stays
  out of git (`.gitignore` covers `secrets/`) and is redacted from error text.
- Second 1-minute series: the US Dollar Index (`--series dxy`, Dukascopy symbol
  `DOLLAR.IDX/USD`) is stored next to gold as `dxy_1m_YYYY-MM.csv`. Series are
  registered in `config.SERIES`, each with its own instrument and file prefix.
- The gold complex as further series, all verified against the live feed:
  silver (`xagusd`, `XAG/USD`) and gold quoted in euro, sterling, francs,
  Australian dollars and yen (`xaueur`, `xaugbp`, `xauchf`, `xauaud`, `xaujpy`).
  Platinum, palladium and gold miner/ETF contracts are not available from this
  endpoint and are therefore not registered.
- A series whose symbol returns no quotes (`[null]` from the feed) now fails with
  a clear message instead of writing empty rows.
- Gap report in `--status`: number of holes and minutes without bars in the newest
  stored month (market closures are counted, so a non-zero value is expected).

### Changed

- The single-file script is now a package: every module stays below the
  `MOD-2` size limit and carries one responsibility (`MOD-1`).
- Ask prices are stored in their own `xauusd_1m_ask_YYYY-MM.csv` files, so bid
  and ask series can never be mixed.
- The single-instance lock moved into the data directory and is ignored by git
  (`GIT-6`, `FLOW-9`).
- `README.md` documents the data format, the commands and the layer boundaries.
- A catch-up segment now takes one request instead of two: the page size follows
  the window and a covered window is not requested again, so a year of history
  needs roughly fifty requests instead of a hundred.

### Fixed

- A run no longer writes bars beyond an unexplained stretch of empty segments;
  such a run stops and reports the pending minutes, so a feed failure cannot
  leave a hole that later runs could no longer fill.
- A repeated minute inside one batch can no longer be written twice.
- `--status` and the run summary report the last bar actually stored instead of
  the internal cursor position.
- Failure output always shows a pending-minute count instead of `None`.
- An unterminated last line left by a killed process is repaired before the next
  row is appended.
- JSONP responses are unwrapped whether or not they carry the expected callback
  name or trailing whitespace.

## [1.0.1] - 2026-11-08

### Added

- Project rule set in `rules.md`: language policy, versioning, git conventions,
  modularity limits, coding conventions, agent workflow, and open decisions.
- `VERSION` file as the single source of truth for the project version.
- Repository scaffolding: `README.md`, `CHANGELOG.md`, and `.gitignore`.
- Git repository initialization on branch `main`.

<!-- Comparison links are added once a remote repository URL is configured. -->
