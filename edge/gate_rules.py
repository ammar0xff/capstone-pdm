"""Pure copy of the Pi's stage-1 breach rules from edge_daq.py (lines ~484-497),
extracted UNCHANGED so they can be characterised offline. edge_daq.py still uses
its own inline copy; nothing here changes Pi behaviour. If these drift from
edge_daq.py the characterization test in tests/test_gate_rules.py will not notice,
so keep the two in step by hand until edge_daq imports this module."""


def edge_flags(rms_dyn, kurtosis, peak_dyn, temp_c, temp_slope, sound_db, sound_zcr, ucl_warning, ucl_fault):
    is_thermal_fault = (temp_c > 70.0) or (temp_slope > 10.0)
    is_thermal_warn = (temp_c > 50.0) or (temp_slope > 5.0)
    is_vib_fault = (rms_dyn > ucl_fault) or (kurtosis > 7.0 and rms_dyn > 0.03) or (peak_dyn > 0.40)
    is_vib_warn = (rms_dyn > ucl_warning) or (kurtosis > 5.0 and rms_dyn > 0.03) or (peak_dyn > 0.25)
    is_sound_fault = (sound_db > 88.0) or (sound_zcr > 0.28)
    return {"thermal_fault": is_thermal_fault, "thermal_warn": is_thermal_warn, "vib_fault": is_vib_fault,
            "vib_warn": is_vib_warn, "sound_fault": is_sound_fault,
            "any_fault": is_vib_fault or is_thermal_fault or is_sound_fault}
