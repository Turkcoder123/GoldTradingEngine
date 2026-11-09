/* Multi-series line chart with a shared date axis (SVG, no dependencies). */
"use strict";

const ChartLine = (function () {
  const PADDING = {top: 14, right: 58, bottom: 28, left: 6};
  const HEIGHT = 260;

  function toSeries(serie) {
    const points = serie.points.map(function (point) {
      return [Date.parse(point[0] + "T00:00:00Z"), point[1]];
    }).filter(function (point) {
      return isFinite(point[0]) && point[1] !== null && isFinite(point[1]);
    });
    return {name: serie.name, color: serie.color, points: points};
  }

  function pathOf(points, xScale, yScale) {
    return points.map(function (point, index) {
      return (index ? "L" : "M") + xScale(point[0]).toFixed(2) +
             " " + yScale(point[1]).toFixed(2);
    }).join(" ");
  }

  function timeLabel(ms) {
    return ChartCore.fmtDay(new Date(ms).toISOString().slice(0, 10));
  }

  function drawAxes(svg, plot, yScale, timeScale, minTime, maxTime, config) {
    ChartCore.ticks(config.min, config.max, 5).forEach(function (value) {
      const y = yScale(value);
      svg.appendChild(ChartCore.el("line", {
        x1: plot.left, x2: plot.right, y1: y, y2: y, class: "chart-grid"
      }));
      ChartCore.text(svg, plot.right + 6, y + 4,
                     config.yFormat(value), {anchor: "start"});
    });
    const count = 5;
    for (let step = 0; step <= count; step += 1) {
      const at = minTime + ((maxTime - minTime) * step) / count;
      ChartCore.text(svg, timeScale(at), plot.bottom + 18, timeLabel(at),
                     {anchor: step === 0 ? "start"
                              : step === count ? "end" : "middle"});
    }
  }

  function nearest(points, time) {
    let best = null;
    points.forEach(function (point) {
      if (!best || Math.abs(point[0] - time) < Math.abs(best[0] - time)) {
        best = point;
      }
    });
    return best;
  }

  function tooltip(series, time) {
    let html = "";
    const found = [];
    series.forEach(function (serie) {
      const point = nearest(serie.points, time);
      if (!point) { return; }
      found.push([serie, point]);
    });
    if (!found.length) { return ""; }
    html += "<b>" + new Date(found[0][1][0]).toISOString().slice(0, 10) + "</b>";
    found.forEach(function (entry) {
      const serie = entry[0];
      html += '<div class="tip-row"><span><i class="dot" style="background:' +
              serie.color + '"></i>' + serie.name + "</span><b>" +
              entry[1][1].toLocaleString("en-US",
                {maximumFractionDigits: 3}) + "</b></div>";
    });
    return html;
  }

  function render(container, rawConfig) {
    ChartCore.clear(container);
    const config = Object.assign({}, rawConfig);
    const width = Math.max(300, container.clientWidth || 720);
    const height = config.height || HEIGHT;
    const svg = ChartCore.makeSvg(width, height);
    container.appendChild(svg);
    const series = (config.series || []).map(toSeries).filter(function (serie) {
      return serie.points.length > 0;
    });
    if (!series.length) {
      ChartCore.emptyNote(container, config.labels.empty);
      return;
    }
    const values = [];
    const times = [];
    series.forEach(function (serie) {
      serie.points.forEach(function (point) {
        values.push(point[1]);
        times.push(point[0]);
      });
    });
    let min = Math.min.apply(null, values);
    let max = Math.max.apply(null, values);
    if (config.zeroLine) {
      min = Math.min(min, 0);
      max = Math.max(max, 0);
    }
    const padding = (max - min) * 0.08 || 1;
    config.min = min - padding;
    config.max = max + padding;
    config.yFormat = config.yFormat || function (value) {
      return ChartCore.fmtValue(value, ChartCore.digitsFor(value));
    };
    const plot = {
      left: PADDING.left, right: width - PADDING.right,
      top: PADDING.top, bottom: height - PADDING.bottom
    };
    const yScale = ChartCore.linear([config.min, config.max],
                                    [plot.bottom, plot.top]);
    const minTime = Math.min.apply(null, times);
    const maxTime = Math.max.apply(null, times);
    const timeScale = ChartCore.linear([minTime, maxTime],
                                       [plot.left, plot.right]);
    drawAxes(svg, plot, yScale, timeScale, minTime, maxTime, config);
    series.forEach(function (serie) {
      svg.appendChild(ChartCore.el("path", {
        d: pathOf(serie.points, timeScale, yScale),
        stroke: serie.color, fill: "none", class: "line-path"
      }));
    });
    const crosshair = ChartCore.el("line", {
      x1: 0, x2: 0, y1: plot.top, y2: plot.bottom,
      class: "chart-crosshair", opacity: 0
    });
    svg.appendChild(crosshair);
    const overlay = ChartCore.el("rect", {
      x: plot.left, y: plot.top, width: plot.right - plot.left,
      height: plot.bottom - plot.top, fill: "transparent",
      class: "chart-overlay"
    });
    svg.appendChild(overlay);
    overlay.addEventListener("mousemove", function (event) {
      const bounds = svg.getBoundingClientRect();
      const scale = width / bounds.width;
      const x = (event.clientX - bounds.left) * scale;
      const time = minTime + ((x - plot.left) / (plot.right - plot.left)) *
                   (maxTime - minTime);
      crosshair.setAttribute("x1", timeScale(time));
      crosshair.setAttribute("x2", timeScale(time));
      crosshair.setAttribute("opacity", 1);
      ChartCore.showTooltip(container, tooltip(series, time),
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
