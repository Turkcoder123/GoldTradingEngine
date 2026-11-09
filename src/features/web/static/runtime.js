/* Shared page runtime: labels, fetch, status line and text helpers. */
"use strict";

const PageRuntime = (function () {
  const configuration = JSON.parse(
    document.getElementById("dashboard-config").textContent);
  const version = document.body.dataset.version || "";

  function label(key) {
    return configuration[key] || key;
  }

  function text(id, value) {
    const node = document.getElementById(id);
    if (node) {
      node.textContent = value;
    }
  }

  function status(message, kind) {
    const node = document.getElementById("status-line");
    node.textContent = message || "";
    node.className = "status-line" + (kind ? " " + kind : "");
    node.hidden = !message;
  }

  async function request(path) {
    const response = await fetch(path, {cache: "no-store"});
    let body = null;
    try {
      body = await response.json();
    } catch (error) {
      throw new Error(label("app.failed") + " (" + response.status + ")");
    }
    if (!body.ok) {
      throw new Error(body.error || label("app.failed"));
    }
    return body.data;
  }

  return {
    labels: configuration,
    version: version,
    label: label,
    text: text,
    status: status,
    request: request
  };
})();
