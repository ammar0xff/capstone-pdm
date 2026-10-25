# Intelligent Predictive Maintenance & Remote Monitoring — G12 Capstone 2026/27

AI-driven edge PdM on Raspberry Pi 4 8GB. Offline-first, 0-EGP cloud mirror.
**Budget: 8240 EGP hardware locked + 0 EGP cloud.**

- 📖 Live book: GitHub Pages `index.html` (mirrors `Project_Book.html`)
- 📋 PRD: `PRD.md` v2.0 (Problem → Solution → Features → Grade → Technical)
- 🎬 Video prompt: `video_prompt.txt`
- 📊 Charts: `book_assets/`
- 📦 BOM: `DOC-20261014-WA0055.xlsx` (25 items = 8240)
- 📚 Sources: `G12_27_ Capstone.pdf`, `fmech-06-578379.pdf`, `machines-10-01006-v3.pdf`

Stack: ADXL345 (I2C) + PT100/MAX31865 (SPI) + INMP441 (I2S) → SPC coarse → RF fine (≥80%) → Flask Custom Panel (offline) + Firebase RTDB (mirror) + Grafana Cloud (analytics).

## Circuit design package (generated, machine-checked)

One source of truth: `circuit/design.py` (components, pins, nets). Rebuild everything:

```bash
python3 circuit/build.py     # stdlib only — runs on the Pi, no KiCad needed
```

| Output | What it is |
|---|---|
| `circuit/out/erc_report.md` | 39 design checks + BOM traceability — **0 ERC errors, 4 documented WARN** |
| `circuit/out/schematic_main.svg` | Sheet 1: system wiring + cable schedule (A3) |
| `circuit/out/rtd_frontend.svg` | Sheet 2: PT100 3-wire theory + computed error budget |
| `circuit/out/wiring_a3.svg` | Sheet 3: assembly, glands, cable lengths, power-on checklist |
| `circuit/out/pdm.net` | KiCad-format netlist (17 nets, 13 components) |
| `circuit/out/pdm_skidl.py` | SKiDL source for a machine with KiCad libraries |
| `circuit/out/block.mmd`, `sequence.mmd`, `state.mmd` | Mermaid diagrams (render on GitHub) |

The build **fails** on any ERC error, so a wrong wire cannot produce a drawing. Sheets are embedded in Project Book §4.3.

Engineering corrections found by the checks and already applied to the book and code:

1. **Rref**: the MAX31865 breakout is 430 Ω, not 400 Ω — using 400 reads **−17.9 °C** at the ice point.
2. **Nyquist**: 50 Hz sampling cannot see a 240 Hz bearing tone — now ODR = fs = 800 Hz with timestamp resampling.
3. **Kurtosis** divided by σ² instead of σ⁴ — now `w.var()**2`.
4. **Gravity**: RMS of |a| included the 1 g offset — now per-axis mean removal.

Open documentation issues (deliberate WARNs): I²C cable must stay <10 cm, the sealed IP65 box needs a lid heat-spreader, and the SPC layer uses a 2-of-3 rule because a single 3σ point false-alarms about every 31 minutes.

## ⚠ Open decision — BOM conflict

The committed BOM (`DOC-20261014-WA0055.xlsx` in git) is the locked 8240 EGP plan: PT100 3-wire + MAX31865, Raspberry Pi 4 8GB.

The **working copy on disk has been changed** and now totals **8888.25 EGP** with a Type-K probe + MAX6675 and a Pi 4 4GB. That breaks three things at once:

1. it is **648.25 EGP over the hard cap**;
2. MAX6675 is ±2 °C / 0.25 °C steps, so M4 (±1.0 °C) can no longer be met by the stated calibration method;
3. the book, code, charts, error budget and calibration plan are all PT100/MAX31865-based.

`circuit/build.py` therefore reports the BOM gate as FAIL (design sheets are still produced). Revert the xlsx to the committed version, or re-approve a new BOM and the design will be re-derived to match.
