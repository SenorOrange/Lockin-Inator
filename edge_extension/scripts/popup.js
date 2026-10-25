const API_URL = "http://127.0.0.1:8765/api/status";
const ACTION_URL = "http://127.0.0.1:8765/api/action";

const badge = document.getElementById("status-badge");
const timer = document.getElementById("timer-display");
const syncInfo = document.getElementById("sync-status");
const btn = document.getElementById("btn-action");

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
      } else if (data.state === "BREAK") {
        badge.className = "badge break";
        badge.textContent = "☕ AI REVIEW";
        btn.textContent = "🔒 Lock In Now";
        btn.disabled = false;
        btn.style.backgroundColor = "#2563eb";
        btn.style.color = "#ffffff";
      } else {
        badge.className = "badge idle";
        badge.textContent = "💤 IDLE";
        btn.textContent = "🔒 Start Study Session";
        btn.disabled = false;
        btn.style.backgroundColor = "#2563eb";
        btn.style.color = "#ffffff";
        timer.textContent = "50:00";
      }
    }
  } catch (e) {
    syncInfo.className = "sync-info disconnected";
    syncInfo.textContent = "⚪ PC App Offline (Launch PC App)";
    timer.textContent = "--:--";
  }
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
