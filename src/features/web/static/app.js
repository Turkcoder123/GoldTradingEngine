/* Dashboard bootstrap: fetch the API, render the panels, wire the controls. */
"use strict";

const DashboardApp = (function () {
  const LABELS = PageRuntime.labels;
  const label = PageRuntime.label;
  const status = PageRuntime.status;
  const request = PageRuntime.request;
  const PANELS = DashboardLayout.panels();
  const state = {
    overview: null,
    seriesKey: "xauusd",
    months: 3,
    price: null,
    smc: null,
    cot: null,
    macro: null,
    groups: {structure: true, zones: true, sweeps: true, swings: false}
  };

  function ratesData() {
    return state.overview ? state.overview.rates : null;
  }

  function renderAlt() {
    if (!state.overview) {
      return;
    }
    DashboardAltPanel.render(PANELS.alt, state.overview.alt, LABELS);
  }

  function overlays() {
    if (!state.smc) {
      return null;
    }
    return {groups: state.groups, events: state.smc.events, labels: LABELS};
  }

  function renderOverview() {
    if (!state.overview) {
      return;
    }
    DashboardOverviewPanel.render(PANELS, state.overview, LABELS, {
      selectedKey: state.seriesKey,
      months: state.months,
      onSelectSeries: function (key) {
        state.seriesKey = key;
        state.smc = null;
        renderOverview();
        loadPrice();
        loadSmc();
        document.getElementById("price-panel")
          .scrollIntoView({behavior: "smooth", block: "start"});
      },
      onSelectRange: function (months) {
        state.months = months;
        state.smc = null;
        renderOverview();
        loadPrice();
        loadSmc();
      }
    });
    DashboardLayout.renderFooter(state.overview);
  }

  function renderPrice() {
    if (!state.price) {
      return;
    }
    DashboardPricePanel.render(PANELS, state.price, LABELS, overlays());
  }

  function renderSmc() {
    DashboardSmcPanel.render(PANELS.smc, state.smc, LABELS, {
      groups: state.groups,
      onToggle: function (name, active) {
        state.groups[name] = active;
        renderSmc();
        renderPrice();
      }
    });
  }

  async function loadPrice() {
    try {
      state.price = await request("/api/series/" +
        encodeURIComponent(state.seriesKey) + "?months=" + state.months);
      renderPrice();
    } catch (error) {
      status(label("app.failed") + ": " + error.message, "error");
    }
  }

  async function loadSmc() {
    try {
      state.smc = await request("/api/smc/" +
        encodeURIComponent(state.seriesKey) + "?months=" + state.months);
    } catch (error) {
      state.smc = null;
      status(label("app.failed") + ": " + error.message, "error");
    }
    renderSmc();
    renderPrice();
  }
  async function loadCot() {
    try {
      state.cot = await request("/api/cot");
      DashboardCotPanel.render(PANELS.cot, state.cot, LABELS);
    } catch (error) {
      status(label("app.failed") + ": " + error.message, "error");
    }
  }

  async function loadMacro() {
    try {
      state.macro = await request("/api/macro");
      DashboardMacroPanel.render(PANELS.macro, state.macro, LABELS,
                                 ratesData());
    } catch (error) {
      status(label("app.failed") + ": " + error.message, "error");
    }
  }

  async function boot() {
    DashboardLayout.renderHeader();
    status(label("app.loading") + "...");
    try {
      state.overview = await request("/api/overview");
    } catch (error) {
      status(label("app.failed") + ": " + error.message, "error");
      return;
    }
    renderOverview();
    renderAlt();
    status("");
    loadPrice();
    loadSmc();
    loadCot();
    loadMacro();
  }

  async function refresh() {
    status(label("app.loading") + "...");
    try {
      await request("/api/refresh");
      state.overview = await request("/api/overview");
      renderOverview();
      renderAlt();
      await Promise.all([loadPrice(), loadSmc(), loadCot(), loadMacro()]);
      status("");
    } catch (error) {
      status(label("app.failed") + ": " + error.message, "error");
    }
  }

  let resizeTimer = null;

  function onResize() {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(function () {
      renderPrice();
      renderSmc();
      if (state.cot) {
        DashboardCotPanel.render(PANELS.cot, state.cot, LABELS);
      }
      if (state.macro) {
        DashboardMacroPanel.render(PANELS.macro, state.macro, LABELS,
                                   ratesData());
      }
      renderAlt();
    }, 200);
  }

  function init() {
    document.getElementById("refresh").addEventListener("click", refresh);
    window.addEventListener("resize", onResize);
    boot();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  return {boot: boot, refresh: refresh};
})();
