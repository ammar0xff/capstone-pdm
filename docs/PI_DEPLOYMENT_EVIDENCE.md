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

## 2026-11-24 11:05 — cloud mirror URL repair

The local dashboard was live (`latest_state.json` updating, `online=True`, `/api/latest`
sequence advancing), but the hosted dashboard was showing a point from 2026-11-23 23:18.
The Pi's local `edge/cloud_config.json` pointed at the non-existent database
`capstone-pdm-2026-default-rtdb.firebaseio.com` (HTTP 404), so `pdm-cloud.service` had
buffered 200 frames in `edge/cloud_backlog.json` and reported
`Offline Buffering: HTTP Error 404: Not Found`.

Backed up `edge/cloud_config.json` to `edge/cloud_config.json.bak-20261124-110456`, then used
the service's own `python3 edge/firebase_mirror.py --set-url ...` to set the documented URL
`https://castpone2026-default-rtdb.firebaseio.com/motor1.json`, and restarted `pdm-cloud.service`.

Verified after the restart: `last_sync_status = OK (HTTP 200)`, `daily_writes_today = 2`,
backlog file gone, service `active`. Two Firebase reads 20 s apart showed `seq 9744 → 9835`
and `ts 11:06:15 → 11:06:29`, so the hosted dashboard is now receiving live data. The
calibration file and all three services were left otherwise unchanged.

## 2026-11-24 11:19 — repository organisation on the Pi

The Pi tree was brought in line with `main`. Nothing was permanently deleted: obsolete files were
moved to `backups/cleanup-20261124-111903/`, earlier deployment backups to
`backups/deployment-20261124/`, and the 14 replaced files were copied first to
`backups/pre-sync-20261124-112022/`. A manifest of every move is in the cleanup folder.

Removed from the active tree: duplicate `edge/edge_daq_backup.py` (identical to `edge_daq.py`),
old `edge/index.html`, `edge/raw_sensors.py.save`, stale `ml.zipped.zip`, LibreOffice lock file,
`__pycache__` folders, `.stitch-mcp/` tool cache and all `.bak-*` siblings. Empty `backups/`,
`updates/` and `uploads/` placeholders were kept as documented in `docs/FILE_MAP.md`.

Synced 30 tracked files that were missing or stale on the Pi, including the current
`edge/edge_daq.py`, `edge/firebase_mirror.py`, `ml/*`, `public/calibration.html`,
`public/guide.html`, the new docs and `requirements.txt`. Runtime state (`edge/cal.json`,
`edge/cloud_config.json`, `latest_state.json`, `hot_backup.csv`) was deliberately not overwritten.
MD5 verification: 30/30 matched the workstation. Remaining identical files are intentional
(hosted-asset mirrors, Fritzing part library, waivers copy), not duplicates to remove.

Post-change verification: `py_compile` OK, all three services `active`, local dashboard HTTP 200,
`latest_state.json` advancing (`seq 189`, 12.8 s old), Firebase `seq 189` (24.8 s old) and
`last_sync_status = OK (HTTP 200)`. The real calibration runner remains
`/home/renad/pdm/edge/calibrate.py`; `python3 edge/calibrate.py --help` works.

## 2026-11-24 11:25 — raw measurement runner

Added `edge/raw_measure.py` at commit `ab6fd4d` and copied it to the Pi with the
updated README, runbook and file map. MD5 matched (`8dff67e48b8c5ab2af21a52a5071e3e7`),
`py_compile` OK and `--help` worked. The old `edge/raw_sensors.py.save` remains in
`backups/cleanup-20261124-111903/`; the new script supersedes it.

With `pdm-daq.service` stopped, `python3 edge/raw_measure.py --count 3 --interval 0.3
--csv /tmp/pdm_raw_check.csv` returned three live raw frames, for example
`X=6 Y=-64 Z=95` LSB and `MAX6675 0x0340 counts=104 open_tc=0 T_datasheet=26.00 C
(UNCALIBRATED)`. The CSV contained the same three rows. No `cal.json` value was
applied or changed. The DAQ service was restarted afterwards; all three services
were `active`, local state `seq 156` was 0.0 s old, `last_sync_status = OK (HTTP 200)`
and the Tailscale dashboard returned HTTP 200.

## 2026-11-24 18:30 — local verification, Pi unreachable

