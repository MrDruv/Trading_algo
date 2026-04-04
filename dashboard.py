from flask import Flask, jsonify, request, render_template_string
from flask_cors import CORS
import json
import os

app = Flask(__name__)
CORS(app)

STATE_FILE = "bot_state.json"
DEFAULT_PATH = r"C:\Users\HP Power\AppData\Roaming\FundedNext MT5 Terminal\terminal64.exe"

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Quantum Scalper | Command Center</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg: #0a0b10;
            --card-bg: #14161f;
            --accent: #0070f3;
            --success: #00ff88;
            --danger: #ff4d4d;
            --text: #ffffff;
            --text-dim: #888ea1;
            --border: #232635;
        }
        
        * { box-sizing: border-box; transition: all 0.2s ease; }
        body { 
            background-color: var(--bg); 
            color: var(--text); 
            font-family: 'Inter', sans-serif; 
            margin: 0; 
            padding: 20px;
            display: flex;
            flex-direction: column;
            align-items: center;
        }

        .container { max-width: 900px; width: 100%; }
        
        .nav { 
            display: flex; 
            justify-content: space-between; 
            align-items: center; 
            width: 100%; 
            margin-bottom: 40px;
            padding: 0 10px;
        }
        
        .logo { font-size: 22px; font-weight: 800; letter-spacing: -1px; }
        .logo span { color: var(--accent); }

        .dashboard-grid {
            display: grid;
            grid-template-columns: 1.5fr 1fr;
            gap: 20px;
            margin-bottom: 20px;
        }

        .card {
            background: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 24px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
        }

        h2 { font-size: 14px; text-transform: uppercase; color: var(--text-dim); margin-top: 0; margin-bottom: 20px; letter-spacing: 1px; }

        input {
            width: 100%;
            background: #0a0b10;
            border: 1px solid var(--border);
            padding: 12px 16px;
            border-radius: 8px;
            color: white;
            font-family: 'JetBrains Mono', monospace;
            font-size: 13px;
            margin-bottom: 15px;
        }

        input:focus { border-color: var(--accent); outline: none; box-shadow: 0 0 0 3px rgba(0,112,243,0.2); }

        .btn-group { display: flex; gap: 10px; }
        .btn {
            flex: 1;
            padding: 12px;
            border-radius: 8px;
            border: none;
            font-weight: 600;
            cursor: pointer;
            font-size: 13px;
        }

        .btn-primary { background: var(--accent); color: white; }
        .btn-secondary { background: rgba(255,255,255,0.05); color: white; border: 1px solid var(--border); }
        .btn-danger { background: var(--danger); color: white; }
        .btn-success { background: var(--success); color: #000; }
        .btn:hover { transform: translateY(-2px); filter: brightness(1.1); }
        .btn:active { transform: translateY(0); }
        .btn:disabled { opacity: 0.5; cursor: not-allowed; }

        .status-pill {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            font-size: 12px;
            font-weight: 700;
            padding: 4px 12px;
            border-radius: 100px;
            background: rgba(255,255,255,0.05);
        }
        
        .dot { width: 8px; height: 8px; border-radius: 50%; }
        .dot-active { background: var(--success); box-shadow: 0 0 10px var(--success); animation: pulse 2s infinite; }
        .dot-inactive { background: var(--danger); }

        .pnl-value { font-size: 48px; font-weight: 800; font-family: 'JetBrains Mono', monospace; margin: 10px 0; }
        
        .table-container { margin-top: 20px; overflow: hidden; border-radius: 12px; border: 1px solid var(--border); }
        table { width: 100%; border-collapse: collapse; background: var(--card-bg); font-size: 13px; }
        th { text-align: left; padding: 16px; background: rgba(255,255,255,0.02); color: var(--text-dim); font-weight: 400; }
        td { padding: 16px; border-top: 1px solid var(--border); }
        
        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.4; }
            100% { opacity: 1; }
        }

        @media (max-width: 768px) {
            .dashboard-grid { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="nav">
            <div class="logo">QUANTUM<span>SCALPER</span></div>
            <div class="status-pill">
                <div id="conn-dot" class="dot dot-inactive"></div>
                MT5: <span id="conn-text">DISCONNECTED</span>
            </div>
        </div>

        <div class="dashboard-grid">
            <div class="card">
                <h2>Terminal Configuration</h2>
                <input type="text" id="mt5-path" placeholder="Path to MetaTrader 5 (terminal64.exe)">
                <div class="btn-group">
                    <button id="connect-btn" class="btn btn-primary">Initialize Connection</button>
                    <button id="disconnect-btn" class="btn btn-secondary">Terminate Link</button>
                </div>
            </div>

            <div class="card" style="display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center;">
                <h2>Algorithm Engine</h2>
                <div id="algo-status" style="font-size: 18px; font-weight: 700; margin-bottom: 15px;">STANDBY</div>
                <button id="toggle-btn" class="btn btn-success" style="width: 100%; padding: 16px;">ACTIVATE SYSTEM</button>
            </div>
        </div>

        <div class="card">
            <div style="display:flex; justify-content: space-between; align-items: flex-start;">
                <div>
                    <h2>Real-time Performance</h2>
                    <div id="pnl-text" class="pnl-value">$0.00</div>
                </div>
                <div style="text-align: right">
                    <h2 style="margin-bottom: 5px;">Active Asset</h2>
                    <div style="font-weight: 700; color: var(--accent)">BTCUSD (M1)</div>
                </div>
            </div>

            <div class="table-container">
                <table>
                    <thead>
                        <tr>
                            <th>TIMESTAMP</th>
                            <th>OPERATION</th>
                            <th>PRICE</th>
                            <th>PNL (USD)</th>
                        </tr>
                    </thead>
                    <tbody id="history-body"></tbody>
                </table>
            </div>
        </div>
    </div>

    <script>
        async function refresh() {
            const r = await fetch('/api/state');
            const s = await r.json();
            
            // Connection UI
            const pathInput = document.getElementById('mt5-path');
            if (!pathInput.value && !window.pathSet) {
                pathInput.value = s.terminal_path;
                window.pathSet = true;
            }
            
            const dot = document.getElementById('conn-dot');
            const ct = document.getElementById('conn-text');
            dot.className = "dot " + (s.connected ? "dot-active" : "dot-inactive");
            ct.innerText = s.connected ? "CONNECTED" : "DISCONNECTED";
            ct.style.color = s.connected ? "var(--success)" : "var(--danger)";

            // Algo UI
            const as = document.getElementById('algo-status');
            const tb = document.getElementById('toggle-btn');
            as.innerText = s.active ? "CORE SYSTEM: RUNNING" : "CORE SYSTEM: STANDBY";
            as.style.color = s.active ? "var(--success)" : "var(--text-dim)";
            tb.innerText = s.active ? "EMERGENCY STOP" : "ACTIVATE SYSTEM";
            tb.className = "btn " + (s.active ? "btn-danger" : "btn-success");
            tb.disabled = !s.connected;

            // PNL UI
            const pt = document.getElementById('pnl-text');
            pt.innerText = (s.total_pnl >= 0 ? "+" : "") + "$" + s.total_pnl.toFixed(2);
            pt.style.color = s.total_pnl >= 0 ? "var(--success)" : "var(--danger)";

            // History UI
            const body = document.getElementById('history-body');
            body.innerHTML = "";
            s.history.slice().reverse().forEach(t => {
                const pnlColor = t.profit >= 0 ? "var(--success)" : "var(--danger)";
                body.innerHTML += `<tr>
                    <td style="color: var(--text-dim); font-family: 'JetBrains Mono'">${t.time}</td>
                    <td style="font-weight:700; color:${t.type=='BUY'?'var(--accent)':'#f44336'}">${t.type}</td>
                    <td style="font-family: 'JetBrains Mono'">${t.price.toFixed(2)}</td>
                    <td style="color:${pnlColor}; font-family: 'JetBrains Mono'; font-weight:700">${t.profit >= 0 ? '+' : ''}${t.profit.toFixed(2)}</td>
                </tr>`;
            });
        }

        document.getElementById('connect-btn').onclick = async () => {
            const p = document.getElementById('mt5-path').value;
            await fetch('/api/settings', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ terminal_path: p })
            });
        };

        document.getElementById('disconnect-btn').onclick = async () => {
            await fetch('/api/disconnect', { method: 'POST' });
        };

        document.getElementById('toggle-btn').onclick = async () => {
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
        initial = {"active": False, "connected": False, "terminal_path": DEFAULT_PATH, "history": [], "total_pnl": 0.0}
        with open(STATE_FILE, 'w') as f: json.dump(initial, f)
        return initial
    try:
        with open(STATE_FILE, 'r') as f: return json.load(f)
    except: return {"active": False, "connected": False, "terminal_path": DEFAULT_PATH, "history": [], "total_pnl": 0.0}

@app.route('/')
def index(): return render_template_string(HTML_TEMPLATE)

@app.route('/api/state')
def api_state(): return jsonify(get_state())

@app.route('/api/settings', methods=['POST'])
def api_settings():
    data = request.json
    state = get_state()
    state["terminal_path"] = data.get("terminal_path", state["terminal_path"])
    state["connected"] = True 
    with open(STATE_FILE, 'w') as f: json.dump(state, f)
    return jsonify(state)

@app.route('/api/disconnect', methods=['POST'])
def api_disconnect():
    state = get_state()
    state["connected"] = False
    state["active"] = False 
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
