/* SMC overlay: zones go behind the candles, levels and markers on top. */
"use strict";

const ChartSmc = (function () {
  const BULLISH = "#3fb950";
  const BEARISH = "#f85149";
  const STRUCTURE = "#e3b341";
  const SWEEP = "#58a6ff";
  const SWING = "#8b949e";
  const SVG_NS = "http://www.w3.org/2000/svg";
  const MIN_ZONE_WIDTH = 3;
  const LABEL_GAP = 11;
  const ZONE_OPACITY = {open: 0.18, filled: 0.07};

  function patternLabel(labels, pattern) {
    return labels["smc.pattern." + pattern] || pattern;
  }

  function directionLabel(labels, direction) {
    return labels["smc.direction." + direction] || direction;
  }

  function xOf(geometry, index) {
    return geometry.plot.left + geometry.band * (index + 0.5);
  }

  function indexOf(geometry, index) {
    return Math.min(geometry.count - 1, Math.max(0, index));
  }

  function note(text) {
    const node = document.createElementNS(SVG_NS, "title");
    node.textContent = text;
    return node;
  }

  function zoneColour(direction) {
    return direction === "bullish" ? BULLISH : BEARISH;
  }

  function zoneNode(geometry, item, labels) {
    const start = xOf(geometry, indexOf(geometry, item.bar_index));
    const end = Math.max(xOf(geometry, indexOf(geometry, item.end_index)),
                         start + MIN_ZONE_WIDTH);
    const top = geometry.yPrice(item.zone_high);
    const height = Math.max(1, geometry.yPrice(item.zone_low) - top);
    const node = ChartCore.el("rect", {
      x: start, y: top, width: end - start, height: height,
      fill: zoneColour(item.direction), class: "smc-zone"
    });
    node.setAttribute("opacity",
                      item.is_filled ? ZONE_OPACITY.filled : ZONE_OPACITY.open);
    node.appendChild(note(patternLabel(labels, item.pattern) + " " +
                          directionLabel(labels, item.direction) + " " +
                          ChartCore.fmtValue(item.zone_low) + " - " +
                          ChartCore.fmtValue(item.zone_high) +
                          " (" + item.pattern_at + ")"));
    return node;
  }

  function structureLine(geometry, item, labels) {
    const x = xOf(geometry, indexOf(geometry, item.bar_index));
    const y = geometry.yPrice(item.level);
    const node = ChartCore.el("line", {
      x1: x, x2: geometry.plot.right, y1: y, y2: y,
      stroke: STRUCTURE, class: "smc-level"
    });
    node.appendChild(note(patternLabel(labels, item.pattern) + " " +
                          ChartCore.fmtValue(item.level) + " (" +
                          item.pattern_at + ")"));
    return node;
  }

  function drawStructure(svg, geometry, items, labels) {
    let lastLabel = null;
    items.forEach(function (item) {
      const node = structureLine(geometry, item, labels);
      svg.appendChild(node);
      const y = geometry.yPrice(item.level);
      if (lastLabel === null || Math.abs(lastLabel - y) >= LABEL_GAP) {
        ChartCore.text(svg, geometry.plot.right - 2, y - 3,
                       patternLabel(labels, item.pattern),
                       {anchor: "end", className: "smc-label"});
        lastLabel = y;
      }
    });
  }

  function markerNode(geometry, item, labels, colour, up) {
    const x = xOf(geometry, indexOf(geometry, item.bar_index));
    const price = item.wick_extreme === undefined ? item.level
                                                  : item.wick_extreme;
    const y = geometry.yPrice(price);
    const size = 4.5;
    const points = up
      ? [x, y - size, x - size, y + size, x + size, y + size]
      : [x, y + size, x - size, y - size, x + size, y - size];
    const node = ChartCore.el("polygon", {
      points: points.join(","), fill: colour, class: "smc-marker"
    });
    node.appendChild(note(patternLabel(labels, item.pattern) + " " +
                          directionLabel(labels, item.direction) + " (" +
                          item.pattern_at + ")"));
    return node;
  }

  function drawZones(svg, geometry, overlays) {
    if (!overlays || !overlays.groups.zones) {
      return;
    }
    overlays.events.forEach(function (item) {
      if (item.zone_low === null || item.zone_low === undefined) {
        return;
      }
      svg.appendChild(zoneNode(geometry, item, overlays.labels));
    });
  }

  function drawLevels(svg, geometry, overlays) {
    if (!overlays) {
      return;
    }
    const labels = overlays.labels;
    const events = overlays.events;
    if (overlays.groups.structure) {
      const structure = events.filter(function (item) {
        return item.pattern === "BOS" || item.pattern === "CHOCH";
      });
      drawStructure(svg, geometry, structure, labels);
    }
    if (overlays.groups.sweeps) {
      events.filter(function (item) {
        return item.pattern === "LIQUIDITY_SWEEP";
      }).forEach(function (item) {
        svg.appendChild(markerNode(geometry, item, labels, SWEEP,
                                   item.direction === "buy_side_taken"));
      });
    }
    if (overlays.groups.swings) {
      events.filter(function (item) {
        return item.pattern === "SWING_HIGH" || item.pattern === "SWING_LOW";
      }).forEach(function (item) {
        svg.appendChild(markerNode(geometry, item, labels, SWING,
                                   item.pattern === "SWING_LOW"));
      });
    }
  }

  return {drawZones: drawZones, drawLevels: drawLevels};
})();
