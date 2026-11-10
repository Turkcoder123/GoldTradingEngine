"""Every user-facing text of the dashboard lives here (LANG-4).

English is the default locale. The page receives this dictionary as JSON, so the
JavaScript never hardcodes a label and a second locale can be added by dropping
one more entry into `_RESOURCES` (OPEN-3 keeps Turkish out until asked for).
"""

from __future__ import annotations

DEFAULT_LOCALE = "en"

_EN = {
    "app.title": "Gold Market Data Dashboard",
    "app.subtitle": "Price, positioning and macro data stored by this project",
    "app.version": "Version",
    "app.data_dir": "Data directory",
    "app.refresh": "Refresh",
    "app.loading": "Loading",
    "app.failed": "Could not load",
    "app.read_only": "Read-only view of the CSV files; nothing is downloaded.",

    "section.overview": "Overview",
    "section.prices": "Price chart",

    "kpi.series": "Price series",
    "kpi.files": "CSV files",
    "kpi.size": "Stored size",
    "kpi.coverage": "Coverage (UTC)",
    "kpi.last_bar": "Last bar (UTC)",
    "kpi.age": "Last bar age",
    "kpi.age_value": "{value} min",

    "price.range.1m": "1M",
    "price.range.3m": "3M",
    "price.range.6m": "6M",
    "price.range.1y": "1Y",
    "price.range.all": "All",
    "price.open": "Open",
    "price.high": "High",
    "price.low": "Low",
    "price.close": "Close",
    "price.change": "Change",
    "price.volume": "Volume",
    "price.bars": "Bars",
    "price.days": "Days",
    "price.empty": "No bars stored for this series",
    "price.note": "Bars aggregated from the stored 1-minute files; pick a timeframe above and hover for one bar.",
    "price.live": "LIVE",
    "price.live_updated": "updated",
    "price.live_stale": "live stream idle",
    "price.live_bars": "live bars",
    "price.interval": "Timeframe",
    "price.range": "Range",
    "price.window": "Window",
    "price.truncated": "window cut to the newest bars",

    "card.files": "Files",
    "card.size": "Size",
    "card.gaps": "Gaps",
    "card.missing": "Minutes without bars",
    "card.stale": "Last bar",

    "cot.title": "COMEX gold positioning (CFTC)",
    "cot.legacy": "Legacy net (non-commercial)",
    "cot.disagg": "Managed money net",
    "cot.open_interest": "Open interest",
    "cot.long": "Long",
    "cot.short": "Short",
    "cot.week": "Week",
    "cot.share": "Share of OI",
    "cot.report": "Report date",
    "cot.note": "Weekly report measured on Tuesday, published on Friday.",
    "cot.empty": "No stored COT report",

    "macro.title": "Macro series (FRED)",
    "macro.points": "Observations",
    "macro.empty": "No stored FRED series",
    "macro.note": "Sparklines show the stored history; click a card for the detail chart.",
    "rates.title": "Real interest rates",
    "rates.note": "Long term government yield minus consumer price inflation, "
                  "joined on the month, and the equal weighted median across "
                  "the stored countries.",
    "rates.country": "Country",
    "rates.latest": "Latest",
    "rates.change": "1y change",
    "rates.median": "World median",
    "rates.countries": "countries",
    "rates.empty": "No real rate series stored yet",
    "rates.hint": "Run python update_rates.py to fill this block.",
    "rates.stale": "stale",

    "section.alt": "Alternative sources",
    "alt.note": "ETF tonnage, the Cboe gold volatility index and the newest "
                "Federal Reserve documents.",
    "alt.tonnes": "tonnes",
    "alt.texts": "texts",
    "alt.tonnes_title": "Gold held by the ETFs (tonnes in trust, last year)",
    "alt.gvz_title": "Cboe gold volatility index (GVZ, last two years)",
    "alt.documents": "Federal Reserve documents",
    "alt.date": "Date",
    "alt.kind": "Kind",
    "alt.title": "Title",
    "alt.chars": "Characters",
    "alt.kind.speech": "Speech",
    "alt.kind.statement": "Statement",
    "alt.kind.minutes_release": "Minutes release",
    "alt.kind.minutes": "Minutes",
    "alt.empty": "No alternative source stored yet",
    "alt.hint": "Run python update_alt.py to fill this panel.",

    "section.smc": "Smart money structures",
    "smc.note": "Swings, structure breaks, liquidity sweeps, order blocks and "
                "fair value gaps detected on the same daily bars the chart "
                "draws.",
    "smc.hint": "A detected structure describes the bars that formed it; it is "
                "not an entry signal.",
    "smc.empty": "No structure detected in this window",
    "smc.timeframe": "Timeframe",
    "smc.timeframe.1d": "Daily bars",
    "smc.window": "Window",
    "smc.bars": "Bars",
    "smc.parameters": "Parameters",
    "smc.parameters_value": "{left}/{right} pivot, block {lookback}",
    "smc.breaks": "Structure breaks",
    "smc.zones": "Zones",
    "smc.sweeps": "Sweeps",
    "smc.swings": "Swings",
    "smc.recent": "Newest structures",
    "smc.column.bar": "Bar",
    "smc.column.pattern": "Pattern",
    "smc.column.direction": "Direction",
    "smc.column.level": "Level",
    "smc.column.state": "State",
    "smc.state.filled": "Filled",
    "smc.state.open": "Open",
    "smc.pattern.SWING_HIGH": "Swing high",
    "smc.pattern.SWING_LOW": "Swing low",
    "smc.pattern.BOS": "Break of structure",
    "smc.pattern.CHOCH": "Change of character",
    "smc.pattern.LIQUIDITY_SWEEP": "Liquidity sweep",
    "smc.pattern.ORDER_BLOCK": "Order block",
    "smc.pattern.FVG": "Fair value gap",
    "smc.direction.bullish": "Bullish",
    "smc.direction.bearish": "Bearish",
    "smc.direction.bullish_reference": "Support pivot",
    "smc.direction.bearish_reference": "Resistance pivot",
    "smc.direction.buy_side_taken": "Buy side taken",
    "smc.direction.sell_side_taken": "Sell side taken",

    "error.not_found": "Not found",
    "error.bad_series": "Unknown price series",
    "error.bad_interval": "Unknown timeframe",
    "error.build": "The dashboard could not build this section",
}

_RESOURCES = {DEFAULT_LOCALE: _EN}


def labels(locale: str = DEFAULT_LOCALE) -> dict:
    """Label dictionary of one locale; an unknown locale falls back to English."""
    return dict(_RESOURCES.get(locale, _EN))


def text(key: str, locale: str = DEFAULT_LOCALE) -> str:
    """One label; an unknown key reports the key instead of failing."""
    return labels(locale).get(key, key)
