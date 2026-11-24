#!/usr/bin/env python3
"""Print raw ADXL345/MAX6675 measurements on the Pi (no cal.json applied).

This is deliberately NOT a calibration script. It applies no ``cal.json``
coefficients: values are the numbers read from the sensors themselves.

    sudo systemctl stop pdm-daq.service
    cd ~/pdm
    python3 edge/raw_measure.py
    python3 edge/raw_measure.py --csv edge/raw_measurements.csv --count 20

Stop the DAQ service first so it does not contend for the I2C/SPI buses.
"""

from __future__ import annotations

import argparse
import csv
import sys
import time
from pathlib import Path
from typing import Any, Callable, Optional

CSV_FIELDS = (
    "n",
    "unix_time",
    "adxl_x_lsb",
    "adxl_y_lsb",
    "adxl_z_lsb",
    "max6675_word_hex",
    "max6675_adc_counts",
    "open_tc",
    "temp_datasheet_c",
)


def positive_float(value: str) -> float:
    parsed = float(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return parsed


def non_negative_int(value: str) -> int:
    parsed = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be zero or greater")
    return parsed


def read_frame(adxl: Any, tc: Any, index: int) -> Optional[dict[str, Any]]:
    """Return one uncalibrated frame, or None when either sensor fails."""
    xyz = adxl.read_raw()
    temp_c, open_tc, raw_word = tc.read_temp()
    if xyz is None or raw_word is None or temp_c is None:
        return None
    x_raw, y_raw, z_raw = xyz
    word = int(raw_word)
    return {
        "n": index,
        "unix_time": time.time(),
        "adxl_x_lsb": int(x_raw),
        "adxl_y_lsb": int(y_raw),
        "adxl_z_lsb": int(z_raw),
        "max6675_word_hex": f"0x{word:04X}",
        "max6675_adc_counts": (word >> 3) & 0x0FFF,
        "open_tc": int(open_tc),
        "temp_datasheet_c": round(float(temp_c), 2),
    }


def format_frame(frame: dict[str, Any]) -> str:
    return (
        f"n={frame['n']:>4} | "
        f"ADXL LSB  X={frame['adxl_x_lsb']:>6} "
        f"Y={frame['adxl_y_lsb']:>6} "
        f"Z={frame['adxl_z_lsb']:>6} | "
        f"MAX6675 {frame['max6675_word_hex']} "
        f"counts={frame['max6675_adc_counts']:>4} "
        f"open_tc={frame['open_tc']} "
        f"T_datasheet={frame['temp_datasheet_c']:.2f} C (UNCALIBRATED)"
    )


def collect(
    adxl: Any,
    tc: Any,
    *,
    count: int = 0,
    interval: float = 0.5,
    csv_path: Optional[Path] = None,
    emit: Callable[[str], None] = print,
) -> int:
    """Read frames until ``count`` is reached (0 = until Ctrl+C)."""
    handle = None
    writer = None
    if csv_path is not None:
        handle = open(csv_path, "w", newline="")
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()

    taken = 0
    try:
        while count == 0 or taken < count:
            frame = read_frame(adxl, tc, taken + 1)
            if frame is not None:
                taken += 1
                emit(format_frame(frame))
                if writer is not None:
                    writer.writerow(frame)
                    handle.flush()
            time.sleep(interval)
    finally:
        if handle is not None:
            handle.close()
    return taken


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--interval",
        type=positive_float,
        default=0.5,
        help="seconds between readings (default: 0.5)",
    )
    parser.add_argument(
        "--count",
        type=non_negative_int,
        default=0,
        help="stop after this many frames; 0 means run until Ctrl+C (default: 0)",
    )
    parser.add_argument(
        "--csv",
        type=Path,
        default=None,
        help="optional CSV output path (raw values, no calibration applied)",
    )
    args = parser.parse_args(argv)

    print("RAW SENSOR MEASUREMENTS - no cal.json applied", flush=True)
    print("Press Ctrl+C to stop. Keep the motor stopped while sampling.\n", flush=True)

    from edge_daq import ADXL345Driver, MAX6675Driver  # noqa: PLC0415

    adxl = ADXL345Driver()
    tc = MAX6675Driver()
    if not adxl.connected or not tc.connected:
        print(
            "[ERR] Sensor init failed; check I2C/SPI and stop pdm-daq.service",
            flush=True,
        )
        return 1

    try:
        taken = collect(
            adxl,
            tc,
            count=args.count,
            interval=args.interval,
            csv_path=args.csv,
        )
    except KeyboardInterrupt:
        print("\nStopped.", flush=True)
        return 0
    print(f"\nStopped after {taken} frame(s).", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
