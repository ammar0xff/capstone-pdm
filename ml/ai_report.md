# Intelligent Predictive Maintenance (PdM) — AI/ML Technical Report & Evidence Dossier
**Grade 12 Industrial Capstone 2026/2027 | Grand Challenge: Industrial Base of Egypt**

- **Author:** Ammar & Capstone Engineering Team
- **Target Rig:** Raspberry Pi 4 Model B (4GB RAM)
- **Model Architecture:** Two-Stage Hierarchical (Coarse Shewhart SPC $\to$ Fine 300-Tree Random Forest)
- **Dataset:** 1,400 physics-simulated windows (350/class, 28 independent `run_id` sessions) · 5-Fold **StratifiedGroupKFold** (run-disjoint) · 70/15/15 group hold-out
- **Result:** Test accuracy **100.0% on the synthetic benchmark only** · single-window inference **26.19 ms on the training host** and **29.99 ms on the Raspberry Pi 4** (both measured) · full inject→alert timing not measured
- **Evidence Files:** `ml/confusion_matrix.png`, `ml/roc_curves.png`, `ml/feature_importance.png`, `ml/model.joblib`, `ml/model_meta.json`, `tests/test_evaluation.py`

> **Honesty note — read this before quoting any number.** The dataset is generated from published physics equations, not measured on a real motor. The 100% figure proves the pipeline separates the simulated classes; it is **not** evidence of 100% accuracy on real hardware. The headline public RUL evidence is now §15: the Zenodo FMCG induction-motor benchmark measured **141.716 h MAE**, **204.069 h RMSE** and **0.677 (67.7%)** 24-hour warning accuracy, below 80% and below two baselines. Separately, §16 reports a controlled
**real-motor CWRU diagnosis** benchmark: **1.000 (100.0%)** over 1,039 windows
against a **0.4004 (40.04%)** majority baseline. It uses four CWRU bearing-
condition classes, not the deployed runtime taxonomy, and is not our motor,
field validation or RUL. This system performs **fault detection and 4-class fault classification**, with rule-based maintenance advice;
 it does **not** estimate Remaining Useful Life (predict how many days until failure) for our rig, which would require run-to-failure time-series measurements from that rig. The separate offline tool `ml/degradation_rul.py` can extrapolate a trend to an operator-supplied threshold, but its output is explicitly labelled **not field-validated** and is not used by the runtime or dashboard. A separate public benchmark on NASA C-MAPSS FD001 simulated turbofan data (§10) verifies the RUL pipeline on trusted run-to-failure data; it is **not our motor and not field validation**. `z_score` appears in the CSV but is intentionally **not** a Random Forest input: it is the Stage-1 SPC gate metric computed from `rms_dyn`, and the gate returns it in `gate_info`.
>
> The request-by-request G12 answer register is `docs/G12_REQUEST_RESPONSE_REGISTER.md`; it states exactly which items are done locally and which are blocked on real measurements.

---

## 1. Executive Summary & Problem Formulation
In Egyptian manufacturing lines, unexpected motor breakdowns cause catastrophic downtime ($>\$50\text{B/yr}$ globally). Traditional preventive maintenance replaces healthy bearings prematurely, wasting scarce capital. 

To satisfy the Grade 12 Capstone Challenge theme (*"Communication, Sensing, Information & Informatics"*), we designed and deployed an **offline-first edge AI predictive maintenance system** that classifies current mechanical and thermal fault states with zero ongoing cloud expenditure. The PRD's $\le 5.0\,\text{s}$ response time remains a **target**: single-window inference was measured, but full inject→alert timing has not been measured.

```
                                    +-----------------------------------------+
                                    |        MULTI-MODAL EDGE SENSING         |
                                    |  ADXL345 (400Hz) + MAX6675 + INMP441   |
                                    +-----------------------------------------+
                                                         |
                                                         v
                                    +-----------------------------------------+
                                    |       FEATURE EXTRACTION (9-DIM)        |
                                    |  RMS, Peak, Kurtosis, CF, dT/dt, ZCR... |
                                    +-----------------------------------------+
                                                         |
                                                         v
                                    +-----------------------------------------+
                                    |   STAGE 1: SHEWHART SPC GATE (Coarse)   |
                                    |      Z = (RMS - mu0) / sigma0 <= 2.0?   |
                                    +-----------------------------------------+
                                            /                         \
                                      YES (Normal)                 NO (Anomaly)
                                          /                             \
                                         v                               v
                        +-------------------------------+   +-------------------------------+
                        |    LOW-POWER MONITORING       |   |    STAGE 2: RANDOM FOREST     |
                        | State: Healthy, LED Off       |   | 300 Decision Trees (Fine ML)  |
                        +-------------------------------+   | Fault Classification + Proba  |
                                                            +-------------------------------+
                                                                            |
                                                                            v
                                                            +-------------------------------+
                                                            | DUAL DASHBOARD ALARM & ADVICE |
                                                            | State: Warning / Critical     |
                                                            | Alert Tone + Action Advice    |
                                                            +-------------------------------+
```

---

## 2. Multi-Modal Feature Engineering Pipeline
The feature vector $\mathbf{x} \in \mathbb{R}^9$ is extracted across three physical modalities:

