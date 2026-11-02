"""fzz.py - write a self-contained Fritzing sketch (.fzz).

Sketch XML is the classic Fritzing layout:

    <module>
      <views>...
      <instances>
        <instance moduleIdRef=... modelIndex=... path="<name>.fzp">
          <title>R2</title>
          <views><breadboardView layer="breadboard">
            <geometry z=... x=... y=.../>
            <connectors>
              <connector connectorId=... layer=...>
                <geometry .../><leg>...</leg><connects>...</connects>
              </connector>
            </connectors>
          </breadboardView></views>
        </instance>

The bundle is a plain zip:

    PDM_Predictive_Maintenance.fz
    part.<name>.fzp
    svg.<viewFolder>.<basename>

Fritzing's bundled-sketch loader strips the ``part.`` / ``svg.`` prefixes,
copies each part to ``contrib/<moduleId>/`` and each SVG to
``contrib/<moduleId>/<view>/<basename>``.  Because every part in this sketch
has a private ``PDM_*`` moduleId, the bundled copy is always the one that is
loaded, so the sketch cannot drift with whatever version is installed.
"""
from __future__ import annotations

import os
import zipfile
from collections import defaultdict

Z = {"board": 1.5, "part": 2.5, "wire": 3.5}


class Wire:
    def __init__(self, net, a, b, color, index):
        self.net = net
        self.a = a
        self.b = b
        self.color = color
        self.index = index

    def delta(self):
        return (round(self.b[0] - self.a[0], 4), round(self.b[1] - self.a[1], 4))


