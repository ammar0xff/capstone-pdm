# Intelligent Predictive Maintenance & Remote Monitoring — G12 Capstone 2026/27

AI-driven edge PdM on Raspberry Pi 4 8GB. Offline-first, 0-EGP cloud mirror.
**Budget: 8240 EGP hardware ceiling + 0 EGP cloud.**

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
| `circuit/out/erc_report.md` | 53 checks = 44 design + 9 BOM — **0 ERC errors, 6 documented design WARN, 1 BOM FAIL** (unpriced MAX6675) |
| `circuit/out/schematic_main.svg` | Sheet 1: system wiring + cable schedule (A3) |
| `circuit/out/tc_frontend.svg` | Sheet 2: K-type/MAX6675 theory, cold junction + computed error budget |
| `circuit/out/wiring_a3.svg` | Sheet 3: assembly, glands, cable lengths, power-on checklist |
| `circuit/out/pdm.net` | KiCad-format netlist (15 nets, 13 components) |
| `circuit/out/pdm_skidl.py` | SKiDL source for a machine with KiCad libraries |
| `circuit/out/block.mmd`, `sequence.mmd`, `state.mmd` | Mermaid diagrams (render on GitHub) |

The build **fails** on any ERC error, so a wrong wire cannot produce a drawing. Sheets are embedded in Project Book §4.3.

Engineering corrections found by the checks and already applied to the book and code:

1. **Nyquist**: 50 Hz sampling cannot see a 240 Hz bearing tone — now ODR = fs = 800 Hz with timestamp resampling.
2. **Kurtosis** divided by σ² instead of σ⁴ — now `w.var()**2`.
3. **Gravity**: RMS of |a| included the 1 g offset — now per-axis mean removal.
4. **Cold junction**: the MAX6675 die *is* T_cold — the module must sit ≥15 cm from the Pi or every reading carries the box's 12 °C rise.
5. **Probe class**: a class-2 K-type is ±2.5 °C on its own — M4 (±2.0 °C) only holds with a **class-1** probe.

Open documentation issues (deliberate WARNs): I²C cable must stay <10 cm, the sealed IP65 box needs a lid heat-spreader, and the SPC layer uses a 2-of-3 rule because a single 3σ point false-alarms about every 31 minutes.

## ⚠ Open decision — BOM

The design is checked against `circuit/bom_target.csv`: **8240.00 EGP**, 26 lines, including a 150 EGP reserve and the MAX6675 at an estimated 200 EGP.

The supplier sheet in the repo (`DOC-20261014-WA0055.xlsx`) is the 2026-10-14 quote. A **newer re-shop (2026-10-25)** is sitting in the working tree: it totals **8888.25 EGP** for 23 priced lines, prices the Pi 4 **4 GB at 6850** (the 8 GB was quoted at 5800), and **removes the case/fan, glands and heat-shrink** while leaving the MAX6675 unpriced. That configuration cannot be built: a Pi 4 without a fan throttles inside a sealed box.

The build marks the supplier sheet as a WARN and fails on the unpriced line. Full analysis and the ordered action list: **`circuit/BOM_reconciliation.md`**. The decisive item is the Pi quote — it is 70 % of the budget.
