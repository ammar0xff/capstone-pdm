# ERC + Physics Report — PdM Rig

Generated from `circuit/design.py` (single source of truth).

BOM: build target `circuit/bom_target.csv` (cap 8240) · supplier sheet `DOC-20261014-WA0055.xlsx`

**44 PASS · 8 WARN · 1 FAIL**

A WARN is a documented engineering trade-off, not a broken rule.

### ERC

| Check | Status | Detail |
|---|---|---|
| every net has >= 2 nodes | **PASS** | 15 nets, min 2 nodes |
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
| no pin assigned twice | **PASS** | 54 pins mapped |
| I2S data direction | **PASS** | U4.SD (out) -> U1.GPIO20 PCM_DIN (in); BCLK/WS are Pi outputs |
| SPI MISO direction | **PASS** | U3.SO (out) -> U1.GPIO9 MISO (in) |
| spare GPIO for buzzer/relay | **PASS** | 14 free physical pins: 7, 11, 13, 15, 16, 18, 22, 26, 29, 31, 32, 33, 37, 40 |

### Signal

| Check | Status | Detail |
|---|---|---|
| Nyquist covers bearing tones | **PASS** | fs=800 Hz -> Nyquist 400 Hz >= 300 Hz (BPFO/BPFI) |
| FFT resolution | **PASS** | 0.195 Hz/bin over 5.12 s -> separates BPFO and BPFI peaks |
| anti-alias configuration | **PASS** | ADXL345 ODR = 800 Hz, internal LPF at ODR/2 = 400 Hz, FIFO 32-sample bursts |
| accelerometer resolution | **PASS** | 3.9 mg/LSB in FULL_RES (all ranges) -> 3.9 mg << 0.1 g budget |
| accelerometer noise floor | **PASS** | 15.0 mg RMS over 400 Hz (< 20 mg spec), averaging lowers it |

### Thermo

| Check | Status | Detail |
|---|---|---|
| 12-bit step size | **PASS** | 0.25 C per step = 12% of the +/-2.0 C budget |
| M4 is reachable with this BOM | **WARN** | MAX6675 is +/-2 C and a class-2 K-type probe +/-2.5 C; only a class-1 probe (+/-1.5 C) plus calibration keeps the RSS under +/-2.0 C. A PT100 + MAX31865 chain gave 0.40 C - this is the trade for range and speed. |
| error budget (class-1 probe) | **PASS** | RSS = sqrt(1.5^2 + 0.5^2 + 0.5^2 + 0.25^2) = 1.68 C vs +/-2.0 C -> margin 1.19x |
| cold-junction placement | **WARN** | box air runs +12 C above ambient; the CJ sensor is on the same die as the terminal block, so mount the module >15 cm from the Pi and warm up 5 min before calibrating |
| self-heating | **PASS** | passive junction: no excitation current, ~0 mW (the RTD needed 2.2 mW pulses) |
| response time | **PASS** | tau ~4 s bare junction: a dryer ramp is visible ~2x sooner than the M6 RTD |
| open-circuit detection | **PASS** | MAX6675 flags an open thermocouple; without that check a broken probe reads ambient and looks healthy |
| lead signal level / EMI | **WARN** | 41 uV/C -> only 4.10 mV over 0-100 C: shielded twisted pair, shield grounded at the Pi end only, keep 10 cm from the fan and the 5 V wires |
| out-of-range guard | **PASS** | reject < -20 C or > 200 C as a wiring fault, not a motor event |

### Bus

| Check | Status | Detail |
|---|---|---|
| I2C rise time @400 kHz | **PASS** | tr=2.2*Rp*Cb=238 ns < 300 ns (with optional 10k: 201 ns) |
| I2C pull-up current | **PASS** | 2.16 mA < 3 mA I2C limit |
| I2C cable length limit | **WARN** | keep < 10 cm / 60 pF; at 200 pF rise time exceeds 300 ns |
| SPI clock vs wiring | **PASS** | MAX6675 supports 4.3 MHz, mode 0; 1 MHz over <10 cm jumper is safe |
| SPI is read-only | **PASS** | MAX6675 has no MOSI: CS low, 16 clocks, 12-bit result + open-TC flag |
| I2S clocking | **PASS** | 16 kHz * 32 bit = 512 kHz BCLK, well within Pi PCM |

### Power

| Check | Status | Detail |
|---|---|---|
| 5V rail headroom | **PASS** | 7.42 W peak = 1.48 A of 3.0 A (49% load) |
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
| build target total | **PASS** | 8240.00 EGP across 26 lines (cap 8240) |
| K-type probe in the target | **PASS** | included |
| MAX6675 front end in the target | **PASS** | included |
| Raspberry Pi 4 in the target | **PASS** | included |
| fan + heatsink in the target | **PASS** | included |
| cable glands in the target | **PASS** | included |
| estimate still to be quoted | **WARN** | priced from an estimate: MAX6675 Module - the 150 EGP reserve absorbs +/-50 |
| supplier sheet is fully priced | **FAIL** | no price for: MAX6675 Module |
| supplier sheet matches the target | **WARN** | 8888.25 EGP across 23 lines; target is 8240.00. See BOM_reconciliation.md - the difference is the Pi quote and the missing cooling hardware, not the sensors. |
