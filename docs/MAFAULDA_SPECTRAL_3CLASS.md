# MAFAULDA spectral features, 3-class (offline evaluation)

Source: MAFAULDA, UFRJ (https://www02.smt.ufrj.br/~offshore/mfs/page_01.html). No terms stated by the source. Local evaluation only. No data or model is stored in this repo.

Setup: real recordings, group-held-out (12 groups, 516 files held out). Signal reduced to the Pi stream (180 Hz low-pass, 400 Hz, 256-sample windows). Features: rms, peak, crest, kurtosis, log band energy at 10-25, 25-50, 50-100, 100-180 Hz. RF, 150 trees. Classes: normal, imbalance, misalignment (horizontal + vertical). Bearing faults excluded.

Real recordings, clean (balanced accuracy): three axes 80.2%, radial 78.9%.
Real recordings through a SIMULATED ADXL345 front end (3 mg noise, 3.9 mg/LSB, clip): +-16 g three axes 80.2%, radial 78.4%; +-4 g three axes 67.2%, radial 78.8%.
Training with SIMULATED noise/gain augmentation added (evaluated only on held-out REAL recordings): +-16 g three axes 82.3%, radial 84.1%; +-4 g radial 85.0%.

Not a rig result. No RUL. Window-level metrics. See ml/mafaulda_spectral_3class_report.json and ml/mafaulda_spectral_5class_report.json (5-class stays below 80%: 59.0% balanced with bands).
