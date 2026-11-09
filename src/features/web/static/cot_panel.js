/* COT panel: the weekly positioning of the two stored reports. */
"use strict";

const DashboardCotPanel = (function () {
  const REPORTS = [["legacy", "cot.legacy", 0], ["disagg", "cot.disagg", 1]];

  function mergeDates(reports) {
    const seen = {};
    Object.keys(reports).forEach(function (report) {
      reports[report].dates.forEach(function (date) {
        seen[date] = true;
      });
    });
    return Object.keys(seen).sort();
  }

  function valuesOn(report, categories) {
    const lookup = {};
    report.dates.forEach(function (date, index) {
      lookup[date] = report.net[index];
    });
    return categories.map(function (date) {
      return Object.prototype.hasOwnProperty.call(lookup, date)
        ? lookup[date] : null;
    });
  }

  function reportCard(report, labels, nameKey) {
    const summary = report.summary;
    const week = summary.weekly_change;
    const change = week === null || week === undefined ? null : {
      className: week >= 0 ? "up" : "down",
      text: labels["cot.week"] + " " +
            DomKit.signed(week, ChartCore.fmtCompact)
    };
    return DomKit.statCard(
      labels[nameKey],
      DomKit.signed(summary.net, ChartCore.fmtCompact),
      change,
      [
        [labels["cot.report"], summary.date || "-"],
        [labels["cot.share"],
         ChartCore.fmtValue(summary.net_share * 100, 1) + "%"],
        [labels["cot.open_interest"],
         ChartCore.fmtValue(summary.open_interest, 0)],
        [labels["cot.long"], ChartCore.fmtValue(summary.long_positions, 0)],
        [labels["cot.short"], ChartCore.fmtValue(summary.short_positions, 0)]
      ]
    );
  }

  function render(panel, data, labels) {
    panel.title.textContent = labels["cot.title"];
    panel.note.textContent = data.year
      ? labels["cot.note"] + " " + data.year
      : labels["cot.empty"];
    panel.summary.innerHTML = "";
    panel.chart.innerHTML = "";
    const reports = data.reports || {};
    if (!Object.keys(reports).length) {
      ChartCore.emptyNote(panel.chart, labels["cot.empty"]);
      return;
    }
    const series = [];
    REPORTS.forEach(function (entry) {
      const report = reports[entry[0]];
      if (!report) {
        return;
      }
      panel.summary.appendChild(reportCard(report, labels, entry[1]));
      series.push({name: labels[entry[1]], color: ChartCore.PALETTE[entry[2]],
                   report: report});
    });
    const categories = mergeDates(reports);
    const chartSeries = series.map(function (serie) {
      return {
        name: serie.name,
        color: serie.color,
        values: valuesOn(serie.report, categories)
      };
    });
    panel.summary.appendChild(DomKit.legend(chartSeries));
    ChartBars.render(panel.chart, {
      categories: categories,
      series: chartSeries,
      height: 260,
      labels: {empty: labels["cot.empty"]},
      yFormat: ChartCore.fmtCompact
    });
  }

  return {render: render};
})();
