# 🧸 How to Build the Robot-Doctor Rig (Explain Like I'm 8)

## What we're building

Imagine a motor (like a fan motor) that we want to keep healthy.
We attach three "senses" to it:

1. **A shake-sensor** (ADXL345) — feels if the motor is shaking too much
2. **A heat-sensor** (MAX6675 + K-type probe) — checks how hot the motor is
3. **A mic** (INMP441) — listens for funny noises

A **Raspberry Pi 4** (the brain) reads all three senses and decides if the motor is sick.
A little **fan** cools things down if it gets too hot.
A little **LED light** tells us "everything OK" or "uh-oh".

Everything sits on a **breadboard** — think of it like a LEGO baseplate with holes where we plug wires and parts in.

---

## 📍 The Breadboard Map

The breadboard has **rows A–J** (like street names) and **columns 1–60** (like house numbers).

```
      1   4   7   10  13  23  33  37  42  43  45  49  58
    ┌───┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───┐
  A │   │   │   │   │   │   │   │   │   │   │   │   │   │
  B │   │   │   │   │   │   │   │   │   │   │   │   │   │
  C │   │   │   │   │   │   │   │   │   │   │   │   │   │
  D │   │   │   │   │   │   │   │   │   │   │   │   │   │
  E │ C1│ C2│ C3│ C4│   │   │   │   │   │   │   │   │   │  ← capacitors
  F │   │   │   │   │   │ U2│   │   │   │   │   │   │   │  ← module bodies
  G │   │   │   │   │   │ U3│   │   │   │   │   │   │   │      above row J
  H │   │   │   │   │   │ U4│   │   │   │   │   │   │   │
  I │   │   │   │   │   │   │   │   │   │   │   │   │   │
  J │C1 │C2 │C3 │C4 │   │U2 │U3 │U4 │D1 │R2 │R4 │   │   │  ← pins plug here
    └───┴───┴───┴───┴───┴───┴───┴───┴───┴───┴───┴───┴───┘
```

Below the breadboard sits the **Raspberry Pi 4**. Its 40 pins line up with the breadboard columns so wires can go straight up.

Off to the right (not on the board):
- **K-type probe** — its two metal tips go into the MAX6675 screw terminal
- **5V fan** — one wire to Pi 5V, one wire to GND

---

## 🔌 Piece-by-piece: what pins go where

### 1. Raspberry Pi 4 (the brain)

| Pi pin | What it's for | Connects to (wire color) |
|--------|---------------|--------------------------|
| Pin 1  | 3.3V power    | 3V3 rail (red)           |
| Pin 3  | I2C data      | ADXL345 SDA (dark blue)  |
| Pin 5  | I2C clock     | ADXL345 SCL (light blue) |
| Pin 9  | GND           | GND rail (dark gray)     |
| Pin 12 | I2S clock     | Mic BCLK (dark teal)     |
| Pin 14 | GND           | GND rail (dark gray)     |
| Pin 17 | 3.3V power    | 3V3 rail (red)           |
| Pin 19 | SPI MOSI      | *(not used)*             |
| Pin 21 | SPI data in   | Heat-sensor SO (gold)    |
| Pin 23 | SPI clock     | Heat-sensor SCK (brown)  |
| Pin 24 | SPI chip-sel  | Heat-sensor CS (dark red)|
| Pin 25 | GND           | GND rail (dark gray)     |
| Pin 35 | I2S word-sel  | Mic WS (teal)            |
| Pin 36 | LED control   | LED resistor (gray)      |
| Pin 38 | I2S data in   | Mic SD (dark green-teal) |
| Pin 39 | GND           | GND rail (dark gray)     |
| Pin 4  | 5V power      | Fan + (orange)           |
| Pin 6  | GND           | Fan return path          |

---

### 2. ADXL345 shake-sensor (module, row J pin 3)

| Module pin | What it does | Connects to (wire color) |
|------------|--------------|--------------------------|
| Pin 1 VCC  | Power        | 3V3 rail (red)           |
| Pin 2 GND  | Ground       | GND rail (dark gray)     |
| Pin 3 CS   | "Use I2C mode" | 3V3 rail (red)         |
| Pin 4 SDO  | "Address 0x53" | GND rail (dark gray)    |
| Pin 5 SDA  | Data         | Pi pin 3 (dark blue)     |
| Pin 6 SCL  | Clock        | Pi pin 5 (light blue)    |

---

### 3. MAX6675 heat-sensor (module, row J pin 23)

| Module pin | What it does | Connects to (wire color) |
|------------|--------------|--------------------------|
| Pin 1 VCC  | Power        | 3V3 rail (red)           |
| Pin 2 GND  | Ground       | GND rail (dark gray)     |
| Pin 3 SCK  | SPI clock    | Pi pin 23 (brown)        |
| Pin 4 CS   | Chip-select  | Pi pin 24 + 10k resistor (dark red) |
| Pin 5 SO   | Data out     | Pi pin 21 (gold)         |
| Pin 6 TP   | Thermocouple + | K-type probe tip T+ (purple) |
| Pin 7 TN   | Thermocouple − | K-type probe tip T− (dark purple) |

