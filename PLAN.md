# Clean-up, guide and calibration plan (2026-11-24)

## Requirements and constraints

- R1 README becomes the single entry point: project purpose, architecture, file map, exact run/test/deploy commands, honest status.
- R2 Organise the repository by documentation, not by deleting or moving user data: add a file map and an operations guide; keep generated artifacts and `.firebase/` untouched.
- R3 Dashboard is presentation-only: keep live state, operator decision, charts, calibration/deck links and alarm mute; remove engineering/debug text, unverified claims and every write endpoint.
- R4 `edge/calibrate.py` becomes a safe Pi calibration runner: 6-face ADXL345 procedure, two-point MAX6675 procedure, schema validation, atomic writes, timestamped backup, run log and honest certificate.
- R5 Calibration execution is documented exactly in README, handbook, tutorial and a dedicated runbook; no fake PASS results.
- R6 English PDF guide `docs/G12_Project_Guide.pdf` covers Pi setup, Firebase setup, dashboard creation, AI init/training/use, data generation, paper implementation, current status, and how/why AI predicts.
- R7 Firebase setup docs state the current unauthenticated RTDB reality and do not invent secrets or auth changes.
- R8 New tests prove calibration math, validation, backup/atomic write, dashboard cleanup and documentation presence.
- R9 Full test suite, `git diff --check`, browser checks at three widths, PDF preview; commit and push.
- C1 No WhatsApp contact of any kind.
- C2 No change to model or Stage-1/Stage-2 decision behaviour.
- C3 No invented physical/RUL/cost/CPU/lead-time claims; 100% stays synthetic-only.
- C4 No new dependency, no deletion of data, no destructive command.
- R10 Offline degradation estimator requires an operator-supplied threshold, fits linear/exponential trends, and labels every result not field-validated; no runtime, dashboard or model change.
- C5 No physical failure threshold invented or bundled with the code.
- R11 Add a reproducible RUL benchmark on a trusted public run-to-failure
  dataset with DOI and licence, labelled not our motor and not field-validated;
  do not change runtime diagnosis, dashboard or model behaviour.
- R12 User request: collect data correctly, use real data, make RUL work on a
  genuine run-to-failure series, and make the whole project exhibition/review
  ready without false claims.
- R13 Choose a real run-to-failure bearing dataset with a defined failure
  endpoint and ground-truth RUL; PRONOSTIA/FEMTO-ST is the working choice
  because it has six full learning runs, vibration + temperature, three loads,
  a 20 g endpoint and a public DOI/licence copy. It is not our motor.
- R14 Vendor only the six-learning-run subset with provenance, source MD5,
  citation and honest licence status; keep the repository within disk budget.
- R15 Build/test a real-data RUL evaluator using bearing-disjoint validation,
  report MAE/RMSE in seconds and avoid claiming field validity on our rig.
- R16 Prepare an exhibition/review pack in Arabic: one-page defence sheet,
  demo sequence, evidence index, Q&A, forbidden claims and honest RUL wording.
- C6 No claim that PRONOSTIA/CWRU/C-MAPSS data came from our motor; no hours
  to failure on our rig; no "100% on real motor"; no runtime/dashboard change.
- C7 No explicit dataset licence is invented. If the authoritative source has
  no SPDX licence, write `[NEED: explicit FEMTO-ST dataset licence]` and cite
  the public figshare DOI/CC BY 4.0 copy plus the original paper.
- R17 Show, with evidence, that the project becomes full predictive maintenance
  once the operator supplies real run-to-failure data from our rig: accept a
  strict CSV of the nine existing Stage-2 features plus operator-accepted
  `failure_timestamp`, build causal trailing features, evaluate leave-one-run-out,
  optionally fit/save a final regressor and predict RUL from a current run.
- R18 Prove the target-rig path with tests for missing/garbage columns, strict
  timestamps, constant failure endpoints, clamped `sound_db`, causality,
  run-disjoint scoring, honest labels, CLI report/model/prediction and no
  runtime/dashboard change. Generated test data must never be presented as rig data.
- R19 Make the readiness evidence discoverable from README, the deck, the
  Arabic review pack, G12 register, file map, AI report, Pi evidence log and
  plan; link `docs/REAL_MOTOR_READINESS.md` as the single readiness entry point.
- R20 Ignore generated `ml/rul_from_rig_report.json` and
  `ml/rul_from_rig_model.joblib`; add no dependency and delete no data.
- C8 Do not claim field-validated RUL, hours-to-failure on our motor or a
  "100% on real motor" result. Do not change Stage-1/Stage-2 behaviour, the
  dashboard, Firebase or Pi files, and do not deploy without user approval.
- R21 Fetch a different trusted public run-to-failure dataset (XJTU-SY through
  the CC BY 4.0 Mendeley derived feature record), vendor lossless CSVs with
  source/CSV hashes, and keep original licence gaps as `[NEED: ...]`.
