# Intelligent Industrial Predictive Maintenance (PdM)
## Master Engineering & Implementation Tutorial (Step-by-Step)
**Grade 12 STEM Capstone 2026/2027 | Grand Challenge: Industrial Base of Egypt**  
*Author: Capstone Engineering Team*  
*Target Rig: Raspberry Pi 4 Model B (4 GB RAM, 64-bit Debian Bookworm)*

---

## 1. Executive Summary & Project Purpose

Industrial motors represent over **70% of electrical power consumption** in heavy manufacturing. Catastrophic motor failures (such as bearing race spalling, rotor unbalance, and lubrication starvation) cost the manufacturing sector billions annually in unplanned downtime.

This project implements an **end-to-end Cyber-Physical Predictive Maintenance (PdM) System** that satisfies the Grade 12 STEM Capstone requirements:
1. **Multi-Modal Edge Sensing**: High-rate digital vibration ($400\,\text{Hz}$ via I2C), cold-junction-compensated casing temperature (SPI), and high-frequency acoustic emission (I2S DMA).
2. **Offline-First Two-Stage Edge AI**: Grounded in **Cinar et al. (2022)**, utilizing a coarse **Shewhart Statistical Process Control (SPC)** gate before a **300-Tree Random Forest Classifier**. CPU savings have not been measured on our Pi, so no percentage is claimed (see `docs/G12_REQUEST_RESPONSE_REGISTER.md` §7).
3. **Traceable Sensor Metrology**: Conducts empirical 6-position gravitational tilt calibration ($<0.51\%$ error) and 2-point thermodynamic calibration satisfying rubric criteria (10 pts).
4. **Zero-Cost Cloud Mirror**: Synchronizes real-time machine health states to Firebase Realtime Database (Spark free tier) with Quota Guard and offline queueing.
5. **Interactive Global Web Dashboards**: Global live telemetry mirror, 12-slide exhibition presentation deck, and official metrology calibration certificate.

---

## 2. Hardware Architecture & Pinout Matrix

The physical rig consists of a single-phase induction test motor mounted on rubber dampening isolators with three digital sensor modalities wired directly to the Raspberry Pi 4 GPIO header.

```
+-------------------------------------------------------------------------------+
|                           RASPBERRY PI 4 MODEL B                              |
|                                                                               |
|   3.3V (Pin 1) ------+--------+--------+                                      |
|   GND  (Pin 6) ------+--------+--------+--------+                             |
|                      |        |        |        |                             |
|   I2C SDA (Pin 3) ---+        |        |        |   ADXL345 3-Axis Accel      |
|   I2C SCL (Pin 5) ---+        |        |        |   [I2C Addr: 0x53, 400 Hz]  |
|                               |        |        |                             |
|   SPI0 CE0  (Pin 24) ---------+        |        |   MAX6675 K-Thermocouple    |
|   SPI0 MISO (Pin 21) ---------+        |        |   [SPI Bus 0, 0.25°C Res]   |
|   SPI0 SCLK (Pin 23) ---------+        |        |                             |
|                                        |        |                             |
|   I2S BCLK (Pin 12 / GPIO 18) ---------+        |   INMP441 Acoustic MEMS     |
|   I2S LRCL (Pin 35 / GPIO 19) ---------+        |   [I2S DMA, 16 kHz 24-bit]  |
|   I2S DIN  (Pin 38 / GPIO 20) ---------+        |                             |
|                                                 |                             |
|   GPIO 17  (Pin 11) ----------------------------+   Optocoupled Safety Relay  |
+-------------------------------------------------------------------------------+
```

### Complete Hardware Wiring Pinout Table

