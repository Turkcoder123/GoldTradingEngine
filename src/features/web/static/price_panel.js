/* Price panel: window summary plus the daily candlestick chart. */
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
      empty: labels["price.empty"]
    };
  }

  function render(panel, data, labels, overlays) {
    DomKit.keyValueStrip(panel.priceSummary, summaryRows(data, labels));
    ChartCandle.render(panel.priceChart, data.bars, chartLabels(labels),
                       overlays);
  }

  return {render: render};
})();
