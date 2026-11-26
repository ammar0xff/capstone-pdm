#!/bin/bash
# READ-ONLY health checklist for the PDM Pi. Changes nothing, restarts nothing, prints no tokens/secrets.
# Run when the Pi is powered and reachable:  bash pi_health_check.sh
E=$HOME/pdm/edge
echo "== time/uptime"; date; uptime -p; uptime -s
echo "== services (expect active x3)"; systemctl is-active pdm-daq pdm-cloud pdm-dashboard
echo "== service start times (was there an unplanned restart?)"; for s in pdm-daq pdm-cloud pdm-dashboard; do echo "$s $(systemctl show $s -p ActiveEnterTimestamp --value) restarts=$(systemctl show $s -p NRestarts --value)"; done
echo "== live file checksums vs last known (prefix match)"
chk(){ f=$1; want=$2; got=$(md5sum "$f" 2>/dev/null | cut -c1-8); [ "$got" = "$want" ] && echo "MATCH $f $got" || echo "DIFF  $f got=$got expected=$want"; }
chk $E/edge_daq.py 61d9d903; chk $E/firebase_mirror.py 6cbecc52; chk $E/templates/index.html 7784aa51
echo "== no experimental files live (expect nothing)"; ls $E/csv_sync2.py $E/*.unflushed_* 2>/dev/null
echo "== Pi health"; vcgencmd get_throttled 2>/dev/null; vcgencmd measure_temp 2>/dev/null; free -m | sed -n 1,2p; df -h / | tail -1
echo "== journal/commit latency (cumulative since mount)"; grep -E "average commit|logging transaction|handles per" /proc/fs/jbd2/*/info 2>/dev/null
echo "== latest state packet (no secrets)"
python3 - <<'PY'
import json,time,os
p="/dev/shm/pdm/latest_state.json"
if not os.path.exists(p): p=os.path.expanduser("~/pdm/edge/latest_state.json")
try:
    d=json.load(open(p)); print("file",p,"age_s",round(time.time()-os.path.getmtime(p),1))
    print({k:d.get(k) for k in ("timestamp","seq","state","fault_label","fault_proba","fault_proba_source","input_valid","rf_executed")})
    ai=d.get("ai") or {}; print("gate_status:",(d.get("ai") or {}).get("gate_status") or d.get("gate_status"))
except Exception as e: print("could not read state:",e)
PY
echo "== hot_backup.csv"; ls -l $E/hot_backup.csv; tail -n 3 $E/hot_backup.csv | cut -c1-200
python3 - <<'PY'
import os,time
p=os.path.expanduser("~/pdm/edge/hot_backup.csv")
L=open(p,"rb").read().splitlines()[-1].decode(errors="ignore").split(",")
try: print("last row age_s",round(time.time()-float(L[0]),1),"fields",len(L))
except Exception as e: print("last row not parseable",e)
PY
echo "== errors in last 10 min (counts only)"; for s in pdm-daq pdm-cloud pdm-dashboard; do echo "$s errors/warnings: $(journalctl -u $s --since '-10 min' -p warning --no-pager 2>/dev/null | grep -vc '^-- ')"; done
echo "== sensors seen in last daq log lines (names only)"; journalctl -u pdm-daq -n 15 --no-pager 2>/dev/null | cut -c1-160
echo "== MANUAL: open the hosted dashboard and read packet age; compare with file age above"
