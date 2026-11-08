# Macro data (FRED)

`update_fred.py` downloads macroeconomic series from the St. Louis Fed and keeps
them as plain `date,value` CSV files under `<data dir>/fred/`.

No API key is needed: the keyless `fredgraph.csv` endpoint is used by default,
so nothing secret lives in the repository. When a key is configured the client
upgrades to the official JSON API instead:

| Where | How |
| ----- | --- |
| environment | `export FRED_API_KEY=...` |
| local file | `secrets/fred_api_key` (git-ignored, one line, mode 600) |

Get a key at https://fred.stlouisfed.org/docs/api/api_key.html. The key is never
printed: error text is redacted before it reaches the console.

```sh
python update_fred.py                      # the registered series
python update_fred.py --series DGS10,DFII10
python update_fred.py --status             # summarize what is stored
python update_fred.py --status --json
```

```
 +10 FRED series (73,798 observations)
   DFII10   2026-11-05        2.600 | change -0.040 | 1y +0.730  (10-year TIPS real yield)
   DGS10    2026-11-05        4.840 | change -0.060 | 1y +0.670  (10-year Treasury yield)
   ...
```

Each line is the latest observation, the change since the previous one and the
change against roughly a year earlier.

## Registered series

| ID | What it is | Why it matters for gold |
| -- | ---------- | ----------------------- |
| `DFII10` | 10-year TIPS real yield | The real yield is the opportunity cost of holding a metal that pays nothing: the classic inverse driver |
| `DGS10` | 10-year Treasury yield | Long-end nominal rates |
| `DGS2` | 2-year Treasury yield | Rate expectations, the front end |
| `T10Y2Y` | 10-year minus 2-year spread | Curve shape, recession pricing |
| `T10YIE` | 10-year breakeven inflation | Inflation compensation the market prices |
| `DTWEXBGS` | Broad trade-weighted dollar index | Gold is quoted in dollars, so the dollar moves it |
| `WALCL` | Fed total assets (weekly) | Balance-sheet expansion is the liquidity story |
| `CPIAUCSL` | Consumer price index (monthly) | Inflation level behind the metal's hedge narrative |
| `FEDFUNDS` | Effective federal funds rate (monthly) | Policy rate |
| `VIXCLS` | CBOE volatility index | Risk appetite, safe-haven flows |

## Format

```
date,value
2003-01-02,2.43
2026-11-05,2.60
```

* `date` is the observation date, `value` the published number, oldest first.
* FRED marks a missing observation with a dot; it is stored as an empty value, so
  a gap stays visible instead of being silently filled.
* Frequencies differ by series (daily, weekly, monthly) and are not resampled:
  the file keeps exactly what FRED publishes, which is what makes the data
  verifiable against the source.
* The whole available history is stored, not a rolling window: `DGS10` reaches
  back to 1962, `DFII10` to 2003, `WALCL` to 2002.

## Pitfalls

* `fredgraph.csv` is a plot endpoint, not an API: it has no metadata, no units
  and no release calendar. Units are the ones FRED documents per series (percent
  for rates, index points for `DTWEXBGS`, millions of dollars for `WALCL`).
* Monthly series are stamped on the first of the month, weekly ones on
  Wednesday. Joining them with 1-minute price data therefore needs a forward
  fill and the release lag in mind: a value for `2026-10-01` was not public on
  that date.
* The host stalls for minutes when a request looks like a browser. The client
  sends the default urllib user agent on purpose and retries with a growing
  pause.
