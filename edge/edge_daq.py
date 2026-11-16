#!/usr/bin/env python3
"""
Intelligent Predictive Maintenance (PdM) - Edge DAQ & Statistical Process Control (SPC)
Offline-first high-speed sensor ingestion, multi-modality fusion, and anomaly detection.
Targets: ADXL345 (I2C), MAX6675 (SPI), INMP441 (I2S/Acoustic), Status LED (GPIO16).
"""

import time
import os
import sys
import json
import csv
import collections
import struct
import math
import numpy as np

# Optional hardware imports with robust fallbacks
try:
    import smbus2
except ImportError:
    smbus2 = None

try:
    import spidev
except ImportError:
    spidev = None

try:
    import paho.mqtt.client as mqtt
except ImportError:
    mqtt = None

# Base directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(BASE_DIR, "latest_state.json")
TMP_STATE_FILE = os.path.join(BASE_DIR, "latest_state.tmp")
HISTORY_FILE = os.path.join(BASE_DIR, "hot_backup.csv")
CAL_FILE = os.path.join(BASE_DIR, "cal.json")

# Load calibration
def load_cal():
    if os.path.exists(CAL_FILE):
        try:
            with open(CAL_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "t_a": 1.0,
        "t_b": 0.0,
        "g_bias_x": 0.0,
        "g_bias_y": 0.0,
        "g_bias_z": 0.0,
        "g_scale": 0.0039
    }

class ADXL345Driver:
    def __init__(self, bus_num=1, address=0x53):
        self.bus_num = bus_num
        self.address = address
        self.bus = None
        self.connected = False
        self.init_sensor()

    def init_sensor(self):
        if not smbus2:
            return False
        try:
            self.bus = smbus2.SMBus(self.bus_num)
            dev_id = self.bus.read_byte_data(self.address, 0x00)
            if dev_id != 0xE5:
                print(f"[WARN] ADXL345 unexpected DEVID: 0x{dev_id:02X}")
            # Set ±4g range: 0x31 -> 0x01 (or 0x0B for ±16g full-res)
            self.bus.write_byte_data(self.address, 0x31, 0x01)
            # Set rate to 400Hz (0x0C) or 800Hz (0x0D)
            self.bus.write_byte_data(self.address, 0x2C, 0x0C)
            # Measurement mode: 0x2D -> 0x08
            self.bus.write_byte_data(self.address, 0x2D, 0x08)
            self.connected = True
            print("[INFO] ADXL345 initialized on I2C bus 1 (0x53)")
            return True
        except Exception as e:
            print(f"[ERR] Failed to init ADXL345: {e}")
            self.connected = False
            return False

    def read_raw(self):
        if not self.connected:
            if not self.init_sensor():
                return None
        try:
            data = self.bus.read_i2c_block_data(self.address, 0x32, 6)
            x, y, z = struct.unpack("<hhh", bytes(data))
            return x, y, z
        except Exception as e:
            self.connected = False
            return None


class MAX6675Driver:
    def __init__(self, bus=0, device=0):
        self.bus_num = bus
        self.dev_num = device
        self.spi = None
        self.connected = False
        self.init_sensor()

    def init_sensor(self):
        if not spidev:
            return False
        try:
            self.spi = spidev.SpiDev()
            self.spi.open(self.bus_num, self.dev_num)
            self.spi.max_speed_hz = 1000000
            self.spi.mode = 0
            self.connected = True
            print("[INFO] MAX6675 initialized on SPI0.0")
            return True
        except Exception as e:
            print(f"[ERR] Failed to init MAX6675: {e}")
            self.connected = False
            return False

    def read_temp(self):
        if not self.connected:
            if not self.init_sensor():
                return None, 1
        try:
            resp = self.spi.readbytes(2)
            raw = (resp[0] << 8) | resp[1]
            open_tc = (raw >> 2) & 1
            temp_c = (raw >> 3) * 0.25
            return temp_c, open_tc
        except Exception as e:
            self.connected = False
            return None, 1


class StatusLED:
    def __init__(self, pin=16):
        self.pin = pin
        self.active = False
        try:
            import gpiod
            chip = gpiod.Chip('gpiochip0')
            self.line = chip.get_line(self.pin)
            self.line.request(consumer="pdm-led", type=gpiod.LINE_REQ_DIR_OUT)
            self.active = True
        except Exception:
            self.line = None

    def set(self, val):
        if self.active and self.line:
            try:
                self.line.set_value(1 if val else 0)
            except Exception:
                pass


