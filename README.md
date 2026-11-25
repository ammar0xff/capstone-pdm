# Intelligent Predictive Maintenance & Remote Monitoring — G12 Capstone 2026/27

Raspberry Pi 4 edge condition monitoring for a three-phase induction motor rig.
The system samples vibration, temperature and acoustic sensors, applies a
statistical gate, then runs a four-class Random Forest diagnosis when that gate
is breached. Results are presented on a local Flask dashboard and mirrored to
Firebase Realtime Database. The hosted dashboard is presentation-only.

**Current status:** implementation and the four-class **synthetic** benchmark
are complete; physical-rig validation, field-validated RUL and measured CPU
savings are not. The headline **real-motor diagnosis** evidence is now a
controlled CWRU four-class bearing-condition benchmark on a real 2 hp Reliance
Electric induction motor: **1.000 (100.0%)** accuracy over 1,039 windows with
sample-disjoint contiguous-block folds, against a **0.4004 (40.04%)**
majority-class baseline. Those four classes (healthy / inner race / ball /
outer race) are **not** the deployed runtime taxonomy, and the result is
`BENCHMARK / NOT OUR MOTOR / NOT FIELD-VALIDATED` — not "on our motor".
The above-80% RUL evidence is a separate **30-cycle RUL warning** benchmark on
NASA's simulated C-MAPSS FD001 turbofan data (DOI
`10.5281/zenodo.15346912`, CC BY 4.0): **0.940 (94.0%)** accuracy on the 100
official last-cycle units against a **0.750** majority baseline, precision
**0.9524**, recall **0.800** and five unit-disjoint folds averaging **0.9705**.
It uses explicit RUL labels, but it is a simulated short-horizon warning task,
not continuous RUL, not our induction motor, not an operator alarm and not field
validation. The separate real induction-motor RUL evidence remains a real 160 kW three-phase
induction-motor dataset with an explicit operating-hours RUL label (Zenodo DOI
`10.5281/zenodo.15637023`, CC BY 4.0). Four leave-one-run-out RUL-to-zero trials
measured MAE **141.716 h**, RMSE **204.069 h** and 24-hour warning accuracy
**0.677 (67.7%)** with recall **0.029** over 334 tail rows. The constant-zero
baseline (MAE **69.185 h**, RMSE **106.164 h**) and the constant-no-warning
baseline (accuracy **0.686**) are better, so the measured shortfall is reported
rather than hidden and is not tuned to reach 80%. An offline degradation
estimator is available as an analysis tool only; it requires an operator-
supplied threshold. Other public checks remain NASA C-MAPSS FD001 (simulated
turbofan), six PRONOSTIA/FEMTO-ST bearings (last-window MAE **182.91 s**, RMSE
**335.26 s**), 15 XJTU-SY bearings (tail MAE **134.924 min**, RMSE **171.776 min**
against **160.859 min** baseline RMSE) and four documented NASA IMS failures
(tail MAE **9165.28 min**, RMSE **12531.9 min** against **17382.2 min** baseline
RMSE), all benchmark-only. CWRU has no run-to-failure series, so it supports
diagnosis but not an RUL claim. A target-rig readiness path is in place: once
the operator supplies real run-to-failure CSVs from our motor,
`ml/rul_from_rig.py` can evaluate, fit and predict RUL; it is not field-validated
until that data and the failure endpoint are accepted. See
`docs/REAL_MOTOR_READINESS.md`,
`docs/G12_REQUEST_RESPONSE_REGISTER.md` for request-by-request evidence and
`docs/EXHIBITION_REVIEW_PACK.md` for the Arabic review/demo sheet.

## Start here

