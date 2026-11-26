# Commissioning baseline for the SPC gate (G28)

Status: written and tested off the Pi. NOT deployed. Deploying needs the user's go-ahead after the test results are shown.

## What it is
The Stage-1 SPC gate compares `rms_dyn` (vibration, in g) with a baseline mean `mu` and spread `sigma`. Today these are fixed: mu 0.080 g, sigma 0.025 g. The live rig reads about 0.007 to 0.08 g depending on the day, so the fixed numbers do not describe this rig.

Commissioning lets the device learn its own `mu` and `sigma` (SPC Phase I). The operator starts a 10 minute run while the machine is running normally. The device collects one `rms_dyn` window about every 0.7 s (non-overlapping windows), then computes the baseline itself.

## What it does not do
- It does not know whether the motor is running or healthy. The baseline is whatever the accelerometer saw while the operator said "healthy". Every result carries `motor_running_verified: false`, and the dashboard says so.
- It does not change the 0.04 g kurtosis condition, the 0.25/0.40 g peak limits, the thermal or sound limits, or the AI model.
- It does not push anything to GitHub or Firebase settings. The new fields (`commissioning`, `spc.baseline_source`) travel in the normal telemetry packet.

## Behaviour
- Until a run is accepted, the defaults stay active ("fallback"). During a run the defaults also stay active.
- When a run is accepted: `mu`/`sigma` replace the defaults in the edge gate and in the RF stage-1 gate (`classifier.spc_baseline_rms` / `spc_sigma_rms`). Warning = mu + 2 sigma, fault = mu + 3 sigma, as before.
- The accepted baseline is saved once to `edge/commissioned_baseline.json` (on the SD card, written atomically, one write per run). It is loaded on restart. A corrupt or out-of-range file is ignored and the defaults are used.
- Reset goes back to the defaults. The old file is renamed `commissioned_baseline.json.reset-<unix time>`, not deleted.

## Acceptance rules (a run is refused, default kept, reason shown)
| Rule | Value |
|---|---|
| Run length | 600 s |
| Minimum windows | 200 |
| Valid windows (finite inputs, fresh accelerometer) | at least 90% |
| Outliers (median +/- 4 robust sd) | at most 10% of windows |
| Drift between first and second half of the run | refused if larger than 0.5 sd and 10% of the mean |
| Mean rms below 0.003 g | refused (sensor noise floor, no usable signal) |
| Mean rms above 0.155 g (default fault limit) | refused |
| Sigma floor | max(measured, 5% of mu, 0.0005 g), so the gate never has zero width |

## Dashboard
The Pi's own dashboard (port 5000) shows: baseline source (default or commissioned), mu and sigma, the live warning/fault limits, run progress, and two buttons: Start/Cancel commissioning and Reset to default. Each asks for confirmation. The hosted Firebase page does not get a button: the Pi only pushes data to Firebase and has no inbound channel from it, and opening one would need write access to the database from the public page.

Command path: `POST /api/commissioning {"cmd": "start|cancel|reset", "confirm": true}` writes a small command file on the Pi (`/dev/shm/pdm/commission_cmd.json`). The DAQ service reads it about once a second and deletes it. The endpoint cannot set thresholds. It answers 403 to addresses outside loopback, Tailscale (100.64.0.0/10) and private LAN ranges (override with `G12_COMMISSION_ALLOW`), and 400 to anything that is not JSON with `confirm: true`. The dashboard has no login, so anyone on the same LAN or tailnet can start a run. Decision for the user: keep as is, or allow only loopback and Tailscale.

## Audio reference (separate, recording-based, not live rig)
Mic recordings of Nov 25 on the Pi (`/home/renad/g12_capture/audio_dataset/`), 48 kHz, channel 0 only. These are NOT vibration and NOT an SPC baseline. Values are fractions of full scale (FS):
- Motor running, everyone silent (user statement 23:13): overall RMS 0.0188; per-second RMS median 0.0083; 96% of energy below 20 Hz; lines near 100 and 200 Hz.
- Motor running plus normal speech (user-reported): overall RMS 0.0287; per-second median 0.0221; energy at 500 Hz to 2 kHz.
- Motor off (first take, corrected label): overall RMS 0.0169; per-second median 0.0050.
Motor-only is only about 1.7x the motor-off ambient, so the mic barely separates motor from no motor. Speech separates clearly.

## Tests
`tests/test_commissioning.py` (logic, 18 tests), `tests/test_commissioning_dashboard.py` (endpoint, needs Flask), `tests/test_commissioning_integration.py` (runs the real `edge_daq.main()` with fake hardware and drives start, accept, reset and a bad command file through the command file). Run: `python3 -m unittest discover -s tests -p "test_commissioning*.py"`.

## Deploy and rollback
Files: `edge/commissioning.py` (new), `edge/edge_daq.py`, `edge/dashboard.py`, `edge/templates/index.html`. Based on the Pi's files of Nov 26 (edge_daq.py md5 bc13bc7c, which is newer than the copy in `pi_deployed/live/`). `pi_deployed/rollback_scripts/g28_apply.sh` refuses to run if the Pi files differ from that base, backs up first, restarts only `pdm-daq` and `pdm-dashboard`. `g28_rollback.sh` restores the backup and removes `commissioning.py`.
