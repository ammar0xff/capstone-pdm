# KAIST belt-looseness HVAC fan, 4 vibration features at the Pi's 400 Hz band

Data: Jung et al., "Belt Looseness Fault Simulation in an HVAC Testbed", Mendeley Data, doi:10.17632/5tt3zb2pns.1, CC BY 4.0 (KAIST; paper: Data in Brief 2025, https://pmc.ncbi.nlm.nih.gov/articles/PMC12361783/). The 3.2 GB archive is not stored here. Script: `ml/kaist_belt_pi_band.py` (reads Vib_D0..D4.tdms), result: `ml/kaist_belt_pi_band_report.json`.

Measured (RandomForest 100 trees, time-blocked 5-fold, 4,680 windows): 5-class Pi band 26.3% vs 20% majority; full band 43.6%. Normal vs looseness: Pi band 64.0%, full band 82.0%, majority 80%. One 300 s recording per condition, so these are same-session results. The live model was not changed.
