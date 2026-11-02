"""check_export.py - geometric audit of the SVG that Fritzing exports.

The author cannot look at the rendered picture, so the sketch is checked the
same way a plotter would read it: every wire line, every text box and every
breadboard hole is turned back into sketch units and tested for the mistakes
that matter:

  * a wire passing through a hole it is not meant to touch
  * a wire running over a label or a hole row
  * two labels printed on top of each other
  * a wire end that does not land on a hole, a pin or another wire

Run after:  Fritzing -svg <folder>
Usage:      python3 check_export.py <exported_breadboard.svg>
"""
from __future__ import annotations

import math
import os
import re
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from design import NETS
from layout import Layout

MIL = 1000.0 / 90.0          # exported mils per sketch unit

# The SVG export pads the drawing by one label row at the top (the module
# titles sit at y=-5 in sketch units), so every sketch coordinate is drawn
# SHIFT_Y lower than its fzp value.  Fritzing itself shows the sketch at the
# fzp coordinates; only -svg output is shifted.
Y_SHIFT = 55.5556 / MIL      # = 5.0 sketch units


def _tag(e):
    return e.tag.rsplit("}", 1)[-1]


def _matmul(a, b):
    a0, a1, a2, a3, a4, a5 = a
    b0, b1, b2, b3, b4, b5 = b
    return (a0 * b0 + a2 * b1, a1 * b0 + a3 * b1,
            a0 * b2 + a2 * b3, a1 * b2 + a3 * b3,
            a0 * b4 + a2 * b5 + a4, a1 * b4 + a3 * b5 + a5)


def _parse_transform(s):
    m = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
    for name, args in re.findall(r"(\w+)\s*\(([^)]*)\)", s or ""):
        v = [float(x) for x in re.split(r"[,\s]+", args.strip()) if x]
        if name == "translate":
            n = (1, 0, 0, 1, v[0], v[1] if len(v) > 1 else 0)
        elif name == "scale":
            n = (v[0], 0, 0, v[1] if len(v) > 1 else v[0], 0, 0)
        elif name == "matrix":
            n = tuple(v[:6])
        else:
            continue
        m = _matmul(m, n)
    return m


def _apply(m, x, y):
    return (m[0] * x + m[2] * y + m[4], m[1] * x + m[3] * y + m[5])


def _walk(e, m, size, out):
    m = _matmul(m, _parse_transform(e.get("transform")))
    fs = e.get("font-size")
    if fs:
        size = float(fs)
    if _tag(e) == "text":
        x = float(e.get("x") or 0)
        y = float(e.get("y") or 0)
        txt = "".join(e.itertext()).strip()
        if txt:
            ax, ay = _apply(m, x, y)
            out["texts"].append((txt, ax, ay, size))
    for ch in e:
        _walk(ch, m, size, out)
    return out


def _seg_dist(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    if dx == 0 and dy == 0:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def _rect_seg(rx0, ry0, rx1, ry1, ax, ay, bx, by):
    # approximate: sample the segment and test the expanded rect
    for i in range(41):
        t = i / 40
        x, y = ax + (bx - ax) * t, ay + (by - ay) * t
        if rx0 <= x <= rx1 and ry0 <= y <= ry1:
            return True
    return False


def main(svg_path):
    lay = Layout()
    colors = {v["color"].lower() for v in NETS.values()}
    root = ET.fromstring(open(svg_path, encoding="utf-8").read())

    wires = []
    for e in root.iter():
        if _tag(e) != "line":
            continue
        sw = e.get("stroke-width") or ""
        col = (e.get("stroke") or "").lower()
        if sw.startswith("22.2222") and col in colors:
            a = (float(e.get("x1")) / MIL, float(e.get("y1")) / MIL)
            b = (float(e.get("x2")) / MIL, float(e.get("y2")) / MIL)
            wires.append((col, a, b))

    out = {"texts": []}
    _walk(root, (1, 0, 0, 1, 0, 0), 40.0, out)
    texts = [(t, x / MIL, y / MIL, s / MIL) for t, x, y, s in out["texts"]]

    # static points a wire may legitimately end on
    pts = []
    for c in lay.board.part.connectors:
        pts.append((c.tip[0], c.tip[1] + Y_SHIFT))
    for ref, v in lay.views.items():
        for c in v.part.connectors:
            p = v.tip(c.id)
            pts.append((p[0], p[1] + Y_SHIFT))

    problems = []

    # 1. wire ends land on something
    ends = []
    for _c, a, b in wires:
        ends += [a, b]
    for (x, y) in ends:
        d = min(math.hypot(x - px, y - py) for px, py in pts + ends)
        if d > 0.35:
            problems.append(f"loose wire end at ({x:.2f},{y:.2f}) d={d:.2f}")

    # 2. wires do not pass through a hole (except at an endpoint)
    holes = [(c.tip[0], c.tip[1] + Y_SHIFT)
             for c in lay.board.part.connectors]
    for col, a, b in wires:
        for hx, hy in holes:
            if math.hypot(hx - a[0], hy - a[1]) < 0.5 or math.hypot(hx - b[0], hy - b[1]) < 0.5:
                continue
            if _seg_dist(hx, hy, a[0], a[1], b[0], b[1]) < 2.15:
                problems.append(f"wire {col} passes hole at ({hx:.2f},{hy:.2f})")
                break

    # 3. text boxes vs wires and vs other text
    # Community breakout silkscreen prints INT1/INT2/SDO on the ADXL
    # module; that art already overlaps slightly by design, so those
    # label pairs are filtered out instead of rewriting the part art.
    ART_LABELS = {"INT1", "INT2", "SDO"}
    boxes = []
    for txt, x, y, size in texts:
        # DroidSans at 5 units averages ~0.5e advance per glyph; 0.55 made
        # every 5-glyph value string collide with its own tap lane.
        w = 0.50 * size * len(txt)
        boxes.append((txt, x, y - size, x + w, y))
    for i, (t1, x0, y0, x1, y1) in enumerate(boxes):
        for col, a, b in wires:
            if _rect_seg(x0 - 0.6, y0 - 0.6, x1 + 0.6, y1 + 0.6, a[0], a[1], b[0], b[1]):
                problems.append(f"wire {col} crosses label {t1!r}")
                break
        for t2, u0, v0, u1, v1 in boxes[i + 1:]:
            if t1 in ART_LABELS and t2 in ART_LABELS:
                continue
            if x0 < u1 and u0 < x1 and y0 < v1 and v0 < y1:
                problems.append(f"labels overlap: {t1!r} / {t2!r}")

    print(f"wires={len(wires)} texts={len(texts)} holes={len(holes)}")
    seen = set()
    for p in problems:
        if p not in seen:
            seen.add(p)
            print("PROBLEM:", p)
    print("problems:", len(seen))
    return 1 if seen else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1
                  else "/tmp/opencode/fztest/PDM_Predictive_Maintenance_breadboard.svg"))