Re-ran both webchecks locally after the verification server restart:
`http://127.0.0.1:5000` → `RESULT: PASS (0 floor, 0 reflex)` and
`https://castpone2026.web.app/` → `RESULT: PASS (0 floor, 0 reflex)` with the four
already documented waivers. Applied the critic's low-risk local fixes (single-line
scrollable formulas, 2×2 mobile controls, lighter muted text, grey standby dots,
primary deck button) and committed them as `25cfa67`; local tests: `Ran 37 tests`, `OK`.

The Pi could not be reached to deploy `25cfa67`: `tailscale status` reports
`100.126.244.75 cast ... offline, last seen 4h ago` and SSH timed out. The Pi is still
running the previously deployed template (`2d618fff6205d6a3cc8fa13ed62829f7`); this
polish is pending until the Pi is back online. No rollback or destructive action was attempted.

### 19:17 recheck

`tailscale status` briefly listed `cast` as `idle` then `active; direct`, but the node is
not actually reachable: `tailscale ping -c 2 cast` → `no reply`, `/dev/tcp/.../22` failed,
and SSH timed out again. One short SSH command succeeded at 19:17:11 and confirmed the Pi
still had template MD5 `2d618fff6205d6a3cc8fa13ed62829f7` and all three services `active`.
The copy of `25cfa67` remains pending; no partial deploy was confirmed.

## 2026-11-24 22:09 — pending polish deployed

The Pi became reachable again (Tailscale DERP, then direct). The final template
`986869caa018ff30df1224065183d9b0` was copied after backup
`edge/templates/index.html.bak-20261124-220934`; the MD5 matches the workstation.
An earlier copy at `22:08` (`e592a588618dfc30d79bfef2fb47ad95`) was superseded by the
accessibility fix in commit `b279f6f`.

After restart: all three services `active`, `http://127.0.0.1:5000/` HTTP 200,
`webcheck http://100.126.244.75:5000` → `RESULT: PASS (0 floor, 0 reflex)` at mobile,
tablet and desktop. Local state `seq 45271` was 2.1 s old; Firebase `seq 45269` was
16.3 s old with `last_sync_status = OK (HTTP 200)`. The earlier offline blocker is closed.

## 2026-11-24 22:20 — sensor health check

Live runtime state reported `adxl_ok=True`, `max6675_ok=True`, `acoustic_ok=True`,
`storage_ok=True`, `state=Healthy`, `seq=45355`; acoustic status was
`Hardware I2S Stream (INMP441)`.

With `pdm-daq.service` briefly stopped, `edge/raw_measure.py --count 3` returned live
raw ADXL345 counts (`X=3 Y=60 Z=95`, stable across samples) and MAX6675 words
`0x0308 / 0x0300 / 0x0310` (`open_tc=0`), with no `cal.json` applied. A separate
`arecord -D plughw:1,0 -c 2 -r 48000 -f S32_LE` capture produced 57 valid 50 ms
windows; the first six RMS values were `0.323, 0.342, 0.164, 0.035, 0.092, 0.130`,
confirming a live microphone signal. `arecord -l` lists the expected Google
voiceHAT/INMP441 capture device, and one `arecord` process runs under the DAQ service.
The DAQ service was restarted and all three services remain `active`.

## 2026-11-24 22:35 — Pi-only raw measurement script fix

The Pi's `edge/raw_measure.py` had been replaced by the operator with a 1,011-line
version containing six-position ADXL coefficients (`G_BIAS_*`, `G_SCALE_*`) and
`ADXL_LSB_PER_G = 256.0`. That Pi file is distinct from the 4.8 KB clean script in
this repository; the repository version was not overwritten. The fix was applied by
exact-text replacement so the operator's coefficients and formatting were preserved.

Final deployed file: `/home/renad/pdm/edge/raw_measure.py`, MD5
`3ea87cc2cbfcc2884e39711b11e9630b`, backup
`edge/raw_measure.py.bak-20261124-223357`. Changes: `sound_cal.json` is resolved beside
the script (or via `--sound-cal`), the calibration constant must be finite,
`--calibrate-sound REF_DB` adds an operator calibration step that writes a backed-up
JSON with reference/measured values, CSV creation is append-only, and a failed
`arecord` now prints `[SOUND ERROR] <arecord stderr>` and backs off 1 s instead of
silently logging zero sound. No `cal.json` value was applied or changed and no SPL
constant was invented.

