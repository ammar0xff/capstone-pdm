# ERC + Physics Report — PdM Rig

Generated from `circuit/design.py` (single source of truth).

**35 PASS · 5 WARN · 4 FAIL**

A WARN is a documented engineering trade-off, not a broken rule.

### ERC

| Check | Status | Detail |
|---|---|---|
| every net has >= 2 nodes | **PASS** | 17 nets, min 2 nodes |
| no 5V/3V3 or GND mis-wiring | **PASS** | 5V feeds only the Pi input and the fan; every sensor pin is on 3V3 |
| U2 power + ground | **PASS** | 3V3 + GND present |
| U3 power + ground | **PASS** | 3V3 + GND present |
| U4 power + ground | **PASS** | 3V3 + GND present |
| C1 decouples U2 | **PASS** | 100nF at module VCC |
| C2 decouples U3 | **PASS** | 100nF at module VCC |
| C3 decouples U4 | **PASS** | 100nF at module VCC |
| C4 bulk 10uF on 3V3 | **PASS** | holds rail during SPI bursts |
| I2C is open-drain only | **PASS** | SDA/SCL driven by open-drain, no push-pull fight |
| I2C pull-ups present | **PASS** | Pi 4 onboard 1.8k on GPIO2/3 (external 10k optional) |
| I2C address unique | **PASS** | ADXL345 = 0x53 (SDO tied to GND) |
| SPI CS dedicated + pulled high | **PASS** | R2 10k keeps MAX31865 deselected during boot |
| no output-output conflicts | **PASS** | one driver per net |
| no pin assigned twice | **PASS** | 59 pins mapped |
| I2S data direction | **PASS** | U4.SD (out) -> U1.GPIO20 PCM_DIN (in); BCLK/WS are Pi outputs |
| SPI MISO direction | **PASS** | U3.SDO (out) -> U1.GPIO9 MISO (in) |
| spare GPIO for buzzer/relay | **PASS** | 14 free physical pins: 7, 11, 13, 15, 16, 18, 22, 26, 29, 31, 32, 33, 37, 40 |

### Signal

| Check | Status | Detail |
|---|---|---|
| Nyquist covers bearing tones | **PASS** | fs=800 Hz -> Nyquist 400 Hz >= 300 Hz (BPFO/BPFI) |
| FFT resolution | **PASS** | 0.195 Hz/bin over 5.12 s -> separates BPFO and BPFI peaks |
| anti-alias configuration | **PASS** | ADXL345 ODR = 800 Hz, internal LPF at ODR/2 = 400 Hz, FIFO 32-sample bursts |
| accelerometer resolution | **PASS** | 3.9 mg/LSB in FULL_RES (all ranges) -> 3.9 mg << 0.1 g budget |
| accelerometer noise floor | **PASS** | 15.0 mg RMS over 400 Hz (< 20 mg spec), averaging lowers it |

### RTD

| Check | Status | Detail |
|---|---|---|
| Rref matches the board | **WARN** | board has 430R; if code says 400R the reading is off by -17.9 C at 0 C -> set ref_resistor=430 |
| ADC resolution | **PASS** | 15-bit over 430R = 13.12 mR = 0.034 C/LSB |
| self-heating error | **PASS** | I=4.65 mA, 2.16 mW during 66 ms, 1.3% duty -> 0.000 C average |
| 3-wire lead compensation | **PASS** | third lead senses IR drop of the shared lead; 2-wire mode would add ~+0.5 C/m |
| thermal slope detectability | **PASS** | tau~8s, 1 C/s ramp -> +5.0 C in 5 s vs 0.5 C alarm threshold |

### Bus

| Check | Status | Detail |
|---|---|---|
| I2C rise time @400 kHz | **PASS** | tr=2.2*Rp*Cb=238 ns < 300 ns (with optional 10k: 201 ns) |
| I2C pull-up current | **PASS** | 2.16 mA < 3 mA I2C limit |
| I2C cable length limit | **WARN** | keep < 10 cm / 60 pF; at 200 pF rise time exceeds 300 ns |
| SPI clock vs wiring | **PASS** | MAX31865 supports 5 MHz; 1 MHz over <10 cm jumper is safe |
| I2S clocking | **PASS** | 16 kHz * 32 bit = 512 kHz BCLK, well within Pi PCM |

### Power

| Check | Status | Detail |
|---|---|---|
| 5V rail headroom | **PASS** | 7.43 W peak = 1.49 A of 3.0 A (50% load) |
| 3.3V rail load | **PASS** | ~15 mA (sensors + LED) vs ~1 A available |
| IP65 + internal fan | **WARN** | sealed box recirculates air: bolt an aluminium plate to the lid as a heat spreader; expect +10..15 C inside, still below 80 C throttle |
| LED current | **PASS** | (3.3-2.0)/330 = 3.9 mA |

### Audio

| Check | Status | Detail |
|---|---|---|
| audio Nyquist | **PASS** | 16 kHz -> 8 kHz bandwidth, covers 2-6 kHz squeal |

### Stats

| Check | Status | Detail |
|---|---|---|
| SPC false-alarm interval | **WARN** | single 3-sigma point = 370 windows (~31 min); use 2-of-3 with 2-sigma warning to reach hours |

### BOM

| Check | Status | Detail |
|---|---|---|
| locked total | **FAIL** | 8888.25 EGP across 23 lines (hard cap 8240) -> +648.25 EGP |
| PT100 3-wire probe present | **FAIL** | MISSING from the working xlsx - M4 (+/-1 C) needs a 3-wire RTD. The book, code, charts and calibration plan all assume this part. |
| MAX31865 front end present | **FAIL** | MISSING from the working xlsx - 15-bit ratiometric conversion, 0.034 C/LSB. The book, code, charts and calibration plan all assume this part. |
| Raspberry Pi 4 8GB present | **FAIL** | MISSING from the working xlsx - headroom for SPC + RF + Flask + Mosquitto. The book, code, charts and calibration plan all assume this part. |
| every BOM line mapped | **WARN** | review: حساس Type-K |
