/* Tiny inline chart for the macro cards: no axes, no dependencies. */
"use strict";

const Sparkline = (function () {
  const DEFAULT_COLOR = "#e3b341";

  function render(container, values, options) {
    ChartCore.clear(container);
    const settings = options || {};
    const width = Math.max(60, container.clientWidth || 160);
    const height = settings.height || 38;
    const svg = ChartCore.makeSvg(width, height);
    svg.setAttribute("class", "spark-svg");
    container.appendChild(svg);
    const points = values.filter(function (value) {
      return value !== null && isFinite(value);
    });
    if (points.length < 2) {
      return;
    }
    let min = Math.min.apply(null, points);
    let max = Math.max.apply(null, points);
    if (min === max) {
      min -= 1;
      max += 1;
    }
    const colour = settings.color || DEFAULT_COLOR;
    const xScale = ChartCore.linear([0, points.length - 1], [1, width - 1]);
    const yScale = ChartCore.linear([min, max], [height - 2, 2]);
    const path = points.map(function (value, index) {
      return (index ? "L" : "M") + xScale(index).toFixed(1) + " " +
             yScale(value).toFixed(1);
    }).join(" ");
    svg.appendChild(ChartCore.el("path", {
      d: path, fill: "none", stroke: colour, class: "spark-path"
    }));
    svg.appendChild(ChartCore.el("circle", {
      cx: xScale(points.length - 1), cy: yScale(points[points.length - 1]),
      r: 2.2, fill: colour
    }));
  }

  return {render: render};
})();