def main():
    print("=" * 60)
    print("  Intelligent Predictive Maintenance (PdM) - Edge DAQ Engine")
    print("=" * 60)

    cal = load_cal()
    adxl = ADXL345Driver()
    tc = MAX6675Driver()
    led = StatusLED(pin=16)

    # Initialize MQTT if available
    client = None
    if mqtt:
        try:
            client = mqtt.Client(client_id="pdm_edge_daq")
            client.connect("localhost", 1883, 60)
            client.loop_start()
            print("[INFO] Connected to local MQTT broker (localhost:1883)")
        except Exception as e:
            print(f"[WARN] Local MQTT broker unavailable: {e}")

    # Baseline & SPC Parameters (Cinar & Shewhart criteria)
    # Target baseline: normal motor ~0.05-0.15g RMS, Warning at 2-sigma, Fault at 3-sigma
    baseline_mu = 0.080
    baseline_sigma = 0.025
    ucl_warning = baseline_mu + 2 * baseline_sigma  # ~0.130 g
    ucl_fault = baseline_mu + 3 * baseline_sigma    # ~0.155 g

    # Buffers
    raw_window = collections.deque(maxlen=256)
    ts_window = collections.deque(maxlen=256)
    temp_history = collections.deque(maxlen=30)  # for temperature slope dT/dt
    
    # State tracking
    seq = 0
    start_time = time.time()
    last_temp_read = 0
    last_temp_c = 25.0
    open_tc_flag = 0

    # Ensure CSV header
    if not os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                "timestamp", "seq", "g_mag", "rms_dyn", "kurtosis",
                "peak_dyn", "temp_c", "temp_slope", "state", "fault_label", "fault_proba"
            ])

    print("[INFO] Starting High-Speed Data Acquisition loop...")

    while True:
        t_now = time.perf_counter()
        now_wall = time.time()

        # 1. Read Accelerometer
        raw_reading = adxl.read_raw()
        if raw_reading:
            x_raw, y_raw, z_raw = raw_reading
            # Sensitivity: ~3.9 mg / LSB in 4g mode
            scale = cal.get("g_scale", 0.0039)
            ax = (x_raw * scale) - cal.get("g_bias_x", 0.0)
            ay = (y_raw * scale) - cal.get("g_bias_y", 0.0)
            az = (z_raw * scale) - cal.get("g_bias_z", 0.0)
            raw_window.append((ax, ay, az))
            ts_window.append(now_wall)
        else:
            time.sleep(0.005)
            continue

        # 2. Read Temperature every 250ms (MAX6675 conversion time ~220ms)
        if now_wall - last_temp_read >= 0.25:
            temp_val, open_flag = tc.read_temp()
            last_temp_read = now_wall
            open_tc_flag = open_flag
            if temp_val is not None and open_flag == 0:
                last_temp_c = temp_val * cal.get("t_a", 1.0) + cal.get("t_b", 0.0)
                temp_history.append((now_wall, last_temp_c))

        # 3. Calculate features once enough samples exist in sliding window (e.g. 128 samples)
        if len(raw_window) >= 128:
            arr = np.array(raw_window)
            # Remove DC gravity component to get dynamic vibration
            dc_gravity = np.mean(arr, axis=0)
            dyn = arr - dc_gravity
            dyn_mag = np.linalg.norm(dyn, axis=1)
            total_g_mag = float(np.linalg.norm(arr[-1]))

            # Dynamic Vibration RMS
            rms_dyn = float(np.sqrt(np.mean(dyn_mag**2)))
            peak_dyn = float(np.max(dyn_mag))

            # Kurtosis calculation (fourth standardized moment)
            var = np.var(dyn_mag)
            if var > 1e-9:
                kurtosis = float(np.mean((dyn_mag - np.mean(dyn_mag))**4) / (var**2))
            else:
                kurtosis = 3.0

            # Temperature slope dT/dt (°C / min)
            if len(temp_history) >= 2:
                dt = temp_history[-1][0] - temp_history[0][0]
                if dt > 1.0:
                    temp_slope = (temp_history[-1][1] - temp_history[0][1]) / (dt / 60.0)
                else:
                    temp_slope = 0.0
            else:
                temp_slope = 0.0

            # Sample rate estimation
            dt_window = ts_window[-1] - ts_window[0]
            fs = round(len(ts_window) / dt_window, 1) if dt_window > 0 else 400.0

            # 4. Shewhart SPC Gating & Anomaly Classification
            # Fault rules:
            # - High vibration: rms > ucl_fault (0.155g) OR peak > 0.40g OR kurtosis > 7.0
            # - High temperature: temp > 70°C OR temp_slope > 10°C/min
            state = "Healthy"
            fault_label = "Normal Operation"
            fault_proba = 0.05
            advice = "Machine operating within nominal limits. Continue routine monitoring."

            is_thermal_fault = (last_temp_c > 70.0) or (temp_slope > 10.0)
            is_thermal_warn = (last_temp_c > 50.0) or (temp_slope > 5.0)

            is_vib_fault = (rms_dyn > ucl_fault) or (kurtosis > 7.0) or (peak_dyn > 0.40)
            is_vib_warn = (rms_dyn > ucl_warning) or (kurtosis > 5.0) or (peak_dyn > 0.25)

            if is_vib_fault or is_thermal_fault:
                state = "Fault"
                led.set(1)
                if is_vib_fault and is_thermal_fault:
                    fault_label = "Severe Compound Fault (Thermal + Bearing)"
                    fault_proba = 0.98
                    advice = "CRITICAL: Imminent seizure risk. Inspect motor bearings and check cooling/lubrication immediately."
                elif is_thermal_fault:
                    fault_label = "Overheating / Friction"
                    fault_proba = 0.92
                    advice = "High thermal gradient detected. Check motor load, ambient airflow, and winding resistance."
                elif kurtosis > 7.0:
                    fault_label = "Bearing Impairment (Inner/Outer Race Defect)"
                    fault_proba = 0.94
                    advice = "High kurtosis indicates repetitive metal-on-metal impact shocks. Plan bearing replacement."
                else:
                    fault_label = "Mechanical Imbalance / Looseness"
                    fault_proba = 0.89
                    advice = "Elevated 1X/2X rotational vibration detected. Check shaft coupling alignment and rotor balance."
            elif is_vib_warn or is_thermal_warn:
                state = "Warning"
                # Blink or pulse LED
                led.set(int(now_wall * 4) % 2)
                fault_proba = 0.65
                if is_thermal_warn:
                    fault_label = "Thermal Trend Warning"
                    advice = "Temperature rising above baseline. Monitor closely for thermal runaway."
                else:
                    fault_label = "Incipient Vibration Warning"
                    advice = "Vibration amplitude exceeded 2-sigma control limit. Schedule inspection."
            else:
                state = "Healthy"
                led.set(0)

            # 5. Build Packet
            packet = {
                "timestamp": round(now_wall, 3),
                "uptime_s": round(now_wall - start_time, 1),
                "seq": seq,
                "state": state,
                "fault_label": fault_label,
                "fault_proba": round(fault_proba, 2),
                "advice": advice,
                "spc": {
                    "baseline_mu": baseline_mu,
                    "baseline_sigma": baseline_sigma,
                    "ucl_warning": round(ucl_warning, 3),
                    "ucl_fault": round(ucl_fault, 3)
                },
                "vibration": {
                    "rms_dyn": round(rms_dyn, 4),
                    "peak_dyn": round(peak_dyn, 4),
                    "kurtosis": round(kurtosis, 2),
                    "g_total": round(total_g_mag, 3),
                    "ax": round(float(arr[-1][0]), 3),
                    "ay": round(float(arr[-1][1]), 3),
                    "az": round(float(arr[-1][2]), 3),
                    "fs_hz": fs
                },
                "temperature": {
                    "temp_c": round(last_temp_c, 2),
                    "slope_c_per_min": round(temp_slope, 2),
                    "open_tc": open_tc_flag
                },
                "system": {
                    "adxl_ok": adxl.connected,
                    "max6675_ok": tc.connected and (open_tc_flag == 0),
                    "storage_ok": True
                }
            }

            # 6. Save latest state atomically
            try:
                with open(TMP_STATE_FILE, 'w') as f:
                    json.dump(packet, f, indent=2)
                os.replace(TMP_STATE_FILE, STATE_FILE)
            except Exception as e:
                print(f"[ERR] Failed to write state file: {e}")

            # 7. Append to hot_backup.csv every ~1 second (decimated)
            if seq % 20 == 0:
                try:
                    with open(HISTORY_FILE, 'a', newline='') as f:
                        writer = csv.writer(f)
                        writer.writerow([
                            packet["timestamp"], seq,
                            packet["vibration"]["g_total"],
                            packet["vibration"]["rms_dyn"],
                            packet["vibration"]["kurtosis"],
                            packet["vibration"]["peak_dyn"],
                            packet["temperature"]["temp_c"],
                            packet["temperature"]["slope_c_per_min"],
                            state, fault_label, fault_proba
                        ])
                except Exception:
                    pass

            # 8. MQTT Publish
            if client:
                try:
                    client.publish("factory/motor1", json.dumps(packet), qos=1)
                except Exception:
                    pass

            seq += 1

        # Control loop frequency (~200Hz - 400Hz)
        elapsed = time.perf_counter() - t_now
        time.sleep(max(0.001, 0.003 - elapsed))

if __name__ == "__main__":
    main()
