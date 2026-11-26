# Target-rig predictive-maintenance readiness — evidence, not field validation

**Date:** 2026-11-25 · **Status:** code path ready · **Field validation:** not done

This is the answer to the question: *“It is fine that we do not have the real
motor now, but show with evidence that, if we get it, the project will be a full
predictive-maintenance system.”*

**Honest claim:** the repository already contains the sensing, diagnosis,
operator response, cloud mirror and offline RUL training/prediction paths. Once
the operator supplies real run-to-failure CSVs from **our** rig and accepts the
failure endpoint, `ml/rul_from_rig.py` can evaluate the RUL model, fit a final
regressor and estimate RUL from a current partial run. Until that data and
acceptance exist, no result is a remaining-life claim for our motor. Every
report and prediction is labelled **not field-validated**.

## 1) What exists today

| Path | Evidence | Present state |
|---|---|---|
| Three-sensor acquisition, features, SPC gate, four-class diagnosis, response plan | `edge/edge_daq.py`, `ml/rf_predictor.py`, `ml/ai_report.md` | Implemented; 100% accuracy is synthetic-only |
| Local dashboard and Firebase RTDB status mirror | `edge/dashboard.py`, `edge/firebase_mirror.py`, `public/index.html`, `docs/FIREBASE_SETUP.md` | Presentation/read status only; no write endpoint on the hosted dashboard |
| Real bearing run-to-failure RUL benchmark | `ml/rul_pronostia.py`, `ml/rul_pronostia_report.json`, `data/pronostia/README.md` | Reproduced on PRONOSTIA/FEMTO-ST |
| Threshold-based degradation estimator | `ml/degradation_rul.py`, `tests/test_degradation_rul.py` | Offline only; needs an operator threshold |
| **Target-rig RUL trainer/evaluator/predictor** | `ml/rul_from_rig.py`, `tests/test_rul_from_rig.py` | **Ready for operator-supplied data; not field-validated** |

The runtime classifier, Stage-1/Stage-2 behaviour, dashboard and Firebase state
are unchanged by this readiness path. No Pi service, calibration artifact or
WhatsApp state was touched.

## 2) Exact data contract

One CSV row per logged window. Timestamps are Unix seconds.

```csv
run_id,timestamp,failure_timestamp,rms_dyn,peak_dyn,crest_factor,kurtosis,temp_c,temp_slope,sound_db,sound_zcr[,sound_rms]
```

- `run_id` groups one complete run-to-failure experiment. Use at least **two**
  complete runs and at least **10 rows per run** for the default trailing window.
- `timestamp` must strictly increase within a run.
- `failure_timestamp` must be constant for a run and at or after its last
  sample. It is the **operator-accepted failure endpoint**, not a number inferred
  from the model, a datasheet or the PRONOSTIA 20 g stop rule.
- The nine feature columns are exactly the inputs already used by the deployed
  Stage-2 Random Forest in `ml/rf_predictor.py`: `rms_dyn`, `peak_dyn`,
  `crest_factor`, `kurtosis`, `temp_c`, `temp_slope`, `sound_rms`, `sound_db`,
  `sound_zcr`. No new sensor or physical threshold is introduced.
- `edge/edge_daq.py` already logs `rms_dyn`, `peak_dyn`, `crest_factor`,
  `kurtosis`, `temp_c`, `temp_slope`, `sound_db` and `sound_zcr` in
  `hot_backup.csv`. `failure_timestamp` is added by the operator when the run's
  endpoint is declared.
- `sound_rms` is optional. If the column is missing or blank on every row, it is
  derived from `sound_db` with the inverse of the transform already used in
  `edge/edge_daq.py`, **only strictly inside the unclamped 30–120 dB range**.
  Clamped values are rejected; the script never guesses them. If any row has
  `sound_rms`, every row must have it.

No fabricated run is bundled as rig data. The tests generate a small fixture
only to prove the contract and the code path.

## 3) Commands to use when the real runs exist

Evaluate with leave-one-run-out validation, write an honest report and fit an
optional final model:

```bash
python3 ml/rul_from_rig.py \
  --history /path/to/rig_runs.csv \
  --report /tmp/rul_from_rig_report.json \
  --model-out /tmp/rul_from_rig_model.joblib
```

Estimate RUL for a current, incomplete run with the fitted model:

```bash
python3 ml/rul_from_rig.py --mode predict \
  --history /path/to/current_run.csv \
  --model /tmp/rul_from_rig_model.joblib
```

If the report/model are written under `ml/`, the names
`ml/rul_from_rig_report.json` and `ml/rul_from_rig_model.joblib` are ignored by
Git because they are generated artifacts. Raw operator data is never deleted or
rewritten by these commands.

## 4) What the code proves

`tests/test_rul_from_rig.py` verifies:

- required-column and empty/garbage-value rejection;
- strictly increasing timestamps and rejection of duplicate/backwards times;
- one constant failure endpoint per run, at or after the last sample;
- rejection of a single run for disjoint evaluation;
- causal trailing mean/std/trend features: future rows cannot change past
  features;
- `sound_rms` derivation only in the valid unclamped dB range;
- leave-one-run-out evaluation, last-window and all-window MAE/RMSE,
  a constant-duration baseline, and per-run metrics;
- CLI report/model writing and CLI prediction with `not field-validated` labels;
- absence of runtime or dashboard changes in the report readiness block.

The method uses 10-row trailing statistics (mean, standard deviation and
half-window trend) over the nine existing features, so each labelled window sees
only data available at that time. The target is `failure_timestamp - window
timestamp`, in seconds. A Random Forest is retrained for every held-out run.
This is a readiness proof, **not** a measured RUL result on our motor.

## 5) Acceptance gate before any field claim

The system may be called field-validated predictive maintenance only after the
operator completes all of the following and the evidence is attached:

1. `[NEED: run-to-failure series with timestamps and failure labels from our rig]`
   with provenance (rig ID, sensor serials, run IDs, timestamp source).
2. `[NEED: operator-accepted failure endpoint and reviewed metric report]`:
   the `failure_timestamp` for each run is signed off, the leave-one-run-out
   report is reviewed, and MAE/RMSE are quoted as measured on our runs.
3. `[NEED: measured degradation curve]` and
   `[NEED: real operator failure threshold]` if threshold-based estimates are
   to replace or support the learned RUL output.
4. A reviewed decision on whether the RUL output is displayed or mirrored;
   the hosted dashboard remains presentation-only until that decision.

Until then, the correct exhibition sentence is:

> “The full predictive-maintenance path is set: real run-to-failure data from
> our rig can be evaluated, fitted and used to predict RUL with
> `ml/rul_from_rig.py`. We have not run that field validation, so no hours-to-
> failure number for our motor is claimed.”

See `docs/EXHIBITION_REVIEW_PACK.md` for the Arabic defence wording and
`docs/G12_REQUEST_RESPONSE_REGISTER.md` §11 for the request-by-request evidence.
