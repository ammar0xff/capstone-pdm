"""
render.py — vector schematics generated from design.py.

Outputs (out/):
  schematic_main.svg   A3 landscape, full wiring + cable schedule + ERC summary
  tc_frontend.svg      K-type + MAX6675 theory, cold junction + error budget
  wiring_a3.svg        physical assembly / enclosure drawing with title block
"""
import math
from design import COMPS, NETS, DESIGN

FONT = "DejaVu Sans, Segoe UI, Arial, sans-serif"
MONO = "DejaVu Sans Mono, Consolas, monospace"

INK = "#12212f"
MUTED = "#5d6d7e"
LINE = "#c8d2da"
CARD = "#ffffff"
PAPER = "#f7f9fb"
NAVY = "#0f2a44"
GOLD = "#c9a227"


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


class SVG:
    def __init__(self, w, h, bg=PAPER):
        self.w, self.h = w, h
        self.parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
            f'viewBox="0 0 {w} {h}" font-family="{FONT}">',
            f'<rect width="{w}" height="{h}" fill="{bg}"/>',
        ]

    def add(self, s):
        self.parts.append(s)

    def rect(self, x, y, w, h, fill="none", stroke="none", rx=0, sw=1, dash=None, op=1):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.add(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" '
                 f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}" opacity="{op}"{d}/>')

    def line(self, x1, y1, x2, y2, stroke=INK, sw=1, dash=None, cap="round", op=1):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.add(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
                 f'stroke="{stroke}" stroke-width="{sw}" stroke-linecap="{cap}" opacity="{op}"{d}/>')

    def poly(self, pts, stroke=INK, sw=2, fill="none", dash=None, op=1):
        p = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.add(f'<polyline points="{p}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" '
                 f'stroke-linejoin="round" stroke-linecap="round" opacity="{op}"{d}/>')

    def text(self, x, y, s, size=12, fill=INK, anchor="start", weight="normal",
             family=FONT, op=1, rotate=None, halo=False, ls=0):
        tr = f' transform="rotate({rotate} {x:.1f} {y:.1f})"' if rotate is not None else ""
        st = ' paint-order="stroke" stroke="#ffffff" stroke-width="3.2" stroke-linejoin="round"' if halo else ""
        self.add(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{fill}" '
                 f'text-anchor="{anchor}" font-weight="{weight}" font-family="{family}" '
                 f'letter-spacing="{ls}" opacity="{op}"{tr}{st}>{esc(s)}</text>')

    def circle(self, cx, cy, r, fill=INK, stroke="none", sw=1, op=1):
        self.add(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r}" fill="{fill}" '
                 f'stroke="{stroke}" stroke-width="{sw}" opacity="{op}"/>')

    def save(self, path):
        self.parts.append("</svg>")
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(self.parts))


# --------------------------------------------------------------- components
def header(svg, title, subtitle, sheet):
    svg.rect(0, 0, svg.w, 96, fill=NAVY)
    svg.rect(0, 90, svg.w, 6, fill=GOLD)
    svg.text(40, 42, title, 26, "#ffffff", weight="bold")
    svg.text(40, 70, subtitle, 13, "#b9cfe0")
    svg.text(svg.w - 40, 42, f"Sheet {sheet}", 13, "#b9cfe0", anchor="end")
    svg.text(svg.w - 40, 66, "PdM Rig · Rev C · 8240 EGP", 12, "#8fb0c6", anchor="end")


def card(svg, x, y, w, h, title, accent=NAVY):
    svg.rect(x, y, w, h, fill=CARD, stroke=LINE, rx=10)
    svg.rect(x, y, 4, h, fill=accent, rx=2)
    svg.text(x + 18, y + 26, title, 12, accent, weight="bold", ls="1.2")


def module(svg, ref, x, y, w, h, pins, accent="#2471a3"):
    comp = COMPS[ref]
    svg.rect(x, y, w, h, fill="#ffffff", stroke=accent, rx=10, sw=1.6)
    svg.rect(x, y, w, 38, fill=accent, rx=10)
    svg.rect(x, y + 24, w, 14, fill=accent)
    svg.text(x + 14, y + 24, ref, 13, "#ffffff", weight="bold")
    svg.text(x + w - 12, y + 24, comp["value"].split("(")[0].strip()[:34], 9.5,
             "#eaf2f8", anchor="end")
    out = []
    for i, key in enumerate(pins):
        py = y + 62 + i * 26
        pin = comp["pins"][key]
        net = next((n for n, v in NETS.items() if (ref, key) in v["nodes"]), "")
        svg.text(x + 12, py + 4, pin[1], 10, INK, family=MONO, weight="bold")
        svg.text(x + 12, py + 15, pin[3][:30], 8.5, MUTED)
        svg.line(x + w, py, x + w + 16, py, NETS.get(net, {}).get("color", MUTED), 2.4)
        out.append((key, py, net))
    return out


