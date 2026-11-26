#!/bin/bash
# NEEDS the user's scoped yes (pdm-daq restart, about 6 to 10 s sensor data gap). Rollback: bash ~/stat_stage/g17_rollback.sh
set -e
T=$(date +%Y%m%dT%H%M%S); B=$HOME/stat_stage/g17_backup_$T; mkdir -p $B; E=$HOME/pdm/edge; S=$HOME/stat_stage/g17_new
cp -p $E/edge_daq.py $B/edge_daq.py; cp -p $E/hot_backup.csv $B/hot_backup.csv.pre_g17_copy 2>/dev/null || true
echo $B > $HOME/stat_stage/g17_last_backup
own=$(stat -c %U:%G $E/edge_daq.py); sudo install -o ${own%%:*} -g ${own##*:} -m $(stat -c %a $E/edge_daq.py) $S/edge_daq.py $E/edge_daq.py
python3 -m py_compile $E/edge_daq.py
sudo systemctl restart pdm-daq; sleep 8
systemctl is-active pdm-daq pdm-cloud pdm-dashboard
