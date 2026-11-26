#!/bin/bash
# Undo G28: restore the 3 backed-up files, remove commissioning.py. The baseline file and any dated .reset-* copies are left alone (they are inert without commissioning.py).
set -e
B=$(cat $HOME/stat_stage/g28_last_backup); E=$HOME/pdm/edge
own=$(stat -c %U:%G $E/edge_daq.py)
inst() { sudo install -o ${own%%:*} -g ${own##*:} -m 644 "$1" "$2"; }
inst $B/edge_daq.py $E/edge_daq.py; inst $B/dashboard.py $E/dashboard.py; inst $B/index.html $E/templates/index.html
if [ -f $B/commissioning.py.prev ]; then inst $B/commissioning.py.prev $E/commissioning.py; else sudo rm -f $E/commissioning.py; fi
sudo systemctl restart pdm-daq pdm-dashboard; sleep 12
systemctl is-active pdm-daq pdm-cloud pdm-dashboard
md5sum $E/edge_daq.py $E/dashboard.py $E/templates/index.html
