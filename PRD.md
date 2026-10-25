# PRD — AI-Driven Edge Predictive Maintenance & Remote Monitoring System
**Grade 12 Capstone 2026/2027 S1 | Theme: Communication, Sensing, Information, Informatics**

- **Date:** 2026-10-14
- **Version:** v2.0 (updated: Firebase + Grafana + Custom Panel, 0-EGP cloud)
- **Source folder:** `/home/ammar/Desktop/pro/`
- **Status:** Approved for build
- **Hard budget cap:** **8240 EGP all-in, not more** (per `DOC-20261014-WA0055.xlsx`)
- **Cloud budget:** **0 EGP** — no paid provider allowed. Free-tier only + offline-first.

## 0. Problem, Solution, Features, Grade Calculation (read first)

### 0.1 Problem
Egyptian lines stop on surprise motor failures. Reactive (fix after break) costs $50B/yr downtime; preventive (fix on schedule) wastes healthy parts. Small factories have no vibration/heat/sound logging, no wireless to cloud, no AI early warning. Capstone demands a solution with sensing + wireless to cloud + AI + hardware + ≥80% accuracy + calibration + portable testable prototype ≤8240 EGP, no Arduino.
**Problem statement:** How can AI+IoT on low-cost edge detect incipient faults and warn in ≤5s with evidence and zero cloud spend?

### 0.2 Solution
Portable offline-first rig on Pi 4 8GB: ADXL345 + K-type/MAX6675 + INMP441 → cal → SPC coarse → RF fine → Healthy/Warning/Fault on **both** Flask Custom Panel (live/QR/mobile) and Grafana (analytics/KPIs), Firebase Spark mirror at 0 EGP for grading. Full workflow runs with zero internet (hotspot + SD buffer); cloud backfills on reconnect.

### 0.3 Features
| # | Feature | Demo | Maps to |
|---|---|---|---|
|F1|3-modality sensing|live g/°C/dB|Capstone sensing|
|F2|Dual-dashboard sync|both flip ≤5s|M2, wireless+ICT|
|F3|Coarse→fine AI|SPC gates DL + proba|M1 ≥80%|
|F4|Fault injection|shake / distant heat / tone|input→output|
|F5|Offline survival|10s WiFi pull → 0 loss|M5/M6|
|F6|Calibration mode|cal.json + sheets|cal req|
|F7|Maintenance advice|fault → action text|industrial value|
|F8|QR + AR/EN + dataset/rubric|scan + print pack|IoT+AI platforms|

### 0.4 Grade calculation (100-pt working model — swap W if school sheet differs)
| Criterion | W | Earned by | Evidence |
|---|---|---|---|
|Prototype functional/portable/testable + input→output|25|dual flip ≤5s, boot <2min, 60min run|§10 script + M2/M5 logs|
|4+ measurables incl. response + accuracy|15|M1-M6 met|charts + KPIs|
|ICT+IoT+AI + hardware, no Arduino|15|Pi+Flask+Firebase+Grafana+RF|wiring + URLs + code|
|Dataset + rubric + AI ≥80%|20|≥1200 windows, GroupKFold, matrix|CSV + rubric + §7|
|Calibration documented|10|6-face + ice/boil + tone|§8 sheets|
|Logbooks + poster + Q&A|15|per-member books + QR poster|books + video prompt|
|**Total**|**100**|**Score = Σ(earned×W/max). Ex: 22+13+14+18+9+13=89.**|M1<80% or no cal = −30 risk; >8240 or Arduino = fail|

## 1. Discovery Summary

### 1.1 Inputs analyzed
1. `G12_27_ Capstone.pdf` (5 pp) — challenge + design requirements + constraints.
2. `DOC-20261014-WA0055.xlsx` (Sheet `الورقة1`, A1:I26 + total A27) — locked BOM, 25 items, total 8240 EGP.
3. `fmech-06-578379.pdf` (Mourtzis et al. 2020) — PdM + DAQ + Digital Twin/RUL + MR vision.
4. `machines-10-01006-v3.pdf` (Cinar et al. 2022) — CPS PaaS, coarse→fine monitoring, AutoML, KPIs, MQTT/ROS/OPC-UA, Grafana.