Verification on the Pi: `python3 -m py_compile` OK; `--help` shows both new flags.
The operator's own `python3 raw_measure.py --interval 1` (PID 2778, `arecord` PID
32491) still held the microphone, so the run reported
`[SOUND ERROR] arecord: main:850: audio open error: Device or resource busy`
exactly twice for two samples (one per backoff interval, down from 14 repeated
errors), logged live ADXL/MAX raw values, left `sound_db_estimated` empty, and kept
`sound_cal.json` absent. A second run with the same `--csv` appended one row without
duplicating the header. All three services were `active` afterwards. The calibration
math was unit-tested with a stubbed `SoundReader`: `REF_DB=94`, RMS `0.01` produced
constant `134.000 dB`, matching the expected value; only `/tmp/cal_logic_test.json`
was written on the Pi, not the real calibration file.

`[NEED: reference dB SPL measurement at the mic]` before `--calibrate-sound` can be
run for real. No WhatsApp contact or state was changed.

### 22:40 — live mic test completed

With the operator's approval, PID 2778 was continued and terminated (its stopped
state had swallowed the first TERM), along with its `arecord` child. With
`pdm-daq.service` briefly stopped, the final script produced five live frames in
`/home/renad/raw_measure_live_test_224021.csv`: nonzero RMS on all 5 rows, for example
`RMS 0.002288 / peak 0.005034 / -52.81 dBFS` and
`RMS 0.005213 / peak 0.015647 / -45.66 dBFS`; `sound_db_estimated` stayed empty
because no real calibration exists. `--calibrate-sound 94 --sound-cal
/tmp/cal_live_test.json` captured a live 2 s window (`RMS 0.003166`,
`-49.989 dBFS`) and wrote constant `143.989 dB` to the temp path only. That temp file
and the earlier stub-test JSON were removed; the real `edge/sound_cal.json` remains
absent. All three services were `active` afterwards.

## 2026-11-24 22:47 — operator's raw_measuree.py restored and sound fixed

The operator asked to stop using my guided `edge/calibrate.py` and the sound-cal
variant, and to use their own `edge/raw_measuree.py` (double-e filename) instead.
That file no longer exists on the Pi, so it was reconstructed from the local copy
made before my earlier edits, with all of my sound-calibration additions removed.
`[NEED: the untouched original if exact 657-line formatting matters]` — the logic is
the operator's, but editor normalisation changed the line layout.

Only one change was made to that script: when `arecord` ends early, the reader now
prints `[SOUND ERROR] <arecord stderr>`, a hint to stop `pdm-daq.service`, and backs
off 1 s instead of silently restarting. Raw ADXL345 counts, MAX6675 words and
INMP441 RMS/peak/dBFS output were left as written by the operator. Deployed to
`/home/renad/pdm/edge/raw_measuree.py`, MD5
`d138b961774a77514691289fb360f0fd`, `py_compile` OK. No existing file was
overwritten.

With the DAQ service active, a two-sample run showed
`[SOUND ERROR] arecord: main:850: audio open error: Device or resource busy` plus the
hint, while ADXL/MAX raw values were still logged. With `pdm-daq.service` briefly
stopped, `/home/renad/raw_measuree_live_224721.csv` had four rows with nonzero sound
RMS on all four (`0.002348`, `0.005073`, `0.000873`, `0.000690`) and dBFS values
`-52.59`, `-45.89`, `-61.18`, `-63.22`; raw ADXL LSB and MAX words/counts were
present. Services were restarted and all three are `active`.
`edge/raw_measure.py` (MD5 `3ea87cc2cbfcc2884e39711b11e9630b`), `cal.json`
(`790891637e9b49c0e3beafd59019f697`) and the absent `sound_cal.json` were untouched.

## 2026-11-24 23:05 — offline degradation estimator (no Pi change)

The operator chose the clearly-labelled degradation-model option from the
MathWorks RUL taxonomy. `ml/degradation_rul.py` and
`tests/test_degradation_rul.py` were added on the host only. The tool is an
offline CSV analyser with a required operator threshold; it does not import
the classifier, touch Firebase or change the dashboard. No Pi file, service
or calibration artifact was changed for this step. Full host suite:
`50 tests ... OK`. The result remains **not field-validated** RUL;
`[NEED: measured degradation curve]` and
`[NEED: run-to-failure series with timestamps and failure labels]` are unchanged.

## 2026-11-24 23:10 — read-only deployment check; operator-owned scripts changed

Hosted `https://castpone2026.web.app/` and `/guide.html` both returned HTTP 200.
All three Pi services were `active`; `cal.json` remains MD5
`790891637e9b49c0e3beafd59019f697`.