| Sensor / Module | Sensor Pin | Raspberry Pi 4 Physical Pin | GPIO / Function | Electrical Protocol | Operating Range / Spec |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **ADXL345** | VCC | Pin 1 | 3.3V Power | DC Power | 3.3V regulated |
| | GND | Pin 6 | Ground | Ground | 0V Reference |
| | SDA | Pin 3 | GPIO 2 (SDA1) | I2C Data | Hardware pull-up ($1.8\,\text{k}\Omega$) |
| | SCL | Pin 5 | GPIO 3 (SCL1) | I2C Clock | $400\,\text{kHz}$ Fast Mode |
| | CS | VCC | 3.3V | I2C Select | High selects I2C mode |
| | SDO | GND | Ground | Address Select | Low sets I2C address to `0x53` |
| **MAX6675** | VCC | Pin 17 | 3.3V Power | DC Power | 3.3V regulated |
| | GND | Pin 9 | Ground | Ground | 0V Reference |
| | SO (MISO) | Pin 21 | GPIO 9 (MISO) | SPI Data Out | Master In Slave Out |
| | SCK | Pin 23 | GPIO 11 (SCLK) | SPI Clock | Master Clock ($4.3\,\text{MHz}$ max) |
| | CS | Pin 24 | GPIO 8 (CE0) | SPI Chip Enable | Active Low Chip Select |
| **INMP441** | VDD | Pin 1 | 3.3V Power | DC Power | 3.3V regulated |
| | GND | Pin 14 | Ground | Ground | 0V Reference |
| | SCK (BCLK) | Pin 12 | GPIO 18 (PCM_CLK) | I2S Bit Clock | Hardware DMA bit clock |
| | WS (LRCL) | Pin 35 | GPIO 19 (PCM_FS) | I2S Word Select | Left/Right frame sync ($16\,\text{kHz}$) |
| | SD | Pin 38 | GPIO 20 (PCM_DIN) | I2S Serial Data | 24-bit audio stream |
| | L/R | GND | Ground | Channel Select | Ground = Left Channel |
| **Safety Relay** | IN | Pin 11 | GPIO 17 | Digital Output | High = Trip / Open Circuit |

---

## 3. Complete File Manifest & Architecture Map

Every file in this repository serves an exact, documented role in the cyber-physical pipeline:

```
intelligent-raman/
├── docs/
│   ├── CAPSTONE_MASTER_HANDBOOK.md  # 25-page comprehensive academic thesis handbook
│   ├── LITERATURE_REFERENCES.md     # Primary source dossier with DOIs and standard mappings
│   ├── SENSOR_CALIBRATION.md        # Official metrology calibration report (10 pts)
│   ├── STUDENT_MASTER_GUIDE.md      # Simplified 15-year-old student conceptual guide
│   └── PROJECT_COMPLETE_TUTORIAL.md # THIS FILE: Complete engineering build tutorial
│
├── edge/
│   ├── edge_daq.py                  # Real-time multi-modal hardware data acquisition daemon
│   ├── calibrate.py                 # Interactive 6-face accelerometer & thermal calibration suite
│   ├── cal.json                     # Active sensor zero-g bias and thermal slope calibration matrix
│   ├── calibration_certificate.md   # Markdown certificate generated from calibration run
│   ├── firebase_mirror.py           # Zero-cost cloud mirror with Quota Guard & offline queue
│   ├── cloud_config.json            # Target Firebase RTDB endpoint and sync rate configuration
│   ├── dashboard.py                 # Lightweight edge web dashboard served on port 8080
│   └── pdm-daq.service              # Systemd unit file for autostarting DAQ on boot
│
├── ml/
│   ├── dataset_generator.py         # Physics-based synthetic dataset generator (Randall & Antoni)
│   ├── windows.csv                  # 1,400 multi-modal feature windows across 4 classes
│   ├── train_rf.py                  # 300-tree Random Forest trainer with 5-fold cross-validation
│   ├── model.joblib                 # Serialized scikit-learn classifier artifact
│   ├── model_meta.json              # Model hyperparameters, decision thresholds, and accuracy
│   ├── rf_predictor.py              # Pure-Python standalone inference script without scikit-learn
│   ├── ai_report.md                 # Complete AI evidence dossier, feature ranking, and ROC report
│   ├── confusion_matrix.png         # Generated 4x4 multi-class confusion matrix plot
│   ├── roc_curves.png               # Receiver Operating Characteristic (ROC-AUC) curves
│   └── feature_importance.png       # Gini impurity feature importance bar chart
│
├── public/
│   ├── index.html                   # Global live telemetry dashboard, device telemetry only
│   ├── guide.html                   # 12-slide interactive exhibition presentation deck (viewport responsive)
│   ├── calibration.html             # Interactive metrology suite, 6-face tilt widget, and printable certificate
│   ├── windows.csv                  # Mirrored dataset accessible for web clients
│   └── favicon.ico                  # Browser tab icon
│
├── firebase.json                    # Firebase Hosting deployment and cache-control configuration
└── .firebaserc                      # Firebase project target binding (castpone2026)
```

---

## 4. First-Principles Physics & Mathematical Formulations

