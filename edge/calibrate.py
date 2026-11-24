#!/usr/bin/env python3
"""Guided sensor calibration runner for the Raspberry Pi edge node.

Run this script on the Pi while the machine is stopped:

    sudo systemctl stop pdm-daq.service
    cd ~/pdm
    python3 edge/calibrate.py
    sudo systemctl start pdm-daq.service

It writes edge/cal.json atomically after creating a timestamped backup, stores a
markdown run record and appends a compact JSONL log. The record never claims
metrology accreditation or real-motor validation; it reports what was measured
and what still needs evidence.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import sys
import tempfile
import time
from collections.abc import Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Optional

BASE_DIR = Path(__file__).resolve().parent
CAL_FILE = BASE_DIR / "cal.json"
BACKUP_DIR = BASE_DIR / "calibration_backups"
CERT_FILE = BASE_DIR / "calibration_certificate.md"
LOG_FILE = BASE_DIR / "calibration_runs.jsonl"

FACE_ORDER = ("+X", "-X", "+Y", "-Y", "+Z", "-Z")
AXES = ("x", "y", "z")
AXIS_INDEX = {"x": 0, "y": 1, "z": 2}
POSITIVE_FACE = {"x": "+X", "y": "+Y", "z": "+Z"}
NEGATIVE_FACE = {"x": "-X", "y": "-Y", "z": "-Z"}

RAW_ABS_LIMIT = 32768.0
ADXL_SCALE_MIN = 0.001  # g/LSB; deliberately wider than the configured 0.0039
ADXL_SCALE_MAX = 0.04  # g/LSB; covers common non-full-resolution ADXL345 modes
ADXL_RESIDUAL_TOL_G = 0.05
TEMP_SLOPE_MIN = 0.1
TEMP_SLOPE_MAX = 10.0
DEFAULT_REFERENCE_BOIL_C = 97.5
DEFAULT_ADXL_SAMPLES = 100
DEFAULT_THERMAL_SAMPLES = 12
ADXL_SAMPLE_INTERVAL_S = 0.02
THERMAL_SAMPLE_INTERVAL_S = 0.25

REQUIRED_CAL_KEYS = (
    "t_a",
    "t_b",
    "g_bias_x",
    "g_bias_y",
    "g_bias_z",
    "g_scale",
)

InputFn = Callable[[str], str]
SleepFn = Callable[[float], None]


class CalibrationError(ValueError):
    """Raised when calibration input or hardware readings are unusable."""


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _run_id(now: Optional[datetime] = None) -> str:
    return (now or _utc_now()).strftime("%Y%m%dT%H%M%SZ")


def _finite_float(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise CalibrationError(f"{label} must be a number")
    number = float(value)
    if not math.isfinite(number):
        raise CalibrationError(f"{label} must be finite")
    return number


def parse_triple(text: str, label: str) -> tuple[float, float, float]:
    """Parse three comma- or space-separated numbers into an XYZ triple."""
    parts = [part for part in text.replace(",", " ").split() if part]
    if len(parts) != 3:
        raise CalibrationError(f"{label} needs exactly three numbers (X Y Z)")
    values = tuple(
        _finite_float(float(part), f"{label}[{i}]") for i, part in enumerate(parts)
    )
    if any(abs(value) > RAW_ABS_LIMIT for value in values):
        raise CalibrationError(
            f"{label} contains a raw count outside +/-{RAW_ABS_LIMIT:g}"
        )
    return values  # type: ignore[return-value]


def validate_face_means(face_means: Mapping[str, Sequence[float]]) -> None:
    """Reject missing, malformed, non-finite or out-of-range six-face readings."""
    if set(face_means) != set(FACE_ORDER):
        missing = sorted(set(FACE_ORDER) - set(face_means))
        extra = sorted(set(face_means) - set(FACE_ORDER))
        raise CalibrationError(
            f"six-face readings invalid; missing={missing}, extra={extra}"
        )
    for face in FACE_ORDER:
        values = face_means[face]
        if isinstance(values, (str, bytes)) or not isinstance(values, Sequence):
            raise CalibrationError(f"face {face} must be a three-number sequence")
        if len(values) != 3:
            raise CalibrationError(f"face {face} must contain exactly three numbers")
        for i, value in enumerate(values):
            number = _finite_float(value, f"{face}[{AXES[i]}]")
            if abs(number) > RAW_ABS_LIMIT:
                raise CalibrationError(
                    f"{face}[{AXES[i]}] exceeds the 16-bit raw range"
                )


def fit_adxl345(
    face_means: Mapping[str, Sequence[float]], samples_per_face: Optional[int] = None
) -> dict[str, Any]:
    """Fit the runtime's single-scale ADXL345 model from six static face means.

    Runtime model: calibrated_axis = raw_axis * g_scale - g_bias_axis.
    Face labels mean "that axis points up", so +X expects +1 g on X and -X
    expects -1 g on X.
    """
    validate_face_means(face_means)

    axis_scales: dict[str, float] = {}
    for axis in AXES:
        plus = float(face_means[POSITIVE_FACE[axis]][AXIS_INDEX[axis]])
        minus = float(face_means[NEGATIVE_FACE[axis]][AXIS_INDEX[axis]])
        differential = plus - minus
        if differential <= 0.0:
            raise CalibrationError(f"{axis}-axis +g reading must exceed its -g reading")
        # Raw counts per g -> g per raw count, matching runtime g_scale.
        axis_scales[axis] = 2.0 / differential

    scale = sum(axis_scales.values()) / len(AXES)
    if not (ADXL_SCALE_MIN <= scale <= ADXL_SCALE_MAX):
        raise CalibrationError(
            f"fitted g_scale {scale:.6f} g/LSB is outside the supported range"
        )

    biases = {
        axis: (
            (
                float(face_means[POSITIVE_FACE[axis]][AXIS_INDEX[axis]])
                + float(face_means[NEGATIVE_FACE[axis]][AXIS_INDEX[axis]])
            )
            / 2.0
        )
        * scale
        for axis in AXES
    }

    max_residual = 0.0
    for face in FACE_ORDER:
        expected = [0.0, 0.0, 0.0]
        axis = face[1].lower()
        expected[AXIS_INDEX[axis]] = 1.0 if face[0] == "+" else -1.0
        for i, axis_name in enumerate(AXES):
            calibrated = float(face_means[face][i]) * scale - biases[axis_name]
            max_residual = max(max_residual, abs(calibrated - expected[i]))

    return {
        "calibration": {
            "g_scale": round(scale, 7),
            "g_bias_x": round(biases["x"], 5),
            "g_bias_y": round(biases["y"], 5),
            "g_bias_z": round(biases["z"], 5),
        },
        "axis_scales": {k: round(v, 7) for k, v in axis_scales.items()},
        "face_means": {face: list(map(float, face_means[face])) for face in FACE_ORDER},
        "max_abs_residual_g": round(max_residual, 5),
        "residual_tolerance_g": ADXL_RESIDUAL_TOL_G,
        "residual_ok": max_residual <= ADXL_RESIDUAL_TOL_G,
        "samples_per_face": samples_per_face,
    }


def fit_temperature(
    raw_ice: Any,
    raw_boil: Any,
    reference_ice_c: Any = 0.0,
    reference_boil_c: Any = DEFAULT_REFERENCE_BOIL_C,
) -> dict[str, Any]:
    """Fit T_cal = t_a * T_raw + t_b from two reference temperatures."""
    ice = _finite_float(raw_ice, "ice-bath reading")
    boil = _finite_float(raw_boil, "boiling-water reading")
    ref_ice = _finite_float(reference_ice_c, "ice reference")
    ref_boil = _finite_float(reference_boil_c, "boiling reference")

    if boil <= ice:
        raise CalibrationError("boiling-water reading must exceed ice-bath reading")
    if ref_boil <= ref_ice:
        raise CalibrationError("boiling reference must exceed ice reference")

    slope = (ref_boil - ref_ice) / (boil - ice)
    if not (TEMP_SLOPE_MIN <= slope <= TEMP_SLOPE_MAX):
        raise CalibrationError(
            f"fitted t_a {slope:.4f} is outside the supported range "
            f"[{TEMP_SLOPE_MIN}, {TEMP_SLOPE_MAX}]"
        )
    intercept = ref_ice - slope * ice
    if not math.isfinite(intercept):
        raise CalibrationError("fitted t_b is not finite")

    return {
        "calibration": {"t_a": round(slope, 6), "t_b": round(intercept, 6)},
        "points": {
            "ice": {"raw_c": ice, "reference_c": ref_ice},
            "boil": {"raw_c": boil, "reference_c": ref_boil},
        },
        "third_check": None,
    }


def add_thermal_check(
    fit: dict[str, Any], raw_c: Any, reference_c: Any, tolerance_c: float = 1.5
) -> dict[str, Any]:
    """Record an optional third-point residual; never overwrite the two-point fit."""
    raw = _finite_float(raw_c, "third-point raw reading")
    reference = _finite_float(reference_c, "third-point reference")
    calibration = fit["calibration"]
    corrected = calibration["t_a"] * raw + calibration["t_b"]
    fit["third_check"] = {
        "raw_c": raw,
        "reference_c": reference,
        "corrected_c": round(corrected, 4),
        "residual_c": round(corrected - reference, 4),
        "tolerance_c": tolerance_c,
        "within_tolerance": abs(corrected - reference) <= tolerance_c,
    }
    return fit


def validate_calibration(cal: Mapping[str, Any]) -> None:
    """Ensure the result can be consumed by edge/edge_daq.py without surprises."""
    for key in REQUIRED_CAL_KEYS:
        if key not in cal:
            raise CalibrationError(f"calibration is missing required key: {key}")
        _finite_float(cal[key], key)
    scale = float(cal["g_scale"])
    if not (ADXL_SCALE_MIN <= scale <= ADXL_SCALE_MAX):
        raise CalibrationError("g_scale is outside the supported range")
    slope = float(cal["t_a"])
    if not (TEMP_SLOPE_MIN <= slope <= TEMP_SLOPE_MAX):
        raise CalibrationError("t_a is outside the supported range")
    for axis in AXES:
        if abs(float(cal[f"g_bias_{axis}"])) > 2.0:
            raise CalibrationError(f"g_bias_{axis} is implausibly large")


def load_existing_cal(path: Path = CAL_FILE) -> dict[str, Any]:
    """Load the current runtime calibration, or return the documented defaults."""
    defaults: dict[str, Any] = {
        "t_a": 1.0,
        "t_b": 0.0,
        "g_bias_x": 0.0,
        "g_bias_y": 0.0,
        "g_bias_z": 0.0,
        "g_scale": 0.0039,
    }
    if not path.exists():
        return defaults
    try:
        with path.open(encoding="utf-8") as handle:
            loaded = json.load(handle)
        if not isinstance(loaded, dict):
            raise CalibrationError("cal.json must contain a JSON object")
        defaults.update(loaded)
        validate_calibration(defaults)
        return defaults
    except (OSError, ValueError, json.JSONDecodeError, CalibrationError) as exc:
        raise CalibrationError(f"cannot use existing {path}: {exc}") from exc


def backup_existing_cal(
    path: Path = CAL_FILE, backup_dir: Path = BACKUP_DIR
) -> Optional[Path]:
    """Copy the current cal.json to a timestamped backup before any write."""
    if not path.exists():
        return None
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = _run_id()
    target = backup_dir / f"cal-{stamp}.json"
    suffix = 1
    while target.exists():
        target = backup_dir / f"cal-{stamp}-{suffix}.json"
        suffix += 1
    shutil.copy2(path, target)
    return target


def atomic_write_json(payload: Mapping[str, Any], path: Path) -> None:
    """Write JSON through a temporary file in the same directory, then replace."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    except BaseException:
        if os.path.exists(temp_name):
            os.unlink(temp_name)
        raise


