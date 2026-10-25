"""
design.py — single source of truth for the PdM rig circuit.

Everything downstream (ERC, physics checks, KiCad netlist, SKiDL, SVG) is
generated from the tables below, so the schematic can never drift from the
netlist. Pure stdlib: runs on the Pi, no KiCad install required.

Refs: Raspberry Pi 4 J8 header, ADXL345 (I2C 0x53), MAX31865 (SPI0),
INMP441 (I2S left channel), PT100 3-wire, 5V/3A PSU.
"""

# ---------------------------------------------------------------- components
# pin tuple: (physical pin / pad, signal name, electrical type, human label)
#   etype: pwr gnd in out io od passive
COMPS = {
    "U1": {
        "value": "Raspberry Pi 4 Model B 8GB",
        "mpn": "RPi4-8GB",
        "fp": "Connector_PinHeader_2.54mm:PinHeader_1x40_P2.54mm_Vertical",
        "pins": {
            "3V3_A":   ("1",  "3V3",      "pwr",     "3V3 (pin 1)"),
            "SDA":     ("3",  "SDA1",     "od",      "GPIO2 / SDA1 (pin 3)"),
            "SCL":     ("5",  "SCL1",     "od",      "GPIO3 / SCL1 (pin 5)"),
            "GND_9":   ("9",  "GND",      "gnd",     "GND (pin 9)"),
            "BCLK":    ("12", "PCM_CLK",  "out",     "GPIO18 / PCM_CLK (pin 12)"),
            "GND_14":  ("14", "GND",      "gnd",     "GND (pin 14)"),
            "3V3_B":   ("17", "3V3",      "pwr",     "3V3 (pin 17)"),
            "MOSI":    ("19", "MOSI",     "out",     "GPIO10 / MOSI (pin 19)"),
            "MISO":    ("21", "MISO",     "in",      "GPIO9 / MISO (pin 21)"),
            "SCLK":    ("23", "SCLK",     "out",     "GPIO11 / SCLK (pin 23)"),
            "CE0":     ("24", "CE0",      "out",     "GPIO8 / CE0 (pin 24)"),
            "GND_25":  ("25", "GND",      "gnd",     "GND (pin 25)"),
            "WS":      ("35", "PCM_FS",   "out",     "GPIO19 / PCM_FS (pin 35)"),
            "LED":     ("36", "GPIO16",   "out",     "GPIO16 (pin 36)"),
            "DIN":     ("38", "PCM_DIN",  "in",      "GPIO20 / PCM_DIN (pin 38)"),
            "GND_39":  ("39", "GND",      "gnd",     "GND (pin 39)"),
            "5V":      ("4",  "5V",       "pwr",     "5V (pin 4, fan)"),
            "GND_6":   ("6",  "GND",      "gnd",     "GND (pin 6, fan)"),
        },
    },
    "U2": {
        "value": "ADXL345 3-axis accelerometer module",
        "mpn": "ADXL345",
        "fp": "Module:ADXL345",
        "pins": {
            "VCC": ("1", "VCC",  "pwr",     "VCC 3.3V"),
            "GND": ("2", "GND",  "gnd",     "GND"),
            "CS":  ("3", "CS",   "in",      "CS -> 3V3 = I2C mode"),
            "SDO": ("4", "SDO",  "in",      "SDO -> GND = addr 0x53"),
            "SDA": ("5", "SDA",  "od",      "SDA"),
            "SCL": ("6", "SCL",  "in",      "SCL"),
        },
    },
    "U3": {
        "value": "MAX6675 K-type thermocouple module",
        "mpn": "MAX6675",
        "fp": "Module:MAX6675",
        "pins": {
            "VIN":  ("1", "VCC",   "pwr",     "VCC 3.0-3.6V (generic board)"),
            "GND":  ("2", "GND",   "gnd",     "GND"),
            "SCLK": ("3", "SCK",   "in",      "SCK (SPI clock)"),
            "CS":   ("4", "CS",    "in",      "CS active low"),
            "SO":   ("5", "SO",    "out",     "SO = MISO, read only"),
            "TP":   ("6", "T+",    "passive", "T+ thermocouple +"),
            "TN":   ("7", "T-",    "passive", "T- thermocouple -"),
        },
    },
    "U4": {
        "value": "INMP441 I2S MEMS microphone",
        "mpn": "INMP441",
        "fp": "Module:INMP441",
        "pins": {
            "VDD": ("1", "VDD",   "pwr",     "VDD 3.3V"),
            "GND": ("2", "GND",   "gnd",     "GND"),
            "LR":  ("3", "L/R",   "in",      "L/R -> GND = left"),
            "BCLK":("4", "BCLK",  "in",      "BCLK"),
            "WS":  ("5", "WS",    "in",      "WS / LRCLK"),
            "SD":  ("6", "SD",    "out",     "SD data out"),
        },
    },
    "R1": {"value": "K-type probe M6 (class 1)", "mpn": "TC-K-M6", "fp": "Module:TC_K_M6",
           "pins": {"P": ("1", "T+", "passive", "chromel lead"),
                    "N": ("2", "T-", "passive", "alumel lead")}},
    "C1": {"value": "100nF X7R", "mpn": "100nF", "fp": "Capacitor_SMD:C_0402_1005Metric",
           "pins": {"1": ("1", "1", "passive", "1"), "2": ("2", "2", "passive", "2")}},
    "C2": {"value": "100nF X7R", "mpn": "100nF", "fp": "Capacitor_SMD:C_0402_1005Metric",
           "pins": {"1": ("1", "1", "passive", "1"), "2": ("2", "2", "passive", "2")}},
    "C3": {"value": "100nF X7R", "mpn": "100nF", "fp": "Capacitor_SMD:C_0402_1005Metric",
           "pins": {"1": ("1", "1", "passive", "1"), "2": ("2", "2", "passive", "2")}},
    "C4": {"value": "10uF electrolytic", "mpn": "10uF", "fp": "Capacitor_SMD:CP_Elec_4x5.4",
           "pins": {"1": ("1", "1", "passive", "1"), "2": ("2", "2", "passive", "2")}},
    "R2": {"value": "10k pull-up (CS idle high)", "mpn": "10k", "fp": "Resistor_SMD:R_0402_1005Metric",
           "pins": {"1": ("1", "1", "passive", "1"), "2": ("2", "2", "passive", "2")}},
    "R4": {"value": "330R LED series (salvaged)", "mpn": "330R", "fp": "Resistor_SMD:R_0402_1005Metric",
           "pins": {"1": ("1", "1", "passive", "1"), "2": ("2", "2", "passive", "2")}},
    "D1": {"value": "Status LED (salvaged)", "mpn": "LED", "fp": "LED_SMD:LED_0603_1608Metric",
           "pins": {"A": ("1", "A", "passive", "anode"), "K": ("2", "K", "passive", "cathode")}},
    "F1": {"value": "5V cooling fan", "mpn": "FAN-5V", "fp": "Module:Fan_5V",
           "pins": {"P": ("1", "P", "pwr", "+5V"), "N": ("2", "N", "gnd", "GND")}},
}

