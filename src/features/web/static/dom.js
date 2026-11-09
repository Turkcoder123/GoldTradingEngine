/* Small DOM helpers shared by the dashboard panels (no dependencies). */
"use strict";

const DomKit = (function () {
  function element(tag, className, text) {
    const node = document.createElement(tag);
    if (className) {
      node.className = className;
    }
    if (text !== undefined) {
      node.textContent = text;
    }
    return node;
  }

  function labelValueRow(list, name, value) {
    const row = element("li");
    row.appendChild(element("span", "", name));
    row.appendChild(element("b", "", value));
    list.appendChild(row);
  }

  function statCard(title, value, change, rows) {
    const card = element("div", "stat");
    card.appendChild(element("h3", "", title));
    const line = element("p", "stat-value");
    line.appendChild(document.createTextNode(value));
    if (change) {
      line.appendChild(element("span", "change " + change.className,
                               change.text));
    }
    card.appendChild(line);
    const list = element("ul", "stat-meta");
    rows.forEach(function (row) {
      labelValueRow(list, row[0], row[1]);
    });
    card.appendChild(list);
    return card;
  }

  function legend(series) {
    const wrap = element("div", "legend");
    series.forEach(function (serie) {
      const item = element("span", "legend-item");
      const dot = element("i", "dot");
      dot.style.background = serie.color;
      item.appendChild(dot);
      item.appendChild(document.createTextNode(serie.name));
      wrap.appendChild(item);
    });
    return wrap;
  }

  function signed(value, format) {
    if (value === null || value === undefined) {
      return "-";
    }
    return (value > 0 ? "+" : "") + format(value);
  }

  function keyValueStrip(target, rows) {
    target.innerHTML = "";
    rows.forEach(function (row) {
      const cell = element("div", "kv");
      cell.appendChild(element("span", "kv-label", row[0]));
      cell.appendChild(element("b", "kv-value", row[1]));
      target.appendChild(cell);
    });
  }

  return {
    element: element,
    statCard: statCard,
    legend: legend,
    signed: signed,
    keyValueStrip: keyValueStrip
  };
})();
