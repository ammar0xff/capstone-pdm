# Sensor calibration method and evidence status

This document replaces the earlier report that contained example-looking raw
counts and verdicts without attached measurement evidence. Those numbers were
not used to write `edge/cal.json` and are withdrawn. The current procedure is
implemented by `edge/calibrate.py`; the operating procedure is
`docs/CALIBRATION_RUNBOOK.md`.

## 1. Why calibrate

Uncalibrated sensors add static offset, sensitivity error and thermal drift.
On this rig the raw ADXL345 counts are converted in `edge/edge_daq.py` as:

```
acceleration_axis = raw_axis * g_scale - g_bias_axis
temperature_c     = raw_temperature_c * t_a + t_b
```

`edge/calibrate.py` fits exactly those five runtime coefficients. It does not
change the classifier, the SPC gate thresholds or the dashboard.

## 2. ADXL345 six-face static test

The sensor is placed with each axis pointing up and down on a level surface.
For axis `i`, let `p_i` be the averaged raw reading with the axis pointing up
(+1 g) and `n_i` the averaged reading pointing down (-1 g).

Per-axis sensitivity in the runtime's units is:

```
scale_i = 2 / (p_i - n_i)                    [g per raw count]
bias_i  = ((p_i + n_i) / 2) * shared_scale   [g]
```

The runtime applies one `g_scale` to all axes, so the shared scale is the mean
of the three `scale_i` values. Each bias uses that same shared scale; this
keeps the certificate and `edge_daq.py` consistent.

Residual for every face and axis is computed after applying the runtime model.
The configured review tolerance is 0.05 g. A residual above tolerance is
reported as `REVIEW`, not hidden or rounded away.

Face order used by the script: `+X, -X, +Y, -Y, +Z, -Z`.

## 3. MAX6675 two-point thermal fit

The K-type probe is measured in two reference states:

1. Crushed ice/distilled water slush: reference 0.0 °C.
2. Boiling distilled water: reference entered by the operator. The historical
   project value is 97.5 °C; `[NEED: measured local boiling temperature or site pressure]`.

For averaged raw readings `R_ice` and `R_boil` and references `T_ice`, `T_boil`:

```
t_a = (T_boil - T_ice) / (R_boil - R_ice)
t_b = T_ice - t_a * R_ice
```

The fit is exact at those two points by construction. It does **not** prove
accuracy at other temperatures. The script therefore offers an optional third
known-temperature check and records its residual separately. Without that
check the certificate explicitly says `Third point: NOT PERFORMED`.

## 4. Safety and data integrity

- The DAQ service must be stopped before calibration so I2C/SPI are not shared.
- Existing `edge/cal.json` is copied to a timestamped backup before any write.
- The new file is written to a temporary file in the same directory and
  replaced atomically.
- Non-finite numbers, wrong face counts, reversed face pairs, implausible
  slopes and hardware read failures abort the run without writing.
- The certificate never issues `PASS`, `CERTIFIED` or exhibition authorization.
  Its verdict is `REVIEW`, `UNVERIFIED` or `FAILED`.

## 5. Evidence status

| Item | Status | Evidence needed |
|---|---|---|
| Calibration runner code | Complete | `edge/calibrate.py`, `tests/test_evaluation.py` |
| Pi operating procedure | Complete | `docs/CALIBRATION_RUNBOOK.md` |
| Six-face raw averages | Not recorded in repository | `[NEED: signed sheet and calibration_runs.jsonl line]` |
| Thermal reference instrument | Not recorded | `[NEED: thermometer ID, calibration date, uncertainty]` |
| Local boiling reference | Default only | `[NEED: measured site value or pressure]` |
| Cold-junction placement | Design constraint documented | `[NEED: photograph and temperature log showing module isolation]` |
| Real-motor feature validation | Not performed | `[NEED: physical run data correlating features with condition]` |

## 6. Withdrawn claims

The following earlier statements are not supported by retained evidence and
must not be repeated in presentations or reports:

- Specific raw ADXL345 counts, offsets and sensitivity percentages in the old
  results table.
- Max temperature error of ±0.50 °C and class-1 probe verification.
- Vibration noise floor of 0.0084 g RMS and derived SNR/ISO zone claim.
- Any automatic “SYSTEM CALIBRATED & AUTHORIZED FOR EXHIBITION” verdict.
