# Changelog and deploy manifest: branch `dashboard-truth-refactor`

Base: `main` at 5d9f648. 19 commits ahead (up to this file). Written 2026-11-25.

## State of the repository
- Branch `dashboard-truth-refactor` is local only. It has not been pushed.
- Local `main` is 3 commits ahead of the stale `origin/main` tracking ref; the remote `main` head is b0fd51e. Nothing in this branch is on GitHub.
- Working tree was clean before this file (no untracked files).
- Hosting: only `public/` (dashboard and guide) was deployed to https://castpone2026.web.app (hosting only, no database rules).
- Raspberry Pi: NOTHING from this branch is deployed. The Pi still runs the files it had before. Its current contents were not re-read after it was turned off, so Pi-side drift is unverified.

## What changed
### Dashboard (deployed to hosting)
- Removed invented gauges, confidence, zones and unrelated benchmark panels. Unvalidated outputs are labelled.
- Guide: unmeasured latency shows "NOT MEASURED"; no static sampling-rate range is claimed.
- Evidence: HUST bearing benchmark shown as exploratory with its limits.
- Rollback source: `backups/pre-dashboard-truth/*.orig` (old index md5 c2b27bd28b82b0a129fec4591130040c).

### Pi-side code (NOT deployed)
| Change | Files |
|---|---|
| Shared alarm gate module, values unchanged | `ml/gate_thresholds.py`, `edge/edge_daq.py`, `ml/rf_predictor.py` |
| History log: never edit the old file; v2 file if the header is old; width-aware reader that skips NUL, partial, glued and odd-width lines | `edge/history_log.py`, `edge/edge_daq.py`, `edge/dashboard.py` |
| Mic capture helper (fake-arecord tests only) | `edge/capture_condition.py` |
| Raw vs filtered mic report, no thresholds | `edge/mic_filter_report.py` |
| Speech guard and stationary extractor (offline candidates, not wired in) | `edge/speech_guard*.py`, `edge/stationary_extract.py` |
| Latency harness, decision compute only | `ml/latency_harness.py` |
| Read-only heat diagnostic, not run | `edge/thermal_diag.sh` |

Behaviour on the Pi changes only if `edge_daq.py`, `rf_predictor.py`, `gate_thresholds.py`, `history_log.py` and `dashboard.py` are deployed together (the gate values are unchanged; the logger writes to `hot_backup_v2.csv` while `hot_backup.csv` has an 11-column header). The offline candidates, helper, report, harness and diagnostic are standalone and change nothing until run.

## Deploy manifest (for the joint review; do not run before it)
Files, with md5 of the repo copies:
- edge/edge_daq.py 4356003a5b19cf5bb4851b71de6ae1bb
- edge/dashboard.py 1536f4318eae1c9efd5daefdc0b8097f
- edge/history_log.py ea61df736a2765474c05e995ee9c4f1b
- ml/rf_predictor.py 5c8eaa228a03c55fdc19ee19afb7688e
- ml/gate_thresholds.py 3d877787309b03a6d68f6a1b075e5da3
Order: back up the five target files on the Pi (copy with a date suffix), copy the new files, restart `pdm-daq` and `pdm-dashboard`, then check the services are active, the dashboard `/api/history` returns correctly labelled rows, and `hot_backup.csv` is byte-identical to before. `edge_daq.py` imports `gate_thresholds` from `ml/`, so `ml/` and `edge/` go together.
Rollback: restore the dated backups and restart the two services. `hot_backup_v2.csv` can stay; the old reader ignores it.
Not part of the deploy: audio capture, any filter wiring, threshold changes, Firebase rules.

## Tests (laptop, repo `.venv`)
Full regression: 179 tests, all OK, 423 s, repo .venv, 2026-11-25 (all tests/test_*.py including capture, report, speech guard, stationary extractor, history, gates, latency, dashboard truth and behaviour, CMAPSS, FMCG, CWRU, IMS, PRONOSTIA, XJTU). Offline benchmark tests are not rig results.

## Known limits
- Latency: laptop reference only. The RF path was about 64 ms p50 on the laptop; the Pi has not been measured.
- Heat on the Pi: cause unknown, no fix assumed. `edge/thermal_diag.sh` is ready for when the owner powers it on.
- Public benchmarks are offline results and not results from this rig.
