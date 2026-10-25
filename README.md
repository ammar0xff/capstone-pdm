# Intelligent Predictive Maintenance & Remote Monitoring — G12 Capstone 2026/27

AI-driven edge PdM on Raspberry Pi 4 4GB. Offline-first, 0-EGP cloud mirror.
**Budget: 9,370 EGP signed ceiling — planned 9,368.25 from real 2026-10-25 quotes. The MAX6675 is a 200 allowance that must be quoted ≤201.75. 0 EGP cloud.**

- 📖 Live book: GitHub Pages `index.html` (mirrors `Project_Book.html`)
- 📋 PRD: `PRD.md` v2.0 (Problem → Solution → Features → Grade → Technical)
- 🎬 Video prompt: `video_prompt.txt`
- 📊 Charts: `book_assets/` (regenerate with `python3 book_assets/make_charts.py`)
- 📦 BOM: `DOC-20261014-WA0055.xlsx` (supplier sheet) · `circuit/bom_target.csv` (build list)
- 📚 Sources: `G12_27_ Capstone.pdf`, `fmech-06-578379.pdf`, `machines-10-01006-v3.pdf`

Stack: ADXL345 (I2C) + K-type/MAX6675 (SPI) + INMP441 (I2S) → SPC coarse → RF fine (≥80%) → Flask Custom Panel (offline) + Firebase RTDB (mirror) + Grafana Cloud (analytics).

## Circuit design package (generated, machine-checked)

One source of truth: `circuit/design.py` (components, pins, nets). Rebuild everything:

```bash
python3 circuit/build.py     # stdlib only — runs on the Pi, no KiCad needed
```

| Output | What it is |
|---|---|
| `circuit/out/erc_report.md` | 52 checks = 44 design + 8 BOM — **0 ERC errors, 8 documented WARN, 0 FAIL** |
| `circuit/out/schematic_main.svg` | Sheet 1: system wiring + cable schedule (A3) |
| `circuit/out/tc_frontend.svg` | Sheet 2: K-type/MAX6675 theory, cold junction + computed error budget |
| `circuit/out/wiring_a3.svg` | Sheet 3: assembly, glands, cable lengths, power-on checklist |
| `circuit/out/breadboard.svg` | Sheet 4: true-scale (1:1 on A3) breadboard view — real part artwork, hole-by-hole |
| `book_assets/breadboard.png` | Raster preview of Sheet 4 (for slides/print; the SVG is the source of truth) |
| `circuit/out/pdm.net` | KiCad-format netlist (15 nets, 13 components) |
| `circuit/out/pdm_skidl.py` | SKiDL source for a machine with KiCad libraries |
| `circuit/out/block.mmd`, `sequence.mmd`, `state.mmd` | Mermaid diagrams (render on GitHub) |

The build **fails** on any ERC error, so a wrong wire cannot produce a drawing. Sheets are embedded in Project Book §4.3–4.4 — §4.4 is the true-scale (1:1 on A3) breadboard view with real part artwork (preview: `book_assets/breadboard.png`).

Engineering corrections found by the checks and already applied to the book and code:

1. **Nyquist**: 50 Hz sampling cannot see a 240 Hz bearing tone — now ODR = fs = 800 Hz with timestamp resampling.
2. **Kurtosis** divided by σ² instead of σ⁴ — now `w.var()**2`.
3. **Gravity**: RMS of |a| included the 1 g offset — now per-axis mean removal.
4. **Cold junction**: the MAX6675 die *is* T_cold — the module must sit ≥15 cm from the Pi or every reading carries the box's 12 °C rise.
5. **Probe class**: a class-2 K-type is ±2.5 °C on its own — M4 (±2.0 °C) only holds with a **class-1** probe.

Open documentation issues (deliberate WARNs): I²C cable must stay <10 cm, the sealed IP65 box needs a lid heat-spreader, and the SPC layer uses a 2-of-3 rule because a single 3σ point false-alarms about every 31 minutes.

## Budget: signed 9,370 ceiling (real quotes)

The 2026-10-25 supplier quotes are real, and they killed the self-imposed 8240 estimate. The
ceiling was restated in writing the same day, because `G12_27_ Capstone.pdf` sets no budget of
its own — only 0 EGP cloud is absolute.

| | EGP |
|---|---|
| 2026-10-25 quotes (20 lines) | 8,888.25 |
| Re-added fan + glands + heat-shrink | 280.00 |
| MAX6675 allowance (not a quote) | 200.00 |
| **Planned** | **9,368.25** |
| **Signed ceiling** | **9,370.00** |
| Headroom | **1.75** |

The Pi 4 4 GB is already bought at 6,850 (73 % of spend, sunk), so a cheaper board is no longer
a lever — that is why the ceiling moved and the parts did not. The only open rule: **the MAX6675
must be quoted at or below 201.75 EGP**; if it is higher, collect the order in person (−220
shipping) rather than raise the ceiling. Decision record and the rejected alternatives:
**`circuit/BOM_reconciliation.md`**.
