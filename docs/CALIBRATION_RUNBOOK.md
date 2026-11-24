# Sensor calibration runbook — Raspberry Pi only

`edge/calibrate.py` is an **operator-run script on the Raspberry Pi**. It is not
a systemd service, not a dashboard button and not a laptop tool. Run it while
the motor is stopped and the DAQ service is down.

## 1. What the script changes

The runtime model in `edge/edge_daq.py` is:

```
acceleration_axis = raw_axis * g_scale - g_bias_axis
temperature_c     = raw_temperature_c * t_a + t_b
```

The script fits exactly those five numbers and writes them to `edge/cal.json`.
It uses one shared ADXL345 scale because the runtime applies one `g_scale` to
all three axes. It never changes the model, gate thresholds or dashboard code.

## 2. Prerequisites

- SSH access to the Pi and repository at `/home/renad/pdm` (adjust if yours differs).
- Motor stopped, rig stationary, sensors mounted as in `circuit/out/wiring_a3.svg`.
- I2C and SPI enabled; ADXL345 at `0x53`, MAX6675 on SPI0 CE0.
- Ice slush from distilled water, boiling distilled water, and a reference
  thermometer. `[NEED: thermometer ID, calibration date and uncertainty]`.
- `[NEED: measured local boiling temperature or site pressure]`. Existing docs
  use 97.5 °C as a default; the script asks you to confirm or replace it.
- A level surface and a stable, printed operator sheet for photos/sign-off.

## 2a. Raw measurement mode (not a calibration)

If you need the sensor outputs themselves, use `edge/raw_measure.py`. It reads
the same I2C/SPI buses but applies **no** `cal.json` coefficients and writes no
calibration state:

```bash
sudo systemctl stop pdm-daq.service
python3 edge/raw_measure.py
python3 edge/raw_measure.py --csv edge/raw_measurements.csv --count 20
sudo systemctl start pdm-daq.service
```

Each line shows ADXL345 X/Y/Z in raw LSB counts and the MAX6675 16-bit word,
ADC counts, open-thermocouple flag and datasheet temperature. The datasheet
temperature is marked `UNCALIBRATED`; it is not a reference thermometer reading.
Use the raw counts as observations for `--manual` if you recorded them yourself.

## 3. Exact run procedure

```bash
ssh renad@<pi-address>
cd ~/pdm
sudo systemctl stop pdm-daq.service
python3 edge/calibrate.py
sudo systemctl start pdm-daq.service
```

The script prompts in this order:

1. **Operator name** — stored in the run record.
2. **Six ADXL345 faces** — for each face, orient it pointing up on the level
   surface and press ENTER. It samples 100 raw XYZ readings at 20 Hz and averages them.

   | Prompt | Expected static acceleration |
   |---|---|
   | `+X pointing up` | X = +1 g, Y = 0, Z = 0 |
   | `-X pointing up` | X = -1 g, Y = 0, Z = 0 |
   | `+Y pointing up` | X = 0, Y = +1 g, Z = 0 |
   | `-Y pointing up` | X = 0, Y = -1 g, Z = 0 |
   | `+Z pointing up` | X = 0, Y = 0, Z = +1 g |
   | `-Z pointing up` | X = 0, Y = 0, Z = -1 g |

3. **MAX6675 ice point** — place the probe in crushed ice/distilled water.
   Press ENTER, then 12 readings are averaged at 4 Hz.
4. **MAX6675 boiling point** — place the probe in boiling distilled water.
   Press ENTER, then 12 readings are averaged at 4 Hz.
5. **Reference boiling temperature** — accept the 97.5 °C default only if it
   is your verified site value; otherwise type the measured value.
6. **Optional third thermal check** — answer `y` and enter a raw reading and an
   independently known reference temperature. This is the only check that can
   show error away from the two fit points.

If a hardware read fails, a face pair is reversed, a value is non-finite or the
fitted scale is outside the supported range, the script stops and writes no new
`cal.json`.

## 4. Useful options

```bash
python3 edge/calibrate.py --samples 200          # more ADXL readings per face
python3 edge/calibrate.py --thermal-samples 20   # more MAX6675 readings per point
python3 edge/calibrate.py --reference-boil 97.2  # measured site boiling point
python3 edge/calibrate.py --skip-temp            # only refit the accelerometer
python3 edge/calibrate.py --no-write             # preview the certificate only
python3 edge/calibrate.py --manual               # enter previously recorded averages
```

`--manual` is for re-entering recorded averages or a rehearsal. It does not
read hardware and must not be presented as a fresh physical calibration.

## 5. Outputs and what they mean

| Output | Meaning |
|---|---|
| `edge/calibration_backups/cal-<UTC>.json` | Exact previous `cal.json`, copied before any write |
| `edge/cal.json` | New runtime calibration, written atomically |
| `edge/calibration_certificate.md` | Human-readable run record with verdict and missing evidence |
| `edge/calibration_runs.jsonl` | Append-only operational log, one JSON object per run |

Possible verdicts:

- `UNVERIFIED` — no new measurements captured; nothing should be trusted.
- `REVIEW` — measurements captured. It still requires operator sign-off,
  reference-instrument evidence and physical validation.
- `FAILED` — input or hardware was invalid; no `cal.json` was written.

The script never prints `PASS`, `CERTIFIED` or `AUTHORIZED FOR EXHIBITION`.
A two-point thermal fit is exact at its two points by construction; that is not
proof of accuracy elsewhere. `[NEED: signed operator sheet and face/bath photographs]`.

## 6. After the run

```bash
cat edge/calibration_certificate.md
tail -n 1 edge/calibration_runs.jsonl
sudo systemctl status pdm-daq.service
curl -s http://127.0.0.1:5000/api/state | head -c 400
```

Confirm the dashboard's calibration card shows the new coefficients after the
DAQ service reloads `cal.json`. If values are unchanged, check that you edited
the Pi copy under `~/pdm/edge`, not a laptop checkout.

## 7. Troubleshooting

| Symptom | Action |
|---|---|
| `ADXL345 is not connected` | Stop `pdm-daq.service`, check I2C `0x53` and wiring; rerun |
| `MAX6675 is not connected` | Stop `pdm-daq.service`, check SPI0 CE0 and open-TC flag; rerun |
| `+g reading must exceed its -g reading` | The face label/orientation is swapped; repeat that face |
| `g_scale outside supported range` | Check raw units are LSB, not g; repeat six faces |
| Residual above tolerance | Level surface and hold the rig still; repeat all six faces |
| Dashboard still shows old values | Restart `pdm-daq.service`; verify path and `cal.json` timestamp |

## 8. Evidence to attach for grading

- Signed operator sheet with date, operator name and rig ID.
- Photographs of each of the six orientations and both reference baths.
- Reference thermometer ID, calibration date and uncertainty.
- `edge/calibration_certificate.md` and the relevant `calibration_runs.jsonl` line.
- `[NEED: real-motor verification that calibrated features correlate with the monitored condition]`.
