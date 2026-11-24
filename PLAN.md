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
