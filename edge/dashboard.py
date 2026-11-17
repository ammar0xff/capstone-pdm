#!/usr/bin/env python3
"""
Intelligent Predictive Maintenance (PdM) - Dual Industrial Dashboard
Offline-first Flask server providing real-time telemetry, SPC charts, and fault diagnostics.
"""

import os
import json
import csv
import time
from flask import Flask, render_template, jsonify, Response, request

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(BASE_DIR, "latest_state.json")
HISTORY_FILE = os.path.join(BASE_DIR, "hot_backup.csv")
CAL_FILE = os.path.join(BASE_DIR, "cal.json")
CLOUD_CONFIG_FILE = os.path.join(BASE_DIR, "cloud_config.json")
CLOUD_BACKLOG_FILE = os.path.join(BASE_DIR, "cloud_backlog.json")

app = Flask(__name__, template_folder=os.path.join(BASE_DIR, "templates"))

def get_cloud_status():
    status = {
        "enabled": True,
        "firebase_url": "https://capstone-pdm-2026-default-rtdb.firebaseio.com/motor1.json",
        "sync_interval_s": 15.0,
        "daily_writes": 0,
        "max_daily_writes": 15000,
        "backlog_count": 0,
        "last_sync_status": "Ready (Quota Guard Active)"
    }
    if os.path.exists(CLOUD_CONFIG_FILE):
        try:
            with open(CLOUD_CONFIG_FILE, 'r') as f:
                cfg = json.load(f)
                status["enabled"] = cfg.get("enabled", True)
                status["firebase_url"] = cfg.get("firebase_url", status["firebase_url"])
                status["daily_writes"] = cfg.get("daily_writes_today", 0)
                status["max_daily_writes"] = cfg.get("max_daily_writes", 15000)
                status["last_sync_status"] = cfg.get("last_sync_status", "Active")
        except Exception:
            pass
    if os.path.exists(CLOUD_BACKLOG_FILE):
        try:
            with open(CLOUD_BACKLOG_FILE, 'r') as bf:
                b = json.load(bf)
                status["backlog_count"] = len(b)
        except Exception:
            pass
    return status

def get_latest_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f:
                data = json.load(f)
                # Check if state is recent (within 5 seconds)
                if time.time() - data.get("timestamp", 0) < 5.0:
                    data["online"] = True
                else:
                    data["online"] = False
                data["cloud"] = get_cloud_status()
                return data
        except Exception:
            pass

    # Default fallback state
    return {
        "timestamp": time.time(),
        "uptime_s": 0,
        "seq": 0,
        "state": "Standby",
        "fault_label": "Initializing DAQ...",
        "fault_proba": 0.0,
        "advice": "Waiting for Edge DAQ service...",
        "online": False,
        "spc": {
            "baseline_mu": 0.08,
            "baseline_sigma": 0.025,
            "ucl_warning": 0.13,
            "ucl_fault": 0.155
        },
        "vibration": {
            "rms_dyn": 0.0,
            "peak_dyn": 0.0,
            "kurtosis": 3.0,
            "g_total": 0.0,
            "ax": 0.0,
            "ay": 0.0,
            "az": 0.0,
            "fs_hz": 0.0
        },
        "temperature": {
            "temp_c": 0.0,
            "slope_c_per_min": 0.0,
            "open_tc": 0
        },
        "system": {
            "adxl_ok": False,
            "max6675_ok": False,
            "storage_ok": True
        }
    }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/latest')
def api_latest():
    return jsonify(get_latest_state())

@app.route('/api/history')
def api_history():
    rows = []
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r') as f:
                reader = csv.DictReader(f)
                all_rows = list(reader)
                # Return last 100 entries
                recent = all_rows[-100:]
                for r in recent:
                    try:
                        rows.append({
                            "t": float(r.get("timestamp", 0)),
                            "rms": float(r.get("rms_dyn", 0)),
                            "temp": float(r.get("temp_c", 0)),
                            "kurt": float(r.get("kurtosis", 3.0)),
                            "state": r.get("state", "Healthy")
                        })
                    except Exception:
                        pass
        except Exception as e:
            return jsonify({"error": str(e), "data": []})
    return jsonify({"count": len(rows), "data": rows})

@app.route('/api/stream')
def api_stream():
    def event_stream():
        while True:
            data = get_latest_state()
            yield f"data: {json.dumps(data)}\n\n"
            time.sleep(0.5)

    return Response(event_stream(), mimetype="text/event-stream")

@app.route('/api/cal', methods=['GET', 'POST'])
def api_cal():
    if request.method == 'POST':
        try:
            new_cal = request.json
            with open(CAL_FILE, 'w') as f:
                json.dump(new_cal, f, indent=2)
            return jsonify({"status": "success", "cal": new_cal})
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 400
    else:
        if os.path.exists(CAL_FILE):
            with open(CAL_FILE, 'r') as f:
                return jsonify(json.load(f))
        return jsonify({})

if __name__ == '__main__':
    print("[INFO] Starting PdM Flask Dashboard on 0.0.0.0:5000")
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
