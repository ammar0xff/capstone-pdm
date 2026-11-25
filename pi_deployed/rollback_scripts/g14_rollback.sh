#!/bin/bash
set -e
B=$(cat $HOME/stat_stage/g14_last_backup); E=$HOME/pdm/edge
own=$(stat -c %U:%G $E/edge_daq.py); sudo install -o ${own%%:*} -g ${own##*:} -m $(stat -c %a $E/edge_daq.py) $B/edge_daq.py $E/edge_daq.py
install -m $(stat -c %a $E/templates/index.html) $B/index.html $E/templates/index.html
sudo systemctl restart pdm-daq; sleep 6; sudo systemctl restart pdm-dashboard; sleep 4
systemctl is-active pdm-daq pdm-cloud pdm-dashboard
