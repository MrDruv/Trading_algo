from flask import Flask, jsonify, request, render_template_string
from flask_cors import CORS
import json
import os

app = Flask(__name__)
CORS(app)

STATE_FILE = "bot_state.json"

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Quantum Scalper | Hub</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet">
    <style>
        :root { --bg: #0a0b10; --card-bg: #14161f; --accent: #0070f3; --success: #00ff88; --danger: #ff4d4d; --text: #ffffff; --text-dim: #888ea1; --border: #232635; }
        [data-theme="light"] { --bg: #f0f2f5; --card-bg: #ffffff; --accent: #0070f3; --success: #28a745; --danger: #d73a49; --text: #1a1a1a; --text-dim: #6a737d; --border: #e1e4e8; }
        * { box-sizing: border-box; transition: background 0.3s, color 0.3s; }
        body { background-color: var(--bg); color: var(--text); font-family: 'Inter', sans-serif; margin: 0; padding: 20px; display: flex; flex-direction: column; align-items: center; min-height: 100vh; }
        .container { max-width: 900px; width: 100%; }
        .nav { display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px; }
        .logo { font-size: 22px; font-weight: 800; letter-spacing: -1px; }
        .logo span { color: var(--accent); }
        .card { background: var(--card-bg); border: 1px solid var(--border); border-radius: 16px; padding: 24px; box-shadow: 0 4px 20px rgba(0,0,0,0.1); margin-bottom: 20px; }
        .dashboard-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px; }
        h2 { font-size: 12px; text-transform: uppercase; color: var(--text-dim); margin-top: 0; margin-bottom: 15px; letter-spacing: 1px; }
        label { display: block; font-size: 11px; color: var(--text-dim); margin-bottom: 5px; }
        input { width: 100%; background: var(--bg); border: 1px solid var(--border); padding: 10px; border-radius: 8px; color: var(--text); font-family: 'JetBrains Mono', monospace; font-size: 13px; margin-bottom: 10px; }
        .btn { padding: 12px; border-radius: 8px; border: none; font-weight: 600; cursor: pointer; font-size: 13px; width: 100%; }
        .btn-primary { background: var(--accent); color: white; }
        .btn-secondary { background: rgba(128,128,128,0.1); color: var(--text); border: 1px solid var(--border); margin-top: 5px; }
        .btn-success { background: var(--success); color: #000; }
        .btn-danger { background: var(--danger); color: white; }
        .btn-disabled { background: #333 !important; color: #666 !important; cursor: not-allowed !important; }
        .info-row { display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 13px; }
        .info-label { color: var(--text-dim); }
        .info-value { font-weight: 600; font-family: 'JetBrains Mono', monospace; }
        .pnl-value { font-size: 32px; font-weight: 800; font-family: 'JetBrains Mono', monospace; }
        table { width: 100%; border-collapse: collapse; font-size: 12px; margin-top: 15px; }
        th { text-align: left; padding: 12px; background: rgba(128,128,128,0.05); color: var(--text-dim); }
        td { padding: 12px; border-top: 1px solid var(--border); }
        .status-pill { display: inline-flex; align-items: center; gap: 8px; font-size: 12px; font-weight: 700; padding: 6px 16px; border-radius: 100px; background: var(--card-bg); border: 1px solid var(--border); }
        .dot { width: 8px; height: 8px; border-radius: 50%; }
        .dot-active { background: var(--success); box-shadow: 0 0 10px var(--success); }
        .dot-inactive { background: var(--danger); }
    </style>
</head>
<body data-theme="dark">
    <div class="container">
        <div class="nav">
            <div class="logo">QUANTUM<span>SCALPER</span></div>
            <div style="display:flex; gap:10px">
                <button style="background:var(--card-bg); color:var(--text); border:1px solid var(--border); padding:8px 15px; border-radius:8px; cursor:pointer" onclick="toggleTheme()" id="theme-btn">🌙 Dark</button>
                <div class="status-pill">
                    <div id="conn-dot" class="dot dot-inactive"></div>
                    MT5: <span id="conn-text">DISCONNECTED</span>
                </div>
            </div>
        </div>

        <div class="dashboard-grid">
            <div class="card">
                <h2>Account Information</h2>
                <div class="info-row"><span class="info-label">Login ID</span><span class="info-value" id="acc-id">---</span></div>
                <div class="info-row"><span class="info-label">Broker</span><span class="info-value" id="acc-broker">---</span></div>
                <div class="info-row"><span class="info-label">Balance</span><span class="info-value" id="acc-balance">$0.00</span></div>
                <div class="info-row"><span class="info-label">Leverage</span><span class="info-value" id="acc-leverage">1:---</span></div>
            </div>

            <div class="card">
                <h2>Terminal Link</h2>
                <input type="text" id="mt5-path" placeholder="terminal64.exe path">
                <button id="connect-btn" class="btn btn-primary">Connect MT5</button>
                <button id="disconnect-btn" class="btn btn-secondary">Disconnect</button>
            </div>
        </div>

        <div class="dashboard-grid">
            <div class="card" style="text-align:center">
                <h2>Algo Engine</h2>
                <label style="text-align:left">Volume (Lots)</label>
                <input type="number" id="lot-size" step="0.01">
                <div id="algo-status" style="font-weight:700; margin-bottom:10px">STANDBY</div>
                <button id="toggle-btn" class="btn btn-success">ACTIVATE ALGO</button>
            </div>

            <div class="card" style="text-align:center">
                <h2>Session Analysis</h2>
                <div id="pnl-text" class="pnl-value">$0.00</div>
                <div class="info-row" style="justify-content: center; gap: 20px; margin-top: 10px;">
                    <div><span class="info-label">Win Rate:</span> <span id="win-rate" style="color:var(--success); font-weight:700">0%</span></div>
                    <div><span class="info-label">Trades:</span> <span id="total-trades" style="font-weight:700">0</span></div>
                </div>
            </div>
        </div>

        <div class="card">
            <h2>Order History</h2>
            <table>
                <thead><tr><th>TIME</th><th>TYPE</th><th>PRICE</th><th>PNL</th></tr></thead>
                <tbody id="history-body"></tbody>
            </table>
        </div>
    </div>

    <script>
        function toggleTheme() {
            const b = document.body;
            const t = b.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
            b.setAttribute('data-theme', t);
            document.getElementById('theme-btn').innerText = t === 'dark' ? '🌙 Dark' : '☀️ Light';
            localStorage.setItem('theme', t);
        }
        if (localStorage.getItem('theme')) {
            const t = localStorage.getItem('theme');
            document.body.setAttribute('data-theme', t);
            document.getElementById('theme-btn').innerText = t === 'dark' ? '🌙 Dark' : '☀️ Light';
        }

        async function refresh() {
            const r = await fetch('/api/state');
            const s = await r.json();
            
            if (!window.uiInit) {
                document.getElementById('mt5-path').value = s.terminal_path || "";
                document.getElementById('lot-size').value = s.lots || 0.50;
                window.uiInit = true;
            }

            document.getElementById('acc-id').innerText = s.account?.id || "---";
            document.getElementById('acc-broker').innerText = s.account?.broker || "---";
            document.getElementById('acc-balance').innerText = "$" + (s.account?.balance || 0).toFixed(2);
            document.getElementById('acc-leverage').innerText = "1:" + (s.account?.leverage || "---");

            document.getElementById('conn-dot').className = "dot " + (s.connected ? "dot-active" : "dot-inactive");
            document.getElementById('conn-text').innerText = s.connected ? "CONNECTED" : "DISCONNECTED";
            document.getElementById('conn-text').style.color = s.connected ? "var(--success)" : "var(--danger)";

            const tb = document.getElementById('toggle-btn');
            const as = document.getElementById('algo-status');
            
            if (!s.connected) {
                as.innerText = "WAITING FOR CONNECTION";
                as.style.color = "var(--text-dim)";
                tb.innerText = "CONNECT MT5 FIRST";
                tb.className = "btn btn-disabled";
                tb.disabled = true;
            } else {
                as.innerText = s.active ? "ALGO: ACTIVE" : "ALGO: STANDBY";
                as.style.color = s.active ? "var(--success)" : "var(--text-dim)";
                tb.innerText = s.active ? "STOP ALGO" : "START ALGO";
                tb.className = "btn " + (s.active ? "btn-danger" : "btn-success");
                tb.disabled = false;
            }

            document.getElementById('pnl-text').innerText = (s.total_pnl >= 0 ? "+" : "") + "$" + s.total_pnl.toFixed(2);
            document.getElementById('pnl-text').style.color = s.total_pnl >= 0 ? "var(--success)" : "var(--danger)";

            const closed = s.history.filter(t => t.profit !== 0);
            document.getElementById('win-rate').innerText = closed.length > 0 ? ((closed.filter(t => t.profit > 0).length / closed.length) * 100).toFixed(1) + "%" : "0.0%";
            document.getElementById('total-trades').innerText = closed.length;

            document.getElementById('history-body').innerHTML = s.history.slice().reverse().map(t => `
                <tr>
                    <td style="color:var(--text-dim)">${t.time}</td>
                    <td style="font-weight:700; color:${t.type=='BUY'?'var(--accent)':'#f44336'}">${t.type}</td>
                    <td>${t.price.toFixed(2)}</td>
                    <td style="color:${t.profit>=0?'var(--success)':'var(--danger)'}; font-weight:700">${t.profit>=0?'+':''}${t.profit.toFixed(2)}</td>
                </tr>
            `).join('');
        }

        document.getElementById('connect-btn').onclick = async () => {
            const p = document.getElementById('mt5-path').value;
            await fetch('/api/settings', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ terminal_path: p, connect_intent: true }) });
        };
        document.getElementById('disconnect-btn').onclick = async () => { await fetch('/api/disconnect', { method: 'POST' }); };
        document.getElementById('toggle-btn').onclick = async () => {
            const lots = document.getElementById('lot-size').value;
            await fetch('/api/settings', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ lots: parseFloat(lots) }) });
            await fetch('/api/toggle', { method: 'POST' });
        };

        setInterval(refresh, 1000);
        refresh();
    </script>
