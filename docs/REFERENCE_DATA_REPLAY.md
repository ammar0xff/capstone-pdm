# Reference-data replay (PRONOSTIA as a stand-in for the motor signal)

Status: built and tested locally. NOT deployed to the Pi. Live mode, the live services and the 0.04 g rms gate are untouched.

## What it is
A second pipeline run that feeds public PRONOSTIA bearing data through the same chain as the rig: baseline commissioning, SPC gate, rule-based fault state, trend indicator. It has its own state dir (default `/dev/shm/pdm_reference`, it refuses the live state dir) and its own dashboard on port 5002.

## Label (shown on screen, English and Arabic)
"Reference data: PRONOSTIA, stand-in for the motor signal (public benchmark)". The Arabic text is `LABEL_AR` in `edge/reference_replay.py`.
This data was not measured on our motor and the result is not validated on the rig. The banner also shows dataset, recording, snapshot, band (180 Hz) and amplitude scale.

## Mapping
- Read `acc_*.csv`, take the 2-axis dynamic magnitude, band-limit to 180 Hz (the rig stream band).
- Compute rms, peak, crest, kurtosis per snapshot, same schema as the rig packets, plus a `reference_data` block.
- Rescale amplitude so the healthy start equals 0.03 g. The scale is shown (Bearing1_2: x0.39195).
- Replay settles 30 snapshots (run-in), then commissioning learns the baseline from 180 snapshots.

## Results, Bearing1_2 (871 snapshots)
- Commissioning started at snapshot 30, accepted at 210: mu 0.0293 g, sigma 0.00157 g, warn 0.0324, fault 0.034.
- Starting at snapshot 1 is refused by the drift rule: the run-in is not steady.
- Default baseline (0.080 / 0.025): nothing ever trips.
- Commissioned baseline: first Warning at 639, first Fault at 730. Healthy 700, Warning 41, Fault 130 snapshots.
- Trend indicator: first estimate at 668 (0.285 h estimated vs 0.564 h true), flickers, at limit from 750.

## Limits (be honest about these)
- Degradation is weak in the 180 Hz band. A 1 kHz band shows it clearly but is beyond the rig stream.
- Trend estimate underpredicts: the gate fault limit is not the failure point. It is a dataset-time indicator, not a validated RUL.
- No classifier. Fault = rule-based gate.
- Not validated on our motor.

## Run
Needs python3, numpy, flask. From the repo root:
`bash edge/run_replay_local.sh data/pronostia/Bearing1_2 4`
It copies what it needs to a temp dir, starts the replay and the dashboard on port 5002, stops on Ctrl-C.
Manual: `python3 edge/reference_replay.py --bearing-dir data/pronostia/Bearing1_2` and `G12_STATE_DIR=/dev/shm/pdm_reference python3 edge/replay_dashboard.py`.
The dashboard needs the staged g28 `dashboard.py` and template (`pi_deployed/staged_not_applied/`).

## If later put on the Pi (user decision, not done)
Only new files: `reference_replay.py`, `replay_dashboard.py`, `commissioning.py`, `gate_thresholds.py`, run on port 5002 in a separate process. Who may reach port 5002 is the user's call. Rollback = stop the process and delete those files; the live services never change. Back up before copying anything over an existing file.
