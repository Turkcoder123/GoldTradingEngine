/* Macro panel: one sparkline card per FRED series, a detail chart and the
   derived real interest rates. */
"use strict";

const DashboardMacroPanel = (function () {
  const state = {data: null, selected: null, panel: null, labels: null,
                 rates: null};

  function detailChart() {
    const serie = state.data.series.filter(function (entry) {
      return entry.id === state.selected;
    })[0];
    if (!serie) {
      return;
    }
    ChartLine.render(state.panel.chart, {
      series: [{name: serie.id, color: ChartCore.PALETTE[0],
                points: serie.points}],
      height: 260,
      labels: {empty: state.labels["macro.empty"]}
    });
  }

  function card(serie, labels) {
    const node = DomKit.element("button", "macro-card");
    node.type = "button";
    if (serie.id === state.selected) {
      node.classList.add("active");
    }
    const change = serie.summary.change;
    const head = DomKit.element("div", "macro-head");
    head.appendChild(DomKit.element("span", "macro-id", serie.id));
    head.appendChild(DomKit.element(
      "span", "macro-change " + (change >= 0 ? "up" : "down"),
      change === null || change === undefined ? "-"
        : DomKit.signed(change, function (value) { return value.toFixed(3); })
    ));
    node.appendChild(head);
    node.appendChild(DomKit.element("span", "macro-value",
                                    ChartCore.fmtValue(serie.summary.value, 3)));
    node.appendChild(DomKit.element("span", "macro-label", serie.label));
    const spark = DomKit.element("div", "macro-spark");
    node.appendChild(spark);
    node.appendChild(DomKit.element(
      "span", "macro-meta",
      (serie.summary.date || "-") + " | " +
      ChartCore.fmtValue(serie.summary.observations, 0) + " " +
      labels["macro.points"].toLowerCase()));
    Sparkline.render(spark, serie.points.map(function (point) {
      return point[1];
    }), {color: ChartCore.PALETTE[0]});
    node.addEventListener("click", function () {
      state.selected = serie.id;
      render(state.panel, state.data, state.labels, state.rates);
    });
    return node;
  }

  function ratesTable(rates, labels) {
    const table = DomKit.element("table", "doc-table");
    const head = DomKit.element("tr");
    [labels["rates.country"], labels["rates.latest"],
     labels["rates.change"]].forEach(function (title) {
      head.appendChild(DomKit.element("th", "", title));
    });
    const thead = DomKit.element("thead");
    thead.appendChild(head);
    table.appendChild(thead);
    const body = DomKit.element("tbody");
    rates.countries.forEach(function (entry) {
      const row = DomKit.element("tr");
      row.appendChild(DomKit.element("td", "", entry.label));
      row.appendChild(DomKit.element("td", "num",
        ChartCore.fmtValue(entry.latest, 2) + "%"));
      row.appendChild(DomKit.element("td", "num",
        entry.change_1y === null || entry.change_1y === undefined
          ? "-" : ChartCore.fmtPercent(entry.change_1y)));
      body.appendChild(row);
    });
    table.appendChild(body);
    return table;
  }

  function renderRates(panel, rates, labels) {
    const world = rates && rates.world ? rates.world : null;
    const median = world && world.median !== null ? world.median : null;
    panel.ratesCaption.textContent = labels["rates.title"] + " - " +
      labels["rates.median"] + ": " +
      (median === null ? "-" : ChartCore.fmtValue(median, 2) + "%") + " (" +
      (world ? world.count : 0) + " " + labels["rates.countries"] + ")";
    ChartCore.clear(panel.ratesChart);
    panel.rates.innerHTML = "";
    if (!world || !world.points.length) {
      ChartCore.emptyNote(panel.ratesChart,
                          labels["rates.empty"] + " " + labels["rates.hint"]);
      return;
    }
    ChartLine.render(panel.ratesChart, {
      series: [{name: labels["rates.median"], color: ChartCore.PALETTE[2],
                points: world.points}],
      height: 220,
      labels: {empty: labels["rates.empty"]}
    });
    panel.rates.appendChild(ratesTable(rates, labels));
  }

  function render(panel, data, labels, rates) {
    state.data = data;
    state.panel = panel;
    state.labels = labels;
    state.rates = rates;
    panel.title.textContent = labels["macro.title"];
    panel.note.textContent = data.series.length
      ? labels["macro.note"] : labels["macro.empty"];
    panel.grid.innerHTML = "";
    panel.chart.innerHTML = "";
    if (!data.series.length) {
      return;
    }
    const visible = data.series.some(function (serie) {
      return serie.id === state.selected;
    });
    if (!visible) {
      state.selected = data.series[0].id;
    }
    data.series.forEach(function (serie) {
      panel.grid.appendChild(card(serie, labels));
    });
    detailChart();
    renderRates(panel, rates, labels);
  }

  return {render: render};
})();
