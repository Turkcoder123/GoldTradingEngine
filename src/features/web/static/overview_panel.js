/* Overview panel: totals, one card per series and the two chip rows. */
"use strict";

const DashboardOverviewPanel = (function () {
  const RANGES = [[1, "price.range.1m"], [3, "price.range.3m"],
                  [6, "price.range.6m"], [13, "price.range.1y"],
                  [0, "price.range.all"]];

  function chip(caption, active, onClick) {
    const button = DomKit.element("button", "chip" + (active ? " active" : ""),
                                  caption);
    button.type = "button";
    button.addEventListener("click", onClick);
    return button;
  }

  function kpiRows(data, labels) {
    const totals = data.totals;
    const ages = data.series.filter(function (card) {
      return card.files;
    }).map(function (card) {
      return card.stale_minutes;
    });
    const freshest = ages.length ? Math.min.apply(null, ages) : null;
    return [
      [labels["kpi.series"], String(totals.series)],
      [labels["kpi.files"], String(totals.files)],
      [labels["kpi.size"], ChartCore.fmtValue(totals.size_mb, 1) + " MB"],
      [labels["kpi.coverage"], (totals.first_bar || "-").slice(0, 10) + " -> " +
                              (totals.last_bar || "-").slice(0, 10)],
      [labels["kpi.last_bar"], totals.last_bar || "-"],
      [labels["kpi.age"], freshest === null ? "-"
        : labels["kpi.age_value"].replace("{value}",
                                          ChartCore.fmtValue(freshest, 0))]
    ];
  }

  function metaRow(name, value) {
    const row = DomKit.element("div", "meta-row");
    row.appendChild(DomKit.element("dt", "", name));
    row.appendChild(DomKit.element("dd", "", value));
    return row;
  }

  function seriesCard(card, labels, options) {
    const node = DomKit.element("button", "series-card");
    node.type = "button";
    if (card.key === options.selectedKey) {
      node.classList.add("active");
    }
    const head = DomKit.element("div", "card-head");
    head.appendChild(DomKit.element("span", "card-instrument",
                                    card.instrument));
    head.appendChild(DomKit.element("span", "card-key", card.key));
    node.appendChild(head);
    const value = DomKit.element(
      "p", "card-value",
      card.last_close === null || card.last_close === undefined
        ? "-" : ChartCore.fmtValue(card.last_close));
    if (card.day_change_pct !== null && card.day_change_pct !== undefined) {
      value.appendChild(DomKit.element(
        "span", "change " + (card.day_change_pct >= 0 ? "up" : "down"),
        ChartCore.fmtPercent(card.day_change_pct)));
    }
    node.appendChild(value);
    const meta = DomKit.element("dl", "card-meta");
    meta.appendChild(metaRow(labels["card.files"],
                             ChartCore.fmtValue(card.files, 0)));
    meta.appendChild(metaRow(labels["card.size"],
                             ChartCore.fmtValue(card.size_mb, 1) + " MB"));
    meta.appendChild(metaRow(labels["card.stale"],
                             (card.last_bar || "-").slice(0, 16)));
    node.appendChild(meta);
    node.appendChild(DomKit.element(
      "span", "card-range",
      (card.first_bar || "-").slice(0, 10) + " -> " +
      (card.last_bar || "-").slice(0, 10)));
    node.addEventListener("click", function () {
      options.onSelectSeries(card.key);
    });
    return node;
  }

  function render(panel, data, labels, options) {
    DomKit.keyValueStrip(panel.kpis, kpiRows(data, labels));
    panel.grid.innerHTML = "";
    data.series.forEach(function (card) {
      panel.grid.appendChild(seriesCard(card, labels, options));
    });
    panel.seriesChips.innerHTML = "";
    data.series.forEach(function (card) {
      panel.seriesChips.appendChild(chip(
        card.instrument, card.key === options.selectedKey, function () {
          options.onSelectSeries(card.key);
        }));
    });
    panel.rangeChips.innerHTML = "";
    RANGES.forEach(function (entry) {
      panel.rangeChips.appendChild(chip(
        labels[entry[1]], entry[0] === options.months, function () {
          options.onSelectRange(entry[0]);
        }));
    });
  }

  return {render: render};
})();
