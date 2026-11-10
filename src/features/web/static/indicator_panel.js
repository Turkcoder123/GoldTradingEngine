/* Indicators panel: the studies drawn over the chart, toggled as chips. */
"use strict";

const DashboardIndicatorPanel = (function () {
  const STUDIES = [
    ["volume", "price.volume"],
    ["lastPrice", "price.last_price"],
    ["ema20", "indicator.ema20"],
    ["ema50", "indicator.ema50"]
  ];
  const GROUPS = [
    ["structure", "smc.breaks"],
    ["zones", "smc.zones"],
    ["sweeps", "smc.sweeps"],
    ["swings", "smc.swings"]
  ];

  function chip(caption, active, onClick) {
    const button = DomKit.element("button", "chip" + (active ? " active" : ""),
                                  caption);
    button.type = "button";
    button.addEventListener("click", onClick);
    return button;
  }

  function render(panel, labels, chart, groups, handlers) {
    panel.title.textContent = labels["section.indicators"];
    panel.note.textContent = labels["indicators.note"];
    panel.chips.innerHTML = "";
    STUDIES.forEach(function (entry) {
      panel.chips.appendChild(chip(
        labels[entry[1]], Boolean(chart[entry[0]]), function () {
          handlers.onStudy(entry[0]);
        }));
    });
    GROUPS.forEach(function (entry) {
      panel.chips.appendChild(chip(
        labels[entry[1]], Boolean(groups[entry[0]]), function () {
          handlers.onGroup(entry[0]);
        }));
    });
  }

  return {render: render};
})();