To ensure the system is scientifically rigorous rather than a superficial black-box, all sensor feature extractions and dataset generation follow established physical and kinematic laws:

### 4.1 Rolling Element Bearing Kinematics (Randall & Antoni, 2011)
For an induction motor rotating at $1800\,\text{RPM}$ ($f_r = 30.0\,\text{Hz}$) with standard 6205 ball bearings ($N_b = 9$ balls, ball diameter $d = 7.94\,\text{mm}$, pitch diameter $D = 39.04\,\text{mm}$, contact angle $\alpha = 0^\circ$):

$$\gamma = \frac{d}{D}\cos\alpha \approx \frac{7.94}{39.04} \approx 0.2034$$

* **Ball Pass Frequency Outer Race (BPFO)**:
  $$f_{\text{BPFO}} = \frac{N_b}{2} f_r (1 - \gamma) = \frac{9}{2} \times 30 \times (1 - 0.2034) = \mathbf{107.54\,\text{Hz}}$$
* **Ball Pass Frequency Inner Race (BPFI)**:
  $$f_{\text{BPFI}} = \frac{N_b}{2} f_r (1 + \gamma) = \frac{9}{2} \times 30 \times (1 + 0.2034) = \mathbf{162.46\,\text{Hz}}$$
* **Ball Spin Frequency (BSF)**:
  $$f_{\text{BSF}} = \frac{D}{2d} f_r (1 - \gamma^2) = \frac{39.04}{2 \times 7.94} \times 30 \times (1 - 0.0414) = \mathbf{70.72\,\text{Hz}}$$
* **Fundamental Train Frequency (FTF)**:
  $$f_{\text{FTF}} = \frac{1}{2} f_r (1 - \gamma) = 0.5 \times 30 \times (1 - 0.2034) = \mathbf{11.95\,\text{Hz}}$$

#### Physical Impulse Response Model
When a ball impacts a fatigue spall, it excites structural resonance ($f_{res} \approx 2400\,\text{Hz}$) with viscous damping $\zeta \approx 0.045$:
$$s(t) = \sum_{k} A_k \cdot e^{-\zeta 2\pi f_{res} (t - t_k)} \sin\left(2\pi f_{res} \sqrt{1 - \zeta^2} (t - t_k)\right) \cdot u(t - t_k)$$

This periodic shockwave drastically elevates the 4th central moment (**Kurtosis** $\kappa > 6.0$, up to $15.0$) and **Crest Factor** ($CF = \frac{\text{Peak}}{\text{RMS}} > 4.5$), while overall RMS only increases moderately.

### 4.2 Mechanical Unbalance & Looseness (ISO 10816-3)
Rotor mass eccentricity $e$ creates a centrifugal unbalance force $F = m e \omega^2$, generating sinusoidal acceleration at fundamental shaft speed ($1\times f_r = 30\,\text{Hz}$). Structural looseness and shaft misalignment produce sharp non-linear clipping, generating strong $2\times f_r$ ($60\,\text{Hz}$) and $3\times f_r$ ($90\,\text{Hz}$) harmonics:
$$a(t) = A_1 \sin(2\pi f_r t) + A_2 \sin(4\pi f_r t + \phi_2) + A_3 \sin(6\pi f_r t + \phi_3) + \nu(t)$$

Because sinusoidal signals are smooth, **Kurtosis remains near Gaussian** ($\kappa \approx 3.0 \pm 0.4$) and Crest Factor remains low ($CF \approx 2.0 - 2.8$), but dynamic RMS velocity surges into ISO 10816 Zone C/D ($> 0.15g$).

### 4.3 Thermal Runaway & Lubrication Starvation (Blok / Newton ODE)
When boundary lubrication fails, the friction coefficient $\mu$ spikes by $50\times - 100\times$. Mechanical power dissipated as heat:
$$P_{\text{loss}} = \mu \cdot F_{\text{radial}} \cdot (2\pi r_{\text{shaft}} f_r)$$
The thermal trajectory is governed by a lumped capacitance differential equation:
$$\frac{dT(t)}{dt} = \frac{P_{\text{loss}}}{C_{\text{thermal}}} - \frac{T(t) - T_{\text{ambient}}}{R_{\text{thermal}} C_{\text{thermal}}}$$
This produces a rapid positive temperature rate of change ($\frac{dT}{dt} > 5.0^\circ\text{C/min}$) with casing temperatures exceeding $70^\circ\text{C} - 95^\circ\text{C}$.