</body>
</html>
"""

def get_state():
    if not os.path.exists(STATE_FILE):
        initial = {"active": False, "connected": False, "connect_intent": False, "terminal_path": "", "lots": 0.50, "history": [], "total_pnl": 0.0, "account": {}}
        with open(STATE_FILE, 'w') as f: json.dump(initial, f)
        return initial
    try:
        with open(STATE_FILE, 'r') as f: return json.load(f)
    except: return {"active": False, "connected": False, "connect_intent": False, "terminal_path": "", "lots": 0.50, "history": [], "total_pnl": 0.0, "account": {}}

@app.route('/')
def index(): return render_template_string(HTML_TEMPLATE)

@app.route('/api/state')
def api_state(): return jsonify(get_state())

@app.route('/api/settings', methods=['POST'])
def api_settings():
    data = request.json
    state = get_state()
    if "terminal_path" in data:
        state["terminal_path"] = data["terminal_path"]
        state["connect_intent"] = True 
    if "lots" in data: state["lots"] = data["lots"]
    with open(STATE_FILE, 'w') as f: json.dump(state, f)
    return jsonify(state)

@app.route('/api/disconnect', methods=['POST'])
def api_disconnect():
    state = get_state()
    state["connected"] = False
    state["connect_intent"] = False
    state["active"] = False 
    state["account"] = {}
    with open(STATE_FILE, 'w') as f: json.dump(state, f)
    return jsonify(state)

@app.route('/api/toggle', methods=['POST'])
def api_toggle():
    state = get_state()
    state["active"] = not state["active"]
    with open(STATE_FILE, 'w') as f: json.dump(state, f)
    return jsonify(state)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
