/* Chart frame: grid, price axis, time axis, last price and the crosshair. */
"use strict";

const ChartAxes = (function () {
  const TAG_WIDTH = 64;
  const TAG_HEIGHT = 16;

  function priceGrid(svg, plot, yPrice, min, max) {
    ChartCore.ticks(min, max, 5).forEach(function (value) {
      const y = yPrice(value);
      svg.appendChild(ChartCore.el("line", {
        x1: plot.left, x2: plot.right, y1: y, y2: y, class: "chart-grid"
      }));
      ChartCore.text(svg, plot.right + 8, y + 4, ChartCore.fmtValue(value),
                     {anchor: "start", className: "chart-label axis"});
    });
  }

  function timeAxis(svg, bars, plot, band, labelFor) {
    const label = labelFor || function (bar) {
      return ChartCore.fmtDay(bar.day);
    };
    const step = Math.max(1, Math.ceil(bars.length / 6));
    bars.forEach(function (bar, index) {
      if (index % step !== 0 && index !== bars.length - 1) {
        return;
      }
      const center = plot.left + band * (index + 0.5);
      svg.appendChild(ChartCore.el("line", {
        x1: center, x2: center, y1: plot.bottom, y2: plot.bottom + 4,
        class: "chart-tick"
      }));
      ChartCore.text(svg, center, plot.bottom + 17, label(bar),
                     {className: "chart-label axis"});
    });
  }

  function lastPrice(svg, plot, yPrice, price, colour) {
    const y = yPrice(price);
    if (!isFinite(y)) {
      return;
    }
    svg.appendChild(ChartCore.el("line", {
      x1: plot.left, x2: plot.right, y1: y, y2: y, stroke: colour,
      class: "chart-lastline"
    }));
    const tag = ChartCore.el("g", {class: "chart-lasttag"});
    tag.appendChild(ChartCore.el("rect", {
      x: plot.left + 2, y: y - TAG_HEIGHT / 2, rx: 3, height: TAG_HEIGHT,
      width: TAG_WIDTH, fill: colour, "fill-opacity": 0.16,
      stroke: colour, "stroke-opacity": 0.55
    }));
    ChartCore.text(tag, plot.left + 2 + TAG_WIDTH / 2, y + 4,
                   ChartCore.fmtValue(price),
                   {className: "chart-label strong", anchor: "middle"});
    svg.appendChild(tag);
  }

  function crosshair(svg, plot) {
    const group = ChartCore.el("g", {class: "chart-crosshair-set",
                                     opacity: 0});
    const vertical = ChartCore.el("line", {
      class: "chart-crosshair", y1: plot.top, y2: plot.bottom
    });
    const horizontal = ChartCore.el("line", {
      class: "chart-crosshair", x1: plot.left, x2: plot.right
    });
    const tag = ChartCore.el("g", {class: "chart-crosshair-tag"});
    tag.appendChild(ChartCore.el("rect", {
      class: "chart-tag-bg", rx: 3, height: TAG_HEIGHT, width: TAG_WIDTH,
      x: plot.right - TAG_WIDTH - 2
    }));
    const label = ChartCore.text(tag, plot.right - TAG_WIDTH / 2 - 2, 0, "",
                                 {className: "chart-label strong"});
    group.appendChild(vertical);
    group.appendChild(horizontal);
    group.appendChild(tag);
    svg.appendChild(group);

    function move(x, y, priceText) {
      vertical.setAttribute("x1", x);
      vertical.setAttribute("x2", x);
      horizontal.setAttribute("y1", y);
      horizontal.setAttribute("y2", y);
      tag.setAttribute("transform", "translate(0 " + (y - TAG_HEIGHT / 2) + ")");
      label.setAttribute("y", TAG_HEIGHT / 2 + 4);
      label.textContent = priceText;
      group.setAttribute("opacity", 1);
    }

    function hide() {
      group.setAttribute("opacity", 0);
    }

    return {move: move, hide: hide};
  }

  return {
    priceGrid: priceGrid,
    timeAxis: timeAxis,
    lastPrice: lastPrice,
    crosshair: crosshair
  };
})();
