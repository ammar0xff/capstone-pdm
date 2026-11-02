"""custom.py - author the four parts the community library does not have.

The community library has the bare MAX6675 SO-8 chip but not the blue breakout
that is actually in the BOM, no INMP441 breakout, no K-type probe and no 5 V
fan.  Those four are drawn here with the same view contract as a community
part (icon / breadboard / schematic / pcb), so the sketch is still fully
self-contained.

All SVGs use 90 units per inch, i.e. one SVG unit == one Fritzing sketch unit.
"""
from __future__ import annotations

import os
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
PARTS_DIR = os.path.join(HERE, "parts")


def _svg(w, h, body, layer="breadboard", extra=None):
    """Wrap a drawing in the layer group Fritzing extracts.

    A part image is not a picture: Fritzing pulls out the group whose id
    matches the fzp layerId.  Without that group the part loads (its
    geometry is known) but renders empty, so every view needs one.
    """
    groups = [f'<g id="{layer}">\n{body}\n</g>']
    for name, content in (extra or {}).items():
        groups.append(f'<g id="{name}">\n{content}\n</g>')
    return (f'<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<svg xmlns="http://www.w3.org/2000/svg" version="1.1" '
            f'width="{w/90:.10f}in" height="{h/90:.10f}in" viewBox="0 0 {w:g} {h:g}">\n'
            + "\n".join(groups) + '\n</svg>\n')


def _pin(cid, x, y, r=2.2, color="#d4af37"):
    return (f'<circle id="{cid}" cx="{x:g}" cy="{y:g}" r="{r:g}" fill="none" '
            f'stroke="{color}" stroke-width="0.8"/>')


def _txt(x, y, s, size=4, fill="#ffffff", anchor="start", weight="normal"):
    return (f'<text x="{x:g}" y="{y:g}" font-family="DejaVu Sans, sans-serif" '
            f'font-size="{size:g}" fill="{fill}" text-anchor="{anchor}" '
            f'font-weight="{weight}">{s}</text>')


# --------------------------------------------------------------------------
# breadboard art
# --------------------------------------------------------------------------

def bb_max6675():
    w, h = 88.6, 74.4
    xs = [26.3 + i * 9 for i in range(5)]
    names = ["VIN", "GND", "SCK", "CS", "SO"]
    b = ['<rect x="0.6" y="0.6" width="87.4" height="73.2" rx="4" fill="#185a94" '
         'stroke="#0b3559" stroke-width="1"/>']
    # header pins + labels
    for x, n in zip(xs, names):
        b.append(f'<rect x="{x-1.6:g}" y="68" width="3.2" height="7" rx="1" '
                 f'fill="#d4af37" stroke="#8a6d1f" stroke-width="0.4"/>')
        b.append(_txt(x, 64.5, n, 3.0, "#ffffff", "middle"))
    # chip
    b.append('<rect x="31" y="24" width="20" height="20" rx="1.5" fill="#1b1b1b" '
             'stroke="#000" stroke-width="0.6"/>')
    for i in range(4):
        y = 27 + i * 4.6
        b.append(f'<rect x="27.6" y="{y:g}" width="3.4" height="2" fill="#cfcfcf"/>')
        b.append(f'<rect x="51" y="{y:g}" width="3.4" height="2" fill="#cfcfcf"/>')
    b.append(_txt(41, 35, "MAX", 4.2, "#cfcfcf", "middle", "bold"))
    b.append(_txt(41, 40, "6675", 4.2, "#cfcfcf", "middle", "bold"))
    # screw terminal
    b.append('<rect x="66" y="20" width="21" height="34" rx="2" fill="#2e7d32" '
             'stroke="#1b4d20" stroke-width="0.8"/>')
    b.append(_txt(76.5, 17, "T+  T-", 3.2, "#ffffff", "middle"))
    for y, lab in ((32, "+"), (50, "-")):
        b.append(f'<circle cx="76.5" cy="{y}" r="4.2" fill="#a5d6a7" '
                 f'stroke="#1b4d20" stroke-width="0.8"/>')
        b.append(f'<rect x="73.6" y="{y-0.7}" width="5.8" height="1.4" '
                 f'fill="#1b4d20"/>')
    # board label
    b.append(_txt(6, 10, "MAX6675", 6, "#ffffff", "start", "bold"))
    b.append(_txt(6, 16, "K-TYPE  SPI", 3.2, "#cfe6ff"))
    # real connector circles (ids must be unique and final)
    for i, (x, y) in enumerate([(xs[0], 74.4), (xs[1], 74.4), (xs[2], 74.4),
                                (xs[3], 74.4), (xs[4], 74.4), (80, 32), (80, 50)]):
        b.append(_pin(f"connector{i}pin", x, y))
    return _svg(w, h, "\n".join(b), "breadboard", {"icon": "\n".join(b)})


