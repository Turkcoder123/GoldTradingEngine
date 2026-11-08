# Changelog

All notable changes to this project are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the
project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
Entries are written in English, from the user's point of view, and every released
version is tagged in git as `vX.Y.Z`.

## [Unreleased]

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
