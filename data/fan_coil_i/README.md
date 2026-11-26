# FAN-COIL-I (derived files only)

Source: Lifsitch et al., "FAN-COIL-I: Vibration sensor dataset for estimating fan coil motor health", Data in Brief 56:110866 (2024). Paper: https://pmc.ncbi.nlm.nih.gov/articles/PMC11402634/ . Data: https://doi.org/10.6084/m9.figshare.25959403.v1 . Licence: CC BY 4.0 (read from the figshare record, https://api.figshare.com/v2/articles/25959403).

Only the small derived files are kept here (about 1 MB): `rms_velocity_{foward,rear}.csv` (RMS vibration velocity of each 10 s capture, one every ~2 min, 5,246 rows from 2024-02-23), `metrics_{foward,rear}.csv` (per-capture acceleration statistics) and `summary_metrics_*.csv`. File names keep the authors' spelling ("foward"). The raw 32 kHz vibration files (13.4 GB and 5.85 GB) are not in this repository.

The data files carry no fault or RUL labels; normal/abnormal periods are described only in the paper. Nothing in this folder is a trained model or a result.