### 4.4 Acoustic Emissions (INMP441 MEMS)
* **Sound Pressure Level (SPL)**:
  $$\text{SPL} = 120.0 + 20 \log_{10}(\text{RMS}_{\text{acoustic}}) \quad [\text{dB SPL}]$$
* **Zero-Crossing Rate (ZCR)**:
  $$\text{ZCR} = \frac{1}{2(N-1)} \sum_{n=1}^{N-1} |\text{sgn}(s[n]) - \text{sgn}(s[n-1])|$$
High-frequency friction and micro-impacts shift acoustic spectral energy into multi-kilohertz bands, driving ZCR from nominal ($<0.04$) to $>0.20$.

---

## 5. Machine Learning Pipeline (`ml/`)

### 5.1 Physics-Grounded Dataset Generator (`ml/dataset_generator.py`)
Rather than drawing arbitrary numbers from random distributions, `ml/dataset_generator.py` generates discrete time-domain waveforms $x[n]$ of length $N=1024$ samples at $f_s = 3200\,\text{Hz}$ using the exact kinematic differential equations described above. It then calculates the 9 physical features:

| # | Feature Name | Sensor Modality | Exact Formula | Diagnostic Interpretation |
|---|---|---|---|---|
| 1 | `rms_dyn` | ADXL345 | $\sqrt{\frac{1}{N}\sum (a_i - \bar{a})^2}$ | Total destructive kinetic energy (ISO 10816). |
| 2 | `peak_dyn` | ADXL345 | $\max \|a_i - \bar{a}\|$ | Maximum instantaneous impact shock amplitude. |
| 3 | `crest_factor` | ADXL345 | $\text{peak\_dyn} / \text{rms\_dyn}$ | Ratio of peak shock to continuous energy. |
| 4 | `kurtosis` | ADXL345 | $\frac{1}{N}\sum(a_i - \bar{a})^4 / \sigma^4$ | Statistical spikiness (Gaussian baseline = 3.0; spalls > 6.0). |
| 5 | `temp_c` | MAX6675 | Calibrated thermocouple reading | Absolute casing thermal state. |
| 6 | `temp_slope` | MAX6675 | $\Delta T / \Delta t$ over sliding window | Heat generation rate ($\ge 5^\circ\text{C/min}$ = runaway). |
| 7 | `sound_rms` | INMP441 | $\sqrt{\frac{1}{N}\sum s_i^2}$ | Acoustic pressure wave amplitude. |
| 8 | `sound_db` | INMP441 | $120.0 + 20\log_{10}(\text{sound\_rms})$ | Calibrated Sound Pressure Level ($\text{dB SPL}$). |
| 9 | `sound_zcr` | INMP441 | Sign-change frequency | High-frequency friction squeal vs. low hum. |

### 5.2 Model Training & Group-Disjoint Evaluation (`ml/train_rf.py`)
Trains a 300-estimator Random Forest classifier (`max_depth=12`, `min_samples_split=4`, `class_weight='balanced'`) with 5-fold `StratifiedGroupKFold` cross-validation by `run_id` and a 70/15/15 whole-run hold-out:
- **Mean Group Cross-Validation Accuracy**: $100.00\%$ on the physics-simulated benchmark (not real-motor accuracy)
- **Measured Inference Latency**: $26.19\,\text{ms}$/window on the training host and $29.99\,\text{ms}$/window on the Raspberry Pi 4 (`ml/benchmark_latency.py`, 100 windows); full inject→alert timing still unmeasured
- **Note**: `z_score` is a Stage-1 SPC gate metric derived from `rms_dyn`, not an independent RF feature
- **Exports**: `ml/model.joblib`, `ml/model_meta.json`, `ml/confusion_matrix.png`, `ml/roc_curves.png`, and `ml/feature_importance.png`.
- **Check the evidence**: `.venv/bin/python -m unittest discover -s tests -v` (asserts no run leakage and that metadata matches the code).
- **Reproduce latency**: `.venv/bin/python ml/benchmark_latency.py`; run the same script on the Pi with `--model/--meta/--csv` to compare (see `docs/PI_DEPLOYMENT_EVIDENCE.md`).

---

## 6. Edge Acquisition & System Services (`edge/`)

