# Dataset provenance and licence evidence

Evidence fetched from public sources on 2026-11-25. It is shown on the hosted
site so that benchmark numbers are never presented as measurements from our
motor. Where an explicit licence is not published, the gap is written as
`[NEED: ...]` rather than guessed.

| Source | What the official source states | Licence evidence | Limit |
|---|---|---|---|
| **XJTU-SY bearing datasets** — [official page](https://biaowang.tech/xjtu-sy-bearing-datasets), [author mirror](https://github.com/WangBiaoXJTU/xjtu-sy-bearing-datasets) | 15 complete run-to-failure bearings from Xi'an Jiaotong University and Changxing Sumyoung Technology; three conditions; vibration only; "publicly available and anyone can use them to validate prognostics algorithms". Publications are asked to cite Wang, Lei, Li & Li, IEEE Trans. Reliability 69(1), 401-412, 2020, DOI `10.1109/TR.2018.2882682`. | `[NEED: explicit XJTU-SY reuse licence]` — citation is requested, but no licence is named on the official page. | Not our motor. No temperature and no acoustic channel. End of life is dataset-defined, not operator-confirmed on our rig. |
| **Derived XJTU-SY feature record** — [Mendeley Data DOI 10.17632/mpn45f4gxc.1](https://data.mendeley.com/datasets/mpn45f4gxc/1) | `VelFeaturesB_1..15.mat`; 54 velocity-domain features per one-minute snapshot, derived from the original XJTU-SY CSVs. Files and hashes are checked in `data/xjtu_sy_mendeley/manifest.json`. | **CC BY 4.0** on the Mendeley record. | This is a derived repository, not the original publisher. The CC BY 4.0 grant applies to this record; it does not silently change the original dataset's terms. |
| **Public combined copy of XJTU-SY + PRONOSTIA** — [figshare DOI 10.6084/m9.figshare.30595484.v1](https://doi.org/10.6084/m9.figshare.30595484.v1) | Figshare record titled "The XJTU-SY Dataset and the IEEE PHM 2012 Bearing Dataset (PRONOSTIA)", published 2025-11-12; API reports licence **CC BY 4.0**. | `https://api.figshare.com/v2/articles/30595484` returns `license.name = "CC BY 4.0"`. | A third-party public copy, useful as licence evidence for that copy only; not a replacement for the original publisher's terms. |
| **IEEE PHM 2012 PRONOSTIA / FEMTO-ST** — [NASA PHM mirror](https://phm-datasets.s3.amazonaws.com/NASA/10.+FEMTO+Bearing.zip) | Six run-to-failure learning bearings with vibration and temperature; run stopped at a 20 g vibration threshold. Used by `ml/rul_pronostia.py`. | The figshare copy above is CC BY 4.0. `[NEED: explicit FEMTO-ST dataset licence]` — the NASA and official challenge pages do not state reuse terms. | Not our motor. The 20 g stop rule is challenge-defined, not operator sign-off on our rig. |
| **CWRU Bearing Data Center** — [overview](https://engineering.case.edu/bearingdatacenter), [apparatus](https://engineering.case.edu/bearingdatacenter/apparatus-and-procedures), [project history](https://engineering.case.edu/bearingdatacenter/project-history) | Experiments used a **2 hp Reliance Electric motor**; bearing faults were seeded by electro-discharge machining at 7-40 mils. Data are normal/faulty diagnosis records, **not run-to-failure trajectories**. | `[NEED: explicit CWRU dataset reuse licence]` — the Bearing Data Center pages give no dataset licence. The [CWRU legal notice](https://case.edu/utech/policies/legal-privacy-notice/) says site information is provided "AS IS" and does not grant a dataset licence. | Seeded faults and no failure endpoint, so CWRU cannot supply a genuine RUL label for our rig. |
| **Reliance Electric motor** — stated on the [CWRU overview](https://engineering.case.edu/bearingdatacenter) and [apparatus page](https://engineering.case.edu/bearingdatacenter/apparatus-and-procedures) | "Experiments were conducted using a 2 hp Reliance Electric motor"; SKF bearings for 7/14/21 mil faults and NTN equivalents for 28/40 mil faults. | `[NEED: exact Reliance Electric catalogue number]` — CWRU states horsepower and manufacturer, not a catalogue/frame number. | Do not infer an exact motor model from the horsepower alone. |

## How this evidence is used

- `ml/rul_xjtu_sy.py` produces a labelled public-bearing benchmark only.
- `docs/REAL_MOTOR_READINESS.md` keeps the exact contract and operator-owned
  failure endpoint required for any claim about our own rig.
- The hosted dashboard shows the XJTU-SY benchmark beside a `BENCHMARK / NOT
  OUR MOTOR / NOT FIELD-VALIDATED` label and this evidence panel.

No benchmark value is written to the live telemetry path, and no public
licence is treated as acceptance of a failure on our motor.
