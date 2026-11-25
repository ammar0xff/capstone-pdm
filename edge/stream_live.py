#!/usr/bin/env python3
"""Retired telemetry simulator uplink.

This tool used to generate physics-simulated packets and PUT them to the
production Firebase RTDB path. It is disabled: hosted and on-device dashboards
show device telemetry only. There is no simulator, no network client and no
upload path left in this file.
"""

import sys

MESSAGE = (
    "SIMULATOR REMOVED: telemetry must come from the Raspberry Pi device via "
    "edge/firebase_mirror.py. No simulated data is generated or uploaded."
)


def main(argv=None):
    print(MESSAGE, file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