def bb_inmp441():
    w, h = 56.7, 49.6
    xs = [5.9 + i * 9 for i in range(6)]
    names = ["VDD", "GND", "LR", "BCLK", "WS", "SD"]
    b = ['<rect x="0.6" y="0.6" width="55.5" height="48.4" rx="3" fill="#3d2b56" '
         'stroke="#221735" stroke-width="1"/>']
    for x, n in zip(xs, names):
        b.append(f'<rect x="{x-1.5:g}" y="44" width="3" height="5.6" rx="0.8" '
                 f'fill="#d4af37" stroke="#8a6d1f" stroke-width="0.4"/>')
        b.append(_txt(x, 40.5, n, 2.6, "#ffffff", "middle"))
    # microphone can
    b.append('<circle cx="28.35" cy="18" r="8.4" fill="#c9ced6" stroke="#7c838d" '
             'stroke-width="0.8"/>')
    b.append('<circle cx="28.35" cy="18" r="5.2" fill="#8f959e"/>')
    b.append('<circle cx="28.35" cy="18" r="1.5" fill="#1a1a1a"/>')
    b.append('<circle cx="24.9" cy="20" r="0.8" fill="#e8e8e8"/>')
    b.append(_txt(6, 8, "INMP441", 5, "#ffffff", "start", "bold"))
    b.append(_txt(6, 12.6, "I2S MEMS MIC", 2.6, "#d9c9f0"))
    for i, (x, y) in enumerate([(xs[0], 49.6), (xs[1], 49.6), (xs[2], 49.6),
                                (xs[3], 49.6), (xs[4], 49.6), (xs[5], 49.6)]):
        b.append(_pin(f"connector{i}pin", x, y))
    return _svg(w, h, "\n".join(b), "breadboard", {"icon": "\n".join(b)})


def bb_probe():
    w, h = 140, 20
    b = []
    # leads: red = +, blue = -
    b.append('<path d="M0,0 L20,5" stroke="#c0392b" stroke-width="2.4" fill="none"/>')
    b.append('<path d="M0,18 L20,13" stroke="#2471a3" stroke-width="2.4" fill="none"/>')
    # plug / handle
    b.append('<rect x="18" y="1" width="22" height="18" rx="3" fill="#1b5e20" '
             'stroke="#0d3311" stroke-width="0.8"/>')
    for i in range(4):
        b.append(f'<rect x="{24+i*4}" y="3" width="1.2" height="14" fill="#2e7d32"/>')
    # stainless sheath
    b.append('<rect x="40" y="5" width="92" height="10" rx="5" fill="#c7ccd3" '
             'stroke="#7d848d" stroke-width="0.8"/>')
    b.append('<rect x="40" y="5" width="92" height="3.2" rx="1.6" fill="#e6eaef" '
             'opacity="0.8"/>')
    b.append('<path d="M120,5 Q136,10 120,15" fill="#b7bec7" stroke="#7d848d" '
             'stroke-width="0.8"/>')
    b.append(_txt(52, 3.4, "K-TYPE  class 1", 3.0, "#1a1a1a"))
    b.append(_pin("connector0pin", 0, 0, 1.6, "#c0392b"))
    b.append(_pin("connector1pin", 0, 18, 1.6, "#2471a3"))
    return _svg(w, h, "\n".join(b), "breadboard", {"icon": "\n".join(b)})


