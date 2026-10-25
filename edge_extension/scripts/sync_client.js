/**
 * Lockin-Inator Edge Extension Local Wi-Fi Sync Client.
 * Connects to the local PC Hub (http://127.0.0.1:8765) to synchronize
 * Study and Break sessions across PC, Browser, and Android Phone.
 */

(function () {
  const SYNC_URL = "http://127.0.0.1:8765/api/status";
  const STREAM_URL = "http://127.0.0.1:8765/api/stream";

  let syncState = {
    connected: false,
    state: "IDLE",
    remaining_seconds: 0,
    server_ip: "127.0.0.1",
  };

  function updateBlockOverlaySyncInfo() {
    const card = document.querySelector(".focuslens-card");
    if (!card) return;

    let syncBadge = document.getElementById("focuslens-sync-badge");
    if (!syncBadge) {
      syncBadge = document.createElement("div");
      syncBadge.id = "focuslens-sync-badge";
      syncBadge.style.cssText =
        "margin-top: 14px; font-size: 13px; font-weight: 600; padding: 6px 14px; border-radius: 10px; text-align: center;";
      card.appendChild(syncBadge);
    }

    if (syncState.state === "STUDY") {
      const mins = Math.floor(syncState.remaining_seconds / 60);
      const secs = syncState.remaining_seconds % 60;
      const timeStr = `${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
      syncBadge.style.backgroundColor = "#032b43";
      syncBadge.style.color = "#38bdf8";
      syncBadge.style.border = "1px solid #0284c7";
      syncBadge.textContent = `🔒 Study Mode Synced: ${timeStr} remaining (PC + Phone + Browser)`;
    } else if (syncState.state === "BREAK") {
      const mins = Math.floor(syncState.remaining_seconds / 60);
      const secs = syncState.remaining_seconds % 60;
      const timeStr = `${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
      syncBadge.style.backgroundColor = "#064e3b";
      syncBadge.style.color = "#34d399";
      syncBadge.style.border = "1px solid #059669";
      syncBadge.textContent = `☕ AI Review Break: ${timeStr} left — wrap up prompts & lock back in!`;
    } else {
      syncBadge.style.backgroundColor = "#1e293b";
      syncBadge.style.color = "#94a3b8";
      syncBadge.style.border = "1px solid #334155";
      syncBadge.textContent = "🛡️ Lockin-Inator: Connected to PC Hub";
    }
  }

  // Poll status endpoint
  async function pollSyncStatus() {
    try {
      const res = await fetch(SYNC_URL);
      if (res.ok) {
        const data = await res.json();
        syncState = { ...data, connected: true };
        updateBlockOverlaySyncInfo();
      }
    } catch (e) {
      syncState.connected = false;
    }
  }

  // Connect to live SSE stream for instant updates
  function connectEventSource() {
    try {
      const sse = new EventSource(STREAM_URL);
      sse.onmessage = function (event) {
        try {
          const data = JSON.parse(event.data);
          syncState = { ...data, connected: true };
          updateBlockOverlaySyncInfo();
        } catch (err) {}
      };
      sse.onerror = function () {
        sse.close();
        setTimeout(connectEventSource, 5000);
      };
    } catch (e) {
      setTimeout(connectEventSource, 5000);
    }
  }

  // Initial fetch and regular polling fallback
  pollSyncStatus();
  setInterval(pollSyncStatus, 2000);
  connectEventSource();

  // Watch for dynamic block overlays added to the DOM
  const observer = new MutationObserver(() => {
    if (document.querySelector(".focuslens-card")) {
      updateBlockOverlaySyncInfo();
    }
  });

  if (document.body) {
    observer.observe(document.body, { childList: true, subtree: true });
  } else {
    document.addEventListener("DOMContentLoaded", () => {
      observer.observe(document.body, { childList: true, subtree: true });
    });
  }
})();