The operator has since edited the raw scripts themselves, so these are now
**operator-owned and must not be overwritten** without an explicit request:

- `edge/raw_measuree.py`, mtime `2026-11-24 23:07:10`, MD5
  `5caef29453067dd34ce8b9fef00c9bfc`, 16,741 bytes. It keeps the
  `[SOUND ERROR]` / `[HINT]` / 1 s backoff fix, now states 256 LSB/g and writes
  extra `adxl_*_g_calibrated` columns.
- `edge/raw_measure.py`, mtime `2026-11-24 23:05:58`, MD5
  `11be08561ed100c95331656b892acd3f`, back to the operator's original 21,227
  byte version; my earlier fixed variant is no longer deployed there.

`/home/renad/raw_sensor_data.csv` (51 rows, 23:08) has all three sensors'
columns but `sound_rms=0.0` and empty `sound_dbfs`, consistent with the DAQ
service holding the microphone during that run; no script change was made.

## 2026-11-25 — public C-MAPSS FD001 RUL benchmark (no Pi change)

The operator selected NASA C-MAPSS FD001 as a trusted public source. The raw
FD001 files were downloaded from Zenodo (DOI `10.5281/zenodo.15346912`, CC BY
4.0, archive MD5 `79a22f36e80606c69d0e9e4da5bb2b7a`) and vendored into
`data/cmapss/` with verified per-file hashes. `ml/train_rul_cmapss.py`,
`tests/test_rul_cmapss.py` and the benchmark write-up were added on the host
only. Official test RMSE 15.51 cycles / MAE 11.51; unit-held-out validation
last-window RMSE 2.25 cycles. These are simulated turbofan data, not our
motor, and are explicitly **not field-validated**.

No Pi file, service, calibration artifact or Firebase state was changed for
this step. The operator-owned scripts listed above remain untouched. Runtime
diagnosis and the dashboard still report current state only; the benchmark is
an offline reproducibility check, not a live RUL feature.

## 2026-11-25 — real-motor CWRU sample (no Pi change)

At the operator's request, seven unmodified `.mat` files were fetched from the
official CWRU Bearing Data Center (2 hp Reliance Electric induction motor,
healthy plus 7 mil seeded inner-race / ball / outer-race faults at 0 hp) into
`data/cwru/`, with documented MD5 hashes and `tests/test_cwru_data.py`. The
faults are seeded short recordings, so this is **not** a run-to-failure series
and cannot validate RUL. No Pi file, service, calibration artifact or Firebase
state was changed; the runtime classifier remains the same.

## 2026-11-25 — real PRONOSTIA bearing RUL benchmark (no Pi change)

At the operator's request, the six learning bearings from IEEE PHM 2012
PRONOSTIA/FEMTO-ST were vendored into `data/pronostia/` (8,384 unmodified CSVs,
601,742,616 bytes) with an MD5 manifest and explicit source/DOI/licence notes.
`ml/rul_pronostia.py`, `tests/test_rul_pronostia.py` and the write-up were added
on the host only. Leave-one-bearing-out last-window MAE is 182.91 s and RMSE
335.26 s, against 8902.25 s constant-baseline RMSE; all-window MAE is 6656.68 s
and RMSE 9557.01 s. These are real bearing trajectories, not our motor, and are
explicitly **not field-validated**.

No Pi file, service, calibration artifact or Firebase state was changed for
this step. The operator-owned scripts listed above remain untouched; runtime
diagnosis and the dashboard still report current state only.

## 2026-11-25 — target-rig RUL readiness path (no Pi change)

At the operator's request, the host-only files `ml/rul_from_rig.py`,
`tests/test_rul_from_rig.py` and `docs/REAL_MOTOR_READINESS.md` were added. They
accept a future operator-supplied run-to-failure CSV containing the nine
already-deployed Stage-2 features plus an operator-accepted
`failure_timestamp`, build causal trailing windows, evaluate
leave-one-run-out, optionally fit a final regressor and predict RUL from a
current run. Every report/prediction is labelled **not field-validated**.

This is readiness evidence only: no run-to-failure series from our rig exists,
no Pi file, service, calibration artifact or Firebase state was changed, and no
runtime or dashboard behaviour was altered. The operator-owned
`edge/raw_measure.py` and `edge/raw_measuree.py` were not modified for this
step. `[NEED: run-to-failure series with timestamps and failure labels from our
rig]` and `[NEED: operator-accepted failure endpoint and reviewed metric
report]` remain before any field claim.