| Goal | Read |
|---|---|
| Understand every file and generated artifact | `docs/FILE_MAP.md` |
| Develop, test, deploy and roll back safely | `docs/DEVELOPMENT_OPERATIONS.md` |
| Calibrate the sensors on the Pi | `docs/CALIBRATION_RUNBOOK.md` and `edge/calibrate.py` |
| Create or audit the Firebase mirror | `docs/FIREBASE_SETUP.md` |
| Full English step-by-step project guide | `docs/PROJECT_GUIDE.html` → `docs/G12_Project_Guide.pdf` |
| Honest answers to all 13 G12 requests | `docs/G12_REQUEST_RESPONSE_REGISTER.md` |
| AI design, training and measured results | `ml/ai_report.md` |
| Pi deployment evidence and latency | `docs/PI_DEPLOYMENT_EVIDENCE.md` |
| Arabic exhibition/review sheet, demo and Q&A | `docs/EXHIBITION_REVIEW_PACK.md` |
| What is ready for RUL on our rig, and what evidence is still missing | `docs/REAL_MOTOR_READINESS.md` |
| Dataset sources, DOI and licence evidence (including `[NEED: ...]` gaps) | `docs/DATA_PROVENANCE_LICENSES.md` |
| Requirements and scope | `PRD.md` |

## System at a glance

```
ADXL345 (I2C) ─┐
MAX6675 (SPI) ─┼─> edge/edge_daq.py ─> Stage 1 SPC gate ─> Stage 2 RF diagnosis
INMP441 (I2S) ─┘          │                       │
                          ├─> edge/dashboard.py    ├─> edge/firebase_mirror.py
                          └─> edge/cal.json        └─> hosted public/index.html
```

- **Stage 1** checks vibration RMS and thermal rise. On a nominal window the
  classifier wrapper returns without calling `predict_proba`.
- **Stage 2** returns one of four classes: Healthy, Mechanical Imbalance,
  Bearing Defect or Thermal Runaway, plus an operator response plan.
- The 100% score in `ml/ai_report.md` belongs only to the run-disjoint
  **synthetic** benchmark. It is not a real-motor accuracy claim.
- The dashboard shows live state, charts and links. The device packet still
  carries `ai.response_plan`, but the hosted page no longer displays the
  priority/timeframe/owner decision block. It has no calibration write endpoint
  and no simulator controls.
- `ml/degradation_rul.py` is an **offline** trend-to-threshold estimator. It is
  not part of the runtime diagnosis, needs an operator threshold, and is
  labelled "not field-validated" in every result.
- `ml/train_rul_cmapss.py` reproduces a public continuous-RUL benchmark on
  simulated turbofan run-to-failure data. It is a pipeline check only, never a
  life prediction for our induction motor.
- `ml/rul_cmapss_warning.py` reproduces the above-80% RUL **warning** benchmark
  on the same public simulated turbofan data with explicit RUL labels and a
  fixed 30-cycle horizon. It is not our motor, not field validation and not a
  runtime alarm.
- `ml/rul_pronostia.py` reproduces RUL on six real PRONOSTIA bearing
  run-to-failure experiments with leave-one-bearing-out validation. It is
  genuine bearing data, still not our motor and not field validation.
- `ml/rul_xjtu_sy.py` evaluates a second public bearing benchmark (XJTU-SY,
  15 run-to-failure bearings) from a CC BY 4.0 derived feature record. Its
  result is labelled `BENCHMARK / NOT OUR MOTOR / NOT FIELD-VALIDATED` and is
  displayed as such on the hosted dashboard.
- `ml/rul_nasa_ims.py` evaluates a third public benchmark on the four failures
  documented in the NASA IMS bearing tests; it is also labelled benchmark only,
  with nominal recorded minutes rather than wall-clock hours.
- `ml/diagnosis_cwru.py` is the headline real-motor diagnosis benchmark: four
  bearing-condition classes from a real CWRU induction motor, grouped by
  non-overlapping sample blocks, with a majority baseline and a `--manifest`
  option for another motor's labelled recordings. Its 100.0% result is not the
  deployed four-class taxonomy and is not our motor.
