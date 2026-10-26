/**
 * Lockin-Inator Edge Extension Local Wi-Fi Sync Client.
 * Connects via persistent keepalive port and background service worker
 * to the local PC Hub (http://127.0.0.1:8765).
 * Provides window.LockinSync for all site blocker scripts.
 */

(function () {
  'use strict';

  if (window.LockinSync) {
    return;
  }

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
    if (!newState) return;
    const prevState = syncState.state;
    const prevConnected = syncState.connected;
    const prevSeconds = syncState.remaining_seconds;

    syncState = {
      ...syncState,
      ...newState,
      connected: newState.connected !== undefined ? newState.connected : syncState.connected,
    };

    if (Array.isArray(newState.blocked_sites) && newState.blocked_sites.length > 0) {
      syncState.blocked_sites = newState.blocked_sites;
    }

    updateOverlayUI();

    if (prevState !== syncState.state || prevConnected !== syncState.connected || Math.abs(prevSeconds - syncState.remaining_seconds) > 1) {
      notifyListeners();
    }
  }

  function updateOverlayUI() {
    const timerEls = document.querySelectorAll("#focuslens-live-timer, .focuslens-study-timer-digits");
    const formatted = formatTime(syncState.remaining_seconds);
    timerEls.forEach(el => {
      el.textContent = formatted;
    });

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

    const timeStr = formatted;

    if (syncState.state === "STUDY" && syncState.remaining_seconds > 0) {
      syncBadge.style.backgroundColor = "#032b43";
      syncBadge.style.color = "#38bdf8";
      syncBadge.style.border = "1px solid #0284c7";
      syncBadge.textContent = `🔒 Study Mode Synced: ${timeStr} remaining (PC + Phone + Browser)`;
    } else if (syncState.state === "BREAK" && syncState.remaining_seconds > 0) {
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

  // 1. Initial state check from chrome.storage.local
  if (typeof chrome !== "undefined" && chrome.storage && chrome.storage.local) {
    chrome.storage.local.get(["lockin_sync_state"], function (res) {
      if (res && res.lockin_sync_state) {
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

  // 2. Persistent keepalive port connection (keeps service worker active!)
  let syncPort = null;
  function connectSyncPort() {
    if (typeof chrome === "undefined" || !chrome.runtime || !chrome.runtime.connect) return;
    try {
      syncPort = chrome.runtime.connect({ name: "lockin_sync" });

      syncPort.onMessage.addListener(function (msg) {
        if (!msg) return;
        if (msg.type === "STATE_UPDATE" && msg.state) {
          applyNewState(msg.state);
        } else if (msg.type === "TICK" && typeof msg.remaining_seconds === "number") {
          syncState.remaining_seconds = msg.remaining_seconds;
          updateOverlayUI();
        }
      });

      syncPort.onDisconnect.addListener(function () {
        syncPort = null;
        setTimeout(connectSyncPort, 1500);
      });
    } catch (e) {
      setTimeout(connectSyncPort, 2000);
    }
  }

  connectSyncPort();

  // 3. Keepalive ping every second (keeps worker active and requests fresh state)
  setInterval(function () {
    if (syncPort) {
      try {
        syncPort.postMessage({ type: "POLL_NOW" });
      } catch (e) {}
    } else {
      connectSyncPort();
    }
  }, 1000);

  // 4. Smooth local countdown timer drops every second
  setInterval(function () {
    if (syncState.remaining_seconds > 0 && (syncState.state === "STUDY" || syncState.state === "BREAK")) {
      syncState.remaining_seconds--;
      updateOverlayUI();
    } else if (syncState.remaining_seconds <= 0 && syncState.state === "STUDY") {
      syncState.state = "IDLE";
      notifyListeners();
    }
  }, 1000);

  // 5. Watch for dynamic block overlays added to DOM
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
      return Boolean(syncState.state === "STUDY" && syncState.remaining_seconds > 0);
    },
    isBreakMode: function () {
      return Boolean(syncState.state === "BREAK" && syncState.remaining_seconds > 0);
    },
    isIdleMode: function () {
      return syncState.state === "IDLE" || !syncState.state;
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
    sendAction: function (action, durationMinutes) {
      if (typeof chrome !== "undefined" && chrome.runtime && chrome.runtime.sendMessage) {
        chrome.runtime.sendMessage({
          type: "REMOTE_ACTION",
          payload: { action: action, duration_minutes: durationMinutes }
        });
      }
    },
    closeTab: function () {
      if (typeof chrome !== "undefined" && chrome.runtime && chrome.runtime.sendMessage) {
        chrome.runtime.sendMessage({ type: "CLOSE_CURRENT_TAB" });
      }
      try {
        window.close();
      } catch (e) {}
      if (window.history.length > 1) {
        window.history.back();
      } else {
        window.location.replace("about:blank");
      }
    },
    onStateChange: function (callback) {
      if (typeof callback === "function") {
        listeners.push(callback);
        callback(syncState);
      }
    },
    forcePoll: function () {
      if (syncPort) {
        try { syncPort.postMessage({ type: "POLL_NOW" }); } catch (e) {}
      }
    }
  };
})();