# ------------------------------------------------------------- main schematic
def schematic_main(path):
    W, H = 1680, 1188
    svg = SVG(W, H)
    header(svg, "PdM Rig — System Wiring",
           "Raspberry Pi 4 · ADXL345 (I2C) · MAX6675 + K-type (SPI) · INMP441 (I2S) · net labels = same net",
           1)

    # ---- modules (left column)
    u2 = module(svg, "U2", 40, 150, 310, 210,
                ["VCC", "GND", "CS", "SDO", "SDA", "SCL"], "#2471a3")
    u3 = module(svg, "U3", 40, 380, 310, 280,
                ["VIN", "GND", "SCLK", "CS", "SO", "TP", "TN"], "#b9770e")
    u4 = module(svg, "U4", 40, 730, 310, 200,
                ["VDD", "GND", "LR", "BCLK", "WS", "SD"], "#117a65")

    # ---- Pi block
    px, pw = 600, 340
    svg.rect(px, 150, pw, 850, fill="#ffffff", stroke="#2471a3", rx=10, sw=1.6)
    svg.rect(px, 150, pw, 38, fill="#2471a3", rx=10)
    svg.rect(px, 174, pw, 14, fill="#2471a3")
    svg.text(px + 14, 174, "U1", 13, "#fff", weight="bold")
    svg.text(px + pw - 12, 174, "Raspberry Pi 4 — J8 header", 9.5, "#eaf2f8", anchor="end")

    groups = [
        ("POWER", [("3V3_A", "3V3", "1"), ("3V3_B", "3V3", "17"), ("5V", "5V", "4"),
                   ("GND_6", "GND", "6"), ("GND_9", "GND", "9"), ("GND_14", "GND", "14"),
                   ("GND_25", "GND", "25"), ("GND_39", "GND", "39")]),
        ("I2C", [("SDA", "SDA1", "3"), ("SCL", "SCL1", "5")]),
        ("SPI0", [("SCLK", "SCLK", "23"), ("MISO", "MISO", "21"), ("CE0", "CE0", "24")]),
        ("I2S", [("BCLK", "PCM_CLK", "12"), ("WS", "PCM_FS", "35"), ("DIN", "PCM_DIN", "38")]),
        ("GPIO", [("LED", "GPIO16", "36")]),
    ]
    ymap = {}
    y = 196
    for gname, rows in groups:
        svg.text(px + 18, y + 8, gname, 8.8, MUTED, weight="bold", ls="1.4")
        svg.line(px + 18, y + 14, px + pw - 18, y + 14, "#e6eef4", 1)
        y += 26
        for key, label, phys in rows:
            svg.rect(px + 18, y - 12, 34, 22, fill="#eef4f9", stroke="#d5e2ec", rx=5)
            svg.text(px + 35, y + 4, phys, 10, "#2471a3", anchor="middle", family=MONO, weight="bold")
            svg.text(px + 62, y + 4, label, 10.5, INK, family=MONO)
            ymap[key] = y
            y += 36

    # ---- signal routing channel
    signals = ["I2C_SDA", "I2C_SCL", "SPI_SCLK", "SPI_MISO",
               "SPI_CS0", "I2S_BCLK", "I2S_WS", "I2S_SD"]
    for i, net in enumerate(signals):
        chx = 430 + i * 17
        svg.line(chx, 150, chx, 1000, NETS[net]["color"], 0.6, dash="2 6", op=0.35)

    def route(mod_pins, mod_x):
        for key, my, net in mod_pins:
            if net not in signals:
                continue
            i = signals.index(net)
            chx = 430 + i * 17
            pi_key = next((k for k, v in ymap.items()
                           if (next(n for n in NETS[net]["nodes"] if n[0] == "U1") == ("U1", k))), None)
            if pi_key is None:
                continue
            piy = ymap[pi_key]
            col = NETS[net]["color"]
            svg.poly([(mod_x + 310 + 16, my), (chx, my), (chx, piy), (px, piy)], col, 2.2)
            svg.circle(px - 3, piy, 3.2, col)
            mid = (my + piy) / 2
            svg.text(chx - 5, mid, net.replace("I2C_", "I2C ").replace("SPI_", "SPI ")
                     .replace("I2S_", "I2S "), 8.6, col, anchor="middle",
                     rotate=-90, weight="bold", halo=True)

    route(u2, 40)
    route(u3, 40)
    route(u4, 40)

    # power / ground tags
    def rail_tag(x, y, label, color, w=54):
        svg.rect(x, y - 11, w, 22, fill="#ffffff", stroke=color, rx=4, sw=1.2)
        svg.text(x + w / 2, y + 3.5, label, 9.5, color, anchor="middle", weight="bold", family=MONO)

    short = {"TC_P": "T+", "TC_N": "T-", "LED_A": "LED_A", "LED_K": "LED_K"}
    for key, my, net in u2 + u3 + u4:
        if net in ("3V3", "GND", "5V"):
            rail_tag(356, my, net, NETS[net]["color"])
        elif net in short:
            rail_tag(354, my, short[net], NETS[net]["color"], w=58)
    for key, py in ymap.items():
        net = next((n for n, v in NETS.items() if ("U1", key) in v["nodes"]), None)
        if net == "5V":
            rail_tag(px + pw + 10, py, "FAN", NETS[net]["color"], w=38)
        elif net == "LED_A":
            rail_tag(px + pw + 10, py, "LED", NETS[net]["color"], w=38)
        elif net in ("3V3", "GND"):
            svg.circle(px + pw + 8, py, 3, NETS[net]["color"])

    # ---- right column: decoupling
    dx, dy, dw = 990, 150, 650
    card(svg, dx, dy, dw, 300, "DECOUPLING — one 100 nF per sensor, at the module")
    for i, (ref, ic, note) in enumerate([
            ("C1", "U2 ADXL345", "3.3 V rail, 4.7 uF equivalent"),
            ("C2", "U3 MAX6675", "kills SPI burst dip"),
            ("C3", "U4 INMP441", "keeps mic bias clean"),
            ("C4", "bulk 10 uF", "holds rail during WiFi TX")]):
        cx = dx + 40 + i * 155
        # capacitor symbol
        svg.line(cx, dy + 60, cx, dy + 96, "#c0392b", 2)
        svg.line(cx - 16, dy + 96, cx + 16, dy + 96, "#c0392b", 3)
        svg.line(cx - 16, dy + 106, cx + 16, dy + 106, "#34495e", 3)
        svg.line(cx, dy + 106, cx, dy + 142, "#34495e", 2)
        svg.text(cx, dy + 168, ref, 12, INK, anchor="middle", weight="bold")
        svg.text(cx, dy + 186, ic, 9, MUTED, anchor="middle")
        svg.text(cx, dy + 202, note, 8, MUTED, anchor="middle")
    svg.text(dx + 20, dy + 232, "Place the cap across VCC/GND at the sensor, not at the Pi. "
             "ADXL345 without it: +/-0.1 g hash.", 9, MUTED)
    svg.line(dx + 20, dy + 246, dx + dw - 20, dy + 246, LINE, 1)
    svg.text(dx + 20, dy + 266, "AUX", 9, MUTED, weight="bold", ls="1.2")
    svg.text(dx + 70, dy + 266, "F1 fan  5V pin 4 -> GND pin 6  (never 3V3)", 9.5, "#e67e22", family=MONO)
    svg.text(dx + 70, dy + 286, "D1 + R4  GPIO16 pin 36 -> 330R -> LED -> GND  (3.9 mA)", 9.5, "#7f8c8d", family=MONO)

    # ---- cable / net schedule
    sy = 470
    card(svg, dx, sy, dw, 320, "CABLE SCHEDULE — 9 signal nets + rails")
    svg.text(dx + 20, sy + 56, "#", 9, MUTED, weight="bold")
    svg.text(dx + 52, sy + 56, "NET", 9, MUTED, weight="bold")
    svg.text(dx + 230, sy + 56, "PI PIN (GPIO)", 9, MUTED, weight="bold")
    svg.text(dx + 430, sy + 56, "SENSOR PIN", 9, MUTED, weight="bold")
    svg.text(dx + 560, sy + 56, "TYPE", 9, MUTED, weight="bold")
    svg.line(dx + 20, sy + 64, dx + dw - 20, sy + 64, LINE, 1)
    detail = {
        "I2C_SDA": ("3 (GPIO2)", "U2.SDA", "open-drain"),
        "I2C_SCL": ("5 (GPIO3)", "U2.SCL", "open-drain"),
        "SPI_SCLK": ("23 (GPIO11)", "U3.SCK", "push-pull"),
        "SPI_MISO": ("21 (GPIO9)", "U3.SO", "push-pull"),
        "SPI_CS0": ("24 (GPIO8)", "U3.CS", "push-pull"),
        "I2S_BCLK": ("12 (GPIO18)", "U4.BCLK", "clock"),
        "I2S_WS": ("35 (GPIO19)", "U4.WS", "clock"),
        "I2S_SD": ("38 (GPIO20)", "U4.SD", "data in"),
    }
    for i, net in enumerate(signals):
        ry = sy + 84 + i * 25
        svg.text(dx + 20, ry, str(i + 1), 9.5, MUTED, family=MONO)
        svg.circle(dx + 40, ry - 4, 4, NETS[net]["color"])
        svg.text(dx + 52, ry, net, 9.5, NETS[net]["color"], family=MONO, weight="bold")
        pi, sp, typ = detail[net]
        svg.text(dx + 230, ry, pi, 9.5, INK, family=MONO)
        svg.text(dx + 430, ry, sp, 9.5, INK, family=MONO)
        svg.text(dx + 560, ry, typ, 9, MUTED)
    svg.line(dx + 20, sy + 296, dx + dw - 20, sy + 296, LINE, 1)
    svg.text(dx + 20, sy + 312, "Power: 3V3 = pins 1 + 17 · 5V = pin 4 (fan only) · "
             "GND = 6/9/14/25/39 (star point at pin 39)", 8.5, MUTED)

    # ---- checks card
    cy = 810
    card(svg, dx, cy, dw, 280, "WHY IT WORKS — derived numbers", accent="#117a65")
    rows = [
        ("Nyquist", f'fs {DESIGN["fs_hz"]} Hz -> 400 Hz, covers BPFO/BPFI to 300 Hz'),
        ("FFT", f'{DESIGN["fs_hz"]}/{DESIGN["window"]} = 0.195 Hz/bin, 5.12 s window'),
        ("ADXL range", "+/-4 g, FULL_RES 3.9 mg/LSB vs 100 mg budget"),
        ("Thermo", "12-bit -> 0.25 C/step, no self-heating"),
        ("Budget", "class-1 probe RSS 1.68 C vs +/-2.0 C (M4)"),
        ("I2C", "1.8k pull-up + 60 pF -> 238 ns rise < 300 ns at 400 kHz"),
        ("Power", "7.4 W peak = 1.48 A of 3 A (49% load), 2x margin"),
        ("AI", "1 RF inference ~2 ms on Pi 4, runs only when SPC fires"),
    ]
    for i, (k, v) in enumerate(rows):
        ry = cy + 56 + i * 29
        svg.text(dx + 22, ry, k, 9.5, "#117a65", weight="bold", family=MONO)
        svg.text(dx + 120, ry, v, 9.5, INK)

    # ---- legend / notes
    ly = 1005
    card(svg, 40, ly, 900, 135, "READING THIS SHEET", accent=GOLD)
    svg.text(60, ly + 56, "1. One net label / colour = one electrical node. The same name at both ends means wired together.",
             10, INK)
    svg.text(60, ly + 78, "2. Signal names are printed along the routing rails; the schedule on the right is the "
             "authoritative pin list.", 10, INK)
    svg.text(60, ly + 100, "3. GND is a star: every return meets at pin 39. Never daisy-chain sensor grounds.",
             10, INK)
    svg.text(60, ly + 122, "4. Never apply 5 V to a sensor pin. Power the Pi from the official 5 V / 3 A supply only.",
             10, "#922b21", weight="bold")

    svg.text(W - 40, H - 18, "Generated by circuit/render.py from circuit/design.py — do not edit by hand",
             9, MUTED, anchor="end")
    svg.save(path)


