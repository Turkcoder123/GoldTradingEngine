/* Grouped bar chart for weekly values (SVG, no dependencies). */
"use strict";

const ChartBars = (function () {
  const PADDING = {top: 14, right: 58, bottom: 28, left: 6};
  const HEIGHT = 260;

  function drawAxes(svg, plot, yScale, config) {
    ChartCore.ticks(config.min, config.max, 5).forEach(function (value) {
      const y = yScale(value);
      svg.appendChild(ChartCore.el("line", {
        x1: plot.left, x2: plot.right, y1: y, y2: y,
        class: value === 0 ? "chart-zero" : "chart-grid"
      }));
      ChartCore.text(svg, plot.right + 6, y + 4,
                     config.yFormat(value), {anchor: "start"});
    });
  }

  function drawCategoryLabels(svg, categories, plot, band) {
    const step = Math.max(1, Math.ceil(categories.length / 6));
    categories.forEach(function (category, index) {
      if (index % step !== 0 && index !== categories.length - 1) {
        return;
      }
      ChartCore.text(svg, plot.left + band * (index + 0.5),
                     plot.bottom + 18, category.slice(5));
    });
  }

  function tooltip(categories, series, index, format) {
    let html = "<b>" + categories[index] + "</b>";
    series.forEach(function (serie) {
      const value = serie.values[index];
      html += ChartCore.row(serie.name,
                            value === null || value === undefined
                              ? "-" : format(value));
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
    const categories = config.categories || [];
    const series = config.series || [];
    const values = [];
    series.forEach(function (serie) {
      serie.values.forEach(function (value) {
        if (value !== null && isFinite(value)) { values.push(value); }
      });
    });
    if (!categories.length || !values.length) {
      ChartCore.emptyNote(container, config.labels.empty);
      return;
    }
    const min = Math.min.apply(null, values.concat([0]));
    const max = Math.max.apply(null, values.concat([0]));
    const padding = (max - min) * 0.08 || 1;
    config.min = min - padding;
    config.max = max + padding;
    config.yFormat = config.yFormat || ChartCore.fmtCompact;
    const plot = {
      left: PADDING.left, right: width - PADDING.right,
      top: PADDING.top, bottom: height - PADDING.bottom
    };
    const yScale = ChartCore.linear([config.min, config.max],
                                    [plot.bottom, plot.top]);
    const band = (plot.right - plot.left) / categories.length;
    const groupWidth = band * 0.76;
    const barWidth = Math.max(1, (groupWidth / series.length) * 0.9);
    drawAxes(svg, plot, yScale, config);
    drawCategoryLabels(svg, categories, plot, band);
    series.forEach(function (serie, seriesIndex) {
      serie.values.forEach(function (value, index) {
        if (value === null || !isFinite(value)) { return; }
        const zero = yScale(0);
        const top = Math.min(zero, yScale(value));
        const left = plot.left + band * index + (band - groupWidth) / 2 +
                     barWidth * seriesIndex;
        svg.appendChild(ChartCore.el("rect", {
          x: left, y: top, width: barWidth,
          height: Math.max(1, Math.abs(yScale(value) - zero)),
          fill: serie.color, class: "bar"
        }));
      });
    });
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
      const index = Math.min(categories.length - 1,
                             Math.max(0, Math.floor((x - plot.left) / band)));
      ChartCore.showTooltip(
        container, tooltip(categories, series, index, config.yFormat),
        event.clientX - bounds.left, event.clientY - bounds.top);
    });
    overlay.addEventListener("mouseleave", function () {
      ChartCore.hideTooltip(container);
    });
  }

  return {render: render};
})();