### 1.2 Decisions locked in v2.0
- **Grand Challenge:** Increase the industrial base of Egypt.
- **Pathway:** A. Industrial Base → automated lines / quality inspection.
- **System:** Portable motor monitor (vibration + temperature + sound) on Raspberry Pi 4, SPC coarse on edge, DL fine, dual dashboard.
- **Cloud stance:** Full working workflow runs **without cloud** (offline-first). Firebase free is a **compliance mirror** to satisfy `wireless to cloud + IoT` grading, at 0 EGP.
- **Dashboards:** **Grafana + Custom Web Panel combined** — Grafana for analytics/KPIs, Custom Panel for live demo/QR/mobile. Both read the same data model.

Why this fits:
- ADXL345 + K-type/MAX6675 + INMP441 = top-3 PdM sensors (Cinar review).
- No Arduino — Pi 4 8GB (encouraged advanced controller).
- ≥4 measurable incl. response time + accuracy, AI ≥80%, calibration docs, portable testable — all achievable.

### 1.3 Locked BOM (8240 EGP ceiling)
| # | Item | Function | Store | Qty | Unit | Total |
|---|---|---|---|---|---|---|
|1|ADXL345 Module|vibration|Makers|1|170|170|
|2|K-type Probe M6 (class 1)|heat|micro ohm|1|250|250|
|3|MAX6675 Module|TC ADC + CJ comp.|micro ohm|1|200|200|
|4|INMP441 Mic Module|sound|Future|1|180|180|
|5|Sensor Magnetic Base|mount|Future|1|120|120|
|6|Shielded Jumper M-F|EMI drain|Future|1|45|45|
|7|Jumper M-M|breadboard|Future|1|35|35|
|8|Male Pin Headers 40p|solder|Future|2|5|10|
|9|M3 Screws & Nuts 15mm|clamp|local|1|10|10|
|10|Nylon Spacers M3|isolation|Future|1|10|10|
|11|RPi PSU 5V/3A|power|Makers|1|320|320|
|12|Raspberry Pi 4 8GB|edge AI+IoT|Makers|1|5800|5800|
|13|MicroSD 32GB C10|OS+buffer|Future|1|190|190|
|14|Breadboard 840|prototyping|Future|1|65|65|
|15|Ceramic 100nF x3|decoupling|Future|3|5|15|
|16|Resistors 10k x2|pull-up|Future|2|5|10|
|17|Electrolytic 10uF|bulk|Future|1|5|5|
|18|Case & Fan|cooling|Makers|1|240|240|
|19|Thermal Paste|conduction|Future|1|35|35|
|20|IP65 Box|field proof|Future|1|140|140|
|21|PG7 Glands x2|seal|Future|2|15|30|
|22|Heat Shrink 1m|insulation|Future|1|10|10|
|23|Ship Makers|logistics|Makers|1|70|70|
|24|Ship RAM|logistics|RAM|1|70|70|
|25|Ship Future|logistics|Future|1|60|60|
|26|Reserve|re-quote + breakage|-|1|150|150|
|**Total**||||||**8240**|

- Compute (Pi + SD + PSU) = 6310 (76.6%). Sensors = 800 (9.7%). Enclosure/cooling = 420. Wiring = 185. Mounting = 175. Shipping = 200. Reserve = 150 for the MAX6675 and Pi re-quote.
- No paid cloud, no extra rig, no HoloLens. Demo motor borrowed. Cloud = free-tier only.

## 2. Vision & Objectives
**Vision:** Factory-ready portable PdM demo proving downtime can be cut by early detection, built ≤8240 EGP, working with or without internet.

