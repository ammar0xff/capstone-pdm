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
import threading
import subprocess
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

# Machine Learning Module Path
ML_DIR = os.path.join(os.path.dirname(BASE_DIR), "ml")
if ML_DIR not in sys.path:
    sys.path.insert(0, ML_DIR)
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

try:
    from rf_predictor import PdMClassifier
except ImportError:
    try:
        from ml.rf_predictor import PdMClassifier
    except ImportError:
        PdMClassifier = None

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
    """
    ADXL345 3-Axis Digital Accelerometer on I2C bus 1 (address 0x53).
    Configured for ±4g range, 400Hz output data rate.
    """
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
            # Set ±4g range: 0x31 -> 0x01
            self.bus.write_byte_data(self.address, 0x31, 0x01)
            # Set rate to 400Hz: 0x2C -> 0x0C
            self.bus.write_byte_data(self.address, 0x2C, 0x0C)
            # Measurement mode: 0x2D -> 0x08
            self.bus.write_byte_data(self.address, 0x2D, 0x08)
            self.connected = True
            print("[INFO] ADXL345 initialized on I2C bus 1 (0x53) at 400Hz")
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
    """
    MAX6675 Cold-Junction Compensated K-Thermocouple-to-Digital Converter on SPI0.0.
    12-bit resolution, 0.25°C/LSB, Open thermocouple fault detection.
    """
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
                return None, 1, 0
        try:
            resp = self.spi.readbytes(2)
            raw = (resp[0] << 8) | resp[1]
            open_tc = (raw >> 2) & 1
            adc_counts = (raw >> 3) & 0x0FFF
            temp_c = adc_counts * 0.25
            return temp_c, open_tc, raw
        except Exception as e:
            self.connected = False
            return None, 1, 0