# ------------------------------------------------------- thermocouple theory
def tc_frontend(path):
    W, H = 1400, 900
    svg = SVG(W, H)
    header(svg, "K-type thermocouple + MAX6675 — front end",
           "Seebeck physics, where the cold junction really is, and the error budget behind M4 (+/-2 C)", 2)

    # ---- probe
    svg.rect(170, 250, 72, 210, fill="#eef3f7", stroke="#7f8c8d", rx=6, sw=1.8)
    svg.text(206, 280, "K-type", 11, INK, anchor="middle", weight="bold")
    svg.text(206, 296, "M6 probe", 9, MUTED, anchor="middle")
    for i in range(7):
        svg.line(170, 330 + i * 16, 178, 330 + i * 16, "#95a5a6", 1.4)
    svg.poly([(170, 460), (242, 460), (206, 512)], fill="#d5dbdb", stroke="#7f8c8d", sw=1.6)
    svg.circle(206, 500, 5, "#c0392b")
    svg.text(216, 528, "measuring junction (T_hot)", 9.5, "#c0392b")

    # ---- twisted pair (the actual thermocouple wires)
    svg.poly([(190, 250), (190, 214), (300, 214)], "#c0392b", 2)
    svg.poly([(222, 250), (222, 226), (300, 226)], "#2471a3", 2)
    for i in range(9):
        x0 = 300 + i * 20
        y0a, y0b = (214, 226) if i % 2 == 0 else (226, 214)
        svg.line(x0, y0a, x0 + 20, y0b, "#c0392b" if i % 2 == 0 else "#2471a3", 1.8)
    svg.poly([(480, 220), (600, 220)], "#8e44ad", 2.2)
    svg.text(392, 200, "twisted pair, shield grounded at the Pi end only", 9, MUTED, anchor="middle")
    svg.text(270, 250, "chromel", 8.5, "#c0392b")
    svg.text(270, 264, "alumel", 8.5, "#2471a3")

    # ---- MAX6675 module
    bx, by, bw, bh = 600, 170, 340, 350
    svg.rect(bx, by, bw, bh, fill="#fff", stroke="#b9770e", rx=10, sw=1.8)
    svg.rect(bx, by, bw, 38, fill="#b9770e", rx=10)
    svg.rect(bx, by + 24, bw, 14, fill="#b9770e")
    svg.text(bx + 14, by + 24, "U3  MAX6675", 12, "#fff", weight="bold")
    # screw terminal = cold junction
    svg.rect(bx + 12, 222, 60, 46, fill="#f4ecf7", stroke="#8e44ad", rx=4, sw=1.4)
    svg.circle(bx + 30, 245, 7, "#fff", stroke="#8e44ad", sw=1.6)
    svg.circle(bx + 54, 245, 7, "#fff", stroke="#8e44ad", sw=1.6)
    svg.text(bx + 29, 264, "+", 9, "#8e44ad", anchor="middle")
    svg.text(bx + 56, 264, "-", 9, "#8e44ad", anchor="middle")
    svg.text(bx + 12, 216, "cold junction = isothermal block", 9, "#8e44ad")
    svg.line(bx + 72, 245, bx + 120, 245, "#8e44ad", 2)
    svg.circle(bx + 124, 245, 4, "#8e44ad")

    # die + internals
    svg.rect(bx + 120, 280, 180, 78, fill="#fef9e7", stroke="#b9770e", rx=6, sw=1.4)
    svg.text(bx + 210, 304, "MAX6675 die", 10, "#b9770e", anchor="middle", weight="bold")
    svg.text(bx + 210, 322, "cold-junction sensor", 8.5, MUTED, anchor="middle")
    svg.text(bx + 210, 338, "amplifier + 12-bit ADC", 8.5, MUTED, anchor="middle")
    svg.text(bx + 210, 352, "linearisation, open-TC flag", 8, MUTED, anchor="middle")
    svg.line(bx + 124, 245, bx + 124, 280, "#8e44ad", 1.6)
    svg.text(bx + 132, 380, "220 ms per conversion", 8.5, MUTED)
    svg.text(bx + 132, 394, "0.25 C per step", 8.5, MUTED)
    svg.text(bx + 20, 410, "VCC 3.3 V (generic board)", 9, INK)
    svg.text(bx + 20, 428, "100 nF at the module", 9, INK)
    svg.text(bx + 20, 446, "SPI mode 0, 1 MHz, read only", 9, INK)
    svg.text(bx + 20, 470, "Do NOT feed an Adafruit board", 9, "#922b21")
    svg.text(bx + 20, 486, "Vin from 3V3 - it needs 5 V.", 9, "#922b21")

    svg.line(bx + bw, 300, 1030, 300, "#b9770e", 2.4)
    svg.text(bx + bw + 8, 292, "SPI0  CS / SCK / SO", 9.5, "#b9770e", weight="bold", family=MONO)
    svg.rect(1030, 270, 330, 60, fill="#fff", stroke="#2471a3", rx=8, sw=1.6)
    svg.text(1195, 296, "Raspberry Pi 4", 10.5, INK, anchor="middle", weight="bold")
    svg.text(1195, 314, "CE0 8 · SCLK 11 · MISO 9", 8.5, MUTED, anchor="middle", family=MONO)

    # ---- reading card
    card(svg, 1030, 150, 330, 110, "ONE READING")
    svg.text(1050, 194, "T = f(V_tc) + T_cold", 10.5, INK, family=MONO)
    svg.text(1050, 216, "the chip does the inverse, you", 9, MUTED)
    svg.text(1050, 232, "just read SPI and apply cal.", 9, MUTED)

    # ---- physics panel
    px, py, pw = 80, 560, 580
    svg.rect(px, py, pw, 300, fill="#fff", stroke=LINE, rx=10)
    svg.text(px + 18, py + 26, "THE PHYSICS — WHY THE COLD JUNCTION MATTERS", 10.5, NAVY, weight="bold", ls="0.8")
    svg.text(px + 18, py + 56, "V = S x (T_hot - T_cold)      S = 41 uV/C", 12, "#8e44ad", family=MONO, weight="bold")
    svg.text(px + 18, py + 80, "A thermocouple does not measure temperature; it measures a", 9.5, MUTED)
    svg.text(px + 18, py + 96, "temperature DIFFERENCE. To report T_hot the chip must know", 9.5, MUTED)
    svg.text(px + 18, py + 112, "T_cold, so it measures its own die and adds that back.", 9.5, MUTED)
    svg.text(px + 18, py + 140, "0 C -> 0.00 mV      100 C -> 4.10 mV", 10, INK, family=MONO)
    svg.text(px + 18, py + 162, "1 C = 41 uV: the whole signal is a few millivolts,", 9.5, MUTED)
    svg.text(px + 18, py + 178, "which is why the pair must be twisted and shielded.", 9.5, MUTED)
    svg.text(px + 18, py + 206, "Trap 1: the terminal block and the die must be at the", 9.5, "#922b21")
    svg.text(px + 18, py + 222, "same temperature. Put the module next to the Pi and", 9.5, "#922b21")
    svg.text(px + 18, py + 238, "the die runs 12 C hot -> every reading is 12 C low.", 9.5, "#922b21")
    svg.text(px + 18, py + 266, "Trap 2: a broken probe reads ambient. Always check", 9.5, "#922b21")
    svg.text(px + 18, py + 282, "the MAX6675 open-thermocouple flag before trusting T.", 9.5, "#922b21")

    # ---- error budget
    ex, ew = 690, 630
    svg.rect(ex, py, ew, 300, fill="#fef5e7", stroke="#e67e22", rx=10)
    svg.text(ex + 18, py + 26, "ERROR BUDGET  (M4 = +/-2.0 C, class-1 probe)", 10.5, "#b9770e", weight="bold", ls="0.8")
    budget = [
        ("K-type probe, class 1", 1.50),
        ("cold-junction tracking", 0.50),
        ("linearisation + offset", 0.50),
        ("12-bit quantisation", 0.25),
    ]
    for i, (k, v) in enumerate(budget):
        yy = py + 56 + i * 18
        svg.text(ex + 18, yy, k, 9.5, INK)
        svg.text(ex + 290, yy, f"{v:.2f} C", 9.5, INK, family=MONO)
    rss = sum(v * v for _, v in budget) ** 0.5
    svg.text(ex + 400, py + 62, f"RSS = {rss:.2f} C", 13, "#922b21", weight="bold", family=MONO)
    svg.text(ex + 400, py + 82, "budget 2.00 C -> margin 1.19x", 9.5, "#922b21")
    svg.text(ex + 18, py + 142, "A class-2 probe is +/-2.5 C on its own:", 9.5, "#922b21", weight="bold")
    svg.text(ex + 18, py + 160, "RSS becomes 2.62 C and M4 must be restated to +/-2.5.", 9.5, "#922b21")
    svg.text(ex + 18, py + 184, "Ordering rule: specify class 1 (0.004|t|) or better.", 9.5, INK)
    svg.line(ex + 18, py + 198, ex + ew - 18, py + 198, "#f0c9a0", 1)
    svg.text(ex + 18, py + 220, "PT100 + MAX31865 gave 0.40 C with 2.5x margin.", 9.5, MUTED)
    svg.text(ex + 18, py + 236, "This BOM trades that accuracy for 0-1000 C range,", 9.5, MUTED)
    svg.text(ex + 18, py + 252, "faster response (tau 4 s vs 8 s) and no self-heating.", 9.5, MUTED)
    svg.text(ex + 18, py + 278, "Meeting M4 therefore depends on the probe class you buy.", 9.5, "#922b21", weight="bold")

    svg.save(path)


