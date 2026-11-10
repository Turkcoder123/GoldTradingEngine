/* Candle and study primitives: wick, body, volume, EMA line and the tip. */
"use strict";

const ChartSeries = (function () {
  const UP = "#3fb950";
  const DOWN = "#f85149";
  const LIVE = "#e3b341";

  function colourOf(bar) {
    return bar.close >= bar.open ? UP : DOWN;
  }

  function liveColour(bar) {
    return bar.live ? LIVE : colourOf(bar);
  }

  function wick(svg, bar, center, yPrice) {
    svg.appendChild(ChartCore.el("line", {
      x1: center, x2: center, y1: yPrice(bar.high), y2: yPrice(bar.low),
      stroke: liveColour(bar),
      class: bar.live ? "candle-wick live" : "candle-wick"
    }));
  }

  function body(svg, bar, center, width, yPrice) {
    const top = Math.min(yPrice(bar.open), yPrice(bar.close));
    const height = Math.max(1.5, Math.abs(yPrice(bar.close) - yPrice(bar.open)));
    const attrs = {
      x: center - width / 2,
      y: top,
      width: width,
      height: height,
      class: bar.live ? "candle-body live" : "candle-body"
    };
    if (bar.live) {
      attrs.stroke = LIVE;
    } else {
      attrs.fill = colourOf(bar);
    }
    svg.appendChild(ChartCore.el("rect", attrs));
  }

  function volume(svg, bar, center, width, yVolume, volumeBottom) {
    if (!bar.volume) {
      return;
    }
    const top = yVolume(bar.volume);
    svg.appendChild(ChartCore.el("rect", {
      x: center - width / 2, y: top, width: width,
      height: Math.max(0, volumeBottom - top),
      fill: liveColour(bar),
      class: bar.live ? "candle-volume live" : "candle-volume"
    }));
  }

  function emaLine(svg, values, frame, colour) {
    const points = [];
    values.forEach(function (value, index) {
      if (value === null || value === undefined || !isFinite(value)) {
        return;
      }
      const x = frame.plot.left + frame.band * (index + 0.5);
      points.push(x.toFixed(1) + "," + frame.yPrice(value).toFixed(1));
    });
    if (points.length < 2) {
      return;
    }
    svg.appendChild(ChartCore.el("polyline", {
      points: points.join(" "), fill: "none", stroke: colour,
      "stroke-width": 1.3, "stroke-opacity": 0.9, class: "chart-ema"
    }));
  }

  function tip(bar, labels) {
    const rows = [
      "<b>" + (bar.time || bar.day) + "</b>",
      ChartCore.row(labels.open, ChartCore.fmtValue(bar.open)),
      ChartCore.row(labels.high, ChartCore.fmtValue(bar.high)),
      ChartCore.row(labels.low, ChartCore.fmtValue(bar.low)),
      ChartCore.row(labels.close, ChartCore.fmtValue(bar.close)),
      ChartCore.row(labels.volume, ChartCore.fmtValue(bar.volume, 2)),
      ChartCore.row(labels.bars, ChartCore.fmtValue(bar.count, 0))
    ];
    if (bar.live) {
      rows.push('<div class="tip-row live"><span>' + labels.live +
                "</span><b>" + labels.live + "</b></div>");
    }
    return rows.join("");
  }

  return {
    colourOf: colourOf,
    liveColour: liveColour,
    wick: wick,
    body: body,
    volume: volume,
    emaLine: emaLine,
    tip: tip,
    LIVE: LIVE
  };
})();
