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
