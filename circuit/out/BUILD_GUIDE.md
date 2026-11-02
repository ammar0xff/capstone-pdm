# 🎯 PDM Rig — Breadboard Master Guide (the .fzz companion)

**Fritzing file:** `PDM_Predictive_Maintenance.fzz`  
**Status:** rebuilt & verified — 14 instances, 15 nets, 166 wires, **0 geometry problems**  
**Read from:** `circuit/PDM_Predictive_Maintenance.fzz` or `circuit/out/PDM_Predictive_Maintenance.fzz`  
**Preview:** `circuit/out/fritzing_breadboard.svg` / `.png`

This document combines **everything** you need to build the rig: the Fritzing sketch, the notes, the clear pin mapping, and comfort-wiring rules so the drawing stays readable.

---

## 📦 What's in the .fzz sketch

| Item | Count |
|------|-------|
| Parts (instances) | 14 |
| Nets (coloured wire groups) | 15 |
| Wires | 166 |
| Breadboard holes | 70 |
| Module IDs | all start with `PDM_*` |

**Parts on the breadboard:**
- `U1` — Raspberry Pi 4 Model B 4GB (below the board)
- `U2` — ADXL345 3-axis accelerometer (I2C, address 0x53)
- `U3` — MAX6675 K-type thermocouple + cold junction (SPI)
- `U4` — INMP441 I2S MEMS microphone
- `C1, C2, C3` — 100 nF ceramic decoupling caps
- `C4` — 10 µF electrolytic cap
- `R2` — 10 kΩ pull-up (heat-sensor chip-select)
- `R4` — 330 Ω LED series resistor
- `D1` — status LED
- `F1` — 5 V cooling fan

**Off-board:**
- `R1` — K-type probe (class 1), two metal tips → MAX6675 screw terminal

---

## 🧩 Clear pin mapping — what connects to what

### Raspberry Pi 4 — U1 (40-pin header, below the breadboard)

| Pi pin | Signal | Connects to | Wire colour |
|--------|--------|-------------|-------------|
| 1 | 3V3 | 3V3 rail | red |
| 3 | SDA (I2C data) | ADXL345 SDA | dark blue |
| 5 | SCL (I2C clock) | ADXL345 SCL | light blue |
| 9 | GND | GND rail | dark gray |
| 12 | BCLK (I2S clock) | Mic BCLK | dark teal |
| 14 | GND | GND rail | dark gray |
| 17 | 3V3 | 3V3 rail | red |
| 19 | MOSI | *(not used)* | — |
| 21 | MISO (SPI data in) | MAX6675 SO | gold |
| 23 | SCLK (SPI clock) | MAX6675 SCK | brown |
| 24 | CE0 (SPI chip-select) | MAX6675 CS | dark red |
| 25 | GND | GND rail | dark gray |
| 35 | WS (I2S word-select) | Mic WS | teal |
| 36 | GPIO16 (LED drive) | → R4 → LED | gray |
| 38 | DIN (I2S data in) | Mic SD | dark green-teal |
| 39 | GND | GND rail | dark gray |
| 4 | 5V power | Fan + | orange |
| 6 | GND | Fan − / GND rail | dark gray |

### ADXL345 shake-sensor — U2 (row J, pin 3)

| Mod pin | Signal | Connects to | Wire colour |
|---------|--------|-------------|-------------|
| 1 | VCC | 3V3 rail | red |
| 2 | GND | GND rail | dark gray |
| 3 | CS | 3V3 rail (I2C mode) | red |
| 4 | SDO | GND rail (address 0x53) | dark gray |
| 5 | SDA | Pi pin 3 | dark blue |
| 6 | SCL | Pi pin 5 | light blue |

### MAX6675 heat-sensor — U3 (row J, pin 23)

| Mod pin | Signal | Connects to | Wire colour |
|---------|--------|-------------|-------------|
| 1 | VCC | 3V3 rail | red |
| 2 | GND | GND rail | dark gray |
| 3 | SCK | Pi pin 23 | brown |
| 4 | CS | Pi pin 24 + R2 pull-up | dark red |
| 5 | SO | Pi pin 21 | gold |
| 6 | T+ / TP | K-type probe tip + | purple |
| 7 | T- / TN | K-type probe tip − | dark purple |

The probe's two metal wires go into the MAX6675 green screw terminal.

### INMP441 microphone — U4 (row J, pin 15)

| Mod pin | Signal | Connects to | Wire colour |
|---------|--------|-------------|-------------|
| 1 | VDD | 3V3 rail | red |
| 2 | GND | GND rail | dark gray |
| 3 | L/R | GND rail (left channel) | dark gray |
| 4 | BCLK | Pi pin 12 | dark teal |
| 5 | WS | Pi pin 35 | teal |
| 6 | SD | Pi pin 38 | dark green-teal |

### Capacitors C1–C4 (row E, on the top power rails)

| Ref | Value | Pin 1 | Pin 2 | Purpose |
|-----|-------|-------|-------|---------|
| C1 | 100 nF | 3V3 rail | GND rail | steady power |
| C2 | 100 nF | 3V3 rail | GND rail | steady power |
| C3 | 100 nF | 3V3 rail | GND rail | steady power |
| C4 | 10 µF | 3V3 rail | GND rail | bigger tank (watch +/−) |