**Objectives:**
1. Sense 3 modalities concurrently on edge.
2. Live input→output: shake/heat/sound → Healthy→Warning→Fault ≤5s on **both** dashboards.
3. Offline-first workflow + Firebase mirror + Grafana analytics + Custom Panel demo UI.
4. Coarse SPC → fine DL, ≥80% accuracy with evidence.
5. Calibrated sensors, documented.
6. Exhibition-ready: boot <2min, run >60min, IP65 portable, logbooks + dataset + rubric hard copies.

**Non-objectives:** No RUL-in-hours, no AR/HoloLens, no PLC/SCADA, no paid cloud, no medical path.

## 3. Users
- Team + supervisor / board — approve path, lend motor, lab access.
- Judges — live test, check M1-M6, AI evidence, calibration, dataset+rubric, scan QR to Custom Panel, inspect Grafana history.
- Technician persona — watches Custom Panel (Arabic/English), gets alert + maintenance advice; engineer watches Grafana KPIs.

## 4. Scope
**In:**
- Edge DAQ: ADXL345 I2C at ODR 800 Hz into 4096-sample windows (5.12 s, Nyquist 400 Hz covers BPFO/BPFI), MAX6675+K-type SPI 0.2 Hz, INMP441 I2S 16 kHz (RMS 10 Hz + 1 s clip on trigger).
- Conditioning: 100nF per sensor, 10uF bulk, 10k pull-ups, shielded M-F, magnet+M3+nylon stack.
- Edge software: Python collector, cal.json offsets, SPC X-bar/R, RF/1D-CNN inference, Mosquitto local + SD CSV buffer, Firebase RTDB mirror, Flask Custom Panel hosted on Pi.
- Cloud 0-EGP: Firebase Spark RTDB (mirror) + Firebase Hosting (Custom Panel public mirror) + Grafana Cloud free (analytics). No card.
- AI: 4-class (Healthy / Vib / Thermal / Acoustic) → fallback 2-class if needed; ≥1200 windows; GroupKFold; ≥80%.
- Enclosure: IP65 + PG7 + fan/paste/shrink; breadboard demo.
- Docs: dataset, rubric, cal sheets, logbooks, poster, QR codes.

**Out:** Paid cloud, vibration shaker/chamber purchase (hand shake + dryer at 30cm + phone tone), RUL regression, CMMS auto-orders (manual text advice only).

### 4.1 Design artifacts (generated, not hand-drawn)
`circuit/design.py` is the single source of truth for every component, pin and net. `python3 circuit/build.py` regenerates:
- `circuit/out/pdm.net` — KiCad-format netlist; `pdm_skidl.py` — SKiDL source for a machine with KiCad libraries.
- `circuit/out/erc_report.md` — 53 checks: 44 design (ERC + physics) + 9 BOM traceability: **0 ERC errors, 6 documented design WARN**, 1 deliberate BOM FAIL while the supplier sheet is unpriced. The BOM gate also fails loudly if the build target stops matching the design or the 8240 cap, or if the supplier sheet drifts from it.
- `circuit/out/schematic_main.svg`, `tc_frontend.svg`, `wiring_a3.svg` — A3 vector sheets embedded in Project Book §4.3.
- `circuit/out/block.mmd`, `sequence.mmd`, `state.mmd` — Mermaid diagrams for GitHub rendering.

The build exits non-zero on any FAIL, so a broken netlist cannot produce a drawing. Enforced invariants: no 5V pin on a 3.3V net, one push-pull driver per net, every IC decoupled by 100 nF on its own supply net, dedicated SPI CS with pull-up, unique I2C address, no pin used twice. WARNs are documented trade-offs (I2C cable length, sealed-box heat, single-point SPC false-alarm rate, Rref-code mismatch guard).

## 5. System Architecture v2.0 (offline-first + dual dashboard)