def atomic_write_text(text: str, path: Path) -> None:
    """Write UTF-8 text atomically using the same safety pattern as JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    except BaseException:
        if os.path.exists(temp_name):
            os.unlink(temp_name)
        raise


def append_run_log(record: Mapping[str, Any], path: Path = LOG_FILE) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")


def sample_adxl_face(
    reader: Any,
    count: int,
    interval: float,
    sleep_fn: SleepFn = time.sleep,
) -> tuple[float, float, float]:
    if count < 10:
        raise CalibrationError("at least 10 samples per face are required")
    readings: list[tuple[float, float, float]] = []
    for _ in range(count):
        raw = reader.read_raw()
        if raw is None:
            raise CalibrationError("ADXL345 returned no data")
        readings.append(parse_triple(",".join(str(v) for v in raw), "ADXL345 raw"))
        sleep_fn(interval)
    return tuple(sum(row[i] for row in readings) / count for i in range(3))  # type: ignore[return-value]


def sample_temperature_point(
    reader: Any,
    label: str,
    count: int,
    interval: float,
    input_fn: InputFn,
    sleep_fn: SleepFn = time.sleep,
) -> float:
    if count < 3:
        raise CalibrationError("at least three thermal samples are required")
    input_fn(f"Place the probe in {label}. Press ENTER when the reading is stable.")
    values: list[float] = []
    for _ in range(count):
        temp_c, open_tc, _raw_word = reader.read_temp()
        if temp_c is None or open_tc:
            raise CalibrationError(f"MAX6675 has no valid reading in {label}")
        values.append(_finite_float(temp_c, f"{label} temperature"))
        sleep_fn(interval)
    return sum(values) / len(values)


def prompt_face_means(input_fn: InputFn) -> dict[str, tuple[float, float, float]]:
    means: dict[str, tuple[float, float, float]] = {}
    for face in FACE_ORDER:
        text = input_fn(
            f"Enter averaged raw X,Y,Z for {face} pointing up (LSB, comma separated): "
        )
        means[face] = parse_triple(text, f"{face} raw")
    return means


def prompt_float(
    input_fn: InputFn, label: str, default: Optional[float] = None
) -> float:
    suffix = f" [default {default}]" if default is not None else ""
    text = input_fn(f"{label}{suffix}: ").strip()
    if not text and default is not None:
        return default
    return _finite_float(float(text), label)


def new_report(
    operator: str, mode: str, run_id: Optional[str] = None
) -> dict[str, Any]:
    return {
        "run_id": run_id or _run_id(),
        "utc": _utc_now().isoformat(timespec="seconds"),
        "operator": operator or "not recorded",
        "mode": mode,
        "adxl": None,
        "temperature": None,
        "errors": [],
        "verdict": "UNVERIFIED — no new measurements captured",
    }


def verdict_for(report: Mapping[str, Any]) -> str:
    if report["errors"]:
        return "FAILED — no calibration file written"
    adxl = report.get("adxl")
    temp = report.get("temperature")
    if not adxl and not temp:
        return "UNVERIFIED — no new measurements captured"
    concerns = []
    if adxl is not None and not adxl["residual_ok"]:
        concerns.append("ADXL345 residual above tolerance")
    if temp is not None and temp["third_check"] is None:
        concerns.append("no third-point thermal check")
    if (
        temp is not None
        and temp["third_check"]
        and not temp["third_check"]["within_tolerance"]
    ):
        concerns.append("third-point thermal residual above tolerance")
    if concerns:
        return "REVIEW — " + "; ".join(concerns)
    return "REVIEW — measurements captured; operator sign-off still required"


def render_certificate(report: Mapping[str, Any], cal: Mapping[str, Any]) -> str:
    adxl = report.get("adxl")
    temp = report.get("temperature")
    adxl_lines = [
        "### ADXL345 six-face fit",
        "- **Status:** " + ("captured" if adxl else "NOT PERFORMED"),
    ]
    if adxl:
        fit = adxl["calibration"]
        adxl_lines += [
            f"- **Samples per face:** {adxl['samples_per_face']}",
            f"- **Shared scale:** {fit['g_scale']:.7f} g/LSB",
            f"- **Biases (g):** X={fit['g_bias_x']:+.5f}, "
            f"Y={fit['g_bias_y']:+.5f}, Z={fit['g_bias_z']:+.5f}",
            f"- **Max absolute residual:** {adxl['max_abs_residual_g']:.5f} g "
            f"(tolerance {adxl['residual_tolerance_g']:.2f} g; "
            f"{'within' if adxl['residual_ok'] else 'outside'} tolerance)",
        ]

    temp_lines = [
        "### MAX6675 two-point thermal fit",
        "- **Status:** " + ("captured" if temp else "NOT PERFORMED"),
    ]
    if temp:
        fit = temp["calibration"]
        ice = temp["points"]["ice"]
        boil = temp["points"]["boil"]
        temp_lines += [
            f"- **Ice point:** raw {ice['raw_c']:.2f} C -> reference {ice['reference_c']:.2f} C",
            f"- **Boiling point:** raw {boil['raw_c']:.2f} C -> reference {boil['reference_c']:.2f} C",
            f"- **Equation:** T_cal = {fit['t_a']:.6f} * T_raw + ({fit['t_b']:+.6f})",
        ]
        check = temp["third_check"]
        if check:
            temp_lines.append(
                f"- **Third point:** raw {check['raw_c']:.2f} C, reference "
                f"{check['reference_c']:.2f} C, residual {check['residual_c']:+.3f} C "
                f"({'within' if check['within_tolerance'] else 'outside'} "
                f"{check['tolerance_c']:.2f} C tolerance)"
            )
        else:
            temp_lines.append("- **Third point:** NOT PERFORMED")

    return f"""# Sensor calibration run record

