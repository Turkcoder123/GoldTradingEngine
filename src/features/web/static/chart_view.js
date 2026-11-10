/* Chart viewport: which slice of the bars is visible (zoom and pan). */
"use strict";

const ChartView = (function () {
  const MIN_BARS = 12;

  function create(total, from, to) {
    const span = Math.min(total, Math.max(MIN_BARS, to === undefined
      ? total : to - (from || 0)));
    const start = Math.max(0, Math.min(from || 0, total - span));
    return {total: total, from: start, to: start + span};
  }

  function clamp(view) {
    const span = Math.min(view.total, Math.max(MIN_BARS,
      Math.round(view.to - view.from)));
    let from = Math.round(view.from);
    if (from < 0) {
      from = 0;
    }
    if (from + span > view.total) {
      from = view.total - span;
    }
    return {total: view.total, from: from, to: from + span};
  }

  function withTotal(view, total) {
    return clamp({total: total, from: view.from, to: view.to});
  }

  function zoom(view, factor, anchor) {
    const span = view.to - view.from;
    const ratio = anchor === undefined ? 0.5 : Math.min(1, Math.max(0, anchor));
    const next = Math.min(view.total, Math.max(MIN_BARS, span * factor));
    const from = view.from + (span - next) * ratio;
    return clamp({total: view.total, from: from, to: from + next});
  }

  function pan(view, ratio) {
    const span = view.to - view.from;
    return clamp({total: view.total, from: view.from + span * ratio,
                  to: view.to + span * ratio});
  }

  function isFull(view) {
    return view.from <= 0 && view.to >= view.total;
  }

  return {
    create: create,
    clamp: clamp,
    withTotal: withTotal,
    zoom: zoom,
    pan: pan,
    isFull: isFull,
    MIN_BARS: MIN_BARS
  };
})();
