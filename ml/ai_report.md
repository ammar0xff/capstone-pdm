# Intelligent Predictive Maintenance (PdM) — AI/ML Technical Report & Evidence Dossier
**Grade 12 Industrial Capstone 2026/2027 | Grand Challenge: Industrial Base of Egypt**

- **Author:** Ammar & Capstone Engineering Team
- **Target Rig:** Raspberry Pi 4 Model B (4GB RAM)
- **Model Architecture:** Two-Stage Hierarchical (Coarse Shewhart SPC $\to$ Fine 300-Tree Random Forest)
- **Dataset:** 1,400 physics-simulated windows (350/class, 28 independent `run_id` sessions) · 5-Fold **StratifiedGroupKFold** (run-disjoint) · 70/15/15 group hold-out
- **Result:** Test accuracy **100.0% on the synthetic benchmark only** · single-window inference **26.19 ms on the training host** and **29.99 ms on the Raspberry Pi 4** (both measured) · full inject→alert timing not measured
- **Evidence Files:** `ml/confusion_matrix.png`, `ml/roc_curves.png`, `ml/feature_importance.png`, `ml/model.joblib`, `ml/model_meta.json`, `tests/test_evaluation.py`

> **Honesty note — read this before quoting any number.** The dataset is generated from published physics equations, not measured on a real motor. The 100% figure proves the pipeline separates the simulated classes; it is **not** evidence of 100% accuracy on real hardware. This system performs **fault detection and 4-class fault classification**, with rule-based maintenance advice; it does **not** estimate Remaining Useful Life (predict how many days until failure), which would require run-to-failure time-series measurements. The separate offline tool `ml/degradation_rul.py` can extrapolate a trend to an operator-supplied threshold, but its output is explicitly labelled **not field-validated** and is not used by the runtime or dashboard. A separate public benchmark on NASA C-MAPSS FD001 simulated turbofan data (§10) verifies the RUL pipeline on trusted run-to-failure data; it is **not our motor and not field validation**. `z_score` appears in the CSV but is intentionally **not** a Random Forest input: it is the Stage-1 SPC gate metric computed from `rms_dyn`, and the gate returns it in `gate_info`.
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
