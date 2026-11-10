/* Price panel: window summary, controls note, live overlay and the chart. */
"use strict";

const DashboardPricePanel = (function () {
  const MINUTES = {"1m": 1, "5m": 5, "15m": 15, "30m": 30, "1h": 60,
                   "4h": 240, "1d": 0};

  function summaryRows(data, labels) {
    const summary = data.summary;
    const quality = data.quality;
    const windowLabel = data.interval === "1d" ? labels["price.days"]
                                               : labels["price.window"];
    return [
      [labels["price.open"], ChartCore.fmtValue(summary.first_close)],
      [labels["price.high"], ChartCore.fmtValue(summary.high)],
      [labels["price.low"], ChartCore.fmtValue(summary.low)],
      [labels["price.close"], ChartCore.fmtValue(summary.last_close)],
      [labels["price.change"], ChartCore.fmtPercent(summary.change_pct)],
      [labels["price.bars"], ChartCore.fmtValue(summary.bars, 0)],
      [windowLabel, ChartCore.fmtValue(summary.days, 0)],
      [labels["card.gaps"], ChartCore.fmtValue(quality.gaps, 0)],
      [labels["card.missing"],
       ChartCore.fmtValue(quality.missing_minutes, 0)]
    ];
  }

  function axisLabel(bar) {
    if (bar.time && bar.time.length > 10) {
      return bar.time.slice(11, 16);
    }
    return ChartCore.fmtDay(bar.day);
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
      live: labels["price.live"],
      axisLabel: axisLabel
    };
  }

  function bucketOf(minute, interval) {
    const size = MINUTES[interval] || 0;
    const day = minute.slice(0, 10);
    if (!size) {
      return {time: day, day: day};
    }
    const minutesOfDay = parseInt(minute.slice(11, 13), 10) * 60 +
                         parseInt(minute.slice(14, 16), 10);
    const start = minutesOfDay - minutesOfDay % size;
    const hour = String(Math.floor(start / 60)).padStart(2, "0");
    const rest = String(start % 60).padStart(2, "0");
    return {time: day + " " + hour + ":" + rest, day: day};
  }

  function liveMinutes(live, key) {
    if (!live || live.stale || !live.series) {
      return [];
    }
    return live.series[key] || [];
  }

  function mergeLive(bars, minutes, interval) {
    const merged = bars.slice();
    minutes.forEach(function (minute) {
      const bucket = bucketOf(minute.minute, interval);
      const last = merged[merged.length - 1];
      if (last && last.time === bucket.time) {
        merged[merged.length - 1] = Object.assign({}, last, {
          high: Math.max(last.high, minute.high),
          low: Math.min(last.low, minute.low),
          close: minute.close,
          count: (last.count || 0) + (minute.ticks || 0),
          live: true
        });
        return;
      }
      if (!last || bucket.time > last.time) {
        merged.push({
          time: bucket.time,
          day: bucket.day,
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

  function renderWindow(node, data, labels) {
    if (!node) {
      return;
    }
    const shown = data.bars.length;
    const total = data.bars_total || shown;
    const parts = [data.interval, ChartCore.fmtValue(shown, 0) + " bars"];
    if (data.truncated) {
      parts.push(labels["price.truncated"] + ": " +
                 ChartCore.fmtValue(total, 0));
    } else {
      parts.push(ChartCore.fmtValue(total, 0) + " in the window");
    }
    node.textContent = parts.join(" · ");
  }

  function render(panel, data, labels, overlays, live) {
    DomKit.keyValueStrip(panel.priceSummary, summaryRows(data, labels));
    renderWindow(panel.priceWindow, data, labels);
    const minutes = liveMinutes(live, data.key);
    renderLive(panel.priceLive, live, minutes, labels);
    ChartCandle.render(panel.priceChart,
                       mergeLive(data.bars, minutes, data.interval),
                       chartLabels(labels), overlays);
  }

  return {render: render};
})();
