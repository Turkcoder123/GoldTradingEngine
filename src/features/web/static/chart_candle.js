/* Candlestick chart: viewport, frame, studies, and the gesture wiring. */
"use strict";

const ChartCandle = (function () {
  const PADDING = {top: 14, right: 64, bottom: 30, left: 8};
  const VOLUME_HEIGHT = 52;
  const VOLUME_GAP = 18;
  const HEIGHT = 360;
  const EMA_FAST = "#58a6ff";
  const EMA_SLOW = "#f778ba";
  const states = new WeakMap();

  function frameFor(bars, width, options) {
    const withVolume = options.volume !== false;
    const bottomSpace = withVolume ? VOLUME_HEIGHT + VOLUME_GAP : 0;
    const plot = {
      left: PADDING.left,
      right: width - PADDING.right,
      top: PADDING.top,
      bottom: HEIGHT - PADDING.bottom - bottomSpace
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
      band: (plot.right - plot.left) / Math.max(1, bars.length),
      yPrice: ChartCore.linear([min - padding, max + padding],
                               [plot.bottom, plot.top]),
      min: min - padding,
      max: max + padding,
      count: bars.length,
      withVolume: withVolume,
      yVolume: ChartCore.linear([0, maxVolume], [volumeBottom, volumeTop]),
      volumeBottom: volumeBottom,
      volumeTop: volumeTop
    };
  }

  function scheduleDraw(container) {
    if (container._chartFrame) {
      return;
    }
    container._chartFrame = requestAnimationFrame(function () {
      container._chartFrame = 0;
      draw(container);
    });
  }

  function draw(container) {
    const state = states.get(container);
    if (!state) {
      return;
    }
    const view = state.view;
    const bars = state.bars;
    const labels = state.labels;
    const options = state.options;
    ChartCore.clear(container);
    const width = Math.max(300, container.clientWidth || 720);
    const svg = ChartCore.makeSvg(width, HEIGHT);
    container.appendChild(svg);
    if (!bars.length) {
      ChartCore.emptyNote(container, labels.empty);
      return;
    }
    const visible = bars.slice(view.from, view.to);
    const frame = frameFor(visible, width, options);
    ChartAxes.priceGrid(svg, frame.plot, frame.yPrice, frame.min, frame.max);
    ChartAxes.timeAxis(svg, visible, frame.plot, frame.band, labels.axisLabel);
    const last = bars[bars.length - 1];
    if (options.lastPrice !== false) {
      ChartAxes.lastPrice(svg, frame.plot, frame.yPrice, last.close,
                          ChartSeries.liveColour(last));
    }
    if (options.ema20) {
      ChartSeries.emaLine(svg,
                          Indicators.emaSeries(bars, 20)
                            .slice(view.from, view.to),
                          frame, EMA_FAST);
    }
    if (options.ema50) {
      ChartSeries.emaLine(svg,
                          Indicators.emaSeries(bars, 50)
                            .slice(view.from, view.to),
                          frame, EMA_SLOW);
    }
    ChartSmc.drawZones(svg, frame, state.overlays);
    if (frame.withVolume) {
      ChartCore.text(svg, frame.plot.left, frame.volumeTop - 5, labels.volume,
                     {anchor: "start", className: "chart-label dim"});
    }
    const bodyWidth = Math.max(1, Math.min(14, frame.band * 0.62));
    visible.forEach(function (bar, index) {
      const center = frame.plot.left + frame.band * (index + 0.5);
      ChartSeries.wick(svg, bar, center, frame.yPrice);
      ChartSeries.body(svg, bar, center, bodyWidth, frame.yPrice);
      if (frame.withVolume) {
        ChartSeries.volume(svg, bar, center, bodyWidth, frame.yVolume,
                           frame.volumeBottom);
      }
    });
    ChartSmc.drawLevels(svg, frame, state.overlays);
    ChartGestures.attach(svg, container, {
      frame: frame,
      visible: visible,
      width: width,
      state: state,
      labels: labels,
      tipContent: ChartSeries.tip,
      redraw: function () {
        scheduleDraw(container);
      }
    });
  }

  function render(container, bars, labels, overlays, options) {
    const previous = states.get(container);
    let view = ChartView.create(bars.length);
    if (previous && !ChartView.isFull(previous.view)) {
      view = ChartView.withTotal(previous.view, bars.length);
    }
    states.set(container, {bars: bars, labels: labels, overlays: overlays,
                           options: options || {}, view: view});
    draw(container);
  }

  function zoomBy(container, factor) {
    const state = states.get(container);
    if (!state) {
      return;
    }
    state.view = ChartView.zoom(state.view, factor, 0.5);
    draw(container);
  }

  function reset(container) {
    const state = states.get(container);
    if (!state) {
      return;
    }
    state.view = ChartView.create(state.bars.length);
    draw(container);
  }

  return {
    render: render,
    zoomIn: function (container) {
      zoomBy(container, 0.8);
    },
    zoomOut: function (container) {
      zoomBy(container, 1.25);
    },
    reset: reset
  };
})();
