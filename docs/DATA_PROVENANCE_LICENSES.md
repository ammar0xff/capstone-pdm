# Dataset provenance and licence evidence

Evidence fetched from public sources on 2026-11-25. It is shown on the hosted
site so that benchmark numbers are never presented as measurements from our
motor. Where an explicit licence is not published, the gap is written as
`[NEED: ...]` rather than guessed.

| Source | What the official source states | Licence evidence | Limit |
|---|---|---|---|
| **FMCG induction-motor RUL dataset** — [Zenodo DOI 10.5281/zenodo.15637023](https://zenodo.org/records/15637023) | 160 kW three-phase induction motors in an FMCG company; accelerometer vibration, electrical/torque readings and an explicit `RUL (jam)` column. Companion paper DOI `10.35784/acs_7299` defines RUL as operating hours from startup to shutdown or retirement from SAP Plant Maintenance history. `data/fmcg_induction_rul/raw.csv` matches the published MD5 `52df07317901bdb7647c86df479d06c6`. | Zenodo metadata states **CC BY 4.0**; licence URL `https://creativecommons.org/licenses/by/4.0/`. This licence is explicit and is not extended to any other dataset. | Not our motor. The 24 h warning bin is a benchmark choice, not operator sign-off; the endpoint is a source RUL label, not a field-confirmed failure on our rig. |
| **XJTU-SY bearing datasets** — [official page](https://biaowang.tech/xjtu-sy-bearing-datasets), [author mirror](https://github.com/WangBiaoXJTU/xjtu-sy-bearing-datasets) | 15 complete run-to-failure bearings from Xi'an Jiaotong University and Changxing Sumyoung Technology; three conditions; vibration only; "publicly available and anyone can use them to validate prognostics algorithms". Publications are asked to cite Wang, Lei, Li & Li, IEEE Trans. Reliability 69(1), 401-412, 2020, DOI `10.1109/TR.2018.2882682`. | Fetched explicit public-use permission: "anyone can use them to validate prognostics algorithms", with citation requested. `[NEED: SPDX-style licence identifier on the original page]` — no licence name is published. | Not our motor. No temperature and no acoustic channel. End of life is dataset-defined, not operator-confirmed on our rig. |
| **Derived XJTU-SY feature record** — [Mendeley Data DOI 10.17632/mpn45f4gxc.1](https://data.mendeley.com/datasets/mpn45f4gxc/1) | `VelFeaturesB_1..15.mat`; 54 velocity-domain features per one-minute snapshot, derived from the original XJTU-SY CSVs. Files and hashes are checked in `data/xjtu_sy_mendeley/manifest.json`. | **CC BY 4.0** on the Mendeley record. | This is a derived repository, not the original publisher. The CC BY 4.0 grant applies to this record; it does not silently change the original dataset's terms. |
| **Public combined copy of XJTU-SY + PRONOSTIA** — [figshare DOI 10.6084/m9.figshare.30595484.v1](https://doi.org/10.6084/m9.figshare.30595484.v1) | Figshare record titled "The XJTU-SY Dataset and the IEEE PHM 2012 Bearing Dataset (PRONOSTIA)", published 2025-11-12; API reports licence **CC BY 4.0**. | `https://api.figshare.com/v2/articles/30595484` returns `license.name = "CC BY 4.0"`. | A third-party public copy, useful as licence evidence for that copy only; not a replacement for the original publisher's terms. |
| **IEEE PHM 2012 PRONOSTIA / FEMTO-ST** — [NASA PHM mirror](https://phm-datasets.s3.amazonaws.com/NASA/10.+FEMTO+Bearing.zip), [official challenge PDF](https://raw.githubusercontent.com/Lucky-Loek/ieee-phm-2012-data-challenge-dataset/master/IEEEPHM2012-Challenge-Details.pdf) | Six run-to-failure learning bearings with vibration and temperature; run stopped at a 20 g vibration threshold. Used by `ml/rul_pronostia.py`. | Fetched statement: "The datasets are being made publicly available. Publications making use of these databases are requested to cite the following paper." Related FEMTO-ST papers are CC BY 3.0 US. The figshare copy above is CC BY 4.0. `[NEED: explicit FEMTO-ST dataset licence]` (SPDX name) — no licence name is published for the data itself. | Not our motor. The 20 g stop rule is challenge-defined, not operator sign-off on our rig. |
| **CWRU Bearing Data Center** — [overview](https://engineering.case.edu/bearingdatacenter), [apparatus](https://engineering.case.edu/bearingdatacenter/apparatus-and-procedures), [project history](https://engineering.case.edu/bearingdatacenter/project-history) | Experiments used a **2 hp Reliance Electric motor**; bearing faults were seeded by electro-discharge machining at 7-40 mils. Data are normal/faulty diagnosis records, **not run-to-failure trajectories**. | A derived copy is explicitly [CC BY 4.0 on Zenodo](https://doi.org/10.5281/zenodo.10986655) (van den Hoogen, 2024) and an [IEEE DataPort copy](https://doi.org/10.21227/g8ts-zd15) is CC BY. `[NEED: explicit CWRU dataset reuse licence on the original site]` — the Bearing Data Center pages give no dataset licence; the CWRU legal notice says site information is provided "AS IS". | Seeded faults and no failure endpoint, so CWRU cannot supply a genuine RUL label for our rig. Derived-copy licences do not grant rights to the original files. |
| **Reliance Electric motor** — stated on the [CWRU overview](https://engineering.case.edu/bearingdatacenter) and [apparatus page](https://engineering.case.edu/bearingdatacenter/apparatus-and-procedures) | "Experiments were conducted using a 2 hp Reliance Electric motor"; SKF bearings for 7/14/21 mil faults and NTN equivalents for 28/40 mil faults. | `[NEED: exact Reliance Electric catalogue number]` — CWRU states horsepower and manufacturer, not a catalogue/frame number. | Do not infer an exact motor model from the horsepower alone. |
| **NASA IMS Bearings** — [NASA Open Data Portal](https://data.nasa.gov/dataset/ims-bearings), [IMS.zip](https://data.nasa.gov/docs/legacy/IMS.zip) | Three run-to-failure bearing tests from the Center for Intelligent Maintenance Systems, University of Cincinnati; 20 kHz vibration snapshots every 10 min; four bearings reached confirmed faults. | Portal metadata field `license = https://www.usa.gov/government-works` (US Government Work); the page displays "other-license-specified", so the raw fields are quoted rather than simplified. | Not our motor. End of testing/fault confirmation is dataset-defined, not operator acceptance on our rig. |

## Options to close the remaining gaps

1. **XJTU-SY / FEMTO-ST / CWRU SPDX names:** ask the data contacts in writing for
   an explicit licence string. Until then the public page quotes the fetched
   public-use statements and keeps `[NEED: ...]` instead of inventing a licence.
2. **Reliance catalogue number:** supply a photograph or transcription of the
   CWRU motor nameplate, or an official CWRU apparatus document that names the
   frame number. Horsepower alone is not a catalogue number.
3. **If no evidence arrives:** keep the `[NEED: ...]` markers visible (current
   choice, honest for review) or hide the unresolved rows from the hosted table.
   Hiding them is an alternative, not a fix.

The short tokens used elsewhere in the repository are kept verbatim:
`[NEED: explicit FEMTO-ST licence]`, `[NEED: explicit XJTU-SY reuse licence]` and
`[NEED: explicit CWRU licence; exact catalogue number]`.

## How this evidence is used

- `ml/diagnosis_cwru.py` produces the headline real-motor **diagnosis** result
  (1.000 / 100.0% on 1,039 windows against a 0.4004 / 40.04% majority baseline)
  from the CWRU files above. It is a controlled bearing-condition task, not our
  motor, not the deployed taxonomy, not RUL and not field validation.
- `ml/rul_fmcg.py` produces the labelled public induction-motor RUL benchmark
  with explicit CC BY 4.0 metadata; its 67.7% warning accuracy is reported as
  measured. `ml/rul_xjtu_sy.py` and the other scripts remain separate public
  benchmarks only.
- `docs/REAL_MOTOR_READINESS.md` keeps the exact contract and operator-owned
  failure endpoint required for any claim about our own rig.
- The hosted dashboard shows the CWRU diagnosis result beside the FMCG,
  XJTU-SY, PRONOSTIA and NASA IMS results, each under
  `BENCHMARK / NOT OUR MOTOR / NOT FIELD-VALIDATED`, with this evidence panel.

No benchmark value is written to the live telemetry path, and no public
licence is treated as acceptance of a failure on our motor.
