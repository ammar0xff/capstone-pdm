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
