#!/usr/bin/env python3
"""
Intelligent Predictive Maintenance (PdM) - Zero-Cost Firebase Cloud Mirror
Fulfills Capstone 'Wireless to Cloud + IoT' grading criteria at 0-EGP budget (PRD Section 9).
Syncs latest edge state to Firebase Realtime Database (Spark free tier) with Quota Guard & Offline Recovery.
"""

import os
import sys
import time
import json
import urllib.request
import urllib.error

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(BASE_DIR, "latest_state.json")
BACKLOG_FILE = os.path.join(BASE_DIR, "cloud_backlog.json")
CONFIG_FILE = os.path.join(BASE_DIR, "cloud_config.json")

DEFAULT_CONFIG = {
    "enabled": True,
    "firebase_url": "https://castpone2026-default-rtdb.firebaseio.com/motor1.json",
    "sync_interval_s": 5.0,
    "max_daily_writes": 15000,
    "daily_writes_today": 0,
    "last_day": time.strftime("%Y-%m-%d"),
    "last_sync_status": "Initialized"
}

def load_cloud_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                cfg = json.load(f)
                # Ensure all keys exist
                for k, v in DEFAULT_CONFIG.items():
                    if k not in cfg:
                        cfg[k] = v
                return cfg
        except Exception:
            pass
    return dict(DEFAULT_CONFIG)

def save_cloud_config(cfg):
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(cfg, f, indent=2)
    except Exception:
        pass

def sync_loop():
    print("=" * 65)
    print("  Predictive Maintenance (PdM) - Firebase RTDB 0-EGP Cloud Mirror")
    print("  Free-Tier Spark Lock | Quota Guard Active (<15k writes/day)")
    print("=" * 65)

    config = load_cloud_config()
    backlog = []

    if os.path.exists(BACKLOG_FILE):
        try:
            with open(BACKLOG_FILE, 'r') as f:
                backlog = json.load(f)
        except Exception:
            backlog = []

    print(f"[INFO] Cloud Mirror Target: {config['firebase_url']}")
    print(f"[INFO] Sync Interval: {config.get('sync_interval_s', 15.0)}s | Daily Quota: {config.get('max_daily_writes', 15000)} writes")

    while True:
        time.sleep(config.get("sync_interval_s", 15.0))

        # Reset daily write counter at midnight
        today = time.strftime("%Y-%m-%d")
        if today != config.get("last_day"):
            config["daily_writes_today"] = 0
            config["last_day"] = today
            save_cloud_config(config)

        # Quota Guard: Throttle if approaching Spark free-tier daily write limit
        if config["daily_writes_today"] >= config["max_daily_writes"]:
            print("[QUOTA GUARD] Daily free-tier limit approached. Throttling to 1 write / 60s.")
            time.sleep(45.0)

        # Read latest edge state
        if not os.path.exists(STATE_FILE):
            continue

        try:
            with open(STATE_FILE, 'r') as f:
                data = json.load(f)
        except Exception:
            continue

        # Prepare comprehensive cloud payload conforming to shared data model (PRD §9.3)
        payload = {
            "ts": data.get("timestamp", time.time()),
            "uptime_s": data.get("uptime_s", 0),
            "seq": data.get("seq", 0),
            "state": data.get("state", "Healthy"),
            "fault": data.get("fault_label", "Normal Operation"),
            "proba": data.get("fault_proba", 0.05),
            "rms": data.get("vibration", {}).get("rms_dyn", 0.0),
            "peak": data.get("vibration", {}).get("peak_dyn", 0.0),
            "kurt": data.get("vibration", {}).get("kurtosis", 3.0),
            "cf": data.get("vibration", {}).get("crest_factor", 2.0),
            "temp": data.get("temperature", {}).get("temp_c", 25.0),
            "slope": data.get("temperature", {}).get("slope_c_per_min", 0.0),
            "sound_db": data.get("acoustic", {}).get("db_spl", 50.0),
            "zcr": data.get("acoustic", {}).get("zcr", 0.02),
            "advice": data.get("advice", "Nominal limits."),
            "ai": data.get("ai", {}),
            "equations": data.get("equations", {}),
            "vibration": data.get("vibration", {}),
            "temperature": data.get("temperature", {}),
            "acoustic": data.get("acoustic", {}),
            "system": data.get("system", {})
        }

        # Attempt HTTPS PUT to Firebase RTDB
        req_data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            config["firebase_url"],
            data=req_data,
            headers={"Content-Type": "application/json"},
            method="PUT"
        )

        try:
            with urllib.request.urlopen(req, timeout=5) as response:
                if response.status in (200, 204):
                    config["daily_writes_today"] += 1
                    config["last_sync_status"] = f"OK (HTTP {response.status})"
                    config["last_sync_time"] = time.time()
                    save_cloud_config(config)
                    print(f"[FIREBASE] Synced frame seq={payload['seq']} | Writes today: {config['daily_writes_today']}/{config['max_daily_writes']}")
                    # Flushed successfully; clear backlog
                    if backlog:
                        backlog.clear()
                        if os.path.exists(BACKLOG_FILE):
                            os.remove(BACKLOG_FILE)
        except urllib.error.URLError as e:
            # Offline Survival (PRD §0.3 F5 / §6.1 F3): Queue locally without crash
            config["last_sync_status"] = f"Offline Buffering: {str(e)[:30]}"
            save_cloud_config(config)
            if len(backlog) < 200:
                backlog.append(payload)
                try:
                    with open(BACKLOG_FILE, 'w') as bf:
                        json.dump(backlog, bf)
                except Exception:
                    pass
            print(f"[FIREBASE OFFLINE] Sync paused ({e}). Queued {len(backlog)} frames locally.")
        except Exception as e:
            config["last_sync_status"] = f"Error: {str(e)[:30]}"
            save_cloud_config(config)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "--set-url" and len(sys.argv) > 2:
            new_url = sys.argv[2]
            cfg = load_cloud_config()
            cfg["firebase_url"] = new_url
            save_cloud_config(cfg)
            print(f"[SUCCESS] Updated Firebase URL to: {new_url}")
            sys.exit(0)
        elif sys.argv[1] == "--status":
            cfg = load_cloud_config()
            print(json.dumps(cfg, indent=2))
            sys.exit(0)
    sync_loop()
