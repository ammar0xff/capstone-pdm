#!/bin/bash
# NEEDS the user's scoped yes. Restarts pdm-cloud (about 9 s cloud gap) and pdm-dashboard (about 4 s). No pdm-daq restart.
# Rollback: bash ~/stat_stage/g15_rollback.sh
set -e
T=$(date +%Y%m%dT%H%M%S); B=$HOME/stat_stage/g15_backup_$T; mkdir -p $B; E=$HOME/pdm/edge; S=$HOME/stat_stage/g15_new
cp -p $E/firebase_mirror.py $B/; cp -p $E/templates/index.html $B/index.html; cp -p $E/cloud_config.json $B/
echo $B > $HOME/stat_stage/g15_last_backup
own=$(stat -c %U:%G $E/firebase_mirror.py); sudo install -o ${own%%:*} -g ${own##*:} -m $(stat -c %a $E/firebase_mirror.py) $S/firebase_mirror.py $E/firebase_mirror.py
install -m $(stat -c %a $E/templates/index.html) $S/index.html $E/templates/index.html
python3 -m py_compile $E/firebase_mirror.py
printf '[Service]\nEnvironment=G12_CONFIG_SAVE_EVERY_S=60\n' | sudo tee /etc/systemd/system/pdm-cloud.service.d/config-save.conf >/dev/null
sudo systemctl daemon-reload
sudo systemctl restart pdm-cloud; sleep 8
sudo systemctl restart pdm-dashboard; sleep 4
systemctl is-active pdm-daq pdm-cloud pdm-dashboard
