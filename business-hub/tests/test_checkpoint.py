"""Confirm that a restore point can recover source and committed SQLite data."""

from contextlib import closing, redirect_stdout
import io
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from tools import checkpoint


class CheckpointTests(unittest.TestCase):
    def test_snapshot_recovers_committed_wal_data_and_excludes_runtime_files(self):
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory) / "project"
            project.mkdir()
            (project / "README.md").write_text("A recoverable source file.", encoding="utf-8")
            (project / "WORK_STATE.md").write_text("Continue from this point.", encoding="utf-8")
            (project / ".env").write_text("PRIVATE_VALUE=do-not-export", encoding="utf-8")
            (project / "__pycache__").mkdir()
            (project / "__pycache__" / "cached.pyc").write_bytes(b"runtime")
            old_snapshots = project / ".restore-points"
            old_snapshots.mkdir()
            (old_snapshots / "older.zip").write_bytes(b"do-not-nest-archives")
            data = project / "data"
            data.mkdir()
            database = data / "business-hub.sqlite3"

            # Keeping this connection open leaves committed data in the WAL,
            # so copying the database file alone would miss the latest state.
            with closing(sqlite3.connect(database)) as live_connection:
                live_connection.execute("PRAGMA journal_mode = WAL")
                live_connection.execute("CREATE TABLE examples (name TEXT)")
                live_connection.execute("INSERT INTO examples VALUES (?)", ("A saved enquiry",))
                live_connection.commit()
                self.assertTrue(Path(str(database) + "-wal").exists())

                with patch.object(checkpoint, "PROJECT_ROOT", project):
                    with redirect_stdout(io.StringIO()):
                        archive_path = checkpoint.create_checkpoint("verified restore")
                with zipfile.ZipFile(archive_path) as archive:
                    names = set(archive.namelist())
                    self.assertIn("README.md", names)
                    self.assertIn("WORK_STATE.md", names)
                    self.assertIn("RESTORE_NOTE.txt", names)
                    self.assertIn("data/business-hub.sqlite3", names)
                    self.assertNotIn(".env", names)
                    self.assertFalse(any("__pycache__" in name for name in names))
                    self.assertFalse(any(".restore-points" in name for name in names))
                    self.assertFalse(any(name.endswith(("-wal", "-shm")) for name in names))
                    restored = Path(directory) / "restored"
                    archive.extractall(restored)

                with closing(sqlite3.connect(restored / "data" / "business-hub.sqlite3")) as restored_connection:
                    result = restored_connection.execute("SELECT name FROM examples").fetchall()
                    self.assertEqual(result, [("A saved enquiry",)])
                    self.assertEqual(restored_connection.execute("PRAGMA integrity_check").fetchone()[0], "ok")


if __name__ == "__main__":
    unittest.main()
