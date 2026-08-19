(() => {
  "use strict";

  const url = window.SE_SESSION_LIVE_URL;
  if (!url) return;

  const submitted = document.getElementById("count-submitted");
  const open = document.getElementById("count-open");
  const total = document.getElementById("count-total");
  const rows = document.getElementById("student-status-rows");
  const statusText = document.getElementById("live-status-text");
  const updatedTime = document.getElementById("live-updated-time");
  const statusLine = document.querySelector(".live-status-line");

  let inFlight = false;
  let timer = null;
  let pollingStopped = false;
  let lastSuccess = "gerade eben";

  function setState(kind, text) {
    if (statusLine) statusLine.dataset.state = kind;
    if (statusText) statusText.textContent = text;
  }

  function timeLabel() {
    return new Intl.DateTimeFormat("de-DE", {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    }).format(new Date());
  }

  async function refresh() {
    if (inFlight || document.hidden) return;
    inFlight = true;
    if (statusLine) statusLine.setAttribute("aria-busy", "true");

    try {
      const response = await fetch(url, {
        method: "GET",
        credentials: "same-origin",
        cache: "no-store",
        headers: { "Accept": "application/json" },
      });
      if (response.status === 404) {
        pollingStopped = true;
        if (timer) clearInterval(timer);
        timer = null;
        setState("error", "Diese Sitzung ist nicht mehr vorhanden.");
        if (updatedTime) {
          updatedTime.innerHTML = '<a href="/admin">Zur Übersicht</a>';
        }
        return;
      }
      if (!response.ok) throw new Error(`HTTP ${response.status}`);

      const data = await response.json();
      submitted.textContent = String(data.submitted);
      open.textContent = String(data.open);
      total.textContent = String(data.total);
      rows.innerHTML = data.rows_html;
      setState("ok", "Abgabestatus wird automatisch aktualisiert.");
      lastSuccess = timeLabel();
      updatedTime.textContent = `Zuletzt aktualisiert: ${lastSuccess}`;
    } catch (error) {
      console.warn("Live-Aktualisierung fehlgeschlagen", error);
      setState("error", "Verbindung unterbrochen – neuer Versuch läuft automatisch.");
      updatedTime.textContent = `Letzter erfolgreicher Stand: ${lastSuccess}`;
    } finally {
      inFlight = false;
      if (statusLine) statusLine.setAttribute("aria-busy", "false");
    }
  }

  function startPolling() {
    if (timer) clearInterval(timer);
    refresh();
    timer = setInterval(refresh, 3000);
  }

  document.addEventListener("visibilitychange", () => {
    if (!document.hidden && !pollingStopped) refresh();
  });
  window.addEventListener("focus", () => {
    if (!pollingStopped) refresh();
  });
  startPolling();
})();
