"""stage.py - copy community parts into the sketch bundle.

Each part is written as ``parts/<name>/<name>.fzp`` with

* a private moduleId (``PDM_*``) so the sketch never collides with an
  installed version of the same part, and
* view SVGs renamed to ``<name>_<view>_<basename>`` so no two parts in the
  bundle can share an ``svg.<view>.<file>`` zip entry.

Fritzing resolves the fzp's ``<layers image="...">`` relative to the fzp
itself, so the same layout is used inside the .fzz.
"""
from __future__ import annotations

import os
import re
import shutil
import xml.etree.ElementTree as ET

from partlib import Part, PARTS_ROOT

HERE = os.path.dirname(os.path.abspath(__file__))
PARTS_DIR = os.path.join(HERE, "parts")


class PartSpec:
    def __init__(self, name, module_id, source):
        self.name = name
        self.module_id = module_id
        self.source = source


# Community parts shipped in the .fzz.  The MAX6675 / INMP441 / probe / fan
# are authored locally (see custom.py) because the community library only has
# the bare MAX6675 SO-8 chip and no INMP441, K-probe or 5 V fan.
SPECS = [
    PartSpec("bb840", "PDM_BB840", "core/breadboard.fzp"),
    PartSpec("pi4b", "PDM_PI4B", "core/raspberry-pi-4B_1.fzp"),
    PartSpec("adxl345", "PDM_ADXL345", "core/ADXL345-BreakoutBoard-v13.fzp"),
    PartSpec("resistor", "PDM_RESISTOR", "core/resistor.fzp"),
    PartSpec("led5", "PDM_LED5", "core/LED-generic-5mm_6852162_005.fzp"),
    PartSpec("cap_cer", "PDM_CAP_CER", "core/capacitor_ceramic_100mil.fzp"),
    PartSpec("cap_elec", "PDM_CAP_ELEC", "core/capacitor_electrolytic_small.fzp"),
]


def _strip_bottom_numbers(path):
    """Hide the board art's bottom column numbers.

    The 840-point board silkscreen prints the column numbers twice: above
    row A and below row J (inside the Z-rail margin).  The wire exit band
    lives exactly in that margin, so on the bundled copy the lower set of
    numbers is removed - the top set still labels every column, and no
    wire covers printed text any more.
    """
    tree = ET.parse(path)
    root = tree.getroot()

    def walk(node):
        for child in list(node):
            tag = child.tag.rsplit("}", 1)[-1]
            if tag == "text" and (child.text or "").strip().isdigit():
                m = re.search(r"matrix\(([^)]*)\)",
                              child.get("transform", ""))
                vals = [float(v) for v in
                        (m.group(1).replace(",", " ").split())] if m else []
                if len(vals) >= 6 and vals[5] > 118.0:
                    node.remove(child)
                    continue
            walk(child)

    walk(root)
    tree.write(path, encoding="utf-8", xml_declaration=True)


def stage(spec: PartSpec) -> Part:
    src = os.path.join(PARTS_ROOT, spec.source)
    out_dir = os.path.join(PARTS_DIR, spec.name)
    os.makedirs(out_dir, exist_ok=True)

    tree = ET.parse(src)
    root = tree.getroot()
    root.set("moduleId", spec.module_id)

    for view in ("iconView", "breadboardView", "schematicView", "pcbView"):
        node = root.find("views/" + view + "/layers")
        if node is None or not node.get("image"):
            continue
        image = node.get("image")
        folder = image.split("/", 1)[0]
        base = image.split("/", 1)[1]
        stem, ext = os.path.splitext(base)
        new_base = f"{spec.name}_{view[:-4]}_{stem}{ext}"
        new_path = f"{folder}/{new_base}"
        node.set("image", new_path)
        dst = os.path.join(out_dir, folder, new_base)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(
            os.path.join(PARTS_ROOT, "svg", spec.source.split("/")[0], image), dst)
        if spec.name == "bb840" and view == "breadboardView" and \
                folder == "breadboard":
            _strip_bottom_numbers(dst)

    dst_fzp = os.path.join(out_dir, spec.name + ".fzp")
    tree.write(dst_fzp, encoding="utf-8", xml_declaration=True)
    return Part(dst_fzp)


def stage_all():
    return {spec.name: stage(spec) for spec in SPECS}


def stage_custom():
    import custom
    out = {}
    for name, _mid in custom.build_all():
        out[name] = Part(os.path.join(PARTS_DIR, name, name + ".fzp"))
    return out


if __name__ == "__main__":
    for name, p in stage_all().items():
        print(f"{name:10s} {p.module_id:18s} conns={len(p.connectors):4d}  {p.title}")