> This is a run record, **not a certified metrology report**. It never authorises
> exhibition use by itself.

- **Run ID:** {report["run_id"]}
- **UTC:** {report["utc"]}
- **Operator:** {report["operator"]}
- **Capture mode:** {report["mode"]}
- **Verdict:** {report["verdict"]}

## What was written

```json
{json.dumps(cal, indent=2, sort_keys=True)}
```

## Measurements

{chr(10).join(adxl_lines)}

{chr(10).join(temp_lines)}

## What this record does not prove

- `[NEED: reference thermometer ID, calibration date and uncertainty]`
- `[NEED: measured local boiling temperature or site pressure]`
- `[NEED: signed operator sheet and photographs of each face/reference bath]`
- `[NEED: real-motor verification of vibration and temperature features]`

The two-point thermal fit is exact at its two reference points by construction;
it does not demonstrate accuracy at other temperatures. The ADXL345 fit uses one
shared scale because `edge/edge_daq.py` applies a single `g_scale` to all axes.
"""


def _load_hardware() -> tuple[Any, Any]:
    edge_dir = str(BASE_DIR)
    if edge_dir not in sys.path:
        sys.path.insert(0, edge_dir)
    from edge_daq import ADXL345Driver, MAX6675Driver  # noqa: PLC0415

    return ADXL345Driver(), MAX6675Driver()


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--samples", type=int, default=DEFAULT_ADXL_SAMPLES)
    parser.add_argument("--thermal-samples", type=int, default=DEFAULT_THERMAL_SAMPLES)
    parser.add_argument(
        "--reference-boil", type=float, default=DEFAULT_REFERENCE_BOIL_C
    )
    parser.add_argument("--operator", default="")
    parser.add_argument(
        "--manual", action="store_true", help="enter averaged raw values"
    )
    parser.add_argument("--skip-adxl", action="store_true")
    parser.add_argument("--skip-temp", action="store_true")
    parser.add_argument(
        "--no-write", action="store_true", help="preview without writing"
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    operator = args.operator or input("Operator name (or press ENTER): ").strip()
    report = new_report(operator, "manual" if args.manual else "hardware")
    cal = load_existing_cal()
    adxl_driver = temp_driver = None

    try:
        if args.skip_adxl and args.skip_temp:
            raise CalibrationError("at least one calibration section must be selected")

        if not args.manual:
            adxl_driver, temp_driver = _load_hardware()
            if not adxl_driver.connected:
                raise CalibrationError(
                    "ADXL345 is not connected; check I2C and stop pdm-daq"
                )
            if not temp_driver.connected:
                raise CalibrationError(
                    "MAX6675 is not connected; check SPI and stop pdm-daq"
                )

        if not args.skip_adxl:
            print("\n=== ADXL345 six-face calibration (machine stopped) ===")
            if args.manual:
                means = prompt_face_means(input)
            else:
                means = {}
                for face in FACE_ORDER:
                    input(
                        f"Orient {face} pointing up on a level surface, then press ENTER. "
                    )
                    means[face] = sample_adxl_face(
                        adxl_driver, args.samples, ADXL_SAMPLE_INTERVAL_S
                    )
            report["adxl"] = fit_adxl345(means, samples_per_face=args.samples)
            cal.update(report["adxl"]["calibration"])

        if not args.skip_temp:
            print("\n=== MAX6675 two-point calibration ===")
            if args.manual:
                ice = prompt_float(input, "Ice-bath raw temperature (C)")
                boil = prompt_float(input, "Boiling-water raw temperature (C)")
            else:
                ice = sample_temperature_point(
                    temp_driver,
                    "crushed ice / distilled water slush",
                    args.thermal_samples,
                    THERMAL_SAMPLE_INTERVAL_S,
                    input,
                )
                boil = sample_temperature_point(
                    temp_driver,
                    "boiling distilled water",
                    args.thermal_samples,
                    THERMAL_SAMPLE_INTERVAL_S,
                    input,
                )
            reference_boil = prompt_float(
                input, "Measured boiling reference (C)", args.reference_boil
            )
            temp_fit = fit_temperature(ice, boil, 0.0, reference_boil)
            answer = (
                input("Do you have a third known-temperature check? (y/N): ")
                .strip()
                .lower()
            )
            if answer == "y":
                raw = prompt_float(input, "Third-point raw temperature (C)")
                reference = prompt_float(input, "Third-point reference temperature (C)")
                add_thermal_check(temp_fit, raw, reference)
            report["temperature"] = temp_fit
            cal.update(temp_fit["calibration"])

        validate_calibration(cal)
    except (CalibrationError, OSError) as exc:
        report["errors"].append(str(exc))
        report["verdict"] = verdict_for(report)
        print(f"\n[ERROR] {exc}", file=sys.stderr)
        print(render_certificate(report, cal))
        return 1

    report["verdict"] = verdict_for(report)
    certificate = render_certificate(report, cal)
    if args.no_write:
        print(certificate)
        return 0

    backup = backup_existing_cal()
    atomic_write_json(cal, CAL_FILE)
    atomic_write_text(certificate, CERT_FILE)
    append_run_log(
        {
            "run_id": report["run_id"],
            "utc": report["utc"],
            "operator": report["operator"],
            "mode": report["mode"],
            "verdict": report["verdict"],
            "cal_file": str(CAL_FILE),
            "backup": str(backup) if backup else None,
            "certificate": str(CERT_FILE),
            "adxl_residual_g": (report["adxl"] or {}).get("max_abs_residual_g"),
            "thermal_slope": (report["temperature"] or {})
            .get("calibration", {})
            .get("t_a"),
        }
    )
    print(f"\n[SUCCESS] Calibration written to {CAL_FILE}")
    print(f"[SUCCESS] Backup: {backup or 'none (no previous cal.json)'}")
    print(f"[SUCCESS] Run record: {CERT_FILE}")
    print(f"[SUCCESS] Verdict: {report['verdict']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
