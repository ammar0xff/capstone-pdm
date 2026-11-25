#!/bin/bash
set -e
B=$(cat $HOME/stat_stage/g15_last_backup); E=$HOME/pdm/edge
own=$(stat -c %U:%G $E/firebase_mirror.py); sudo install -o ${own%%:*} -g ${own##*:} -m $(stat -c %a $E/firebase_mirror.py) $B/firebase_mirror.py $E/firebase_mirror.py
install -m $(stat -c %a $E/templates/index.html) $B/index.html $E/templates/index.html
sudo rm -f /etc/systemd/system/pdm-cloud.service.d/config-save.conf; sudo systemctl daemon-reload
sudo systemctl restart pdm-cloud; sleep 8; sudo systemctl restart pdm-dashboard; sleep 4
systemctl is-active pdm-daq pdm-cloud pdm-dashboard
