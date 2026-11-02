# Connection table — PdM rig breadboard
# Source of truth: circuit/design.py (COMPS + NETS), circuit/fzz/routes.py, circuit/fzz/layout.py
# Rebuild check: python3 circuit/build.py  (44 PASS / 8 WARN / 0 FAIL, netlist balanced 15 nets / 13 comps)

Net colour key:
- 3V3 #c0392b   GND #34495e   5V #e67e22   I2C_SDA #1f618d   I2C_SCL #5dade2
- SPI_SCLK #b9770e   SPI_MISO #d4ac0d   SPI_CS0 #a04000
- I2S_BCLK #117a65   I2S_WS #1abc9c   I2S_SD #0e6655
- TC_P #8e44ad   TC_N #6c3483   LED #7f8c8d

----------------------------------------------------------------------
1 · Raspberry Pi 4 Model B — U1  (J8 40-pin header, below the breadboard)
----------------------------------------------------------------------
| J8 pin | Pi signal      | Net       | Connects to                         | Notes                                  |
|--------|----------------|-----------|-------------------------------------|----------------------------------------|
| 1      | 3V3            | 3V3       | 3V3 rail (W/Y)                      | Pi 3V3 supply                          |
| 3      | SDA1 (GPIO2)   | I2C_SDA   | ADXL345 U2 pin5 SDA                 | I2C data, 1.8 kΩ onboard pull-up       |
| 5      | SCL1 (GPIO3)   | I2C_SCL   | ADXL345 U2 pin6 SCL                 | I2C clock                              |
| 9      | GND            | GND       | GND rail (X/Z)                      |                                        |
| 12     | PCM_CLK (GPIO18)| I2S_BCLK | INMP441 U4 pin4 BCLK                | I2S bit clock                          |
| 14     | GND            | GND       | GND rail                            |                                        |
| 17     | 3V3            | 3V3       | 3V3 rail (W/Y)                      | Pi 3V3 supply                          |
| 19     | MOSI (GPIO10)  | —         | (not wired)                         | Spare — MAX6675 is read-only (SO only) |
| 21     | MISO (GPIO9)   | SPI_MISO  | MAX6675 U3 pin5 SO                  | SPI data in to Pi                      |
| 23     | SCLK (GPIO11)  | SPI_SCLK  | MAX6675 U3 pin3 SCK                 | SPI clock                              |
| 24     | CE0 (GPIO8)    | SPI_CS0   | MAX6675 U3 pin4 CS  (via R2 10k)    | SPI chip select; R2 pulls CS to 3V3    |
| 25     | GND            | GND       | GND rail                            |                                        |
| 35     | PCM_FS (GPIO19)| I2S_WS    | INMP441 U4 pin5 WS                  | I2S word select / LRCLK                |
| 36     | GPIO16         | LED_A     | R4 pin1 → R4 pin2 → LED anode       | Status LED drive                       |
| 38     | PCM_DIN (GPIO20)| I2S_SD   | INMP441 U4 pin6 SD                  | I2S data in to Pi                      |
| 39     | GND            | GND       | GND rail                            |                                        |
| 4      | 5V             | 5V        | Fan F1 pin1 (+)                     | Direct 5 V to fan, no rail             |
| 6      | GND            | GND       | Fan return path via GND rail        | Fan − returns to GND rail col 58       |

----------------------------------------------------------------------
2 · ADXL345 3-axis accelerometer — U2  (module pins row J, body above)
----------------------------------------------------------------------
| Mod pin | Signal | Net     | Connects to                    | Notes                              |
|---------|--------|---------|--------------------------------|------------------------------------|
| 1       | VCC    | 3V3     | 3V3 rail                       | Module supply 3.3 V                |
| 2       | GND    | GND     | GND rail                       |                                    |
| 3       | CS     | 3V3     | 3V3 rail                       | CS tied high → I2C mode            |
| 4       | SDO    | GND     | GND rail                       | SDO low → I2C address 0x53         |
| 5       | SDA    | I2C_SDA | Pi pin3 SDA                    | I2C data                           |
| 6       | SCL    | I2C_SCL | Pi pin5 SCL                    | I2C clock                          |