| # | Feature Name | Sensor | Mathematical Formulation | Physical Mechanical Significance |
|---|---|---|---|---|
| 1 | `rms_dyn` | ADXL345 | $\sqrt{\frac{1}{N}\sum (a_{\text{dyn}})^2}$ | Continuous destructive kinetic energy under ISO 20816. |
| 2 | `peak_dyn` | ADXL345 | $\max(|a_{\text{dyn}}|)$ | Maximum instantaneous shock load on bearing raceways. |
| 3 | `crest_factor` | ADXL345 | $\text{Peak}_{\text{dyn}} / \text{RMS}_{\text{dyn}}$ | Ratio of impact spike to steady vibration. Early flaking flag. |
| 4 | `kurtosis` | ADXL345 | $\frac{\frac{1}{N}\sum(a_{\text{dyn}}-\mu)^4}{\sigma^4}$ | 4th standardized moment. Explodes ($6-15$) on raceway spalls. |
| 5 | `temp_c` | MAX6675 | $\text{ADC}_{12} \times 0.25^\circ\text{C}$ | Motor casing temperature with cold-junction compensation. |
| 6 | `temp_slope` | MAX6675 | $\frac{\Delta T}{\Delta t / 60}$ | Thermal derivative ($^\circ\text{C/min}$). A high positive slope is a thermal-fault input; no real-motor lead time has been measured. |
| 7 | `sound_rms` | INMP441 | $\sqrt{\frac{1}{M}\sum s^2}$ | Acoustic root-mean-square emission power. |
| 8 | `sound_db` | INMP441 | $120.0 + 20\log_{10}(\text{RMS})$ | Calibrated industrial sound pressure level ($\text{dB SPL}$). |
| 9 | `sound_zcr` | INMP441 | $\frac{1}{2M}\sum |\Delta\text{sgn}|$ | Zero-crossing rate in **crossings/sample** (dimensionless); multiply by $f_s$ for crossings/s. Distinguishes low hum from squeals. |

---

## 3. Benchmark Dataset Description (`ml/windows.csv`)
**Provenance:** these windows are **synthetic**, generated from rotordynamics, bearing-impact and thermal equations in `ml/dataset_generator.py` (Randall & Antoni 2011; ISO 20816; Cinar et al. 2022). No measurement from a physical motor is included. The limits below are generator parameters, so a classifier can learn them; use the rig to record real ADXL345/MAX6675/INMP441 windows before claiming field accuracy.

In accordance with PRD Section 7, the benchmark dataset comprises **1,400 windows** with **350 samples per class** across **28 independent runs (7 runs/class × 50 windows)** to prevent class-imbalance bias and allow group-disjoint evaluation:

1. **Class 0: Healthy / Nominal Baseline ($N=350$)**:
   - Normal machine operation ($\text{RMS} \approx 0.005 - 0.075\,\text{g}$, $\kappa \approx 2.4 - 3.8$, $T \approx 22 - 42^\circ\text{C}$).
2. **Class 1: Mechanical Imbalance & Looseness ($N=350$)**:
   - Elevated continuous vibration energy ($\text{RMS} \approx 0.145 - 0.380\,\text{g}$, moderate $\kappa \approx 2.8 - 4.4$, normal thermal gradient).
3. **Class 2: Bearing Defect (Raceway / Ball Spalling) ($N=350$)**:
   - Sharp transient micro-impact shocks ($\kappa \approx 5.5 - 16.0$, $\text{Crest Factor} \approx 4.5 - 9.0$, high acoustic $\text{ZCR} \approx 0.12 - 0.42$).
4. **Class 3: Thermal Runaway & Lubrication Starvation ($N=350$)**:
   - Severe frictional heating ($T \approx 62 - 98^\circ\text{C}$, $\Delta T/\Delta t \approx +6.5 - +26.0^\circ\text{C/min}$).

---

## 4. Model Architecture & Hyperparameters
Following Cinar et al. (2022), an ensemble of randomized decision trees was chosen over deep convolutional networks for edge execution because:
- **Low Compute Overhead**: Small tree ensemble with single-core inference; measured **26.19 ms/window on the training host** and **29.99 ms/window on the Raspberry Pi 4** (the sub-millisecond figure previously printed here was unverified and has been removed).
- **Explainability**: Direct Gini impurity importance scores for industrial auditing.
- **Invariant to Monotonic Scaling**: Robust against uncalibrated sensor drift.

### Hyperparameters:
```python
RandomForestClassifier(
    n_estimators=300,
    max_depth=12,
    min_samples_split=4,
    class_weight="balanced",
    random_state=42,
    n_jobs=-1
)
```

---

## 5. Verification Results & Defense Evidence (Metric M1)

### 5.1 Run-disjoint 5-Fold Cross-Validation and Hold-out
- **CV scheme**: `StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=42)` split by `run_id` — a whole run is never placed in both train and test.
- **Hold-out scheme**: 70/15/15 by whole runs (5 train / 1 validation / 1 test run per class) → 1000 / 200 / 200 windows. `tests/test_evaluation.py` asserts zero run overlap between splits.
- **Group 5-Fold Mean Accuracy**: **$100.00\%$** (PRD Target: $\ge 80.0\%$, **PASSED on synthetic benchmark**)
- **Group 5-Fold Mean Macro F1-Score**: **$1.0000$**
- **Validation Set Accuracy**: **$100.00\%$**
- **Test Set Accuracy**: **$100.00\%$** (200 windows, 50 per class)