- `ml/rul_fmcg.py` is the headline public RUL benchmark on real 160 kW
  three-phase induction-motor data with explicit operating-hour RUL labels. Its
  measured 67.7% 24-hour warning accuracy is below 80% and is reported as-is.
- `ml/rul_from_rig.py` is the offline target-rig readiness path: it validates
  operator-supplied run-to-failure CSVs, evaluates causally and run-disjointly,
  fits a final RUL regressor and predicts from a current run. No field result is
  claimed and no runtime behaviour is changed.

## First-time setup

### Development machine

```bash
cd ~/Documents/antigravity/intelligent-raman
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m unittest discover -s tests -v
python3 circuit/build.py
```

### Raspberry Pi

The verified Pi path is `/home/renad/pdm`, user `renad`. Confirm `User=`,
`WorkingDirectory=` and `ExecStart=` in `edge/*.service` before copying them.

```bash
ssh renad@<pi-address>
cd ~/pdm
sudo cp edge/pdm-daq.service edge/pdm-cloud.service edge/pdm-dashboard.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now pdm-daq.service pdm-cloud.service pdm-dashboard.service
sudo systemctl status pdm-daq.service pdm-cloud.service pdm-dashboard.service
```

Only the three units above are services. `edge/calibrate.py`,
`edge/raw_measure.py`, `edge/exhibition_drill.py` and `edge/generate_qr.py` are
operator-run tools, not daemons. `edge/stream_live.py` is retired: it no longer
generates or uploads simulated packets. The RTDB path is written only by
`edge/firebase_mirror.py` from device state; `tests/test_device_only_telemetry.py`
guards this.

**REMOVE SIMULATOR, ALL FROM DEVICE.** No simulator can publish to the hosted
dashboard. Missing, null or stale packets are shown as `NO DATA` or
`AWAITING DATA`; they are not falsely labelled as device telemetry.

### Raw measurements — read the sensors directly

`edge/raw_measure.py` prints the uncalibrated ADXL345 LSB counts and the raw
MAX6675 16-bit word. It does **not** apply `edge/cal.json` and does not write it.
Stop the DAQ service first so the buses are not shared:

```bash
ssh renad@<pi-address>
cd ~/pdm
sudo systemctl stop pdm-daq.service
python3 edge/raw_measure.py
python3 edge/raw_measure.py --csv edge/raw_measurements.csv --count 20
sudo systemctl start pdm-daq.service
```

Use these readings as the raw observations for a manual calibration entry; they
are not calibrated `g` or `°C` values. The `T_datasheet` column is the MAX6675
datasheet conversion only and is marked `UNCALIBRATED`.

### Calibration — run on the Pi, not on the laptop

Stop the DAQ service first so the SPI/I2C buses are not shared during sampling:

```bash
ssh renad@<pi-address>
cd ~/pdm
sudo systemctl stop pdm-daq.service
python3 edge/calibrate.py
sudo systemctl start pdm-daq.service
```

The script asks for the operator name, samples six ADXL345 faces and two
MAX6675 reference points, backs up `edge/cal.json`, writes it atomically, saves
`edge/calibration_certificate.md` and appends `edge/calibration_runs.jsonl`.
It reports `REVIEW` or `UNVERIFIED`; it never issues a fake PASS. Use
`python3 edge/calibrate.py --manual` only when entering previously recorded
averaged readings. Full procedure: `docs/CALIBRATION_RUNBOOK.md`.

### Firebase

The current project is `castpone2026` and the mirror URL is
`https://castpone2026-default-rtdb.firebaseio.com/motor1.json`.
The existing rules are public read/write; no auth change has been made.
See `docs/FIREBASE_SETUP.md` before altering the rules or client behavior.

### Dashboard

- Local: `http://<pi-address>:5000/` from `edge/dashboard.py`.
- Hosted: `https://castpone2026.web.app/` from `public/index.html`.
- Exhibition deck: `https://castpone2026.web.app/guide.html`.
- Update hosted files: `firebase deploy --only hosting`.

## Verification status

