# Temporary live feed (Twelve Data)

`stream_live.py` streams XAU/USD ticks from Twelve Data into an in-memory
1-minute buffer and prints every bar the stream closes. It is an overlay only:
Dukascopy stays the authoritative source of the stored history, and the live
layer never writes to a CSV file. The point is the gap between two Dukascopy
refreshes (about fifteen minutes), not a replacement for them.

## Setup

The live feed is the one part of the project with a third-party dependency:
`websocket-client`, approved for this feature only (`OPEN-6`). It is imported
lazily, so every other command and the whole test suite still run without it.

```sh
python -m pip install websocket-client
```

The API key is read from `$TWELVE_DATA_API_KEY` first and from a `.env` file at
the repository root second. The process environment always wins, so a shell
export or a CI secret is never overridden.

```sh
cp .env.example .env        # then fill in TWELVE_DATA_API_KEY
chmod 600 .env              # the file holds a secret
```

`.env` is ignored by git; only the empty `.env.example` placeholder is
committed (`GIT-6`). The key is sent in the `X-TD-APIKEY` header, never in the
URL, and it is redacted from every message the stream prints.

## Running

```sh
python stream_live.py                    # stream until interrupted
python stream_live.py --seconds 60       # bounded run
python stream_live.py --json             # one JSON object per closed bar
python stream_live.py --side A           # ask instead of bid
python stream_live.py --buffer-minutes 240
```

Every closed bar is printed as it closes, and the run ends with one summary
line (bars, ticks, ignored frames, reconnects and the stored boundary):

```
   2026-11-09 12:01:00  O   4069.790  H   4071.357  L   4069.375  C   4069.545   37 ticks
 live buffer: 3 bars | 412 ticks | 4 ignored frames | 0 reconnects | boundary 2026-11-09 12:00:00
```

Exit codes: `0` when the run finished, `1` for a missing key or an unusable
setting, `130` when it was interrupted.

## Protocol

| Item | Value |
| ---- | ----- |
| Endpoint | `wss://ws.twelvedata.com/v1/quotes/price` |
| Authentication | `X-TD-APIKEY: <key>` request header (never the URL) |
| Subscription | `{"action": "subscribe", "params": {"symbols": "XAU/USD"}}` |
| Heartbeat | `{"action": "heartbeat"}` about every 10 seconds |
| Price event | `event`, `symbol`, `type`, `timestamp` (UNIX seconds), `price`, `bid`, `ask` |
| Status event | `event: "subscribe-status"` with `status`, `success` and `fails` |

The quote side (`--side B|A`) picks `bid` or `ask`; `price` is the documented
fallback when the side field is missing. Provider timestamps are normalised to
epoch milliseconds, and a millisecond value is recognised by its magnitude.

## Data precedence and buffer rules

- Dukascopy data is authoritative and persistent; Twelve Data is temporary and
  memory-only.
- The boundary is the newest minute already stored by Dukascopy. A tick at or
  before that minute is refused, so live data can never rewrite history.
- The boundary is refreshed before the ticks of a new minute (a tail read of a
  few kilobytes), and every live bar it now covers is dropped from the buffer.
- Bars are keyed by the UTC minute of the tick: open is the earliest tick of
  that minute, close the latest, high and low come from every accepted tick.
  A tick that arrives out of order updates its own minute only.
- Minutes without ticks produce no bar: no candle is ever synthesised.
- The buffer keeps a bounded number of minutes (`--buffer-minutes`); the oldest
  bars are dropped first.
- Volume is not published by the provider, so a live bar carries
  `volume: null` instead of a fabricated number.
- Nothing in this layer opens a file for writing; a test asserts it.

## Limitations

- Twelve Data plans limit connections and symbols. The Basic plan allows one
  connection and eight trial symbols; `XAU/USD` must be available to the
  account for the stream to deliver ticks.
- No latency is promised. Provider, network and entitlements decide what the
  end-to-end delay is; the project claims no sub-100 ms figure.
- Market closures deliver no ticks, so the buffer stays empty and the summary
  reports `empty` as the boundary until Dukascopy stores data.
- Live bars are not shown in the dashboard and are not stored; adding the
  overlay to the page is a separate, separately requested change.
- A dropped socket is retried with a bounded exponential backoff (1 s doubling
  up to 60 s); the run reports each interruption and reconnect.
