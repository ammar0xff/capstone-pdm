# Stall diagnosis 2026-11-26 (read-only measurements)
1. Paired 200 s log (paired_timing_20261126_0205.log): edge state file had gaps of 7.0, 19.2, 5.8, 14.3, 6.9 s; cloud /motor1/seq stood still 20.0, 15.0, 11.5 s at the same times; mirror kept syncing every 5 s (no interval over 7 s); HTTPS GET latency p50 0.66 s, max 1.07 s, 0 errors. So stale cloud data came from the edge loop, not the mirror or the network.
2. Task states of the edge_daq main thread sampled every 20 ms for 100 s while in uninterruptible sleep: about 1160 samples blocked in write() to /home/renad/pdm/edge/hot_backup.csv (ext4 journal wait, do_get_write_access / folio_wait_bit_common); the rest were short I2C transfers and sleeps.
3. Proposed fix (staged, not applied): CSV append moved to a writer thread, one row per open/append/close as before, drained on SIGTERM. Tested offline with a simulated blocked disk.
Not claimed: that the card is degraded; that the fix removes every stall.
