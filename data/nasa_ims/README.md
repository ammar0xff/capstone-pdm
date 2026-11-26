# NASA IMS bearing run-to-failure evidence — provenance

| Item | Value |
|---|---|
| Source | [NASA Open Data Portal — IMS Bearings](https://data.nasa.gov/dataset/ims-bearings) |
| Origin | NSF I/UCR Center for Intelligent Maintenance Systems, University of Cincinnati; Rexnord ZA-2115 bearings |
| Archive | [IMS.zip](https://data.nasa.gov/docs/legacy/IMS.zip) |
| Archive SHA-256 | `6cb42c263b0281c725abf99f4b9fcf49915c949f31dbd2333877dc2e06ce9ec2` |
| Portal licence metadata | `https://www.usa.gov/government-works` (US Government Work); the page displays `other-license-specified`, so both facts are quoted rather than simplified |
| Requested citation | Qiu, H., Lee, J. and Lin, J., "Wavelet Filter-based Weak Signature Detection Method and its Application on Roller Bearing Prognostics", Journal of Sound and Vibration 289 (2006) 1066-1090 |
| Labelled failures | Set 1 bearing 3 inner race, set 1 bearing 4 rolling element, set 2 bearing 1 outer race, set 3 bearing 3 outer race — as documented in the archive README PDF |
| Snapshot counts | 2,156 / 2,156 / 984 / 6,324 in the published RAR files; the README PDF describes 4,448 files for set 3, so the archive listing is used and the discrepancy is recorded rather than silently resolved |
| Limit | **OFFLINE RESULT / NAMED PUBLIC DATASET.** The last published snapshot is a dataset-defined end of test, not operator-accepted failure of the capstone motor |

## What is vendored here

`failed_bearings.csv` is a compact derived record, not the raw archive. One row
is one 1-second, 20 kHz vibration snapshot (20,480 samples) for one of the four
documented failed bearings. It stores RMS and kurtosis for the relevant
accelerometer channel(s) plus the nominal recorded minutes. No temperature or
acoustic channel exists in this source. `manifest.json` records the source hash,
the feature-file hash and the per-bearing failure labels and counts.

The source ZIP contains RAR archives whose raw text expands to roughly 6.5 GB.
`ml/nasa_ims_features.py` regenerates the compact record by streaming one RAR
member at a time with the already-installed `unrar` tool; no new dependency and
no bulk extraction are required.

## Time convention

Snapshots are recorded every 10 minutes, except the first 43 snapshots of set 1
(which are 5 minutes apart). The archive also contains multi-day gaps when the
experiment resumed. `minutes` is the nominal recorded cadence from the first
snapshot, **not** wall-clock operating hours. Any RUL number from this record
is therefore in nominal recorded minutes and cannot be read as hours-to-failure
for our rig.

## Reproduction

```bash
python3 ml/nasa_ims_features.py --zip /path/IMS.zip \
    --out data/nasa_ims/failed_bearings.csv
python3 ml/rul_nasa_ims.py --report /tmp/rul_nasa_ims_report.json
```

The benchmark uses leave-one-bearing-out evaluation on the last 20% of the held
bearing's snapshots. Every prediction uses only snapshots up to the prediction
time and the other three bearings. See `ml/rul_nasa_ims_report.json` for the
measured result and the constant baseline. No result here changes the runtime
dashboard or adds a field-validated RUL claim.