| Area | Evidence | Status |
|---|---|---|
| Run-disjoint synthetic benchmark | `ml/ai_report.md`, `tests/test_evaluation.py` | Complete |
| Edge gate and four-class decision | `edge/edge_daq.py`, `ml/rf_predictor.py` | Complete in code |
| Pi services and model deployment | `docs/PI_DEPLOYMENT_EVIDENCE.md` | Verified on 2026-11-23 |
| Pi latency | 26.19 ms host / 29.99 ms Pi, single-window inference | Measured; full inject→alert timing not measured |
| Offline degradation estimator | `ml/degradation_rul.py`, `tests/test_degradation_rul.py` | Implemented; operator threshold required; not field-validated |
| Public continuous-RUL benchmark | `ml/train_rul_cmapss.py`, `data/cmapss/`, `tests/test_rul_cmapss.py` | Complete on NASA C-MAPSS FD001 (simulated turbofan); not our motor |
| Above-80% public RUL warning benchmark | `ml/rul_cmapss_warning.py`, `ml/rul_cmapss_warning_report.json`, `tests/test_rul_cmapss_warning.py` | 0.940 (94.0%) at 100 official last-cycle units vs 0.750 majority; precision 0.9524, recall 0.800; five unit-disjoint folds mean 0.9705; simulated turbofan, not our motor or field validation |
| Real-bearing RUL benchmark | `ml/rul_pronostia.py`, `data/pronostia/`, `tests/test_rul_pronostia.py` | Complete on six PRONOSTIA run-to-failure bearings; not our motor, not field-validated |
| Second real-bearing RUL benchmark | `ml/rul_xjtu_sy.py`, `data/xjtu_sy_mendeley/`, `tests/test_rul_xjtu_sy.py` | Complete on 15 XJTU-SY bearings; labelled benchmark, baseline comparison reported honestly; not our motor |
| Third public RUL benchmark | `ml/rul_nasa_ims.py`, `data/nasa_ims/`, `tests/test_rul_nasa_ims.py` | Four documented NASA IMS failed bearings; benchmark only, nominal recorded minutes, not field-validated |
| Headline real induction-motor RUL benchmark | `ml/rul_fmcg.py`, `data/fmcg_induction_rul/`, `tests/test_rul_fmcg.py` | Four RUL-to-zero runs from Zenodo DOI `10.5281/zenodo.15637023`, CC BY 4.0; measured 141.716 h MAE, 204.069 h RMSE and 67.7% 24 h warning accuracy; not our motor |
| Simulator removed from cloud path | `edge/stream_live.py`, `tests/test_device_only_telemetry.py` | Retired stub cannot generate or upload packets; only `edge/firebase_mirror.py` writes RTDB |
| Dataset provenance and licences | `docs/DATA_PROVENANCE_LICENSES.md`, `tests/test_rul_xjtu_sy.py` | CC BY 4.0 derived record and US Government Work metadata for NASA IMS; original XJTU-SY, FEMTO-ST, CWRU SPDX names and Reliance catalogue number remain `[NEED: ...]` |
| Real-motor sample | `data/cwru/`, `tests/test_cwru_data.py` | CWRU 2 hp Reliance Electric; seeded faults, no run-to-failure |
| Headline real-motor diagnosis benchmark | `ml/diagnosis_cwru.py`, `ml/diagnosis_cwru_report.json`, `tests/test_diagnosis_cwru.py` | 1.000 (100.0%) on 1,039 CWRU windows, majority baseline 0.4004; sample-disjoint folds; not our motor or deployed taxonomy |
| Real-motor accuracy on our rig, field-validated RUL, cost savings | — | `[NEED: physical run data]` |
| Sensor calibration certificate | `edge/calibrate.py` and runbook | Procedure ready; `[NEED: signed run record]` |

## Offline degradation estimate (not field-validated)

