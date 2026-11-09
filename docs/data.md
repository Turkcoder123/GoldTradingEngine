# Data

Three datasets live in this project. All are produced by scripts in this
repository, all are stored under the data directory, and none of them is
committed to git (`.gitignore` covers `xauusd_data/`).

## Inventory

| Dataset | Files | Coverage | Size | Update command |
| ------- | ----- | -------- | ---- | -------------- |
| XAU/USD 1-minute bars | `xauusd_data/xauusd_1m_YYYY-MM.csv` | 2025-11-09 -> 2026-11-06, 353,003 bars | 22 MB | `python update_1m.py` |
| Gold complex, 6 more series | `xauusd_data/<key>_1m_YYYY-MM.csv` | same window, ~352,000 bars each | ~21 MB each | `python update_1m.py --series <key>` |
| DXY 1-minute bars | `xauusd_data/dxy_1m_YYYY-MM.csv` | 2025-11-10 -> 2026-11-06, 314,886 bars | 17 MB | `python update_1m.py --series dxy` |
| CFTC COT, gold | `xauusd_data/cot/cot_*_gold_YYYY.csv` | 44 weekly reports of the current year | ~8 KB | `python update_cot.py` |
| FRED macro series | `xauusd_data/fred/<SERIES>.csv` | full history per series (1962 -> today) | ~1.3 MB | `python update_fred.py` |
| Gold ETF holdings | `xauusd_data/alt/etf_<fund>_daily.csv` | GLD 2004 -> today, IAU snapshots | ~360 KB | `python update_alt.py --source etf` |
| Gold volatility index | `xauusd_data/alt/gvz_daily.csv` | 2009-09-18 -> today | ~120 KB | `python update_alt.py --source gvz` |
| Federal Reserve documents | `xauusd_data/alt/fed_documents.csv` + `alt/fed_text/` | newest 10 per run | grows with use | `python update_alt.py --source fed` |
| Real interest rates | `xauusd_data/rates/real_<cc>.csv` | 5 countries, monthly | ~15 KB | `python update_rates.py` |
| Text inventory | `xauusd_data/data_report.txt` | snapshot of everything above | ~10 KB | `python data_report.py` |

Default data directory: `$XAUUSD_DATA_DIR` or `<project>/xauusd_data`. Override
per run with `--data-dir`.

## 1-minute bars

Every series shares this format and stays in its own files, distinguished by the
file prefix (`--series`):

| Series | Dukascopy symbol | Prefix | Session |
| ------ | ---------------- | ------ | ------- |
| `xauusd` | `XAU/USD` | `xauusd_1m` | ~23 h/day |
| `xagusd` | `XAG/USD` | `xagusd_1m` | ~23 h/day |
| `xaueur` | `XAU/EUR` | `xaueur_1m` | ~23 h/day |
| `xaugbp` | `XAU/GBP` | `xaugbp_1m` | ~23 h/day |
| `xauchf` | `XAU/CHF` | `xauchf_1m` | ~23 h/day |
| `xauaud` | `XAU/AUD` | `xauaud_1m` | ~23 h/day |
| `xaujpy` | `XAU/JPY` | `xaujpy_1m` | ~23 h/day |
| `dxy` | `DOLLAR.IDX/USD` | `dxy_1m` | ~20.5 h/day |

The registry lives in `config.SERIES`; the prefix is always `<key>_1m`, so no two
series can write into the same file.

```
timestamp,open,high,low,close,volume
2026-11-06 21:59:00,4069.79,4071.357,4069.375,4069.545,0.02946
```

* `timestamp` is UTC, `YYYY-MM-DD HH:MM:SS`, no suffix, one row per minute.
* `--offer-side A` writes ask prices to `*_ask_YYYY-MM.csv`, so no two series
  mix. A symbol that returns no quotes (any unknown Dukascopy name) is rejected
  with an error instead of writing empty rows.
* `volume` is the Dukascopy unit for that minute, not a contract count.
* One header per file, CRLF endings, strictly increasing minutes, one file per
  calendar month.
* Append-only: stored rows are never rewritten and an already stored minute is
  never written twice, so a retry is safe.
* A run stops instead of writing beyond an unexplained stretch of empty bars
  (`--empty-allowance-hours`, default 72). Without that, a feed outage would
  leave a hole that later runs could no longer fill.