----------------------------------------------------------------------
3 · MAX6675 K-type thermocouple — U3  (module pins row J, body above)
----------------------------------------------------------------------
| Mod pin | Signal  | Net       | Connects to                  | Notes                                      |
|---------|---------|-----------|------------------------------|--------------------------------------------|
| 1       | VCC     | 3V3       | 3V3 rail                     | Module supply 3.0–3.6 V                    |
| 2       | GND     | GND       | GND rail                     |                                            |
| 3       | SCK     | SPI_SCLK  | Pi pin23 SCLK                | SPI clock                                  |
| 4       | CS      | SPI_CS0   | Pi pin24 CE0 (+ R2 to 3V3)   | SPI chip select, active low                |
| 5       | SO      | SPI_MISO  | Pi pin21 MISO                | SPI data out (read-only)                   |
| 6       | T+ / TP | TC_P      | Probe R1 pin1 T+ (chromel)   | Thermocouple + lead                        |
| 7       | T- / TN | TC_N      | Probe R1 pin2 T- (alumel)    | Thermocouple – lead                        |

----------------------------------------------------------------------
4 · INMP441 I2S MEMS microphone — U4  (module pins row J, body above)
----------------------------------------------------------------------
| Mod pin | Signal | Net       | Connects to      | Notes                  |
|---------|--------|-----------|------------------|------------------------|
| 1       | VDD    | 3V3       | 3V3 rail         | Mic supply 3.3 V       |
| 2       | GND    | GND       | GND rail         |                        |
| 3       | L/R    | GND       | GND rail         | L/R low → left channel |
| 4       | BCLK   | I2S_BCLK  | Pi pin12 BCLK    | I2S bit clock          |
| 5       | WS     | I2S_WS    | Pi pin35 WS      | I2S word select        |
| 6       | SD     | I2S_SD    | Pi pin38 DIN     | I2S data out           |

----------------------------------------------------------------------
5 · K-type probe M6 (class 1) — R1  (off-board right, at MAX6675 terminal)
----------------------------------------------------------------------
| Pin | Signal | Net   | Connects to            | Notes                  |
|-----|--------|-------|------------------------|------------------------|
| 1   | T+ / P | TC_P  | MAX6675 pin6 TP        | Chromel lead           |
| 2   | T- / N | TC_N  | MAX6675 pin7 TN        | Alumel lead            |

----------------------------------------------------------------------
6 · Decoupling caps C1–C3 100 nF X7R, C4 10 µF  (row E bank on top rails)
----------------------------------------------------------------------
| Ref | Pin | Net   | Connects to | Notes                                |
|-----|-----|-------|-------------|--------------------------------------|
| C1  | 1   | 3V3   | 3V3 rail    | Decouple at module pin               |
| C1  | 2   | GND   | GND rail    |                                      |
| C2  | 1   | 3V3   | 3V3 rail    |                                      |
| C2  | 2   | GND   | GND rail    |                                      |
| C3  | 1   | 3V3   | 3V3 rail    |                                      |
| C3  | 2   | GND   | GND rail    |                                      |
| C4  | 1   | 3V3   | 3V3 rail    | Electrolytic — observe polarity      |
| C4  | 2   | GND   | GND rail    |                                      |

----------------------------------------------------------------------
7 · Pull-up R2 10 kΩ — SPI_CS0  (row J right)
----------------------------------------------------------------------
| Pin | Net       | Connects to                 | Notes                         |
|-----|-----------|-----------------------------|-------------------------------|
| 1   | 3V3       | 3V3 rail                    | Pull-up supply                |
| 2   | SPI_CS0   | MAX6675 CS + Pi CE0         | Holds CS idle-high            |

----------------------------------------------------------------------
8 · Series R4 330 Ω — LED chain  (row J right)
----------------------------------------------------------------------
| Pin | Net   | Connects to           | Notes                       |
|-----|-------|-----------------------|-----------------------------|
| 1   | LED_A | Pi pin36 GPIO16       | LED drive                   |
| 2   | LED_K | LED D1 anode (pin A)  | → LED cathode → GND         |

----------------------------------------------------------------------
9 · Status LED D1  (row J right)
----------------------------------------------------------------------
| Pin | Signal | Net   | Connects to      | Notes        |
|-----|--------|-------|------------------|--------------|
| A   | —      | LED_K | R4 pin2          | Anode        |
| K   | —      | GND   | GND rail         | Cathode      |