`ml/degradation_rul.py` fits a linear or exponential trend to one condition
indicator from a CSV history and returns the estimated time to a threshold.
The runtime diagnosis, model and dashboard are unchanged. The threshold is a
required argument and must come from the operator; no physical threshold is
bundled with the code.

```
python3 ml/degradation_rul.py \
    --history raw_measurements.csv \
    --time-column unix_time --value-column sound_rms \
    --threshold '<operator value>' [--model exponential]
```

Every result carries `"threshold_source": "operator-supplied"` and a
`"not field-validated"` label. `[NEED: measured degradation curve]` and
`[NEED: run-to-failure series with timestamps and failure labels]` remain
before this can be presented as real RUL.

## Above-80% RUL warning benchmark — C-MAPSS FD001 (not our motor)

The above-80% **RUL** result is a short-horizon warning benchmark on NASA's
public simulated turbofan dataset. It does not relabel the FMCG result below and
does not change the runtime, dashboard telemetry, Firebase state or Pi.

```sh
python3 ml/rul_cmapss_warning.py --report ml/rul_cmapss_warning_report.json
```

The evaluator verifies the three raw file MD5s, trains only on train windows,
labels the warning task from the explicit train regression target
(`true RUL <= 30 cycles`) and reconstructs each withheld test row's RUL from
NASA's last-cycle `RUL_FD001.txt` labels. The 30-cycle horizon is a published
maintenance-planning convention fixed before scoring, not tuned on test data.
It scores one decision per unit at its final recorded cycle and also reports
five unit-disjoint grouped folds where every window of a held-out unit stays
together:

| Metric | Result |
|---|---:|
| Last-cycle warning accuracy | **0.940 (94.0%)** |
| Last-cycle majority baseline | **0.750 (75.0%)** |
| Last-cycle precision / recall / F1 | 0.9524 / 0.800 / 0.8696 |
| Mean grouped unit-disjoint CV accuracy | **0.9705 (97.05%)** |
| Mean grouped CV majority baseline | 0.8248 |

This is `RUL WARNING BENCHMARK / SIMULATED TURBOFAN / NOT OUR MOTOR /
NOT FIELD-VALIDATED`. It is not continuous RUL accuracy, not a measurement from
our induction motor, not an operator-approved alarm threshold and not evidence
that the capstone rig predicts remaining life. The separate FMCG real-motor
result below stays at 67.7% and is reported unchanged.

## Public continuous-RUL benchmark (not our motor)

To validate the RUL pipeline on trusted run-to-failure data, use NASA C-MAPSS
FD001. The three raw text files are vendored in `data/cmapss/` with their MD5
hashes and provenance in `data/cmapss/README.md`. Source: NASA PCoE,
DOI `10.5281/zenodo.15346912`, CC BY 4.0.

```
python3 ml/train_rul_cmapss.py --report /tmp/rul_cmapss_report.json
```

The script trains a 30-cycle-window Random Forest with a 125-cycle RUL cap,
holds out units 81–100 by unit for validation, and scores the final model on
NASA's withheld `RUL_FD001.txt` labels. Reproduced values: validation
last-window RMSE **2.25** cycles; official test RMSE **15.51** cycles and MAE
**11.51** cycles, versus **43.39** for a constant baseline. Full details and
the citation are in `ml/ai_report.md` §10.

This is a **public simulated turbofan benchmark only**: it does not use our
sensors, our motor or our failure modes, and must not be reported as remaining
useful life of the capstone rig. The classifier, dashboard and Firebase state
are untouched. `[NEED: run-to-failure series with timestamps and failure
labels from our rig]` before any field-validated RUL claim.

## Real bearing RUL benchmark (not our motor)

