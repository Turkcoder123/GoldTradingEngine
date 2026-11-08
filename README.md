# x

Project workspace repository, versioned with git and governed by a written rule set.

## Status

Initialized, with one application that has three parts, all Python 3 and
standard library only: a 1-minute price keeper for the gold complex and the
dollar index, a weekly CFTC COT export, and a FRED macro export. The project
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
| `src/shared/` | Constants, series registry, UTC time helpers, `VERSION` reader. |
| `src/core/` | Domain layer: prices, COT and FRED (feed, storage, refresh, status). |
| `src/features/cli/` | Command line surfaces: parsers, report writers, wiring. |
| `tests/` | Test suite mirroring `src/` (`MOD-9`); run with `python -m pytest`. |
| `docs/` | `data.md`, `cot.md`, `macro.md`: formats, column guides, pitfalls. |

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

## Documentation

| Document | Content |
| -------- | ------- |
| `docs/data.md` | All datasets: paths, schemas, coverage, quality guarantees, how to join them |
| `docs/cot.md` | What the COT report means, column dictionary, how to read it, pitfalls |
| `docs/macro.md` | FRED series registry, units, frequencies and how each one relates to gold |
| `rules.md` | Project rule set: language, versioning, git, modularity, workflow |

## Development

```sh
python -m pytest          # full test suite, no network access
```

No third-party dependency is required or allowed without approval (`CODE-6`).

## Version

The version is stored in the `VERSION` file and is bumped only after the user
decides the new number (`VER-2`, `VER-3`). Released versions are tagged in git
as `vX.Y.Z` and documented in `CHANGELOG.md` (`VER-6`).

Current version:

```sh
cat VERSION
```

## Contributing

Read `rules.md` before writing any code. All files, comments, commit messages,
and branch names are in English; conversation is in Turkish (`LANG-1`, `LANG-2`).

