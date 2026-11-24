# Development and operations guide

This is the day-to-day operating manual. Follow it in order; each step names
the command and the evidence that proves it worked.

## 1. Principles

1. Change the source, regenerate outputs, then test. Never hand-edit generated
   files in `circuit/out/`, `public/*.png` or `ml/*.png`.
2. Keep model and Stage-1/Stage-2 decision behavior unchanged unless the task
   explicitly asks for it and `tests/test_evaluation.py` is updated.
3. Never claim field accuracy, RUL, cost savings or CPU savings without a
   measurement. Use `[NEED: ...]` in docs when evidence is absent.
4. No WhatsApp access, no chat state changes and no secrets in the repository.
5. Calibration is a deliberate Pi-side operation, never a dashboard button.

## 2. Local development loop

```bash
cd ~/Documents/antigravity/intelligent-raman
git status --short
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m unittest discover -s tests -v
git diff --check
```

Expected baseline at the time of writing: **31 tests, OK**. If a test fails,
read the full failure before editing; do not weaken the test.

After a successful change:

```bash
git add <exact-files>
git diff --staged --check
git commit -m "short imperative summary"
git push origin main
```

## 3. Regenerating artifacts

| Change | Command | Output |
|---|---|---|
| Circuit wiring or parts | `python3 circuit/build.py` | `circuit/out/` |
| Report/book charts | `python3 book_assets/make_charts.py` | `book_assets/*.png`, `ml/*.png` |
| Synthetic dataset | `python3 ml/dataset_generator.py` | `ml/windows.csv` |
| Model and metadata | `python3 ml/train_rf.py` | `ml/model.joblib`, `ml/model_meta.json` |
| English PDF guide | print `docs/PROJECT_GUIDE.html` to PDF | `docs/G12_Project_Guide.pdf` |

Training and dataset generation must stay run-disjoint. `tests/test_evaluation.py`
checks grouping, feature policy and that `z_score` remains a gate-only metric.

## 4. Pi deployment

Verified deployment path is `/home/renad/pdm`, user `renad`.

```bash
ssh renad@<pi-address>
cd ~/pdm
git pull --ff-only
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v

for s in pdm-daq pdm-cloud pdm-dashboard; do
  sudo cp "edge/$s.service" "/etc/systemd/system/$s.service"
done
sudo systemctl daemon-reload
sudo systemctl restart pdm-daq.service pdm-cloud.service pdm-dashboard.service
sudo systemctl status pdm-daq.service pdm-cloud.service pdm-dashboard.service
journalctl -u pdm-daq.service -n 50 --no-pager
```

Only these three units are services. Calibration and exhibition tools run
manually. See `docs/PI_DEPLOYMENT_EVIDENCE.md` for the verified 2026-11-23
service table and model MD5 match.

### Rollback

1. Stop the affected unit: `sudo systemctl stop pdm-daq.service`.
2. Restore the previous file from the Pi backup or `git checkout <known-commit> -- <file>`.
3. Restart and verify with `systemctl status` and `journalctl`.
4. For the model, restore the `.bak-*` files listed in
   `docs/PI_DEPLOYMENT_EVIDENCE.md`, then restart `pdm-daq.service`.

Do not use `git reset --hard`, force push or delete runtime state without an
explicit decision.

## 5. Calibration operation

Calibration changes how raw sensor counts become engineering units, so the DAQ
service must be stopped:

```bash
sudo systemctl stop pdm-daq.service
python3 edge/calibrate.py
sudo systemctl start pdm-daq.service
```

Outputs: timestamped backup in `edge/calibration_backups/`, atomic
`edge/cal.json`, `edge/calibration_certificate.md` and one line in
`edge/calibration_runs.jsonl`. The record says `REVIEW` or `UNVERIFIED`; it does
not grant exhibition authorization. Full procedure: `docs/CALIBRATION_RUNBOOK.md`.

## 6. Firebase and hosting operation

- Project: `castpone2026`.
- RTDB mirror: `https://castpone2026-default-rtdb.firebaseio.com/motor1.json`.
- Current rules are public read/write. Treat the URL as a security issue until
  an auth decision is made; see `docs/FIREBASE_SETUP.md`.
- Deploy the presentation site with `firebase deploy --only hosting`.

## 7. Definition of done

- [ ] Requirement mapped to a test or a named evidence file.
- [ ] Full test suite run and `git diff --check` clean.
- [ ] Docs updated in the same commit as behavior.
- [ ] No new unverified claim, secret, debug print or generated-file edit.
- [ ] Dashboard change browser-checked at 390, 768 and 1440 px.
- [ ] Commit pushed to `origin/main`; Pi deployment evidence recorded if deployed.
