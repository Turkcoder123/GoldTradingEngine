/* Shared SVG helpers for the dashboard charts (no third-party library). */
"use strict";

const ChartCore = (function () {
  const SVG_NS = "http://www.w3.org/2000/svg";
  const PALETTE = ["#e3b341", "#58a6ff", "#3fb950", "#f778ba", "#a371f7",
                   "#39c5cf", "#ff7b72", "#8b949e"];
  const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

  function el(name, attrs) {
    const node = document.createElementNS(SVG_NS, name);
    Object.keys(attrs || {}).forEach(function (key) {
      node.setAttribute(key, attrs[key]);
    });
    return node;
  }

  function clear(node) {
    while (node.firstChild) {
      node.removeChild(node.firstChild);
    }
  }

  function makeSvg(width, height) {
    return el("svg", {
      viewBox: "0 0 " + width + " " + height,
      width: width,
      height: height,
      class: "chart-svg",
      role: "img"
    });
  }

  function linear(domain, range) {
    const span = (domain[1] - domain[0]) || 1;
    const size = range[1] - range[0];
    return function (value) {
      return range[0] + ((value - domain[0]) / span) * size;
    };
  }

  function ticks(min, max, count) {
    if (!isFinite(min) || !isFinite(max)) {
      return [];
    }
    if (min === max) {
      return [min];
    }
    const rough = (max - min) / Math.max(1, count);
    const power = Math.pow(10, Math.floor(Math.log10(rough)));
    const ratio = rough / power;
    let factor = 10;
    if (ratio < 1.5) {
      factor = 1;
    } else if (ratio < 3.5) {
      factor = 2;
    } else if (ratio < 7.5) {
      factor = 5;
    }
    const step = factor * power;
    const values = [];
    const first = Math.ceil(min / step) * step;
    for (let value = first; value <= max + step * 1e-6; value += step) {
      values.push(Number(value.toFixed(10)));
    }
    return values;
  }

  function digitsFor(value) {
    return Math.abs(value) >= 1 ? 2 : 3;
  }

  function fmtValue(value, digits) {
    if (value === null || value === undefined || !isFinite(value)) {
      return "-";
    }
    const chosen = digits === undefined ? digitsFor(value) : digits;
    return Number(value).toLocaleString("en-US", {
      minimumFractionDigits: chosen,
      maximumFractionDigits: chosen
    });
  }

  function fmtCompact(value) {
    if (value === null || value === undefined || !isFinite(value)) {
      return "-";
    }
    const size = Math.abs(value);
    if (size >= 1e9) { return (value / 1e9).toFixed(1) + "B"; }
    if (size >= 1e6) { return (value / 1e6).toFixed(1) + "M"; }
    if (size >= 1e3) { return (value / 1e3).toFixed(1) + "K"; }
    return fmtValue(value, 0);
  }

  function fmtPercent(value) {
    if (value === null || value === undefined || !isFinite(value)) {
      return "-";
    }
    return (value > 0 ? "+" : "") + value.toFixed(2) + "%";
  }

  function fmtDay(iso) {
    if (!iso) { return "-"; }
    const month = MONTHS[parseInt(iso.slice(5, 7), 10) - 1];
    return iso.slice(8, 10) + " " + month;
  }

  function text(parent, x, y, content, options) {
    const settings = options || {};
    const node = el("text", {
      x: x,
      y: y,
      class: settings.className || "chart-label",
      "text-anchor": settings.anchor || "middle"
    });
    node.textContent = content;
    parent.appendChild(node);
    return node;
  }

  function row(label, value) {
    return '<div class="tip-row"><span>' + label +
           "</span><b>" + value + "</b></div>";
  }

  function showTooltip(container, html, x, y) {
    let node = container.querySelector(".chart-tip");
    if (!node) {
      node = document.createElement("div");
      node.className = "chart-tip";
      container.appendChild(node);
    }
    node.innerHTML = html;
    node.hidden = false;
    const bounds = container.getBoundingClientRect();
    const width = node.offsetWidth;
    const left = Math.min(Math.max(4, x - width / 2), bounds.width - width - 4);
    node.style.left = left + "px";
    node.style.top = Math.max(4, y - node.offsetHeight - 12) + "px";
  }

  function hideTooltip(container) {
    const node = container.querySelector(".chart-tip");
    if (node) {
      node.hidden = true;
    }
  }

  function emptyNote(container, message) {
    const note = document.createElement("p");
    note.className = "chart-empty";
    note.textContent = message;
    container.appendChild(note);
  }

  return {
    el: el,
    clear: clear,
    makeSvg: makeSvg,
    linear: linear,
    ticks: ticks,
    fmtValue: fmtValue,
    fmtCompact: fmtCompact,
    fmtPercent: fmtPercent,
    fmtDay: fmtDay,
    digitsFor: digitsFor,
    text: text,
    row: row,
    showTooltip: showTooltip,
    hideTooltip: hideTooltip,
    emptyNote: emptyNote,
    PALETTE: PALETTE
  };
})();