# ------------------------------------------------------------- assembly A3
def wiring_a3(path):
    W, H = 1680, 1188
    svg = SVG(W, H)
    header(svg, "PdM Rig — Assembly & Cable Drawing",
           "IP65 enclosure, panel layout, cable schedule and power-on checklist (A3, not to scale)", 3)

    # enclosure
    bx, by, bw, bh = 60, 140, 900, 700
    svg.rect(bx, by, bw, bh, fill="#eef3f7", stroke=NAVY, rx=14, sw=2)
    svg.rect(bx + 12, by + 12, bw - 24, bh - 24, fill="none", stroke="#9fb3c4", rx=10, dash="6 6")
    svg.text(bx + 24, by + 34, "IP65 enclosure — top view, lid removed", 10, MUTED, weight="bold")

    # Pi board
    px, py = bx + 60, by + 120
    svg.rect(px, py, 340, 220, fill="#1b6b4a", stroke="#0d3d2a", rx=8, sw=1.5)
    for hx, hy in [(px + 12, py + 12), (px + 328, py + 12), (px + 12, py + 208), (px + 328, py + 208)]:
        svg.circle(hx, hy, 7, "#d5dbdb", stroke="#7f8c8d")
    svg.rect(px + 250, py + 40, 60, 150, fill="#2c3e50", rx=4)
    svg.text(px + 170, py + 60, "Raspberry Pi 4  8 GB", 12, "#eafaf1", anchor="middle", weight="bold")
    svg.text(px + 170, py + 82, "5 V / 3 A  ·  Type-C at top edge", 9, "#a9dfbf", anchor="middle")
    svg.text(px + 170, py + 110, "40-pin header -> 26-way ribbon", 9, "#a9dfbf", anchor="middle")
    svg.text(px + 170, py + 150, "microSD 32 GB", 9, "#a9dfbf", anchor="middle")
    svg.text(px + 170, py + 176, "fan on 5 V pin 4 / GND pin 6", 9, "#a9dfbf", anchor="middle")

    # breadboard
    bb_x, bb_y = bx + 470, by + 150
    svg.rect(bb_x, bb_y, 360, 180, fill="#fdfefe", stroke="#95a5a6", rx=6, sw=1.5)
    svg.line(bb_x + 8, bb_y + 22, bb_x + 352, bb_y + 22, "#e74c3c", 2)
    svg.line(bb_x + 8, bb_y + 34, bb_x + 352, bb_y + 34, "#2471a3", 2)
    for i in range(24):
        svg.line(bb_x + 16 + i * 14, bb_y + 50, bb_x + 16 + i * 14, bb_y + 150, "#d5dbdb", 1)
    svg.text(bb_x + 180, bb_y + 16, "840-point breadboard", 9, MUTED, anchor="middle")
    svg.text(bb_x + 180, bb_y + 172, "U2 / U3 / U4 + C1..C4 + R2", 9, MUTED, anchor="middle")

    # sensor modules
    for i, (label, col) in enumerate([("U2 ADXL345", "#2471a3"), ("U3 MAX6675", "#b9770e"),
                                      ("U4 INMP441", "#117a65")]):
        mx = bb_x + 20 + i * 115
        svg.rect(mx, bb_y + 62, 100, 62, fill="#fff", stroke=col, rx=5, sw=1.4)
        svg.text(mx + 50, bb_y + 88, label.split()[0], 10, col, anchor="middle", weight="bold")
        svg.text(mx + 50, bb_y + 106, label.split()[1], 8.5, INK, anchor="middle")

    # glands
    for i, gx in enumerate([bx + 380, bx + 560]):
        svg.circle(gx, by + bh - 6, 14, "#bdc3c7", stroke="#7f8c8d", sw=1.5)
        svg.circle(gx, by + bh - 6, 6, "#7f8c8d")
    svg.text(bx + 470, by + bh - 34, "2 x PG7 cable glands (sensor bundle + USB-C power)",
             9, MUTED, anchor="middle")

    # cable runs
    svg.poly([(bb_x + 60, bb_y + 62), (bb_x + 60, by + 100), (px + 300, by + 100),
              (px + 300, py + 110)], "#2471a3", 2, dash="5 4")
    svg.text(bb_x + 66, by + 94, "ADXL345  I2C  0.25 m shielded", 8.5, "#2471a3")
    svg.poly([(bb_x + 180, bb_y + 62), (bb_x + 180, by + 88), (px + 340, by + 88),
              (px + 340, py + 130)], "#b9770e", 2, dash="5 4")
    svg.text(bb_x + 190, by + 82, "K-type pair  SPI  0.4 m shielded/twisted", 8.5, "#b9770e")
    svg.poly([(bb_x + 300, bb_y + 62), (bb_x + 300, by + 76), (px + 360, by + 76),
              (px + 360, py + 160)], "#117a65", 2, dash="5 4")
    svg.text(bb_x + 310, by + 70, "INMP441  I2S  0.25 m twisted", 8.5, "#117a65")

    # sensor heads outside the box
    sx, sy = bx + 380, by + bh + 70
    svg.circle(sx, sy, 10, "#e67e22")
    svg.text(sx + 18, sy + 4, "magnet + M3 + nylon -> ADXL345 on motor skin", 9, INK)
    svg.circle(sx + 10, sy + 26, 8, "#b9770e")
    svg.text(sx + 26, sy + 30, "K-type M6 probe, thermal paste, finger-tight", 9, INK)
    svg.circle(sx + 480, sy, 9, "#117a65")
    svg.text(sx + 498, sy + 4, "INMP441 facing bearing, 10-20 cm", 9, INK)

    # right column: tables
    rx, ry, rw = 990, 140, 650
    card(svg, rx, ry, rw, 300, "CABLE SCHEDULE")
    svg.text(rx + 18, ry + 56, "FROM", 8.5, MUTED, weight="bold")
    svg.text(rx + 180, ry + 56, "TO", 8.5, MUTED, weight="bold")
    svg.text(rx + 400, ry + 56, "LEN", 8.5, MUTED, weight="bold")
    svg.text(rx + 470, ry + 56, "RULE", 8.5, MUTED, weight="bold")
    svg.line(rx + 18, ry + 62, rx + rw - 18, ry + 62, LINE, 1)
    cables = [
        ("ADXL345 VCC/GND", "3V3 p1 / GND p9", "0.25 m", "100 nF at module"),
        ("ADXL345 SDA/SCL", "GPIO2 / GPIO3", "0.25 m", "shielded pair"),
        ("MAX6675 VCC/GND", "3V3 p17 / GND p25", "0.10 m", "100 nF at module"),
        ("SPI 3-wire", "GPIO 8/9/11", "0.10 m", "keep < 10 cm, mode 0"),
        ("K-type pair", "T+ / T-", "0.40 m", "twisted, shield 1 end"),
        ("INMP441 VDD/GND", "3V3 p1 / GND p14", "0.25 m", "100 nF at module"),
        ("INMP441 I2S", "GPIO 18/19/20", "0.25 m", "twisted, away from SPI"),
        ("Fan", "5V p4 / GND p6", "0.15 m", "never to 3V3"),
    ]
    for i, row in enumerate(cables):
        yy = ry + 82 + i * 26
        svg.text(rx + 18, yy, row[0], 9, INK)
        svg.text(rx + 180, yy, row[1], 9, INK, family=MONO)
        svg.text(rx + 400, yy, row[2], 9, MUTED, family=MONO)
        svg.text(rx + 470, yy, row[3], 8.5, MUTED)

    card(svg, rx, 460, rw, 250, "ASSEMBLY ORDER", accent="#117a65")
    steps = ["1. Pi + heatsink + paste + fan in the case; boot and update.",
             "2. i2cdetect -y 1 must show 0x53 before anything else.",
             "3. Breadboard U2/U3/U4 with 100 nF each. Verify 3.3 V at every VCC.",
             "4. Ice-point test 0 C; the open-TC flag must read 0 before you trust T.",
             "5. Bolt the sensor stack: magnet / M3 / nylon / PCB / nylon / nut.",
             "6. Cable glands + heat-shrink, strain-relief, then close the lid."]
    for i, s in enumerate(steps):
        svg.text(rx + 18, 500 + i * 30, s, 9.5, INK)

    card(svg, rx, 730, rw, 210, "POWER-ON CHECKLIST", accent="#922b21")
    checks = ["[ ] 5 V/3 A official supply, not a phone charger",
              "[ ] 3.3 V at U2/U3/U4, no 5 V on any sensor pin",
              "[ ] i2cdetect 0x53, spidev0.0 present, arecord -l shows the mic",
              "[ ] ice point 0 +/-2 C, boil ~97 C, ADXL flat = 1.00 g",
              "[ ] Panel + Grafana both flip within 5 s, WiFi pull = no data loss"]
    for i, s in enumerate(checks):
        svg.text(rx + 18, 770 + i * 30, s, 9.5, INK)

    # title block
    ty = 1040
    svg.rect(60, ty, W - 120, 100, fill="#fff", stroke=LINE, rx=8)
    svg.line(60 + 420, ty, 60 + 420, ty + 100, LINE, 1)
    svg.line(60 + 900, ty, 60 + 900, ty + 100, LINE, 1)
    svg.text(80, ty + 30, "Intelligent Predictive Maintenance Rig", 13, NAVY, weight="bold")
    svg.text(80, ty + 52, "G12 Capstone 2026/27 — Industrial pathway", 9.5, MUTED)
    svg.text(80, ty + 72, "Raspberry Pi 4 8GB · ADXL345 · K-type/MAX6675 · INMP441", 9.5, MUTED)
    svg.text(500, ty + 30, "SHEET 3 of 3", 11, NAVY, weight="bold")
    svg.text(500, ty + 52, "NTS  ·  A3  ·  print at 100%, do not fit to page", 9.5, MUTED)
    svg.text(500, ty + 72, "Print at 100% — do not fit-to-page", 9.5, MUTED)
    svg.text(980, ty + 30, "REV C", 11, NAVY, weight="bold")
    svg.text(980, ty + 52, "Hardware 8240 EGP · cloud 0 EGP", 9.5, MUTED)
    svg.text(980, ty + 72, "ERC: see out/erc_report.md", 9.5, MUTED)

    svg.save(path)
