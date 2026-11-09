# Alternative sources

Besides the price bars, the COT report and the macro series, the project keeps
three market context sources under `<data dir>/alt/`. All of them are fetched
with the standard library only (`urllib`, `zipfile`, `csv`, `xml.etree`,
`html.parser`), so `OPEN-2` stays intact: no package manager, no dependency.

```sh
python update_alt.py                    # all three sources
python update_alt.py --source etf       # one source, repeatable
python update_alt.py --source etf --etf gld
python update_alt.py --status           # what is stored, no network
python update_alt.py --status --json
```

Every run prints one line per stored series with the covered range and the
latest value, and `--json` prints the same as machine-readable output. The
runs are idempotent: a source that publishes its whole history is merged by
date, and a snapshot source only adds today's row.

## 1. Gold ETF holdings (`etf`)

| Fund | Label | File | Source |
| ---- | ----- | ---- | ------ |
| `gld` | SPDR Gold Shares | `alt/etf_gld_daily.csv` | SPDR Gold Shares historical archive (XLSX) |
| `iau` | iShares Gold Trust | `alt/etf_iau_daily.csv` | iShares product page (tonnes in trust) |

**GLD.** The official archive endpoint returns an XLSX workbook:

```
https://api.spdrgoldshares.com/api/v1/historical-archive?product=gld&exchange=NYSE&lang=en
```

The workbook holds a disclaimer sheet and the data sheet (`US GLD Historical
Archive`); the parser reads the header row and keeps `Date`, `Closing Price`,
`Daily Share Volume`, `Total Ounces of Gold in the Trust`, `Tonnes of Gold` and
`Total Net Asset Value in the Trust`. The stored history starts on 2004-11-18
with roughly 5,700 rows, so a run costs one download of about 540 KB.

**IAU.** iShares has no open endpoint; the tonnage figure is embedded in the
product page as JSON (`"tonnes":{"formattedValue":"460.81",
"formattedAsOfDate":"Nov 06, 2026"}`) and is read with a regular expression
after unescaping the HTML. That is a snapshot, so the file grows by one row per
run and the tonnage column is the only populated value. The old
`.ajax?fileType=csv` endpoint answers with an HTML page now, which is why it is
not used.

Columns of both files: `date,close,volume,tonnes,ounces,nav` (a cell stays empty
when the source does not publish it).

What it is good for: the tonnage is the physical demand side of the metal, the
volume is ETF activity and the NAV tracks the fund's gold at market price.

## 2. Gold volatility index (`gvz`)

```
https://cdn.cboe.com/api/global/us_indices/daily_prices/GVZ_History.csv
```

The Cboe file is `DATE,GVZ` with `MM/DD/YYYY` dates and starts on 2009-09-18
(about 4,300 rows). It is stored as `date,close` in `alt/gvz_daily.csv`.
GVZ is the Cboe Gold ETF Volatility Index: the implied volatility the options
market prices for GLD, a direct read of how much movement is expected.

## 3. Federal Reserve documents (`fed`)

| Feed | Contents |
| ---- | -------- |
| `https://www.federalreserve.gov/feeds/speeches.xml` | Board speeches, 15 newest |
| `https://www.federalreserve.gov/feeds/press_monetary.xml` | FOMC statements and minutes releases |

The list needs no scraping: both feeds are RSS with title, publication date and
link. Only the body text of a new document is fetched once, from the page's
`<div id="article">`, paragraph by paragraph with `html.parser` (no
BeautifulSoup). A release that announces FOMC minutes also carries the link to
the minutes document, which is fetched and stored as its own row.

Storage:

* `alt/fed_documents.csv` with `date,kind,title,speaker,url,chars`, where `kind`
  is `speech`, `statement`, `minutes_release` or `minutes`.
* `alt/fed_text/<page>.txt` with the body text of every document.

`--limit` (default 10) caps how many new documents one run fetches; a document
that is already stored is never downloaded again.

## Sources that were tested and rejected

| Source | Result |
| ------ | ------ |
| CME warehouse stocks (`cmeGroup.com/delivery_reports/...xls`) | HTTP 403 from the storage bucket; needs a browser session or a licensed CME feed |
| IMF IFS reserves API | The legacy `dataservices.imf.org` SDMX service is gone, `data.imf.org` answers 403 and the new SDMX 2.1 catalogue has no IFS dataflow |
| World Gold Council monthly XLSX | The page is readable and lists the file links, the download itself answers 403 |
| Yahoo Finance chart API | Works occasionally and then answers HTTP 429; not a base to build on, so it is not used in the code |

## Limits worth knowing

* ETF and volatility series are daily, not minute bars; the metal itself has no
  ETF symbol, so prices stay in the 1-minute series.
* Nothing is redistributed beyond the local data directory, but the sources keep
  their rights: the SPDR archive forbids redistribution without consent, Cboe
  and the Federal Reserve publish public data under their own terms.
* The iShares tonnage and the Fed article text depend on page structure. A
  layout change shows up as a loud parse error, never as a silent zero.
