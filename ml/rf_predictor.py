#!/usr/bin/env python3
"""
Intelligent Predictive Maintenance (PdM) - Real-Time Inference Wrapper
Implements the Two-Stage Gated Monitoring Architecture (Cinar et al. 2022):
  Stage 1: Statistical Process Control (SPC) Shewhart Filter (cheap gate)
  Stage 2: Multi-Modal Random Forest Classifier (awakened only upon anomaly breach),
           followed by a structured post-classification response plan
"""

import os
import time
import numpy as np

try:
    from gate_thresholds import rf_stage1
except ImportError:
    from ml.gate_thresholds import rf_stage1


class PdMClassifier:
    def __init__(
        self,
        model_path=None,
        spc_baseline_rms=0.080,
        spc_sigma_rms=0.025,
        spc_z_thresh=2.0,
        spc_slope_thresh=5.0,
    ):
        self.model = None
        self.spc_baseline_rms = spc_baseline_rms
        self.spc_sigma_rms = spc_sigma_rms
        self.spc_z_thresh = spc_z_thresh
        self.spc_slope_thresh = spc_slope_thresh

        self.class_names = [
            "Normal Operation",
            "Mechanical Imbalance / Shaft Looseness",
            "Bearing Defect (Raceway / Ball Spalling)",
            "Thermal Runaway / Overheating",
        ]

        # Post-classification decision table. The classifier supplies the fault
        # class; this table turns that class into an operator instruction.
        self.response_plans = {
            0: {
                "class": self.class_names[0],
                "priority": "ROUTINE",
                "action": "Continue unattended monitoring; no maintenance stop required.",
                "timeframe": "Next scheduled inspection",
                "owner": "Operations operator",
                "rationale": "Stage 1 SPC gate passed; no vibration or thermal anomaly signature is present.",
            },
            1: {
                "class": self.class_names[1],
                "priority": "SCHEDULE",
                "action": "Check rotor balance, mounting bolt torque and coupling alignment; book a maintenance window.",
                "timeframe": "Within 24 hours / next planned stop",
                "owner": "Maintenance technician",
                "rationale": "Sustained 1X rotational vibration and looseness signature without impact shocks.",
            },
            2: {
                "class": self.class_names[2],
                "priority": "URGENT",
                "action": "Inspect raceways and rolling elements; arrange bearing replacement before extended operation.",
                "timeframe": "Within 4 hours",
                "owner": "Maintenance engineer",
                "rationale": "High kurtosis, crest factor and acoustic ZCR indicate rolling-element impact spalls.",
            },
            3: {
                "class": self.class_names[3],
                "priority": "CRITICAL",
                "action": "Trip the motor, let it cool, and inspect lubrication, mechanical binding and ventilation before restart.",
                "timeframe": "Immediate",
                "owner": "Shift supervisor + maintenance engineer",
                "rationale": "Temperature and thermal slope exceeded runaway limits; bearing seizure risk is active.",
            },
        }

        if model_path is None:
            model_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), "model.joblib"
            )

        if os.path.exists(model_path):
            try:
                import joblib

                self.model = joblib.load(model_path)
                print(
                    f"[INFO] Two-Stage PdM Classifier initialized with ML model: {model_path}"
                )
            except Exception as e:
                print(
                    f"[WARN] Failed to load joblib model: {e}. Using decision-boundary fallback."
                )

    def get_response_plan(self, class_id):
        """Return the structured operator decision for a classified fault."""
        if type(class_id) is not int or class_id not in self.response_plans:
            raise ValueError(f"Unknown fault class: {class_id!r}")
        return dict(self.response_plans[class_id])

    def get_advice(self, class_id):
        try:
            plan = self.get_response_plan(class_id)
        except ValueError:
            return "Inspect machine condition."
        return (
            f"[{plan['priority']}] {plan['action']} "
            f"Timeframe: {plan['timeframe']}. Owner: {plan['owner']}."
        )

    def predict(self, feature_dict, return_gate_info=False):
        """
        Two-Stage Gated Architecture (Cinar et al. 2022):
          Stage 1: Statistical Process Control (SPC) Shewhart Gate.
                   Evaluates dynamic RMS Z-Score and thermal slope (dT/dt).
                   If nominal, the machine is declared Healthy and the RF stays dormant.
          Stage 2: Random Forest Multi-Modal Classifier.
                   Awakens ONLY when Stage 1 gate is breached, then returns an
                   operator response plan with the classification.
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
        stage1_breached, z_score = rf_stage1(
            rms, kurt, cf, temp, slope,
            self.spc_baseline_rms, self.spc_sigma_rms, self.spc_z_thresh, self.spc_slope_thresh,
        )

        if not stage1_breached:
            # Stage 1 Passed: Nominal Machine State. Random Forest stays DORMANT!
            t_stage1 = (time.perf_counter() - t_start) * 1000.0
            gate_info = {
                "gate_status": "Stage 1 (SPC Normal)",
                "stage1_breached": False,
                "z_score": round(float(z_score), 2),
                "rf_executed": False,
                "latency_ms": round(t_stage1, 4),
                "response_plan": self.get_response_plan(0),
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
                    "latency_ms": round(t_total, 3),
                    "response_plan": self.get_response_plan(class_id),
                }
                if return_gate_info:
                    return (
                        class_id,
                        self.class_names[class_id],
                        round(proba, 2),
                        self.get_advice(class_id),
                        gate_info,
                    )
                return (
                    class_id,
                    self.class_names[class_id],
                    round(proba, 2),
                    self.get_advice(class_id),
                )
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
            "latency_ms": round(t_total, 3),
            "response_plan": self.get_response_plan(cid),
        }
        if return_gate_info:
            return cid, self.class_names[cid], prob, self.get_advice(cid), gate_info
        return cid, self.class_names[cid], prob, self.get_advice(cid)