### Resistors & LED (row J, right side)

| Ref | Pin 1 | Pin 2 | Purpose |
|-----|-------|-------|---------|
| R2 | 3V3 rail | MAX6675 CS + Pi pin 24 | holds chip-select idle-high |
| R4 | Pi pin 36 | LED anode (+) | protects LED |
| D1 (LED) | anode (+) | cathode (−) → GND | status light |

Chain: **Pi pin 36 → R4 → LED → GND**

### 5 V fan — F1 (off-board right)

| Fan wire | Connects to | Wire colour |
|----------|-------------|-------------|
| + | Pi pin 4 (5V) | orange |
| − | GND rail column 58 | dark gray |

---

## 🎨 Wire colour cheat-sheet

| Colour | Carries | Think of it as… |
|--------|---------|-----------------|
| 🔴 Red | 3.3V power | food |
| ⚫ Dark gray | Ground | return path / drain |
| 🟠 Orange | 5V power | fan power |
| 🟦 Dark blue | I2C data | shake-sensor talking |
| 🔵 Light blue | I2C clock | shake-sensor timing |
| 🟤 Brown | SPI clock | heat-sensor timing |
| 🟡 Gold | SPI data in | heat-sensor talking back |
| 🟫 Dark red | SPI chip-select | "heat-sensor, your turn!" |
| 🟢 Dark teal | I2S bit clock | mic timing |
| 🟣 Teal | I2S word-select | mic left/right |
| 🟢 Dark green-teal | I2S data | mic talking |
| 🟪 Purple | Thermocouple + | heat probe tip + |
| 🟣 Dark purple | Thermocouple − | heat probe tip − |
| ⚪ Gray | LED drive | status light |

---

## 🏗️ Comfort-wiring rules (so it stays readable)

These are the rules baked into the `.fzz` file and verified by the geometric auditor:

1. **No wires over labels.** Cap labels sit half a pitch left of each cap body; tap lanes run half a pitch outside the cap legs so verticals never cross text.
2. **No wires over column numbers.** The breadboard's bottom row numbers (inside the wire-exit band) are removed; top numbers stay and are never crossed.
3. **No wires over row letters.** The GND right-edge bridge runs at x=604, just outside the board, so the printed row letters A–J stay readable.
4. **TC wire avoids text.** The thermocouple TC_N wire drops to y=128.5 (between printed G and H row letters) instead of running through the "G" label.
5. **Export shift handled.** Fritzing's SVG export pads the top by one label row (+5 units); the auditor accounts for this so holes line up with wires exactly.
6. **Community parts kept as-is.** The ADXL345 community silkscreen has small INT1/INT2/SDO overlaps — that's the part's own design, left untouched (whitelisted in the auditor).

---

## 🧱 Build order

1. **Rails first.** Plug the power/ground rails. Meter-check 3.3 V and 5 V before plugging anything in.
2. **U2 only.** `i2cdetect -y 1` must show `0x53`.
3. **U3 only.** Probe in ice water → reads `0 ±2 °C`, open-TC flag is 0.
4. **U4 only.** `arecord -l` shows the microphone.
5. **If a step fails, stop there** — adding the next module hides which one is wrong.

---

## 📁 Files in the repo

| File | What it is |
|------|------------|
| `circuit/PDM_Predictive_Maintenance.fzz` | The Fritzing sketch deliverable |
| `circuit/out/PDM_Predictive_Maintenance.fzz` | Same file, staged for the book |
| `circuit/out/fritzing_breadboard.svg` | Verified breadboard export (source of truth) |
| `circuit/out/fritzing_breadboard.png` | 2400 px raster preview |
| `circuit/out/connection_table.md` | Technical pin-by-pin connection table |
| `circuit/out/connection_table_simple.md` | Explain-like-I'm-8 wiring guide |
| `circuit/fzz/build_fzz.py` | Rebuilds the .fzz from design.py |
| `circuit/fzz/check_export.py` | Geometric auditor (0 problems) |
| `circuit/fzz/routes.py` | All 15 net wire routes |
| `circuit/fzz/layout.py` | All 14 part placements |
| `circuit/design.py` | Single source of truth (components + nets) |
| `circuit/out/erc_report.md` | 44 PASS / 8 WARN / 0 FAIL |

---

## ✅ Verification

Run on the Pi or any machine with Python (stdlib only):

```bash
python3 circuit/build.py
```

Expected: `44 PASS / 8 WARN / 0 FAIL`, netlist balanced (15 nets, 13 components).

The 8 WARNs are documented trade-offs (MAX6675 allowance needs a real quote ≤201.75 EGP, I²C cable <10 cm, sealed-box heat-spreader, SPC 2-of-3 rule, class-1 probe required).

---

*Source of truth: `circuit/design.py` (components + nets) → `circuit/fzz/routes.py` (wire paths) → `circuit/fzz/build_fzz.py` (the .fzz). Every coloured wire in the sketch ends in a numbered hole — no invented connections.*