/* Alternative sources: ETF tonnage, GVZ and the newest Fed documents. */
"use strict";

const DashboardAltPanel = (function () {
  function valueText(value, suffix) {
    if (value === null || value === undefined) {
      return "-";
    }
    return ChartCore.fmtValue(value, 2) + (suffix || "");
  }

  function changeText(value) {
    return value === null || value === undefined
      ? "-" : ChartCore.fmtPercent(value);
  }

  function summaryRows(data, labels) {
    const rows = [];
    data.etf.forEach(function (row) {
      rows.push([
        labels["alt.tonnes"] + " " + row.key.toUpperCase(),
        valueText(row.tonnes, " t") + "   " + changeText(row.change_pct)
      ]);
    });
    rows.push([
      data.volatility.key,
      valueText(data.volatility.close) + "   " +
        changeText(data.volatility.change_pct)
    ]);
    rows.push([
      labels["alt.documents"],
      ChartCore.fmtValue(data.fed.rows, 0) + " (" +
        ChartCore.fmtValue(data.fed.texts, 0) + " " +
        labels["alt.texts"] + ")"
    ]);
    return rows;
  }

  function drawChart(container, points, name, colour, labels) {
    ChartCore.clear(container);
    if (!points || !points.length) {
      ChartCore.emptyNote(container, labels["alt.empty"]);
      return;
    }
    ChartLine.render(container, {
      series: [{name: name, color: colour, points: points}],
      height: 220,
      labels: {empty: labels["alt.empty"]}
    });
  }

  function documentTable(data, labels) {
    const table = DomKit.element("table", "doc-table");
    const head = DomKit.element("tr");
    [labels["alt.date"], labels["alt.kind"], labels["alt.title"],
     labels["alt.chars"]].forEach(function (title) {
      head.appendChild(DomKit.element("th", "", title));
    });
    const thead = DomKit.element("thead");
    thead.appendChild(head);
    table.appendChild(thead);
    const body = DomKit.element("tbody");
    data.fed.documents.forEach(function (entry) {
      const row = DomKit.element("tr");
      row.appendChild(DomKit.element("td", "", entry.date || "-"));
      row.appendChild(DomKit.element("td", "",
        labels["alt.kind." + entry.kind] || entry.kind || "-"));
      const cell = DomKit.element("td");
      if (entry.url) {
        const link = DomKit.element("a", "", entry.title || entry.url);
        link.href = entry.url;
        link.target = "_blank";
        link.rel = "noopener";
        cell.appendChild(link);
      } else {
        cell.textContent = entry.title || "-";
      }
      row.appendChild(cell);
      row.appendChild(DomKit.element("td", "num",
                                     ChartCore.fmtValue(entry.chars, 0)));
      body.appendChild(row);
    });
    table.appendChild(body);
    return table;
  }

  function render(panel, data, labels) {
    panel.title.textContent = labels["section.alt"];
    panel.tonnesTitle.textContent = labels["alt.tonnes_title"];
    panel.gvzTitle.textContent = labels["alt.gvz_title"];
    if (!data) {
      panel.note.textContent = labels["alt.empty"] + " " + labels["alt.hint"];
      return;
    }
    panel.note.textContent = labels["alt.note"];
    DomKit.keyValueStrip(panel.summary, summaryRows(data, labels));
    const gld = data.etf.filter(function (row) {
      return row.key === "gld";
    })[0];
    drawChart(panel.tonnesChart, gld ? gld.points : [],
              gld ? gld.label : "GLD", ChartCore.PALETTE[0], labels);
    drawChart(panel.gvzChart, data.volatility.points, data.volatility.key,
              ChartCore.PALETTE[1], labels);
    panel.documents.innerHTML = "";
    if (data.fed.documents.length) {
      panel.documents.appendChild(
        DomKit.element("h3", "sub-title", labels["alt.documents"]));
      panel.documents.appendChild(documentTable(data, labels));
    }
  }

  return {render: render};
})();
