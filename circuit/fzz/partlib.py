"""Minimal Fritzing part-geometry reader.

Internal sketch units are 1/90 inch (Fritzing's canonical unit), so a
0.1 in breadboard pitch is 9.0 sketch units.

For a part, every connector has
  anchor  : where the leg attaches to the body (bendable parts) or the
            pin itself (fixed parts), in sketch units, origin = SVG top-left
  tip     : the electrical end point (leg tip, or pin centre), sketch units
  leg     : (dx, dy) from anchor to tip; (0,0) for fixed pins
"""
from __future__ import annotations

import math
import os
import re
import xml.etree.ElementTree as ET

PARTS_ROOT = os.environ.get("FRITZING_PARTS", "/tmp/opencode/fritzing-parts")
UNITS_PER_INCH = 90.0


def _strip_ns(tag):
    return tag.rsplit("}", 1)[-1]


def _elements(root):
    for el in root.iter():
        yield el


def _num(el, name, default=0.0):
    try:
        return float(el.get(name, default))
    except (TypeError, ValueError):
        return default


def _path_points(d):
    """Very small path reader: every coordinate pair in d, in order."""
    toks = re.findall(r"[MmLlHhVvCcSsQqTtAaZz]|-?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?", d or "")
    pts = []
    cmd = None
    i = 0
    cur = (0.0, 0.0)
    while i < len(toks):
        t = toks[i]
        if re.match(r"[A-Za-z]", t):
            cmd = t
            i += 1
            if cmd in "Zz":
                continue
        if i >= len(toks):
            break
        if cmd in "MmLl":
            x = float(toks[i]); y = float(toks[i + 1]); i += 2
            if cmd.islower():
                x += cur[0]; y += cur[1]
            cur = (x, y)
            pts.append(cur)
            cmd = "L" if cmd == "M" else ("l" if cmd == "m" else cmd)
        elif cmd in "Hh":
            x = float(toks[i]); i += 1
            if cmd == "h":
                x += cur[0]
            cur = (x, cur[1]); pts.append(cur)
        elif cmd in "Vv":
            y = float(toks[i]); i += 1
            if cmd == "v":
                y += cur[1]
            cur = (cur[0], y); pts.append(cur)
        elif cmd in "Cc":
            # last pair is the on-curve end point
            vals = [float(v) for v in toks[i:i + 6]]
            i += 6
            if len(vals) < 6:
                break
            x, y = vals[4], vals[5]
            if cmd == "c":
                x += cur[0]; y += cur[1]
            cur = (x, y); pts.append(cur)
        elif cmd in "SsQq":
            vals = [float(v) for v in toks[i:i + 4]]
            i += 4
            if len(vals) < 4:
                break
            x, y = vals[2], vals[3]
            if cmd in "sq":
                x += cur[0]; y += cur[1]
            cur = (x, y); pts.append(cur)
        elif cmd in "Tt":
            x = float(toks[i]); y = float(toks[i + 1]); i += 2
            if cmd == "t":
                x += cur[0]; y += cur[1]
            cur = (x, y); pts.append(cur)
        elif cmd in "Aa":
            vals = [float(v) for v in toks[i:i + 7]]
            i += 7
            if len(vals) < 7:
                break
            x, y = vals[5], vals[6]
            if cmd == "a":
                x += cur[0]; y += cur[1]
            cur = (x, y); pts.append(cur)
        else:
            i += 1
    return pts


