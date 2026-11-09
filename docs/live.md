# Temporary live layer

`stream_live.py` keeps a live window of three series in memory and prints every
1-minute bar that closes:

| Series | Source | Shape |
| ------ | ------ | ----- |
| `xauusd` | SiftingIO WebSocket, product `com` | bid/ask ticks, ~100 ms apart |
| `eurusd` | SiftingIO WebSocket, product `fx` | bid/ask ticks, ~100 ms apart |
| `dxy` | Dukascopy 1-minute feed, polled | complete OHLCV bars, ~1 min behind |

It is an overlay only. Dukascopy stays the authoritative source of the stored
history, the live layer never writes to a CSV file, and every live bar the
keeper later covers is dropped from the buffer.

## Setup

The live layer is the one part of the project with a third-party dependency:
`websocket-client`, approved for this feature only (`OPEN-6`). It is imported
lazily, so every other command and the whole test suite run without it.

```sh
python -m pip install websocket-client
```

The SiftingIO key is read from `$SIFTING_API_KEY` first and from a `.env` file
at the repository root second. The process environment always wins.

```sh
cp .env.example .env        # then fill in SIFTING_API_KEY
chmod 600 .env              # the file holds a secret
```

`.env` is ignored by git; only the empty `.env.example` placeholder is
committed (`GIT-6`). The WebSocket is authenticated with the key in the query
string, which is the only method the provider documents for the socket; the key
is redacted from every message the layer prints.

## Running

```sh
python stream_live.py                     # all three series, until interrupted
python stream_live.py --seconds 120       # bounded run
python stream_live.py --json              # one JSON object per closed bar
python stream_live.py --series dxy        # dollar index only, no API key needed
python stream_live.py --side A            # ask instead of bid
python stream_live.py --buffer-minutes 240
```

Every closed bar is printed as it closes, and the run ends with a summary of the
buffers, the frame counters and the stored boundary of each series:

```
   2026-11-09 07:33:00  xauusd  O  4099.87300  H  4100.04100  L  4099.70500  C  4099.70500  13 ticks
   2026-11-09 07:33:00  dxy     O    101.86000  H    101.87000  L    101.84500  C    101.85100  volume 0.108
 live buffer xauusd=2 dxy=3 | 47 ticks | 0 ignored frames | 0 errors | 0 reconnects
 boundaries xauusd=2026-11-06 21:59:00 dxy=2026-11-06 21:59:00
```

Exit codes: `0` when the run finished, `1` for a missing key or an unusable
setting, `130` when it was interrupted.

## SiftingIO protocol

| Item | Value |
| ---- | ----- |
| Endpoint | `wss://stream.sifting.io/ws/v1?key=<key>` |
| Authentication | `key` query parameter (the only documented WebSocket method) |
| Subscribe | `{"op": "subscribe", "product": "com", "symbols": ["XAUUSD"]}` |
| Keepalive | `{"op": "ping"}` every 20 seconds, answered with `{"f": "pong"}` |
| Products | `com` for spot commodities, `fx` for currency pairs |
| Tick frame | `{"f":"tick","s":"XAUUSD","p":4086.3,"b":4085.99,"a":4086.62,"t":1794211181154}` |
| Ack frame | `{"f":"ack","op":"auth","tier":"free","max_conn":1,"max_subs":5}` |
| Error frame | `{"f":"error","code":"...","message":"..."}` |

Every server frame carries an `f` discriminator, so the client branches on that
first. Prices arrive as strings or numbers; both are accepted. Timestamps are
already epoch milliseconds, which is what the buffers key on. The quote side
(`--side B|A`) picks `b` or `a`; `p` is the documented fallback. SiftingIO
publishes no tick feed for the dollar index, hence the polled source below.

## Dollar index poll

The Dukascopy chart service is asked for the stored-through minute onwards, once
a minute (`DXY_POLL_SECONDS`), and every returned bar enters the buffer:

- One request per poll, with the same retry and timeout settings as the keeper.
- Bars are complete minutes, so they are buffered and printed immediately; a
  polled bar replaces a bar that ticks had built for the same minute.
- A failing poll is reported and skipped, never raised: the next poll retries
  from the last accepted minute.
- Five minutes of history are fetched on the first poll, so a fresh start shows
  a short window instead of a single bar.

## Dashboard overlay

The web page cannot read another process's memory, so the session publishes its
buffers as one small JSON document under `<data dir>/live/last.json`
(`core/live_snapshot.py`). It is runtime state, not market history: rewritten
when a bar closes, written atomically, and ignored by git with the rest of the
data directory.

The dashboard reads it through `GET /api/live` (`features/web/live_view.py`) and
draws the newest live minutes of the selected series as a partial bar on the
right of the daily chart: hollow, dashed, amber, with a `LIVE` badge above the
chart and a gold last-price line. The page polls the endpoint every twenty
seconds; the badge turns grey when the document is older than ten minutes, and
the overlay disappears when it is missing.

```sh
python serve_dashboard.py         # reads the overlay when the stream is running
python stream_live.py --no-snapshot   # run without publishing to the page
python stream_live.py --snapshot /path/last.json
```

## Data precedence and buffer rules

- Dukascopy data is authoritative and persistent; live data is temporary and
  memory-only.
- The boundary of each series is the newest minute its own CSV already holds. A
  tick or bar at or before that minute is refused, so live data can never
  rewrite history. The keeper refreshes that history every five minutes.
- The boundary is refreshed before the ticks of a new minute (a tail read of a
  few kilobytes), and every live bar it now covers is dropped.
- Bars are keyed by the UTC minute: open is the earliest tick of that minute,
  close the latest, high and low come from every accepted tick. A tick that
  arrives out of order updates its own minute only.
- Minutes without ticks produce no bar: no candle is ever synthesised.
- The buffer keeps a bounded number of minutes per series (`--buffer-minutes`);
  the oldest bars are dropped first.
- Tick-built bars carry `volume: null` (the provider publishes no volume); the
  polled dollar index bars carry the Dukascopy volume.

## Limits

- SiftingIO free tier: 1 connection and 5 subscriptions, which covers gold,
  EUR/USD and three more symbols. A second connection closes the first.
- Gold has no REST snapshot on SiftingIO: `/v1/last/quote/...` rejects the
  commodity venue, so the WebSocket is the only live path. Historical gold bars
  are available through `/v1/hist/commodities/XAUUSD/bars` (gzip required).
- SiftingIO data is aggregated and normalised, not a raw exchange feed; against
  the stored Dukascopy bars the gold price differed by about 0.008 percent on
  the same minutes, which is the bid/ask definition, but the provider states its
  values are synthetic references and may differ materially.
- The dollar index arrives about a minute late and only as 1-minute bars; no
  provider tested offers a DXY tick. UUP is an ETF proxy, not the index.
- Live bars are not shown in the dashboard and are not stored; wiring the buffer
  into the page is a separate change.
- A dropped socket is retried with a bounded exponential backoff (1 s doubling
  up to 60 s); the run reports each interruption and reconnect.

