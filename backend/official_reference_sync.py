import subprocess
import sys
from pathlib import Path
from threading import Lock
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[1]
OFFICIAL_SOURCE_DIR = ROOT_DIR / "data" / "official_sources"
REFERENCE_DIR = ROOT_DIR / "data" / "reference"
INGEST_SCRIPT_PATH = ROOT_DIR / "scripts" / "ingest_official_rates.py"

OFFICIAL_SOURCE_PDFS = [
    OFFICIAL_SOURCE_DIR / "pmjay_hbp.pdf",
    OFFICIAL_SOURCE_DIR / "cghs_rates.pdf",
    OFFICIAL_SOURCE_DIR / "nppa_prices.pdf",
]

REFERENCE_OUTPUTS = [
    REFERENCE_DIR / "hospital_packages.json",
    REFERENCE_DIR / "bed_rates.json",
    REFERENCE_DIR / "investigation_rates.json",
    REFERENCE_DIR / "pmjay_hbp_packages.json",
    REFERENCE_DIR / "cghs_packages.json",
    REFERENCE_DIR / "nppa_medicine_prices.json",
    REFERENCE_DIR / "medicine_prices.json",
]

SYNC_LOCK = Lock()
LAST_SYNC_STATUS: dict[str, Any] = {"status": "not_run"}


def _path_mtime_ns(path: Path) -> int:
    if not path.exists():
        return -1
    try:
        return int(path.stat().st_mtime_ns)
    except OSError:
        return -1


def _latest_mtime(paths: list[Path]) -> int:
    values = [_path_mtime_ns(path) for path in paths if path.exists()]
    return max(values) if values else -1


def _all_sources_present() -> bool:
    return all(path.exists() for path in OFFICIAL_SOURCE_PDFS)


def _is_reference_stale() -> bool:
    if not _all_sources_present():
        return False

    if any(not output.exists() for output in REFERENCE_OUTPUTS):
        return True

    latest_source = _latest_mtime(OFFICIAL_SOURCE_PDFS)
    earliest_output = min(_path_mtime_ns(path) for path in REFERENCE_OUTPUTS if path.exists())
    return latest_source > earliest_output


def sync_reference_data(force: bool = False) -> dict[str, Any]:
    global LAST_SYNC_STATUS

    with SYNC_LOCK:
        if not force and not _is_reference_stale():
            LAST_SYNC_STATUS = {
                "status": "skipped",
                "reason": "reference_up_to_date_or_source_missing",
                "sourceDir": str(OFFICIAL_SOURCE_DIR),
                "referenceDir": str(REFERENCE_DIR),
            }
            return LAST_SYNC_STATUS

        if not _all_sources_present():
            LAST_SYNC_STATUS = {
                "status": "skipped",
                "reason": "missing_official_source_pdfs",
                "sourceDir": str(OFFICIAL_SOURCE_DIR),
                "missingFiles": [str(path) for path in OFFICIAL_SOURCE_PDFS if not path.exists()],
            }
            return LAST_SYNC_STATUS

        if not INGEST_SCRIPT_PATH.exists():
            LAST_SYNC_STATUS = {
                "status": "failed",
                "reason": "ingest_script_not_found",
                "scriptPath": str(INGEST_SCRIPT_PATH),
            }
            return LAST_SYNC_STATUS

        command = [sys.executable, str(INGEST_SCRIPT_PATH)]
        completed = subprocess.run(
            command,
            cwd=str(ROOT_DIR),
            capture_output=True,
            text=True,
            check=False,
        )

        if completed.returncode != 0:
            LAST_SYNC_STATUS = {
                "status": "failed",
                "reason": "ingestion_process_failed",
                "returncode": completed.returncode,
                "stdoutTail": completed.stdout[-1500:],
                "stderrTail": completed.stderr[-1500:],
            }
            return LAST_SYNC_STATUS

        LAST_SYNC_STATUS = {
            "status": "synced",
            "reason": "reference_regenerated_from_official_sources",
            "sourceDir": str(OFFICIAL_SOURCE_DIR),
            "referenceDir": str(REFERENCE_DIR),
            "stdoutTail": completed.stdout[-1500:],
        }
        return LAST_SYNC_STATUS


def get_sync_status() -> dict[str, Any]:
    return dict(LAST_SYNC_STATUS)


__all__ = ["sync_reference_data", "get_sync_status"]