class Sketch:
    def __init__(self, lay, routes, name="PDM_Predictive_Maintenance"):
        self.lay = lay
        self.name = name
        self.views = lay.views
        self.routes = routes

        # ---- model indices -------------------------------------------
        self.mi = {}
        n = 1000
        for ref in ("bb840",):
            pass
        # board is a PartView stored separately in Layout
        self.board_mi = n
        n += 1
        for ref in self.views:
            self.mi[ref] = n
            n += 1
        self.wire_mi = {}

        # ---- connectors as geometry nodes ----------------------------
        # node -> (position, modelIndex, connectorId, layer)
        self.nodes = {}
        # board holes actually used (pin in hole or wire end)
        self.used_holes = set()
        for ref, v in self.views.items():
            for c in v.part.connectors:
                self.nodes[("part", ref, c.id)] = (
                    self._tip(v, c.id), self.mi[ref], c.id, "breadboard")
            for cid, hid in v.holes.items():
                self.used_holes.add(hid)
        # every hole coordinate, for wire ends that tap a rail
        import re as _re
        self.hole_at = {}
        for c in lay.board.part.connectors:
            m = _re.fullmatch(r"([A-Z]+)(\d+)", c.id)
            if m:
                self.hole_at[self._key(c.tip)] = c.id

        # ---- wires ---------------------------------------------------
        self.wires = []
        wi = 1
        for net, paths in routes.items():
            color = self._color(net)
            for path in paths:
                path = self._simplify(path)
                for a, b in zip(path, path[1:]):
                    if a == b:
                        continue
                    w = Wire(net, a, b, color, wi)
                    wi += 1
                    self.wires.append(w)
        for w in self.wires:
            self.wire_mi[id(w)] = n
            n += 1

        # ---- edges ---------------------------------------------------
        self.edges = defaultdict(set)

        def edge(a, b):
            if a == b:
                return
            self.edges[a].add(b)
            self.edges[b].add(a)

        # explicit pin-in-hole edges
        for ref, v in self.views.items():
            for cid, hid in v.holes.items():
                edge(("part", ref, cid), ("hole", hid))

        # wire ends -> co-located nodes
        self.wire_ends = defaultdict(list)   # rounded point -> [node]
        for w in self.wires:
            node_a = ("wire", w.index, "connector0")
            node_b = ("wire", w.index, "connector1")
            self.nodes[node_a] = (w.a, self.wire_mi[id(w)], "connector0", "breadboardWire")
            self.nodes[node_b] = (w.b, self.wire_mi[id(w)], "connector1", "breadboardWire")
            edge(node_a, node_b)          # the two ends of one wire are joined
            self.wire_ends[self._key(w.a)].append(node_a)
            self.wire_ends[self._key(w.b)].append(node_b)
            for p in (w.a, w.b):
                hid = self.hole_at.get(self._key(p))
                if hid:
                    self.used_holes.add(hid)

        # hole nodes (after wire taps have been collected)
        for hid in self.used_holes:
            row, col = hid[0], int(hid[1:])
            self.nodes[("hole", hid)] = (
                lay.hole(row, col), self.board_mi, hid, "breadboardbreadboard")

        # index static nodes by rounded point
        self.at = defaultdict(list)
        for node, (p, *_rest) in self.nodes.items():
            if node[0] == "wire":
                continue
            self.at[self._key(p)].append(node)

        for w in self.wires:
            for node, p in ((("wire", w.index, "connector0"), w.a),
                            (("wire", w.index, "connector1"), w.b)):
                k = self._key(p)
                stat = self.at[k]
                holes = [x for x in stat if x[0] == "hole"]
                pins = [x for x in stat if x[0] == "part"]
                if holes:
                    for h in holes:
                        edge(node, h)
                    # a pin in that hole is connected through pin<->hole
                elif pins:
                    for q in pins:
                        edge(node, q)
                else:
                    # free-hanging junction? must meet another wire end
                    pass
                for other in self.wire_ends[k]:
                    if other != node:
                        edge(node, other)

        # any wire end that touches nothing is a bug
        self.dangling = []
        for w in self.wires:
            for node, p in ((("wire", w.index, "connector0"), w.a),
                            (("wire", w.index, "connector1"), w.b)):
                if not self.edges[node]:
                    self.dangling.append((w.net, p))

    # ------------------------------------------------------------------
    def _tip(self, v, cid):
        c = v.part.connector(cid)
        if cid in v.leg:
            dx, dy = v.leg[cid]
            return (round(v.origin[0] + c.anchor[0] + dx, 4),
                    round(v.origin[1] + c.anchor[1] + dy, 4))
        return (round(v.origin[0] + c.tip[0], 4),
                round(v.origin[1] + c.tip[1], 4))

    @staticmethod
    def _key(p):
        return (round(p[0], 1), round(p[1], 1))

    @staticmethod
    def _simplify(path):
        out = []
        for p in path:
            if out and abs(p[0] - out[-1][0]) < 1e-6 and abs(p[1] - out[-1][1]) < 1e-6:
                continue
            out.append((round(p[0], 4), round(p[1], 4)))
        return out

    def _color(self, net):
        from design import NETS
        return NETS.get(net, {}).get("color", "#404040")

    # ------------------------------------------------------------------
    def check(self):
        """Union-find over the graph + board buses; returns (ok, problems)."""
        from design import COMPS, NETS
        parent = {}

        def find(x):
            parent.setdefault(x, x)
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(a, b):
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[ra] = rb

        for a, bs in self.edges.items():
            for b in bs:
                union(a, b)

        # board buses: every used hole joins its bus mates (all holes on that bus)
        by_bus = defaultdict(list)
        for c in self.lay.board.part.connectors:
            bid = self.lay.board.bus.get(c.id)
            if bid:
                by_bus[bid].append(c.id)
        for bid, ids in by_bus.items():
            used = [h for h in ids if h in self.used_holes]
            if len(used) > 1:
                for h in used[1:]:
                    union(("hole", used[0]), ("hole", h))

        problems = []
        # every design pin must be a node
        net_root = {}
        for net, data in NETS.items():
            roots = set()
            for ref, dpin in data["nodes"]:
                v = self.views.get(ref)
                if v is None:
                    problems.append(f"{net}: unknown ref {ref}")
                    continue
                cid = v.pinmap[dpin]
                node = ("part", ref, cid)
                if node not in self.nodes:
                    problems.append(f"{net}: missing node {ref}.{dpin}")
                    continue
                roots.add(find(node))
            if len(roots) > 1:
                problems.append(f"{net}: {len(roots)} disconnected groups")
            net_root[net] = roots

        # shorts: a component may not contain pins of two different nets
        seen = {}
        for net, data in NETS.items():
            for ref, dpin in data["nodes"]:
                v = self.views[ref]
                node = ("part", ref, v.pinmap[dpin])
                r = find(node)
                if r in seen and seen[r] != net:
                    problems.append(f"SHORT: {seen[r]} and {net} share a node")
                seen[r] = net

        if self.dangling:
            problems.append(f"{len(self.dangling)} dangling wire ends")

        return (not problems), problems

    # ------------------------------------------------------------------
    def _instance_xml(self, ref, v, title, props, z, is_board=False, label=None):
        part = v.part
        mi = self.board_mi if is_board else self.mi[ref]
        layer = "breadboardbreadboard" if is_board else "breadboard"
        L = [f'        <instance moduleIdRef="{part.module_id}" '
             f'modelIndex="{mi}" path="{os.path.basename(part.fzp_path)}">']
        for k, val in (props or {}).items():
            L.append(f'            <property name="{k}" value="{val}"/>')
        L.append(f'            <title>{title}</title>')
        L.append('            <views>')
        L.append(f'                <breadboardView layer="{layer}">')
        L.append(f'                    <geometry z="{z:.4f}" x="{v.origin[0]:.4f}" '
                 f'y="{v.origin[1]:.4f}"/>')
        if label:
            lx, ly, keys = label
            L.append(f'                    <titleGeometry visible="true" '
                     f'x="{lx:.4f}" y="{ly:.4f}" z="5.5" xOffset="0" '
                     f'yOffset="0" textColor="#000000" fontSize="5">')
            for k in keys:
                L.append(f'                        <displayKey key="{k}"/>')
            L.append('                    </titleGeometry>')
        L.append('                    <connectors>')
        if is_board:
            entries = [(hid, self.lay.hole(hid[0], int(hid[1:])), None)
                       for hid in sorted(self.used_holes,
                                         key=lambda h: (h[0], int(h[1:])))]
        else:
            entries = [(c.id, None, c) for c in part.connectors]
        for cid, pos, c in entries:
            node = ("hole", cid) if is_board else ("part", ref, cid)
            L.append(f'                        <connector connectorId="{cid}" '
                     f'layer="{layer}">')
            if is_board:
                L.append('                            <geometry x="0" y="0"/>')
            elif cid in v.leg:
                dx, dy = v.leg[cid]
                L.append(f'                            <geometry '
                         f'x="{c.anchor[0]:.4f}" y="{c.anchor[1]:.4f}"/>')
                L.append('                            <leg>')
                L.append('                                <point x="0" y="0"/>')
                L.append('                                <bezier/>')
                L.append(f'                                <point x="{dx:.4f}" '
                         f'y="{dy:.4f}"/>')
                L.append('                                <bezier/>')
                L.append('                            </leg>')
            else:
                L.append(f'                            <geometry '
                         f'x="{c.tip[0]:.4f}" y="{c.tip[1]:.4f}"/>')
            conns = self.edges.get(node, set())
            if conns:
                L.append('                            <connects>')
                for other in sorted(conns):
                    op, omi, ocid, olayer = self.nodes[other]
                    L.append(f'                                <connect '
                             f'connectorId="{ocid}" modelIndex="{omi}" '
                             f'layer="{olayer}"/>')
                L.append('                            </connects>')
            L.append('                        </connector>')
        L.append('                    </connectors>')
        L.append('                </breadboardView>')
        L.append('            </views>')
        L.append('        </instance>')
        return "\n".join(L)

    def _wire_xml(self, w):
        mi = self.wire_mi[id(w)]
        dx, dy = w.delta()
        L = [f'        <instance moduleIdRef="WireModuleID" modelIndex="{mi}" '
             f'path="wire.fzp">',
             f'            <title>Wire{w.index}</title>',
             '            <views>',
             '                <breadboardView layer="breadboardWire">',
             f'                    <geometry z="{Z["wire"] + w.index * 0.0001:.4f}" '
             f'x="{w.a[0]:.4f}" y="{w.a[1]:.4f}" x1="0" y1="0" '
             f'x2="{dx:.4f}" y2="{dy:.4f}" wireFlags="64"/>',
             f'                    <wireExtras mils="22.2222" color="{w.color}" '
             f'opacity="1" banded="0"/>',
             '                    <connectors>']
        for cid, node in (("connector0", ("wire", w.index, "connector0")),
                          ("connector1", ("wire", w.index, "connector1"))):
            L.append(f'                        <connector connectorId="{cid}" '
                     f'layer="breadboardWire">')
            L.append('                            <geometry x="0" y="0"/>')
            conns = self.edges.get(node, set())
            if conns:
                L.append('                            <connects>')
                for other in sorted(conns):
                    op, omi, ocid, olayer = self.nodes[other]
                    L.append(f'                                <connect '
                             f'connectorId="{ocid}" modelIndex="{omi}" '
                             f'layer="{olayer}"/>')
                L.append('                            </connects>')
            L.append('                        </connector>')
        L += ['                    </connectors>',
              '                </breadboardView>',
              '            </views>',
              '        </instance>']
        return "\n".join(L)

    def xml(self):
        from design import COMPS
        L = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<module fritzingVersion="0.9.3.1" icon=".png">',
             '    <views>',
             '        <view name="breadboardView" backgroundColor="#ffffff" '
             'gridSize="0.1in" showGrid="1" alignToGrid="1" viewFromBelow="0"/>',
             '        <view name="schematicView" backgroundColor="#ffffff" '
             'gridSize="0.1in" showGrid="1" alignToGrid="1" viewFromBelow="0"/>',
             '    </views>',
             '    <instances>']
        # parts
        L.append(self._instance_xml("bb840", self.lay.board_view, "Breadboard",
                                    None, Z["board"], is_board=True))
        titles = {"U1": "U1 Raspberry Pi 4", "U2": "U2 ADXL345",
                  "U3": "U3 MAX6675", "U4": "U4 INMP441",
                  "R1": "R1 K-type probe", "R2": "R2", "R4": "R4",
                  "C1": "C1", "C2": "C2", "C3": "C3", "C4": "C4",
                  "D1": "D1", "F1": "F1 5V fan"}
        props = {
            "R2": {"resistance": "10k", "tolerance": "1%", "power": "0.25W"},
            "R4": {"resistance": "330", "tolerance": "5%", "power": "0.25W"},
            "C1": {"capacitance": "100nF", "voltage": "16V"},
            "C2": {"capacitance": "100nF", "voltage": "16V"},
            "C3": {"capacitance": "100nF", "voltage": "16V"},
            "C4": {"capacitance": "10uF", "voltage": "16V"},
        }
        def cx(ref):
            v = self.views[ref]
            xs = [self._tip(v, c.id)[0] for c in v.part.connectors]
            return (min(xs) + max(xs)) / 2

        labels = {
            # cap labels sit half a pitch left of centre so the tap lanes
            # (left leg -4.5, right leg +4.5) never run through the text
            "C1": (cx("C1") - 7.5, 64, ["", "capacitance"]),
            "C2": (cx("C2") - 7.5, 64, ["", "capacitance"]),
            "C3": (cx("C3") - 7.5, 64, ["", "capacitance"]),
            "C4": (cx("C4") - 7.5, 64, ["", "capacitance"]),
            # y=132 keeps the TC_N lane (y=128.5) below the series parts
            "R2": (cx("R2"), 132, ["", "resistance"]),
            "R4": (cx("R4"), 132, ["", "resistance"]),
            "D1": (cx("D1"), 132, [""]),
            "U1": (cx("U1"), 470, [""]),
            "U2": (cx("U2"), -5, [""]),
            "U3": (cx("U3"), -5, [""]),
            "U4": (cx("U4"), -5, [""]),
            "R1": (cx("R1"), 95, [""]),
            "F1": (cx("F1"), 188, [""]),
        }
        for i, ref in enumerate(("U1", "U2", "U3", "U4", "R1", "R2", "R4",
                                 "C1", "C2", "C3", "C4", "D1", "F1")):
            L.append(self._instance_xml(
                ref, self.views[ref], titles.get(ref, ref), props.get(ref),
                Z["part"] + i * 0.001, label=labels.get(ref)))
        # wires
        for w in self.wires:
            L.append(self._wire_xml(w))
        L += ['    </instances>', '</module>', '']
        return "\n".join(L)

    # ------------------------------------------------------------------
    def bundle(self, out_path):
        """Write the .fzz: sketch + every part + every SVG."""
        import io
        sketch_xml = self.xml()
        tmp = out_path + ".tmp"
        with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr(self.name + ".fz", sketch_xml)
            seen_svg = set()
            for spec_name, part in self.lay.parts.items():
                fzp = os.path.join(os.path.dirname(part.fzp_path),
                                   os.path.basename(part.fzp_path))
                z.writestr("part." + os.path.basename(fzp), open(fzp, "rb").read())
                for view, img in part.views.items():
                    folder, base = img.split("/", 1)
                    entry = f"svg.{folder}.{base}"
                    if entry in seen_svg:
                        continue
                    seen_svg.add(entry)
                    src = os.path.join(os.path.dirname(part.fzp_path), img)
                    z.writestr(entry, open(src, "rb").read())
        os.replace(tmp, out_path)
        return out_path

    def write_fz(self, path):
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.xml())