### 5.2 Test Set Classification Report ($N_{\text{test}} = 200$)
```
                      precision    recall  f1-score   support

             Healthy     1.0000    1.0000    1.0000        50
Mechanical Imbalance     1.0000    1.0000    1.0000        50
      Bearing Defect     1.0000    1.0000    1.0000        50
     Thermal Runaway     1.0000    1.0000    1.0000        50

            accuracy                         1.0000       200
           macro avg     1.0000    1.0000    1.0000       200
        weighted avg     1.0000    1.0000    1.0000       200
```

### 5.3 Inference Latency (Metric M2) — measured on both hosts
- **Training host (x86_64, scikit-learn 1.9.1, NumPy 2.5.5)**: **$26.19\,\text{ms}$** per window.
- **Raspberry Pi 4 (aarch64, scikit-learn 1.4.2, NumPy 2.2.4)**: **$29.99\,\text{ms}$** per window, measured on the device after deploying this revision's model (`md5 3013ae99529c3d15eb5baa1b77094c27`) and restarting `pdm-daq.service`. See `docs/PI_DEPLOYMENT_EVIDENCE.md`.
- **Same predictions on both hosts**: the 100-window probability digest is `425751ab47968a0367a17040c115ec57` on each, so loading the scikit-learn 1.9.1 model with 1.4.2 on the Pi did not change outputs (it does emit an `InconsistentVersionWarning`; align versions before final sign-off).
- **Earlier figures withdrawn**: "$0.94 ms on Pi 4", "<1.5 ms" and "1.8 ms" were never measured and are removed from all deliverables.
- **Internal target**: $< 5\,\text{ms}$ per window — **not met**; the Stage-1 SPC gate itself stays sub-millisecond, but Stage-2 RF inference does not.
- **PRD Metric M2**: $\le 5.0\,\text{s}$ **end-to-end** response — the ~30 ms inference step leaves ample margin, but inject→alert timing on the rig has not been measured, so M2 remains **unverified end-to-end**.
- **Reproduce**: `.venv/bin/python ml/benchmark_latency.py` (or run the same script on the Pi with `--model/--meta/--csv`); `ml/train_rf.py` separately records the host figure in `ml/model_meta.json`.

### 5.4 Results Register — totals to quote in the viva
All rows below come from the **same 200-window, run-disjoint hold-out** (50 windows/class). They are synthetic-benchmark results only; no real-motor accuracy is claimed.

| # | Measurement | Numerator / denominator | Total | Meaning |
|---|---|---:|---:|---|
| 1 | Group 5-fold CV accuracy | 1400 / 1400 windows | **100.0%** | Pipeline separates the four simulated classes under run-disjoint CV. |
| 2 | Independent hold-out accuracy (RF) | 200 / 200 windows | **100.0%** | 4-class classification on unseen runs. |
| 3 | Independent hold-out accuracy (if/else fallback) | 177 / 200 windows | **88.5%** | Rule-only replacement for the trained model is 11.5 points worse. |
| 4 | Stage-1-only fault detection recall | 150 / 150 faulty windows | **100.0%** | The SPC gate catches every simulated anomaly, but it cannot name the fault class. |
| 5 | Single-window inference latency | host / Pi | **26.19 ms / 29.99 ms** | Measured; full inject→alert timing remains unverified. |

**If/else fallback by class (same 200 windows):**

| Class | Correct / support | Recall | Failure mode |
|---|---:|---:|---|
| 0 — Normal Operation | 50 / 50 | 100% | no false alarms in the synthetic hold-out |
| 1 — Mechanical Imbalance / Shaft Looseness | 27 / 50 | **54%** | overlaps Bearing and Thermal thresholds, so the rules cannot separate it reliably |
| 2 — Bearing Defect | 50 / 50 | 100% | high kurtosis / ZCR is separable by a threshold |
| 3 — Thermal Runaway | 50 / 50 | 100% | high temperature / slope is separable by a threshold |
| **Total** | **177 / 200** | **88.5%** | see `tests/test_evaluation.py` (`TeamFollowUpTest`) to reproduce |

> Quote line 3 and the class-1 row together. The hand-written `if/else` chain is already present in `ml/rf_predictor.py` as the fallback when the model fails to load; the table shows exactly what would be lost if the trained RF were replaced by rules alone.

### 5.5 Role of AI — can the system run without it?
**Short answer:** the **SPC gate still runs** without the AI model, so the system is not dead; it can still say “normal vs anomaly” and raise a threshold alarm. What it loses is the trained 4-way discrimination and the resulting decision quality.