```
[ADXL345 I2C] ─┐
[K-type+MAX6675 SPI]┼→ [Pi 4 EDGE: cal → SPC coarse → DL fine → state]
[INMP441 I2S] ──┘         │ SD hot_backup.csv + Mosquitto local
                           ├→ [Flask Custom Panel :5000 on Pi hotspot] → phone/laptop (OFFLINE, primary demo)
                           └→ [Firebase RTDB REST 1/15s] → [Public Custom mirror + Grafana Cloud] (ONLINE, grading)
```

- Mourtzis Fig.2 simplified: DAQ→Edge AI→Dual Dashboard (Twin/RUL deferred — unaffordable).
- Cinar Fig.1/10/11: hot (SD + RTDB) / cold (CSV GitHub) + coarse→fine gating (90% fewer DL calls) + KPIs + Grafana.
- Power: official 5V/3A Type-C only; fan+paste mandatory. Mount: magnet+M3+nylon breaks ground loop; shielded runs; I2S short.

### 5.1 Dashboard split (why both)
| Aspect | Custom Web Panel (Flask + Firebase Hosting) | Grafana Cloud free |
|---|---|---|
|Audience|Judges + technician, mobile-first|Engineer + judges (depth)|
|Shows|Live g / temp / dB, big Healthy/Warning/Fault lamp, fault-type + advice, alert banner, QR, AR/EN toggle|Time series, FFT overlay, X-bar/R SPC, TBA/TB_VA, Th_DB, MQTT_QM, QL_M, confusion-matrix snapshot|
|Source|Pi Flask :5000 live; public mirror reads RTDB|RTDB via JSON API plugin + CSV snapshot upload|
|Offline|Yes — Pi hotspot, fully working|Cached snapshot + SD replay|
|Cost|0 EGP (Flask local + Hosting free 10GB)|0 EGP (free tier)|

Single data model shared by both (see §9.3). Same `state` value → both flip together in demo.

## 6. Requirements

### 6.1 Functional
1. F1: Concurrent timestamped sampling of 3 sensors.
2. F2: Live values + state on **both** Grafana and Custom Panel; consistent within 2s.
3. F3: Offline workflow: SD + local MQTT + Flask works with zero internet; auto-reconnect + backfill; ≤5s outage lossless.
4. F4: SPC breach → DL inference → notification (Custom banner + Firebase push + Grafana annotation) ≤5s.
5. F5: Fault-injection demo (shake / distant heat / tone) visibly flips both UIs.
6. F6: Calibration mode + QR to each dashboard + AR/EN labels.
7. F7: Firebase mirror toggle + quota guard (downgrade to 1/60s if near limit).

### 6.2 Measurable (mandate ≥4; we commit 6)
| ID | Metric | Target | How measured |
|---|---|---|---|
|M1|Accuracy|≥80% (goal ≥85%)|held-out GroupKFold, confusion + F1|
|M2|Response inject→both UIs alert|≤5s (goal ≤3s)|video + logs|
|M3|Vib error|±0.1g static / ±5% dyn|tilt reference|
|M4|Temp error|±2.0°C 0-97°C (class-1 probe)|ice+boil 3-pt, 5-min warm-up|
|M5|Uptime|≥60min, 0 crashes|log|
|M6|Loss/completeness|≤2% loss venue WiFi, 100% SD-recoverable|seq gaps|

Secondary on Grafana: TBA/TB_VA/TB_CA, Th_DB, P_Loss, MQTT_QM, QL_M, reconnect interval.

### 6.3 Non-functional
- Portable <3kg, setup <10min, boot <2min. Watchdog + read-only root + data partition.
- Usable: one-click `start.sh`, QR stickers, AR/EN. Testable without lab gear. No hard-coded secrets (env file).

