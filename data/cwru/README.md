# CWRU bearing data — real induction motor, provenance

This directory contains a small, unmodified sample of the Case Western Reserve
University (CWRU) Bearing Data Center recordings. It is **real measured data
from a real induction motor**, unlike our generated `windows.csv` and unlike
the simulated NASA C-MAPSS turbofan benchmark.

## Motor and test rig (as published by CWRU)

| Item | Value |
|---|---|
| Motor | **2 hp Reliance Electric induction motor** |
| Exact catalogue / model number | `[NEED: exact Reliance Electric catalogue number]` — the official pages state only "2 hp Reliance Electric motor" |
| Drive-end bearing | SKF 6205-2RS JEM, deep-groove ball bearing |
| Fan-end bearing | SKF 6203-2RS JEM, deep-groove ball bearing |
| Load / speed in our sample | 0 hp, approximately 1797 rpm |
| Sampling rate | 12,000 samples/s for these drive-end files |
| Fault creation | Electro-discharge machining (EDM), seeded single-point faults |
| Fault size in our sample | 0.007 inch (7 mil) |

Sources (official):

- Overview and motor description: `https://engineering.case.edu/bearingdatacenter/welcome`
- Bearing models and defect frequencies: `https://engineering.case.edu/bearingdatacenter/bearing-information`
- Normal baseline download page: `https://engineering.case.edu/bearingdatacenter/normal-baseline-data`
- 12k drive-end fault download page: `https://engineering.case.edu/bearingdatacenter/12k-drive-end-bearing-fault-data`

No explicit reuse licence is stated on the official CWRU pages:
`[NEED: explicit CWRU reuse licence]`. A republished copy of the same dataset on
IEEE DataPort is licensed CC BY 4.0 (DOI `10.21227/g8ts-zd15`); cite CWRU as the
origin in any presentation regardless.

## Local files (do not edit; verify with `md5sum`)

The names below are the CWRU file labels; the numeric part is the original
`.mat` filename on the CWRU server.

| File | CWRU file | Condition | MD5 | Drive-end samples |
|---|---|---|---|---:|
| `Normal_0.mat` | `97.mat` | healthy, 0 hp | `ee410e7243aefcd8b7120876556464e7` | 243,938 |
| `Normal_1.mat` | `98.mat` | healthy, 1 hp | `3983dcddead0d4b910ee1e8d3da164b9` | — |
| `Normal_2.mat` | `99.mat` | healthy, 2 hp | `edc080a0b4fbc0c2ec8b7f1403372b73` | — |
| `Normal_3.mat` | `100.mat` | healthy, 3 hp | `cc57a511b95785c805055d99281ea2bb` | — |
| `IR007_0.mat` | `105.mat` | inner race fault, 0 hp | `f14821b40412f33018279198da7f9cdc` | 121,265 |
| `B007_0.mat` | `118.mat` | rolling element fault, 0 hp | `ff0f20588edc64140ae33888fcf1114a` | 122,571 |
| `OR007@6_0.mat` | `130.mat` | outer race fault at 6 o'clock, 0 hp | `e45f73f65cc3de4482d28d758503f2c1` | 121,991 |

Each file is a MATLAB `.mat` dictionary. The drive-end vibration array is
`X<number>_DE_time` (column vector, acceleration samples); the fan-end array is
`X<number>_FE_time`; `X<number>RPM` is the recorded speed. Fault files also
contain a base accelerometer array `X<number>_BA_time`.

## Scope warning

These are real motor vibrations, but the faults were **artificially seeded**
and each file is a short steady-state recording. There is no run-to-failure
trajectory, so this dataset can support a **diagnosis** benchmark on real motor
data, **not** an RUL / time-to-failure claim. It is also not our capstone rig's
motor. Any accuracy measured here is "on CWRU's 2 hp Reliance Electric motor",
not "on our motor" and not field validation of our deployed model.
