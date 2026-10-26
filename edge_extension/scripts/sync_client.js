/**
 * Lockin-Inator Edge Extension Local Wi-Fi Sync Client.
 * Connects to the local PC Hub (http://127.0.0.1:8765) to synchronize
 * Study and Break sessions across PC, Browser, and Android Phone.
 * Provides window.LockinSync for all site blocker scripts.
 */

(function () {
  'use strict';

  if (window.LockinSync) {
    return;
  }

  const SYNC_URL = "http://127.0.0.1:8765/api/status";
  const STREAM_URL = "http://127.0.0.1:8765/api/stream";

  const DEFAULT_BLOCKED_SITES = [
    "instagram.com",
    "youtube.com",
    "tiktok.com",
    "twitter.com",
    "x.com",
    "reddit.com",
    "twitch.tv",
    "facebook.com",
    "netflix.com"
  ];

  let syncState = {
    connected: false,
    state: "IDLE",
    remaining_seconds: 0,
    server_ip: "127.0.0.1",
    blocked_sites: DEFAULT_BLOCKED_SITES.slice(),
  };

  const listeners = [];

  function formatTime(totalSeconds) {
    const s = Math.max(0, Math.floor(totalSeconds || 0));
    const mins = Math.floor(s / 60);
    const secs = s % 60;
    return `${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
  }

  function notifyListeners() {
    for (let i = 0; i < listeners.length; i++) {
      try {
        listeners[i](syncState);
      } catch (err) {
        console.error("[LockinSync] Listener error:", err);
      }
    }
    try {
      window.dispatchEvent(new CustomEvent("lockin-sync-change", { detail: syncState }));
    } catch (e) {}
  }

  function applyNewState(newState) {
    const prevState = syncState.state;
    const prevConnected = syncState.connected;
    const prevSeconds = syncState.remaining_seconds;

    syncState = {
      ...syncState,
      ...newState,
      connected: newState.connected !== undefined ? newState.connected : true,
    };

    if (Array.isArray(newState.blocked_sites) && newState.blocked_sites.length > 0) {
      syncState.blocked_sites = newState.blocked_sites;
    }

    // Persist to chrome.storage.local for instantaneous cold-start reads
    if (typeof chrome !== "undefined" && chrome.storage && chrome.storage.local) {
      chrome.storage.local.set({ lockin_sync_state: syncState });
    }

    updateOverlayUI();

    if (prevState !== syncState.state || prevConnected !== syncState.connected || Math.abs(prevSeconds - syncState.remaining_seconds) > 1) {
      notifyListeners();
    }
  }

  function handleDisconnect() {
    const wasActive = syncState.connected || syncState.state !== "IDLE";
    syncState.connected = false;
    syncState.state = "IDLE";
    syncState.remaining_seconds = 0;

    if (typeof chrome !== "undefined" && chrome.storage && chrome.storage.local) {
      chrome.storage.local.set({ lockin_sync_state: syncState });
    }

    updateOverlayUI();

    if (wasActive) {
      notifyListeners();
    }
  }

  function updateOverlayUI() {
    const timerEl = document.getElementById("focuslens-live-timer");
    if (timerEl) {
      timerEl.textContent = formatTime(syncState.remaining_seconds);
    }

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

    const timeStr = formatTime(syncState.remaining_seconds);

    if (syncState.connected && syncState.state === "STUDY") {
      syncBadge.style.backgroundColor = "#032b43";
      syncBadge.style.color = "#38bdf8";
      syncBadge.style.border = "1px solid #0284c7";
      syncBadge.textContent = `🔒 Study Mode Synced: ${timeStr} remaining (PC + Phone + Browser)`;
    } else if (syncState.connected && syncState.state === "BREAK") {
      syncBadge.style.backgroundColor = "#064e3b";
      syncBadge.style.color = "#34d399";
      syncBadge.style.border = "1px solid #059669";
      syncBadge.textContent = `☕ AI Review Break: ${timeStr} left — wrap up prompts & lock back in!`;
    } else {
      syncBadge.style.backgroundColor = "#1e293b";
      syncBadge.style.color = "#94a3b8";
      syncBadge.style.border = "1px solid #334155";
      syncBadge.textContent = "🛡️ Lockin-Inator: PC App Idle / Offline";
    }
  }

  // 1. Initial check from chrome.storage.local
  if (typeof chrome !== "undefined" && chrome.storage && chrome.storage.local) {
    chrome.storage.local.get(["lockin_sync_state"], function (res) {
      if (res && res.lockin_sync_state) {
        // If storage says study but we're not sure yet, check network immediately
        applyNewState(res.lockin_sync_state);
      }
    });

    chrome.storage.onChanged.addListener(function (changes, areaName) {
      if (areaName === "local" && changes.lockin_sync_state) {
        const newVal = changes.lockin_sync_state.newValue;
        if (newVal) {
          applyNewState(newVal);
        }
      }
    });
  }

  // 2. Poll status endpoint
  async function pollSyncStatus() {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 2000);
      const res = await fetch(SYNC_URL, { signal: controller.signal });
      clearTimeout(timeoutId);

      if (res.ok) {
        const data = await res.json();
        applyNewState({ ...data, connected: true });
      } else {
        handleDisconnect();
      }
    } catch (e) {
      handleDisconnect();
    }
  }

  // 3. Connect to live SSE stream for instant updates
  let eventSource = null;
  function connectEventSource() {
    try {
      if (eventSource) {
        eventSource.close();
      }
      eventSource = new EventSource(STREAM_URL);
      eventSource.onmessage = function (event) {
        try {
          const data = JSON.parse(event.data);
          applyNewState({ ...data, connected: true });
        } catch (err) {}
      };
      eventSource.onerror = function () {
        if (eventSource) {
          eventSource.close();
          eventSource = null;
        }
        handleDisconnect();
        setTimeout(connectEventSource, 4000);
      };
    } catch (e) {
      handleDisconnect();
      setTimeout(connectEventSource, 4000);
    }
  }

  // 4. Local tick timer so countdown drops smoothly every second
  setInterval(function () {
    if (syncState.connected && (syncState.state === "STUDY" || syncState.state === "BREAK") && syncState.remaining_seconds > 0) {
      syncState.remaining_seconds--;
      updateOverlayUI();
    }
  }, 1000);

  // Initial network fetches
  pollSyncStatus();
  setInterval(pollSyncStatus, 1500);
  connectEventSource();

  // Watch for dynamic block overlays added to the DOM
  const observer = new MutationObserver(() => {
    if (document.querySelector(".focuslens-card")) {
      updateOverlayUI();
    }
  });

  if (document.body) {
    observer.observe(document.body, { childList: true, subtree: true });
  } else {
    document.addEventListener("DOMContentLoaded", () => {
      if (document.body) {
        observer.observe(document.body, { childList: true, subtree: true });
      }
    });
  }

  // Public API exposed on window
  window.LockinSync = {
    getState: function () {
      return { ...syncState };
    },
    isStudyMode: function () {
      // Must be BOTH connected to the PC hub AND state === "STUDY"
      return Boolean(syncState.connected && syncState.state === "STUDY");
    },
    isBreakMode: function () {
      return Boolean(syncState.connected && syncState.state === "BREAK");
    },
    isIdleMode: function () {
      return !syncState.connected || syncState.state === "IDLE";
    },
    getRemainingSeconds: function () {
      return syncState.remaining_seconds;
    },
    formatTime: formatTime,
    getBlockedSites: function () {
      return syncState.blocked_sites || DEFAULT_BLOCKED_SITES;
    },
    isSiteBlocked: function (hostname) {
      const host = (hostname || window.location.hostname).toLowerCase();
      const sites = syncState.blocked_sites || DEFAULT_BLOCKED_SITES;
      return sites.some(site => host === site || host.endsWith("." + site));
    },
    onStateChange: function (callback) {
      if (typeof callback === "function") {
        listeners.push(callback);
        // Call immediately with current state
        callback(syncState);
      }
    },
    forcePoll: pollSyncStatus
  };
})();
