/*
 * ============================================================================
   PDM RIG WIRING GUIDE — CONTENT MODULE (EXPANDED EDITION)
   "قم بتوصيل الروبوتdoctor" — Complete interactive educational content
   ============================================================================
   This file contains ALL educational content for the wiring guide:
   - 5 levels with 17 lessons (detailed)
   - Part catalog with real photos, Fritzing artwork, full specs
   - Wire-by-pin connection tables (all 15 nets)
   - Quiz questions (multiple choice, true/false)
   - Comfort-wiring tips, safety warnings, troubleshooting
   - Simulator scenarios
   - Gamification data (XP values, achievements)
   ============================================================================
*/

'use strict';

const CONTENT = {
  meta: {
    title: "Wire the Robot-Doctor Rig",
    subtitle: "Edge Predictive-Maintenance Breadboard — G12 Capstone",
    version: "2.1.0-expanded",
    totalLevels: 5,
    totalLessons: 17,
    fzzFile: "PDM_Predictive_Maintenance.fzz",
    fzzStats: { instances: 14, nets: 15, wires: 166, problems: 0 },
    buildCheck: "44 PASS / 8 WARN / 0 FAIL",
    budgetCeiling: "9,370 EGP",
    plannedSpend: "9,368.25 EGP",
    headroom: "1.75 EGP"
  },

  // ===========================================================================
  // COLOR PALETTE (net colors from design.py / routes.py)
  // ===========================================================================
  COLORS: {
    '3V3':        { hex: '#c0392b', name: '3.3V Power',           emoji: '🔴', category: 'power',   desc: 'Raspberry Pi 3.3V supply for all sensor modules' },
    GND:          { hex: '#34495e', name: 'Ground / Common',      emoji: '⚫', category: 'ground',  desc: 'Common ground return path for all circuits' },
    '5V':         { hex: '#e67e22', name: '5V Fan Power',         emoji: '🟠', category: 'power',   desc: '5V supply for the cooling fan (direct from Pi, no rail)' },
    I2C_SDA:      { hex: '#1f618d', name: 'I2C Data (SDA)',       emoji: '🟦', category: 'signal',  desc: 'I2C data line — ADXL345 to Pi GPIO2' },
    I2C_SCL:      { hex: '#5dade2', name: 'I2C Clock (SCL)',      emoji: '🔵', category: 'signal',  desc: 'I2C clock line — ADXL345 to Pi GPIO3' },
    SPI_SCLK:     { hex: '#b9770e', name: 'SPI Clock (SCK)',      emoji: '🟤', category: 'signal',  desc: 'SPI clock — MAX6675 to Pi GPIO11' },
    SPI_MISO:     { hex: '#d4ac0d', name: 'SPI Data In (MISO)',   emoji: '🟡', category: 'signal',  desc: 'SPI data out from MAX6675 to Pi GPIO9' },
    SPI_CS0:      { hex: '#a04000', name: 'SPI Chip-Select',      emoji: '🟫', category: 'signal',  desc: 'SPI chip-select — MAX6675 to Pi GPIO8' },
    I2S_BCLK:     { hex: '#117a65', name: 'I2S Bit Clock',        emoji: '🟢', category: 'signal',  desc: 'I2S bit clock — INMP441 to Pi GPIO18' },
    I2S_WS:       { hex: '#1abc9c', name: 'I2S Word-Select',      emoji: '🟣', category: 'signal',  desc: 'I2S word select / LRCLK — INMP441 to Pi GPIO19' },
    I2S_SD:       { hex: '#0e6655', name: 'I2S Data Out (SD)',    emoji: '🟢', category: 'signal',  desc: 'I2S data out — INMP441 to Pi GPIO20' },
    TC_P:         { hex: '#8e44ad', name: 'Thermocouple +',       emoji: '🟪', category: 'analog',  desc: 'K-type thermocouple positive (chromel) lead' },
    TC_N:         { hex: '#6c3483', name: 'Thermocouple −',       emoji: '🟣', category: 'analog',  desc: 'K-type thermocouple negative (alumel) lead' },
    LED_A:        { hex: '#7f8c8d', name: 'LED Anode Drive',      emoji: '⚪', category: 'signal',  desc: 'Status LED anode drive from Pi GPIO16' },
    LED_K:        { hex: '#7f8c8d', name: 'LED Cathode → GND',    emoji: '⚪', category: 'signal',  desc: 'Status LED cathode to ground' },
    '3V3→GND':    { hex: '#c0392b', name: '3.3V→GND (decouple)',  emoji: '🔴', category: 'power',   desc: 'Decoupling cap between 3V3 and GND' },
    '3V3→SPI_CS0':{ hex: '#c0392b', name: '3.3V Pull-up',         emoji: '🔴', category: 'power',   desc: 'R2 10 kΩ pull-up to 3V3 for MAX6675 CS' }
  },

  // ===========================================================================
  // PART CATALOG — real photos + Fritzing artwork + full specs
  // ===========================================================================
  PARTS: {
    pi4b: {
      id: 'pi4b', name: 'Raspberry Pi 4 Model B 4GB', role: 'brain',
      emoji: '🍓', mascot: '🧠',
      photo: 'https://upload.wikimedia.org/wikipedia/commons/thumb/d/d3/Raspberry-Pi-4_Model_B_%28TOP%29.jpg/640px-Raspberry-Pi-4_Model_B_%28TOP%29.jpg',
      fritzing: 'circuit/fzz/parts/pi4b/breadboard/pi4b_breadboard_raspberry-pi-4B_1_breadboard.svg',
      icon: 'circuit/fzz/parts/pi4b/icon/pi4b_icon_raspberry-pi-4B_1_icon.svg',
      pcb: 'circuit/fzz/parts/pi4b/pcb/pi4b_pcb_raspberry-pi-4B_1_pcb.svg',
      schematic: 'circuit/fzz/parts/pi4b/schematic/pi4b_schematic_raspberry-pi-4B_1_schematic.svg',
      pins: 40,
      description: 'The brain of the rig. A 1.5 GHz ARM Cortex-A72 quad-core with 4 GB RAM. Reads all sensors via I2C/SPI/I2S, runs the SPC + RandomForest AI, hosts the Flask dashboard and local Mosquitto MQTT broker, and mirrors data to Firebase RTDB.',
      power: { '3V3': [1, 17], '5V': [2, 4], 'GND': [6, 9, 14, 20, 25, 30, 34, 39] },
      i2c: { SDA: 3, SCL: 5, name: 'I2C-1' },
      spi: { SCLK: 23, MISO: 21, MOSI: 19, CE0: 24, CE1: 26 },
      i2s: { BCLK: 12, WS: 35, DIN: 38, DOUT: 40 },
      gpio: { LED: 36, available: [7, 11, 13, 15, 16, 18, 22, 31, 32, 33, 35, 36, 37, 38, 40] },
      placement: { row: 'below', col: 'aligned-to-breadboard' },
      tips: 'Pin 1 is bottom-left when USB and Ethernet ports face upward. Odd-numbered pins are on the row nearest the board edge. Even pins on the inner row.',
      warnings: [ 'Never connect 5V to a 3.3V-only sensor pin', 'Always check power with a multimeter before plugging in sensors' ]
    },
    adxl345: {
      id: 'adxl345', name: 'ADXL345 3-Axis Accelerometer', role: 'vibration-sensor',
      emoji: '📳', mascot: '💥',
      photo: 'https://upload.wikimedia.org/wikipedia/commons/thumb/8/8c/ADXL345_accelerometer_sensor_module.jpg/320px-ADXL345_accelerometer_sensor_module.jpg',
      fritzing: 'circuit/fzz/parts/adxl345/breadboard/adxl345_breadboard_ADXL345-BreakoutBoard-v13_breadboard.svg',
      icon: 'circuit/fzz/parts/adxl345/icon/adxl345_icon_ADXL345-BreakoutBoard-v13_breadboard.svg',
      pcb: 'circuit/fzz/parts/adxl345/pcb/adxl345_pcb_ADXL345-BreakoutBoard-v13_pcb.svg',
      schematic: 'circuit/fzz/parts/adxl345/schematic/adxl345_schematic_ADXL345-BreakoutBoard-v13_schematic.svg',
      pins: 6,
      description: 'A small, thin, low-power, 3-axis accelerometer with high resolution (13-bit) measurement at up to ±16 g. Used here to feel motor vibration. Digital output via I2C at address 0x53 (SDO grounded) or 0x1D (SDO high).',
      pinsMap: { VCC:1, GND:2, CS:3, SDO:4, SDA:5, SCL:6 },
      placement: { row: 'J', col: 3 },
      specs: { voltage: '2.0–3.6 V', interface: 'I2C / SPI', address: '0x53 (SDO=GND) or 0x1D (SDO=3V3)', range: '±2/±4/±8/±16 g selectable', odr: '0.10–3200 Hz' },
      tips: 'CS→3V3 and SDO→GND enable I2C mode at address 0x53. Mount the module securely to the motor so vibration transfers well.',
      warnings: [ 'CS must be high for I2C mode', 'SDO low selects 0x53; high selects 0x1D' ]
    },
    max6675: {
      id: 'max6675', name: 'MAX6675 K-Type Thermocouple Amplifier', role: 'heat-sensor',
      emoji: '🌡️', mascot: '🔥',
      photo: 'https://upload.wikimedia.org/wikipedia/commons/thumb/6/6b/MAX6675_thermocouple_module.jpg/320px-MAX6675_thermocouple_module.jpg',
      fritzing: 'circuit/fzz/parts/max6675/breadboard/max6675.svg',
      icon: 'circuit/fzz/parts/max6675/icon/max6675_icon.svg',
      pcb: 'circuit/fzz/parts/max6675/pcb/max6675.svg',
      schematic: 'circuit/fzz/parts/max6675/schematic/max6675.svg',
      pins: 7,
      description: 'Cold-junction-compensated K-type thermocouple-to-digital converter with 12-bit resolution (0.25 °C/LSB). SPI-compatible read-only interface. Measures −200 to +700 °C with the cold junction compensated internally.',
      pinsMap: { VCC:1, GND:2, SCK:3, CS:4, SO:5, TP:6, TN:7 },
      placement: { row: 'J', col: 23 },
      specs: { voltage: '3.0–3.6 V (module regulator)', interface: 'SPI read-only', resolution: '0.25 °C', range: '−200 to +700 °C', conversion: '~220 ms' },
      tips: 'Keep the module ≥15 cm from the Pi so enclosure air heat does not falsely raise the cold-junction reading. Use a class-1 K-type probe.',
      warnings: [ 'Class-2 probe (±2.5 °C) alone breaks the ±2.0 °C requirement', 'Mount module ≥15 cm from Pi', 'Allow 5 min warm-up before calibrating' ]
    },
    inmp441: {
      id: 'inmp441', name: 'INMP441 I2S MEMS Microphone', role: 'sound-sensor',
      emoji: '🎤', mascot: '👂',
      photo: 'https://upload.wikimedia.org/wikipedia/commons/thumb/3/3a/INMP441_MEMS_microphone_module.jpg/320px-INMP441_MEMS_microphone_module.jpg',
      fritzing: 'circuit/fzz/parts/inmp441/breadboard/inmp441.svg',
      icon: 'circuit/fzz/parts/inmp441/icon/inmp441_icon.svg',
      pcb: 'circuit/fzz/parts/inmp441/pcb/inmp441.svg',
      schematic: 'circuit/fzz/parts/inmp441/schematic/inmp441.svg',
      pins: 6,
      description: 'A low-power, low-noise, omnidirectional MEMS microphone with I2S digital output. Ideal for listening to motor bearing and gearbox anomalies. Outputs left channel when L/R is grounded.',
      pinsMap: { VDD:1, GND:2, LR:3, BCLK:4, WS:5, SD:6 },
      placement: { row: 'J', col: 15 },
      specs: { voltage: '1.6–3.6 V', interface: 'I2S', sensitivity: '−26 dBFS', SNR: '61 dBA', sampleRate: 'up to 48 kHz' },
      tips: 'L/R→GND selects the left channel. Keep I2S wires (BCLK, WS, SD) short and away from the 5V fan wire to avoid digital noise coupling.',
      warnings: [ 'I2S timing must be clean', 'Keep away from 5V fan wire' ]
    },
    kprobe: {
      id: 'kprobe', name: 'K-Type Thermocouple Probe (Class 1)', role: 'probe',
      emoji: '🔌', mascot: '🌡️',
      photo: 'https://upload.wikimedia.org/wikipedia/commons/thumb/e/e6/K-type_thermocouple_probe.jpg/320px-K-type_thermocouple_probe.jpg',
      fritzing: 'circuit/fzz/parts/kprobe/breadboard/kprobe.svg',
      icon: 'circuit/fzz/parts/kprobe/icon/kprobe_icon.svg',
      pcb: 'circuit/fzz/parts/kprobe/pcb/kprobe.svg',
      schematic: 'circuit/fzz/parts/kprobe/schematic/kprobe.svg',
      pins: 2,
      description: 'A K-type thermocouple consists of two dissimilar metal wires: chromel (nickel-chromium, positive) and alumel (nickel-aluminium, negative). Class 1 tolerance: ±1.5 °C or 0.004|t|, whichever is greater.',
      pinsMap: { Tplus:1, Tminus:2 },
      placement: { row: 'offboard', col: 'right' },
      specs: { type: 'K (chromel–alumel)', class: '1 (±1.5 °C or 0.004|t|)', range: '−40 to +1000 °C typical', junction: 'grounded/ungrounded' },
      tips: 'Push chromel (T+) into MAX6675 TP (pin 6) and alumel (T−) into TN (pin 7) on the green screw terminal. Reversed leads give negative readings.',
      warnings: [ 'Class-2 probe (±2.5 °C) breaks the ±2.0 °C goal', 'Reverse leads = negative temperature readings' ]
    },
    fan: {
      id: 'fan', name: '5V Cooling Fan', role: 'actuator',
      emoji: '🌀', mascot: '❄️',
      photo: 'https://upload.wikimedia.org/wikipedia/commons/thumb/8/8d/5V_cooling_fan.jpg/320px-5V_cooling_fan.jpg',
      fritzing: 'circuit/fzz/parts/fan5v/breadboard/fan5v.svg',
      icon: 'circuit/fzz/parts/fan5v/icon/fan5v_icon.svg',
      pcb: 'circuit/fzz/parts/fan5v/pcb/fan5v.svg',
      schematic: 'circuit/fzz/parts/fan5v/schematic/fan5v.svg',
      pins: 2,
      description: 'A small 5 V DC cooling fan that activates when the MAX6675 reports high temperature. Prevents the Pi and enclosure from thermal throttling.',
      pinsMap: { plus:1, minus:2 },
      placement: { row: 'offboard', col: 'right' },
      specs: { voltage: '5 V DC', current: '~0.2 A', power: '~1.0 W', function: 'Cools Pi + enclosure' },
      tips: 'Direct 5 V from Pi pin 4 (orange wire) — no rail detour. Return via GND rail column 58 (dark gray wire). Mount to blow air across the Pi.',
      warnings: [ 'Do not exceed 5 V on fan', 'Fan − returns to GND rail, not directly to Pi' ]
    },
    caps: {
      id: 'caps', name: 'Decoupling Capacitors (C1–C4)', role: 'passive',
      emoji: '🔋', mascot: '⚡',
      photo: 'https://upload.wikimedia.org/wikipedia/commons/thumb/4/4c/Ceramic_capacitor_100nF.jpg/320px-Ceramic_capacitor_100nF.jpg',
      fritzing: 'circuit/fzz/parts/cap_cer/breadboard/cap_cer_breadboard_ceramic_capacitor_blue_leg.svg',
      icon: 'circuit/fzz/parts/cap_cer/icon/cap_cer_icon_ceramic_capacitor_blue_icon.svg',
      pcb: 'circuit/fzz/parts/cap_cer/pcb/cap_cer_pcb_capacitor_ceramic_100mil.svg',
      schematic: 'circuit/fzz/parts/cap_cer/schematic/cap_cer_schematic_capacitor.svg',
      pins: 2,
      description: 'C1–C3 are 100 nF X7R ceramic capacitors. C4 is a 10 µF electrolytic capacitor. They act as small local energy reservoirs to keep power supply voltage steady when sensors draw sudden current.',
      pinsMap: { pin1:1, pin2:2 },
      placement: { row: 'E', cols: [4,5,7,8,10,11,13,14] },
      specs: { C1: '100 nF X7R ceramic', C2: '100 nF X7R ceramic', C3: '100 nF X7R ceramic', C4: '10 µF electrolytic' },
      tips: 'Solder caps directly at module pins. C4 is polarized — long leg to 3V3, short leg to GND. Labels sit half a pitch left of each cap body so tap lanes never cross text.',
      warnings: [ 'C4 is polarized — observe + and −', 'Labels must stay clear of wire tap lanes' ]
    },
    r2: {
      id: 'r2', name: 'R2 — 10 kΩ Pull-Up Resistor', role: 'passive',
      emoji: '🔧', mascot: '➰',
      photo: 'https://upload.wikimedia.org/wikipedia/commons/thumb/1/1e/Resistor_10k.jpg/320px-Resistor_10k.jpg',
      fritzing: 'circuit/fzz/parts/resistor/breadboard/resistor_breadboard_resistor_220.svg',
      icon: 'circuit/fzz/parts/resistor/icon/resistor_icon_resistor_icon_220.svg',
      pcb: 'circuit/fzz/parts/resistor/pcb/resistor_pcb_axial_lay_2_400mil_pcb.svg',
      schematic: 'circuit/fzz/parts/resistor/schematic/resistor_schematic_resistor.svg',
      pins: 2,
      description: 'A 10 kΩ resistor that pulls the MAX6675 chip-select line up to 3.3 V when the Pi is not actively selecting the sensor. This keeps CS idle-high so the MAX6675 stays quiet on the SPI bus.',
      pinsMap: { pin1:1, pin2:2 },
      placement: { row: 'J', cols: [33, 37] },
      specs: { value: '10 kΩ', tolerance: '±1% or ±5%', power: '1/4 W' },
      tips: 'R2 pin1 → 3V3 rail, pin2 → MAX6675 CS + Pi CE0. Resistors are symmetric — orientation does not matter electrically.',
      warnings: [ 'Without R2, CS may float and cause false SPI triggers' ]
    },
    r4: {
      id: 'r4', name: 'R4 — 330 Ω LED Series Resistor', role: 'passive',
      emoji: '🔧', mascot: '➰',
      photo: 'https://upload.wikimedia.org/wikipedia/commons/thumb/1/1e/Resistor_330R.jpg/320px-Resistor_330R.jpg',
      fritzing: 'circuit/fzz/parts/resistor/breadboard/resistor_breadboard_resistor_220.svg',
      icon: 'circuit/fzz/parts/resistor/icon/resistor_icon_resistor_icon_220.svg',
      pcb: 'circuit/fzz/parts/resistor/pcb/resistor_pcb_axial_lay_2_400mil_pcb.svg',
      schematic: 'circuit/fzz/parts/resistor/schematic/resistor_schematic_resistor.svg',
      pins: 2,
      description: 'A 330 Ω current-limiting resistor in series with the status LED. Protects the LED from excessive current when Pi GPIO16 drives it high.',
      pinsMap: { pin1:1, pin2:2 },
      placement: { row: 'J', cols: [45, 49] },
      specs: { value: '330 Ω', tolerance: '±5%', power: '1/4 W' },
      tips: 'R4 pin1 → Pi GPIO16 (pin 36), pin2 → LED anode. Resistors are symmetric.',
      warnings: [ 'Without R4, the LED may burn out from excess current' ]
    },
    led: {
      id: 'led', name: 'D1 — Status LED', role: 'actuator',
      emoji: '💡', mascot: '✨',
      photo: 'https://upload.wikimedia.org/wikipedia/commons/thumb/5/54/Red_LED_5mm.jpg/320px-Red_LED_5mm.jpg',
      fritzing: 'circuit/fzz/parts/led5/breadboard/led5_breadboard_LED-5mm-red-leg.svg',
      icon: 'circuit/fzz/parts/led5/icon/led5_icon_LED-red-5mmicon.svg',
      pcb: 'circuit/fzz/parts/led5/pcb/led5_pcb_LED-generic-5mm_6852162_005.svg',
      schematic: 'circuit/fzz/parts/led5/schematic/led_schematic_led.svg',
      pins: 2,
      description: 'A small red status LED. Lights up when the Pi drives GPIO16 high, indicating all systems OK or a status condition.',
      pinsMap: { anode:1, cathode:2 },
      placement: { row: 'J', cols: [42, 43] },
      specs: { color: 'Red', forwardVoltage: '~1.8–2.2 V', current: '~10–20 mA' },
      tips: 'Anode (+) is the longer leg. Cathode (−) has the flat side on the LED rim and connects to GND. LED chain: Pi 36 → R4 → LED anode → LED cathode → GND.',
      warnings: [ 'Anode = longer leg, cathode = shorter leg with flat rim', 'Always use R4 in series — never drive LED directly from GPIO' ]
    },
    breadboard: {
      id: 'breadboard', name: '840-Point Breadboard', role: 'canvas',
      emoji: '🧱', mascot: '📐',
      photo: 'https://upload.wikimedia.org/wikipedia/commons/thumb/0/0e/Breadboard_840_points.jpg/320px-Breadboard_840_points.jpg',
      fritzing: 'circuit/fzz/parts/bb840/breadboard/bb840_breadboard_breadboard.svg',
      icon: 'circuit/fzz/parts/bb840/icon/bb840_icon_breadboardicon.svg',
      pcb: 'circuit/fzz/parts/bb840/breadboard/bb840_pcb_breadboard.svg',
      schematic: 'circuit/fzz/parts/bb840/breadboard/bb840_schematic_breadboard.svg',
      pins: 840,
      description: 'A solderless prototyping board with 840 tie-points. Rows A–J run horizontally, columns 1–60 run vertically. The central gap separates left and right halves for DIP ICs. Four power rails run along the top and bottom edges.',
      pinsMap: {},
      placement: { row: 'center', col: 'all' },
      specs: { rows: 'A–J (10 rows)', columns: '1–60', tiePoints: '840', rails: 'W/X top (3V3/GND), Y/Z bottom (5V/GND)' },
      tips: 'Wires connect only where they end in a numbered hole — crossings are NOT connections. Never run wires over printed row letters or column numbers.',
      warnings: [ 'Wires over labels violate comfort-wiring rules', 'A wire crossing is not a connection' ]
    }
  },

  // ===========================================================================
  // LEVELS & LESSONS (17 lessons across 5 levels)
  // ===========================================================================
  LEVELS: [
    {
      id: 1, title: 'Power Rails', subtitle: '3V3 & GND — The Foundation',
      mascot: '🔌', emoji: '⚡', theme: { uc: '#FF5C8A', ucd: '#D93B69', ue: '🔌' },
      xp: 40, estimated: '8 min',
      description: 'Lay the power foundation. Every sensor needs 3.3V and GND before anything else works. Get this wrong and nothing else matters.',
      icon: '⚡',
      lessons: [
        {
          id: 'l1-1', level: 1, title: 'Meet the Breadboard', type: 'tour',
          emoji: '🧱',
          goal: 'Learn where rows A–J and columns 1–60 live, and what the power rails are.',
          content: `The breadboard is your canvas. <strong>Rows A–J</strong> run horizontally (10 rows).
          <strong>Columns 1–60</strong> run vertically (60 columns). The central gap separates the left
          and right halves — useful for straddling DIP ICs. Four power rails run along the edges:
          <strong>W</strong> (top-left, 3V3), <strong>X</strong> (top-left, GND),
          <strong>Y</strong> (top-right, 3V3), <strong>Z</strong> (bottom-right, GND for fan).
          Bottom rail strips carry 5V and GND for the fan.`,
          wires: [
            { from: 'Pi pin 1', net: '3V3', to: 'Row W col 1 (top-left 3V3 rail)', color: '#c0392b' },
            { from: 'Pi pin 9', net: 'GND', to: 'Row X col 3 (top-left GND rail)', color: '#34495e' },
            { from: 'Pi pin 17', net: '3V3', to: 'Row Y col 29 (top-right 3V3 rail)', color: '#c0392b' },
            { from: 'Pi pin 14', net: 'GND', to: 'Row Z col 27 (bottom-right GND rail)', color: '#34495e' }
          ],
          tips: 'Bridge the rails across the middle gap (columns 29→32) so both halves of the board get 3V3 and GND. The bottom-number labels (inside the wire exit band) were removed from the export so no wire crosses printed text.',
          quiz: [
            { q: 'Which top-rail row carries 3V3 on the left?', a: 'W', options: ['W', 'X', 'Y', 'Z'], hint: 'W = 3V3, X = GND on the top-left rail' },
            { q: 'Which Pi pin gives 5V to the fan?', a: 'Pin 4', options: ['Pin 1', 'Pin 4', 'Pin 9', 'Pin 17'], hint: 'Pin 4 is the 5V power output' },
            { q: 'True or false: wires may cross over printed row letters.', a: 'False', options: ['True', 'False'], hint: 'Comfort-wiring rule: no wires over labels' },
            { q: 'What is removed from the wire-exit band to clear collisions?', a: 'Bottom column numbers', options: ['Top numbers', 'Bottom column numbers', 'Row letters', 'Wire colours'], hint: 'Bottom numbers sit where wires exit' }
          ]
        },
        {
          id: 'l1-2', level: 1, title: 'Fan Power & Return', type: 'wire',
          emoji: '🌀',
          goal: 'Wire the fan: 5V direct from Pi, GND return to the rail.',
          content: 'The fan does NOT use a power rail — it gets 5V straight from Pi pin 4 (orange wire) and returns via GND rail column 58 (dark gray wire). This is a direct point-to-point connection, the shortest safe path.',
          wires: [
            { from: 'Pi pin 4', net: '5V', to: 'Fan + (off-board right)', color: '#e67e22' },
            { from: 'Fan −', net: 'GND', to: 'GND rail column 58', color: '#34495e' }
          ],
          tips: 'Direct wire = no detour through other parts. Keep the fan wire away from the I2S microphone lines to avoid noise coupling.',
          quiz: [
            { q: 'Does the fan use the GND rail?', a: 'Yes', options: ['Yes', 'No'], hint: 'Fan − returns to GND rail column 58' },
            { q: 'What color is the 5V fan wire?', a: 'Orange (#e67e22)', options: ['Red', 'Orange (#e67e22)', 'Dark gray', 'Purple'], hint: '5V is orange in our net color key' },
            { q: 'Why no rail detour for the fan?', a: 'Shortest safe path', options: ['Looks nicer', 'Shortest safe path', 'More parts', 'Tradition'], hint: 'Direct connection reduces voltage drop and noise' }
          ]
        }
      ]
    },
    {
      id: 2, title: 'ADXL345 Shake Sensor', subtitle: 'I2C Vibration Sensor — Row J, Pin 3',
      mascot: '📳', emoji: '💥', theme: { uc: '#7C5CFF', ucd: '#5B3FE0', ue: '📳' },
      xp: 40, estimated: '12 min',
      description: 'Connect the 3-axis accelerometer that feels motor vibration. Digital I2C interface at address 0x53.',
      icon: '📳',
      lessons: [
        {
          id: 'l2-1', level: 2, title: 'ADXL345 Pin-by-Pin', type: 'wire',
          emoji: '📳',
          goal: 'Connect all 6 ADXL345 pins correctly.',
          content: `Plug the ADXL345 at <strong>row J, pin 3</strong> with the body above (rows F–I).
          <strong>CS→3V3</strong> and <strong>SDO→GND</strong> put the chip in I2C mode at address 0x53.
          <strong>SDA→Pi pin 3</strong>, <strong>SCL→Pi pin 5</strong>.
          VCC→3V3, GND→GND rail.`,
          wires: [
            { from: 'ADXL345 VCC', net: '3V3', to: '3V3 rail', color: '#c0392b' },
            { from: 'ADXL345 GND', net: 'GND', to: 'GND rail', color: '#34495e' },
            { from: 'ADXL345 CS', net: '3V3', to: '3V3 rail (I2C mode)', color: '#c0392b' },
            { from: 'ADXL345 SDO', net: 'GND', to: 'GND rail (address 0x53)', color: '#34495e' },
            { from: 'ADXL345 SDA', net: 'I2C_SDA', to: 'Pi pin 3', color: '#1f618d' },
            { from: 'ADXL345 SCL', net: 'I2C_SCL', to: 'Pi pin 5', color: '#5dade2' }
          ],
          tips: 'CS high + SDO low = I2C at 0x53. If SDO is high, address becomes 0x1D. Never swap SDA and SCL — I2C will not work.',
          quiz: [
            { q: 'What I2C address does ADXL345 use here?', a: '0x53', options: ['0x1A', '0x53', '0x68', '0x77'], hint: 'SDO→GND sets address 0x53' },
            { q: 'Which Pi pin is I2C data (SDA)?', a: 'Pin 3', options: ['Pin 3', 'Pin 5', 'Pin 12', 'Pin 23'], hint: 'GPIO2 / SDA1 is pin 3' },
            { q: 'Which Pi pin is I2C clock (SCL)?', a: 'Pin 5', options: ['Pin 3', 'Pin 5', 'Pin 7', 'Pin 9'], hint: 'GPIO3 / SCL1 is pin 5' },
            { q: 'What happens if SDO is tied to 3V3 instead of GND?', a: 'Address becomes 0x1D', options: ['No change', 'Address becomes 0x1D', 'Sensor breaks', 'I2C stops'], hint: 'SDO high = 0x1D, SDO low = 0x53' }
          ]
        },
        {
          id: 'l2-2', level: 2, title: 'I2C Bus Test', type: 'quiz',
          emoji: '🔍',
          goal: 'Verify the ADXL345 is detected on the I2C bus.',
          content: 'After wiring, run <code>i2cdetect -y 1</code> on the Raspberry Pi. You must see <code>0x53</code> appear in the bus scan table. If you see nothing, check that CS→3V3 and SDO→GND are correct, and that SDA/SCL are not swapped.',
          quiz: [
            { q: 'Command to scan the I2C bus?', a: 'i2cdetect -y 1', options: ['i2cdetect -y 1', 'i2cscan', 'ls /dev/i2c', 'modprobe i2c-dev'], hint: 'Standard Linux I2C detection tool' },
            { q: 'Expected I2C address for ADXL345?', a: '0x53', options: ['0x53', '0x50', '0x68', '0x1C'], hint: 'SDO tied to GND selects 0x53' },
            { q: 'What if i2cdetect shows nothing?', a: 'Check wiring and power', options: ['Ignore it', 'Check wiring and power', 'Replace the Pi', 'Use a different sensor'], hint: 'No response means power or connection problem' }
          ]
        }
      ]
    },
    {
      id: 3, title: 'MAX6675 + K-Probe', subtitle: 'Heat Sensor + Thermocouple — Row J, Pin 23',
      mascot: '🌡️', emoji: '🔥', theme: { uc: '#FF5C8A', ucd: '#D93B69', ue: '🌡️' },
      xp: 40, estimated: '12 min',
      description: 'Connect the thermocouple amplifier and class-1 probe. SPI interface plus analog thermocouple leads.',
      icon: '🌡️',
      lessons: [
        {
          id: 'l3-1', level: 3, title: 'MAX6675 SPI Wiring', type: 'wire',
          emoji: '🌡️',
          goal: 'Wire SCK, CS, SO, VCC, GND to the Pi and rails.',
          content: `Plug MAX6675 at <strong>row J, pin 23</strong>. Keep the module <strong>≥15 cm from the Pi</strong>
          so enclosure air heat does not falsely raise the cold-junction reading (the MAX6675 die IS the cold junction).
          SCK→Pi pin 23, CS→Pi pin 24 (+ R2 10 kΩ pull-up to 3V3), SO→Pi pin 21. VCC→3V3, GND→GND.`,
          wires: [
            { from: 'MAX6675 VCC', net: '3V3', to: '3V3 rail', color: '#c0392b' },
            { from: 'MAX6675 GND', net: 'GND', to: 'GND rail', color: '#34495e' },
            { from: 'MAX6675 SCK', net: 'SPI_SCLK', to: 'Pi pin 23', color: '#b9770e' },
            { from: 'MAX6675 CS', net: 'SPI_CS0', to: 'Pi pin 24 + R2 pull-up', color: '#a04000' },
            { from: 'MAX6675 SO', net: 'SPI_MISO', to: 'Pi pin 21', color: '#d4ac0d' }
          ],
          tips: 'R2 (10 kΩ) holds chip-select idle-high so the MAX6675 stays quiet on the SPI bus until the Pi selects it. MOSI (Pi pin 19) is unused because MAX6675 is read-only.',
          quiz: [
            { q: 'Why keep MAX6675 ≥15 cm from the Pi?', a: 'Box heat fakes temperature rise', options: ['Looks nicer', 'Box heat fakes temperature rise', 'Fan blows on it', 'Cable too short'], hint: 'The MAX6675 die IS the cold junction' },
            { q: 'What does R2 (10 kΩ) do?', a: 'Pulls CS idle-high', options: ['Powers the fan', 'Pulls CS idle-high', 'Reads temperature', 'Grounds SO'], hint: 'Pull-up keeps MAX6675 quiet on SPI bus' },
            { q: 'Which Pi pin is unused (MOSI)?', a: 'Pin 19', options: ['Pin 19', 'Pin 21', 'Pin 23', 'Pin 24'], hint: 'MAX6675 is read-only, so MOSI is not needed' }
          ]
        },
        {
          id: 'l3-2', level: 3, title: 'K-Type Probe Connection', type: 'wire',
          emoji: '🔌',
          goal: 'Connect chromel (+) and alumel (−) to the green screw terminal.',
          content: `The K-type probe has two metal wires: <strong>chromel (T+ / nickel-chromium)</strong> and
          <strong>alumel (T− / nickel-aluminium)</strong>. Push T+ into MAX6675 <strong>TP</strong> (pin 6)
          and T− into <strong>TN</strong> (pin 7) on the green screw terminal.
          <strong>Must be CLASS 1 probe</strong> (±1.5 °C or 0.004|t|), NOT class 2 (±2.5 °C).`,
          wires: [
            { from: 'Probe T+ / chromel', net: 'TC_P', to: 'MAX6675 TP (pin 6)', color: '#8e44ad' },
            { from: 'Probe T− / alumel', net: 'TC_N', to: 'MAX6675 TN (pin 7)', color: '#6c3483' }
          ],
          tips: 'TC_N drops to y=128.5 (between printed G and H row letters) so it never runs through the "G" label. Reversed leads give negative temperature readings.',
          quiz: [
            { q: 'Which probe wire goes to TP?', a: 'T+ / chromel (+)', options: ['T− / alumel (−)', 'T+ / chromel (+)', 'Either one', 'Neither'], hint: 'TP = Thermocouple Positive' },
            { q: 'Class-1 probe tolerance?', a: '±1.5 °C', options: ['±1.0 °C', '±1.5 °C', '±2.5 °C', '±5.0 °C'], hint: 'Class 1 is tighter than class 2' },
            { q: 'What if leads are reversed?', a: 'Negative temperature reading', options: ['No reading', 'Negative temperature reading', 'Sensor burns out', 'Pi reboots'], hint: 'T+ and T− swapped = inverted signal' }
          ]
        }
      ]
    },
    {
      id: 4, title: 'INMP441 Microphone', subtitle: 'I2S MEMS Mic — Row J, Pin 15',
      mascot: '🎤', emoji: '👂', theme: { uc: '#7C5CFF', ucd: '#5B3FE0', ue: '🎤' },
      xp: 40, estimated: '10 min',
      description: 'Connect the digital microphone that listens for motor bearing and gearbox anomalies. I2S digital output, left channel.',
      icon: '🎤',
      lessons: [
        {
          id: 'l4-1', level: 4, title: 'INMP441 I2S Wiring', type: 'wire',
          emoji: '🎤',
          goal: 'Wire VDD, GND, L/R, BCLK, WS, SD to Pi and rails.',
          content: `Plug INMP441 at <strong>row J, pin 15</strong>.
          <strong>L/R→GND</strong> selects the left channel.
          <strong>BCLK→Pi pin 12</strong> (GPIO18 / PCM_CLK),
          <strong>WS→Pi pin 35</strong> (GPIO19 / PCM_FS),
          <strong>SD→Pi pin 38</strong> (GPIO20 / PCM_DIN).
          VDD→3V3, GND→GND rail.`,
          wires: [
            { from: 'INMP441 VDD', net: '3V3', to: '3V3 rail', color: '#c0392b' },
            { from: 'INMP441 GND', net: 'GND', to: 'GND rail', color: '#34495e' },
            { from: 'INMP441 L/R', net: 'GND', to: 'GND rail (left channel)', color: '#34495e' },
            { from: 'INMP441 BCLK', net: 'I2S_BCLK', to: 'Pi pin 12', color: '#117a65' },
            { from: 'INMP441 WS', net: 'I2S_WS', to: 'Pi pin 35', color: '#1abc9c' },
            { from: 'INMP441 SD', net: 'I2S_SD', to: 'Pi pin 38', color: '#0e6655' }
          ],
          tips: 'I2S needs clean timing. Keep BCLK, WS, SD short and away from the 5V fan wire to prevent digital noise coupling into the audio signal.',
          quiz: [
            { q: 'Which Pi pin is I2S data IN (SD)?', a: 'Pin 38', options: ['Pin 12', 'Pin 35', 'Pin 38', 'Pin 21'], hint: 'GPIO20 / PCM_DIN is pin 38' },
            { q: 'L/R → GND selects which channel?', a: 'Left', options: ['Left', 'Right', 'Both', 'Neither'], hint: 'L/R low = left channel selected' },
            { q: 'Why keep I2S wires away from fan wire?', a: 'Prevent digital noise coupling', options: ['Looks nicer', 'Prevent noise coupling', 'More room', 'Tradition'], hint: 'Fan motor noise can corrupt I2S timing' }
          ]
        }
      ]
    },
    {
      id: 5, title: 'Caps, Pull-up, LED & Fan', subtitle: 'Decoupling + Status Light — Finish the Rig',
      mascot: '🧩', emoji: '✨', theme: { uc: '#58CC02', ucd: '#429A02', ue: '🧩' },
      xp: 40, estimated: '12 min',
      description: 'Add decoupling capacitors, the R2 pull-up, the LED status chain, and final fan connections.',
      icon: '🧩',
      lessons: [
        {
          id: 'l5-1', level: 5, title: 'Decoupling Capacitors C1–C4', type: 'wire',
          emoji: '🔋',
          goal: 'Place capacitors on row E top rails, labels clear of wires.',
          content: `C1–C3 are 100 nF X7R ceramic capacitors. C4 is a 10 µF electrolytic capacitor.
          Place them in <strong>row E</strong> on the top power rails, one pair near each sensor module.
          Labels sit half a pitch left of each cap body so the tap verticals (left leg −4.5, right leg +4.5)
          never cross the text or cap body.
          C4 is electrolytic — <strong>watch polarity</strong> (long leg to 3V3, short leg to GND).`,
          wires: [
            { from: 'C1 100 nF', net: '3V3→GND', to: 'Row E cols 4–5', color: '#c0392b' },
            { from: 'C2 100 nF', net: '3V3→GND', to: 'Row E cols 7–8', color: '#c0392b' },
            { from: 'C3 100 nF', net: '3V3→GND', to: 'Row E cols 10–11', color: '#c0392b' },
            { from: 'C4 10 µF', net: '3V3→GND', to: 'Row E cols 13–14 (watch polarity)', color: '#c0392b' }
          ],
          tips: 'Decoupling caps act as local energy reservoirs — they keep voltage steady when sensors draw sudden current. Place them as close to module pins as possible.',
          quiz: [
            { q: 'Which capacitor is electrolytic?', a: 'C4 (10 µF)', options: ['C1', 'C2', 'C3', 'C4 (10 µF)'], hint: 'Only C4 is electrolytic — watch polarity' },
            { q: 'Why are cap labels on the left?', a: 'Keep tap lanes clear', options: ['Looks nicer', 'Keep tap lanes clear', 'More room', 'Tradition'], hint: 'Tap verticals must not cross text or cap body' },
            { q: 'C4 polarity?', a: 'Long leg to 3V3, short to GND', options: ['Short to 3V3', 'Long to 3V3', 'Either way', 'Does not matter'], hint: 'Electrolytics are polarized' }
          ]
        },
        {
          id: 'l5-2', level: 5, title: 'LED Chain & Final Integration', type: 'wire',
          emoji: '💡',
          goal: 'Wire Pi GPIO16 → R4 → LED → GND. Final integration check.',
          content: `LED status chain: <strong>Pi pin 36 → R4 (330 Ω) → LED anode → LED cathode → GND</strong>.
          R4 limits current to protect the LED. When the Pi drives GPIO16 high, the LED lights — indicating
          all systems OK or a status condition.
          Final integration check: all rails live, all three sensors detected on their buses, LED responds,
          fan spins when hot.`,
          wires: [
            { from: 'Pi pin 36', net: 'LED_A', to: 'R4 pin 1', color: '#7f8c8d' },
            { from: 'R4 pin 2', net: 'LED_K', to: 'LED anode', color: '#7f8c8d' },
            { from: 'LED cathode', net: 'GND', to: 'GND rail', color: '#34495e' }
          ],
          tips: 'Anode (+) is the longer leg. Cathode (−) has the flat side on the LED rim. Always use R4 — never drive an LED directly from a GPIO pin.',
          quiz: [
            { q: 'Correct LED chain order?', a: 'Pi 36 → R4 → LED → GND', options: ['Pi 36 → LED → R4 → GND', 'Pi 36 → R4 → LED → GND', 'R4 → Pi 36 → LED → GND', 'LED → R4 → Pi 36 → GND'], hint: 'Resistor protects the LED first' },
            { q: 'Final integration check includes?', a: 'All rails live + sensors detected + LED responds', options: ['Just power on', 'All rails live + sensors detected + LED responds', 'Only check fan', 'Only check LED'], hint: 'Test each piece before adding the next' },
            { q: 'What if you drive LED directly from GPIO?', a: 'LED may burn out', options: ['Brighter light', 'LED may burn out', 'No effect', 'Pi reboots'], hint: 'GPIO pins cannot source enough current directly' }
          ]
        }
      ]
    }
  ],

  // ===========================================================================
  // NET SUMMARY (all 15 nets)
  // ===========================================================================
  NETS: [
    { name: '3V3', hex: '#c0392b', kind: 'power', nodes: 'U1:1,17 · U2:1,3 · U3:1 · U4:1 · C1:1,C2:1,C3:1,C4:1 · R2:1', desc: '3.3 V power for all sensor modules' },
    { name: 'GND', hex: '#34495e', kind: 'ground', nodes: 'U1:6,9,14,25,39 · U2:2,4 · U3:2 · U4:2,3 · C1:2–C4:2 · D1:K · F1:N', desc: 'Common ground return' },
    { name: '5V', hex: '#e67e22', kind: 'power', nodes: 'U1:4 · F1:P', desc: '5 V fan power (direct)' },
    { name: 'I2C_SDA', hex: '#1f618d', kind: 'signal', nodes: 'U1:3 · U2:5', desc: 'I2C data — shake sensor' },
    { name: 'I2C_SCL', hex: '#5dade2', kind: 'signal', nodes: 'U1:5 · U2:6', desc: 'I2C clock — shake sensor' },
    { name: 'SPI_SCLK', hex: '#b9770e', kind: 'signal', nodes: 'U1:23 · U3:3', desc: 'SPI clock — heat sensor' },
    { name: 'SPI_MISO', hex: '#d4ac0d', kind: 'signal', nodes: 'U3:5 · U1:21', desc: 'SPI data in — heat sensor' },
    { name: 'SPI_CS0', hex: '#a04000', kind: 'signal', nodes: 'U1:24 · U3:4 · R2:2', desc: 'SPI chip-select + pull-up' },
    { name: 'I2S_BCLK', hex: '#117a65', kind: 'signal', nodes: 'U1:12 · U4:4', desc: 'I2S bit clock — mic' },
    { name: 'I2S_WS', hex: '#1abc9c', kind: 'signal', nodes: 'U1:35 · U4:5', desc: 'I2S word-select — mic' },
    { name: 'I2S_SD', hex: '#0e6655', kind: 'signal', nodes: 'U1:38 · U4:6', desc: 'I2S data out — mic' },
    { name: 'TC_P', hex: '#8e44ad', kind: 'analog', nodes: 'R1:1 · U3:6', desc: 'Thermocouple + (chromel)' },
    { name: 'TC_N', hex: '#6c3483', kind: 'analog', nodes: 'R1:2 · U3:7', desc: 'Thermocouple − (alumel)' },
    { name: 'LED_A', hex: '#7f8c8d', kind: 'signal', nodes: 'U1:36 · R4:1', desc: 'LED anode drive' },
    { name: 'LED_K', hex: '#7f8c8d', kind: 'signal', nodes: 'R4:2 · D1:A', desc: 'LED cathode → GND' }
  ],

  // ===========================================================================
  // TROUBLESHOOTING GUIDE
  // ===========================================================================
  TROUBLESHOOTING: [
    { symptom: 'i2cdetect shows nothing', cause: 'ADXL345 not powered or CS/SDO wrong', fix: 'Check VCC→3V3, GND→GND, CS→3V3, SDO→GND. Verify SDA/SCL not swapped.' },
    { symptom: 'Temperature reads negative', cause: 'Thermocouple leads reversed', fix: 'Swap T+ and T− at the MAX6675 screw terminal.' },
    { symptom: 'Temperature reads ~25 °C when cold', cause: 'Module too close to Pi / box heat', fix: 'Move MAX6675 ≥15 cm from Pi. Allow 5 min warm-up.' },
    { symptom: 'i2cdetect shows 0x1D not 0x53', cause: 'SDO tied to 3V3 instead of GND', fix: 'Move SDO wire from 3V3 rail to GND rail.' },
    { symptom: 'LED does not light', cause: 'R4 missing or LED backwards', fix: 'Check R4 330 Ω is in series. Reverse LED (anode=long leg).' },
    { symptom: 'Fan does not spin', cause: '5V/GND swapped or loose', fix: 'Check fan + → Pi pin 4, fan − → GND rail col 58.' },
    { symptom: 'Mic not detected by arecord', cause: 'I2S wires wrong or noisy', fix: 'Check BCLK→12, WS→35, SD→38. Keep away from 5V fan wire.' },
    { symptom: 'SPI data corrupted', cause: 'CS floating without R2', fix: 'Verify R2 10 kΩ pulls CS up to 3V3.' }
  ],

  // ===========================================================================
  // COMFORT WIRING RULES
  // ===========================================================================
  COMFORT_RULES: [
    { id: 'c1', title: 'No wires over labels', icon: '🚫', desc: 'No wire may cross a printed part label, row letter, or column number.' },
    { id: 'c2', title: 'Bottom numbers removed', icon: '🔢', desc: 'Bottom column numbers (in the wire-exit band) are stripped from the staged board SVG so wires never cross them.' },
    { id: 'c3', title: 'GND bridge at x=604', icon: '🌉', desc: 'The right-edge GND bridge runs at x=604, just outside the board, so row letters A–J stay readable.' },
    { id: 'c4', title: 'TC_N dogleg', icon: '📐', desc: 'TC_N drops to y=128.5 between printed G/H row letters — never runs through the "G" leg-end text.' },
    { id: 'c5', title: 'Cap labels left-shifted', icon: '⬅️', desc: 'Cap labels sit half a pitch left of each cap body; tap lanes run half a pitch outside the cap body/label.' },
    { id: 'c6', title: 'Export shift +5 Y', icon: '📏', desc: 'Fritzing SVG export pads the top by one label row (+5 units); the auditor accounts for this so holes line up with wires exactly.' },
    { id: 'c7', title: 'Community art whitelisted', icon: '🎨', desc: 'ADXL345 community silkscreen INT1/INT2/SDO overlaps are part-design, not authoring errors — whitelisted in the auditor.' }
  ],

  // ===========================================================================
  // ACHIEVEMENTS & GAMIFICATION
  // ===========================================================================
  ACHIEVEMENTS: [
    { id: 'first-wire', name: 'First Connection', icon: '🔌', xp: 10, desc: 'Wire your first pin.' },
    { id: 'rails-master', name: 'Rails Master', icon: '⚡', xp: 25, desc: 'Complete all power rail lessons.' },
    { id: 'i2c-detective', name: 'I2C Detective', icon: '🔍', xp: 25, desc: 'Find 0x53 on the bus.' },
    { id: 'spi-sleuth', name: 'SPI Sleuth', icon: '🕵️', xp: 25, desc: 'Wire SCK, CS, SO correctly.' },
    { id: 'i2s-listener', name: 'I2S Listener', icon: '👂', xp: 25, desc: 'Wire the microphone.' },
    { id: 'thermo-pro', name: 'Thermo Pro', icon: '🌡️', xp: 30, desc: 'Class-1 probe wired.' },
    { id: 'rig-complete', name: 'Rig Complete', icon: '🎉', xp: 100, desc: 'Finish all 5 levels.' },
    { id: 'perfect-score', name: 'Perfect Score', icon: '💯', xp: 50, desc: 'Complete all quizzes with no wrong answers.' },
    { id: 'streak-3', name: '3-Day Streak', icon: '🔥', xp: 30, desc: 'Study 3 days in a row.' },
    { id: 'comfort-wiring', name: 'Comfort Wiring', icon: '🎨', xp: 20, desc: 'No wires over labels.' }
  ],

  // ===========================================================================
  // SIMULATOR SCENARIOS
  // ===========================================================================
  SIMULATOR: {
    levels: {
      1: { name: 'Power Rail Test', checks: ['3V3 live', 'GND live', '5V to fan'], successMsg: 'Rails humming nicely ⚡' },
      2: { name: 'I2C Bus Scan', checks: ['0x53 detected', 'SDA/SCL not swapped'], successMsg: 'Shake sensor talking 📳' },
      3: { name: 'SPI + Thermocouple', checks: ['CS idle-high', 'SO data valid', 'Ice point 0 °C'], successMsg: 'Heat sensor reading 🌡️' },
      4: { name: 'I2S Audio', checks: ['BCLK running', 'WS left channel', 'SD data flowing'], successMsg: 'Mic listening 🎤' },
      5: { name: 'Full Integration', checks: ['All sensors OK', 'LED responds', 'Fan spins'], successMsg: 'Rig fully operational 🎉' }
    }
  },

  // ===========================================================================
  // BUDGET / BOM INFO
  // ===========================================================================
  BOM: {
    ceiling: 9370,
    planned: 9368.25,
    headroom: 1.75,
    realQuotes: 8888.25,
    fanGlandsShrink: 280,
    max6675Allowance: 200,
    max6675MaxQuote: 201.75,
    note: 'MAX6675 is an allowance — must be quoted ≤201.75 EGP or buy in person (−220 shipping).'
  }
};

// Export for use in app.js (if module system available)
if (typeof module !== 'undefined' && module.exports) {
  module.exports = CONTENT;
}
