# COT (Commitments of Traders)

The CFTC requires large futures traders in the United States to report their
positions every week. The result is the COT report: a count of who holds how
many contracts, measured on Tuesday and published on the following Friday.

`python update_cot.py` downloads the yearly archives and keeps the COMEX gold
rows under `xauusd_data/cot/`.

## What one row means

| Field | Meaning |
| ----- | ------- |
| `open_interest` | All contracts open in that market (each has a long and a short side) |
| `noncomm_long` / `noncomm_short` | Non-commercial (speculative) positions: funds, CTAs, traders |
| `noncomm_spread` | Spread positions: long one expiry, short another; direction-neutral |
| `traders_long` / `traders_short` | How many large traders hold those positions |
| `net` | `noncomm_long - noncomm_short`, the speculative tilt |

One COMEX gold contract is 100 troy ounces, so 220,530 long contracts is about
686 tonnes of gold. That conversion is the quickest way to judge magnitude.

## The three groups

| Group | Who | Behaviour |
| ----- | --- | --------- |
| Non-commercial / managed money | Funds, CTAs, systematic traders | Take directional risk, the group to read |
| Producer / merchant | Miners, refiners | Sell forward to fix the price of future production, structurally short |
| Swap dealer | Banks | Take the other side of OTC client flow, usually structurally short |

A short producer or swap position is normal hedging, not a bearish forecast.
Read the speculative side for direction.

## Reading it with three numbers

1. `net`: rising means optimism is building, falling means it is fading.
2. `net / open_interest`: a high share means a crowded trade. Extremes are the
   classic contrarian warning, not an entry signal.
3. The multi-week change of `net`, not the single week. One week is noise.

`python update_cot.py --status` prints exactly these, without touching the
network:

```
 COT 2026 (as stored)
   disagg   2026-11-03 | OI 399,169 | net +103,614 (26.0% of OI) | week -1,948 | 6w -23,775
   legacy   2026-11-03 | OI 399,169 | net +179,548 (45.0% of OI) | week -6,903 | 6w -46,305
```

## The two reports

* `legacy` (`cot_legacy_gold_YYYY.csv`): all non-commercial positions in one
  bucket. Good for a long history and for the headline "speculators are long X".
* `disaggregated` (`cot_disagg_gold_YYYY.csv`): splits that bucket into managed
  money, producer/merchant and swap dealer. Good for asking who exactly moved.

The two are different slices of the same market, not two estimates of one
number: managed money net is part of non-commercial net, never equal to it.

## Snapshot at the latest stored report (2026-11-03)

| Report | Net | Share of OI | Last week | 6 weeks |
| ------ | --- | ----------- | --------- | ------- |
| legacy (non-commercial) | +179,548 | 45.0% | -6,903 | -46,305 |
| disagg (managed money) | +103,614 | 26.0% | -1,948 | -23,775 |

Speculators were still heavily net long, but they had been cutting that position
for six weeks while the price fell from about 4,150 to 3,875 USD. Long
liquidation plus new shorts, not a sudden change in physical demand.

## Pitfalls

* Measured Tuesday, published Friday: it is a positioning snapshot, never a
  timing tool, and anything you backtest must respect the publication delay.
* Yearly archives only: the current file starts in January, so early-year
  history comes from the previous year's archive (`--year 2025`).
* The CFTC header itself is inconsistent (`Swap_Positions_Long_All` but
  `Swap__Positions_Short_All`). The client validates every mapped column and
  fails loudly instead of writing empty columns.
* `--all-gold` also matches micro gold and tokenised gold products; use the
  default exact market name for the COMEX contract.