The probe's two metal wires go into the MAX6675's green screw terminal.

---

### 4. INMP441 microphone (module, row J pin 15)

| Module pin | What it does | Connects to (wire color) |
|------------|--------------|--------------------------|
| Pin 1 VDD  | Power        | 3V3 rail (red)           |
| Pin 2 GND  | Ground       | GND rail (dark gray)     |
| Pin 3 L/R  | "Left channel" | GND rail (dark gray)   |
| Pin 4 BCLK | Bit clock    | Pi pin 12 (dark teal)    |
| Pin 5 WS   | Word select  | Pi pin 35 (teal)         |
| Pin 6 SD   | Data out     | Pi pin 38 (dark green-teal) |

---

### 5. Capacitors C1–C4 (row E, on the top power rails)

These are like little water-tanks that keep power steady.

| Ref | Pin 1 | Pin 2 | What it does |
|-----|-------|-------|--------------|
| C1 (100nF) | 3V3 rail | GND rail | Steady power for ADXL345 |
| C2 (100nF) | 3V3 rail | GND rail | Steady power |
| C3 (100nF) | 3V3 rail | GND rail | Steady power |
| C4 (10µF)  | 3V3 rail | GND rail | Bigger tank, watch + and − ends |

---

### 6. Resistors R2 & R4 and LED D1 (row J, right side)

| Ref | Pin 1 | Pin 2 | What it does |
|-----|-------|-------|--------------|
| R2 (10k) | 3V3 rail | Heat-sensor CS + Pi pin 24 | Holds heat-sensor "awake" |
| R4 (330Ω) | Pi pin 36 | LED anode (+) | Protects the LED |
| D1 LED   | Anode (+) | Cathode (−) → GND | Blinks when Pi says OK |

So: **Pi pin 36 → R4 → LED → GND**

---

### 7. 5V fan (off-board, right side)

| Fan wire | Connects to (wire color) |
|----------|--------------------------|
| + (red)  | Pi pin 4 (5V, orange)    |
| − (black)| GND rail column 58 (dark gray) |

---

## 🎨 Wire color cheat-sheet

| Color | What it carries | Like... |
|-------|----------------|---------|
| 🔴 Red (#c0392b) | 3.3V power | Food |
| ⚫ Dark gray (#34495e) | Ground | The return path / drain |
| 🟠 Orange (#e67e22) | 5V power | Fan power |
| 🟦 Dark blue (#1f618d) | I2C data | Shake-sensor talking |
| 🔵 Light blue (#5dade2) | I2C clock | Shake-sensor timing |
| 🟤 Brown (#b9770e) | SPI clock | Heat-sensor timing |
| 🟡 Gold (#d4ac0d) | SPI data in | Heat-sensor talking back |
| 🟫 Dark red (#a04000) | SPI chip-select | "Heat-sensor, your turn!" |
| 🟢 Dark teal (#117a65) | I2S bit clock | Mic timing |
| 🟣 Teal (#1abc9c) | I2S word-select | Mic "left/right" |
| 🟢 Dark green-teal (#0e6655) | I2S data | Mic talking |
| 🟪 Purple (#8e44ad) | Thermocouple + | Heat probe tip + |
| 🟣 Dark purple (#6c3483) | Thermocouple − | Heat probe tip − |
| ⚪ Gray (#7f8c8d) | LED | Status light |

---

## 🧱 Step-by-step build order

1. **Plug the modules into row J:** ADXL345 at pin 3, INMP441 at pin 15, MAX6675 at pin 23.
2. **Plug the capacitors into row E:** C1–C4 on the top power rails.
3. **Plug R2, D1, R4 into row J** on the right side.
4. **Push wires into the holes** following the table above. Each colored wire goes to the hole of the right row/column.
5. **Plug the K-type probe** into the MAX6675 green screw terminal.
6. **Plug the Pi below** so its header lines up with the breadboard columns.
7. **Connect the fan:** + to Pi pin 4, − to GND rail.
8. **Double-check:** No wire should cross over printed letters or numbers. Every wire ends in a numbered hole.

---

## ✅ How to know it's right

- Turn power on and **use a multimeter** to check you have 3.3V and 5V before plugging anything in.
- **ADXL345:** `i2cdetect -y 1` must show `0x53`
- **MAX6675:** Put the probe in ice water — it should read `0 ±2 °C`
- **Mic:** `arecord -l` should show the microphone
- **LED:** Should light up when the Pi says everything is OK

---

If a step fails, **stop there** — don't add the next part until the first one works. That way you know exactly which piece is the problem.

*Source: `circuit/design.py` (the master list) and `circuit/fzz/routes.py` (the wire paths). Rebuild check: `python3 circuit/build.py` — 44 PASS / 8 WARN / 0 FAIL.*