----------------------------------------------------------------------
10 · 5 V cooling fan — F1  (off-board right)
----------------------------------------------------------------------
| Pin | Signal | Net | Connects to            | Notes                   |
|-----|--------|-----|------------------------|-------------------------|
| P   | +5V    | 5V  | Pi pin4 5V             | Direct wire, no rail    |
| N   | GND    | GND | GND rail (Z col 58)    | Fan return              |

----------------------------------------------------------------------
11 · Net summary (what each coloured wire carries)
----------------------------------------------------------------------
| Net        | Colour     | Nodes (component:pin)                                         | Kind   |
|------------|------------|---------------------------------------------------------------|--------|
| 3V3        | #c0392b    | U1:1, U1:17, U2:1, U2:3, U3:1, U4:1, C1:1, C2:1, C3:1, C4:1, R2:1 | power  |
| GND        | #34495e    | U1:9,14,25,39,6 · U2:2,4 · U3:2 · U4:2,3 · C1:2–C4:2 · D1:K · F1:N | gnd    |
| 5V         | #e67e22    | U1:4 · F1:P                                                   | power  |
| I2C_SDA    | #1f618d    | U1:3 · U2:5                                                   | signal |
| I2C_SCL    | #5dade2    | U1:5 · U2:6                                                   | signal |
| SPI_SCLK   | #b9770e    | U1:23 · U3:3                                                  | signal |
| SPI_MISO   | #d4ac0d    | U3:5 · U1:21                                                  | signal |
| SPI_CS0    | #a04000    | U1:24 · U3:4 · R2:2                                           | signal |
| I2S_BCLK   | #117a65    | U1:12 · U4:4                                                  | signal |
| I2S_WS     | #1abc9c    | U1:35 · U4:5                                                  | signal |
| I2S_SD     | #0e6655    | U1:38 · U4:6                                                  | signal |
| TC_P       | #8e44ad    | R1:1 · U3:6                                                   | analog |
| TC_N       | #6c3483    | R1:2 · U3:7                                                   | analog |
| LED_A      | #7f8c8d    | U1:36 · R4:1                                                  | signal |
| LED_K      | #7f8c8d    | R4:2 · D1:A                                                   | signal |

----------------------------------------------------------------------
12 · Breadboard placement (where to plug each part)
----------------------------------------------------------------------
| Ref | Part              | Placement                     | Notes                                  |
|-----|-------------------|-------------------------------|----------------------------------------|
| U2  | ADXL345           | row J pin 3                   | pins in row J, body above (rows F–I)   |
| U4  | INMP441           | row J pin 15                  |                                        |
| U3  | MAX6675           | row J pin 23                  | screw terminal faces out (probe lands) |
| C1  | 100 nF            | row E cols 4–5                | on top rails W(3V3)/X(GND)             |
| C2  | 100 nF            | row E cols 7–8                |                                        |
| C3  | 100 nF            | row E cols 10–11              |                                        |
| C4  | 10 µF             | row E cols 13–14              |                                        |
| R2  | 10 kΩ             | row J cols 33–37              | right of MAX6675                       |
| D1  | LED               | row J cols 42–43              |                                        |
| R4  | 330 Ω             | row J cols 45–49              |                                        |
| U1  | Pi 4              | below board, header aligned   | pin 1 near board col 1; GPIO16 at col  |
| R1  | K-type probe      | off-board right (620,101.6)   | T+→TP, T−→TN screw terminals           |
| F1  | 5 V fan           | off-board right (620,195)     | +5V direct from Pi pin4, − to GND rail |

----------------------------------------------------------------------
13 · Assembly order (from Project Book §4.4)
----------------------------------------------------------------------
1. Rails first; meter-check 3.3 V and 5 V before anything is plugged in.
2. U2 only: `i2cdetect -y 1` must show `0x53`.
3. U3 only: ice-point reads 0 ±2 °C and the open-TC flag is 0.
4. U4 only: `arecord -l` shows the mic.
5. If a step fails, stop there — adding the next module hides which one is wrong.

----------------------------------------------------------------------
End of connection table.