# --------------------------------------------------------------------- nets
# kind: signal | power | gnd | analog
NETS = {
    "3V3":        {"color": "#c0392b", "kind": "power",  "nodes": [
        ("U1", "3V3_A"), ("U1", "3V3_B"), ("U2", "VCC"), ("U2", "CS"), ("U3", "VIN"),
        ("U4", "VDD"), ("C1", "1"), ("C2", "1"), ("C3", "1"), ("C4", "1"), ("R2", "1")]},
    "GND":        {"color": "#34495e", "kind": "gnd",    "nodes": [
        ("U1", "GND_9"), ("U1", "GND_14"), ("U1", "GND_25"), ("U1", "GND_39"),
        ("U1", "GND_6"), ("U2", "GND"), ("U2", "SDO"), ("U3", "GND"), ("U4", "GND"),
        ("U4", "LR"), ("C1", "2"), ("C2", "2"), ("C3", "2"), ("C4", "2"),
        ("D1", "K"), ("F1", "N")]},
    "5V":         {"color": "#e67e22", "kind": "power",  "nodes": [("U1", "5V"), ("F1", "P")]},
    "I2C_SDA":    {"color": "#2471a3", "kind": "signal", "nodes": [("U1", "SDA"), ("U2", "SDA")]},
    "I2C_SCL":    {"color": "#2471a3", "kind": "signal", "nodes": [("U1", "SCL"), ("U2", "SCL")]},
    "SPI_SCLK":   {"color": "#b9770e", "kind": "signal", "nodes": [("U1", "SCLK"), ("U3", "SCLK")]},
    "SPI_MISO":   {"color": "#b9770e", "kind": "signal", "nodes": [("U3", "SO"), ("U1", "MISO")]},
    "SPI_CS0":    {"color": "#b9770e", "kind": "signal", "nodes": [("U1", "CE0"), ("U3", "CS"), ("R2", "2")]},
    "I2S_BCLK":   {"color": "#117a65", "kind": "signal", "nodes": [("U1", "BCLK"), ("U4", "BCLK")]},
    "I2S_WS":     {"color": "#117a65", "kind": "signal", "nodes": [("U1", "WS"), ("U4", "WS")]},
    "I2S_SD":     {"color": "#117a65", "kind": "signal", "nodes": [("U1", "DIN"), ("U4", "SD")]},
    "TC_P":       {"color": "#8e44ad", "kind": "analog", "nodes": [("R1", "P"), ("U3", "TP")]},
    "TC_N":       {"color": "#8e44ad", "kind": "analog", "nodes": [("R1", "N"), ("U3", "TN")]},
    "LED_A":      {"color": "#7f8c8d", "kind": "signal", "nodes": [("U1", "LED"), ("R4", "1")]},
    "LED_K":      {"color": "#7f8c8d", "kind": "signal", "nodes": [("R4", "2"), ("D1", "A")]},
}