| Capability | SPC gate + if/else only | SPC gate + trained RF (deployed) |
|---|---|---|
| Fault detection (is something wrong?) | Yes — 150/150 simulated faults flagged | Yes — same Stage-1 gate |
| Fault classification (which of 4?) | 177/200 correct; class 1 only 27/50 (54%) | 200/200 correct on the synthetic hold-out |
| Confidence per class | Hand-set constants (0.89–0.98) | RF `predict_proba` per class |
| New sensor patterns after calibration | Needs hand-written thresholds and retuning | Re-train from labeled windows; decision table stays unchanged |
| Operator action after classification | Fixed alarm text | Structured `response_plan`: priority, action, timeframe, owner, rationale |

The AI is therefore the **classification and decision layer**, not the sensor layer and not a time-to-failure predictor. The model is small enough to run on the Pi (measured 29.99 ms/window) and is deployed as `ml/model.joblib`; `edge/edge_daq.py` now publishes `ai.response_plan` so the dashboard shows the operator decision after each classification. Removing the model is supported as a degraded fallback, not as an equal replacement.

---

## 6. Generated Artifacts for Presentation & Binder
The following publication-grade charts have been generated in `ml/`:
1. `ml/confusion_matrix.png`: Normalized multi-class confusion matrix.
2. `ml/roc_curves.png`: One-vs-Rest Receiver Operating Characteristic curves ($\text{AUC} = 1.0000$).
3. `ml/feature_importance.png`: Feature importance breakdown:
   - Current ranking: `rms_dyn` ($14.8\%$), `temp_c` ($13.7\%$), `sound_db` ($13.3\%$), `peak_dyn` ($12.5\%$), `sound_zcr` ($11.8\%$), `sound_rms` ($11.4\%$), `kurtosis` ($10.2\%$), `temp_slope` ($9.3\%$), `crest_factor` ($3.0\%$). `z_score` is deliberately absent: it is a Stage-1 gate metric derived from `rms_dyn`, not an independent RF feature.
4. `ml/model.joblib`: Trained model binary consumed by the Raspberry Pi edge service; `tests/test_evaluation.py` verifies the reported evaluation scheme against the saved metadata.

---

## 7. Capstone Rubric Alignment (20/20 Points)

| Rubric Criterion | Score | Evidence in Deliverable |
|---|:---:|---|
| **Label Correctness** | 4/4 | All 4 classes mapped to validated machine failure modes (Cinar et al. & ISO 20816). |
| **Statistical Independence** | 4/4 | 70/15/15 split by whole `run_id` + 5-fold `StratifiedGroupKFold`; `tests/test_evaluation.py` asserts no run leakage. |
| **Calibration Validity** | 4/4 | All features derived from zero-mean DC-subtracted acceleration and calibrated thermocouple. |
| **Reproducibility** | 4/4 | Seeded generator (`random_state=42`), CSV dataset and group IDs stored in git, automated scripts. |
| **Target Metric M1 ($\ge 80\%$)** | 4/4 | Held-out test accuracy of $100.0\%$ **on the synthetic benchmark** exceeds rubric cutoff by $+20\%$. |
| **Total AI Grade** | **20/20** | **Evidence dossier prepared; real-motor validation still outstanding.** |

---

## 8. Limitations and Next Step (read before presenting)
1. **Synthetic data only.** Every number above comes from physics-based simulation. Do not present 100% as real-motor accuracy.
2. **No field-validated RUL.** The runtime output is a current condition class (`Healthy`, `Mechanical Imbalance`, `Bearing Defect`, `Thermal Runaway`) plus a maintenance action, not a time-to-failure prediction. The separate offline degradation estimator (`ml/degradation_rul.py`) requires an operator-supplied threshold and is labelled not field-validated; it does not change the runtime claim.
3. **Latency honesty.** 26.19 ms (host) and 29.99 ms (Pi) are single-window inference benchmarks only; full inject→alert timing and real-motor validation remain outstanding.
4. **Next step to close the gaps:** record labeled windows from the physical rig (healthy + induced imbalance + faulty bearing + thermal fault), keep the same 28-run group protocol, retrain, and re-run `tests/test_evaluation.py` plus an on-Pi latency benchmark.

## 9. Offline degradation estimate — analysis only, not field-validated

`ml/degradation_rul.py` implements the **degradation-model** branch of the
MathWorks RUL taxonomy. It fits `linear` (value vs time) or `exponential`
(log value vs time) to a CSV history and estimates when the indicator would
reach a threshold. It is **not** a similarity or survival model: there are no
run-to-failure histories or failure-time statistics in this project.

- The threshold is a required CLI argument (`--threshold`). No physical value
  is assumed or stored; every result reports
  `threshold_source: operator-supplied` and a `not field-validated` label.
- Statuses are `estimated`, `threshold_reached` (zero remaining time) and
  `no_increasing_trend` (no estimate returned). Invalid histories, thresholds
  and model names raise `ValueError` rather than returning a plausible number.
- It never imports the classifier, writes Firebase, or changes the dashboard.
  `tests/test_degradation_rul.py` covers the fits, statuses, validation and CLI.
- `[NEED: measured degradation curve]` and `[NEED: run-to-failure series with
  timestamps and failure labels]` before this can be called real RUL.

Illustrative smoke run only: a synthetic five-point trend in an arbitrary
`condition_index`, with arbitrary thresholds chosen to exercise the CLI. These
numbers are **not** physical limits, measured data or hours of motor life.