## 7. AI/ML Plan
- Features per 5s window (50% overlap): rms/peak/kurt per axis, fft25/95, temp+temp_slope, zcr, mfcc0-2.
- Dataset ≥1200 (≥300/class), CSV `windows.csv` + `event_id` + notes; 70/15/15 Group split; augment shift/noise/mixup; drop-impute by interpolation.
- Baseline RF 300 trees (balanced) → 1D-CNN stretch. Must beat 80%; else collapse to Healthy vs Fault (+5-8%).
- Rubric 0-4 × label correctness / independence / cal validity / reproducibility, 2 raters, printed.
- Evidence: acc, P/R/F1, confusion, ROC, ms/inference on Pi, SPC trigger rate, training log.

## 8. Calibration (mandatory)
- ADXL345 6-face ±1g, 10s each → offset/scale → `g_bias`; accept bias ≤0.05g.
- K-type chain ice 0°C + boil ~97°C Cairo + room check → `t_a/t_b`; accept ±2°C with a class-1 probe. Cold junction: module ≥15 cm from the Pi, 5-min warm-up, log the open-TC flag (must be 0).
- INMP441 1kHz 60/75/90dB phone-app ref → gain; relative use only.
- Signed sheets + `calibration/` CSV + photos + `cal.json`. Re-run exhibition morning.

## 9. Communication / IoT / Cloud Plan (0 EGPter)

### 9.1 Zero-cost proof
| Service | Tier | Limit used | Cost |
|---|---|---|---|
|Firebase RTDB Spark|free, no card|1 write/15s ≈ 5.7k/day (limit ~20k writes, 1GB)|0|
|Firebase Hosting Spark|free|Custom mirror <10MB, <10GB/mo|0|
|Grafana Cloud free|free|1 dashboard, CSV + RTDB plugin|0|
|Mosquitto on Pi + Flask|local|unlimited offline|0|
|**Total cloud**| | |**0 EGP**|

Quota guard: Pi counts writes/day; if >15k, auto-throttle to 1/60s + SD-only + Grafana CSV replay.

### 9.2 Protocols & sampling
- Local primary: MQTT `factory/motor1` QoS1 to Mosquitto on Pi; Flask SSE to browser. Works on `pi-hotspot` with zero internet.
- Mirror: HTTPS REST `PUT https://<proj>.firebaseio.com/motor1.json?auth=KEY` every 15s (5s in demo burst ≤10min to stay under quota); JSON NGSI-like `urn:ngsi-ld:Motor:*`.
- Sampling: accel 800 Hz continuous, ODR = fs so the chip filter sits at Nyquist, timestamp-resampled to 4096 samples (5.12 s); temp 0.2 Hz; audio RMS 10 Hz + 1 s clip on trigger only.
- Security: TLS only, RTDB rules read-open/write-keyed for demo + locked after; key in `.env`, never git.

### 9.3 Shared data model (both UIs must render this)
```json
{"ts": 1729..., "g": 0.42, "rms": 0.51, "kurt": 7.2, "temp": 68.4,
 "temp_slope": 0.8, "zcr": 0.12, "state": "Warning|Fault|Healthy",
 "fault": "vib|thermal|acoustic|none", "proba": 0.91, "seq": 1234}
```

### 9.4 Custom Panel spec (Flask, ~1 page, mobile-first)
- Route `/` live cards + big lamp + Arabic/English toggle; `/api/latest` JSON; `/api/history?h=1` CSV-backed; SSE refresh 1s local / 15s Firebase mirror.
- Alert banner + beep + maintenance text: e.g. `Vib Fault 0.91 → check coupling, order bearing, re-measure in 1h`.
- QR: `http://192.168.4.1:5000` (offline) + `https://<proj>.web.app` (public). Both printed on box.
- Grafana spec: panels — (a) live RTDB temp/rms, (b) X-bar/R SPC with UCL/LCL, (c) event annotations from `state` flips, (d) KPI stat tiles TBA/QL_M, (e) confusion-matrix image panel.

