"""layout.py - place every part and assign every pin a coordinate.

Coordinate system: Fritzing sketch units, 90 per inch.  The breadboard's
top-left is (0, 0).  Holes are on a 0.1 in (9 unit) grid.

Placement summary
-----------------
* breadboard  : origin (0,0), 840-point board
* modules     : pins in row J, bodies above (rows F..I), so every wire leaves
                the pin row downwards into the free lane band
* passives    : decoupling bank in row E on the top rails; series parts in
                row J on the right
* Raspberry Pi: below the board, header facing the board, columns aligned to
                the breadboard grid (so power taps are straight)
* probe / fan : off-board right, short leads to the MAX6675 terminal / rails
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from design import COMPS, NETS
from partlib import Board
from stage import stage_all, stage_custom

# design pin name -> part connector id.  Resistors are symmetric, so R2/R4
# intentionally map "1" to the right-hand connector: it keeps the series
# chain (GPIO16 -> R4 -> LED A -> LED K -> GND) short and crossing-free.
PINS = {
    "U1": {"3V3_A": "connector0", "SDA": "connector2", "SCL": "connector4",
           "GND_9": "connector8", "BCLK": "connector11", "GND_14": "connector13",
           "3V3_B": "connector16", "MOSI": "connector18", "MISO": "connector20",
           "SCLK": "connector22", "CE0": "connector23", "GND_25": "connector24",
           "WS": "connector34", "LED": "connector35", "DIN": "connector37",
           "GND_39": "connector38", "5V": "connector3", "GND_6": "connector5"},
    "U2": {"VCC": "connector7", "GND": "connector6", "CS": "connector8",
           "SDO": "connector11", "SDA": "connector12", "SCL": "connector13"},
    "U3": {"VIN": "connector0", "GND": "connector1", "SCLK": "connector2",
           "CS": "connector3", "SO": "connector4", "TP": "connector5",
           "TN": "connector6"},
    "U4": {"VDD": "connector0", "GND": "connector1", "LR": "connector2",
           "BCLK": "connector3", "WS": "connector4", "SD": "connector5"},
    "R1": {"P": "connector0", "N": "connector1"},
    "R2": {"1": "connector1", "2": "connector0"},
    "R4": {"1": "connector1", "2": "connector0"},
    "C1": {"1": "connector0", "2": "connector1"},
    "C2": {"1": "connector0", "2": "connector1"},
    "C3": {"1": "connector0", "2": "connector1"},
    "C4": {"1": "connector1", "2": "connector0"},
    "D1": {"A": "connector1", "K": "connector0"},
    "F1": {"P": "connector0", "N": "connector1"},
}

# custom parts drawn by custom.py: name -> (moduleId, pin tip locals)
CUSTOM = {
    "max6675": ("PDM_MAX6675", {
        "VIN": (26.3, 74.4), "GND": (35.3, 74.4), "SCLK": (44.3, 74.4),
        "CS": (53.3, 74.4), "SO": (62.3, 74.4), "TP": (80.0, 32.0), "TN": (80.0, 50.0)}),
    "inmp441": ("PDM_INMP441", {
        "VDD": (5.9, 49.6), "GND": (14.9, 49.6), "LR": (23.9, 49.6),
        "BCLK": (32.9, 49.6), "WS": (41.9, 49.6), "SD": (50.9, 49.6)}),
    "probe": ("PDM_KPROBE", {
        "P": (0.0, 0.0), "N": (0.0, 18.0)}),
    "fan": ("PDM_FAN5V", {
        "P": (0.0, 20.0), "N": (0.0, 60.0)}),
}


class PartView:
    """Geometry for one part: fixed pins or bendable legs."""

    def __init__(self, ref, part, origin, leg=None, holes=None, pinmap=None):
        self.ref = ref
        self.part = part
        self.origin = origin
        self.leg = leg or {}          # connector id -> (dx, dy) custom leg
        self.holes = holes or {}      # connector id -> hole id (pin in hole)
        self.pinmap = pinmap or {}    # design pin -> connector id

    def tip(self, cid):
        c = self.part.connector(cid)
        if cid in self.leg:
            dx, dy = self.leg[cid]
            return (self.origin[0] + c.anchor[0] + dx,
                    self.origin[1] + c.anchor[1] + dy)
        return (self.origin[0] + c.tip[0], self.origin[1] + c.tip[1])

    def pin(self, design_pin):
        return self.tip(self.pinmap[design_pin])


class Layout:
    def __init__(self):
        self.parts = stage_all()
        self.parts.update(stage_custom())
        self.board = Board(self.parts["bb840"])
        self.board_view = PartView("BB1", self.parts["bb840"], (0.0, 0.0))
        self.views = {}
        self.wires = []          # (net, [(x,y), ...])
        self._place()

    # ---- helpers -----------------------------------------------------
    def hole(self, row, col):
        return self.board.hole(row, col)

    def fixed(self, ref, part, pin_cid, point):
        c = part.connector(pin_cid)
        v = PartView(ref, part, (point[0] - c.tip[0], point[1] - c.tip[1]))
        # every pin that lands on a hole becomes an explicit pin-in-hole edge
        for cc in part.connectors:
            p = v.tip(cc.id)
            try:
                v.holes[cc.id] = self.hole_id(p)
            except KeyError:
                pass
        return v

    def legs(self, ref, part, tips, body_row):
        """Place a bendable part so its leg tips land exactly on `tips`.

        The body is positioned on `body_row` (the y of the tip anchors), then
        each leg is bent to its hole.  This is exactly what a Fritzing user
        does when dragging a resistor/LED/capacitor onto the board.
        """
        ids = list(tips)
        # align the body to the mean anchor position
        ax = sum(part.connector(c).anchor[0] for c in ids) / len(ids)
        ay = sum(part.connector(c).anchor[1] for c in ids) / len(ids)
        mx = sum(tips[c][0] for c in ids) / len(ids)
        my = sum(tips[c][1] for c in ids) / len(ids)
        origin = (mx - ax, my - ay)
        leg = {}
        for c in ids:
            cc = part.connector(c)
            leg[c] = (tips[c][0] - origin[0] - cc.anchor[0],
                      tips[c][1] - origin[1] - cc.anchor[1])
        holes = {c: self.hole_id(tips[c]) for c in ids}
        return PartView(ref, part, origin, leg=leg, holes=holes)

    def hole_id(self, point):
        for c in self.board.part.connectors:
            if abs(c.tip[0] - point[0]) < 0.01 and abs(c.tip[1] - point[1]) < 0.01:
                return c.id
        raise KeyError(point)

    def add(self, view, pinmap):
        view.pinmap = pinmap
        self.views[view.ref] = view
        return view

    # ---- placement ---------------------------------------------------
    def _place(self):
        P = self.parts
        self.add(self.fixed("U2", P["adxl345"], "connector6", self.hole("J", 3)), PINS["U2"])
        self.add(self.fixed("U4", P["inmp441"], "connector0", self.hole("J", 15)), PINS["U4"])
        self.add(self.fixed("U3", P["max6675"], "connector0", self.hole("J", 23)), PINS["U3"])

        # decoupling bank, row E, on the top rails (W=3V3, X=GND)
        for ref, part, c0, c1 in (
                ("C1", "cap_cer", ("E", 4), ("E", 5)),
                ("C2", "cap_cer", ("E", 7), ("E", 8)),
                ("C3", "cap_cer", ("E", 10), ("E", 11)),
                ("C4", "cap_elec", ("E", 13), ("E", 14))):
            self.add(self.legs(ref, P[part],
                               {"connector0": self.hole(*c0), "connector1": self.hole(*c1)},
                               body_row=81), PINS[ref])

        # series resistors, row J right of the MAX6675
        self.add(self.legs("R2", P["resistor"],
                           {"connector0": self.hole("J", 33), "connector1": self.hole("J", 37)},
                           body_row=144), PINS["R2"])
        self.add(self.legs("R4", P["resistor"],
                           {"connector0": self.hole("J", 45), "connector1": self.hole("J", 49)},
                           body_row=144), PINS["R4"])
        self.add(self.legs("D1", P["led5"],
                           {"connector0": self.hole("J", 42), "connector1": self.hole("J", 43)},
                           body_row=144), PINS["D1"])

        # off-board right
        probe = P["kprobe"]
        self.add(PartView("R1", probe, (620.0, 101.6)), PINS["R1"])
        fan = P["fan5v"]
        self.add(PartView("F1", fan, (620.0, 195.0)), PINS["F1"])

        # Raspberry Pi, header columns aligned to breadboard columns
        pi = P["pi4b"]
        origin = (211.65 - pi.connector("connector0").tip[0], 250.0)
        self.add(PartView("U1", pi, origin), PINS["U1"])

    # ---- reporting ---------------------------------------------------
    def dump(self):
        for ref in ("U1", "U2", "U3", "U4", "R1", "R2", "R4", "C1", "C2", "C3", "C4", "D1", "F1"):
            v = self.views[ref]
            print(f"== {ref} {v.part.title}  origin=({v.origin[0]:.3f},{v.origin[1]:.3f})")
            for dp, cid in v.pinmap.items():
                x, y = v.pin(dp)
                h = v.holes.get(cid, "")
                print(f"   {dp:6s} {cid:11s} ({x:8.3f},{y:8.3f}) {h}")


if __name__ == "__main__":
    lay = Layout()
    lay.dump()
