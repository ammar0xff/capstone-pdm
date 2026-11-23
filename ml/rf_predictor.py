#!/usr/bin/env python3
"""
Intelligent Predictive Maintenance (PdM) - Real-Time Inference Wrapper
Implements the Two-Stage Gated Monitoring Architecture (Cinar et al. 2022):
  Stage 1: Statistical Process Control (SPC) Shewhart Filter (Ultra-low latency <0.05ms)
  Stage 2: Multi-Modal Random Forest Classifier (Awakened only upon anomaly breach)
"""

import os
import time
import numpy as np

class PdMClassifier:
    def __init__(self, model_path=None, spc_baseline_rms=0.080, spc_sigma_rms=0.025, spc_z_thresh=2.0, spc_slope_thresh=5.0):
        self.model = None
        self.spc_baseline_rms = spc_baseline_rms
        self.spc_sigma_rms = spc_sigma_rms
        self.spc_z_thresh = spc_z_thresh
        self.spc_slope_thresh = spc_slope_thresh
        
        self.class_names = [
            "Normal Operation",
            "Mechanical Imbalance / Shaft Looseness",
            "Bearing Defect (Raceway / Ball Spalling)",
            "Thermal Runaway / Overheating"
        ]

        if model_path is None:
            model_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "model.joblib")

        if os.path.exists(model_path):
            try:
                import joblib
                self.model = joblib.load(model_path)
                print(f"[INFO] Two-Stage PdM Classifier initialized with ML model: {model_path}")
            except Exception as e:
                print(f"[WARN] Failed to load joblib model: {e}. Using decision-boundary fallback.")

    def get_advice(self, class_id):
        if class_id == 0:
            return "Machine operating within nominal ISO limits. Continue routine monitoring."
        elif class_id == 1:
            return "Elevated continuous RMS vibration detected. Check rotor balance, motor mounting bolts, and coupling alignment."
        elif class_id == 2:
            return "High kurtosis confirms sharp transient micro-impact shocks from raceway spalls. Plan rolling-element bearing replacement."
        elif class_id == 3:
            return "CRITICAL: Steep thermal gradient (dT/dt) detected. Check lubrication viscosity, mechanical binding, and motor ventilation immediately."
        return "Inspect machine condition."

    def predict(self, feature_dict, return_gate_info=False):
        """
        Two-Stage Gated Architecture (Cinar et al. 2022):
          Stage 1: Statistical Process Control (SPC) Shewhart Gate.
                   Evaluates dynamic RMS Z-Score and thermal slope (dT/dt).
                   If nominal, machine is declared Healthy with latency <0.05ms!
          Stage 2: Random Forest Multi-Modal Classifier.
                   Awakens ONLY when Stage 1 gate is breached.
        """
        t_start = time.perf_counter()
        
        rms = feature_dict.get("rms_dyn", 0.05)
        peak = feature_dict.get("peak_dyn", 0.10)
        cf = feature_dict.get("crest_factor", 2.0)
        kurt = feature_dict.get("kurtosis", 3.0)
        temp = feature_dict.get("temp_c", 26.0)
        slope = feature_dict.get("temp_slope", 0.0)
        s_rms = feature_dict.get("sound_rms", 0.01)
        s_db = feature_dict.get("sound_db", 50.0)
        s_zcr = feature_dict.get("sound_zcr", 0.02)

        # -------------------------------------------------------------
        # STAGE 1: Statistical Process Control (SPC) Shewhart Gate
        # -------------------------------------------------------------
        # Z-Score relative to calibrated healthy baseline
        z_score = (rms - self.spc_baseline_rms) / max(1e-5, self.spc_sigma_rms)
        is_thermal_anomaly = abs(slope) > self.spc_slope_thresh or temp > 55.0
        is_vibration_anomaly = z_score > self.spc_z_thresh or kurt > 5.0 or cf > 4.0 or rms > 0.120

        stage1_breached = is_vibration_anomaly or is_thermal_anomaly

        if not stage1_breached:
            # Stage 1 Passed: Nominal Machine State. Random Forest stays DORMANT!
            t_stage1 = (time.perf_counter() - t_start) * 1000.0
            gate_info = {
                "gate_status": "Stage 1 (SPC Normal)",
                "stage1_breached": False,
                "z_score": round(float(z_score), 2),
                "rf_executed": False,
                "latency_ms": round(t_stage1, 4)
            }
            if return_gate_info:
                return 0, self.class_names[0], 0.98, self.get_advice(0), gate_info
            return 0, self.class_names[0], 0.98, self.get_advice(0)

        # -------------------------------------------------------------
        # STAGE 2: Multi-Modal Random Forest Inference Engine
        # -------------------------------------------------------------
        # Awakens ONLY when Stage 1 gate is breached!
        rf_executed = True
        if self.model is not None:
            try:
                vec = np.array([[rms, peak, cf, kurt, temp, slope, s_rms, s_db, s_zcr]])
                probas = self.model.predict_proba(vec)[0]
                class_id = int(np.argmax(probas))
                proba = float(probas[class_id])
                
                t_total = (time.perf_counter() - t_start) * 1000.0
                gate_info = {
                    "gate_status": "Stage 2 (RF Triggered)",
                    "stage1_breached": True,
                    "z_score": round(float(z_score), 2),
                    "rf_executed": True,
                    "latency_ms": round(t_total, 3)
                }
                if return_gate_info:
                    return class_id, self.class_names[class_id], round(proba, 2), self.get_advice(class_id), gate_info
                return class_id, self.class_names[class_id], round(proba, 2), self.get_advice(class_id)
            except Exception:
                pass

        # Robust physics-aligned heuristic fallback if model object fails
        if (temp > 65.0) or (slope > 8.0):
            cid = 3
            prob = 0.95
        elif (kurt > 5.5) or (cf > 4.0) or (s_zcr > 0.18):
            cid = 2
            prob = 0.93
        elif (rms > 0.140) or (peak > 0.35):
            cid = 1
            prob = 0.89
        else:
            cid = 0
            prob = 0.98

        t_total = (time.perf_counter() - t_start) * 1000.0
        gate_info = {
            "gate_status": "Stage 2 (Fallback Triggered)",
            "stage1_breached": True,
            "z_score": round(float(z_score), 2),
            "rf_executed": False,
            "latency_ms": round(t_total, 3)
        }
        if return_gate_info:
            return cid, self.class_names[cid], prob, self.get_advice(cid), gate_info
        return cid, self.class_names[cid], prob, self.get_advice(cid)