def _element_bbox(el):
    """Axis-aligned bbox of a simple SVG element (absolute, no transforms)."""
    tag = _strip_ns(el.tag)
    if tag == "circle":
        cx, cy, r = _num(el, "cx"), _num(el, "cy"), _num(el, "r")
        return (cx - r, cy - r, cx + r, cy + r)
    if tag == "ellipse":
        cx, cy = _num(el, "cx"), _num(el, "cy")
        rx, ry = _num(el, "rx"), _num(el, "ry")
        return (cx - rx, cy - ry, cx + rx, cy + ry)
    if tag == "rect":
        x, y = _num(el, "x"), _num(el, "y")
        w, h = _num(el, "width"), _num(el, "height")
        return (x, y, x + w, y + h)
    if tag == "line":
        x1, y1 = _num(el, "x1"), _num(el, "y1")
        x2, y2 = _num(el, "x2"), _num(el, "y2")
        return (min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2))
    if tag in ("polygon", "polyline"):
        raw = el.get("points", "")
        vals = [float(v) for v in re.findall(r"-?(?:\d+\.?\d*|\.\d+)", raw)]
        pts = list(zip(vals[0::2], vals[1::2]))
        if not pts:
            return None
        xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
        return (min(xs), min(ys), max(xs), max(ys))
    if tag == "path":
        pts = _path_points(el.get("d", ""))
        if not pts:
            return None
        xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
        return (min(xs), min(ys), max(xs), max(ys))
    if tag == "g":
        boxes = []
        for child in el:
            b = _element_bbox(child)
            if b:
                boxes.append(b)
        if not boxes:
            return None
        return (min(b[0] for b in boxes), min(b[1] for b in boxes),
                max(b[2] for b in boxes), max(b[3] for b in boxes))
    return None


def _center(box):
    return ((box[0] + box[2]) / 2.0, (box[1] + box[3]) / 2.0)


class SvgView:
    def __init__(self, path):
        self.path = path
        self.tree = ET.parse(path)
        self.root = self.tree.getroot()
        self.by_id = {}
        for el in _elements(self.root):
            i = el.get("id")
            if i and i not in self.by_id:
                self.by_id[i] = el
        self.scale = self._scale()

    def _scale(self):
        root = self.root
        vb = root.get("viewBox")
        if not vb:
            return 1.0
        vbw = float(vb.replace(",", " ").split()[2])
        w = root.get("width", "")
        m = re.match(r"([\d.]+)\s*([a-zA-Z]*)", w or "")
        if not m or not vbw:
            return 1.0
        val, unit = float(m.group(1)), (m.group(2) or "px").lower()
        if unit == "in":
            inches = val
        elif unit == "mm":
            inches = val / 25.4
        elif unit in ("cm",):
            inches = val / 2.54
        elif unit in ("pt",):
            inches = val / 72.0
        elif unit in ("pc",):
            inches = val / 6.0
        else:  # px: Fritzing's drawing convention is 72 px/in
            inches = val / 72.0
        return UNITS_PER_INCH * inches / vbw

    def center(self, element_id):
        el = self.by_id.get(element_id)
        if el is None:
            return None
        b = _element_bbox(el)
        return None if b is None else _center(b)

    def body_center(self):
        """Centre of the visible part, ignoring connector helpers."""
        boxes = []
        for el in _elements(self.root):
            i = el.get("id") or ""
            if i.startswith("connector"):
                continue
            if _strip_ns(el.tag) in ("svg", "g", "defs", "title", "desc", "metadata"):
                continue
            b = _element_bbox(el)
            if b:
                boxes.append(b)
        if not boxes:
            return (0.0, 0.0)
        b = (min(x[0] for x in boxes), min(x[1] for x in boxes),
             max(x[2] for x in boxes), max(x[3] for x in boxes))
        return _center(b)

    def leg_points(self, element_id):
        el = self.by_id.get(element_id)
        if el is None:
            return None
        tag = _strip_ns(el.tag)
        if tag == "line":
            return ((_num(el, "x1"), _num(el, "y1")), (_num(el, "x2"), _num(el, "y2")))
        if tag in ("path", "polyline", "polygon"):
            pts = _path_points(el.get("d", "")) if tag == "path" else \
                [tuple(map(float, p.split(","))) for p in el.get("points", "").split()]
            if len(pts) >= 2:
                return (pts[0], pts[-1])
        b = _element_bbox(el)
        if b:
            return (b[:2], b[2:])
        return None


class Connector:
    def __init__(self, cid, name, ctype, anchor, tip, leg, svg_id, leg_id):
        self.id = cid
        self.name = name
        self.type = ctype
        self.anchor = anchor      # sketch units
        self.tip = tip            # sketch units
        self.leg = leg            # (dx, dy) sketch units, or (0,0)
        self.svg_id = svg_id
        self.leg_id = leg_id

    def __repr__(self):
        return f"<{self.id} {self.name} tip=({self.tip[0]:.2f},{self.tip[1]:.2f})>"


