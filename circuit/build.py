"""
build.py — run the whole pipeline.

    python3 build.py

1. ERC + physics + BOM traceability  -> out/erc_report.md
2. KiCad netlist                     -> out/pdm.net
3. SKiDL source                      -> out/pdm_skidl.py
4. Vector schematics                 -> out/schematic_main.svg, tc_frontend.svg, wiring_a3.svg, breadboard.svg
5. Mermaid diagrams                  -> out/block.mmd, out/sequence.mmd, out/state.mmd
"""
import os
import sys
import time

import checks
import render
from design import COMPS, NETS, DESIGN

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")


def kicad_netlist(path):
    """KiCad-compatible .net (also importable as an interchange file)."""
    def q(s):
        return '"' + str(s).replace('"', '') + '"'

    L = ['(export (version "E")', '  (design',
         '    (source "pdm_rig.kicad_sch")',
         '    (date "%s")' % time.strftime("%Y-%m-%d"),
         '    (tool "pdm-pipeline 1.0"))',
         '  (components']
    for ref, c in COMPS.items():
        L += ['    (comp (ref %s)' % q(ref),
              '      (value %s)' % q(c["value"]),
              '      (footprint %s)' % q(c["fp"]),
              '      (fields (field (name "MPN") %s))' % q(c["mpn"]),
              '    )']
    L.append('  )')
    L.append('  (nets')
    for code, (name, net) in enumerate(NETS.items(), start=1):
        L.append('    (net (code %d) (name %s)' % (code, q(name)))
        for ref, pin in net["nodes"]:
            L.append('      (node (ref %s) (pin %s))' % (q(ref), q(COMPS[ref]["pins"][pin][0])))
        L.append('    )')
    L += ['  )', ')', '']
    txt = "\n".join(L)
    with open(path, "w") as f:
        f.write(txt)
    return txt


def balanced(txt):
    depth = 0
    for ch in txt:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth < 0:
                return False
    return depth == 0


def skidl_script(path):
    lines = ['"""SKiDL source, regenerated from design.py.',
             '',
             'Run where KiCad symbol libraries exist:',
             '    python3 pdm_skidl.py      # writes pdm_rig.net',
             '"""',
             'import os',
             'os.environ.setdefault("KICAD_SYMBOL_DIR", "/usr/share/kicad/symbols")',
             'from skidl import *',
             '']
    for ref, c in COMPS.items():
        lines.append(f'{ref} = Part("pdmlib", "{c["mpn"]}", footprint="{c["fp"]}", ref={ref!r})')
    lines.append('')
    for name, net in NETS.items():
        nodes = ", ".join(
            f'{ref}["{COMPS[ref]["pins"][pin][0]}"]' for ref, pin in net["nodes"])
        lines.append(f'Net("{name}") += [{nodes}]')
    lines += ['', 'ERC()', 'generate_netlist("pdm_rig.net")', '']
    with open(path, "w") as f:
        f.write("\n".join(lines))