To check RUL on genuine run-to-failure trajectories, use the six learning
bearings from IEEE PHM 2012 PRONOSTIA/FEMTO-ST. The 8,384 unmodified CSV
recordings are vendored in `data/pronostia/` with an MD5 manifest. Sources:
NASA PHM mirror (`https://phm-datasets.s3.amazonaws.com/NASA/10.+FEMTO+Bearing.zip`,
outer archive MD5 `0feedeab9584a68199f1f72fe45e3d19`) and a public CC BY 4.0
copy at figshare DOI `10.6084/m9.figshare.30595484.v1`. The FEMTO-ST pages do
not state an explicit reuse licence: `[NEED: explicit FEMTO-ST dataset licence]`.

```
python3 ml/rul_pronostia.py --report /tmp/rul_pronostia_report.json
```

The script builds 15 causal features from trailing vibration windows (RMS,
kurtosis, peak, crest factor) plus the latest temperature reading, labels each
window as seconds to the final vibration burst, and validates by leaving one
whole bearing out at a time. It uses the published 10 s vibration / 60 s
temperature cadence because two wall-clock resets in `Bearing1_1` are counted
but not silently repaired. Measured results in `ml/rul_pronostia_report.json`:

| Metric | Result |
|---|---:|
| Last-window MAE (six held-out bearings) | **182.91 s** |
| Last-window RMSE (six held-out bearings) | **335.26 s** |
| All-window MAE (7,480 windows) | 6656.68 s |
| All-window RMSE (7,480 windows) | 9557.01 s |
| Constant-baseline last-window RMSE | 8902.25 s |

The last-window error is far below the constant baseline, so the model tracks
late-life degradation on these bearings. The all-window error is large, which
is reported honestly rather than hidden. This remains a **public real-bearing
benchmark only**: PRONOSTIA used a 250 W motor/gearbox, not our induction rig;
no result here is a remaining-life estimate for our motor. Field RUL still
requires `[NEED: run-to-failure series with timestamps and failure labels from
our rig]`. Full write-up: `ml/ai_report.md` §11.

## Second real-bearing RUL benchmark — XJTU-SY (not our motor)

The user asked for a different trusted public run-to-failure dataset. The
XJTU-SY collection has 15 complete bearing runs; the benchmark uses the
CC BY 4.0 Mendeley derived feature record DOI `10.17632/mpn45f4gxc.1`, whose
15 `.mat` file hashes were checked against the Mendeley API. The vendored
`data/xjtu_sy_mendeley/csv/` files hold 9,216 one-minute snapshots. The
original XJTU-SY page requests citation but states no reuse licence:
`[NEED: explicit XJTU-SY reuse licence]`. Full evidence for XJTU-SY, FEMTO-ST,
CWRU and the Reliance motor is in `docs/DATA_PROVENANCE_LICENSES.md`.

```
python3 ml/rul_xjtu_sy.py --report /tmp/rul_xjtu_sy_report.json
```

The script uses three causal horizontal time-domain features, extrapolates the
trailing 40-snapshot log-health trend to the 75th-percentile terminal health
of the other bearings, and validates by leaving one whole bearing out. It
scores the last 20% of each held bearing (1,861 windows):

| Metric | Result |
|---|---:|
| Tail-window MAE | **134.924 min** |
| Tail-window RMSE | **171.776 min** |
| Constant-baseline tail-window RMSE | 160.859 min |

The trend model's RMSE is **worse** than the constant baseline here; that is
reported as measured, not hidden. All values are public bearing minutes, never
hours-to-failure for our motor. The hosted dashboard shows them only under
`BENCHMARK / NOT OUR MOTOR / NOT FIELD-VALIDATED`. Dataset-defined run ends are
**not** operator confirmation of a failure on our rig. No temperature or
acoustic channel exists in this record, so it cannot validate those sensors.

## Third public RUL benchmark — NASA IMS (not our motor)

