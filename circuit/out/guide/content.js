/*
 * ============================================================================
   PDM RIG WIRING GUIDE — CONTENT MODULE
   "قم بتوصيل الروبوتdoctor" — Complete interactive educational content
   ============================================================================
   This file contains ALL educational content for the wiring guide:
   - 5 levels with multiple lessons each
   - Part catalog with real photos and Fritzing artwork
   - Wire-by-pin connection tables
   - Quiz questions (multiple choice, true/false, drag-match)
   - Comfort-wiring tips and safety warnings
   - Simulator scenarios
   - Gamification data (XP values, achievements)
   ============================================================================
*/

'use strict';

const CONTENT = {
  meta: {
    title: "Wire the Robot-Doctor Rig",
    subtitle: "Edge Predictive-Maintenance Breadboard — G12 Capstone",
    version: "2.0.0",
    totalLevels: 5,
    totalLessons: 17,
    fzzFile: "PDM_Predictive_Maintenance.fzz",
    fzzStats: { instances: 14, nets: 15, wires: 166, problems: 0 },
    buildCheck: "44 PASS / 8 WARN / 0 FAIL"
  },

  // ---------------------------------------------------------------------------
  // COLOR PALETTE (net colors from design.py)
  // ---------------------------------------------------------------------------
  COLORS: {
    '3V3':        { hex: '#c0392b', name: '3.3V Power',           emoji: '🔴', category: 'power'   },
    GND:          { hex: '#34495e', name: 'Ground / Common',      emoji: '⚫', category: 'ground'  },
    '5V':         { hex: '#e67e22', name: '5V Fan Power',         emoji: '🟠', category: 'power'   },
    I2C_SDA:      { hex: '#1f618d', name: 'I2C Data (SDA)',       emoji: '🟦', category: 'signal'  },
    I2C_SCL:      { hex: '#5dade2', name: 'I2C Clock (SCL)',      emoji: '🔵', category: 'signal'  },
    SPI_SCLK:     { hex: '#b9770e', name: 'SPI Clock (SCK)',      emoji: '🟤', category: 'signal'  },
    SPI_MISO:     { hex: '#d4ac0d', name: 'SPI Data In (MISO)',   emoji: '🟡', category: 'signal'  },
    SPI_CS0:      { hex: '#a04000', name: 'SPI Chip-Select',      emoji: '🟫', category: 'signal'  },
    I2S_BCLK:     { hex: '#117a65', name: 'I2S Bit Clock',        emoji: '🟢', category: 'signal'  },
    I2S_WS:       { hex: '#1abc9c', name: 'I2S Word-Select',      emoji: '🟣', category: 'signal'  },
    I2S_SD:       { hex: '#0e6655', name: 'I2S Data Out (SD)',    emoji: '🟢', category: 'signal'  },
    TC_P:         { hex: '#8e44ad', name: 'Thermocouple +',       emoji: '🟪', category: 'analog'  },
    TC_N:         { hex: '#6c3483', name: 'Thermocouple −',       emoji: '🟣', category: 'analog'  },
    LED_A:        { hex: '#7f8c8d', name: 'LED Anode Drive',      emoji: '⚪', category: 'signal'  },
    LED_K:        { hex: '#7f8c8d', name: 'LED Cathode → GND',    emoji: '⚪', category: 'signal'  },
    '3V3→GND':    { hex: '#c0392b', name: '3.3V→GND (decouple)',  emoji: '🔴', category: 'power'   },
    '3V3→SPI_CS0':{ hex: '#c0392b', name: '3.3V Pull-up',         emoji: '🔴', category: 'power'   },
  },

  // ---------------------------------------------------------------------------
  // PART CATALOG — real photos + Fritzing artwork + specs
  // ---------------------------------------------------------------------------
  PARTS: {
    pi4b: {
      id: 'pi4b', name: 'Raspberry Pi 4 Model B 4GB', role: 'brain',
      emoji: '🍓', mascot: '🧠',
      photo: 'https://upload.wikimedia.org/wikipedia/commons/thumb/d/d3/Raspberry-Pi-4_Model_B_%28TOP%29.jpg/640px-Raspberry-Pi-4_Model_B_%28TOP%29.jpg',
      fritzing: 'circuit/fzz/parts/pi4b/breadboard/pi4b_breadboard_raspberry-pi-4B_1_breadboard.svg',
      icon: 'circuit/fzz/parts/pi4b/icon/pi4b_icon_raspberry-pi-4B_1_icon.svg',
      pins: 40,
      description: 'The brain of the rig. Reads all sensors, runs the AI, hosts Flask + MQTT.',
      power: { '3V3': [1, 17], '5V': [4], 'GND': [6, 9, 14, 20, 25, 39] },
      i2c: { SDA: 3, SCL: 5 },
      spi: { SCLK: 23, MISO: 21, MOSI: 19, CE0: 24 },
      i2s: { BCLK: 12, WS: 35, DIN: 38 },
      gpio: { LED: 36 },
      placement: { row: 'below', col: 'aligned' },
      tips: 'Pin 1 is bottom-left when USB/Ethernet face up. Odd row nearest board edge.'
    },
    adxl345: {
      id: 'adxl345', name: 'ADXL345 3-Axis Accelerometer', role: 'vibration-sensor',
      emoji: '📳', mascot: '💥',
      photo: 'https://upload.wikimedia.org/wikipedia/commons/thumb/8/8c/ADXL345_accelerometer_sensor_module.jpg/320px-ADXL345_accelerometer_sensor_module.jpg',
      fritzing: 'circuit/fzz/parts/adxl345/breadboard/adxl345_breadboard_ADXL345-BreakoutBoard-v13_breadboard.svg',
      icon: 'circuit/fzz/parts/adxl345/icon/adxl345_icon_ADXL345-BreakoutBoard-v13_breadboard.svg',
      pins: 6,
      description: 'Feels if the motor is shaking too much. I2C at address 0x53.',
      pinsMap: { VCC:1, GND:2, CS:3, SDO:4, SDA:5, SCL:6 },
      placement: { row: 'J', col: 3 },
      tips: 'CS→3V3 and SDO→GND enable I2C mode at 0x53.'
    },
    max6675: {
      id: 'max6675', name: 'MAX6675 K-Type Thermocouple', role: 'heat-sensor',
      emoji: '🌡️', mascot: '🔥',
      photo: 'https://upload.wikimedia.org/wikipedia/commons/thumb/6/6b/MAX6675_thermocouple_module.jpg/320px-MAX6675_thermocouple_module.jpg',
      fritzing: 'circuit/fzz/parts/max6675/breadboard/max6675.svg',
      icon: 'circuit/fzz/parts/max6675/icon/max6675_icon.svg',
      pins: 7,
      description: 'Reads temperature via K-type probe. SPI interface, cold-junction inside.',
      pinsMap: { VCC:1, GND:2, SCK:3, CS:4, SO:5, TP:6, TN:7 },
      placement: { row: 'J', col: 23 },
      tips: 'Keep ≥15 cm from Pi. Class-1 probe required for ±2.0 °C.'
    },
    inmp441: {
      id: 'inmp441', name: 'INMP441 I2S MEMS Microphone', role: 'sound-sensor',
      emoji: '🎤', mascot: '👂',
      photo: 'https://upload.wikimedia.org/wikipedia/commons/thumb/3/3a/INMP441_MEMS_microphone_module.jpg/320px-INMP441_MEMS_microphone_module.jpg',
      fritzing: 'circuit/fzz/parts/inmp441/breadboard/inmp441.svg',
      icon: 'circuit/fzz/parts/inmp441/icon/inmp441_icon.svg',
      pins: 6,
      description: 'Listens for funny motor noises. I2S digital output, left channel.',
      pinsMap: { VDD:1, GND:2, LR:3, BCLK:4, WS:5, SD:6 },
      placement: { row: 'J', col: 15 },
      tips: 'L/R→GND selects left channel. BCLK→12, WS→35, SD→38.'
    },
    kprobe: {
      id: 'kprobe', name: 'K-Type Thermocouple Probe (Class 1)', role: 'probe',
      emoji: '🔌', mascot: '🌡️',
      photo: 'https://upload.wikimedia.org/wikipedia/commons/thumb/e/e6/K-type_thermocouple_probe.jpg/320px-K-type_thermocouple_probe.jpg',
      fritzing: 'circuit/fzz/parts/kprobe/breadboard/kprobe.svg',
      icon: 'circuit/fzz/parts/kprobe/icon/kprobe_icon.svg',
      pins: 2,
      description: 'Chromel (+) and Alumel (−) wires. Class 1: ±1.5 °C or 0.004|t|.',
      pinsMap: { Tplus:1, Tminus:2 },
      placement: { row: 'offboard', col: 'right' },
      tips: 'T+ → MAX6675 TP, T− → MAX6675 TN (green screw terminal).'
    },
    fan: {
      id: 'fan', name: '5V Cooling Fan', role: 'actuator',
      emoji: '🌀', mascot: '❄️',
      photo: 'https://upload.wikimedia.org/wikipedia/commons/thumb/8/8d/5V_cooling_fan.jpg/320px-5V_cooling_fan.jpg',
      fritzing: 'circuit/fzz/parts/fan5v/breadboard/fan5v.svg',
      icon: 'circuit/fzz/parts/fan5v/icon/fan5v_icon.svg',
      pins: 2,
      description: 'Cools the Pi and box when temperature rises. 5V direct, no rail.',
      pinsMap: { plus:1, minus:2 },
      placement: { row: 'offboard', col: 'right' },
      tips: 'Plus → Pi pin 4 (5V). Minus → GND rail column 58.'
    },
    caps: {
      id: 'caps', name: 'Decoupling Capacitors (C1–C4)', role: 'passive',
      emoji: '🔋', mascot: '⚡',
      photo: 'https://upload.wikimedia.org/wikipedia/commons/thumb/4/4c/Ceramic_capacitor_100nF.jpg/320px-Ceramic_capacitor_100nF.jpg',
      fritzing: 'circuit/fzz/parts/cap_cer/breadboard/cap_cer_breadboard_ceramic_capacitor_blue_leg.svg',
      icon: 'circuit/fzz/parts/cap_cer/icon/cap_cer_icon_ceramic_capacitor_blue_icon.svg',
      pins: 2,
      description: 'C1–C3: 100 nF X7R. C4: 10 µF electrolytic. Keep power steady.',
      pinsMap: { pin1:1, pin2:2 },
      placement: { row: 'E', cols: [4,5,7,8,10,11,13,14] },
      tips: 'C4 is electrolytic — watch polarity! Labels clear of wires.'
    },
    r2: {
      id: 'r2', name: 'R2 — 10 kΩ Pull-Up', role: 'passive',
      emoji: '🔧', mascot: '➰',
      photo: 'https://upload.wikimedia.org/wikipedia/commons/thumb/1/1e/Resistor_10k.jpg/320px-Resistor_10k.jpg',
      fritzing: 'circuit/fzz/parts/resistor/breadboard/resistor_breadboard_resistor_220.svg',
      icon: 'circuit/fzz/parts/resistor/icon/resistor_icon_resistor_icon_220.svg',
      pins: 2,
      description: 'Holds MAX6675 chip-select idle-high when not talking.',
      pinsMap: { pin1:1, pin2:2 },
      placement: { row: 'J', cols: [33, 37] },
      tips: 'R2 pin1 → 3V3, pin2 → MAX6675 CS + Pi CE0.'
    },
    r4: {
      id: 'r4', name: 'R4 — 330 Ω LED Series', role: 'passive',
      emoji: '🔧', mascot: '➰',
      photo: 'https://upload.wikimedia.org/wikipedia/commons/thumb/1/1e/Resistor_330R.jpg/320px-Resistor_330R.jpg',
      fritzing: 'circuit/fzz/parts/resistor/breadboard/resistor_breadboard_resistor_220.svg',
      icon: 'circuit/fzz/parts/resistor/icon/resistor_icon_resistor_icon_220.svg',
      pins: 2,
      description: 'Protects the status LED from too much current.',
      pinsMap: { pin1:1, pin2:2 },
      placement: { row: 'J', cols: [45, 49] },
      tips: 'R4 pin1 → Pi GPIO16, pin2 → LED anode.'
    },
    led: {
      id: 'led', name: 'D1 — Status LED', role: 'actuator',
      emoji: '💡', mascot: '✨',
      photo: 'https://upload.wikimedia.org/wikipedia/commons/thumb/5/54/Red_LED_5mm.jpg/320px-Red_LED_5mm.jpg',
      fritzing: 'circuit/fzz/parts/led5/breadboard/led5_breadboard_LED-5mm-red-leg.svg',
      icon: 'circuit/fzz/parts/led5/icon/led5_icon_LED-red-5mmicon.svg',
      pins: 2,
      description: 'Shows OK / uh-oh. Anode (+) → R4, Cathode (−) → GND.',
      pinsMap: { anode:1, cathode:2 },
      placement: { row: 'J', cols: [42, 43] },
      tips: 'Anode longer leg. Cathode (flat side) → GND.'
    },
    breadboard: {
      id: 'breadboard', name: '840-Point Breadboard', role: 'canvas',
      emoji: '🧱', mascot: '📐',
      photo: 'https://upload.wikimedia.org/wikipedia/commons/thumb/0/0e/Breadboard_840_points.jpg/320px-Breadboard_840_points.jpg',
      fritzing: 'circuit/fzz/parts/bb840/breadboard/bb840_breadboard_breadboard.svg',
      icon: 'circuit/fzz/parts/bb840/icon/bb840_icon_breadboardicon.svg',
      pins: 840,
      description: 'Rows A–J, columns 1–60. Top rails W/X (3V3/GND), bottom rails Y/Z (5V/GND).',
      pinsMap: {},
      placement: { row: 'center', col: 'all' },
      tips: 'Wires end in numbered holes. No wires over row letters or column numbers.'
    }
  },

  // ---------------------------------------------------------------------------
  // LEVELS & LESSONS
  // ---------------------------------------------------------------------------
  LEVELS: [
    {
      id: 1, title: 'Power Rails', subtitle: '3V3 & GND — The Foundation',
      mascot: '🔌', emoji: '⚡', theme: { uc: '#FF5C8A', ucd: '#D93B69', ue: '🔌' },
      xp: 40, estimated: '8 min',
      description: 'Lay the power foundation. Every sensor needs 3.3V and GND before anything else works.',
      icon: '⚡',
      lessons: [
        {
          id: 'l1-1', level: 1, title: 'Meet the Breadboard', type: 'tour',
          emoji: '🧱',
          goal: 'Learn where rows A–J and columns 1–60 live, and what the power rails are.',
          content: `The breadboard is your canvas. <strong>Rows A–J</strong> run across (10 rows).
          <strong>Columns 1–60</strong> run up-and-down. The middle gap separates left and right.
          Top rails (W, X) carry 3V3 and GND. Bottom rails (Y, Z) carry 5V and GND for the fan.`,
          wires: [
            { from: 'Pi pin 1', net: '3V3', to: 'Row W col 1 (top-left 3V3 rail)', color: '#c0392b' },
            { from: 'Pi pin 9', net: 'GND', to: 'Row X col 3 (top-left GND rail)', color: '#34495e' },
            { from: 'Pi pin 17', net: '3V3', to: 'Row Y col 29 (top-right 3V3 rail)', color: '#c0392b' },
            { from: 'Pi pin 14', net: 'GND', to: 'Row Z col 27 (bottom-right GND rail)', color: '#34495e' }
          ],
          tips: 'Bridge the rails across the middle gap so both halves of the board get power.',
          quiz: [
            { q: 'Which row carries 3V3 on the top-left?', a: 'W', options: ['W', 'X', 'Y', 'Z'], hint: 'W is 3V3, X is GND' },
            { q: 'Which Pi pin gives 5V to the fan?', a: 'Pin 4', options: ['Pin 1', 'Pin 4', 'Pin 9', 'Pin 17'], hint: 'Pin 4 is 5V power' },
            { q: 'True or false: wires may cross over printed row letters.', a: 'False', options: ['True', 'False'], hint: 'No wires over labels — that is a comfort-wiring rule!' }
          ]
        },
        {
          id: 'l1-2', level: 1, title: 'Fan Power & Return', type: 'wire',
          emoji: '🌀',
          goal: 'Wire the fan: 5V direct from Pi, GND return to the rail.',
          content: 'The fan does NOT use a rail. It gets 5V straight from Pi pin 4 (orange wire) and returns via GND rail column 58 (dark gray wire).',
          wires: [
            { from: 'Pi pin 4', net: '5V', to: 'Fan + (off-board right)', color: '#e67e22' },
            { from: 'Fan −', net: 'GND', to: 'GND rail column 58', color: '#34495e' }
          ],
          tips: 'Direct wire = no detour through other parts. Shortest safe path wins.',
          quiz: [
            { q: 'Does the fan use the GND rail?', a: 'Yes', options: ['Yes', 'No'], hint: 'Fan − returns to GND rail column 58' },
            { q: 'What color is the 5V fan wire?', a: 'Orange (#e67e22)', options: ['Red', 'Orange (#e67e22)', 'Dark gray', 'Purple'], hint: '5V is orange in our color key' }
          ]
        }
      ]
    },
    {
      id: 2, title: 'ADXL345 Shake Sensor', subtitle: 'I2C Vibration Sensor — Row J, Pin 3',
      mascot: '📳', emoji: '💥', theme: { uc: '#7C5CFF', ucd: '#5B3FE0', ue: '📳' },
      xp: 40, estimated: '12 min',
      description: 'Connect the 3-axis accelerometer that feels motor vibration. I2C at address 0x53.',
      icon: '📳',
      lessons: [
        {
          id: 'l2-1', level: 2, title: 'ADXL345 Pin-by-Pin', type: 'wire',
          emoji: '📳',
          goal: 'Connect all 6 ADXL345 pins correctly.',
          content: `Plug the ADXL345 at <strong>row J, pin 3</strong> with the body above (rows F–I).
          CS→3V3 and SDO→GND put it in I2C mode at address 0x53. SDA→Pi pin 3, SCL→Pi pin 5.`,
          wires: [
            { from: 'ADXL345 VCC', net: '3V3', to: '3V3 rail', color: '#c0392b' },
            { from: 'ADXL345 GND', net: 'GND', to: 'GND rail', color: '#34495e' },
            { from: 'ADXL345 CS', net: '3V3', to: '3V3 rail (I2C mode)', color: '#c0392b' },
            { from: 'ADXL345 SDO', net: 'GND', to: 'GND rail (addr 0x53)', color: '#34495e' },
            { from: 'ADXL345 SDA', net: 'I2C_SDA', to: 'Pi pin 3', color: '#1f618d' },
            { from: 'ADXL345 SCL', net: 'I2C_SCL', to: 'Pi pin 5', color: '#5dade2' }
          ],
          tips: 'CS high + SDO low = I2C at 0x53. Never swap SDA and SCL.',
          quiz: [
            { q: 'What I2C address does ADXL345 use?', a: '0x53', options: ['0x1A', '0x53', '0x68', '0x77'], hint: 'SDO→GND sets 0x53' },
            { q: 'Which Pi pin is I2C data?', a: 'Pin 3', options: ['Pin 3', 'Pin 5', 'Pin 12', 'Pin 23'], hint: 'SDA → Pi pin 3' }
          ]
        },
        {
          id: 'l2-2', level: 2, title: 'I2C Test', type: 'quiz',
          emoji: '🔍',
          goal: 'Verify the ADXL345 is detected on the bus.',
          content: 'After wiring, run <code>i2cdetect -y 1</code> on the Pi. You must see <code>0x53</code>. If not, check CS and SDO.',
          quiz: [
            { q: 'Command to scan I2C bus?', a: 'i2cdetect -y 1', options: ['i2cdetect -y 1', 'i2cscan', 'ls /dev/i2c', 'modprobe i2c'], hint: 'Standard Linux I2C detection tool' },
            { q: 'Expected address for ADXL345?', a: '0x53', options: ['0x53', '0x50', '0x68', '0x1C'], hint: 'SDO tied to GND' }
          ]
        }
      ]
    },
    {
      id: 3, title: 'MAX6675 + K-Probe', subtitle: 'Heat Sensor + Thermocouple — Row J, Pin 23',
      mascot: '🌡️', emoji: '🔥', theme: { uc: '#FF5C8A', ucd: '#D93B69', ue: '🌡️' },
      xp: 40, estimated: '12 min',
      description: 'Connect the thermocouple amplifier and class-1 probe. SPI + analog temperature.',
      icon: '🌡️',
      lessons: [
        {
          id: 'l3-1', level: 3, title: 'MAX6675 SPI Wiring', type: 'wire',
          emoji: '🌡️',
          goal: 'Wire SCK, CS, SO, VCC, GND to the Pi and rails.',
          content: `Plug MAX6675 at <strong>row J, pin 23</strong>. Keep it ≥15 cm from the Pi so box heat doesn't fake a temperature rise.
          SCK→Pi 23, CS→Pi 24 (+ R2 pull-up to 3V3), SO→Pi 21.`,
          wires: [
            { from: 'MAX6675 VCC', net: '3V3', to: '3V3 rail', color: '#c0392b' },
            { from: 'MAX6675 GND', net: 'GND', to: 'GND rail', color: '#34495e' },
            { from: 'MAX6675 SCK', net: 'SPI_SCLK', to: 'Pi pin 23', color: '#b9770e' },
            { from: 'MAX6675 CS', net: 'SPI_CS0', to: 'Pi pin 24 + R2', color: '#a04000' },
            { from: 'MAX6675 SO', net: 'SPI_MISO', to: 'Pi pin 21', color: '#d4ac0d' }
          ],
          tips: 'R2 (10 kΩ) holds CS idle-high so the sensor stays quiet until the Pi selects it.',
          quiz: [
            { q: 'Why keep MAX6675 ≥15 cm from Pi?', a: 'Box heat fakes temperature rise', options: ['Looks nicer', 'Box heat fakes temperature rise', 'Fan blows on it', 'Cable too short'], hint: 'Cold junction is on the MAX6675 die' },
            { q: 'What does R2 do?', a: 'Pulls CS idle-high', options: ['Powers fan', 'Pulls CS idle-high', 'Reads temperature', 'Grounds SO'], hint: '10 kΩ pull-up to 3V3' }
          ]
        },
        {
          id: 'l3-2', level: 3, title: 'K-Type Probe Connection', type: 'wire',
          emoji: '🔌',
          goal: 'Connect chromel (+) and alumel (−) to the screw terminal.',
          content: `The K-type probe has two metal wires: <strong>chromel (T+)</strong> and <strong>alumel (T−)</strong>.
          Push T+ into MAX6675 <strong>TP</strong> and T− into <strong>TN</strong> on the green screw terminal.
          Must be CLASS 1 probe (±1.5 °C), not class 2 (±2.5 °C).`,
          wires: [
            { from: 'Probe T+ / chromel', net: 'TC_P', to: 'MAX6675 TP (pin 6)', color: '#8e44ad' },
            { from: 'Probe T− / alumel', net: 'TC_N', to: 'MAX6675 TN (pin 7)', color: '#6c3483' }
          ],
          tips: 'TC_N drops to y=128.5 between printed G/H row letters — never runs through the "G" label.',
          quiz: [
            { q: 'Which probe wire goes to TP?', a: 'T+ / chromel (+)', options: ['T− / alumel', 'T+ / chromel (+)', 'Either one', 'Neither'], hint: 'TP = Thermocouple Positive' },
            { q: 'Class-1 probe tolerance?', a: '±1.5 °C', options: ['±1.0 °C', '±1.5 °C', '±2.5 °C', '±5.0 °C'], hint: 'Class 1 is tighter than class 2' }
          ]
        }
      ]
    },
    {
      id: 4, title: 'INMP441 Microphone', subtitle: 'I2S MEMS Mic — Row J, Pin 15',
      mascot: '🎤', emoji: '👂', theme: { uc: '#7C5CFF', ucd: '#5B3FE0', ue: '🎤' },
      xp: 40, estimated: '10 min',
      description: 'Connect the digital microphone that listens for motor anomalies. I2S left channel.',
      icon: '🎤',
      lessons: [
        {
          id: 'l4-1', level: 4, title: 'INMP441 I2S Wiring', type: 'wire',
          emoji: '🎤',
          goal: 'Wire VDD, GND, L/R, BCLK, WS, SD to Pi and rails.',
          content: `Plug INMP441 at <strong>row J, pin 15</strong>. L/R→GND selects the left channel.
          BCLK→Pi 12, WS→Pi 35, SD→Pi 38. All three I2S lines go straight to the Pi header.`,
          wires: [
            { from: 'INMP441 VDD', net: '3V3', to: '3V3 rail', color: '#c0392b' },
            { from: 'INMP441 GND', net: 'GND', to: 'GND rail', color: '#34495e' },
            { from: 'INMP441 L/R', net: 'GND', to: 'GND rail (left channel)', color: '#34495e' },
            { from: 'INMP441 BCLK', net: 'I2S_BCLK', to: 'Pi pin 12', color: '#117a65' },
            { from: 'INMP441 WS', net: 'I2S_WS', to: 'Pi pin 35', color: '#1abc9c' },
            { from: 'INMP441 SD', net: 'I2S_SD', to: 'Pi pin 38', color: '#0e6655' }
          ],
          tips: 'I2S needs clean timing — keep these three wires short and away from the 5V fan wire.',
          quiz: [
            { q: 'Which Pi pin is I2S data IN?', a: 'Pin 38', options: ['Pin 12', 'Pin 35', 'Pin 38', 'Pin 21'], hint: 'SD = Serial Data → DIN pin 38' },
            { q: 'L/R → GND selects which channel?', a: 'Left', options: ['Left', 'Right', 'Both', 'Neither'], hint: 'L/R low = left channel' }
          ]
        }
      ]
    },
    {
      id: 5, title: 'Caps, Pull-up, LED & Fan', subtitle: 'Decoupling + Status Light — Finish the Rig',
      mascot: '🧩', emoji: '✨', theme: { uc: '#58CC02', ucd: '#429A02', ue: '🧩' },
      xp: 40, estimated: '12 min',
      description: 'Add decoupling caps, the R2 pull-up, the LED chain, and final fan connections.',
      icon: '🧩',
      lessons: [
        {
          id: 'l5-1', level: 5, title: 'Decoupling Capacitors C1–C4', type: 'wire',
          emoji: '🔋',
          goal: 'Place caps on row E top rails, labels clear of wires.',
          content: `C1–C3 are 100 nF ceramic. C4 is 10 µF electrolytic (watch polarity!).
          Place them in row E on the top power rails, one pair per module, labels to the left so tap lanes never cross text.`,
          wires: [
            { from: 'C1 100 nF', net: '3V3→GND', to: 'Row E cols 4–5', color: '#c0392b' },
            { from: 'C2 100 nF', net: '3V3→GND', to: 'Row E cols 7–8', color: '#c0392b' },
            { from: 'C3 100 nF', net: '3V3→GND', to: 'Row E cols 10–11', color: '#c0392b' },
            { from: 'C4 10 µF', net: '3V3→GND', to: 'Row E cols 13–14 (polarity!)', color: '#c0392b' }
          ],
          tips: 'Cap labels sit half a pitch left of the body. Tap verticals land half a pitch outside the cap body/label.',
          quiz: [
            { q: 'Which cap is electrolytic?', a: 'C4 (10 µF)', options: ['C1', 'C2', 'C3', 'C4 (10 µF)'], hint: 'Only C4 is electrolytic — watch polarity' },
            { q: 'Why labels left of caps?', a: 'Keep tap lanes clear', options: ['Looks nicer', 'Keep tap lanes clear', 'More room', 'Tradition'], hint: 'Tap verticals must not cross text' }
          ]
        },
        {
          id: 'l5-2', level: 5, title: 'LED Chain & Final Test', type: 'wire',
          emoji: '💡',
          goal: 'Wire Pi GPIO16 → R4 → LED → GND. Final integration check.',
          content: `LED chain: <strong>Pi pin 36 → R4 (330 Ω) → LED anode → LED cathode → GND</strong>.
          When the Pi says everything is OK, the LED lights up. Final check: all rails live, all sensors detected, LED responds.`,
          wires: [
            { from: 'Pi pin 36', net: 'LED_A', to: 'R4 pin 1', color: '#7f8c8d' },
            { from: 'R4 pin 2', net: 'LED_K', to: 'LED anode', color: '#7f8c8d' },
            { from: 'LED cathode', net: 'GND', to: 'GND rail', color: '#34495e' }
          ],
          tips: 'Anode = longer leg. Cathode = flat side / shorter leg → GND.',
          quiz: [
            { q: 'LED chain order?', a: 'Pi 36 → R4 → LED → GND', options: ['Pi 36 → LED → R4 → GND', 'Pi 36 → R4 → LED → GND', 'R4 → Pi 36 → LED → GND', 'LED → R4 → Pi 36 → GND'], hint: 'Resistor protects the LED first' },
            { q: 'Final integration check?', a: 'All rails live + sensors detected + LED responds', options: ['Just power on', 'All rails live + sensors detected + LED responds', 'Only check fan', 'Only check LED'], hint: 'Test each piece before adding the next' }
          ]
        }
      ]
    }
  ],

  // ---------------------------------------------------------------------------
  // ACHIEVEMENTS & GAMIFICATION
  // ---------------------------------------------------------------------------
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

  // ---------------------------------------------------------------------------
  // SIMULATOR SCENARIOS
  // ---------------------------------------------------------------------------
  SIMULATOR: {
    levels: {
      1: { name: 'Power Rail Test', checks: ['3V3 live', 'GND live', '5V to fan'], successMsg: 'Rails humming nicely ⚡' },
      2: { name: 'I2C Bus Scan', checks: ['0x53 detected', 'SDA/SCL not swapped'], successMsg: 'Shake sensor talking 📳' },
      3: { name: 'SPI + Thermocouple', checks: ['CS idle-high', 'SO data valid', 'Ice point 0 °C'], successMsg: 'Heat sensor reading 🌡️' },
      4: { name: 'I2S Audio', checks: ['BCLK running', 'WS left channel', 'SD data flowing'], successMsg: 'Mic listening 🎤' },
      5: { name: 'Full Integration', checks: ['All sensors OK', 'LED responds', 'Fan spins'], successMsg: 'Rig fully operational 🎉' }
    }
  }
};

// Export for use in app.js (if module system available)
if (typeof module !== 'undefined' && module.exports) {
  module.exports = CONTENT;
}
