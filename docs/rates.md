# Real interest rates

`update_rates.py` turns the macro series into the number that drives a metal
with no yield: the real interest rate of a country.

```
real = long term government yield (percent) - consumer price inflation (percent)
```

Both inputs are monthly OECD series that FRED republishes, joined on the month,
so the result is an **ex-post** real rate (the Fisher approximation): it says
what a bond holder kept after realised inflation, not what the market expects.

```sh
python update_rates.py                 # download the FRED series, rebuild the rates
python update_rates.py --offline       # rebuild from the stored series only
python update_rates.py --country US,DE
python update_rates.py --status --json
```

## Countries and series

| Code | Country | Yield series | Inflation series (CPI index, YoY) |
| ---- | ------- | ------------ | --------------------------------- |
| `US` | United States | `IRLTLT01USM156N` | `CPIAUCSL` |
| `DE` | Germany | `IRLTLT01DEM156N` | `CP0000DEM086NEST` |
| `FR` | France | `IRLTLT01FRM156N` | `CP0000FRM086NEST` |
| `IT` | Italy | `IRLTLT01ITM156N` | `CP0000ITM086NEST` |
| `GB` | United Kingdom | `IRLTLT01GBM156N` | `GBRCPIALLMINMEI` (last 2025-03) |

Inflation is computed from the CPI **index** as the year over year change,
because the OECD growth series (`CPALTT01...M659N`) that FRED republishes are no
longer updated: they stop in 2025-03, and Japan in 2022. The yields are current
(2026-09 for most countries), so the index path is what keeps the derived rate
alive.

A series whose newest month is older than six months is marked `STALE` in the
CLI, in the report and in the page, instead of pretending to be current.

Not registered, with the reason a run showed:

* `JP` - every Japan CPI series on FRED stops in 2021, far too old to be useful.
* `TR` - FRED has no OECD long term rate for Turkey (`IRLTLT01TRM156N` answers
  HTTP 400); a national source such as the central bank EVDS would be needed.

### Current UK and Japan inflation: attempted, blocked

Both gaps were chased against the national publishers; the result is recorded
here so the next attempt starts from the same evidence.

| Attempt | Endpoint | Result |
| ------- | -------- | ------ |
| ONS beta API, CPI index `CP00` | `api.beta.ons.gov.uk/v1/datasets/cpih01/editions/time-series/versions/67/observations?aggregate=CP00` | Works, 457 monthly points, but the newest is **2024-07**: the beta API is frozen and is older than FRED |
| ONS legacy time series | `api.ons.gov.uk/timeseries/{cdid}/dataset/{id}/data` | **404** for every CDID/dataset pairing tried (`D7G7`, `D7BT` x `mm23`) |
| Statistics Bureau (e-Stat) | `api.e-stat.go.jp/rest/3.0/app/json/getStatsData?...` | **Status 100, authentication failed**: e-Stat needs a free `appId` |
| Bank of Japan time series | `stat-search.boj.or.jp/api/v1/getMetadata?db=CO&code=PR01` | Reachable (HTTP 200) but the data calls **time out** from this host, so it cannot carry an updater |
| OECD SDMX (new API) | `sdmx.oecd.org/public/rest/data/OECD.SDD.TPS,DSD_PRICES...` | **404 / 406** for every path and `Accept` pair tried |

Consequences: `GB` stays registered with its FRED CPI and is marked `STALE`,
`JP` stays unregistered. Unblocking them needs one of: an ONS series id taken
from the live site, an e-Stat `appId` (free registration, a secret that would
live in `secrets/`), or a BoJ access path that answers within a normal timeout.

The raw series are stored like every other macro series under
`<data dir>/fred/<ID>.csv`; the derived rate is written to
`<data dir>/rates/real_<cc>.csv` with `date,real` columns.

## Output

```
 +2 real rate series
   US  United States    2026-09-01   +1.250  1y -0.750
   DE  Germany          2026-09-01   +0.400  1y +0.100
   world median +0.825 over 2 countries
```

The world figure is the **equal weighted median** of the stored countries: it is
a "what does the typical country pay" number, not a GDP weighted aggregate, and
the report says so. Countries with a missing series are reported as a warning
and simply skipped, so one unavailable id never blocks the rest.

`DFII10` stays the purest market read for the United States (the 10-year TIPS
real yield, already part of the macro registry); the derived US series is the
ex-post counterpart that can be compared with the other countries.

## Limits worth knowing

* Monthly resolution and a publication lag of weeks: this is a regime filter,
  not a trading signal.
* The yield is a 10-year government yield, the inflation is headline CPI. A
  core measure or an inflation-linked bond would tell a different story.
* FRED is the only source used. Yahoo Finance has the nominal yields (`^TNX`,
  `^FVX`, `^TYX`, `^IRX`) but no breakevens and no real yields, and the World
  Bank `FR.INR.RINR` series lags years and is empty for most countries, so both
  were tested and rejected (`docs/alternative.md`).
* A series id that does not resolve makes the run fail loudly with that id:
  the registry is never silently trimmed.
