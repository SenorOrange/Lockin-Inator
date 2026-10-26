const API_URL = "http://127.0.0.1:8765/api/status";
const ACTION_URL = "http://127.0.0.1:8765/api/action";

const badge = document.getElementById("status-badge");
const timer = document.getElementById("timer-display");
const syncInfo = document.getElementById("sync-status");
const btn = document.getElementById("btn-action");
const btnEnd = document.getElementById("btn-end");

let currentState = "IDLE";

async function fetchStatus() {
  try {
    const res = await fetch(API_URL);
    if (res.ok) {
      const data = await res.json();
      currentState = data.state;
      syncInfo.className = "sync-info";
      syncInfo.textContent = "🟢 Synced with PC Hub";

      const mins = Math.floor(data.remaining_seconds / 60);
      const secs = data.remaining_seconds % 60;
      timer.textContent = `${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;

      if (data.state === "STUDY") {
        badge.className = "badge study";
        badge.textContent = "🔒 STUDYING";
        btn.textContent = "🔒 Study in Progress (Locked)";
        btn.disabled = true;
        btn.style.backgroundColor = "#1e293b";
        btn.style.color = "#64748b";
        if (btnEnd) {
          btnEnd.style.display = "block";
          btnEnd.textContent = "🛑 End Study Session Early";
        }
      } else if (data.state === "BREAK") {
        badge.className = "badge break";
        badge.textContent = "☕ AI REVIEW";
        btn.textContent = "🔒 Lock In Now";
        btn.disabled = false;
        btn.style.backgroundColor = "#2563eb";
        btn.style.color = "#ffffff";
        if (btnEnd) {
          btnEnd.style.display = "block";
          btnEnd.textContent = "🛑 Return to Idle (End Session)";
        }
      } else {
        badge.className = "badge idle";
        badge.textContent = "💤 IDLE";
        btn.textContent = "🔒 Start Study Session";
        btn.disabled = false;
        btn.style.backgroundColor = "#2563eb";
        btn.style.color = "#ffffff";
        timer.textContent = "50:00";
        if (btnEnd) {
          btnEnd.style.display = "none";
        }
      }
    }
  } catch (e) {
    syncInfo.className = "sync-info disconnected";
    syncInfo.textContent = "⚪ PC App Offline (Launch PC App)";
    timer.textContent = "--:--";
    if (btnEnd) {
      btnEnd.style.display = "none";
    }
  }
}

if (btnEnd) {
  btnEnd.addEventListener("click", async () => {
    const promptMsg = currentState === "BREAK" 
      ? "End break and return to Idle mode?"
      : "Are you sure you want to end your study session early? All blocked websites and desktop applications will be unlocked.";
    if (confirm(promptMsg)) {
      await fetch(ACTION_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "RESET" }),
      });
      fetchStatus();
    }
  });
}

const btnResetState = document.getElementById("btn-reset-state");
if (btnResetState) {
  btnResetState.addEventListener("click", () => {
    if (typeof chrome !== "undefined" && chrome.storage && chrome.storage.local) {
      chrome.storage.local.set({
        lockin_sync_state: {
          connected: false,
          state: "IDLE",
          remaining_seconds: 0,
          server_ip: "127.0.0.1",
        }
      }, () => {
        fetchStatus();
      });
    }
  });
}

btn.addEventListener("click", async () => {
  if (currentState === "IDLE") {
    await fetch(ACTION_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "START_STUDY", duration_minutes: 50 }),
    });
  } else if (currentState === "BREAK") {
    await fetch(ACTION_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "LOCK_IN" }),
    });
  }
  fetchStatus();
});

fetchStatus();
setInterval(fetchStatus, 1000);
