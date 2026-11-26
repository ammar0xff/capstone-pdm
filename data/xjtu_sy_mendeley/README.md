# XJTU-SY bearing run-to-failure evidence — provenance

This directory contains a **public bearing benchmark**, not readings from our
capstone induction motor. It cannot establish remaining life on our rig, and no
public dataset endpoint is operator acceptance of a failure on our rig.

| Item | Value |
|---|---|
| Original dataset | XJTU-SY Rolling Element Bearing Accelerated Life Test Datasets |
| Original publisher | Institute of Design Science and Basic Component, Xi'an Jiaotong University, and Changxing Sumyoung Technology Co., Ltd. |
| Official page | `https://biaowang.tech/xjtu-sy-bearing-datasets` |
| Official mirror | `https://github.com/WangBiaoXJTU/xjtu-sy-bearing-datasets` |
| Required citation | Wang, Lei, Li and Li, IEEE Transactions on Reliability 69(1), 401-412, 2020, DOI `10.1109/TR.2018.2882682` |
| Original reuse licence | `[NEED: explicit XJTU-SY reuse licence]` — the official page says the data are public and requests citation; it does not name a licence |
| Derived record used here | `Bearing_Dataset_XJTU_Processed`, Mendeley Data DOI `10.17632/mpn45f4gxc.1` |
| Derived record licence | **CC BY 4.0** |
| Derived record author | Venkat Nemani, Iowa State University, published 2021-11-11 |
| Derived record URL | `https://data.mendeley.com/datasets/mpn45f4gxc/1` |
| Feature definition code | `https://github.com/VNemani14/Bearing_LSTMPrognostics/blob/main/get_velocity_features.m` |

## What was fetched

The 15 `VelFeaturesB_*.mat` files from the derived record were downloaded over
HTTPS from the Mendeley public-file endpoints listed in `manifest.json`. Each
file's SHA-256 was checked against the hash returned by the Mendeley Data API
(`https://data.mendeley.com/api/datasets/mpn45f4gxc/files`). All 15 matched.
The unmodified `.mat` files are kept in `features/`.

`csv/` holds lossless CSV conversions of the `FFv` matrices, with a leading
`snapshot` column (0, 1, 2, ...). The conversion used
`numpy.savetxt(..., fmt="%.10g")` from the original double-precision values;
`manifest.json` records the CSV SHA-256 as well as the original file hash.

Total: **15 bearings**, **9,216 one-minute snapshots**, 54 published features
per snapshot. There are three operating conditions (35, 37.5 and 40 Hz shaft
frequency; five bearings each) and the original sampling was 25.6 kHz with
32,768 points recorded each minute.

## Feature contract

The derived `FFv` matrix has 54 columns: 27 horizontal-axis features followed
by the same 27 for the vertical axis. Columns 1-3 of each axis are time-domain
maximum amplitude, RMS and kurtosis. Columns 4-27 are fault-band and spectral
RMS features. The benchmark in `ml/rul_xjtu_sy.py` uses only the three
horizontal time-domain features that are finite in every record.

| Our rig contract field | XJTU-SY derived record |
|---|---|
| `rms_dyn` | present as velocity-domain RMS (`feature_02`), **not acceleration** |
| `peak_dyn` | present as velocity-domain peak (`feature_01`) |
| `kurtosis` | present (`feature_03`) |
| `crest_factor` | not present |
| `temp_c`, `temp_slope` | `[NEED: not available — do not invent temperature]` |
| `sound_db`, `sound_zcr`, `sound_rms` | `[NEED: not available — do not invent acoustic data]` |
| `failure_timestamp` | dataset-defined last snapshot; **not operator confirmation** |

## Benchmark result

`ml/rul_xjtu_sy.py --csv-dir data/xjtu_sy_mendeley/csv --report ml/rul_xjtu_sy_report.json`
reproduces `ml/rul_xjtu_sy_report.json`.

The reported endpoint is the published last snapshot of each bearing. The
leave-one-bearing-out evaluation covers the last 20% of the held bearing's
snapshots. See the report for exact MAE/RMSE and the constant-baseline
comparison. The label is `OFFLINE RESULT / NAMED PUBLIC DATASET`.

## Scope warning

Do not present any minute value from this benchmark as an hours-to-failure
estimate for the capstone motor. Do not present the public end-of-life rule as
operator sign-off on our rig. Our own field validation still requires
`[NEED: real run-to-failure CSVs from our rig with operator-confirmed
failure timestamps]`.
