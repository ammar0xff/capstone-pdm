# G12 PDM handover (short)

Written 2026-11-27. Read this first. Details are in `docs/`.

## What the system is
- Sensors on the fan motor: vibration (ADXL345), temperature (MAX6675), microphone (INMP441).
- A Raspberry Pi reads them (about 400 Hz vibration) and runs the DAQ service.
- Stage 1: rules (vibration against a baseline, kurtosis, temperature, sound level). Result: No rule / Warning / Fault.
- Stage 2: Random Forest, runs only when Stage 1 flags something.
- Dashboards: live on the Pi (port 5000), recorded-data replay on the Pi (port 5002), hosted page on Firebase.

## How to run
- Pi services: `pdm-daq`, `pdm-cloud`, `pdm-dashboard`, `pdm-replay`, `pdm-replay-dashboard`. Check with `systemctl is-active <name>`. All start at boot.
- Open the dashboard through Tailscale: `http://<pi-tailscale-ip>:5000` (live) and `:5002` (replay). The commissioning button works only from Tailscale or the device.
- Presentation mode: press the "Presentation" button or add `?present=1`. On replay data it hides alert-style banners and shows a small data-source footer and a model card. On live sensor data it hides nothing.
- Tests: `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m unittest discover -s tests -v`.
- Rollback scripts are in `~/stat_stage/` on the Pi (one per deployed change, for example `g34_rollback.sh`).
- Nothing in this work was pushed to GitHub. All commits are local on branch `feat/commissioning-baseline`.

## What is real and what is a benchmark
| Item | Status |
|---|---|
| Live sensor readings | Real, from our Pi. While the motor ran they were noisy (see below). |
| Replay on port 5002 | PRONOSTIA public bearing recordings, replayed as a stand-in. Not our motor. |
| Stage 2 model deployed on the Pi | Trained on generated data. Not validated on our motor. |
| KAIST candidate model (offline) | Trained on public KAIST rig data at the Pi's 400 Hz band. Held-out public recordings: 74-81% balanced accuracy (see `docs/` and the results file). Not deployed. |
| Remaining life card | Pooled model on 25 public run-to-failure bearings (XJTU-SY, NASA IMS, PRONOSTIA). Error in the last 20% of life 0.29 vs 0.40 for a constant guess. 19 of 25 bearings warned in time. Not validated on our fan. Gives a percent range, not hours. |
| Speech filter | Only stops the loud-sound Warning while speech is detected. Tested on 3 recordings. Music or TV also count as speech. |
| Demo mode / display caps | Display only, labeled on screen. The raw reading stays visible. |

## Known problems (not fixed)
- The motor is reported broken. Do not treat any recording from it as healthy or normal. Do not commission a baseline from it.
- When the motor started, the Pi rebooted once and temperature jumped between 62 and 312 C (real value about 50 C). Sampling fell to 5-55 Hz. This looks like electrical noise (power, ground, wiring). Fix the wiring or power first.
- No temperature history exists (CSV recording is off).
- The DAQ has no filter for bad temperature reads. Only the display layer caps them.

## How to commission after the motor is fixed
Only start when all of these hold on the dashboard: temperature steady and believable, vibration sampling near 390-400 Hz, no Pi reboot since the motor started, no spikes, and a person confirms the motor runs normally.
1. Run the motor at its normal operating condition for a few minutes first.
2. Open the live dashboard (port 5000) over Tailscale. Confirm there is no "Sensor unreliable" banner.
3. Press "Start commissioning (10 min)" and confirm. Keep the motor at the same load for the whole 10 minutes.
4. Wait for "accepted". If it is refused, the reason is shown (too few windows, drift, outliers, noise floor, or mean above the limit). Fix that and repeat.
5. The baseline is saved on the Pi and loaded at restart. "Reset to default" returns to the fixed defaults and keeps the old file under a dated name.
6. The remaining life card starts only after a commissioned baseline exists and 40 valid samples were collected. Its number is a trend range, not a promise.
The baseline is whatever the sensor saw while the operator said "normal". The dashboard says the motor state is not verified.

## Do not
- Do not claim accuracy, remaining life or "healthy motor" for our fan from benchmark results.
- Do not change the 0.04 g kurtosis rule or the vibration gate without tests and a new review.
- Do not merge public and own data under one dataset name. Name both sources on any model card.
