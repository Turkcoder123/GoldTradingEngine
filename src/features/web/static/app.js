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
    interval: "1d",
    days: 0,
    price: null,
    smc: null,
    live: null,
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
      onSelectSeries: function (key) {
        state.seriesKey = key;
        state.smc = null;
        renderOverview();
        loadPrice();
        loadSmc();
        document.getElementById("price-panel")
          .scrollIntoView({behavior: "smooth", block: "start"});
      }
    });
    DashboardLayout.renderFooter(state.overview);
  }

  function renderControls() {
    ChartControls.render(PANELS, state, LABELS, {
      onInterval: function (interval) {
        state.interval = interval;
        renderControls();
        loadPrice();
      },
      onRange: function (days) {
        state.days = days;
        renderControls();
        loadPrice();
      }
    });
  }

  function renderPrice() {
    if (!state.price) {
      return;
    }
    const overlay = state.interval === "1d" ? overlays() : null;
    DashboardPricePanel.render(PANELS, state.price, LABELS, overlay,
                               state.live);
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
        encodeURIComponent(state.seriesKey) + "?interval=" +
        encodeURIComponent(state.interval) + "&days=" + state.days);
      renderPrice();
    } catch (error) {
      status(label("app.failed") + ": " + error.message, "error");
    }
  }

  async function loadLive() {
    try {
      state.live = await request("/api/live");
    } catch (error) {
      state.live = null;
    }
    renderPrice();
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
    renderControls();
    renderAlt();
    status("");
    loadPrice();
    loadLive();
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
      await Promise.all([loadPrice(), loadLive(), loadSmc(), loadCot(),
                         loadMacro()]);
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

  const LIVE_POLL_MS = 20000;

  function startLivePolling() {
    setInterval(function () {
      if (!document.hidden) {
        loadLive();
      }
    }, LIVE_POLL_MS);
  }

  function init() {
    document.getElementById("refresh").addEventListener("click", refresh);
    window.addEventListener("resize", onResize);
    boot();
    startLivePolling();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  return {boot: boot, refresh: refresh};
})();