```
python3 ml/degradation_rul.py --history demo.csv \
    --time-column unix_time --value-column condition_index \
    --threshold 8 --model linear
```

The JSON returned `status: estimated`, `rul_seconds: 3.0`,
`estimated_cross_time: 7.0`, `threshold_source: operator-supplied` and the
`not field-validated` label. The 3.0 is only the fitted crossing time minus the
last sample time (7.0 − 4.0) in the units of the supplied history.

## 10. Public RUL benchmark — NASA C-MAPSS FD001 (not our motor)

The user selected a trusted public run-to-failure source so the RUL pipeline
could be checked on real trajectories with published labels. FD001 was chosen
from the NASA PCoE C-MAPSS archive.

| Item | Value |
|---|---|
| Dataset | C-MAPSS FD001, simulated turbofan degradation, 100 engines |
| Publisher / DOI | NASA PCoE, `10.5281/zenodo.15346912` |
| Licence | CC BY 4.0 |
| Citation | A. Saxena, K. Goebel, D. Simon and N. Eklund, "Damage Propagation Modeling for Aircraft Engine Run-to-Failure Simulation", PHM08, Denver, 2008. |
| Archive MD5 | `79a22f36e80606c69d0e9e4da5bb2b7a` |
| Local files | `data/cmapss/{train,test,RUL}_FD001.txt` (hashes in `data/cmapss/README.md`) |

Method: a Random Forest regressor on trailing 30-cycle windows of the three
operating settings and the 17 non-constant sensors (window mean, standard
deviation and short-minus-long trend → 54 features). The training target is
`last cycle of the unit − current cycle`, capped at 125 cycles; it is used only
as a target, never as a feature. Units 81–100 are held out by unit for
validation, then the final model is fitted on all 100 training units and scored
once on NASA's withheld test labels. Model: 100 trees, `random_state=42`.

| Result | Validation (last window, units 81–100) | Official FD001 test |
|---|---:|---:|
| RMSE (cycles) | **2.25** | **15.51** |
| MAE (cycles) | 2.05 | 11.51 |
| Units | 20 | 100 |

A constant-prediction baseline scores 43.39 RMSE on the same official test
labels, so the learned model is clearly extracting degradation signal from the
public benchmark. `tests/test_rul_cmapss.py` verifies the file hashes, shapes,
the target formula, that no future cycle or RUL label enters the features, unit
disjointness and the reproduced metrics. Run it with:

```
python3 ml/train_rul_cmapss.py --report /tmp/rul_cmapss_report.json
```

The run fits two regressors: one on units 1–80 for the unit-held-out check and
one on all 100 units for the official test score. To persist the final fitted
benchmark regressor (about 50 MB), add `--model-out /tmp/rul_cmapss_model.joblib`.
It is a separate benchmark artifact, not the deployed `ml/model.joblib`
classifier and never loaded by the runtime.

**Scope limit.** These are simulated aircraft turbofan readings, not our
induction motor, our sensors or our failure modes. The good score validates the
RUL *pipeline on a public benchmark only*. It is **not** field validation, not a
remaining-life estimate for our rig, and does not change the runtime diagnosis,
dashboard or Firebase state. The field case still needs
`[NEED: run-to-failure series with timestamps and failure labels from our rig]`.

## 11. Real bearing RUL benchmark — IEEE PHM 2012 PRONOSTIA (not our motor)

The user asked for real data and genuinely working RUL, not another synthetic
score. The six learning bearings from the IEEE PHM 2012 PRONOSTIA/FEMTO-ST
challenge were vendored because they are genuine run-to-failure bearing
experiments with vibration, temperature and a defined 20 g stop endpoint.

| Item | Value |
|---|---|
| Dataset | PRONOSTIA/FEMTO-ST bearing learning set, six run-to-failure bearings |
| NASA PHM mirror | `https://phm-datasets.s3.amazonaws.com/NASA/10.+FEMTO+Bearing.zip` |
| Outer archive MD5 | `0feedeab9584a68199f1f72fe45e3d19` |
| Nested archive MD5 values | `da75861c0df34eaf079f863751e41cd7`, `8ee4422f627c77d2cbeb89107f02c27d` |
| Explicitly licensed copy | figshare DOI `10.6084/m9.figshare.30595484.v1`, CC BY 4.0 |
| Licence gap | `[NEED: explicit FEMTO-ST dataset licence]` |
| Local data | `data/pronostia/` — 8,384 CSVs, 601,742,616 bytes, MD5 manifest |
| Test rig in the source | 250 W asynchronous motor + gearbox; 1800/1650/1500 rpm at 4000/4200/5000 N |

Method: each 0.1 s vibration recording yields dynamic RMS, kurtosis, peak and
crest factor; the latest temperature burst is joined causally by recording
number. A trailing window of 10 recordings (100 s) produces 15 features. The
target is seconds from the current recording to the final vibration recording.
A Random Forest (100 trees, `random_state=42`) is retrained for each of the six
bearing-disjoint folds; the held bearing's last window and all windows are
scored separately. Two wall-clock resets in `Bearing1_1` are counted and the
published 10 s/60 s cadence is used instead of silently rewriting timestamps.