## 2026-11-25 — XJTU-SY benchmark and hosted evidence (no Pi change)

At the user's request a different public run-to-failure source was fetched:
15 XJTU-SY bearing feature matrices from Mendeley Data DOI
`10.17632/mpn45f4gxc.1` (CC BY 4.0 derived record, source SHA-256 values
checked against the Mendeley API). Host-only files `ml/rul_xjtu_sy.py`,
`ml/rul_xjtu_sy_report.json`, `tests/test_rul_xjtu_sy.py`,
`data/xjtu_sy_mendeley/` and `docs/DATA_PROVENANCE_LICENSES.md` were added.
The causal leave-one-bearing-out benchmark over 9,216 one-minute snapshots
reports last-20% MAE 134.924 min and RMSE 171.776 min against a constant
baseline RMSE of 160.859 min; the model is slightly worse and that is shown as
measured. The hosted `public/index.html` displays these numbers only beside
`BENCHMARK / NOT OUR MOTOR / NOT FIELD-VALIDATED` and the source/licence table;
`public/index.html`, `public/guide.html` and `public/calibration.html` were
converted to light mode.

No Pi file, service, calibration artifact, calibration run record, Firebase
state, Stage-1/Stage-2 behaviour, dependency or runtime model was changed.
Public end-of-life labels are not operator acceptance on our rig, and no
benchmark minute value is a hours-to-failure claim for our motor. Unresolved
licence facts remain `[NEED: explicit XJTU-SY reuse licence]`,
`[NEED: explicit FEMTO-ST dataset licence]`, `[NEED: explicit CWRU dataset
reuse licence]` and `[NEED: exact Reliance Electric catalogue number]`.

## 2026-11-25 — commit `e143171` applied to the powered-on Pi

The verified working tree was committed as `e143171`
(`docs+web: honest real-data RUL benchmark, provenance evidence and light-mode
pages`) and pushed to `origin/main`. The same 39 changed/new non-runtime files
were copied from that commit to `/home/renad/pdm` with `tar`/`scp` (the Pi has
no `git`). Every file that already existed on the Pi was first backed up to
`/home/renad/pdm_backup_e143171_20261125151611` (12 files backed up). All 39
files passed `md5sum -c` on the Pi (`39` OK, no FAILED lines).

Verification on the Pi: `pdm-daq.service`, `pdm-cloud.service` and
`pdm-dashboard.service` were all `active`; `http://127.0.0.1:5000/` returned
HTTP 200. The Flask app serves `edge/templates/index.html`, which was not part
of this change and remains untouched, so `/guide.html` and `/calibration.html`
return 404 on the local Flask port by design — those are hosted Firebase pages
and the synced copies in `public/` contain the benchmark and licence-evidence
markers. The sync manifest contained no `edge/`, `cal.json`, `cloud_config.json`
or state file; any timestamp change on `edge/cloud_config.json` is the Pi's own
cloud writer, not this file sync.

No runtime service was restarted, no calibration artifact, calibration run
record, Stage-1/Stage-2 behaviour, Firebase state or deployed model was changed.
The unresolved `[NEED: ...]` items above are still open and no field-validated
RUL claim is made.

## 2026-11-25 (final) — NASA IMS benchmark and simulator removal

The verified working tree was committed as `83c22e7`
(`Add NASA IMS benchmark, licence evidence and device-only telemetry guard`)
and pushed to `origin/main`. Local checks before deployment:
`PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m unittest discover -s tests` →
`Ran 133 tests` / `OK` in 134.524 s; the 32 targeted NASA/device-only/dashboard
tests also passed; `git diff --check`, `py_compile` and the staged secret scan
passed.

The NASA IMS CSV now contains all 11,620 documented snapshots
(s1_b3 2,156; s1_b4 2,156; s2_b1 984; s3_b3 6,324), SHA-256
`bea57b5ba1fc81c39adda9d550f4a3d39402cbb26bb0ed5c06e0fcba98a7d77d`. The
labelled report gives 2,328 tail windows with MAE 9,165.276 min and RMSE
12,531.872 min against constant-baseline MAE 17,011.804 min and RMSE
17,382.217 min. These are nominal recorded minutes from public bearing tests,
`BENCHMARK / NOT OUR MOTOR / NOT FIELD-VALIDATED`, never hours-to-failure for
our motor.

