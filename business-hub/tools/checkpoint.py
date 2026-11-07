"""Create a local, self-contained restore point without changing project files.

Source files are zipped, and SQLite's backup API takes a consistent copy even
when the demo server is running. No network access or third-party tools.
"""

import argparse
import re
import sqlite3
import tempfile
import zipfile
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_DIRECTORIES = {".restore-points", "__pycache__", ".git", "node_modules"}


def create_checkpoint(label):
    safe_label = re.sub(r"[^a-zA-Z0-9-]+", "-", label).strip("-") or "checkpoint"
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    checkpoint_directory = PROJECT_ROOT / ".restore-points"
    checkpoint_directory.mkdir(exist_ok=True)
    archive_path = checkpoint_directory / f"{timestamp}-{safe_label}.zip"

    with tempfile.TemporaryDirectory(prefix="business-hub-backup-") as temporary:
        backups = []
        data_directory = PROJECT_ROOT / "data"
        if data_directory.exists():
            for database_path in data_directory.glob("*.sqlite3"):
                backup_path = Path(temporary) / database_path.name
                with closing(sqlite3.connect(f"{database_path.as_uri()}?mode=ro", uri=True)) as source:
                    with closing(sqlite3.connect(backup_path)) as destination:
                        source.backup(destination)
                backups.append((backup_path, f"data/{database_path.name}"))

        with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(PROJECT_ROOT.rglob("*")):
                relative = path.relative_to(PROJECT_ROOT)
                if any(part in EXCLUDED_DIRECTORIES for part in relative.parts):
                    continue
                if not path.is_file() or path.is_symlink():
                    continue
                # The database copy above includes committed state, never live WAL files.
                if path.suffix in {".sqlite3", ".pyc"} or path.name.endswith(("-wal", "-shm")):
                    continue
                # Runtime secrets should never become portable source snapshots.
                if path.name == ".env" or path.name.startswith(".env.") and path.name != ".env.example":
                    continue
                archive.write(path, str(relative).replace("\\", "/"))
            for backup_path, relative in backups:
                archive.write(backup_path, relative)
            archive.writestr("RESTORE_NOTE.txt", (
                f"Business Hub restore point: {safe_label}\nCreated (UTC): {timestamp}\n\n"
                "Extract into a NEW EMPTY folder. Read WORK_STATE.md then README.md.\n"
                "This is a local snapshot; any included database may contain customer data.\n"
                "Keep it private. No passwords or external account credentials are included.\n"
                "Do not replace the database while the application is running.\n"
            ))
    print(f"Restore point saved: {archive_path}")
    return archive_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label", default="manual", help="Short name for this milestone")
    create_checkpoint(parser.parse_args().label)
