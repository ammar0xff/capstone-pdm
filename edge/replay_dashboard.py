#!/usr/bin/env python3
"""Second dashboard instance (port 5002) for the reference-data replay. Reads only the replay state dir.
The live dashboard (port 5000) and its state are untouched."""
import os
import sys

STATE = os.environ.get("G12_STATE_DIR")
if not STATE or "reference" not in STATE:
    sys.exit("set G12_STATE_DIR to the replay state dir (its path must contain 'reference'), e.g. /dev/shm/pdm_reference")
import dashboard  # noqa: E402  (same app as the live dashboard, different state dir)

if __name__ == "__main__":
    port = int(os.environ.get("G12_REPLAY_PORT", "5002"))
    print("[INFO] Reference-data replay dashboard on 0.0.0.0:%d (state %s)" % (port, STATE))
    dashboard.app.run(host=os.environ.get("G12_REPLAY_HOST", "0.0.0.0"), port=port, debug=False, threaded=True)