What a reader should expect:

* Roughly 25,000-31,000 bars per month, not 44,000: no series trades around
  the clock. Gold pauses about one hour a day, the index CFD about three, both
  close over the weekend, and the UTC boundary moves by an hour with daylight
  saving. `--status` reports those minutes as gaps on purpose.
* Holidays shorten the session further: the Friday after Thanksgiving ends in
  the early evening UTC, Christmas Day is missing almost entirely.

## COT (weekly positioning)

```
market,date,open_interest,noncomm_long,noncomm_short,noncomm_spread,traders_long,traders_short,net
GOLD - COMMODITY EXCHANGE INC.,2026-11-03,399169,220530,40982,68289,152,62,179548
```

* Source: CFTC yearly archives, `deacot{year}.zip` (legacy report) and
  `fut_disagg_txt_{year}.zip` (disaggregated report).
* Only the COMEX gold market is kept by default; `--all-gold` keeps every market
  whose name contains GOLD (micro gold, tokenised gold products).
* `date` is the report date, which is a Tuesday; the report is published on the
  following Friday.
* Rows are sorted oldest report first, so `tail -1` gives the latest week.
* `net` is computed, not downloaded: long minus short for the report's main
  speculative group. See `docs/cot.md` for what the numbers mean.

## Joining the datasets

* All three store dates in UTC without a time zone suffix, so no conversion is
  needed before a join.
* Price bars are minute level, COT is weekly and measured on Tuesday, FRED series
  are daily, weekly or monthly. Aggregate the minute bars to the coarsest
  frequency you need instead of filling the coarse series down to minutes.
* Align COT on the **publication** day (Friday) or the following Monday, never on
  the Tuesday report date, otherwise a model sees information that did not exist
  yet at that moment.
* FRED stamps a monthly value on the first of the month but publishes it weeks
  later: shift it to its release date before comparing it with prices.
* The 1-minute series starts at 23:00 UTC on a Sunday; a weekly aggregate that
  assumes calendar days will therefore show a shorter first bucket.

## Alternative sources

Three context sources live under `<data dir>/alt/` and are updated by one entry
point:

```sh
python update_alt.py                  # ETF gold holdings, GVZ, Fed documents
python update_alt.py --status         # what is stored, no network
```

* `etf_<fund>_daily.csv` - `date,close,volume,tonnes,ounces,nav`; GLD holds the
  full SPDR archive, IAU only the tonnage snapshots of each run.
* `gvz_daily.csv` - `date,close` of the Cboe gold volatility index.
* `fed_documents.csv` - `date,kind,title,speaker,url,chars` plus one
  `fed_text/<page>.txt` per document.

Sources, columns, rejected endpoints and the licensing notes are documented in
`docs/alternative.md`.

## Real interest rates

`update_rates.py` derives an ex-post real rate per country
(`long term yield - CPI inflation`, joined on the month) from the stored FRED
series and writes `rates/real_<cc>.csv` (`date,real`). The country registry and
the formula are documented in `docs/rates.md`.

## Text inventory

`data_report.py` writes one plain ASCII file with what is stored right now: per
price series the resolution, the covered range, the row and file counts, the
size, the last close and the two changes, plus both stored COT reports and every
macro series with its unit, frequency, coverage and last value.

```sh
python data_report.py                  # <data dir>/data_report.txt
python data_report.py --output -       # print it instead of writing
python data_report.py --year 2025      # another COT year
```

The file is a snapshot and is regenerated, never edited. It lives in the data
directory, so it is not committed (`.gitignore` covers `xauusd_data/`).

## Keeping this list current

Adding a data type (a price series, a COT report, a macro series, a new dataset)
is a single change (`FLOW-10`): the registry in `src/shared/config.py`, the
tables here and in the matching guide, `README.md`, and a fresh
`python data_report.py` run. The dashboard and the report read the registry, so
they show a new type without code changes, and the tests in
`tests/shared/test_config.py` fail when this document, `docs/macro.md` and the
registry drift apart.

## Backups and scratch files

Market data is regenerable: the three updater scripts can re-download it. That is
why the data directory is ignored by git instead of being committed. Temporary
files belong outside the repository.