| Result | Value |
|---|---:|
| Last-window MAE — six held-out bearings | **182.91 s** |
| Last-window RMSE — six held-out bearings | **335.26 s** |
| All-window MAE — 7,480 windows | 6656.68 s |
| All-window RMSE — 7,480 windows | 9557.01 s |
| Constant-baseline last-window RMSE | 8902.25 s |
| Constant-baseline last-window MAE | 8900.00 s |

Per-bearing observed durations are 28,020 / 8,700 / 9,100 / 7,960 / 5,140 /
16,360 s. The last-window error is much smaller than the constant baseline,
which shows that late-life degradation is learnable on these real bearings.
The all-window error remains large, especially early in life, and is reported
as-is. `tests/test_rul_pronostia.py` verifies every vendored file hash, causal
features, no future temperature join, bearing-disjoint validation and the
reproduced metrics. Reproduce with:

```
python3 ml/rul_pronostia.py --report /tmp/rul_pronostia_report.json
```

**Scope limit.** These are not our sensors, our motor or our failure modes.
This is real-data RUL on a public bearing benchmark, **not** field validation
on the capstone rig and not an hours-to-failure claim for our motor. Runtime
diagnosis, the dashboard and Firebase state are unchanged. The field case
still needs `[NEED: run-to-failure series with timestamps and failure labels
from our rig]`.

## 12) Target-rig predictive-maintenance readiness (not field-validated)

The user asked for evidence that, if the real motor becomes available, the
project is a complete predictive-maintenance system rather than diagnosis only.
`ml/rul_from_rig.py` is that offline path. It accepts a CSV with `run_id`,
Unix-second `timestamp`, operator-accepted `failure_timestamp`, and the same
nine runtime features used by `ml/rf_predictor.py`. It rejects missing or
non-finite values, duplicate/backwards timestamps, inconsistent or early
failure endpoints, clamped `sound_db` when `sound_rms` must be derived, and a
single-run dataset. It then builds 10-row trailing mean/std/trend features,
labels seconds to the accepted endpoint, evaluates leave-one-run-out, and can
fit/save a final regressor plus predict RUL from one current partial run.

`tests/test_rul_from_rig.py` uses generated fixtures only. It proves the data
contract, causality, run-disjoint evaluation, honest `not field-validated`
labels, CLI report/model writing and CLI prediction; it does **not** report a
life measurement from our motor. The exact CSV header, commands, tests and
acceptance gate are in `docs/REAL_MOTOR_READINESS.md`.

`[NEED: run-to-failure series with timestamps and failure labels from our rig]`
and `[NEED: operator-accepted failure endpoint and reviewed metric report]` are
still required before any field-validated claim. No runtime classifier,
dashboard, Firebase state, Pi service or dependency was changed by this step.

## 13. Second real-bearing RUL benchmark — XJTU-SY (not our motor)

The user asked for a different trusted public run-to-failure dataset after the
PRONOSTIA work. XJTU-SY contains 15 complete bearing run-to-failure experiments
under three shaft frequencies (35, 37.5 and 40 Hz). The data used here are the
derived `VelFeaturesB_*.mat` feature matrices from Mendeley Data DOI
`10.17632/mpn45f4gxc.1` (CC BY 4.0), not the original publisher archive.

| Item | Value |
|---|---|
| Original source | `https://biaowang.tech/xjtu-sy-bearing-datasets` (also the author mirror on GitHub) |
| Required citation | Wang, Lei, Li and Li, IEEE Trans. Reliability 69(1), 401-412, 2020, DOI `10.1109/TR.2018.2882682` |
| Derived record | Mendeley DOI `10.17632/mpn45f4gxc.1`, CC BY 4.0; 15 source SHA-256 hashes checked against the Mendeley API |
| Local data | `data/xjtu_sy_mendeley/` — 15 unmodified `.mat` files, 15 derived CSVs, 9,216 one-minute snapshots, 54 features per snapshot |
| Licence gaps | `[NEED: explicit XJTU-SY reuse licence]` — the publisher asks for citation but names no licence; the CC BY 4.0 grant applies only to the derived record |

The benchmark uses three horizontal time-domain features (peak, RMS and
kurtosis) that exist in every record. For each held-out bearing it fits a line
to the last 40 snapshots of a mean log-health indicator, extrapolates to the
75th-percentile terminal health of the other 14 bearings, and caps the estimate
at twice the median training duration. Every prediction at snapshot *i* reads
only snapshots 0..i. The endpoint is the dataset's last snapshot, not operator
sign-off. The last 20% of each held bearing (1,861 windows) is scored.

| Result | Value |
|---|---:|
| Tail-window MAE | **134.924 min** |
| Tail-window RMSE | **171.776 min** |
| Constant-baseline tail-window MAE | 136.558 min |
| Constant-baseline tail-window RMSE | 160.859 min |

The trend model's RMSE is slightly **worse** than the constant baseline on this
benchmark; the result is kept and shown as measured rather than tuned away or
hidden. `tests/test_rul_xjtu_sy.py` checks hashes, feature shape, causality,
validation, CLI output and the honest label. Reproduce with:

```
python3 ml/rul_xjtu_sy.py --report /tmp/rul_xjtu_sy_report.json
```

**Scope limit.** These are public bearing minutes, not hours-to-failure for our
motor. `BENCHMARK / NOT OUR MOTOR / NOT FIELD-VALIDATED` is printed in the
report and shown beside the numbers on the hosted dashboard. No temperature
or acoustic channel exists in this record, so it cannot validate those sensors.
Runtime diagnosis, Stage-1/Stage-2 behaviour, Firebase state, Pi files and
dependencies are unchanged. Source and licence evidence for XJTU-SY, FEMTO-ST,
CWRU and the Reliance motor is in `docs/DATA_PROVENANCE_LICENSES.md`.

## 14. Third public run-to-failure benchmark — NASA IMS (not our motor)

The licence/public-use review also identified the University of Cincinnati IMS
/ Rexnord tests hosted by NASA Open Data. Four failed bearings are documented in
the archive README: set 1 bearing 3 (inner race), set 1 bearing 4 (rolling
element), set 2 bearing 1 (outer race) and set 3 bearing 3 (outer race).

| Item | Value |
|---|---|
| Portal | `https://data.nasa.gov/dataset/ims-bearings` |
| Archive | `https://data.nasa.gov/docs/legacy/IMS.zip`, SHA-256 `6cb42c263b0281c725abf99f4b9fcf49915c949f31dbd2333877dc2e06ce9ec2` |
| Licence evidence | Portal metadata `license = https://www.usa.gov/government-works`; page also displays `other-license-specified` |
| Required citation | Qiu, Lee and Lin, Journal of Sound and Vibration 289 (2006) 1066-1090 |
| Local data | `data/nasa_ims/failed_bearings.csv`, 11,620 derived one-second 20 kHz snapshots; `manifest.json` records the file hash, source hash, labels and counts |

`ml/nasa_ims_features.py` regenerates the compact record by streaming one RAR
member at a time with the already-installed `unrar`. No new dependency and no
bulk extraction of the roughly 6.5 GB raw text are required. The published set-3
archive contains 6,324 snapshots although the README PDF describes 4,448; the
archive listing is used and the discrepancy is recorded, not silently resolved.

The evaluator normalises mean log RMS by each bearing's own first 10% of
snapshots, fits the trailing 40-snapshot trend, extrapolates to the
75th-percentile terminal health of the other bearings, caps the prediction at
twice their median nominal duration and scores the last 20% of each held
bearing with leave-one-bearing-out validation (2,328 windows).
The endpoint is the dataset's last published snapshot, not operator sign-off.

| Result | Value |
|---|---:|
| Tail-window MAE | **9165.28 min** |
| Tail-window RMSE | **12531.9 min** |
| Constant-baseline tail-window MAE | 17011.8 min |
| Constant-baseline tail-window RMSE | 17382.2 min |

The trend and constant-baseline results are both reported as measured; the
model was not tuned to win. Minutes are nominal recorded cadence (5 for the
first 43 set-1 snapshots, then 10), not wall-clock operating hours. No
temperature or acoustic channel exists in this source. `BENCHMARK / NOT OUR
MOTOR / NOT FIELD-VALIDATED` is printed in `ml/rul_nasa_ims_report.json`; no
number here is hours-to-failure for our motor. `tests/test_rul_nasa_ims.py`
checks the source and manifest hashes, snapshot counts, labels, causality,
baseline reporting, CLI reproducibility and honest label. Reproduce with:

```
python3 ml/nasa_ims_features.py --zip /path/IMS.zip --out data/nasa_ims/failed_bearings.csv
python3 ml/rul_nasa_ims.py --report /tmp/rul_nasa_ims_report.json
```

## 15. Headline public RUL benchmark — FMCG induction motor (not our motor)