### 6.1 Real-Time DAQ Daemon (`edge/edge_daq.py`)
1. Reads 6 bytes from ADXL345 via I2C at $400\,\text{Hz}$, subtracts static calibrated $0g$ biases ($b_x, b_y, b_z$), and evaluates sliding window RMS, Peak, Kurtosis, and Crest Factor.
2. Reads 2 bytes from MAX6675 via SPI Bus 0 every 1 second ($0.25^\circ\text{C}$ resolution) and calculates thermal slope $\Delta T / \Delta t$.
3. Reads 24-bit DMA acoustic samples from INMP441 via I2S ALSA capture.
4. **Stage 1 Shewhart SPC Gating**: Computes normalized $Z = \frac{\text{RMS} - \mu_0}{\sigma_0}$ with the configured $\mu_0=0.080\,g$, $\sigma_0=0.025\,g$. The classifier wrapper in `ml/rf_predictor.py` skips `predict_proba` on a nominal window (`rf_executed=False`), but `edge_daq.py:511-520` still calls the wrapper on every 100 ms state update. CPU reduction has **not** been measured; do not quote a percentage.
5. Emits state to local shared memory file `edge/latest_state.json` and circular buffer `edge/pdm_buffer.db`.

### 6.2 Zero-Cost Firebase Cloud Mirror (`edge/firebase_mirror.py`)
1. Reads `edge/latest_state.json` every 5 seconds.
2. Sends an HTTPS `PUT` request to `https://castpone2026-default-rtdb.firebaseio.com/motor1.json`.
3. **Quota Guard**: Tracks writes per day, resetting at midnight, ensuring total daily writes stay below 15,000 (well within Firebase Spark free tier).
4. **Offline Queueing**: If WiFi or internet drops, frames are safely buffered in `edge/cloud_backlog.json` and flushed immediately upon reconnection.

### 6.3 Systemd Service Setup (`edge/pdm-daq.service`)
To ensure automatic launch on boot and continuous recovery from crashes:

```ini
[Unit]
Description=Predictive Maintenance Edge DAQ & SPC Engine
After=network.target

[Service]
Type=simple
User=renad
WorkingDirectory=/home/renad/pdm/edge
ExecStart=/usr/bin/python3 /home/renad/pdm/edge/edge_daq.py
Restart=always
RestartSec=3
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

This is the exact content of `edge/pdm-daq.service`. Only files named in `ExecStart=` of an
enabled unit start automatically; uploading another `.py` file does not run it.

Enable and start on the Raspberry Pi:
```bash
sudo cp edge/pdm-daq.service /etc/systemd/system/pdm-daq.service
sudo systemctl daemon-reload
sudo systemctl enable pdm-daq.service
sudo systemctl start pdm-daq.service
```

---

## 7. Frontend Web Architecture (`public/`)

### 7.1 Telemetry Dashboard (`public/index.html`)
* **Live Server-Sent Events (SSE) & Fallback Polling**: Subscribes to `https://castpone2026-default-rtdb.firebaseio.com/motor1.json`.
* **Hardware Connection Health Classifier**:
  Computes telemetry age: $\Delta t_{\text{age}} = t_{\text{now}} - t_{\text{packet}}$.
  - $\Delta t_{\text{age}} \le 20\,\text{s}$: 🟢 **Pi Online & Streaming** (Green beacon).
  - $20\,\text{s} < \Delta t_{\text{age}} \le 90\,\text{s}$: 🟡 **Pi Stale** (Amber warning).
  - $\Delta t_{\text{age}} > 90\,\text{s}$ or network error: 🔴 **Pi Disconnected / Offline** (Red alert badge and persistent banner).
* **Decision data**: The edge packet still carries `ai.response_plan` (priority, action, timeframe, owner), but the hosted dashboard no longer displays that block. The dashboard displays real telemetry only; simulator controls and synthetic scenario buttons have been removed.
* **Anti-Drift Chart Protection**: Freezes timeline history pushes when the Pi is offline to prevent false duplicate points.

### 7.2 STEM Exhibition Presentation Deck (`public/guide.html`)
A 12-slide responsive slide deck formatted for laptop, projector, and mobile screens without vertical scrollbars:
- Slide 1: Title & Exhibition Overview
- Slide 2: Grand Challenge & Egyptian Industrial Problem
- Slide 3: System Architecture & Cyber-Physical Pipeline
- Slide 4: Multi-Modal Edge Hardware & Pinout
- Slide 5: Sensor Calibration & Metrology (Rubric Highlight)
- Slide 6: Two-Stage Monitoring Architecture (Cinar et al. 2022)
- Slide 7: Physics-Grounded Synthetic Dataset Generation
- Slide 8: Machine Learning Training & Evaluation
- Slide 9: Edge Acquisition, DAQ & System Services
- Slide 10: Zero-Cost Firebase Cloud Mirroring
- Slide 11: Real-Time Web Telemetry & Offline Detection
- Slide 12: Cost Analysis, Conclusion & Future Roadmap

