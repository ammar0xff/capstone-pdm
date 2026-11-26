# MAFAULDA at the Pi's 400 Hz band (local evaluation only)

Source: MAFAULDA, Machinery Fault Database, Signals, Multimedia and Telecommunications Laboratory (SMT), COPPE/Poli, Universidade Federal do Rio de Janeiro. https://www02.smt.ufrj.br/~offshore/mfs/page_01.html (contact: F. M. L. Ribeiro). **Licence: no terms stated by the source.** The data were downloaded for local evaluation only, are not stored in this repository and must not be redistributed. Cite UFRJ/MAFAULDA when quoting results.

Rig: SpectraQuest Machinery Fault Simulator (ABVT), 1/4 CV DC motor, 50 kHz, 5 s per recording. Used: normal (49 recordings), imbalance (333), horizontal misalignment (197); underhang-bearing IMI 601A01 accelerometer, columns 2 to 4 (axial, radial, tangential), converted from volts at the stated 100 mV/g (the unit conversion is my assumption from the page).

Method: 180 Hz low-pass, decimate 50 kHz to 400 Hz, 256-sample windows, 4 features (rms, peak, crest factor, kurtosis, same definitions as the Pi). RandomForest 100 trees depth 8. Splits: 5-fold GroupKFold by recording, and by severity group (imbalance load, misalignment offset, normal in 5 speed groups). Results and baselines: `ml/mafaulda_pi_band_report.json`. Scripts: `ml/mafaulda_features.py`, `ml/mafaulda_eval.py`.