## 10. Exhibition Script (input→output on both screens)
1. Power → both dashboards Online <2min (show QR scans).
2. Healthy 60s → SPC in-limits on Grafana, green lamp on Panel.
3. Shake 3s → RMS spike → Warning→Fault + banner + Grafana annotation ≤5s (film it).
4. Warm K-type probe (hand/dryer 30cm) → slope alarm on both.
5. Clap/tone → acoustic flag.
6. Pull WiFi 10s → Panel-local keeps live, SD buffers → restore → Firebase backfill, Grafana gap filled.
7. Show hard copies: confusion matrix + cal sheets + dataset sample + rubric + logbooks + receipts (8240).

## 11. Budget Control
- Freeze BOM. Spares already in BOM (headers/caps). Pi/SD failure = borrow, not rebuy.
- Out-of-stock swap only at ≤ price; cut improvements first (paste→borrow, shrink→tape), never ضروري 1-17.
- `budget/` receipts photo log weekly. Pi ordered W1 (volatility risk #1). Cloud changes never add cost (free-tier lock).

## 12. Milestones (6 weeks)
- W1: Order (Pi first) + OS/SD/power/fan + Firebase project + Grafana org created.
- W2: Wire 3 sensors + `i2cdetect` 0x53 + hello logs + mount + Mosquitto + Flask hello.
- W3: Cal + healthy baseline + Firebase mirror + Grafana live + Custom Panel live.
- W4: Fault dataset + SPC tuning + RF ≥80% + dual-UI flip test.
- W5: IP65/PG7 + SD buffer + quota guard + alerts + full drill + docs/rubric/logbooks + QR stickers.
- W6: Freeze code/wiring, rehearsal ×3, hard copies, spare kit, read-only SD image backup.

## 13. Risks
| Risk | Impact | Mitigation |
|---|---|---|
|Pi stock/price|halt|order W1, sealed receipt, borrow dev backup|
|MAX wiring noise|jitter|shielded, 100nF, 3-wire, averaging|
|Venue WiFi blocked|no cloud|hotspot + local Flask primary; cloud mirror optional for grading|
|Firebase quota hit|mirror stall|throttle 1/60s + SD replay; Grafana CSV fallback|
|Grafana plugin auth|no live|pre-cache snapshot image + CSV upload backup|
|SD corruption|loss|read-only root, safe shutdown, laptop CSV copy|
|Acc <80%|fail|more windows, 2-class fallback, feature fix before CNN|
|Heat damage|overrun|30cm heat only, nylon isolation|

## 14. Acceptance (Done = all checked)
- [ ] M1-M6 met with logs/plots on Grafana + Panel screenshots.
- [ ] Both dashboards flip together 3× without reboot, ≤5s.
- [ ] Offline-only run ≥30min proven (WiFi off) + Firebase mirror proven (WiFi on).
- [ ] AI ≥80% + confusion + dataset + rubric printed.
- [ ] Cal docs signed + before/after + `cal.json`.
- [ ] Spend ≤8240 + receipts; cloud spend = 0.
- [ ] Portable rig + QR + logbooks ready; no Arduino; no lab gear removed; code/wiring frozen.

## 15. Traceability
- Capstone → §2, §6.2, §8, §10, §14. BOM → §1.3, §11. Mourtzis DAQ/Twin/RUL → edge AI + future Twin. Cinar CPS/coarse-fine/KPI/Grafana → §5, §6.2, §7, §9.
- v2.0 deltas: Firebase Spark mirror (§9.1-9.4), Grafana+Panel split (§5.1, §9.4-9.5), offline-first F3/M6 + quota guard (§6-§9), updated script/milestones/acceptance (§10, §12, §14).

---
*Next: create Firebase Spark project + Grafana Cloud org (both free), wire Flask `/api/latest` to RTDB mirror, freeze BOM and order W1. Any paid-cloud proposal is rejected — 0 EGP lock.*
