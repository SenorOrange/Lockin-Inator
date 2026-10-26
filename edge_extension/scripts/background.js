/**
 * Lockin-Inator Edge Extension Background Service Worker.
 *
 * Runs in the extension background context to completely bypass webpage
 * Content Security Policy (CSP) restrictions. Polls the local PC Hub
 * (http://127.0.0.1:8765), listens to SSE status streams, persists the live
 * state to chrome.storage.local, and handles remote actions (RESET, START_STUDY).
 */

const SYNC_URL = "http://127.0.0.1:8765/api/status";
const ACTION_URL = "http://127.0.0.1:8765/api/action";

let syncState = {
  connected: false,
  state: "IDLE",
  remaining_seconds: 0,
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
      chrome.storage.local.set({ lockin_sync_state: syncState });
    } else {
      markDisconnected();
    }
  } catch (err) {
    markDisconnected();
  }
}

function markDisconnected() {
  if (syncState.connected || syncState.state !== "IDLE") {
    syncState.connected = false;
    syncState.state = "IDLE";
    syncState.remaining_seconds = 0;
    chrome.storage.local.set({ lockin_sync_state: syncState });
  }
}

// Poll status every 1000ms
pollStatus();
setInterval(pollStatus, 1000);

// Smooth local decrement in background
setInterval(() => {
  if (syncState.connected && (syncState.state === "STUDY" || syncState.state === "BREAK") && syncState.remaining_seconds > 0) {
    syncState.remaining_seconds--;
    chrome.storage.local.set({ lockin_sync_state: syncState });
  }
}, 1000);

// Handle messages from content scripts (e.g. End Study Session Early)
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message && message.type === "REMOTE_ACTION") {
    fetch(ACTION_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(message.payload || { action: "RESET" })
    })
      .then(async (res) => {
        const text = await res.text();
        pollStatus();
        sendResponse({ success: res.ok, data: text });
      })
      .catch((err) => {
        sendResponse({ success: false, error: err.toString() });
      });
    return true; // Keep message channel open for async response
  }
});
