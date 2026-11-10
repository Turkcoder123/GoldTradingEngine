/* Chart controls: the timeframe and range chip rows of the price panel. */
"use strict";

const ChartControls = (function () {
  const INTERVALS = [["1m", "1m"], ["5m", "5m"], ["15m", "15m"],
                     ["30m", "30m"], ["1h", "1h"], ["4h", "4h"],
                     ["1d", "1D"]];
  const RANGES = [[1, "1D"], [7, "1W"], [30, "1M"], [90, "3M"],
                  [365, "1Y"], [0, "All"]];

  function chip(caption, active, onClick) {
    const button = DomKit.element("button", "chip" + (active ? " active" : ""),
                                  caption);
    button.type = "button";
    button.addEventListener("click", onClick);
    return button;
  }

  function renderIntervals(node, state, handlers) {
    node.innerHTML = "";
    INTERVALS.forEach(function (entry) {
      node.appendChild(chip(entry[1], entry[0] === state.interval,
                            function () {
                              handlers.onInterval(entry[0]);
                            }));
    });
  }

  function renderRanges(node, state, labels, handlers) {
    node.innerHTML = "";
    RANGES.forEach(function (entry) {
      const caption = entry[0] === 0 ? labels["price.range.all"] : entry[1];
      node.appendChild(chip(caption, entry[0] === state.days, function () {
        handlers.onRange(entry[0]);
      }));
    });
  }

  function renderZoom(node, labels, handlers) {
    node.innerHTML = "";
    node.appendChild(chip("−", false, handlers.onZoomOut));
    node.appendChild(chip("+", false, handlers.onZoomIn));
    node.appendChild(chip(labels["price.zoom_reset"], false, handlers.onReset));
  }

  function render(panel, state, labels, handlers) {
    renderIntervals(panel.intervalChips, state, handlers);
    renderRanges(panel.rangeChips, state, labels, handlers);
    renderZoom(panel.zoomChips, labels, handlers);
  }

  return {render: render, INTERVALS: INTERVALS, RANGES: RANGES};
})();