- R22 Build/test a causal leave-one-bearing-out benchmark on those data and
  report MAE/RMSE and the constant baseline honestly, including the case where
  the model is worse than the baseline.
- R23 Show the benchmark on the hosted dashboard only under
  `BENCHMARK / NOT OUR MOTOR / NOT FIELD-VALIDATED`, with source/licence
  evidence and light-mode public pages; fetch/display FEMTO-ST, CWRU and
  Reliance evidence without inventing missing facts.
- C9 Public dataset end-of-life labels are not operator acceptance on our rig;
  no benchmark value may be called hours-to-failure for our motor.

## Checklist

- [x] P0 Read project rules, map repository, run baseline tests (18 tests OK on 2026-11-24)
- [x] P1 Write README as clean entry point with links to file map, operations, calibration runbook and English guide
- [x] P2 Add `docs/FILE_MAP.md` and `docs/DEVELOPMENT_OPERATIONS.md`
- [x] P3 Remove `/api/cal` write endpoint from `edge/dashboard.py` and clean public/local dashboard claims
- [x] P4 Rewrite `edge/calibrate.py` with pure math, Pi hardware flow, validation, backup and honest certificate
- [x] P5 Add `docs/CALIBRATION_RUNBOOK.md`; update handbook/tutorial/SENSOR_CALIBRATION to match the new script
- [x] P6 Add `docs/FIREBASE_SETUP.md` and update tutorial security note
- [x] P7 Build styled English `docs/PROJECT_GUIDE.html` and generate `docs/G12_Project_Guide.pdf`
- [x] P8 Add calibration/dashboard/guide tests; run full suite and `git diff --check`
- [x] P9 Browser-verify dashboard at 390/768/1440 px and preview PDF; fix visual findings
- [x] P10 Commit and push; report in Arabic with evidence
- [x] P11 Deploy cleaned `public/` to Firebase Hosting and recheck the live URL
- [x] P12 Restore the operator's `edge/raw_measuree.py`, remove my sound-cal additions, add sound-error reporting/backoff, deploy and verify live raw three-sensor logging
- [x] P13 Add `ml/degradation_rul.py` with tests and docs; operator threshold required, every result not field-validated
- [x] P14 Re-run full suite, `git diff --check`, commit and push the estimator work
- [x] P15 Vendor C-MAPSS FD001 raw files with provenance and build `ml/train_rul_cmapss.py`; reproduce official test RMSE 15.51 / MAE 11.51
- [x] P16 Add `tests/test_rul_cmapss.py`, document the benchmark as public simulated turbofan data in README, AI report, G12 register, file map and Pi evidence
- [x] P17 Run `git diff --check` plus the full suite, then commit and push the benchmark work (63 tests OK, commit `9c5f8f2`)
- [x] P18 Verify PRONOSTIA source/DOI/licence and disk budget; record the choice and missing licence status
- [x] P19 Download the public PRONOSTIA archive, verify MD5, vendor the six learning runs and provenance
- [x] P20 Add `ml/rul_pronostia.py` and tests: real features, RUL labels, bearing-disjoint metrics, honest labels
- [x] P21 Add exhibition/review pack and update README, guide, file map, register and evidence logs
- [x] P22 Run `git diff --check`, full suite, PRONOSTIA reproduction, deck webcheck/visual review and forbidden-claim grep; commit and push; report exact numbers and limits
- [x] P23 Add `ml/rul_from_rig.py`, `tests/test_rul_from_rig.py` and `docs/REAL_MOTOR_READINESS.md` with the strict CSV contract and honest acceptance gate
- [x] P24 Link the readiness evidence from README, deck, exhibition pack, register, file map, AI report, Pi evidence, plan and `.gitignore`
- [ ] P25 Rerun targeted/full tests and `git diff --check`, webcheck/visual-review the deck, then commit and push with remaining `[NEED: ...]` items stated
- [x] P26 Remove fabricated readings and numeric fallbacks from `public/index.html`, add real-data-only guard tests, browser-verify real and missing packets, and rerun webcheck, visual review and the full suite
- [x] P27 Fetch and hash the XJTU-SY derived feature record, vendor CSVs and provenance, build/test `ml/rul_xjtu_sy.py`, and reproduce the labelled report
- [x] P28 Add the labelled benchmark and licence-evidence panel to the hosted dashboard, convert the three hosted pages to light mode, and guard with tests
- [x] P29 Link the new benchmark/provenance evidence from README, plan, file map, AI report, register, review pack and Pi evidence; rerun full suite and browser checks
- [x] P30 Check Firebase CLI auth, complete approved OAuth sign-in if needed, deploy the verified hosted site and report the live URL
