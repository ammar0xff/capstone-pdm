# Storage / stall review, 2026-11-26 (read-only; nothing applied; g17 archived, not execution-ready)

Observed
- Edge state source paused 5-19 s; cloud seq froze 11-20 s at the same times; mirror synced every 5 s; Firebase GET latency steady (paired 200 s log).
- edge_daq main thread sampled in uninterruptible sleep: ~1160 samples in write() to hot_backup.csv waiting on the ext4 journal.
- 30 s write sample: jbd2 64 KB, tailscaled 8 KB, edge_daq 4 KB. No fsync in edge_daq or the mirror.
- jbd2 (cumulative since mount, 1713 txns): avg commit 1.33 s, logging 2.08 s, ~12 logged blocks per txn.
- Root: ext4 rw,noatime on mmcblk0p2. Card descriptor: date 08/2014, zeroed manfid/oemid.

Qualified reading
- Consistent with slow storage/journal commit latency. Not proven to be the only cause; CPU/GIL not conclusively ruled out; card degradation not established.
- No software-only change was found that keeps the current synchronous per-row CSV contract and removes the stalls. This is a statement about what was reviewed, not proof that none exists.

Options (each needs a user decision)
- Writer thread (g17, archived): removes loop stall; changes durability (crash-loss window, separate unflushed spill file, up to 1 duplicated row, counted fragments/drops).
- ext4 commit/data-mode tuning or tmpfs staging + periodic sync: widens power-cut loss window.
- Different medium for hot_backup.csv: any hardware path must first verify the actual device, mount, filesystem and permissions; never format or assume empty; no purchase without user decision.
