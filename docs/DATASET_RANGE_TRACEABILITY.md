# Dataset Range-to-Source Traceability Register

**Scope.** `ml/dataset_generator.py` produces the 1,400-window synthetic benchmark used for the reported 100% score. This register records where each numeric range came from. A source line is not proof that the value matches the physical rig: synthetic values are marked **simulated**, and missing physical evidence is marked `[NEED: ...]`.

**Read this first.** The benchmark validates the pipeline on physics-inspired simulated windows only. It does not establish real-motor accuracy, time-to-failure, or the false-alarm rate of the deployed gate.

| Quantity | Value / range in generator | Source | Status and evidence gap |
|---|---|---|---|
| `F_R_NOMINAL` | `30.0 Hz` (comment derives `1800 RPM = 30 Hz × 60`) | `ml/dataset_generator.py:58` | Simulated nominal. `[NEED: motor nameplate or tachometer measurement before quoting 1800 RPM as rig hardware.]` |
| Per-run shaft frequency | `F_R_NOMINAL × U(0.96, 1.04)` = `28.8–31.2 Hz` (`1728–1872 RPM`) | `ml/dataset_generator.py:250-252` | Simulated run-to-run slip only; not measured speed variation. |
| `FS_VIB` | `3200 Hz` virtual sampling rate | `ml/dataset_generator.py:59` | **3200 Hz is a synthetic generator rate.** It is not the deployed ADXL345 rate. `[NEED: reconcile with README/PRD `800 Hz`, handbook `340 Hz`, student guide `270 Hz`, and runtime timestamp-derived `fs`.]` |
| `N_SAMPLES` | `1024` samples per vibration window (`1024 / 3200 = 0.32 s`) | `ml/dataset_generator.py:60,80` | Simulated window length. |
| `FS_AUDIO` / `N_AUDIO` | `16000 Hz` / `5120` samples (`0.32 s`) | `ml/dataset_generator.py:61-62,181` | Synthetic I2S rate. `[NEED: reconcile with `edge/edge_daq.py:186` (`48000 Hz`) and the student guide (`48000 Hz`).]` |
| Bearing geometry | 9 balls; ball `7.94 mm`; pitch `39.04 mm`; contact angle `0`; `GAMMA ≈ 0.2034` | `ml/dataset_generator.py:64-69` | Comment names a standard 6205 deep-groove bearing. `[NEED: installed bearing part number and measured geometry.]` |
| Structural resonance / damping | `F_RES = 2400 Hz`; `ZETA = 0.045` | `ml/dataset_generator.py:71-72,123-131` | Simulated impulse response. `[NEED: measured rig resonance and damping; no tap-test evidence in repo.]` |
| Vibration noise floor | `N(0.0084 × noise_factor, 0.0012) g`, floored at `0.005 g`; `noise_factor ~ U(0.85, 1.20)` | `ml/dataset_generator.py:82-84,254` | Comment says “calibrated from ADXL345”, but no raw calibration log is linked. `[NEED: calibration trace or measurement record.]` |
| Healthy 1X amplitude | `U(0.010, 0.038) g` | `ml/dataset_generator.py:93` | Simulated ISO-Zone-A-like residual unbalance. |
| Imbalance harmonics | 1X `U(0.180, 0.320) g`; 2X `U(0.040, 0.110) g`; 3X `U(0.015, 0.045) g` | `ml/dataset_generator.py:100-102` | Simulated centrifugal/looseness signature. |
| Bearing impulses | slip `U(0.01, 0.02)`; amplitude `N(0.48, 0.08)`; background `U(0.025, 0.065) g` | `ml/dataset_generator.py:113-136` | Simulated BPFO/BPFI impact train. |
| Thermal-runaway vibration | rub modulation `0.045 × (1 + 0.4 sin(...))`; 1X `U(0.04, 0.08) g` | `ml/dataset_generator.py:142-144` | Simulated dry rubbing. |
| Ambient temperature | `U(21.5, 26.5) °C` | `ml/dataset_generator.py:253` | Simulated ambient. `[NEED: measured cabinet/ambient range.]` |
| Thermal state by class | Healthy: ambient + `N(2.5, 0.5)`, slope `N(0.02, 0.08)`; imbalance: +`10 + N(3, 1.2)`, slope `N(0.65, 0.25)`; bearing: +`18 + N(5, 2)`, slope `N(2.1, 0.6)`; runaway: +`35 + progress × 28 + N(0, 1.5)`, slope `N(12.5, 2.5)` °C/min | `ml/dataset_generator.py:155-171` | Synthetic thermal trajectories, not measured motor temperatures. The cited ODE is **not** integrated in code. |
| Acoustic synthesis | class hum/noise levels `0.002–0.028`; bursts `U(0.04, 0.12)`; tones `3600/4200/5800 Hz`; SPL clipped to `35–115 dB` | `ml/dataset_generator.py:184-217` | Synthetic microphone signal and SPL formula. `[NEED: acoustic calibration reference.]` |
| Severity zones | Zone A `<0.10 g`; B `<0.15 g`; C `0.15–0.35 g`; D `>0.35 g` | `ml/dataset_generator.py:16-19`; ISO 10816-3 / ISO 20816-3 | Literature threshold used to label simulated severity; not a measured rig limit. |

## SPC baseline mismatch

The synthetic dataset and the runtime gate do **not** use the same baseline:

| Component | Mean `mu_0` | Sigma `sigma_0` | Derived limits | Source |
|---|---:|---:|---|---|
| Dataset `z_score` column | `0.038 g` | `0.014 g` | not used as a hard limit in the CSV | `ml/dataset_generator.py:228-230,280-281` |
| Deployed Stage-1 gate | `0.080 g` | `0.025 g` | warning `≈ 0.130 g`; fault `≈ 0.155 g` | `edge/edge_daq.py:327-330,466-467,484-496` |

This is an explicit **SPC baseline mismatch**, not a verified equivalence. The CSV `z_score` is a Stage-1 gate metric derived from `rms_dyn` and is deliberately excluded from the Random Forest input; the deployed gate recomputes `z_score` from its own configured constants. `[NEED: choose or justify one healthy baseline, then re-run the gate benchmark on real rig data.]`

## Unmeasured rig properties

- `[NEED: motor nameplate speed, load and bearing part number.]` `1800 RPM` above is derived from a simulation constant, not observed on the rig.
- `[NEED: physical DAQ sample rate and resampling method.]` The repository contains conflicting rates: generator `3200 Hz`, README/PRD `800 Hz`, handbook `340 Hz`, student guide `270 Hz`.
- `[NEED: measured resonance, damping, noise floor, and temperature rise.]` Current values are assumptions in `ml/dataset_generator.py`.
- `[NEED: labeled real-motor windows and run-to-failure series.]` Without them, no real-motor accuracy or RUL claim is supportable.

## Verification rule

Any change to these constants requires: (1) updating this register, (2) regenerating and re-testing the dataset if generator constants change, and (3) recording the physical measurement that justifies a rig value. Do not promote a `[NEED:` item into a result without evidence.
