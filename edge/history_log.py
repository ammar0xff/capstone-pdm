"""History CSV schema handling. Never edits an existing log file.

The Pi's hot_backup.csv was created with an 11-column header; the writer now
adds 14 columns per row. csv.DictReader then mislabels every new row. Rather
than rewrite the raw file, new rows go to a versioned file when the existing
header does not match, and readers map each row by its own column count.
"""
import csv
import os

COLUMNS_V2 = ["timestamp", "seq", "g_mag", "rms_dyn", "kurtosis", "crest_factor", "peak_dyn",
              "temp_c", "temp_slope", "sound_db", "sound_zcr", "state", "fault_label", "fault_proba"]
COLUMNS_V1 = ["timestamp", "seq", "g_mag", "rms_dyn", "kurtosis", "peak_dyn", "temp_c",
              "temp_slope", "state", "fault_label", "fault_proba"]
LEGACY_NAME = "hot_backup.csv"
V2_NAME = "hot_backup_v2.csv"


def _header(path):
    try:
        with open(path, newline="") as f:
            return next(csv.reader(f), None)
    except OSError:
        return None


def resolve_history_path(base_dir):
    """Path new rows should be appended to. Creates nothing. Uses an absolute base_dir
    so the result does not depend on the working directory."""
    base_dir = os.path.abspath(base_dir)
    legacy = os.path.join(base_dir, LEGACY_NAME)
    if not os.path.exists(legacy) or _header(legacy) == COLUMNS_V2:
        return legacy
    return os.path.join(base_dir, V2_NAME)


def ensure_header(path):
    """Write the header only to a missing or empty file, so a restart never adds a second one."""
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        with open(path, "w", newline="") as f:
            csv.writer(f).writerow(COLUMNS_V2)


def _parse_lines(path):
    """Yield (row list) for each trustworthy line. Skipped, never repaired: lines with
    NUL bytes (power-loss zero fill), undecodable lines, an unterminated last line
    (a writer may be mid-write), and lines whose first field is not a timestamp."""
    with open(path, "rb") as f:
        data = f.read()
    lines = data.split(b"\n")
    if lines and lines[-1] != b"":
        lines = lines[:-1]  # unterminated last line: possibly being written right now
    for raw in lines[1:]:  # first line is the header
        if not raw or b"\x00" in raw:
            continue
        try:
            text = raw.decode("utf-8").rstrip("\r")
            row = next(csv.reader([text]))
            float(row[0])
        except (UnicodeDecodeError, StopIteration, ValueError, IndexError, csv.Error):
            continue
        yield row


def read_rows(base_dir):
    """All trustworthy rows from the legacy file and the v2 file as dicts, mapped by each
    row's own width (11 or 14). Any other width is skipped, never guessed."""
    out = []
    for name in (LEGACY_NAME, V2_NAME):
        path = os.path.join(base_dir, name)
        if not os.path.exists(path):
            continue
        for row in _parse_lines(path):
            if len(row) == len(COLUMNS_V2):
                out.append(dict(zip(COLUMNS_V2, row)))
            elif len(row) == len(COLUMNS_V1):
                out.append(dict(zip(COLUMNS_V1, row)))
    return out
