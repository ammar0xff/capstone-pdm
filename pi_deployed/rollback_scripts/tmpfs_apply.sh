#!/bin/bash
# Needs the user's explicit yes. Restarts pdm-daq, pdm-cloud, pdm-dashboard (about 20 s without data). Rollback: bash ~/stat_stage/tmpfs_rollback.sh
set -e
T=$(date +%Y%m%dT%H%M%S); B=$HOME/stat_stage/tmpfs_backup_$T; mkdir -p $B; E=$HOME/pdm/edge; S=$HOME/stat_stage/tmpfs_new
for f in edge_daq.py firebase_mirror.py dashboard.py exhibition_drill.py; do cp -p $E/$f $B/$f; done
echo $B > $HOME/stat_stage/tmpfs_last_backup
for f in edge_daq.py firebase_mirror.py dashboard.py exhibition_drill.py; do
  own=$(stat -c %U:%G $E/$f); sudo install -o ${own%%:*} -g ${own##*:} -m $(stat -c %a $E/$f) $S/$f $E/$f
done
for u in pdm-daq pdm-cloud pdm-dashboard; do sudo mkdir -p /etc/systemd/system/$u.service.d; done
printf '[Service]\nEnvironment=G12_STATE_DIR=/dev/shm/pdm\n' | sudo tee /etc/systemd/system/pdm-daq.service.d/tmpfs-state.conf >/dev/null
printf '[Service]\nEnvironment=G12_STATE_DIR=/dev/shm/pdm\nEnvironment=G12_MIRROR_LIGHT=1\nEnvironment=G12_MIRROR_KEEPALIVE=1\nEnvironment=PYTHONUNBUFFERED=1\n' | sudo tee /etc/systemd/system/pdm-cloud.service.d/tmpfs-state.conf >/dev/null
printf '[Service]\nEnvironment=G12_STATE_DIR=/dev/shm/pdm\n' | sudo tee /etc/systemd/system/pdm-dashboard.service.d/tmpfs-state.conf >/dev/null
sudo systemctl daemon-reload
sudo systemctl restart pdm-daq; sleep 6
sudo systemctl restart pdm-cloud pdm-dashboard; sleep 8
systemctl is-active pdm-daq pdm-cloud pdm-dashboard
ls -la /dev/shm/pdm/latest_state.json
