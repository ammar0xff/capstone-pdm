"""Single home of the alarm-gate rules used by the Pi.

Behaviour-preserving extraction: every number below is the value the code used before,
kept per source. The two sources DISAGREE and neither is calibrated on this rig; that is
recorded here on purpose and not resolved. Do not change a value without a calibration result.
"""

# Source 1: edge_daq.py (displayed state)
EDGE = {
    "thermal_fault_temp": 70.0, "thermal_fault_slope": 10.0,
    "thermal_warn_temp": 50.0, "thermal_warn_slope": 5.0,
    "vib_fault_kurtosis": 7.0, "vib_kurtosis_min_rms": 0.03, "vib_fault_peak": 0.40,
    "vib_warn_kurtosis": 5.0, "vib_warn_peak": 0.25,
    "sound_fault_db": 88.0, "sound_fault_zcr": 0.28,
}

# Source 2: rf_predictor.py stage-1 gate (decides whether the RF runs)
RF_GATE = {
    "baseline_rms": 0.080, "sigma_rms": 0.025, "z_thresh": 2.0, "slope_thresh": 5.0,
    "kurtosis": 5.0, "crest_factor": 4.0, "rms": 0.120, "temp": 55.0,
}


def edge_flags(rms_dyn, kurtosis, peak_dyn, temp_c, temp_slope, sound_db, sound_zcr, ucl_warning, ucl_fault):
    t = EDGE
    is_thermal_fault = (temp_c > t["thermal_fault_temp"]) or (temp_slope > t["thermal_fault_slope"])
    is_thermal_warn = (temp_c > t["thermal_warn_temp"]) or (temp_slope > t["thermal_warn_slope"])
    is_vib_fault = (
        (rms_dyn > ucl_fault)
        or (kurtosis > t["vib_fault_kurtosis"] and rms_dyn > t["vib_kurtosis_min_rms"])
        or (peak_dyn > t["vib_fault_peak"])
    )
    is_vib_warn = (
        (rms_dyn > ucl_warning)
        or (kurtosis > t["vib_warn_kurtosis"] and rms_dyn > t["vib_kurtosis_min_rms"])
        or (peak_dyn > t["vib_warn_peak"])
    )
    is_sound_fault = (sound_db > t["sound_fault_db"]) or (sound_zcr > t["sound_fault_zcr"])
    return {"thermal_fault": is_thermal_fault, "thermal_warn": is_thermal_warn, "vib_fault": is_vib_fault,
            "vib_warn": is_vib_warn, "sound_fault": is_sound_fault,
            "any_fault": is_vib_fault or is_thermal_fault or is_sound_fault}


def rf_stage1(rms, kurt, cf, temp, slope, baseline_rms, sigma_rms, z_thresh, slope_thresh):
    """Returns (breached, z_score)."""
    g = RF_GATE
    z_score = (rms - baseline_rms) / max(1e-5, sigma_rms)
    thermal = abs(slope) > slope_thresh or temp > g["temp"]
    vib = z_score > z_thresh or kurt > g["kurtosis"] or cf > g["crest_factor"] or rms > g["rms"]
    return (vib or thermal), z_score
