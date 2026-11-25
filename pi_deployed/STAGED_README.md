Staged 2026-11-26, NOT applied (needs the user's scoped yes for a pdm-cloud and pdm-dashboard restart):
- firebase_mirror.py.g15: throttled, atomic cloud_config.json save (G12_CONFIG_SAVE_EVERY_S=60 via drop-in). SIGTERM flushes the daily counter exactly; after an unclean stop the counter is rounded UP by the writes that could be unsaved, never reset or lowered. Tested against a local fake Firebase (counter continuity after clean stop and SIGKILL, rewrites 3 vs about 35 in 7 s).
- templates_index.html.next: Unknown/Input invalid header, neutral warning/fault header text, AI card shows rule result for Healthy, Arabic strings. Rendered with synthetic feeds only.
- Apply: bash ~/stat_stage/g15_apply.sh on the Pi. Rollback: g15_rollback.sh.
