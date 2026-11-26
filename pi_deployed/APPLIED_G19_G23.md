# Applied on the Pi, 2026-11-26 (EET): g19 to g23 (edge_daq.py)

LIVE NOW: edge_daq.py md5 cba63adf (g23, installed 08:41:37, pdm-daq restarted once for each step). firebase_mirror.py 6cbecc52 (g15) and templates/index.html 7784aa51 are unchanged by these steps.

Each step was approved by the user in WhatsApp (recording off 07:41 and restart "اه" 07:46; sensor fix "اعتمد متسألنيش" 08:18; routine PDM repairs and necessary service restarts then covered by the user's 08:19 calibration). One pdm-daq restart each: g19 07:47, g20 08:19, g21 08:24, g22 08:32, g23 08:41.

| step | md5 (8) | change vs previous |
|---|---|---|
| g14 | 61d9d903 | earlier live version |
| g19 | e4bb40dd | local CSV recording OFF by default (env G12_CSV_RECORDING=1 turns it on). hot_backup.csv is never opened or changed while off. |
| g20 | 17a51081 | ADXL345 and MAX6675 drivers close the old handle before reopen, re-init at most once per second; stale accelerometer (no sample over 1 s) gives Unknown, never Healthy; a thermal Fault is still reported. Fixes a file-descriptor leak (about 41,000 re-opens in 30 s, then "Too many open files" froze publishing). |
| g21 | 9222ca1b | one read error reopens at once, backoff only after 3 consecutive errors; stale threshold 2 s; read errors logged at most every 10 s. |
| g22 | 414d4406 | if the accelerometer never delivers a 64-sample window, NaN samples are seeded so an explicit Unknown packet still publishes (before: no packet, frozen file and cloud). |
| g23 | cba63adf | kurtosis is null (not 3.0) for a NaN window; thermal-fault carry-through checks temperature values only. |

Rollback (each restarts pdm-daq once): ~/stat_stage/g23_rollback.sh returns to g22. Earlier rollback scripts g22, g21, g20, g19 each restore the previous file from ~/stat_stage/gNN_backup_*. Old g14 rollback: g14_rollback.sh. Backups exist on the Pi under ~/stat_stage.

Measured (live): 08:25 to 08:32 cloud frozen (g20/g21 and a dead ADXL: no packet published; cause found in a fake-hardware full-loop test). After g22: 169 cloud reads over 374 s, age median 3.0 s, p95 5.8 s, max 19.4 s (restart), 6 of 169 over 8 s. After g23: 48 reads over 100 s, median 2.8 s, max 5.3 s. Live strict JSON: 29 payloads with no NaN/Infinity.

Known limits (not validated):
- The ADXL345 I2C link is intermittent (Remote I/O errors 08:25 to 08:38, answering again by 08:42). Cause unknown; no wiring claim.
- The dead-ADXL branch of g22/g23 was tested only with fake devices and the real main() loop on a laptop, not on the Pi. The 1 s and 2 s thresholds and the 3-error backoff were chosen, not tuned on the rig.
- ai.predicted_class still says "Normal Operation" when the Random Forest was not run. The UI uses rf_executed and gate_status, so the page states "RF not run" correctly. Left as a documented limitation.
- Recording is off by the user's choice for speed. hot_backup.csv (12,415,541 bytes, last modified 07:47:11) is preserved and still readable; /api/history returns the last 100 old rows and no longer advances.
- The state labels come from an uncalibrated rule gate. The user states the motor has been stopped since the last recording yesterday (exact time unknown), so today's Healthy, Unknown and Fault readings are unvalidated stopped-rig readings, not mechanical findings. The historical CSV is not a healthy baseline.
- No RUL is supported for this rig.

## g24 (2026-11-26 09:03 EET, routine repair)
- edge_daq.py md5 d9245a42. One pdm-daq restart at 09:03:17. Backup ~/stat_stage/g24_backup_20261126T090313 on the Pi, rollback ~/stat_stage/g24_rollback.sh (not run).
- ai.predicted_class and ai.predicted_class_id are null when rf_executed is false (before: "Normal Operation" / 0, including for Unknown packets).
- Loud-sound label and advice use "relative mic level" wording. Thresholds unchanged.
- Measured after restart: 48 cloud reads over 100 s, median 2.5 s, max 5.5 s, 0 over 8 s, 0 errors, no NaN/Infinity tokens. CSV untouched. The dashboard pages render with live data.
- Hosted page text for the "RF not run" case now says no class is reported.