# ------------------------------------------------------------------ settings
DESIGN = {
    "fs_hz": 800,            # ADXL345 ODR = 800 Hz, FIFO burst read
    "window": 4096,          # 5.12 s at 800 Hz
    "g_range": 4,            # +/-4 g
    "tc_res_c": 0.25,        # MAX6675 12-bit output
    "tc_acc_c": 2.0,         # restated M4, class-1 probe + calibration
    "tc_class1_c": 1.5,      # probe tolerance, class 1 (0.004|t| at 100 C)
    "tc_cj_c": 0.5,          # cold-junction tracking error
    "tc_lin_c": 0.5,         # internal linearisation + offset
    "tc_tau_s": 4.0,
    "tc_emf_uv_c": 41.0,     # K-type Seebeck coefficient near 25 C
    "box_rise_c": 12.0,
    "cj_distance_cm": 15,
    "i2c_rp_ohm": 1800.0,    # Pi 4 onboard pull-ups on GPIO2/3
    "i2c_cb_pf": 60.0,       # ~10 cm shielded pair
    "vdd": 3.3,
    "psu_a": 3.0,
    "pi_idle_w": 2.7,
    "pi_peak_w": 6.4,
    "fan_w": 1.0,
    "audio_fs": 16000,
    "temp_tau_s": 8.0,
}

# --------------------------------------------------------------- BOM (xlsx)
def bom_rows(path=None):
    """Parse the locked BOM xlsx with stdlib only (zip + xml)."""
    import os, zipfile, xml.etree.ElementTree as ET
    if path is None:
        path = os.environ.get("PDM_BOM", os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", "DOC-20261014-WA0055.xlsx"))
    ns = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    with zipfile.ZipFile(path) as z:
        sst = ET.fromstring(z.read("xl/sharedStrings.xml"))
        strings = ["".join(t.text or "" for t in si.findall(".//m:t", ns))
                   for si in sst.findall("m:si", ns)]
        sheet = ET.fromstring(z.read("xl/worksheets/sheet1.xml"))
    rows = []
    for row in sheet.findall(".//m:row", ns):
        cells = {}
        for c in row.findall("m:c", ns):
            ref = c.get("r")
            col = "".join(ch for ch in ref if ch.isalpha())
            v = c.find("m:v", ns)
            val = v.text if v is not None else ""
            if c.get("t") == "s" and val != "":
                val = strings[int(val)]
            cells[col] = val
        rows.append(cells)
    return rows