class Part:
    def __init__(self, fzp_path):
        self.fzp_path = fzp_path
        self.root = ET.parse(fzp_path).getroot()
        self.module_id = self.root.get("moduleId")
        self.title = self.root.findtext("title") or self.module_id
        self.properties = []
        props = self.root.find("properties")
        if props is not None:
            for p in props:
                self.properties.append((p.get("name"), p.get("value")))
        self.buses = {}
        for bus in self.root.findall("buses/bus"):
            bid = bus.get("id")
            for n in bus:
                self.buses[n.get("connectorId")] = bid
        self.views = {}
        for v in self.root.find("views"):
            if v.tag in ("iconView", "breadboardView", "schematicView", "pcbView"):
                layers = v.find("layers")
                if layers is not None and layers.get("image"):
                    self.views[v.tag] = layers.get("image")
        self.parts_root = os.path.dirname(os.path.dirname(os.path.abspath(fzp_path)))
        self.bucket = os.path.basename(os.path.dirname(os.path.abspath(fzp_path)))
        self.svg_paths = {}
        for view, img in self.views.items():
            # Staged part: image paths are relative to the fzp itself.
            # Community library: svg/<bucket>/<image> under the repo root.
            candidates = [
                os.path.join(os.path.dirname(os.path.abspath(fzp_path)), img),
                os.path.join(self.parts_root, "svg", self.bucket, img),
            ]
            for p in candidates:
                if os.path.exists(p):
                    self.svg_paths[view] = p
                    break
        self.connectors = []
        self._read_breadboard_connectors()

    def svg(self, view):
        p = self.svg_paths.get(view)
        return SvgView(p) if p and os.path.exists(p) else None

    def _read_breadboard_connectors(self):
        svg = self.svg("breadboardView")
        if svg is None:
            return
        body = svg.body_center()
        for c in self.root.findall("connectors/connector"):
            cid, name, ctype = c.get("id"), c.get("name"), c.get("type")
            p = c.find("views/breadboardView/p")
            if p is None:
                continue
            svg_id, leg_id = p.get("svgId"), p.get("legId")
            if leg_id:
                pts = svg.leg_points(leg_id)
                if not pts:
                    continue
                a, b = pts
                # root = endpoint nearer the body, tip = the other
                da = math.dist(a, body); db = math.dist(b, body)
                root, tip = (a, b) if da <= db else (b, a)
                anchor = (root[0] * svg.scale, root[1] * svg.scale)
                tip_s = (tip[0] * svg.scale, tip[1] * svg.scale)
                leg = (tip_s[0] - anchor[0], tip_s[1] - anchor[1])
                self.connectors.append(Connector(cid, name, ctype, anchor, tip_s, leg, svg_id, leg_id))
            else:
                ctr = svg.center(svg_id)
                if ctr is None:
                    # some parts put the id on a <g> or use a terminal
                    ctr = svg.center(svg_id.replace("pin", "")) or (0.0, 0.0)
                pt = (ctr[0] * svg.scale, ctr[1] * svg.scale)
                self.connectors.append(Connector(cid, name, ctype, pt, pt, (0.0, 0.0), svg_id, None))

    def connector(self, cid):
        for c in self.connectors:
            if c.id == cid:
                return c
        raise KeyError(cid)


class Board:
    """Breadboard hole grid + bus membership."""

    def __init__(self, part: Part):
        self.part = part
        self.by_id = {c.id: c for c in part.connectors}
        self.bus = part.buses
        self.rows = {}
        self.cols = {}
        for cid, c in self.by_id.items():
            m = re.fullmatch(r"([A-Z]+)(\d+)", cid)
            if m:
                row, col = m.group(1), int(m.group(2))
                self.rows.setdefault(row, {})[col] = c.tip
                self.cols.setdefault(col, {})[row] = c.tip
        self.row_letters = sorted(self.rows)
        self.col_ids = sorted(self.cols)

    def hole(self, row, col, origin=(0.0, 0.0)):
        p = self.rows[row][col]
        return (origin[0] + p[0], origin[1] + p[1])

    def id(self, row, col):
        for cid, c in self.by_id.items():
            m = re.fullmatch(r"([A-Z]+)(\d+)", cid)
            if m and m.group(1) == row and int(m.group(2)) == col:
                return cid
        raise KeyError((row, col))

    def bus_of(self, row, col):
        return self.bus.get(self.id(row, col))