A third source was added after the licence/public-use review: the University of
Cincinnati IMS / Rexnord run-to-failure tests hosted by
[NASA Open Data](https://data.nasa.gov/dataset/ims-bearings). The published
[IMS.zip](https://data.nasa.gov/docs/legacy/IMS.zip) has SHA-256
`6cb42c263b0281c725abf99f4b9fcf49915c949f31dbd2333877dc2e06ce9ec2`; its portal
metadata names US Government Work while displaying `other-license-specified`, so
both facts are quoted in `docs/DATA_PROVENANCE_LICENSES.md`.

`data/nasa_ims/failed_bearings.csv` contains 11,620 one-second, 20 kHz
snapshots for the four failures documented in the archive README: set 1 bearing
3 (inner race), set 1 bearing 4 (rolling element), set 2 bearing 1 (outer race)
and set 3 bearing 3 (outer race). Reproduce it with
`ml/nasa_ims_features.py`, which streams RAR members with the already-installed
`unrar` tool and does not need a new dependency or a multi-gigabyte extraction.

The benchmark normalises mean log RMS by each bearing's first 10% of snapshots,
fits the trailing 40-snapshot trend, extrapolates to the 75th-percentile
terminal health of the other bearings, and scores the last 20% of each held
bearing under leave-one-bearing-out validation (2,328 windows):

| Metric | Result |
|---|---:|
| Tail-window MAE | **9165.28 min** |
| Tail-window RMSE | **12531.9 min** |
| Constant-baseline tail-window MAE | 17011.8 min |
| Constant-baseline tail-window RMSE | 17382.2 min |

Both scores are reported as measured; the trend model was not tuned to beat the
constant baseline. The minutes are nominal recorded cadence (5 minutes for the
first 43 set-1 snapshots, then 10), **not wall-clock operating hours**, and the
endpoint is the last published snapshot, not operator sign-off on our rig.
This result is `BENCHMARK / NOT OUR MOTOR / NOT FIELD-VALIDATED` and does not
change the runtime classifier, dashboard readings, Firebase state or Pi files.

## Headline real-motor diagnosis benchmark — CWRU (not our motor)

The real-motor result above 80% is a **diagnosis** benchmark, not an RUL claim.
It uses unmodified drive-end vibration recordings from CWRU's 2 hp Reliance
Electric induction motor (0 hp, approximately 1797 rpm, 12,000 samples/s). Four
hash-verified files give four explicit condition labels: healthy, inner-race
fault, rolling-element fault and outer-race fault (0.007 inch seeded faults).
The 1 hp / 2 hp / 3 hp healthy files are excluded so all four classes share the
same operating point.

```sh
python3 ml/diagnosis_cwru.py --report ml/diagnosis_cwru_report.json
```

The evaluator takes 1,024-sample windows with a 512-sample hop **inside**
4,096-sample contiguous blocks. Folds hold out whole blocks from every file, so
windows from different folds never share a vibration sample; the scaler and
200-tree Random Forest are fitted on training folds only. Each window has 16
time- and frequency-domain features. The held-out result over 150 blocks and
1,039 windows is:

| Metric | Result |
|---|---:|
| Four-class accuracy | **1.000 (100.0%)** |
| Majority-class baseline accuracy | **0.4004 (40.04%)** |
| Macro precision / recall / F1 | 1.000 / 1.000 / 1.000 |
| Per-class recall | 1.000 for all four classes |
| Per-fold accuracy | 1.000 in all five folds |

This is a perfect score on a small, controlled public sample with seeded
faults; it is **not** evidence of 100% accuracy on our rig, in the field, or on
the deployed runtime classes (healthy / imbalance / bearing defect / thermal
runaway). It is `BENCHMARK / NOT OUR MOTOR / NOT FIELD-VALIDATED`. To run the
same evaluator on another motor later, pass a JSON class manifest with
`--data-dir` and `--manifest`; no runtime, dashboard or Firebase file changes.
The exact CWRU reuse licence and Reliance catalogue number remain
`[NEED: explicit CWRU licence; exact catalogue number]`. A report produced from
`--manifest` is labelled `OPERATOR-SUPPLIED / PROVENANCE UNVERIFIED /
NOT FIELD-VALIDATED` and does not inherit CWRU source metadata.

## Headline public RUL benchmark — FMCG induction motor (not our motor)

The headline RUL evidence was changed from a synthetic score to a real
three-phase induction-motor dataset: Zenodo DOI
`10.5281/zenodo.15637023` (CC BY 4.0), companion paper DOI
`10.35784/acs_7299`. The paper defines RUL as the hours a motor runs from
startup to shutdown or retirement, derived from SAP Plant Maintenance history
combined with accelerometer readings. `data/fmcg_induction_rul/raw.csv` is the
hash-matched source CSV; `manifest.json` records the source, hashes, selected
runs and exclusions.

```sh
python3 ml/rul_fmcg.py --report ml/rul_fmcg_report.json
```

The evaluator keeps four contiguous, time-ordered blocks whose RUL label
descends to zero (582 / 312 / 552 / 193 rows) and excludes blocks that never
reach zero instead of relabelling them. It builds causal trailing 5-row mean
and standard-deviation features, imputes from training runs only, holds out one
whole run at a time and scores the last 20% of that run (334 tail rows):

| Metric | Result |
|---|---:|
| RUL MAE | **141.716 h** |
| RUL RMSE | **204.069 h** |
| 24-hour warning accuracy | **0.677 (67.7%)** |
| 24-hour warning precision / recall / F1 | 0.333 / 0.029 / 0.053 |
| Constant-zero baseline MAE / RMSE | 69.185 h / 106.164 h |
| Constant-median baseline MAE / RMSE | 254.993 h / 263.054 h |
| Constant-no-warning baseline accuracy | 0.686 |

The model is **worse** than the zero regression baseline and the no-warning
accuracy baseline on this split. Those are the measured numbers; the 24-hour
value is a benchmark bin, not an operator-approved alarm threshold. This is a
public industrial motor benchmark, not the capstone rig, not field validation
and not a change to the deployed classifier, dashboard, Firebase state or Pi.

## Target-rig readiness (not field-validated)

`ml/rul_from_rig.py` is the last offline code path. It accepts the same nine
features used by the deployed Stage-2 classifier, requires operator-labelled
`failure_timestamp` values from our rig, builds causal 10-row trailing windows,
evaluates by leaving one whole run out, and can fit/save a model for a current
run. It does not touch the classifier, dashboard, Firebase or the Pi.

```
python3 ml/rul_from_rig.py --history /path/to/rig_runs.csv \
  --report /tmp/rul_from_rig_report.json \
  --model-out /tmp/rul_from_rig_model.joblib

python3 ml/rul_from_rig.py --mode predict --history /path/to/current_run.csv \
  --model /tmp/rul_from_rig_model.joblib
```

The CSV contract, validation rules, tests and acceptance gate are in
`docs/REAL_MOTOR_READINESS.md`. Tests use generated fixtures only; they prove
the code path, not a measured life for our motor. Remaining evidence:
`[NEED: run-to-failure series with timestamps and failure labels from our rig]`
and `[NEED: operator-accepted failure endpoint and reviewed metric report]`.

## Budget

Signed ceiling **9,370 EGP**; planned **9,368.25 EGP** from 2026-10-25 quotes.
The MAX6675 remains a 200 EGP allowance that must be quoted at or below
201.75 EGP. Cloud cost is 0 EGP. Decision record:
`circuit/BOM_reconciliation.md`.

## Circuit package

`circuit/design.py` is the single source of truth. Rebuild all sheets, netlist,
Fritzing sketch and checks with `python3 circuit/build.py`. Generated outputs
live in `circuit/out/` and are described in `docs/FILE_MAP.md`. The build fails
on ERC errors; the remaining WARNs are documented design constraints, not
hidden failures.

## Repository conventions

- Edit sources, never generated `circuit/out/` files directly.
- Keep model and gate behavior unchanged unless a test and evidence are updated.
- Do not commit secrets, local `.firebase/` cache, calibration backups or logs.
- No WhatsApp contact or chat state changes are part of this repository workflow.
