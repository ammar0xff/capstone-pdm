#!/usr/bin/env python3
"""
Intelligent Predictive Maintenance (PdM) - Benchmark Dataset Generator
Generates realistic multi-modal sensor windows according to PRD Section 7,
incorporating physical dynamics from Cinar et al. (2022) and empirical baseline rig measurements.

Classes:
  0: Normal / Healthy Operation
  1: Mechanical Imbalance & Looseness (1X/2X rotational vibration)
  2: Bearing Defect (Raceway / Ball Spalling - transient impact shocks)
  3: Thermal Runaway & Friction (Lubrication starvation / binding)
"""

import os
import csv
import numpy as np

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_FILE = os.path.join(OUTPUT_DIR, "windows.csv")

CLASS_NAMES = [
    "Healthy",
    "Mechanical Imbalance",
    "Bearing Defect",
    "Thermal Runaway"
]

def generate_dataset(samples_per_class=350, random_state=42):
    np.random.seed(random_state)
    records = []
    
    # Base parameters
    spc_mu_0 = 0.080
    spc_sigma_0 = 0.025

    print(f"[INFO] Generating {samples_per_class * 4} multi-modal telemetry windows across 4 classes...")

    for class_id in range(4):
        for i in range(samples_per_class):
            event_id = f"EVT_{class_id}_{i:04d}"
            
            if class_id == 0:
                # Class 0: Healthy / Nominal
                rms_dyn = float(np.clip(np.random.normal(0.035, 0.012), 0.005, 0.075))
                peak_dyn = float(rms_dyn * np.random.uniform(1.6, 2.6))
                kurtosis = float(np.clip(np.random.normal(3.0, 0.25), 2.4, 3.8))
                temp_c = float(np.clip(np.random.normal(27.0, 3.5), 22.0, 42.0))
                temp_slope = float(np.random.normal(0.0, 0.4))
                sound_rms = float(np.clip(np.random.normal(0.008, 0.003), 0.002, 0.020))
                sound_db = float(120.0 + 20.0 * np.log10(sound_rms + 1e-9))
                sound_zcr = float(np.clip(np.random.normal(0.025, 0.010), 0.002, 0.065))
                notes = "Nominal machine baseline operation"

            elif class_id == 1:
                # Class 1: Mechanical Imbalance / Shaft Looseness
                # Elevated 1X/2X vibration, continuous energy rise, moderate crest factor, low-frequency hum
                rms_dyn = float(np.clip(np.random.normal(0.220, 0.040), 0.145, 0.380))
                peak_dyn = float(rms_dyn * np.random.uniform(2.0, 3.2))
                kurtosis = float(np.clip(np.random.normal(3.4, 0.35), 2.8, 4.4))
                temp_c = float(np.clip(np.random.normal(38.0, 5.0), 28.0, 52.0))
                temp_slope = float(np.random.normal(0.8, 0.6))
                sound_rms = float(np.clip(np.random.normal(0.035, 0.010), 0.015, 0.075))
                sound_db = float(120.0 + 20.0 * np.log10(sound_rms + 1e-9))
                sound_zcr = float(np.clip(np.random.normal(0.045, 0.015), 0.015, 0.090))
                notes = "Elevated 1X rotational vibration, unbalance / structural looseness"

            elif class_id == 2:
                # Class 2: Bearing Defect (Inner/Outer Race Spalling, Ball Flaking)
                # Severe impulse shocks: Kurtosis explodes to 6-15, High Crest Factor, High ZCR squeal
                rms_dyn = float(np.clip(np.random.normal(0.125, 0.030), 0.070, 0.220))
                kurtosis = float(np.clip(np.random.normal(8.5, 1.8), 5.5, 16.0))
                peak_dyn = float(rms_dyn * np.random.uniform(4.5, 9.0))  # sharp impact peaks
                temp_c = float(np.clip(np.random.normal(48.0, 7.0), 34.0, 68.0))
                temp_slope = float(np.random.normal(2.5, 1.2))
                sound_rms = float(np.clip(np.random.normal(0.045, 0.015), 0.020, 0.095))
                sound_db = float(120.0 + 20.0 * np.log10(sound_rms + 1e-9))
                sound_zcr = float(np.clip(np.random.normal(0.240, 0.045), 0.120, 0.420))  # high-frequency squeal
                notes = "Repetitive impact shockwaves, raceway spalls, high acoustic ZCR"

            elif class_id == 3:
                # Class 3: Thermal Runaway & Lubrication Starvation
                # High absolute temp (>65°C), steep positive thermal slope (>8°C/min), rising friction
                rms_dyn = float(np.clip(np.random.normal(0.095, 0.035), 0.040, 0.190))
                peak_dyn = float(rms_dyn * np.random.uniform(1.8, 3.0))
                kurtosis = float(np.clip(np.random.normal(3.2, 0.4), 2.5, 4.2))
                temp_c = float(np.clip(np.random.normal(76.0, 8.0), 62.0, 98.0))
                temp_slope = float(np.clip(np.random.normal(12.5, 3.5), 6.5, 26.0))
                sound_rms = float(np.clip(np.random.normal(0.025, 0.008), 0.010, 0.055))
                sound_db = float(120.0 + 20.0 * np.log10(sound_rms + 1e-9))
                sound_zcr = float(np.clip(np.random.normal(0.060, 0.020), 0.020, 0.120))
                notes = "Thermal runaway, rapid casing temperature rise, lubrication failure"

            crest_factor = float(peak_dyn / (rms_dyn + 1e-9))
            z_score = float((rms_dyn - spc_mu_0) / spc_sigma_0)
            g_total = float(np.sqrt(rms_dyn**2 + 1.0**2))  # combined dynamic + static 1g

            records.append({
                "event_id": event_id,
                "class_id": class_id,
                "class_name": CLASS_NAMES[class_id],
                "rms_dyn": round(rms_dyn, 5),
                "peak_dyn": round(peak_dyn, 5),
                "crest_factor": round(crest_factor, 3),
                "kurtosis": round(kurtosis, 3),
                "g_total": round(g_total, 4),
                "temp_c": round(temp_c, 2),
                "temp_slope": round(temp_slope, 2),
                "sound_rms": round(sound_rms, 5),
                "sound_db": round(sound_db, 1),
                "sound_zcr": round(sound_zcr, 4),
                "z_score": round(z_score, 2),
                "notes": notes
            })

    # Shuffle dataset
    np.random.shuffle(records)

    with open(DATASET_FILE, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "event_id", "class_id", "class_name", "rms_dyn", "peak_dyn",
            "crest_factor", "kurtosis", "g_total", "temp_c", "temp_slope",
            "sound_rms", "sound_db", "sound_zcr", "z_score", "notes"
        ])
        writer.writeheader()
        writer.writerows(records)

    print(f"[SUCCESS] Benchmark dataset written to {DATASET_FILE} ({len(records)} windows)")
    return DATASET_FILE

if __name__ == "__main__":
    generate_dataset()
