B=$(cat $HOME/stat_stage/g14m_last_backup); E=$HOME/pdm/edge
own=$(stat -c %U:%G $E/firebase_mirror.py); sudo install -o ${own%%:*} -g ${own##*:} -m $(stat -c %a $E/firebase_mirror.py) $B/firebase_mirror.py $E/firebase_mirror.py; sudo systemctl restart pdm-cloud; sleep 6; systemctl is-active pdm-cloud
