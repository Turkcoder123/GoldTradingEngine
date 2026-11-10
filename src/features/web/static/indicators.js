/* Client-side studies computed on the stored bars (no dependency). */
"use strict";

const Indicators = (function () {
  function ema(values, period) {
    const result = [];
    if (!values.length) {
      return result;
    }
    const weight = 2 / (period + 1);
    let value = values[0];
    result.push(value);
    for (let index = 1; index < values.length; index += 1) {
      value = values[index] * weight + value * (1 - weight);
      result.push(value);
    }
    return result;
  }

  function closes(bars) {
    return bars.map(function (bar) {
      return bar.close;
    });
  }

  function emaSeries(bars, period) {
    return ema(closes(bars), period);
  }

  return {ema: ema, emaSeries: emaSeries, closes: closes};
})();
