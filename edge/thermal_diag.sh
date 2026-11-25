#!/bin/sh
# READ-ONLY heat diagnostic for the Pi. Run only after the owner powers it on and agrees.
# Changes nothing: no restarts, no config edits, no writes except stdout. Save with:
#   sh thermal_diag.sh > /tmp/thermal_diag.txt
# It reports facts; it does not name a cause.
echo "== time/uptime"; date; uptime
echo "== temperature"; vcgencmd measure_temp 2>&1
cat /sys/class/thermal/thermal_zone0/temp 2>&1
echo "== throttled flags (0x0 = never throttled/undervolted since boot)"; vcgencmd get_throttled 2>&1
echo "== clocks"; vcgencmd measure_clock arm 2>&1; cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq 2>&1
echo "== supply voltage"; vcgencmd measure_volts core 2>&1; vcgencmd pmic_read_adc EXT5V_V 2>&1 | head -2
echo "== load"; cat /proc/loadavg; nproc
echo "== top CPU processes"; ps -eo pid,pcpu,pmem,etime,comm --sort=-pcpu | head -12
echo "== pdm services"; systemctl is-active pdm-daq pdm-dashboard pdm-cloud 2>&1
systemctl show pdm-daq -p NRestarts -p ActiveEnterTimestamp 2>&1
echo "== kernel thermal/power messages"; dmesg 2>/dev/null | grep -i -E "under-?volt|throttl|thermal|over-?temp" | tail -15
echo "== recent service log lines"; journalctl -u pdm-daq -n 15 --no-pager 2>&1 | tail -15
echo "== disk"; df -h / | tail -1
