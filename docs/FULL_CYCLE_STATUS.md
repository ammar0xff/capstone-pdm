# PDM full-cycle status (G12), checked 2026-11-26 00:57 to 01:15 EET

Scope: read-only checks of the live Pi (services, code, state), the Firebase copy and the hosted dashboard. No faults were induced. No new recordings. Numbers below are measurements from that window unless marked otherwise.

## Stage table

| Stage | What it does | Status | Evidence |
|---|---|---|---|
| ADXL345 vibration | Polled in the main loop, software timestamps | REAL, rate unstable | Polled rate in the packet ranged 8 to 382 Hz (40 samples: median 245 to 287 Hz, 10 to 15% of seconds under 50 Hz). Sensor output rate is 400 Hz. |
| MAX6675 temperature | Read every 250 ms | REAL | adxl_ok / max6675_ok flags true in latest_state.json |
| INMP441 microphone | arecord stream, level, ZCR | REAL, uncalibrated level | acoustic_ok true; dB value is not a calibrated sound pressure level |
| Stationary mic component (stat_*) | Median-spectrum filter, display only | REAL, experimental | Enabled 00:52 with G12_MIC_STAT=1; not an input to the gate or the classifier; about 6 to 12 dB below raw, so not comparable; not speech removal |
| Features | rms, peak, crest, kurtosis, temp slope, sound | REAL values | computed on the Pi each 100 ms window |
| Stage 1 SPC gate | Shewhart rule on rms_dyn | NOT CALIBRATED FOR THIS RIG | Hard-coded baseline 0.080 g, sigma 0.025 g, warning 0.13 g. Live rms_dyn about 0.007 g, z about -2.9. The gate cannot breach at this scale. "Healthy / Normal Operation" is a result of this, not proof of motor health. |
| Stage 2 Random Forest | 300 trees, 4 classes | SYNTHETIC TRAINING, NOT RUN LIVE | model_meta.json: physics-simulated benchmark, no real motor measurements. It only runs after a gate breach. No accuracy on real faults exists. |
| fault_proba 0.05 | Value in the packet | DEFAULT, NOT A MEASUREMENT | It is the gated default when the classifier did not run. |
| Advice and response plan | Text per class | STATIC LOOKUP | A table keyed by the class label, not a model output. |
| RUL | Remaining useful life | DISCONNECTED | No RUL in the runtime, state, dashboard or cloud payload. ml/rul_*.py are offline benchmark scripts. No run-to-failure data from this rig exists. The dashboard shows no RUL number. |
| Local state file | latest_state.json, rewritten 10 times a second on the SD card | BOTTLENECK (hypothesis) | iowait 19 to 50%, SD busy writing about 36 to 47% of the time, state age up to 4.9 s. Fix prepared, not applied. |
| Cloud mirror | PUT of the whole state every 5 s plus request time | REAL, near-real-time | Cloud copy age typically 5 to 6 s, spikes of 10 to 23 s measured. Not sub-second. |
| Offline queue | Up to 200 frames in cloud_backlog.json | PARTIAL | Frames are kept while offline and cleared after the next success. They are NOT replayed to the cloud. No SQLite. |
| Hosted dashboard | Polls and SSE from Firebase | REAL | Shows stale state after 20 s without a new packet. |

## What this does not show

- No fault-detection accuracy, no RUL validity and no proof that the motor is healthy.
- The vibration baseline log (hot_backup.csv) is unlabelled for motor state and handling. Its median rms_dyn of 0.0072 g only describes what the logger usually saw.
- Sync delay causes are measured at the symptom level. The state-file I/O stall is a hypothesis until a before and after test.
- Firebase limits (Spark plan): 1 GB stored, 10 GB per month downloads, 100 simultaneous connections. Source: https://firebase.google.com/docs/database/usage/limits and https://firebase.google.com/pricing . The 15,000 writes per day guard is an app-defined constant, not a provider quota. A daily-equivalent of the monthly download figure is not a proven enforced daily cap.
