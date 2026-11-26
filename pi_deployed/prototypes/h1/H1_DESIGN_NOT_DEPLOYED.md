# H1 (EXPERIMENTAL, NOT QUALIFIED FOR APPROVAL OR DEPLOYMENT): tmpfs append log + separate sync process (design, prototype only; nothing deployed)
edge_daq keeps appending one row per open/append/close, but to a tmpfs file; a separate process copies whole lines to the durable hot_backup.csv with pwrite at a deterministic offset (idempotent retries). The sampling loop no longer waits on the SD journal.
Facts: dirty_expire 30 s, writeback 5 s, so today's appends already sit in page cache for 5-35 s before reaching the card; a power cut already loses that window.
Needs (not done): edge_daq change (append target tmpfs, header only on durable) + restart; new systemd unit (After/Before ordering, final flush on stop); user decision on the loss contract.
Contract if built: daq crash loses nothing; power cut/reboot loses rows not yet synced (target sync every 1-2 s); durable file lags by the sync delay; if durable file is truncated externally the syncer halts and logs, never guesses; a failed pwrite is retried at the same offset (no duplicate); a power cut mid-pwrite can leave a torn last line, as today.
Open: tmpfs growth (about 9 MB/day at 1 row/s), reader lag (dashboard history), stop ordering, syncer stats file.

## v2 (csv_sync2.py, test_csv_sync2.py) - offline results only
Passed: 8x real-subprocess SIGKILL + restart under continuous appends (exactly-once, in order); kill between write and state save (replay, no duplicate); state file lost (recovered by matching durable tail to live, or halt for manual check if ambiguous); reboot-style loss of tmpfs (fresh start, history kept); torn durable tail isolated with one extra newline (extend only); live shrink or durable truncation (halt and flag, nothing written); short write and ENOSPC (retry same offset, io_errors counted, last_error visible). fsync after every copy step (intended ordering, power-loss behaviour NOT tested). Rows in live are never deleted by the program.
Unit files: pdm-csv-sync.service + pdm-daq drop-in (daq After= syncer, so stop order is daq then syncer; final drain bounded to 20 s, TimeoutStopSec=40). Only syntax-checked with systemd-analyze here; real stop ordering not exercised on the Pi.
Not built: edge_daq g18 (append target tmpfs, header only on durable, behaviour when tmpfs append fails), apply/rollback scripts.

## Known gaps (per review, 2026-11-26 02:44)
- Lost-state tail matching can still duplicate rows when the durable tail is corrupt in specific ways.
- No handling yet for a failed append to the tmpfs log in edge_daq (g18 not built).
- Stats are not surfaced outside /dev/shm.
- Shutdown ordering and bounded drain not exercised on real systemd.
- Power-loss durability not tested. Status: experimental only.
