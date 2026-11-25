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
import http.client
import urllib.parse

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(os.environ.get("G12_STATE_DIR") or BASE_DIR, "latest_state.json")
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

# G12 latency options. All default to the previous behaviour (opt-in via environment).
LIGHT_PAYLOAD = os.environ.get("G12_MIRROR_LIGHT", "0") == "1"   # omit the static 'equations' block (about 70% of bytes); the hosted dashboard does not read it
KEEPALIVE = os.environ.get("G12_MIRROR_KEEPALIVE", "0") == "1"   # reuse one HTTPS connection instead of a new TLS handshake per write
_INTERVAL_ENV = os.environ.get("G12_MIRROR_INTERVAL_S")          # optional override of sync_interval_s (seconds)
_conn = None

def put_json(url, body, timeout):
    """PUT body, return HTTP status. Persistent connection when KEEPALIVE is on."""
    global _conn
    if not KEEPALIVE:
        rq = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="PUT")
        with urllib.request.urlopen(rq, timeout=timeout) as r:
            return r.status
    u = urllib.parse.urlsplit(url)
    path = u.path + (("?" + u.query) if u.query else "")
    for attempt in (0, 1):
        try:
            if _conn is None:
                cls = http.client.HTTPSConnection if u.scheme == "https" else http.client.HTTPConnection
                _conn = cls(u.netloc, timeout=timeout)
            _conn.request("PUT", path, body=body, headers={"Content-Type": "application/json"})
            r = _conn.getresponse(); r.read()
            return r.status
        except Exception as e:
            try: _conn.close()
            except Exception: pass
            _conn = None
            if attempt == 1:
                raise urllib.error.URLError(e)

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
    """Immediate save (settings changes, midnight reset, clean shutdown). Atomic via temp file + rename."""
    try:
        tmp = CONFIG_FILE + ".tmp"
        with open(tmp, 'w') as f:
            json.dump(cfg, f, indent=2)
        os.replace(tmp, CONFIG_FILE)
    except Exception:
        pass

# G12: the per-PUT save forced an ext4 journal commit every 5 s on a slow SD card.
# Throttled save: write at most every SAVE_EVERY_S, or at once when the status text changes.
# The daily write counter is never reset by this: a clean stop flushes it exactly; after an unclean stop
# it is rounded UP on load by the writes that could have gone unsaved, so the guard never under-counts.
SAVE_EVERY_S = float(os.environ.get("G12_CONFIG_SAVE_EVERY_S", "0"))   # 0 keeps the old save-per-PUT behaviour
_last_save = 0.0
_last_status = None
_cfg_ref = None

def save_cloud_config_throttled(cfg):
    global _last_save, _last_status
    now = time.time()
    if SAVE_EVERY_S <= 0 or now - _last_save >= SAVE_EVERY_S or cfg.get("last_sync_status") != _last_status:
        cfg["clean_shutdown"] = False
        save_cloud_config(cfg)
        _last_save = now
        _last_status = cfg.get("last_sync_status")

def flush_config_on_exit(*_a):
    if _cfg_ref is not None and SAVE_EVERY_S > 0:
        _cfg_ref["clean_shutdown"] = True
        save_cloud_config(_cfg_ref)

def sync_loop():
    print("=" * 65)
    print("  Predictive Maintenance (PdM) - Firebase RTDB 0-EGP Cloud Mirror")
    print("  Free-Tier Spark Lock | Quota Guard Active (<15k writes/day)")
    print("=" * 65)

    global _cfg_ref
    config = load_cloud_config()
    if SAVE_EVERY_S > 0 and config.get("last_day") == time.strftime("%Y-%m-%d") and config.get("clean_shutdown") is not True:
        # previous run did not flush: round the counter up by the writes that may have gone unsaved
        config["daily_writes_today"] = int(config.get("daily_writes_today", 0)) + int(SAVE_EVERY_S / max(float(_INTERVAL_ENV) if _INTERVAL_ENV else float(config.get("sync_interval_s", 5.0)), 0.05)) + 2
    config["clean_shutdown"] = False
    save_cloud_config(config)
    _cfg_ref = config
    import signal, atexit
    signal.signal(signal.SIGTERM, lambda *a: (flush_config_on_exit(), sys.exit(0)))
    atexit.register(flush_config_on_exit)
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
        time.sleep(float(_INTERVAL_ENV) if _INTERVAL_ENV else config.get("sync_interval_s", 15.0))

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
            "proba": data.get("fault_proba"),
            "proba_source": data.get("fault_proba_source"),
            "input_valid": data.get("input_valid"),
            "rf_executed": data.get("rf_executed"),
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

        if LIGHT_PAYLOAD:
            payload.pop("equations", None)
        # Attempt HTTPS PUT to Firebase RTDB
        req_data = json.dumps(payload).encode('utf-8')
        try:
            status = put_json(config["firebase_url"], req_data, 5)
            if status in (200, 204):
                config["daily_writes_today"] += 1
                config["last_sync_status"] = f"OK (HTTP {status})"
                config["last_sync_time"] = time.time()
                save_cloud_config_throttled(config)
                print(f"[FIREBASE] Synced frame seq={payload['seq']} | Writes today: {config['daily_writes_today']}/{config['max_daily_writes']}", flush=True)
                # Flushed successfully; clear backlog
                if backlog:
                    backlog.clear()
                    if os.path.exists(BACKLOG_FILE):
                        os.remove(BACKLOG_FILE)
        except urllib.error.URLError as e:
            # Offline Survival (PRD §0.3 F5 / §6.1 F3): Queue locally without crash
            config["last_sync_status"] = f"Offline Buffering: {str(e)[:30]}"
            save_cloud_config_throttled(config)
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
            save_cloud_config_throttled(config)

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
