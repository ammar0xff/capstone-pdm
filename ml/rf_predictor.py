#!/usr/bin/env python3
"""
Intelligent Predictive Maintenance (PdM) - Real-Time Inference Wrapper
Loads trained Random Forest model and maps multi-modal features to industrial fault classes.
Provides seamless fallback logic and industrial maintenance advice.
"""

import os
import numpy as np

class PdMClassifier:
    def __init__(self, model_path=None):
        self.model = None
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
                print(f"[INFO] ML Inference Engine initialized with {model_path}")
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

    def predict(self, feature_dict):
        """
        Features expected:
          rms_dyn, peak_dyn, crest_factor, kurtosis, temp_c, temp_slope, sound_rms, sound_db, sound_zcr
        Returns:
          class_id (int), class_name (str), proba (float), advice (str)
        """
        rms = feature_dict.get("rms_dyn", 0.05)
        peak = feature_dict.get("peak_dyn", 0.10)
        cf = feature_dict.get("crest_factor", 2.0)
        kurt = feature_dict.get("kurtosis", 3.0)
        temp = feature_dict.get("temp_c", 26.0)
        slope = feature_dict.get("temp_slope", 0.0)
        s_rms = feature_dict.get("sound_rms", 0.01)
        s_db = feature_dict.get("sound_db", 50.0)
        s_zcr = feature_dict.get("sound_zcr", 0.02)

        if self.model is not None:
            try:
                vec = np.array([[rms, peak, cf, kurt, temp, slope, s_rms, s_db, s_zcr]])
                probas = self.model.predict_proba(vec)[0]
                class_id = int(np.argmax(probas))
                proba = float(probas[class_id])
                return class_id, self.class_names[class_id], round(proba, 2), self.get_advice(class_id)
            except Exception:
                pass

        # Robust physics-aligned heuristic fallback
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

        return cid, self.class_names[cid], prob, self.get_advice(cid)