Web verification: the live `https://castpone2026.web.app/` passed webcheck with
`FLOOR 0`, `REFLEX 0`. A local fixture with an empty RTDB event stream also
passed with `FLOOR 0`, `REFLEX 0` using the written brief; this removes
changing live device figures from the unsourced-figure scan while still
rendering the same page and its `NO DATA` / `AWAITING DATA` paths. The existing
waivers for tiny-text, default-font, long-lines and small-body were retained.
An independent visual-critic subagent was attempted but could not run because
the model usage limit was reached; no visual change was made on that basis.

Firebase CLI (`15.35.0`, logged in as `ammar0xf@gmail.com`) deployed 14 files:
`firebase deploy --only hosting --project castpone2026` finished with
`Release complete` and `Hosting URL: https://castpone2026.web.app`. After
deployment, `index.html`, `guide.html` and `calibration.html` each returned
HTTP 200 (70,200 / 73,727 / 38,644 bytes). The live index contains
`DEVICE TELEMETRY ONLY` and the benchmark label, contains no simulator tokens,
and the calibration page still shows `REVIEW` / `UNVERIFIED`.

All 19 changed/new files from commit `83c22e7` were copied to `/home/renad/pdm`
over SSH. Files already present on the Pi (11) were backed up first to
`/home/renad/pdm_backup_20261125T141936Z`; all 19 files then passed
`md5sum -c` on the Pi with no FAILED lines. Verification on the Pi:
`pdm-daq.service`, `pdm-cloud.service` and `pdm-dashboard.service` were all
`active`; `http://127.0.0.1:5000/` returned HTTP 200; and
`python3 /home/renad/pdm/edge/stream_live.py` only printed
`SIMULATOR REMOVED: telemetry must come from the Raspberry Pi device via
edge/firebase_mirror.py. No simulated data is generated or uploaded.` and
exited without generating or uploading packets.

The runtime services, `edge/templates/index.html`, calibration artifacts,
model and Firebase state were not changed by this sync. The user wording
`REMOVE SIMULATOR, ALL FROM DEVICE` is now present in README, plan, dashboard
and review pack; missing, null and stale dashboard values remain `NO DATA`,
`AWAITING DATA` or `NOT REPORTED`. The unresolved licence `NEED` markers are
still visible and no field-validated RUL claim is made.

## FMCG induction-motor RUL benchmark — repository only, no Pi change

A subsequent repository-only change added `data/fmcg_induction_rul/` and
`ml/rul_fmcg.py` for the headline public RUL benchmark. The vendored Zenodo CSV
matches published MD5 `52df07317901bdb7647c86df479d06c6`, with explicit
CC BY 4.0 metadata and paper DOI `10.35784/acs_7299`. Four RUL-to-zero runs were
evaluated leave-one-run-out on the last 20% of each held run: MAE **141.716 h**,
RMSE **204.069 h** and 24-hour warning accuracy **0.677 (67.7%)**, with the
constant-zero baseline better at **69.185 / 106.164 h** and the no-warning
baseline better at **0.686**. These are measured benchmark values, not
hours-to-failure for our motor and not operator alarm thresholds.

No Pi sync, hosting deploy, runtime service, model, calibration artifact or
Firebase state was changed by this FMCG step. The device-only telemetry rule
`REMOVE SIMULATOR, ALL FROM DEVICE` and the `NO DATA` / `AWAITING DATA` /
`NOT REPORTED` rendering rules remain exactly as verified above.

## CWRU real-motor diagnosis benchmark — repository only, no Pi change

A subsequent repository-only change added `ml/diagnosis_cwru.py`,
`ml/diagnosis_cwru_report.json` and `tests/test_diagnosis_cwru.py`. The four
selected drive-end `.mat` files remain hash-checked and unmodified. Five folds
hold out contiguous 4,096-sample blocks so no vibration sample crosses from
training into test; the measured held-out accuracy is **1.000 (100.0%)** over
1,039 windows against a **0.4004 (40.04%)** majority baseline. These are four
bearing-condition classes on CWRU's 2 hp Reliance Electric motor: not our
deployed taxonomy, not our rig, not RUL and not field validation.

No Pi sync, hosting deploy, runtime service, model, calibration artifact or
Firebase state was changed by this CWRU step. The device-only telemetry rule
and `NO DATA` / `AWAITING DATA` / `NOT REPORTED` rendering remain unchanged.
