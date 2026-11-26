# MAFAULDA 3-class at the rig sampling rate (offline evaluation)

Source: MAFAULDA, UFRJ/COPPE. No terms stated by the source. Data and models are not in this repo.

The rig stream is about 249 Hz, not 400 Hz. Held-out REAL recordings (12 groups) were resampled to a rig-like stream (249 Hz, timing jitter, 3 mg noise, 3.9 mg/LSB, +-16 g). Training used noise, rate and gain augmentation (modelled, not measured on the rig). Balanced accuracy, 3 classes, window level:

- 400 Hz model on the 249 Hz stream: 67.7%
- 250 Hz-native, radial, 8 features: 77.6%
- 250 Hz-native, three axes sorted by rms, 8 features: 79.8% (acc 91.4%)
- 250 Hz-native, three axes, rich spectral features: 79.0% (77.5% with larger leaves)
- Averaging probabilities over 8 windows did not help (74.7-76.2%).

None is reliably at or above 80%. With 12 held-out groups the differences between these variants are within noise. Not validated on the rig. See ml/mafaulda_rig_rate_report.json.
