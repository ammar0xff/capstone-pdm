# MAFAULDA: 5-class real-data training at the Pi band, with offline replay

Source: MAFAULDA, SMT/COPPE, Universidade Federal do Rio de Janeiro (https://www02.smt.ufrj.br/~offshore/mfs/page_01.html). **No terms stated by the source.** Data used locally in a sandbox only, not stored here, not redistributed. Cite UFRJ/MAFAULDA when quoting.

All 1,951 recordings, 5 classes (normal, imbalance, horizontal misalignment, vertical misalignment, bearing fault). Pi band only: 180 Hz low-pass, 400 Hz, 256-sample windows, rms/peak/crest/kurtosis per axis. RandomForest 150 trees, balanced class weights. About 25% of the condition groups of each class are held out entirely (12 groups, 516 recordings); 5-fold group CV on the rest. Measured balanced accuracy on held-out groups (chance 20%): radial only 44.8%, three axes 51.4% (accuracy 57.2% against a 51.2% majority baseline). Replay through the feature pipeline with a simulated ADXL345 front end: three axes 53.8% balanced at +-16 g, 39.8% at +-4 g. Full numbers: `ml/mafaulda_train_replay_report.json`. No model was committed and nothing was changed on the Pi.

Scripts: `ml/mafaulda_features_a.py` (normal, imbalance, horizontal), `ml/mafaulda_features_b.py` (vertical, bearing), `ml/mafaulda_train_replay.py`. Signal volts are converted to g at the 100 mV/g stated on the source page (assumption).
