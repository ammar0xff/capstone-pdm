# PRONOSTIA / FEMTO-ST bearing run-to-failure data — provenance

This directory contains only the **six learning bearings** from the IEEE PHM
2012 Prognostic Challenge (PRONOSTIA) run-to-failure experiment. They are real
measured vibration and temperature recordings with a defined RUL endpoint.
They are **not readings from our capstone induction motor**, and the benchmark
in `ml/rul_pronostia.py` is not field validation of our rig.

| Item | Value |
|---|---|
| Dataset | IEEE PHM 2012 PRONOSTIA/FEMTO-ST bearing learning set |
| NASA PHM mirror | `https://phm-datasets.s3.amazonaws.com/NASA/10.+FEMTO+Bearing.zip` |
| Outer archive MD5 | `0feedeab9584a68199f1f72fe45e3d19` |
| Nested `FEMTOBearingDataSet.zip` MD5 | `da75861c0df34eaf079f863751e41cd7` |
| Nested `Training_set.zip` MD5 | `8ee4422f627c77d2cbeb89107f02c27d` |
| Explicitly licensed public copy | figshare DOI `10.6084/m9.figshare.30595484.v1`, CC BY 4.0 |
| Author of that copy | Yuanyuan Wu, posted 2025-11-12; its supplied and computed MD5 are both `bc1f94f1c6be497653eb5a43e8a41f0f` |
| Original challenge description | *IEEE PHM 2012 Prognostic Challenge — Outline, Experiments, Scoring of results, Winners*, FEMTO-ST Institute, 2012 |
| Explicit FEMTO-ST reuse licence | `[NEED: explicit FEMTO-ST dataset licence]` — the official/NASA pages do not state one; the figshare copy is CC BY 4.0 |

The six bearing directories were extracted unmodified from
`Training_set.zip/Learning_set/` and flattened into this directory. There are
**8,384 CSV files**, 601,742,616 bytes in total. `manifest.json` records the
MD5 of every file and can be checked with `tests/test_rul_pronostia.py`.

| Bearing directory | `acc_*.csv` | `temp_*.csv` | Published load condition |
|---|---:|---:|---|
| `Bearing1_1` | 2,803 | 466 | 1800 rpm / 4000 N |
| `Bearing1_2` | 871 | 144 | 1800 rpm / 4000 N |
| `Bearing2_1` | 911 | 151 | 1650 rpm / 4200 N |
| `Bearing2_2` | 797 | 0 | 1650 rpm / 4200 N |
| `Bearing3_1` | 515 | 89 | 1500 rpm / 5000 N |
| `Bearing3_2` | 1,637 | 0 | 1500 rpm / 5000 N |

Two learning bearings have no temperature files in the published archive; the
benchmark records a zero temperature plus an availability flag for them rather
than inventing values. The wall-clock column in `Bearing1_1` resets twice, so
the benchmark derives time from the recording number and the published cadence
(10 s per vibration recording, 60 s per temperature recording). The resets are
counted in `ml/rul_pronostia_report.json`; no timestamp is silently repaired.

## Published acquisition facts

- Test rig: **250 W asynchronous motor with gearbox**, rated motor speed
  2830 rpm; secondary shaft below 2000 rpm. This is not our motor.
- Vibration: 25.6 kHz sampling, 2560 horizontal/vertical samples recorded every
  10 s (0.1 s of signal per recording).
- Temperature: 10 Hz sampling, 600 RTD samples recorded each minute.
- Vibration columns: hour, minute, second, microsecond, horizontal acceleration,
  vertical acceleration.
- Temperature columns: hour, minute, second, 0.x second, RTD sensor.
- Run endpoint: experiments stopped when vibration exceeded **20 g**. The
  challenge defines RUL as time to that endpoint; our benchmark uses the last
  vibration recording timestamp as the endpoint.

## Scope warning

These recordings support a real-bearing RUL benchmark with genuine degradation
trajectories and leave-one-bearing-out validation. They do **not** prove that
our classifier works on our motor, that our sensors are calibrated, or that
remaining life can be predicted on our rig. Do not present the reported seconds
as an hours-to-failure estimate for the capstone motor. The field case still
requires `[NEED: run-to-failure series with timestamps and failure labels from
our rig]`.