### 7.3 Calibration & Metrology Suite (`public/calibration.html`)
- Interactive 6-face static tilt visualizer ($+Z, -Z, +X, -X, +Y, -Y$).
- 2-point thermodynamic reference data table.
- Printable ISO 17025 style Certificate of Calibration with digital signature blocks.

---

## 8. Step-by-Step Reproduction Guide (From Zero to Working Rig)

### Step 1: Clone Repository & Set Up Virtual Environment
```bash
git clone https://github.com/ammar0xf/intelligent-raman.git
cd intelligent-raman
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**On the Raspberry Pi** the systemd units in `edge/*.service` currently run `/usr/bin/python3`
from `/home/renad/pdm/edge`. Install the same dependencies there before starting the services:

```bash
# On the Pi, as the user named in the service files (currently renad):
cd ~/pdm                      # must match WorkingDirectory=.../pdm/edge
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# If the services must use this venv, update ExecStart= in edge/*.service
# from /usr/bin/python3 to /home/renad/pdm/.venv/bin/python, then daemon-reload.
```

Verify the Pi user and deployment path before enabling any unit:
```bash
whoami                        # must equal User= in edge/*.service
ls -d ~/pdm/edge              # must equal WorkingDirectory= in edge/*.service
```

### Step 2: Generate Physics Dataset & Train AI Model
```bash
python3 ml/dataset_generator.py
python3 ml/train_rf.py
```

### Step 3: Calibrate Physical Sensors on the Raspberry Pi
`edge/calibrate.py` runs on the Pi, not on the laptop, and is not a systemd
service. Stop the DAQ so the I2C/SPI buses are free:

```bash
ssh renad@<pi-address>
cd ~/pdm
sudo systemctl stop pdm-daq.service
python3 edge/calibrate.py
sudo systemctl start pdm-daq.service
```

The script asks for the operator, samples six ADXL345 faces (100 readings each)
and two MAX6675 reference points (12 readings each), offers a third thermal
check, backs up `edge/cal.json`, writes it atomically, and creates
`edge/calibration_certificate.md` plus `edge/calibration_runs.jsonl`. The
verdict is `REVIEW` or `UNVERIFIED` — it never issues a fake PASS. See
`docs/CALIBRATION_RUNBOOK.md` for the full guided procedure.

### Step 4: Configure Firebase Realtime Database
1. Go to [Firebase Console](https://console.firebase.google.com/) and create project `castpone2026`.
2. Create a Realtime Database in `us-central1` or default region.
3. The deployed project currently uses public read/write rules for exhibition telemetry:
```json
{
  "rules": {
    ".read": true,
    ".write": true
  }
}
```
   **Security warning:** anyone with the URL can read or overwrite `motor1`.
   No auth change was made in this cleanup because it changes client behavior.
   See `docs/FIREBASE_SETUP.md` for the least-privilege migration plan.
4. Verify the database URL matches `https://castpone2026-default-rtdb.firebaseio.com/motor1.json`.

### Step 5: Start Edge Daemons as Systemd Services
Confirm `User=`, `WorkingDirectory=` and `ExecStart=` in each unit match the real Pi deployment
(user `renad`, path `~/pdm/edge` at the time of writing) before copying them:

```bash
for s in pdm-daq pdm-cloud pdm-dashboard; do
  sudo cp "edge/$s.service" "/etc/systemd/system/$s.service"
done
sudo systemctl daemon-reload
sudo systemctl enable --now pdm-daq.service pdm-cloud.service pdm-dashboard.service
sudo systemctl status pdm-daq.service pdm-cloud.service pdm-dashboard.service
```

### Step 6: Deploy Frontend to Firebase Hosting
```bash
firebase login
firebase use castpone2026
firebase deploy --only hosting
```

Your live dashboards are now active at:
- **Global Dashboard**: `https://castpone2026.web.app/`
- **Exhibition Deck**: `https://castpone2026.web.app/guide.html`
- **Calibration Suite**: `https://castpone2026.web.app/calibration.html`
