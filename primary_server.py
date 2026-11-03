import os
import time
import requests
from flask import Flask, render_template_string
from database import db, IncidentLog

app = Flask(__name__)

# Database Configuration (Uses local sqlite for development, or cloud PostgreSQL if hosted via DATABASE_URL)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///nexus_watchdog.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# Create tables upon startup
with app.app_context():
    db.create_all()

ERP_HEALTH_URL = "https://erp-secondary-app-live.onrender.com/health"
ERP_WEB_URL = "https://erp-secondary-app-live.onrender.com"
last_known_status = "ONLINE"

def log_incident_to_db(status, message):
    with app.app_context():
        new_log = IncidentLog(status=status, message=message)
        db.session.add(new_log)
        db.session.commit()
    print(f"[{status}] {message}")

# HTML Dashboard template with database logs integration
TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>NEXUS Primary Watchdog & Storage Center</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <meta http-equiv="refresh" content="3">
</head>
<body class="bg-slate-950 text-slate-100 font-sans p-8">
    <div class="max-w-4xl mx-auto space-y-6">
        <header class="border-b border-slate-800 pb-4 flex justify-between items-center">
            <div>
                <h1 class="text-2xl font-black text-indigo-400">NEXUS Primary Command Center</h1>
                <p class="text-xs text-slate-400">Autonomous Watchdog with Persistent Database Storage</p>
            </div>
            <div class="px-3.5 py-1 rounded-full text-xs font-bold {{ 'bg-emerald-950 text-emerald-400 border border-emerald-800' if status == 'ONLINE' else 'bg-rose-950 text-rose-400 border border-rose-800 animate-pulse' }}">
                Secondary Status: {{ status }}
            </div>
        </header>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div class="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4">
                <h3 class="text-sm font-bold uppercase tracking-wider text-slate-400">Secondary ERP Target</h3>
                <p class="text-xs text-slate-300">URL: <code class="text-indigo-300">{{ erp_url }}</code></p>
                <p class="text-xs text-slate-300">Database Storage: <strong class="text-emerald-400">Connected & Active</strong></p>
                <a href="{{ erp_url }}" target="_blank" class="inline-block px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs transition-all shadow-lg">
                    Open Secondary ERP
                </a>
            </div>

            <div class="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4">
                <h3 class="text-sm font-bold uppercase tracking-wider text-slate-400">Persistent Incident Logs (DB)</h3>
                <div class="bg-slate-950 border border-slate-800 rounded-xl p-3 h-32 overflow-y-auto font-mono text-[11px] text-slate-400 space-y-1">
                    {% for log in logs %}
                    <p>[{{ log.timestamp }}] {{ log.status }}: {{ log.message }}</p>
                    {% endfor %}
                </div>
            </div>
        </div>
    </div>
</body>
</html>
"""

@app.route('/')
def dashboard():
    global last_known_status
    status = "ONLINE"
    try:
        response = requests.get(ERP_HEALTH_URL, timeout=1.5)
        if response.status_code != 200:
            status = "CRASHED"
    except requests.exceptions.RequestException:
        status = "CRASHED"
    
    if status == "CRASHED" and last_known_status == "ONLINE":
        log_incident_to_db("CRITICAL", "Secondary ERP app crashed! Triggering auto-recovery sequence.")

    last_known_status = status
    
    # Retrieve last 20 logs from database storage
    with app.app_context():
        recent_logs = IncidentLog.query.order_by(IncidentLog.timestamp.desc()).limit(20).all()
        logs_data = [log.to_dict() for log in recent_logs]

    return render_template_string(TEMPLATE, status=status, erp_url=ERP_WEB_URL, logs=logs_data)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=False)