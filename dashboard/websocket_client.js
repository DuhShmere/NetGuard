const API_BASE = "http://localhost:8000";
const WS_URL   = "ws://localhost:8000/ws/compliance";

async function loadDevices() {
  const res  = await fetch(`${API_BASE}/compliance/`);
  const data = await res.json();
  const tbody = document.getElementById("device-table");

  if (!data.length) {
    tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:#999;padding:2rem">No compliance data yet. Waiting for first poll...</td></tr>';
    return;
  }

  const total = data.reduce((s, d) => s + d.score, 0);
  const violations = data.reduce((s, d) => s + (d.violations?.length || 0), 0);
  document.getElementById("fleet-score").textContent   = Math.round(total / data.length) + "%";
  document.getElementById("device-count").textContent  = data.length;
  document.getElementById("violation-count").textContent = violations;

  tbody.innerHTML = data.map(d => `
    <tr>
      <td>${d.device_id}</td>
      <td>--</td>
      <td>--</td>
      <td><span class="pill ${d.score >= 80 ? 'ok' : d.score >= 50 ? 'medium' : 'high'}">${Math.round(d.score)}%</span></td>
      <td>${d.violations?.length || 0}</td>
      <td>${new Date(d.evaluated_at).toLocaleString()}</td>
    </tr>`).join("");
}

// WebSocket for live updates
function connectWS() {
  const ws = new WebSocket(WS_URL);
  ws.onopen = () => {
    document.getElementById("status").textContent = "Live — connected to compliance feed";
    document.getElementById("status").style.background = "#eaf3de";
  };
  ws.onmessage = (e) => {
    const data = JSON.parse(e.data);
    console.log("Live update:", data);
    loadDevices();
  };
  ws.onclose = () => {
    document.getElementById("status").textContent = "Disconnected — retrying in 5s...";
    document.getElementById("status").style.background = "#fffbe6";
    setTimeout(connectWS, 5000);
  };
}

loadDevices();
connectWS();
