#!/usr/bin/env python3
"""
Live Edge Telemetry Uplink Streamer
Streams continuous real-time physics telemetry packets to Firebase RTDB.
Usage:
  python3 edge/stream_live.py [--scenario healthy|imbalance|bearing|thermal] [--interval 2.5]
"""

import sys
import time
import math
import random
import json
import urllib.request
import argparse

FIREBASE_URL = "https://castpone2026-default-rtdb.firebaseio.com/motor1.json"

def stream(scenario="healthy", interval=2.5):
    print("=" * 65)
    print("  Predictive Maintenance SCADA - Live Cloud Uplink Streamer")
    print(f"  Target: {FIREBASE_URL}")
    print(f"  Initial Scenario: {scenario.upper()} | Push Interval: {interval}s")
    print("  Press Ctrl+C to stop streaming.")
    print("=" * 65)

    step = 0
    start_time = time.time()

    while True:
        step += 1
        now = time.time()
        uptime = round(now - start_time, 1)

        if scenario == 'healthy':
            rms = 0.0080 + random.uniform(0.0005, 0.0035)
            peak = rms * random.uniform(1.8, 2.3)
            frame = {
                "ts": now,
                "seq": 3100 + step,
                "uptime_s": uptime,
                "state": "Healthy",
                "fault": "Normal Operation",
                "proba": 0.03,
                "rms": round(rms, 4),
                "peak": round(peak, 4),
                "kurt": round(2.95 + random.uniform(-0.1, 0.25), 2),
                "cf": round(peak / rms, 2),
                "temp": round(24.5 + math.sin(step * 0.1) * 0.4, 2),
                "slope": round(0.02 + random.uniform(-0.05, 0.05), 2),
                "sound_db": round(58.0 + random.uniform(0, 4.0), 1),
                "zcr": round(0.018 + random.uniform(0, 0.005), 4),
                "advice": "Machine operating within nominal limits. Continuous baseline monitoring active."
            }
        elif scenario == 'imbalance':
            rms = 0.235 + random.uniform(-0.02, 0.03)
            peak = rms * random.uniform(2.1, 2.5)
            frame = {
                "ts": now,
                "seq": 3100 + step,
                "uptime_s": uptime,
                "state": "Warning",
                "fault": "Mechanical Imbalance & Looseness",
                "proba": 0.94,
                "rms": round(rms, 4),
                "peak": round(peak, 4),
                "kurt": round(3.2 + random.uniform(-0.2, 0.3), 2),
                "cf": round(peak / rms, 2),
                "temp": round(36.5 + math.sin(step * 0.1) * 1.5, 2),
                "slope": round(0.85 + random.uniform(0, 0.2), 2),
                "sound_db": round(78.5 + random.uniform(0, 3.0), 1),
                "zcr": round(0.042 + random.uniform(0, 0.01), 4),
                "advice": "Elevated 1X rotational vibration detected. Inspect rotor balance and bolt torque."
            }
        elif scenario == 'bearing':
            rms = 0.138 + random.uniform(-0.015, 0.025)
            peak = rms * random.uniform(5.0, 7.5)
            frame = {
                "ts": now,
                "seq": 3100 + step,
                "uptime_s": uptime,
                "state": "Fault",
                "fault": "Bearing Raceway Defect (BPFO)",
                "proba": 0.98,
                "rms": round(rms, 4),
                "peak": round(peak, 4),
                "kurt": round(8.8 + random.uniform(0, 3.5), 2),
                "cf": round(peak / rms, 2),
                "temp": round(46.0 + math.sin(step * 0.1) * 2.0, 2),
                "slope": round(2.4 + random.uniform(0, 0.5), 2),
                "sound_db": round(86.0 + random.uniform(0, 4.0), 1),
                "zcr": round(0.265 + random.uniform(0, 0.04), 4),
                "advice": "High-frequency impulse shocks matching BPFO. Schedule bearing replacement immediately."
            }
        else: # thermal
            rms = 0.095 + random.uniform(-0.01, 0.02)
            peak = rms * random.uniform(1.9, 2.4)
            frame = {
                "ts": now,
                "seq": 3100 + step,
                "uptime_s": uptime,
                "state": "Fault",
                "fault": "Thermal Runaway & Lubrication Starvation",
                "proba": 0.99,
                "rms": round(rms, 4),
                "peak": round(peak, 4),
                "kurt": round(3.1 + random.uniform(-0.1, 0.2), 2),
                "cf": round(peak / rms, 2),
                "temp": round(72.0 + (step % 50) * 0.5, 2),
                "slope": round(14.5 + random.uniform(-1.0, 2.0), 2),
                "sound_db": round(88.5 + random.uniform(0, 4.0), 1),
                "zcr": round(0.065 + random.uniform(0, 0.02), 4),
                "advice": "Critical casing temperature rise (dT/dt > 10°C/min). Trip motor to prevent bearing seizure."
            }

        data_bytes = json.dumps(frame).encode('utf-8')
        req = urllib.request.Request(FIREBASE_URL, data=data_bytes, method='PUT')
        req.add_header('Content-Type', 'application/json')

        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status == 200:
                    print(f"[{time.strftime('%H:%M:%S')}] ✓ Frame #{frame['seq']} streamed | State: {frame['state']} ({frame['fault'][:22]}) | RMS: {frame['rms']}g | Temp: {frame['temp']}°C")
        except Exception as e:
            print(f"[{time.strftime('%H:%M:%S')}] ✗ Cloud push failed: {e}")

        time.sleep(interval)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Live Cloud Telemetry Uplink")
    parser.add_argument("--scenario", choices=["healthy", "imbalance", "bearing", "thermal"], default="healthy", help="Simulation scenario")
    parser.add_argument("--interval", type=float, default=2.5, help="Push interval in seconds")
    args = parser.parse_args()

    try:
        stream(scenario=args.scenario, interval=args.interval)
    except KeyboardInterrupt:
        print("\n[INFO] Streaming terminated by user.")
