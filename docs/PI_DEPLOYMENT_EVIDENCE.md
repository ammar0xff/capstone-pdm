# Raspberry Pi deployment & latency evidence

Verified on **2026-11-23** over SSH to `renad@100.126.244.75` (Tailscale), host `CAST`.

## Service and path verification

All three systemd units match the repository files and are **active**:

| Unit | User | WorkingDirectory | ExecStart | State |
|---|---|---|---|---|
| `pdm-daq.service` | `renad` | `/home/renad/pdm/edge` | `/usr/bin/python3 /home/renad/pdm/edge/edge_daq.py` | active |
| `pdm-cloud.service` | `renad` | `/home/renad/pdm/edge` | `/usr/bin/python3 /home/renad/pdm/edge/firebase_mirror.py` | active |
| `pdm-dashboard.service` | `renad` | `/home/renad/pdm/edge` | `/usr/bin/python3 /home/renad/pdm/edge/dashboard.py` | active |

## Model deployment

The Pi was still running the previous model (`train_samples=980`, `test_samples=210`, 457,689 bytes).
Before replacing it, backups were created on the Pi:

```
/home/renad/pdm/ml/model.joblib.bak-20261123-233334
/home/renad/pdm/ml/model_meta.json.bak-20261123-233334
```

The current repository artifacts were copied into place; MD5 matched on both sides:

```
3013ae99529c3d15eb5baa1b77094c27  ml/model.joblib
60a9f663d758cd560da98a7b6956a5f4  ml/model_meta.json
```

`sudo systemctl restart pdm-daq.service` completed cleanly (`Deactivated successfully` → `Started`),
and the service remained active afterwards. The other two units do not load the model and were left running.

## Inference wrapper synchronization

The Pi was still running an older `ml/rf_predictor.py` without the two-stage SPC gate. It was backed up as
`rf_predictor.py.bak-<timestamp>`, replaced with the repository version (MD5 `bd1acaf576ce584e398bad6b5ff475c1`),
and `pdm-daq.service` was restarted again. No errors appeared in the journal.

Smoke test against the deployed model on the Pi:

- nominal window → `Stage 1 (SPC Normal)`, `z_score=-1.2`, `rf_executed=false`, **0.02 ms**
- breached window → `Stage 2 (RF Triggered)`, `z_score=4.8`, `rf_executed=true`, **30.995 ms**
- `latest_state.json` was fresh (`seq=163`, age 0.2 s), so the live stream kept updating after both restarts.

## Latency benchmark

Reproduce with `python ml/benchmark_latency.py` (100 single-core `predict_proba` calls, 5-call warm-up,
9 features from `windows.csv`), locally and on the Pi with `--model/--meta/--csv` pointing at the
deployed files.

| Host | Machine | Python | scikit-learn | NumPy | Inference latency | Probability digest |
|---|---|---|---|---|---|---|
| `latitude-e6530` (training) | x86_64 | 3.13.15 | 1.9.1 | 2.5.5 | **26.19 ms** | `425751ab47968a0367a17040c115ec57` |
| `CAST` (Raspberry Pi 4) | aarch64 | 3.13.5 | 1.4.2 | 2.2.4 | **29.99 ms** | `425751ab47968a0367a17040c115ec57` |

The identical digest proves the cross-version model load produced the same predictions on the Pi.
scikit-learn 1.4.2 does emit `InconsistentVersionWarning` when loading the model serialized by 1.9.1;
align the scikit-learn versions before final sign-off.

## What this does and does not prove

- **Proves:** single-window Stage-2 RF inference takes about 30 ms on the actual Pi; the deployed model
  is the one described in `ml/ai_report.md`; the service restarts cleanly with it.
- **Does not prove:** 100% accuracy on a real motor (all training data is synthetic), or the PRD M2
  end-to-end inject→alert time (only the inference step was timed). Real rig windows and an
  end-to-end timing run are still outstanding.

## 2026-11-24 — clean-up and calibration runner deployment

Applied over SSH to `renad@100.126.244.75` (host `CAST`, repository `/home/renad/pdm`).
The Pi has no `git` binary, so the 18 changed/new files from commits `4a9e2c9` and `f9c9dd6`
were streamed with `tar`/`ssh` into the existing tree. Nothing was deleted: the three runtime
files were first copied to timestamped `.bak-20261124-102301` siblings, and `edge/cal.json`
was not touched.

Verified on the Pi after the copy:

| File | MD5 on Pi and workstation |
|---|---|
| `edge/dashboard.py` | `76104e89e724638a900f1bccb2c5c03f` |
| `edge/calibrate.py` | `551be0509530b658f2fe8a3116fd8ff1` |
| `edge/templates/index.html` | `2d618fff6205d6a3cc8fa13ed62829f7` |
| `public/index.html` | `4a0abcd5c4f73243068feb434b40e1d7` |

`python3 -m py_compile edge/dashboard.py edge/calibrate.py` → `COMPILE_OK`.
`python3 edge/calibrate.py --help` printed the full option list without touching hardware.
`sudo systemctl restart pdm-dashboard.service` completed; `pdm-daq`, `pdm-cloud` and
`pdm-dashboard` were all `active`, and `http://127.0.0.1:5000/` returned HTTP 200 with the new
standby text. Actual six-face calibration was **not** run remotely: it requires the operator,
the stationary rig and the reference baths described in `docs/CALIBRATION_RUNBOOK.md`.
