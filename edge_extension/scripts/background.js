/**
 * Lockin-Inator Edge Extension Background Service Worker.
 *
 * Runs in the extension background context to completely bypass webpage
 * Content Security Policy (CSP) restrictions. Polls the local PC Hub
 * (http://127.0.0.1:8765), persists the live state to chrome.storage.local,
 * broadcasts state changes to connected tab ports, and handles remote actions (RESET, CLOSE_CURRENT_TAB).
 */

const SYNC_URL = "http://127.0.0.1:8765/api/status";
const ACTION_URL = "http://127.0.0.1:8765/api/action";

let syncState = {
  connected: false,
  state: "IDLE",
  remaining_seconds: 0,
  study_duration_minutes: 50,
  break_duration_minutes: 10,
  server_ip: "127.0.0.1",
  blocked_sites: [
    "instagram.com",
    "youtube.com",
    "tiktok.com",
    "twitter.com",
    "x.com",
    "reddit.com",
    "twitch.tv",
    "facebook.com",
    "netflix.com"
  ]
};

const activePorts = new Set();

function broadcastState(state) {
  // Push down all active keepalive ports
  for (const port of activePorts) {
    try {
      port.postMessage({ type: "STATE_UPDATE", state });
    } catch (e) {
      activePorts.delete(port);
    }
  }

  // Also broadcast via tabs API if available
  if (chrome.tabs && chrome.tabs.query) {
    chrome.tabs.query({}, (tabs) => {
      if (!tabs) return;
      for (const tab of tabs) {
        if (tab.id) {
          chrome.tabs.sendMessage(tab.id, { type: "LOCKIN_STATE_CHANGED", state }).catch(() => {});
        }
      }
    });
  }

  chrome.storage.local.set({ lockin_sync_state: state });
}

async function pollStatus() {
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 2000);
    const res = await fetch(SYNC_URL, { signal: controller.signal });
    clearTimeout(timeoutId);

    if (res.ok) {
      const data = await res.json();
      syncState = {
        ...syncState,
        ...data,
        connected: true
      };
      broadcastState(syncState);
      return syncState;
    } else {
      markDisconnected();
    }
  } catch (err) {
    markDisconnected();
  }
  return syncState;
}

function markDisconnected() {
  if (syncState.connected) {
    syncState.connected = false;
    chrome.storage.local.set({ lockin_sync_state: syncState });
  }
  // If time has completely expired, revert to IDLE
  if (syncState.remaining_seconds <= 0 && syncState.state !== "IDLE") {
    syncState.state = "IDLE";
    broadcastState(syncState);
  }
}

// Initial poll
pollStatus();

// Polling interval
setInterval(pollStatus, 1000);

// Smooth local decrement in background
setInterval(() => {
  if (syncState.remaining_seconds > 0 && (syncState.state === "STUDY" || syncState.state === "BREAK")) {
    syncState.remaining_seconds--;
    chrome.storage.local.set({ lockin_sync_state: syncState });
    for (const port of activePorts) {
      try {
        port.postMessage({ type: "TICK", remaining_seconds: syncState.remaining_seconds });
      } catch (e) {}
    }
  } else if (syncState.remaining_seconds <= 0 && syncState.state === "STUDY") {
    syncState.state = "IDLE";
    broadcastState(syncState);
  }
}, 1000);

// Persistent keepalive port connection from content scripts (keeps service worker active!)
chrome.runtime.onConnect.addListener((port) => {
  if (port.name === "lockin_sync" || port.name === "lockin_keepalive") {
    activePorts.add(port);
    // Send immediate state
    port.postMessage({ type: "STATE_UPDATE", state: syncState });

    port.onDisconnect.addListener(() => {
      activePorts.delete(port);
    });

    port.onMessage.addListener((msg) => {
      if (msg && msg.type === "POLL_NOW") {
        pollStatus().then((st) => {
          try { port.postMessage({ type: "STATE_UPDATE", state: st }); } catch (e) {}
        });
      }
    });
  }
});

// Periodic alarm to keep service worker alive
if (chrome.alarms) {
  try {
    chrome.alarms.create("lockin_poll_keepalive", { periodInMinutes: 0.1 });
    chrome.alarms.onAlarm.addListener((alarm) => {
      if (alarm.name === "lockin_poll_keepalive") {
        pollStatus();
      }
    });
  } catch (e) {}
}

// Tab navigation listener to poll immediately on new pages
if (chrome.tabs && chrome.tabs.onUpdated) {
  chrome.tabs.onUpdated.addListener((tabId, changeInfo) => {
    if (changeInfo.status === "loading") {
      pollStatus();
    }
  });
}

// Handle messages from content scripts
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (!message) return;

  if (message.type === "GET_STATUS" || message.type === "POLL_STATUS") {
    pollStatus().then((state) => {
      sendResponse({ success: true, state: state || syncState });
    }).catch(() => {
      sendResponse({ success: true, state: syncState });
    });
    return true;
  }

  if (message.type === "CLOSE_CURRENT_TAB") {
    if (sender && sender.tab && sender.tab.id && chrome.tabs && chrome.tabs.remove) {
      chrome.tabs.remove(sender.tab.id).catch(() => {});
      sendResponse({ success: true });
    } else {
      sendResponse({ success: false });
    }
    return false;
  }

  if (message.type === "REMOTE_ACTION") {
    fetch(ACTION_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(message.payload || { action: "RESET" })
    })
      .then(async (res) => {
        const text = await res.text();
        const updated = await pollStatus();
        broadcastState(updated);
        sendResponse({ success: res.ok, data: text });
      })
      .catch((err) => {
        sendResponse({ success: false, error: err.toString() });
      });
    return true;
  }
});
