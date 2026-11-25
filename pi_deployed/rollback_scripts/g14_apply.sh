#!/bin/bash
# User approved 01:29 EET. Restarts pdm-daq and pdm-dashboard only. Rollback: bash ~/stat_stage/g14_rollback.sh
set -e
T=$(date +%Y%m%dT%H%M%S); B=$HOME/stat_stage/g14_backup_$T; mkdir -p $B; E=$HOME/pdm/edge; S=$HOME/stat_stage/g14_new
cp -p $E/edge_daq.py $B/edge_daq.py; cp -p $E/templates/index.html $B/index.html
echo $B > $HOME/stat_stage/g14_last_backup
own=$(stat -c %U:%G $E/edge_daq.py); sudo install -o ${own%%:*} -g ${own##*:} -m $(stat -c %a $E/edge_daq.py) $S/edge_daq.py $E/edge_daq.py
install -m $(stat -c %a $E/templates/index.html) $S/index.html $E/templates/index.html
python3 -m py_compile $E/edge_daq.py
sudo systemctl restart pdm-daq; sleep 6
sudo systemctl restart pdm-dashboard; sleep 4
systemctl is-active pdm-daq pdm-cloud pdm-dashboard