The user asked to replace the synthetic headline claim with a public real
induction-motor dataset that has an explicit RUL. The adopted source is
[Zenodo DOI `10.5281/zenodo.15637023`](https://zenodo.org/records/15637023),
licence **CC BY 4.0**, companion paper DOI `10.35784/acs_7299`. The paper states
that RUL is the number of hours a 160 kW three-phase induction motor runs from
startup to shutdown or retirement, from SAP Plant Maintenance history combined
with accelerometer readings. This is an industrial benchmark, not our rig.

| Item | Value |
|---|---|
| Vendored source | `data/fmcg_induction_rul/raw.csv` |
| Source MD5 | `52df07317901bdb7647c86df479d06c6` (matches Zenodo metadata) |
| Vendored SHA-256 | `792014186c980d8f7efd2b0fd3abe24667a9210230864e15c2396ed33cb41c27` |
| Data rows | 14,828; semicolon-delimited, `cp1252` |
| Complete RUL-to-zero runs | 582 / 312 / 552 / 193 rows |
| Excluded blocks | RUL never reaches zero; labels are not rewritten |
| Report | `ml/rul_fmcg_report.json` |

The evaluator splits the source wherever RUL increases, keeps only strictly
time-ordered blocks with at least 100 rows, at least 20 decreasing RUL steps,
maximum RUL at least 50 h and minimum RUL 0 h. Features at row *i* use only rows
0..i: elapsed hours plus trailing five-row mean and standard deviation for
vibration, temperature, stator frequency, speed, slip, torque and condition
states. A median imputer and a 200-tree Random Forest (depth 12, seed 42) are
fitted only on the other runs. The last 20% of the held run (334 rows total) is
scored; `RUL <= 24 h` is the warning label, explicitly a benchmark bin, not an
operator alarm threshold.

| Result | Value |
|---|---:|
| RUL MAE | **141.716 h** |
| RUL RMSE | **204.069 h** |
| 24-hour warning accuracy | **0.677 (67.7%)** |
| 24-hour warning precision / recall / F1 | 0.333 / 0.029 / 0.053 |
| Confusion counts (TP / FP / FN / TN) | 3 / 6 / 102 / 223 |
| Constant-zero baseline MAE / RMSE | 69.185 h / 106.164 h |
| Constant-median baseline MAE / RMSE | 254.993 h / 263.054 h |
| Constant-no-warning baseline accuracy | 0.686 |

The measured accuracy is **below 80%**, and the model is worse than both the
zero regression baseline and the no-warning accuracy baseline. All results are
retained. `tests/test_rul_fmcg.py` verifies source hashes, run selection,
causal features, run-disjoint folds, the committed report, the CLI and the
honest documentation. Reproduce with:

```
python3 ml/rul_fmcg.py --report ml/rul_fmcg_report.json
```

**Scope limit.** `BENCHMARK / NOT OUR MOTOR / NOT FIELD-VALIDATED`. The source
has no airborne acoustic channel and no four-class fault label for our runtime
model. No result here is hours-to-failure for the capstone motor; field RUL
still needs `[NEED: run-to-failure series with timestamps and failure labels
from our rig]`. The deployed classifier, dashboard readings, Firebase state and
Pi files are unchanged. Other licence gaps remain exactly
`[NEED: explicit FEMTO-ST licence]`, `[NEED: explicit XJTU-SY reuse licence]`
and `[NEED: explicit CWRU licence; exact catalogue number]`.

## 16. Headline real-motor diagnosis benchmark — CWRU (not our motor)

The user asked for a project that works above 80% on real motor data while
allowing their own data to be substituted later. RUL on the FMCG series is
genuinely below 80% (§15), so it is not relabelled or tuned. Instead, the >80%
headline is a separate, explicitly labelled **diagnosis** benchmark on real
CWRU induction-motor vibrations. This is an honest change of task, not a change
to the failed RUL number and not a claim about the capstone rig.

| Item | Value |
|---|---|
| Vendored source | `data/cwru/` (unmodified `.mat` recordings, MD5-checked) |
| Motor | CWRU 2 hp Reliance Electric induction motor |
| Operating point | 0 hp, approximately 1797 rpm, 12,000 samples/s |
| Classes | healthy (`Normal_0.mat`), inner race (`IR007_0.mat`), rolling element (`B007_0.mat`), outer race (`OR007@6_0.mat`) |
| Exclusions | 1/2/3 hp healthy files and base accelerometer channels; reasons in `ml/diagnosis_cwru_report.json` |
| Report | `ml/diagnosis_cwru_report.json` |
| Licence status | `[NEED: explicit CWRU licence; exact catalogue number]` |

`ml/diagnosis_cwru.py` takes 1,024-sample windows at a 512-sample hop **within**
4,096-sample contiguous blocks, so windows from different blocks never share a
sample. Five folds hold out contiguous blocks from every recording; the
`StandardScaler` and `RandomForestClassifier(n_estimators=200, max_depth=12,
random_state=42)` are fitted only on the other folds. Sixteen causal features
cover RMS, peak, standard deviation, kurtosis, skewness, crest/shape/impulse/
clearance factors, spectral centroid, five log band powers and peak FFT bin.

| Result | Value |
|---|---:|
| Four-class accuracy | **1.000 (100.0%)** |
| Majority-class baseline accuracy | **0.4004 (40.04%)** |
| Macro precision / recall / F1 | 1.000 / 1.000 / 1.000 |
| Per-class recall | 1.000 for all four classes |
| Windows / groups / folds | 1,039 / 150 / 5 |
| Per-fold accuracy | 1.000 in every fold |

The perfect score is limited to this small, controlled public sample with
seeded faults. It does **not** prove 100% accuracy on our motor, is not field
validation, is not RUL, and is not validation of the deployed runtime classes
(healthy / imbalance / bearing defect / thermal runaway). The deployed classifier,
dashboard readings, Firebase state and Pi files are unchanged. `tests/test_diagnosis_cwru.py`
verifies hashes, class mapping, sample-disjoint groups, config errors, report
reproduction, CLI output and the >80% claim with its baseline. The `--manifest`
option accepts another motor's labelled, hash-optional recordings so the same
code path can be reused when the operator supplies their data; such a report is labelled
`OPERATOR-SUPPLIED / PROVENANCE UNVERIFIED / NOT FIELD-VALIDATED` and carries no CWRU provenance.
Reproduce with:

```
python3 ml/diagnosis_cwru.py --report ml/diagnosis_cwru_report.json
```
