# Pi deployed files (captured 2026-11-26 EET from the live Pi, read-only copy)
live/ = files running now. Not the repo's source of truth for the Pi; the Pi itself holds the backups listed in rollback_scripts/backup_dirs_on_pi.txt.
staged_not_applied/ = template wording fix waiting for the next approved pdm-dashboard restart.
tests/ = offline tests (synthetic inputs only). Rollback: rollback_scripts/*.
Not claimed: fault accuracy, calibrated baselines, RUL, speech removal.
## md5 of live files
 4b9438943f73e7a0e9a854bb304486b2  live/dashboard.py
 61d9d9038980cb339bc322a02268699c  live/edge_daq.py
 860917d12be1c34d2c43b77335d892fa  live/exhibition_drill.py
 319e4709dd10a814cdca1134a44cbd21  live/firebase_mirror.py
 2d27499ef6161ee40c0b1e9348399839  live/index.html
