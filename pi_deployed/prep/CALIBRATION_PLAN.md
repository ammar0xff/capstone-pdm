# Healthy-baseline calibration plan (preparation only)

Status: prepared offline. Nothing here changes a threshold, restarts a service or injects a fault. Every threshold decision belongs to the user.

## What this can and cannot give
- It gives what the sensors read on this rig during chosen windows, and how often each current rule fires in them.
- It does not give fault-detection accuracy, a validated alarm, or any RUL. hot_backup.csv is unlabelled, and the RF was trained on synthetic data.

## Recordings to take (no induced faults)
Use the normal running rig and the existing logging. For each window write down the start time, end time, motor speed and load, mic position, and who was near the rig.
1. Motor OFF, Pi and sensors ON, 10 min. Separates room and electrical noise from motor noise, mainly for the mic. The 16% of packets above 88 dB with normal vibration needs this.
2. Motor ON, normal running, undisturbed, at least 30 min per speed/load condition actually used. Repeat on a second day if possible.
3. Motor ON, mic physically covered or moved away from the motor (user's choice), 10 min. Only to see whether sound_db follows the motor or the room.
No one touches the sensors during the windows, so any change cannot be blamed on handling.

## Analysis (read-only, runs on the Pi or on a copy)
`python3 baseline_summary.py hot_backup.csv --from <epoch> --to <epoch> --json out.json` for each window. It reports, per feature, percentiles, timestamp gaps, state counts, and the share of rows on which each current rule would fire (values from ml/gate_thresholds.py EDGE). It uses only rows in the current 14-field layout and never edits the CSV.

## How to read the result
- A window the user confirms was healthy where a rule fires on a large share of rows: that threshold does not fit this rig or mic. It is not proof of a fault, and not proof the rule is wrong for a real fault.
- Motor-off sound_db close to motor-on sound_db: the mic reads room noise. The 88 dB rule would then say little about the motor.
- Candidate new thresholds can be proposed as a high percentile of a confirmed healthy window plus a margin the user picks. They stay proposals. Any change needs the user's yes, a staged test, a rollback script and a pdm-daq restart approval. Faults still have no real labelled examples, so a changed threshold stays "uncalibrated for faults".

## Decisions the user must make
1. Which time windows count as healthy.
2. Whether sound alone should keep giving Warning while the mic is uncalibrated (current g14 behaviour), or be shown as information only.
3. Who approves any threshold change, and whether a restart is allowed for it.
4. Whether to keep the hot_backup.csv logging as is, accepting the cloud lag, or choose a no-hardware recording change with its loss window, or a hardware option.
5. Whether to collect run-to-failure data at all. Without it no RUL for this rig is possible.