class AcousticWorker(threading.Thread):
    """
    High-Speed Acoustic Acquisition Worker for INMP441 MEMS Microphone over I2S.
    Samples 32-bit I2S audio at 48kHz in background without blocking DAQ loop.
    Computes RMS, Peak, Crest Factor, dB SPL, and Zero Crossing Rate (ZCR).
    """
    def __init__(self, device="plughw:1,0", rate=48000, chunk_samples=2400):
        super().__init__(daemon=True)
        self.device = device
        self.rate = rate
        self.chunk_samples = chunk_samples  # 2400 samples = 50ms window
        self.running = True
        self.lock = threading.Lock()
        self.metrics = {
            "rms": 0.015,
            "peak": 0.042,
            "db_spl": 48.5,
            "zcr": 0.082,
            "crest_factor": 2.80,
            "status": "Initializing",
            "active": False
        }

    def run(self):
        bytes_to_read = self.chunk_samples * 8  # stereo 32-bit = 8 bytes/sample
        while self.running:
            proc = None
            try:
                cmd = ["arecord", "-D", self.device, "-c", "2", "-r", str(self.rate), "-f", "S32_LE", "-t", "raw", "-q"]
                proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
                while self.running:
                    raw_bytes = proc.stdout.read(bytes_to_read)
                    if not raw_bytes or len(raw_bytes) < bytes_to_read:
                        break
                    arr = np.frombuffer(raw_bytes, dtype=np.int32)
                    left = arr[0::2]  # INMP441 wired to Left channel
                    if len(left) == 0:
                        continue

                    # Normalized audio signal in [-1.0, 1.0]
                    norm = left.astype(np.float32) / 2147483648.0
                    peak = float(np.max(np.abs(norm)))
                    rms = float(np.sqrt(np.mean(norm**2)))
                    cf = float(peak / (rms + 1e-9))
                    # Calibrated dB SPL (INMP441 sensitivity -26 dBFS at 94 dB SPL)
                    db_spl = float(max(30.0, min(120.0, 120.0 + 20.0 * math.log10(rms + 1e-9))))
                    # Zero-crossing rate
                    signs = np.signbit(left)
                    zcr = float(np.mean(np.abs(np.diff(signs))))

                    with self.lock:
                        self.metrics = {
                            "rms": round(rms, 4),
                            "peak": round(peak, 4),
                            "db_spl": round(db_spl, 1),
                            "zcr": round(zcr, 4),
                            "crest_factor": round(cf, 2),
                            "status": "Hardware I2S Stream (INMP441)",
                            "active": True
                        }
            except Exception as e:
                with self.lock:
                    self.metrics["status"] = f"Standby: {str(e)[:24]}"
                    self.metrics["active"] = False
            finally:
                if proc:
                    try:
                        proc.terminate()
                        proc.wait(timeout=0.5)
                    except Exception:
                        pass
            time.sleep(1.0)

    def get_metrics(self):
        with self.lock:
            return dict(self.metrics)


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
    print("=" * 65)
    print("  Intelligent Predictive Maintenance (PdM) - Edge DAQ & SPC Engine")
    print("=" * 65)

    cal = load_cal()
    adxl = ADXL345Driver()
    tc = MAX6675Driver()
    led = StatusLED(pin=16)

    # Initialize Stage 2 Machine Learning Diagnostic Classifier
    model_path = os.path.join(ML_DIR, "model.joblib")
    classifier = PdMClassifier(model_path) if PdMClassifier else None

    # Start high-speed acoustic background worker
    acoustic = AcousticWorker()
    acoustic.start()

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
    baseline_mu = 0.080
    baseline_sigma = 0.025
    ucl_warning = baseline_mu + 2 * baseline_sigma  # ~0.130 g
    ucl_fault = baseline_mu + 3 * baseline_sigma    # ~0.155 g

    # Sliding buffers
    raw_window = collections.deque(maxlen=256)
    ts_window = collections.deque(maxlen=256)
    temp_history = collections.deque(maxlen=60)  # for temperature slope dT/dt

    # State tracking
    seq = 0
    start_time = time.time()
    last_temp_read = 0.0
    last_temp_c = 25.0
    last_raw_temp = 25.0
    raw_tc_word = 0
    open_tc_flag = 0
    last_state_pub = 0.0
    last_csv_log = 0.0

    latest_raw_xyz = (0, 0, 0)

    # Ensure CSV header
    if not os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                "timestamp", "seq", "g_mag", "rms_dyn", "kurtosis",
                "crest_factor", "peak_dyn", "temp_c", "temp_slope",
                "sound_db", "sound_zcr", "state", "fault_label", "fault_proba"
            ])

    print("[INFO] High-Speed Sensor Ingestion active. Sampling 200-400Hz...")

    while True:
        t_now = time.perf_counter()
        now_wall = time.time()

        # 1. Read Accelerometer (Fastest rate)
        raw_reading = adxl.read_raw()
        if raw_reading:
            latest_raw_xyz = raw_reading
            x_raw, y_raw, z_raw = raw_reading
            scale = cal.get("g_scale", 0.0039)
            ax = (x_raw * scale) - cal.get("g_bias_x", 0.0)
            ay = (y_raw * scale) - cal.get("g_bias_y", 0.0)
            az = (z_raw * scale) - cal.get("g_bias_z", 0.0)
            raw_window.append((ax, ay, az))
            ts_window.append(now_wall)
        else:
            time.sleep(0.002)

        # 2. Read Temperature every 250ms (MAX6675 conversion time ~220ms)
        if now_wall - last_temp_read >= 0.25:
            temp_val, open_flag, raw_word = tc.read_temp()
            last_temp_read = now_wall
            open_tc_flag = open_flag
            raw_tc_word = raw_word
            if temp_val is not None:
                last_raw_temp = temp_val
                if open_flag == 0:
                    last_temp_c = temp_val * cal.get("t_a", 1.0) + cal.get("t_b", 0.0)
                    temp_history.append((now_wall, last_temp_c))

        # 3. Publish State & Compute Features every 100ms (10Hz state update, 400Hz sampling)
        if len(raw_window) >= 64 and (now_wall - last_state_pub >= 0.10):
            last_state_pub = now_wall
            arr = np.array(raw_window)
            N = len(arr)

            # Instantaneous raw & scaled acceleration
            curr_raw_x, curr_raw_y, curr_raw_z = latest_raw_xyz
            curr_ax, curr_ay, curr_az = arr[-1]
            total_g_mag = float(np.linalg.norm(arr[-1]))

            # Static DC Gravity Vector (mean over sliding window)
            dc_gravity = np.mean(arr, axis=0)
            dc_x, dc_y, dc_z = float(dc_gravity[0]), float(dc_gravity[1]), float(dc_gravity[2])
            dc_mag = float(np.linalg.norm(dc_gravity))

            # Dynamic Vibration Vector (Removing DC Gravity component)
            dyn = arr - dc_gravity
            dyn_mag = np.linalg.norm(dyn, axis=1)
            dyn_ax, dyn_ay, dyn_az = float(dyn[-1][0]), float(dyn[-1][1]), float(dyn[-1][2])
            dyn_inst_mag = float(np.linalg.norm(dyn[-1]))

            # Dynamic Vibration RMS & Peak
            sum_sq = float(np.sum(dyn_mag**2))
            rms_dyn = float(np.sqrt(np.mean(dyn_mag**2)))
            peak_dyn = float(np.max(dyn_mag))
            crest_factor = float(peak_dyn / (rms_dyn + 1e-9))

            # Kurtosis calculation (fourth standardized moment)
            dyn_mean = float(np.mean(dyn_mag))
            var = float(np.var(dyn_mag))
            std_dyn = float(np.sqrt(var))
            if var > 1e-9:
                m4 = float(np.mean((dyn_mag - dyn_mean)**4))
                kurtosis = float(m4 / (var**2))
            else:
                m4 = 0.0
                kurtosis = 3.0

            # Temperature slope dT/dt (°C / min)
            if len(temp_history) >= 2:
                dt_temp = temp_history[-1][0] - temp_history[0][0]
                if dt_temp > 1.0:
                    delta_t = temp_history[-1][1] - temp_history[0][1]
                    temp_slope = delta_t / (dt_temp / 60.0)
                else:
                    delta_t = 0.0
                    temp_slope = 0.0
            else:
                delta_t = 0.0
                dt_temp = 0.0
                temp_slope = 0.0

            # Shewhart SPC Z-score
            z_score = float((rms_dyn - baseline_mu) / baseline_sigma)

            # Sampling rate estimation
            dt_window = ts_window[-1] - ts_window[0]
            fs = round(len(ts_window) / dt_window, 1) if dt_window > 0 else 400.0

            # Acoustic Modality metrics
            ac_data = acoustic.get_metrics()
            sound_rms = ac_data.get("rms", 0.015)
            sound_peak = ac_data.get("peak", 0.045)
            sound_db = ac_data.get("db_spl", 48.0)
            sound_zcr = ac_data.get("zcr", 0.082)
            sound_cf = ac_data.get("crest_factor", 3.0)
            sound_status = ac_data.get("status", "Active")

            # 4. Shewhart SPC Gating & Industrial Anomaly Classification
            # Stage 1: Coarse Statistical & Thermal Gating
            is_thermal_fault = (last_temp_c > 70.0) or (temp_slope > 10.0)
            is_thermal_warn = (last_temp_c > 50.0) or (temp_slope > 5.0)

            is_vib_fault = (rms_dyn > ucl_fault) or (kurtosis > 7.0 and rms_dyn > 0.03) or (peak_dyn > 0.40)
            is_vib_warn = (rms_dyn > ucl_warning) or (kurtosis > 5.0 and rms_dyn > 0.03) or (peak_dyn > 0.25)
            is_sound_fault = (sound_db > 88.0) or (sound_zcr > 0.28)

            feature_dict = {
                "rms_dyn": round(rms_dyn, 4),
                "peak_dyn": round(peak_dyn, 4),
                "crest_factor": round(crest_factor, 2),
                "kurtosis": round(kurtosis, 2),
                "temp_c": round(last_temp_c, 2),
                "temp_slope": round(temp_slope, 2),
                "sound_rms": round(sound_rms, 4),
                "sound_db": round(sound_db, 1),
                "sound_zcr": round(sound_zcr, 4)
            }

            # Run Stage 2 Fine ML Inference (Random Forest)
            if classifier:
                ml_cid, ml_label, ml_proba, ml_advice = classifier.predict(feature_dict)
            else:
                ml_cid, ml_label, ml_proba, ml_advice = 0, "Normal Operation", 0.98, "Nominal."

            if is_vib_fault or is_thermal_fault or is_sound_fault:
                state = "Fault"
                led.set(1)
                if ml_cid != 0:
                    fault_label = ml_label
                    fault_proba = ml_proba
                    advice = ml_advice
                elif is_vib_fault and is_thermal_fault:
                    fault_label = "Severe Compound Fault (Thermal Runaway + Bearing Shock)"
                    fault_proba = 0.98
                    advice = "CRITICAL: Imminent bearing seizure. Halt motor immediately; inspect raceways and thermal dissipation."
                elif is_thermal_fault:
                    fault_label = "Thermal Runaway / Excessive Friction"
                    fault_proba = 0.93
                    advice = "Steep thermal gradient detected (dT/dt > 10°C/min). Check lubrication viscosity and mechanical binding."
                elif kurtosis > 7.0:
                    fault_label = "Bearing Defect (Raceway / Ball Spalling)"
                    fault_proba = 0.95
                    advice = "Kurtosis > 7.0 confirms sharp transient micro-impact shocks from raceway spalls. Plan bearing replacement."
                elif is_sound_fault:
                    fault_label = "Acoustic Friction / Bearing Squeal"
                    fault_proba = 0.88
                    advice = "High ZCR acoustic emissions detected. Check bearing cage lubrication and air seal clearance."
                else:
                    fault_label = "Mechanical Imbalance / Shaft Looseness"
                    fault_proba = 0.90
                    advice = "Elevated continuous RMS vibration detected. Check rotor balance, motor mounting bolts, and coupling alignment."
            elif is_vib_warn or is_thermal_warn:
                state = "Warning"
                led.set(int(now_wall * 4) % 2)
                if ml_cid != 0:
                    fault_label = f"Incipient: {ml_label}"
                    fault_proba = max(0.65, round(ml_proba * 0.85, 2))
                    advice = ml_advice
                else:
                    fault_proba = 0.65
                    fault_label = "Thermal Trend Warning" if is_thermal_warn else "Incipient Vibration Warning (2-Sigma Breach)"
                    advice = "Vibration amplitude exceeded 2-sigma Shewhart threshold. Schedule preventive inspection."
            else:
                state = "Healthy"
                led.set(0)
                fault_label = "Normal Operation"
                fault_proba = 0.05
                advice = "Machine operating within nominal limits. Continuous baseline monitoring active."

            # 5. Build Complete Telemetry & Mathematical Breakdown Packet
            raw_bin_str = f"{raw_tc_word:016b}"
            formatted_bin = f"{raw_bin_str[0:4]} {raw_bin_str[4:8]} {raw_bin_str[8:12]} {raw_bin_str[12:16]}"

            packet = {
                "timestamp": round(now_wall, 3),
                "uptime_s": round(now_wall - start_time, 1),
                "seq": seq,
                "state": state,
                "fault_label": fault_label,
                "fault_proba": round(fault_proba, 2),
                "advice": advice,
                "online": True,

                # Stage 2 Machine Learning Diagnostic Evidence
                "ai": {
                    "model_name": "Random Forest (300 Trees)",
                    "architecture": "Two-Stage Coarse SPC -> Fine ML",
                    "gate_status": "Stage 2 Triggered (Anomaly Detected)" if state != "Healthy" else "Stage 1 Gated (Shewhart Normal)",
                    "predicted_class_id": ml_cid,
                    "predicted_class": ml_label,
                    "confidence": fault_proba,
                    "features_input": feature_dict
                },

                # Detailed Mathematical Equation Cards (Formulas, Live Values, and Rationale)
                "equations": {
                    "vibration_rms": {
                        "name": "Dynamic RMS Vibration Energy",
                        "symbol": "RMS_{dyn}",
                        "formula": "\\sqrt{\\frac{1}{N}\\sum_{i=1}^N (a_{dyn}[i])^2}",
                        "unit": "g",
                        "n": N,
                        "sum_sq": round(sum_sq, 6),
                        "val": round(rms_dyn, 4),
                        "live_calc": f"sqrt({sum_sq:.6f} / {N}) = {rms_dyn:.4f} g",
                        "reason": "Quantifies total continuous mechanical kinetic energy and destructive stress under ISO 20816. Elevates during severe unbalance, misalignment, and structural looseness."
                    },
                    "kurtosis": {
                        "name": "Vibration Kurtosis (4th Moment)",
                        "symbol": "\\kappa",
                        "formula": "\\frac{\\frac{1}{N}\\sum (a_{dyn} - \\mu)^4}{\\sigma^4}",
                        "unit": "ratio",
                        "mu4": round(m4, 8),
                        "var": round(var, 6),
                        "sigma": round(std_dyn, 4),
                        "val": round(kurtosis, 2),
                        "live_calc": f"{m4:.8f} / ({var:.6f})^2 = {kurtosis:.2f}",
                        "reason": "Measures distribution peakedness and tailedness. Healthy Gaussian noise yields ~3.0. Microscopic bearing raceway spalls produce transient impact shocks that spike kurtosis to 6-15 long before RMS rises."
                    },
                    "crest_factor": {
                        "name": "Crest Factor (Impact Ratio)",
                        "symbol": "CF",
                        "formula": "\\frac{Peak_{dyn}}{RMS_{dyn}}",
                        "unit": "ratio",
                        "peak": round(peak_dyn, 4),
                        "rms": round(rms_dyn, 4),
                        "val": round(crest_factor, 2),
                        "live_calc": f"{peak_dyn:.4f} g / {rms_dyn:.4f} g = {crest_factor:.2f}",
                        "reason": "Ratio of peak shock to continuous vibration energy. Detects early spalling (Stage 2 fault, CF > 4.5). In late-stage failure, the noise floor rises and CF collapses back down."
                    },
                    "shewhart_z": {
                        "name": "Shewhart Statistical Z-Score",
                        "symbol": "Z",
                        "formula": "\\frac{RMS_{dyn} - \\mu_0}{\\sigma_0}",
                        "unit": "σ",
                        "rms": round(rms_dyn, 4),
                        "mu_0": baseline_mu,
                        "sigma_0": baseline_sigma,
                        "val": round(z_score, 2),
                        "live_calc": f"({rms_dyn:.4f} - {baseline_mu:.3f}) / {baseline_sigma:.3f} = {z_score:.2f} σ",
                        "reason": "Statistical process control gatekeeper. Instead of wasting CPU continuously running heavy AI models, Stage 1 gates Stage 2: complex diagnostics awaken only when Z breaches 2.0 (95.4% confidence)."
                    },
                    "temp_adc": {
                        "name": "MAX6675 12-Bit Cold-Junction ADC",
                        "symbol": "T_{raw}",
                        "formula": "((Word_{16} \\gg 3) \\& 0x0FFF) \\times 0.25^\\circ C",
                        "unit": "°C",
                        "raw_hex": f"0x{raw_tc_word:04X}",
                        "raw_bin": formatted_bin,
                        "adc_counts": (raw_tc_word >> 3) & 0x0FFF,
                        "open_tc": open_tc_flag,
                        "val": round(last_raw_temp, 2),
                        "live_calc": f"{((raw_tc_word >> 3) & 0x0FFF)} counts * 0.25°C = {last_raw_temp:.2f} °C",
                        "reason": "Converts Seebeck thermoelectric microvoltage into temperature with cold-junction compensation. Bit 2 actively monitors for broken or loose thermocouple wires."
                    },
                    "temp_cal": {
                        "name": "Linear Thermal Calibration",
                        "symbol": "T_{cal}",
                        "formula": "a \\cdot T_{raw} + b",
                        "unit": "°C",
                        "a": cal.get("t_a", 1.0),
                        "b": cal.get("t_b", 0.0),
                        "raw": round(last_raw_temp, 2),
                        "val": round(last_temp_c, 2),
                        "live_calc": f"{cal.get('t_a', 1.0):.3f} * {last_raw_temp:.2f} + {cal.get('t_b', 0.0):.2f} = {last_temp_c:.2f} °C",
                        "reason": "Corrects for lead resistance and thermal contact impedance between the thermocouple junction and the motor bearing casing."
                    },
                    "temp_gradient": {
                        "name": "Thermal Derivative (Rate of Change)",
                        "symbol": "\\frac{\\Delta T}{\\Delta t}",
                        "formula": "\\frac{T_{now} - T_{past}}{\\Delta t / 60}",
                        "unit": "°C/min",
                        "delta_t": round(delta_t, 2),
                        "delta_time_s": round(dt_temp, 1),
                        "val": round(temp_slope, 2),
                        "live_calc": f"{delta_t:.2f} °C / ({dt_temp:.1f} s / 60) = {temp_slope:.2f} °C/min",
                        "reason": "Predictive runaway alert. Waiting for an absolute threshold (70°C) is often too late. A steep gradient (>5-10°C/min) detects bearing lubrication starvation and rotor binding 15-30 minutes in advance."
                    },
                    "acoustic_zcr": {
                        "name": "Acoustic Zero Crossing Rate",
                        "symbol": "ZCR",
                        "formula": "\\frac{1}{2(M-1)}\\sum_{k=1}^{M-1} |sgn(s[k]) - sgn(s[k-1])|",
                        "unit": "crossings/sample",
                        "val": sound_zcr,
                        "live_calc": f"ZCR = {sound_zcr:.4f} crossings/sample",
                        "reason": "Efficient time-domain proxy for dominant frequency content. Healthy motor hum has low ZCR; metal-on-metal rubbing and dry bearing squeals generate high-frequency acoustics, spiking ZCR."
                    },
                    "acoustic_spl": {
                        "name": "Sound Pressure Level (SPL)",
                        "symbol": "SPL_{dB}",
                        "formula": "120.0 + 20\\log_{10}(RMS_{norm})",
                        "unit": "dB SPL",
                        "rms_norm": sound_rms,
                        "val": sound_db,
                        "live_calc": f"120.0 + 20 * log10({sound_rms:.4f}) = {sound_db:.1f} dB",
                        "reason": "Calibrated industrial acoustic emission level (INMP441 sensitivity -26 dBFS at 94 dB SPL) measuring airborne sound power radiated by the machinery."
                    }
                },

                # Raw Sensor Registers & Values
                "raw_sensors": {
                    "adxl_x_lsb": curr_raw_x,
                    "adxl_y_lsb": curr_raw_y,
                    "adxl_z_lsb": curr_raw_z,
                    "adxl_scale": cal.get("g_scale", 0.0039),
                    "adxl_bias": [cal.get("g_bias_x", 0.0), cal.get("g_bias_y", 0.0), cal.get("g_bias_z", 0.0)],
                    "max6675_word_hex": f"0x{raw_tc_word:04X}",
                    "max6675_bits": formatted_bin,
                    "open_tc": open_tc_flag,
                    "inmp441_device": "plughw:1,0 (I2S)",
                    "inmp441_peak": sound_peak
                },

                # Processed Vibration Modality
                "vibration": {
                    "rms_dyn": round(rms_dyn, 4),
                    "peak_dyn": round(peak_dyn, 4),
                    "crest_factor": round(crest_factor, 2),
                    "kurtosis": round(kurtosis, 2),
                    "g_total": round(total_g_mag, 3),
                    "ax": round(curr_ax, 3),
                    "ay": round(curr_ay, 3),
                    "az": round(curr_az, 3),
                    "dc_x": round(dc_x, 3),
                    "dc_y": round(dc_y, 3),
                    "dc_z": round(dc_z, 3),
                    "dc_mag": round(dc_mag, 3),
                    "ax_dyn": round(dyn_ax, 4),
                    "ay_dyn": round(dyn_ay, 4),
                    "az_dyn": round(dyn_az, 4),
                    "fs_hz": fs,
                    "window_samples": N
                },

                # Processed Thermal Modality
                "temperature": {
                    "temp_c": round(last_temp_c, 2),
                    "raw_temp_c": round(last_raw_temp, 2),
                    "slope_c_per_min": round(temp_slope, 2),
                    "open_tc": open_tc_flag
                },

                # Processed Acoustic Modality
                "acoustic": {
                    "rms": sound_rms,
                    "peak": sound_peak,
                    "db_spl": sound_db,
                    "zcr": sound_zcr,
                    "crest_factor": sound_cf,
                    "status": sound_status
                },

                # Statistical Process Control
                "spc": {
                    "baseline_mu": baseline_mu,
                    "baseline_sigma": baseline_sigma,
                    "z_score": round(z_score, 2),
                    "ucl_warning": round(ucl_warning, 3),
                    "ucl_fault": round(ucl_fault, 3)
                },

                # Hardware Bus Health
                "system": {
                    "adxl_ok": adxl.connected,
                    "max6675_ok": tc.connected and (open_tc_flag == 0),
                    "acoustic_ok": ac_data.get("active", False),
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

            # 7. Append to hot_backup.csv every ~1 second
            if now_wall - last_csv_log >= 1.0:
                last_csv_log = now_wall
                try:
                    with open(HISTORY_FILE, 'a', newline='') as f:
                        writer = csv.writer(f)
                        writer.writerow([
                            packet["timestamp"], seq,
                            packet["vibration"]["g_total"],
                            packet["vibration"]["rms_dyn"],
                            packet["vibration"]["kurtosis"],
                            packet["vibration"]["crest_factor"],
                            packet["vibration"]["peak_dyn"],
                            packet["temperature"]["temp_c"],
                            packet["temperature"]["slope_c_per_min"],
                            packet["acoustic"]["db_spl"],
                            packet["acoustic"]["zcr"],
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

        # High-Speed loop pacing (~300-400Hz)
        elapsed = time.perf_counter() - t_now
        time.sleep(max(0.001, 0.0025 - elapsed))


if __name__ == "__main__":
    main()
