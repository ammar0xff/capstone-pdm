#!/usr/bin/env python3
"""Regenerate the compact NASA IMS feature record from the downloaded archive.

This tool is only for reproducibility. It needs ``unrar`` on PATH and the
1.06 GB public IMS.zip; it never runs as part of the tests or the dashboard.
It streams one RAR member at a time, so the multi-gigabyte raw text is never
bulk-extracted to disk. Only RMS and kurtosis of the documented failed-bearing
channels are kept.

Usage:

    python3 ml/nasa_ims_features.py --zip /path/IMS.zip \
        --out data/nasa_ims/failed_bearings.csv
"""

from __future__ import annotations

import argparse
import csv
import datetime
import hashlib
import json
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Sequence

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rul_nasa_ims import ARCHIVE_SHA256, BEARING_CONFIG  # noqa: E402

SAMPLES_PER_SNAPSHOT = 20_480
SET_CONFIG = {
    "1st_test": dict(rar="1st_test.rar", prefix="1st_test/", channels=8, first_5min=43),
    "2nd_test": dict(rar="2nd_test.rar", prefix="2nd_test/", channels=4, first_5min=0),
    "3rd_test": dict(
        rar="3rd_test.rar", prefix="4th_test/txt/", channels=4, first_5min=0
    ),
}
CSV_COLUMNS = (
    "set",
    "bearing",
    "failure",
    "snapshot",
    "minutes",
    "timestamp",
    "rms1",
    "kurt1",
    "rms2",
    "kurt2",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def nominal_minutes(index: int, first_5min: int) -> float:
    if index < first_5min:
        return index * 5.0
    return first_5min * 5.0 + (index - first_5min) * 10.0


def rms_and_kurtosis(values: np.ndarray) -> tuple[float, float]:
    rms = float(np.sqrt(np.mean(np.square(values))))
    centred = values - float(np.mean(values))
    denominator = float(np.mean(np.square(centred)))
    kurtosis = (
        float(np.mean(np.power(centred, 4)) / denominator**2 - 3.0)
        if denominator > 0
        else float("nan")
    )
    return rms, kurtosis


def derive(zip_path: Path, out_path: Path, extract_dir: Path) -> dict[str, int]:
    """Write the feature CSV; return snapshot counts keyed by bearing id."""

    if sha256_file(zip_path) != ARCHIVE_SHA256:
        raise ValueError(f"{zip_path} does not match the recorded IMS.zip SHA-256")
    counts: dict[str, int] = {}
    with zipfile.ZipFile(zip_path) as archive:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(CSV_COLUMNS)
            for set_name, config in SET_CONFIG.items():
                rar_path = extract_dir / "IMS" / config["rar"]
                if not rar_path.exists():
                    rar_path.parent.mkdir(parents=True, exist_ok=True)
                    archive.extract("IMS/" + config["rar"], extract_dir)
                names = [
                    name
                    for name in subprocess.check_output(
                        ["unrar", "lb", str(rar_path)], text=True
                    ).splitlines()
                    if name.startswith(config["prefix"]) and len(name) > len(config["prefix"])
                ]
                bearings = [entry for entry in BEARING_CONFIG if entry[1] == set_name]
                for index, name in enumerate(names):
                    raw = subprocess.check_output(
                        ["unrar", "p", "-inul", str(rar_path), name]
                    )
                    values = np.fromstring(raw, dtype=float, sep="\t")
                    expected = SAMPLES_PER_SNAPSHOT * config["channels"]
                    if values.size != expected:
                        raise ValueError(
                            f"{name}: got {values.size} values, expected {expected}"
                        )
                    stamp = datetime.datetime.strptime(
                        name[len(config["prefix"]) :], "%Y.%m.%d.%H.%M.%S"
                    )
                    for bearing_id, failure, channels in bearings:
                        stats = [
                            rms_and_kurtosis(values[channel :: config["channels"]])
                            for channel in channels
                        ]
                        row = [
                            set_name,
                            bearing_id,
                            failure,
                            index,
                            nominal_minutes(index, config["first_5min"]),
                            stamp.isoformat(),
                        ]
                        for pair in stats:
                            row.extend(pair)
                        while len(stats) < 2:
                            row.extend(["", ""])
                            stats.append(None)
                        writer.writerow(row)
                        counts[bearing_id] = counts.get(bearing_id, 0) + 1
                    if index and index % 500 == 0:
                        print(f"{set_name}: {index}/{len(names)}", file=sys.stderr)
    return counts


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--zip", default="/tmp/opencode/IMS.zip")
    parser.add_argument(
        "--out",
        default=str(
            Path(__file__).resolve().parent.parent
            / "data"
            / "nasa_ims"
            / "failed_bearings.csv"
        ),
    )
    parser.add_argument("--extract-dir", default="/tmp/opencode/ims_extract")
    args = parser.parse_args(argv)
    try:
        counts = derive(Path(args.zip), Path(args.out), Path(args.extract_dir))
    except (OSError, ValueError, zipfile.BadZipFile) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(json.dumps(counts, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
