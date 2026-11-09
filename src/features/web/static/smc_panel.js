/* SMC panel: window summary, overlay toggles and the newest structures. */
"use strict";

const DashboardSmcPanel = (function () {
  const RECENT_LIMIT = 10;
  const BREAKS = ["BOS", "CHOCH"];
  const GROUPS = [["structure", "smc.breaks"], ["zones", "smc.zones"],
                  ["sweeps", "smc.sweeps"], ["swings", "smc.swings"]];

  function countPatterns(summary, patterns) {
    return patterns.reduce(function (total, pattern) {
      const bucket = summary[pattern] || {};
      return total + Object.keys(bucket).reduce(function (sum, direction) {
        return sum + bucket[direction];
      }, 0);
    }, 0);
  }

  function parametersText(data, labels) {
    const parameters = data.parameters;
    return labels["smc.parameters_value"]
      .replace("{left}", parameters.left_bars)
      .replace("{right}", parameters.right_bars)
      .replace("{lookback}", parameters.ob_lookback);
  }

  function summaryRows(data, labels) {
    const summary = data.summary || {};
    return [
      [labels["smc.timeframe"], labels["smc.timeframe." + data.timeframe] ||
                                data.timeframe],
      [labels["smc.window"], (data.bars.first_day || "-") + " -> " +
                             (data.bars.last_day || "-")],
      [labels["smc.bars"], ChartCore.fmtValue(data.bars.count, 0)],
      [labels["smc.breaks"],
       ChartCore.fmtValue(countPatterns(summary, BREAKS), 0)],
      [labels["smc.zones"],
       ChartCore.fmtValue(countPatterns(summary, ["FVG", "ORDER_BLOCK"]), 0)],
      [labels["smc.sweeps"],
       ChartCore.fmtValue(countPatterns(summary, ["LIQUIDITY_SWEEP"]), 0)],
      [labels["smc.swings"],
       ChartCore.fmtValue(countPatterns(summary, ["SWING_HIGH", "SWING_LOW"]),
                          0)],
      [labels["smc.parameters"], parametersText(data, labels)]
    ];
  }

  function toggleChips(target, groups, labels, onToggle) {
    target.innerHTML = "";
    GROUPS.forEach(function (group) {
      const active = Boolean(groups[group[0]]);
      const button = DomKit.element("button",
                                    "chip" + (active ? " active" : ""),
                                    labels[group[1]]);
      button.type = "button";
      button.addEventListener("click", function () {
        onToggle(group[0], !active);
      });
      target.appendChild(button);
    });
  }

  function stateText(item, labels) {
    if (item.zone_low === null || item.zone_low === undefined) {
      return "-";
    }
    return item.is_filled ? labels["smc.state.filled"]
                          : labels["smc.state.open"];
  }

  function eventRow(item, labels) {
    const row = DomKit.element("tr");
    row.appendChild(DomKit.element("td", "", item.detected_at || "-"));
    row.appendChild(DomKit.element(
      "td", "", labels["smc.pattern." + item.pattern] || item.pattern));
    row.appendChild(DomKit.element(
      "td", "", labels["smc.direction." + item.direction] || item.direction));
    row.appendChild(DomKit.element("td", "num",
                                   ChartCore.fmtValue(item.level)));
    row.appendChild(DomKit.element("td", "", stateText(item, labels)));
    return row;
  }

  function eventTable(events, labels) {
    const table = DomKit.element("table", "smc-table");
    const head = DomKit.element("tr");
    ["smc.column.bar", "smc.column.pattern", "smc.column.direction",
     "smc.column.level", "smc.column.state"].forEach(function (key) {
      head.appendChild(DomKit.element("th", "", labels[key]));
    });
    const thead = DomKit.element("thead");
    thead.appendChild(head);
    table.appendChild(thead);
    const body = DomKit.element("tbody");
    events.slice().reverse().slice(0, RECENT_LIMIT).forEach(function (item) {
      body.appendChild(eventRow(item, labels));
    });
    table.appendChild(body);
    return table;
  }

  function render(panel, data, labels, options) {
    panel.title.textContent = labels["section.smc"];
    panel.events.innerHTML = "";
    if (!data) {
      panel.note.textContent = labels["smc.empty"] + " " + labels["smc.hint"];
      panel.toggles.innerHTML = "";
      panel.summary.innerHTML = "";
      return;
    }
    panel.note.textContent = labels["smc.note"];
    DomKit.keyValueStrip(panel.summary, summaryRows(data, labels));
    toggleChips(panel.toggles, options.groups, labels, options.onToggle);
    panel.events.appendChild(
      DomKit.element("h3", "sub-title", labels["smc.recent"]));
    if (!data.events.length) {
      panel.events.appendChild(
        DomKit.element("p", "chart-empty", labels["smc.empty"]));
      return;
    }
    panel.events.appendChild(eventTable(data.events, labels));
  }

  return {render: render};
})();