def bb_fan():
    w, h = 80, 80
    b = ['<rect x="1" y="1" width="78" height="78" rx="9" fill="#1c1c1c" '
         'stroke="#000" stroke-width="1"/>',
         '<circle cx="40" cy="40" r="32" fill="#0c0c0c" stroke="#2a2a2a" '
         'stroke-width="1"/>']
    # 5 blades
    for i in range(5):
        a = i * 72
        b.append(f'<path d="M40,40 Q30,22 44,14 Q54,24 46,38 Z" fill="#3a3a3a" '
                 f'stroke="#555" stroke-width="0.4" transform="rotate({a} 40 40)"/>')
    b.append('<circle cx="40" cy="40" r="9" fill="#2b2b2b" stroke="#555" '
             'stroke-width="0.6"/>')
    b.append('<circle cx="40" cy="40" r="3" fill="#111"/>')
    for x, y in ((7, 7), (73, 7), (7, 73), (73, 73)):
        b.append(f'<circle cx="{x}" cy="{y}" r="2.4" fill="#0c0c0c" '
                 f'stroke="#444" stroke-width="0.6"/>')
    b.append('<path d="M0,20 L12,20" stroke="#c0392b" stroke-width="2.2"/>')
    b.append('<path d="M0,60 L12,60" stroke="#1a1a1a" stroke-width="2.2"/>')
    b.append(_txt(62, 78, "5V", 3.4, "#dddddd", "end"))
    b.append(_pin("connector0pin", 0, 20, 1.6, "#c0392b"))
    b.append(_pin("connector1pin", 0, 60, 1.6, "#1a1a1a"))
    return _svg(w, h, "\n".join(b), "breadboard", {"icon": "\n".join(b)})


# --------------------------------------------------------------------------
# schematic art (box symbol, pins on the outside)
# --------------------------------------------------------------------------

def sch_box(w, h, title, pins, side_pins=()):
    """pins: [(cid, name, x, y, side)] with the tip coordinate."""
    b = [f'<rect x="10" y="8" width="{w-20:g}" height="{h-16:g}" rx="2" '
         f'fill="#fdf6e3" stroke="#6b4f1d" stroke-width="1.2"/>',
         _txt(w / 2, 20, title, 5.5, "#3b2a12", "middle", "bold")]
    for cid, name, x, y, side in pins:
        bx = 10 if side == "L" else w - 10
        b.append(f'<line x1="{bx:g}" y1="{y:g}" x2="{x:g}" y2="{y:g}" '
                 f'stroke="#6b4f1d" stroke-width="0.9"/>')
        b.append(_txt(bx + (2 if side == "L" else -2), y - 1.6, name,
                      3.2, "#3b2a12", "start" if side == "L" else "end"))
        b.append(f'<circle id="{cid}terminal" cx="{bx:g}" cy="{y:g}" r="1.1" '
                 f'fill="#6b4f1d"/>')
        b.append(f'<circle id="{cid}pin" cx="{x:g}" cy="{y:g}" r="1.8" '
                 f'fill="none" stroke="#1f618d" stroke-width="0.9"/>')
    return _svg(w, h, "\n".join(b), "schematic")


def sch_max6675():
    w, h = 96, 74
    pins = [("connector0", "VIN", 0, 28, "L"),
            ("connector1", "GND", 0, 38, "L"),
            ("connector2", "SCLK", 0, 48, "L"),
            ("connector3", "CS", 0, 58, "L"),
            ("connector4", "SO", 0, 68, "L"),
            ("connector5", "T+", w, 38, "R"),
            ("connector6", "T-", w, 58, "R")]
    return sch_box(w, h, "MAX6675", pins)