def mermaid(path_block, path_seq, path_state):
    with open(path_block, "w") as f:
        f.write("""flowchart LR
  subgraph SENSE["Sensing"]
    A["ADXL345<br/>I2C 0x53<br/>800 Hz FIFO"]:::s
    B["K-type + MAX6675<br/>SPI0<br/>0.2 Hz"]:::s
    C["INMP441<br/>I2S 16 kHz"]:::s
  end
  subgraph EDGE["Raspberry Pi 4 4GB (edge, offline)"]
    D["Calibration<br/>cal.json"]:::e
    E{"SPC coarse<br/>X-bar / R<br/>mu +/- 2s / 3s"}:::e
    F["RF fine<br/>4-class + probability"]:::e
    G[("SD hot_backup.csv")]:::e
    H["Mosquitto + Flask<br/>192.168.4.1:5000"]:::e
  end
  subgraph CLOUD["0 EGP mirror"]
    I["Firebase RTDB<br/>1 write / 15 s"]:::c
    J["Grafana Cloud<br/>SPC + KPIs + annotations"]:::c
  end
  A --> D
  B --> D
  C --> D
  D --> E
  E -- "in control" --> G
  E -- "out of control" --> F
  F --> G
  G --> H
  H --> I
  I --> J
  H -- "QR / local first" --> K["Phone or laptop"]:::u
  classDef s fill:#eaf2f8,stroke:#2471a3,color:#12212f
  classDef e fill:#fef9e7,stroke:#b9770e,color:#12212f
  classDef c fill:#f4ecf7,stroke:#8e44ad,color:#12212f
  classDef u fill:#eafaf1,stroke:#117a65,color:#12212f
""")
    with open(path_seq, "w") as f:
        f.write("""sequenceDiagram
  autonumber
  participant S as Sensors
  participant P as Pi edge
  participant F as Flask Panel
  participant B as Firebase RTDB
  participant G as Grafana

  S->>P: g, temperature, audio RMS (timestamped)
  P->>P: calibrate -> window -> RMS / kurtosis / FFT
  alt SPC inside limits
    P->>F: state=Healthy (1 s SSE)
    P->>B: PUT /motor1.json (15 s)
    B-->>G: JSON datasource
  else SPC out of control
    P->>P: RF infer (~2 ms) -> fault + probability
    P->>F: state=Fault + advice (<= 5 s)
    P->>B: PUT + seq
    B-->>G: annotation on the time series
  end
  Note over P,B: WiFi down -> SD buffer, replay on reconnect
""")
    with open(path_state, "w") as f:
        f.write("""stateDiagram-v2
  [*] --> Booting
  Booting --> Healthy: cal.json + baseline loaded
  Healthy --> Warning: RMS > mu+2s OR T > 60 C
  Warning --> Healthy: 3 windows in limits
  Warning --> Fault: RMS > mu+3s OR kurtosis > 6 OR T > 75 C
  Fault --> Warning: 3 clean windows
  Fault --> OfflineBuffering: WiFi lost
  OfflineBuffering --> Fault: backfill complete
  Healthy --> OfflineBuffering: WiFi lost
""")


def main():
    os.makedirs(OUT, exist_ok=True)
    results = checks.all_results()
    report = checks.report_md(results)
    with open(os.path.join(OUT, "erc_report.md"), "w") as f:
        f.write(report)

    net = kicad_netlist(os.path.join(OUT, "pdm.net"))
    ok = balanced(net)
    skidl_script(os.path.join(OUT, "pdm_skidl.py"))
    mermaid(os.path.join(OUT, "block.mmd"), os.path.join(OUT, "sequence.mmd"),
            os.path.join(OUT, "state.mmd"))
    render.schematic_main(os.path.join(OUT, "schematic_main.svg"))
    render.tc_frontend(os.path.join(OUT, "tc_frontend.svg"))
    render.wiring_a3(os.path.join(OUT, "wiring_a3.svg"))
    render.breadboard(os.path.join(OUT, "breadboard.svg"))

    counts = {s: sum(1 for x in results if x.status == s) for s in ("PASS", "WARN", "FAIL")}
    electrical = sum(1 for x in results if x.group != "BOM" and x.status == checks.FAIL)
    print(f"netlist balanced: {ok}  nets={len(NETS)}  comps={len(COMPS)}")
    print(f"checks: {counts['PASS']} PASS / {counts['WARN']} WARN / {counts['FAIL']} FAIL")
    for x in results:
        if x.status != "PASS":
            print(f"  [{x.status}] {x.group}: {x.name} — {x.detail}")
    if counts["FAIL"]:
        print("\nArtifacts were written, but the build is marked failed.")
        if electrical:
            print("BLOCKER: electrical rule violation - do not build this netlist.")
        else:
            print("BLOCKER: BOM does not match the design/9,370 cap - reconcile the xlsx "
                  "(see out/erc_report.md) before ordering parts.")
        sys.exit(1)


if __name__ == "__main__":
    main()
