#!/bin/bash
set -e
B=$(cat $HOME/stat_stage/g20_last_backup); E=$HOME/pdm/edge
own=$(stat -c %U:%G $E/edge_daq.py); sudo install -o ${own%%:*} -g ${own##*:} -m $(stat -c %a $E/edge_daq.py) $B/edge_daq.py $E/edge_daq.py
sudo systemctl restart pdm-daq; sleep 10; systemctl is-active pdm-daq pdm-cloud pdm-dashboard