def sch_inmp441():
    w, h = 86, 74
    pins = [("connector0", "VDD", 0, 22, "L"),
            ("connector1", "GND", 0, 32, "L"),
            ("connector2", "L/R", 0, 42, "L"),
            ("connector3", "BCLK", 0, 52, "L"),
            ("connector4", "WS", 0, 62, "L"),
            ("connector5", "SD", 0, 72, "L")]
    return sch_box(w, h, "INMP441", pins)


def sch_probe():
    w, h = 56, 40
    pins = [("connector0", "T+", 0, 15, "L"), ("connector1", "T-", 0, 30, "L")]
    return sch_box(w, h, "K probe", pins)


def sch_fan():
    w, h = 56, 40
    pins = [("connector0", "+5V", 0, 15, "L"), ("connector1", "GND", 0, 30, "L")]
    return sch_box(w, h, "Fan 5V", pins)


# --------------------------------------------------------------------------
# pcb art (simple pads)
# --------------------------------------------------------------------------

def pcb_pads(w, h, pins, label):
    pads = [f'<rect x="0" y="0" width="{w:g}" height="{h:g}" fill="#333" opacity="0.25"/>']
    for i, (x, y) in enumerate(pins):
        pads.append(f'<circle id="connector{i}pad" cx="{x:g}" cy="{y:g}" r="4.5" '
                    f'fill="#c9a227" stroke="#8a6d1f" stroke-width="0.6"/>')
        pads.append(f'<circle cx="{x:g}" cy="{y:g}" r="2" fill="#333"/>')
    silk = _txt(w / 2, h - 3, label, 4, "#ffffff", "middle")
    return _svg(w, h, "\n".join(pads), "copper0",
                {"copper1": "\n".join(pads), "silkscreen": silk})


# --------------------------------------------------------------------------
# fzp writer
# --------------------------------------------------------------------------

def write_fzp(name, module_id, title, pins, w, h, description=""):
    """pins: [(connector_id, name, breadboard (x,y), schematic (x,y), pcb (x,y))]"""
    def q(s):
        return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    L = ['<?xml version="1.0" encoding="UTF-8"?>',
         f'<module fritzingVersion="1.0" moduleId="{module_id}">',
         '  <version>1.0</version>',
         '  <date>2026-10-26</date>',
         '  <author>Ammar - capstone PDM rig</author>',
         f'  <title>{q(title)}</title>',
         f'  <description>{q(description)}</description>',
         '  <tags><tag>capstone</tag><tag>predictive maintenance</tag></tags>',
         '  <properties>',
         f'    <property name="family">{q(title)}</property>',
         '    <property name="Interface">3V3</property>',
         '  </properties>',
         '  <views>',
         f'    <breadboardView><layers image="breadboard/{name}.svg">'
         f'<layer layerId="breadboard"/></layers></breadboardView>',
         f'    <schematicView><layers image="schematic/{name}.svg">'
         f'<layer layerId="schematic"/></layers></schematicView>',
         f'    <pcbView><layers image="pcb/{name}.svg"><layer layerId="copper1"/>'
         f'<layer layerId="silkscreen"/><layer layerId="copper0"/></layers></pcbView>',
         f'    <iconView><layers image="breadboard/{name}.svg">'
         f'<layer layerId="icon"/></layers></iconView>',
         '  </views>',
         '  <connectors>']
    for cid, cname, bb, sch, pcb in pins:
        L += [f'    <connector id="{cid}" type="male" name="{q(cname)}">',
              f'      <description>{q(cname)}</description>',
              '      <views>',
              f'        <breadboardView><p layer="breadboard" svgId="{cid}pin"/></breadboardView>',
              f'        <schematicView><p layer="schematic" svgId="{cid}pin" '
              f'terminalId="{cid}terminal"/></schematicView>',
              f'        <pcbView><p layer="copper0" svgId="{cid}pad"/>'
              f'<p layer="copper1" svgId="{cid}pad"/></pcbView>',
              '      </views>',
              '    </connector>']
    L += ['  </connectors>', '</module>', '']
    return "\n".join(L)


