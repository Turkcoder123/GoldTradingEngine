/* Candlestick chart with a volume strip (SVG, no dependencies). */
"use strict";

const ChartCandle = (function () {
  const PADDING = {top: 12, right: 58, bottom: 26, left: 6};
  const VOLUME_HEIGHT = 54;
  const VOLUME_GAP = 16;
  const HEIGHT = 340;
  const UP = "#3fb950";
  const DOWN = "#f85149";

  function drawGrid(svg, plot, yPrice, min, max) {
    ChartCore.ticks(min, max, 5).forEach(function (value) {
      const y = yPrice(value);
      svg.appendChild(ChartCore.el("line", {
        x1: plot.left, x2: plot.right, y1: y, y2: y, class: "chart-grid"
      }));
      ChartCore.text(svg, plot.right + 6, y + 4,
                     ChartCore.fmtValue(value), {anchor: "start"});
    });
  }

  function drawDayLabels(svg, bars, plot, band) {
    const step = Math.max(1, Math.ceil(bars.length / 6));
    bars.forEach(function (bar, index) {
      if (index % step !== 0 && index !== bars.length - 1) {
        return;
      }
      const center = plot.left + band * (index + 0.5);
      ChartCore.text(svg, center, plot.bottom + 18,
                     ChartCore.fmtDay(bar.day));
    });
  }

  function drawBar(svg, bar, center, bodyWidth, yPrice, yVolume, volumeBottom) {
    const colour = bar.close >= bar.open ? UP : DOWN;
    svg.appendChild(ChartCore.el("line", {
      x1: center, x2: center, y1: yPrice(bar.high), y2: yPrice(bar.low),
      stroke: colour, class: "candle-wick"
    }));
    const top = Math.min(yPrice(bar.open), yPrice(bar.close));
    const height = Math.max(1, Math.abs(yPrice(bar.close) - yPrice(bar.open)));
    svg.appendChild(ChartCore.el("rect", {
      x: center - bodyWidth / 2, y: top, width: bodyWidth, height: height,
      fill: colour, class: "candle-body"
    }));
    const volumeTop = yVolume(bar.volume);
    svg.appendChild(ChartCore.el("rect", {
      x: center - bodyWidth / 2, y: volumeTop, width: bodyWidth,
      height: Math.max(0, volumeBottom - volumeTop), fill: colour,
      class: "candle-volume"
    }));
  }

  function tipContent(bar, labels) {
    return "<b>" + bar.day + "</b>" +
      ChartCore.row(labels.open, ChartCore.fmtValue(bar.open)) +
      ChartCore.row(labels.high, ChartCore.fmtValue(bar.high)) +
      ChartCore.row(labels.low, ChartCore.fmtValue(bar.low)) +
      ChartCore.row(labels.close, ChartCore.fmtValue(bar.close)) +
      ChartCore.row(labels.volume, ChartCore.fmtValue(bar.volume, 2)) +
      ChartCore.row(labels.bars, ChartCore.fmtValue(bar.count, 0));
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
    const plot = {
      left: PADDING.left,
      right: width - PADDING.right,
      top: PADDING.top,
      bottom: HEIGHT - PADDING.bottom - VOLUME_HEIGHT - VOLUME_GAP
    };
    const volumeBottom = HEIGHT - PADDING.bottom;
    const volumeTop = plot.bottom + VOLUME_GAP;
    let min = Math.min.apply(null, bars.map(function (bar) { return bar.low; }));
    let max = Math.max.apply(null, bars.map(function (bar) { return bar.high; }));
    const padding = (max - min) * 0.06 || 1;
    const yPrice = ChartCore.linear([min - padding, max + padding],
                                    [plot.bottom, plot.top]);
    const maxVolume = Math.max.apply(null, bars.map(function (bar) {
      return bar.volume;
    })) || 1;
    const yVolume = ChartCore.linear([0, maxVolume], [volumeBottom, volumeTop]);
    const band = (plot.right - plot.left) / bars.length;
    const bodyWidth = Math.max(1, Math.min(14, band * 0.62));

    drawGrid(svg, plot, yPrice, min - padding, max + padding);
    drawDayLabels(svg, bars, plot, band);
    const geometry = {plot: plot, band: band, yPrice: yPrice,
                      count: bars.length};
    ChartSmc.drawZones(svg, geometry, overlays);
    ChartCore.text(svg, plot.left, volumeTop - 5, labels.volume,
                   {anchor: "start", className: "chart-label dim"});
    bars.forEach(function (bar, index) {
      drawBar(svg, bar, plot.left + band * (index + 0.5), bodyWidth,
              yPrice, yVolume, volumeBottom);
    });
    ChartSmc.drawLevels(svg, geometry, overlays);

    const crosshair = ChartCore.el("line", {
      x1: 0, x2: 0, y1: plot.top, y2: volumeBottom,
      class: "chart-crosshair", opacity: 0
    });
    svg.appendChild(crosshair);
    const overlay = ChartCore.el("rect", {
      x: plot.left, y: plot.top,
      width: plot.right - plot.left, height: volumeBottom - plot.top,
      fill: "transparent", class: "chart-overlay"
    });
    svg.appendChild(overlay);
    overlay.addEventListener("mousemove", function (event) {
      const bounds = svg.getBoundingClientRect();
      const scale = width / bounds.width;
      const x = (event.clientX - bounds.left) * scale;
      const index = Math.min(bars.length - 1,
                             Math.max(0, Math.floor((x - plot.left) / band)));
      const bar = bars[index];
      const center = plot.left + band * (index + 0.5);
      crosshair.setAttribute("x1", center);
      crosshair.setAttribute("x2", center);
      crosshair.setAttribute("opacity", 1);
      ChartCore.showTooltip(container, tipContent(bar, labels),
                            event.clientX - bounds.left,
                            event.clientY - bounds.top);
    });
    overlay.addEventListener("mouseleave", function () {
      crosshair.setAttribute("opacity", 0);
      ChartCore.hideTooltip(container);
    });
  }

  return {render: render};
})();
