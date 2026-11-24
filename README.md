# Intelligent Predictive Maintenance & Remote Monitoring — G12 Capstone 2026/27

Raspberry Pi 4 edge condition monitoring for a three-phase induction motor rig.
The system samples vibration, temperature and acoustic sensors, applies a
statistical gate, then runs a four-class Random Forest diagnosis when that gate
is breached. Results are presented on a local Flask dashboard and mirrored to
Firebase Realtime Database. The hosted dashboard is presentation-only.

**Current status:** implementation and synthetic benchmark are complete;
physical-rig validation, field-validated RUL and measured CPU savings are not.
An offline degradation estimator is available as an analysis tool only; it
requires an operator-supplied threshold and is explicitly not field-validated.
See `docs/G12_REQUEST_RESPONSE_REGISTER.md` for request-by-request evidence.

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
- The dashboard shows live state, decisions, charts and links. It has no
  calibration write endpoint and no simulator controls.
- `ml/degradation_rul.py` is an **offline** trend-to-threshold estimator. It is
  not part of the runtime diagnosis, needs an operator threshold, and is
  labelled "not field-validated" in every result.

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
`edge/raw_measure.py`, `edge/exhibition_drill.py`, `edge/stream_live.py` and
`edge/generate_qr.py` are operator-run tools, not daemons.

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
| Real-motor accuracy, field-validated RUL, cost savings | — | `[NEED: physical run data]` |
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
