#!/bin/bash
set -e
B=$(cat $HOME/stat_stage/tmpfs_last_backup); E=$HOME/pdm/edge
for f in edge_daq.py firebase_mirror.py dashboard.py exhibition_drill.py; do
  own=$(stat -c %U:%G $E/$f); sudo install -o ${own%%:*} -g ${own##*:} -m $(stat -c %a $E/$f) $B/$f $E/$f
done
sudo rm -f /etc/systemd/system/pdm-{daq,cloud,dashboard}.service.d/tmpfs-state.conf
sudo systemctl daemon-reload; sudo systemctl restart pdm-daq; sleep 6; sudo systemctl restart pdm-cloud pdm-dashboard; sleep 6
systemctl is-active pdm-daq pdm-cloud pdm-dashboard; ls -la $E/latest_state.json
