/* Page layout: the element handles and the static text of the shell. */
"use strict";

const DashboardLayout = (function () {
  const label = PageRuntime.label;
  const text = PageRuntime.text;
  const VERSION = PageRuntime.version;

  function panels() {
    return {
      kpis: document.getElementById("kpi-strip"),
      grid: document.getElementById("series-grid"),
      seriesChips: document.getElementById("series-chips"),
      intervalChips: document.getElementById("interval-chips"),
      rangeChips: document.getElementById("range-chips"),
      priceSummary: document.getElementById("price-summary"),
      priceChart: document.getElementById("price-chart"),
      priceLive: document.getElementById("price-live"),
      priceHint: document.getElementById("price-hint"),
      priceWindow: document.getElementById("price-window"),
      zoomChips: document.getElementById("zoom-chips"),
      indicators: {
        title: document.getElementById("indicators-title"),
        note: document.getElementById("indicators-note"),
        chips: document.getElementById("indicator-chips")
      },
      smc: {
        title: document.getElementById("smc-title"),
        note: document.getElementById("smc-note"),
        toggles: document.getElementById("smc-toggles"),
        summary: document.getElementById("smc-summary"),
        events: document.getElementById("smc-events")
      },
      cot: {
        title: document.getElementById("cot-title"),
        note: document.getElementById("cot-note"),
        summary: document.getElementById("cot-summary"),
        chart: document.getElementById("cot-chart")
      },
      macro: {
        title: document.getElementById("macro-title"),
        note: document.getElementById("macro-note"),
        grid: document.getElementById("macro-grid"),
        chart: document.getElementById("macro-chart"),
        ratesCaption: document.getElementById("macro-rates-caption"),
        ratesChart: document.getElementById("macro-rates-chart"),
        rates: document.getElementById("macro-rates")
      },
      alt: {
        title: document.getElementById("alt-title"),
        note: document.getElementById("alt-note"),
        summary: document.getElementById("alt-summary"),
        tonnesTitle: document.getElementById("alt-tonnes-title"),
        tonnesChart: document.getElementById("alt-tonnes-chart"),
        gvzTitle: document.getElementById("alt-gvz-title"),
        gvzChart: document.getElementById("alt-gvz-chart"),
        documents: document.getElementById("alt-documents")
      }
    };
  }

  function renderHeader() {
    text("app-title", label("app.title"));
    text("app-subtitle", label("app.subtitle"));
    text("app-version", label("app.version") + " " + VERSION);
    text("refresh", label("app.refresh"));
    text("overview-title", label("section.overview"));
    text("price-title", label("section.prices"));
    text("price-hint", label("price.hint"));
    text("price-note", label("price.note"));
  }

  function renderFooter(overview) {
    const parts = [label("app.data_dir") + ": " +
                   (overview ? overview.data_dir : "-"),
                   label("app.read_only")];
    text("footer-note", parts.join(" | "));
  }

  return {panels: panels, renderHeader: renderHeader,
          renderFooter: renderFooter};
})();