def build_all():
    """Write parts/<name>/... for the four custom parts; return metadata."""
    specs = []

    # MAX6675 module
    name, mid = "max6675", "PDM_MAX6675"
    pins = [("connector0", "VIN", (26.3, 74.4), (0, 28), (6, 10)),
            ("connector1", "GND", (35.3, 74.4), (0, 38), (14, 10)),
            ("connector2", "SCLK", (44.3, 74.4), (0, 48), (22, 10)),
            ("connector3", "CS", (53.3, 74.4), (0, 58), (30, 10)),
            ("connector4", "SO", (62.3, 74.4), (0, 68), (38, 10)),
            ("connector5", "T+", (80, 32), (96, 38), (48, 8)),
            ("connector6", "T-", (80, 50), (96, 58), (48, 16))]
    _emit(name, mid, "MAX6675 K-type thermocouple module", pins,
          bb_max6675(), sch_max6675(), pcb_pads(56, 24, [(6 + i * 8, 10) for i in range(5)] +
                                                [(48, 8), (48, 16)], "MAX6675"))
    specs.append((name, mid))

    name, mid = "inmp441", "PDM_INMP441"
    pins = [("connector0", "VDD", (5.9, 49.6), (0, 22), (4, 10)),
            ("connector1", "GND", (14.9, 49.6), (0, 32), (12, 10)),
            ("connector2", "LR", (23.9, 49.6), (0, 42), (20, 10)),
            ("connector3", "BCLK", (32.9, 49.6), (0, 52), (28, 10)),
            ("connector4", "WS", (41.9, 49.6), (0, 62), (36, 10)),
            ("connector5", "SD", (50.9, 49.6), (0, 72), (44, 10))]
    _emit(name, mid, "INMP441 I2S MEMS microphone", pins,
          bb_inmp441(), sch_inmp441(), pcb_pads(52, 22, [(4 + i * 8, 10) for i in range(6)], "INMP441"))
    specs.append((name, mid))

    name, mid = "kprobe", "PDM_KPROBE"
    pins = [("connector0", "T+", (0, 0), (0, 15), (4, 8)),
            ("connector1", "T-", (0, 18), (0, 30), (4, 16))]
    _emit(name, mid, "K-type thermocouple probe (class 1)", pins,
          bb_probe(), sch_probe(), pcb_pads(20, 24, [(4, 8), (4, 16)], "K"))
    specs.append((name, mid))

    name, mid = "fan5v", "PDM_FAN5V"
    pins = [("connector0", "+5V", (0, 20), (0, 15), (4, 8)),
            ("connector1", "GND", (0, 60), (0, 30), (4, 16))]
    _emit(name, mid, "5 V cooling fan 30 mm", pins,
          bb_fan(), sch_fan(), pcb_pads(40, 40, [(4, 8), (4, 16)], "FAN"))
    specs.append((name, mid))
    return specs


def _emit(name, module_id, title, pins, bb, sch, pcb):
    d = os.path.join(PARTS_DIR, name)
    for sub in ("breadboard", "schematic", "pcb"):
        os.makedirs(os.path.join(d, sub), exist_ok=True)
    open(os.path.join(d, "breadboard", name + ".svg"), "w").write(bb)
    open(os.path.join(d, "schematic", name + ".svg"), "w").write(sch)
    open(os.path.join(d, "pcb", name + ".svg"), "w").write(pcb)
    fzp_pins = [(cid, cname, bb_p, sch_p, pcb_p) for cid, cname, bb_p, sch_p, pcb_p in pins]
    open(os.path.join(d, name + ".fzp"), "w").write(
        write_fzp(name, module_id, title, fzp_pins, 0, 0))


if __name__ == "__main__":
    for name, mid in build_all():
        print(name, mid)
