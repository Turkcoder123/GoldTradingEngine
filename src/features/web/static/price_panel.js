/* Price panel: window summary, live overlay and the daily candlestick chart. */
"use strict";

const DashboardPricePanel = (function () {
  function summaryRows(data, labels) {
    const summary = data.summary;
    const quality = data.quality;
    return [
      [labels["price.open"], ChartCore.fmtValue(summary.first_close)],
      [labels["price.high"], ChartCore.fmtValue(summary.high)],
      [labels["price.low"], ChartCore.fmtValue(summary.low)],
      [labels["price.close"], ChartCore.fmtValue(summary.last_close)],
      [labels["price.change"], ChartCore.fmtPercent(summary.change_pct)],
      [labels["price.bars"], ChartCore.fmtValue(summary.bars, 0)],
      [labels["price.days"], ChartCore.fmtValue(summary.days, 0)],
      [labels["card.gaps"], ChartCore.fmtValue(quality.gaps, 0)],
      [labels["card.missing"],
       ChartCore.fmtValue(quality.missing_minutes, 0)]
    ];
  }

  function chartLabels(labels) {
    return {
      open: labels["price.open"],
      high: labels["price.high"],
      low: labels["price.low"],
      close: labels["price.close"],
      volume: labels["price.volume"],
      bars: labels["price.bars"],
      empty: labels["price.empty"],
      live: labels["price.live"]
    };
  }

  function liveMinutes(live, key) {
    if (!live || live.stale || !live.series) {
      return [];
    }
    return live.series[key] || [];
  }

  function mergeLive(bars, minutes) {
    const merged = bars.slice();
    minutes.forEach(function (minute) {
      const day = minute.minute.slice(0, 10);
      const last = merged[merged.length - 1];
      if (last && last.day === day) {
        merged[merged.length - 1] = {
          day: day,
          open: last.open,
          high: Math.max(last.high, minute.high),
          low: Math.min(last.low, minute.low),
          close: minute.close,
          volume: last.volume,
          count: (last.count || 0) + (minute.ticks || 0),
          live: true
        };
        return;
      }
      if (!last || day > last.day) {
        merged.push({
          day: day,
          open: minute.open,
          high: minute.high,
          low: minute.low,
          close: minute.close,
          volume: minute.volume || 0,
          count: minute.ticks || 0,
          live: true
        });
      }
    });
    return merged;
  }

  function renderLive(node, live, minutes, labels) {
    if (!node) {
      return;
    }
    if (!minutes.length) {
      node.hidden = true;
      return;
    }
    const last = minutes[minutes.length - 1];
    node.hidden = false;
    node.classList.toggle("stale", Boolean(live.stale));
    node.innerHTML = '<span class="dot"></span>' + labels["price.live"] + " " +
      ChartCore.fmtValue(last.close) + " &middot; " +
      last.minute.slice(11, 16) + " UTC &middot; " + minutes.length + " " +
      labels["price.live_bars"];
  }

  function render(panel, data, labels, overlays, live) {
    DomKit.keyValueStrip(panel.priceSummary, summaryRows(data, labels));
    const minutes = liveMinutes(live, data.key);
    renderLive(panel.priceLive, live, minutes, labels);
    ChartCandle.render(panel.priceChart, mergeLive(data.bars, minutes),
                       chartLabels(labels), overlays);
  }

  return {render: render};
})();
