#!/bin/bash
# Run the reference-data replay and its dashboard (port 5002) from a scratch directory, on any machine with python3, numpy and flask.
# Touches nothing else: not the Pi, not the live services, not edge/ or its templates. Stop with Ctrl-C.
# Usage: bash edge/run_replay_local.sh [path/to/data/pronostia/Bearing1_2] [snapshots-per-second]
set -e
R=$(cd "$(dirname "$0")/.." && pwd); B=${1:-$R/data/pronostia/Bearing1_2}; SPEED=${2:-4}
W=$(mktemp -d /tmp/pdm_replay_run.XXXX); mkdir -p $W/templates $W/state_reference
cp $R/pi_deployed/staged_not_applied/dashboard.py.g28 $W/dashboard.py
cp $R/pi_deployed/staged_not_applied/templates_index.html.g28 $W/templates/index.html
cp $R/edge/commissioning.py $R/edge/reference_replay.py $R/edge/replay_dashboard.py $W/
cp $R/ml/gate_thresholds.py $W/
cat > $W/history_log.py <<'PY'
def read_rows(base): return []
PY
cd $W
trap 'kill 0' EXIT
python3 reference_replay.py --bearing-dir "$B" --state-dir $W/state_reference --speed $SPEED --loop &
sleep 2
G12_STATE_DIR=$W/state_reference python3 replay_dashboard.py
