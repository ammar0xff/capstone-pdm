#!/bin/bash
# G28 commissioning baseline. NOT RUN YET: waits for the user's go-ahead after the plan and test results are shown.
# Run on the Pi after copying the 4 files to ~/stat_stage/g28_new/. Backs up first, refuses to run if the Pi files are not the expected ones.
set -e
E=$HOME/pdm/edge; S=$HOME/stat_stage/g28_new; B=$HOME/stat_stage/g28_backup_$(date +%Y%m%dT%H%M%S); mkdir -p $B
# 1. the files on the Pi must be the ones this change was written against (Nov 26 evening)
[ "$(md5sum $E/edge_daq.py | cut -c1-32)" = "bc13bc7cb2ff46f5d445051ab267a8dd" ] || { echo "edge_daq.py on the Pi changed since G28 was written; stop"; exit 1; }
[ "$(md5sum $E/dashboard.py | cut -c1-32)" = "4b9438943f73e7a0e9a854bb304486b2" ] || { echo "dashboard.py changed; stop"; exit 1; }
[ "$(md5sum $E/templates/index.html | cut -c1-32)" = "85171f49a1fb80f48276b2effb726917" ] || { echo "templates/index.html changed; stop"; exit 1; }
# 2. new files must match the expected md5s (set by the caller from the tested copies)
for f in edge_daq.py commissioning.py dashboard.py index.html; do
  v=G28_MD5_$(echo $f | tr a-z. A-Z_); exp=${!v:?set $v}
  [ "$(md5sum $S/$f | cut -c1-32)" = "$exp" ] || { echo "$f md5 mismatch"; exit 1; }
done
# 3. backup
cp -p $E/edge_daq.py $E/dashboard.py $B/; cp -p $E/templates/index.html $B/index.html
[ -f $E/commissioning.py ] && cp -p $E/commissioning.py $B/commissioning.py.prev || true
echo $B > $HOME/stat_stage/g28_last_backup
# 4. install (keep owner and mode), compile, restart the two services that changed
own=$(stat -c %U:%G $E/edge_daq.py)
inst() { sudo install -o ${own%%:*} -g ${own##*:} -m 644 "$1" "$2"; }
inst $S/commissioning.py $E/commissioning.py; inst $S/edge_daq.py $E/edge_daq.py
inst $S/dashboard.py $E/dashboard.py; inst $S/index.html $E/templates/index.html
python3 -m py_compile $E/edge_daq.py $E/commissioning.py $E/dashboard.py
sudo systemctl restart pdm-daq pdm-dashboard; sleep 12
systemctl is-active pdm-daq pdm-cloud pdm-dashboard
journalctl -u pdm-daq -n 6 --no-pager | cut -c1-160
