/* Chart gestures: wheel zoom, drag pan, pinch zoom, reset and hover tip. */
"use strict";

const ChartGestures = (function () {
  function attach(svg, container, context) {
    const frame = context.frame;
    const visible = context.visible;
    const width = context.width;
    const state = context.state;
    const labels = context.labels;
    const redraw = context.redraw;
    const tipContent = context.tipContent;
    const guide = ChartAxes.crosshair(svg, frame.plot);
    const overlay = ChartCore.el("rect", {
      x: frame.plot.left, y: frame.plot.top,
      width: frame.plot.right - frame.plot.left,
      height: frame.volumeBottom - frame.plot.top,
      fill: "transparent", class: "chart-overlay"
    });
    svg.appendChild(overlay);
    const pointers = new Map();
    let pinch = 0;

    function distance() {
      const points = Array.from(pointers.values());
      return Math.hypot(points[0].x - points[1].x,
                        points[0].y - points[1].y) || 1;
    }

    function anchorAt(clientX) {
      const bounds = svg.getBoundingClientRect();
      const x = (clientX - bounds.left) * (width / bounds.width);
      return Math.min(1, Math.max(0, (x - frame.plot.left) /
                                     (frame.plot.right - frame.plot.left)));
    }

    overlay.addEventListener("wheel", function (event) {
      event.preventDefault();
      state.view = ChartView.zoom(state.view, event.deltaY > 0 ? 1.18 : 0.85,
                                  anchorAt(event.clientX));
      redraw();
    }, {passive: false});
    overlay.addEventListener("pointerdown", function (event) {
      overlay.setPointerCapture(event.pointerId);
      pointers.set(event.pointerId, {x: event.clientX, y: event.clientY});
      if (pointers.size === 2) {
        pinch = distance();
      }
    });
    overlay.addEventListener("pointermove", function (event) {
      const previous = pointers.get(event.pointerId);
      if (!previous) {
        return;
      }
      pointers.set(event.pointerId, {x: event.clientX, y: event.clientY});
      if (pointers.size >= 2) {
        const next = distance();
        if (pinch) {
          state.view = ChartView.zoom(state.view, pinch / next, 0.5);
          pinch = next;
          redraw();
        }
        return;
      }
      const bounds = svg.getBoundingClientRect();
      const step = (event.clientX - previous.x) / Math.max(1, bounds.width);
      if (step) {
        state.view = ChartView.pan(state.view, -step);
        redraw();
      }
    });
    function release(event) {
      pointers.delete(event.pointerId);
      if (pointers.size < 2) {
        pinch = 0;
      }
    }
    overlay.addEventListener("pointerup", release);
    overlay.addEventListener("pointercancel", release);
    overlay.addEventListener("dblclick", function () {
      state.view = ChartView.create(state.bars.length);
      redraw();
    });
    overlay.addEventListener("mousemove", function (event) {
      const bounds = svg.getBoundingClientRect();
      const scale = width / bounds.width;
      const x = (event.clientX - bounds.left) * scale;
      const y = (event.clientY - bounds.top) * scale;
      const index = Math.min(visible.length - 1, Math.max(
        0, Math.floor((x - frame.plot.left) / frame.band)));
      const bar = visible[index];
      const center = frame.plot.left + frame.band * (index + 0.5);
      guide.move(center,
                 Math.min(Math.max(y, frame.plot.top), frame.plot.bottom),
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

  return {attach: attach};
})();
