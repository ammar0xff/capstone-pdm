# FMCG induction-motor RUL evidence — provenance

| Item | Value |
|---|---|
| Dataset | [Dataset for Predicting Downtime and RUL for 3 Phase Induction Motor from FMCG Company](https://zenodo.org/records/15637023) |
| DOI | `10.5281/zenodo.15637023` |
| Creator | Muhammad Dzulfiqar Anindhito (Binus University) |
| Zenodo licence | `CC BY 4.0` — <https://creativecommons.org/licenses/by/4.0/> |
| Companion paper | Anindhito & Suharjito, *Applied Computer Science* 21(3), 72–86, DOI [`10.35784/acs_7299`](https://doi.org/10.35784/acs_7299) |
| Motor | 160 kW three-phase induction motors in an FMCG company |
| RUL definition | Hours from startup to shutdown or retirement, from SAP Plant Maintenance history combined with accelerometer readings (paper §3.4.2) |
| Vendored file | `raw.csv`, unchanged copy of `Downtime and RUL Prediction .csv` |
| Size | 3,005,861 bytes; 14,829 lines including header; 14,828 data rows |
| Source MD5 | `52df07317901bdb7647c86df479d06c6` (matches Zenodo metadata) |
| Vendored SHA-256 | `792014186c980d8f7efd2b0fd3abe24667a9210230864e15c2396ed33cb41c27` |
| Encoding / delimiter | `cp1252`, semicolon |

The source mixes ISO dates and Excel serial dates and stores clock time as
`1970-01-01 HH:MM:SS`. `ml/rul_fmcg.py` converts both date forms before building
any feature.

## Run selection

A run is a contiguous block whose `RUL (jam)` label descends to zero. Blocks are
split whenever the label increases. Only strictly time-ordered blocks with at
least 100 rows, at least 20 decreasing RUL steps, maximum RUL at least 50 h and
minimum RUL 0 h are used. Blocks that never reach zero are excluded rather than
relabelled.

| Run | CSV lines | Rows | Duration (h) | `Downtime=YES` rows |
|---|---:|---:|---:|---:|
| `run_01` | 2–583 | 582 | 837.722 | 1 |
| `run_02` | 860–1171 | 312 | 456.017 | 0 |
| `run_03` | 9534–10085 | 552 | 814.006 | 0 |
| `run_04` | 10086–10278 | 193 | 280.998 | 21 |

## Measured result

**Label:** `OFFLINE RESULT / NAMED PUBLIC DATASET`.

Reproduce with:

```sh
python3 ml/rul_fmcg.py --report ml/rul_fmcg_report.json
```

Leave-one-run-out validation on the last 20% of the held run measured:

- RUL MAE **141.716 h**, RMSE **204.069 h** over 334 tail rows.
- 24 h warning accuracy **0.677** (67.7%), precision **0.333**, recall **0.029**, F1 **0.053**.
- Constant-zero baseline: MAE **69.185 h**, RMSE **106.164 h**.
- Constant-no-warning baseline accuracy: **0.686**.
- Median-RUL baseline: MAE **254.993 h**, RMSE **263.054 h**.

The model is worse than the zero regression baseline and the no-warning accuracy
baseline on this split. Those are the measured results. The 24 h value is a
benchmark bin only; it is not an operator-approved alarm threshold. This dataset
is not from the capstone rig, does not establish field-validated RUL and does not
change the four-class runtime model or hosted device-only telemetry.

Other dataset licence gaps in this repository remain explicitly unresolved:
`[NEED: explicit FEMTO-ST licence]`, `[NEED: explicit XJTU-SY reuse licence]`,
`[NEED: explicit CWRU licence; exact catalogue number]`.
