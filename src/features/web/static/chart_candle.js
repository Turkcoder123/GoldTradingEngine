/* Candlestick chart: price grid, live overlay, volume strip, crosshair tip. */
"use strict";

const ChartCandle = (function () {
  const PADDING = {top: 14, right: 64, bottom: 30, left: 8};
  const VOLUME_HEIGHT = 52;
  const VOLUME_GAP = 18;
  const HEIGHT = 360;
  const UP = "#3fb950";
  const DOWN = "#f85149";
  const LIVE = "#e3b341";

  function colourOf(bar) {
    return bar.close >= bar.open ? UP : DOWN;
  }

  function drawWick(svg, bar, center, yPrice) {
    svg.appendChild(ChartCore.el("line", {
      x1: center, x2: center, y1: yPrice(bar.high), y2: yPrice(bar.low),
      stroke: bar.live ? LIVE : colourOf(bar),
      class: bar.live ? "candle-wick live" : "candle-wick"
    }));
  }

  function drawBody(svg, bar, center, bodyWidth, yPrice) {
    const top = Math.min(yPrice(bar.open), yPrice(bar.close));
    const height = Math.max(1.5, Math.abs(yPrice(bar.close) - yPrice(bar.open)));
    const attrs = {
      x: center - bodyWidth / 2,
      y: top,
      width: bodyWidth,
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

  function drawVolume(svg, bar, center, bodyWidth, yVolume, volumeBottom) {
    if (!bar.volume) {
      return;
    }
    const top = yVolume(bar.volume);
    svg.appendChild(ChartCore.el("rect", {
      x: center - bodyWidth / 2, y: top, width: bodyWidth,
      height: Math.max(0, volumeBottom - top),
      fill: bar.live ? LIVE : colourOf(bar),
      class: bar.live ? "candle-volume live" : "candle-volume"
    }));
  }

  function tipContent(bar, labels) {
    const rows = [
      "<b>" + bar.day + "</b>",
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

  function frameFor(bars, width) {
    const plot = {
      left: PADDING.left,
      right: width - PADDING.right,
      top: PADDING.top,
      bottom: HEIGHT - PADDING.bottom - VOLUME_HEIGHT - VOLUME_GAP
    };
    let min = Infinity;
    let max = -Infinity;
    bars.forEach(function (bar) {
      min = Math.min(min, bar.low);
      max = Math.max(max, bar.high);
    });
    const padding = (max - min) * 0.06 || Math.max(1, Math.abs(max) * 0.001);
    const volumeBottom = HEIGHT - PADDING.bottom;
    const volumeTop = plot.bottom + VOLUME_GAP;
    const maxVolume = Math.max.apply(null, bars.map(function (bar) {
      return bar.volume || 0;
    })) || 1;
    return {
      plot: plot,
      band: (plot.right - plot.left) / bars.length,
      yPrice: ChartCore.linear([min - padding, max + padding],
                               [plot.bottom, plot.top]),
      min: min - padding,
      max: max + padding,
      count: bars.length,
      yVolume: ChartCore.linear([0, maxVolume], [volumeBottom, volumeTop]),
      volumeBottom: volumeBottom,
      volumeTop: volumeTop
    };
  }

  function draw(svg, container, bars, labels, overlays, width) {
    const frame = frameFor(bars, width);
    ChartAxes.priceGrid(svg, frame.plot, frame.yPrice, frame.min, frame.max);
    ChartAxes.timeAxis(svg, bars, frame.plot, frame.band);
    const last = bars[bars.length - 1];
    ChartAxes.lastPrice(svg, frame.plot, frame.yPrice, last.close,
                        last.live ? LIVE : colourOf(last));
    ChartSmc.drawZones(svg, frame, overlays);
    ChartCore.text(svg, frame.plot.left, frame.volumeTop - 5, labels.volume,
                   {anchor: "start", className: "chart-label dim"});
    const bodyWidth = Math.max(1, Math.min(14, frame.band * 0.62));
    bars.forEach(function (bar, index) {
      const center = frame.plot.left + frame.band * (index + 0.5);
      drawWick(svg, bar, center, frame.yPrice);
      drawBody(svg, bar, center, bodyWidth, frame.yPrice);
      drawVolume(svg, bar, center, bodyWidth, frame.yVolume,
                 frame.volumeBottom);
    });
    ChartSmc.drawLevels(svg, frame, overlays);

    const guide = ChartAxes.crosshair(svg, frame.plot);
    const overlay = ChartCore.el("rect", {
      x: frame.plot.left, y: frame.plot.top,
      width: frame.plot.right - frame.plot.left,
      height: frame.volumeBottom - frame.plot.top,
      fill: "transparent", class: "chart-overlay"
    });
    svg.appendChild(overlay);
    overlay.addEventListener("mousemove", function (event) {
      const bounds = svg.getBoundingClientRect();
      const scale = width / bounds.width;
      const x = (event.clientX - bounds.left) * scale;
      const y = (event.clientY - bounds.top) * scale;
      const index = Math.min(bars.length - 1, Math.max(
        0, Math.floor((x - frame.plot.left) / frame.band)));
      const bar = bars[index];
      const center = frame.plot.left + frame.band * (index + 0.5);
      guide.move(center, Math.min(Math.max(y, frame.plot.top), frame.plot.bottom),
                 ChartCore.fmtValue(bar.close));
      ChartCore.showTooltip(container, tipContent(bar, labels),
                            event.clientX - bounds.left,
                            event.clientY - bounds.top);
    });
    overlay.addEventListener("mouseleave", function () {
      guide.hide();
      ChartCore.hideTooltip(container);
    });
  }

  function render(container, bars, labels, overlays) {
    ChartCore.clear(container);
    const width = Math.max(300, container.clientWidth || 720);
    const svg = ChartCore.makeSvg(width, HEIGHT);
    container.appendChild(svg);
    if (!bars.length) {
      ChartCore.emptyNote(container, labels.empty);
      return;
    }
    draw(svg, container, bars, labels, overlays, width);
  }

  return {render: render};
})();

