set -e
E=$HOME/pdm/edge; B=$HOME/stat_stage/g14m_backup_$(date +%Y%m%dT%H%M%S); mkdir -p $B; cp -p $E/firebase_mirror.py $B/
echo $B > $HOME/stat_stage/g14m_last_backup
own=$(stat -c %U:%G $E/firebase_mirror.py); sudo install -o ${own%%:*} -g ${own##*:} -m $(stat -c %a $E/firebase_mirror.py) $HOME/stat_stage/g14_new/firebase_mirror.py $E/firebase_mirror.py
python3 -m py_compile $E/firebase_mirror.py
sudo systemctl restart pdm-cloud; sleep 8; systemctl is-active pdm-cloud
