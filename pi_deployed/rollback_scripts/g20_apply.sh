#!/bin/bash
# NOT APPROVED. Needs the user's explicit scoped yes: replace edge_daq.py (sensor handle-leak fix), restart pdm-daq only (~6-10 s sensor gap).
set -e
E=$HOME/pdm/edge; S=$HOME/stat_stage/g20_new; B=$HOME/stat_stage/g20_backup_$(date +%Y%m%dT%H%M%S); mkdir -p $B
[ "$(md5sum $S/edge_daq.py | cut -c1-8)" = "${G20_EXPECT_MD5:?set G20_EXPECT_MD5}" ] || { echo md5 mismatch; exit 1; }
cp -p $E/edge_daq.py $B/edge_daq.py; echo $B > $HOME/stat_stage/g20_last_backup
own=$(stat -c %U:%G $E/edge_daq.py); sudo install -o ${own%%:*} -g ${own##*:} -m $(stat -c %a $E/edge_daq.py) $S/edge_daq.py $E/edge_daq.py
python3 -m py_compile $E/edge_daq.py; sudo systemctl restart pdm-daq; sleep 10
systemctl is-active pdm-daq pdm-cloud pdm-dashboard; journalctl -u pdm-daq -n 5 --no-pager | grep -i "recording disabled" || true
