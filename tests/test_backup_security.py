import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
import warnings
from zipfile import ZipFile

import backup


class BackupSecurityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.archive = self.root / "backup.zip"
        self.dest = self.root / "restore"

    def make_backup(self, extra=None, checksum=None, duplicate=False):
        members = {"control.db": b"malformed SQLite!"}
        if extra:
            members[extra] = b"abc"
        hashes = {name: hashlib.sha256(data).hexdigest() for name, data in members.items()}
        if checksum:
            hashes["control.db"] = checksum
        with warnings.catch_warnings(), ZipFile(self.archive, "w") as z:
            warnings.simplefilter("ignore", UserWarning)
            for name, data in members.items():
                z.writestr(name, data)
            if duplicate:
                z.writestr("control.db", members["control.db"])
            z.writestr("manifest.json", json.dumps({"format": 1, "sha256": hashes}))

    def test_restore_rejects_duplicate_and_unsafe_paths_before_writing(self):
        for kwargs in ({"duplicate": True}, {"extra": "evidence-files/../escape"}, {"extra": "evidence-files/../control.db"}):
            self.make_backup(**kwargs)
            with self.assertRaises(ValueError):
                backup.restore(self.archive, self.dest)
            self.assertFalse(self.dest.exists())

    def test_restore_byte_limit_applies_before_writing(self):
        self.make_backup()
        with self.assertRaisesRegex(ValueError, "oversized"):
            backup.restore(self.archive, self.dest, max_bytes=10)
        self.assertFalse(self.dest.exists())

    def test_incomplete_restore_removed(self):
        self.make_backup(checksum="0" * 64)
        with self.assertRaisesRegex(ValueError, "checksum mismatch"):
            backup.restore(self.archive, self.dest)
        self.assertFalse(self.dest.exists())
        self.make_backup()
        with self.assertRaises(sqlite3.DatabaseError):
            backup.restore(self.archive, self.dest)
        self.assertFalse(self.dest.exists())

    def test_backup_race_preserves_existing_destination(self):
        db_path = self.root / "db"
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE test(a)")
        conn.close()

        def collision(source, target):
            target.write_bytes(b"other backup")
            raise FileExistsError

        with patch("backup.os.link", side_effect=collision), self.assertRaises(FileExistsError):
            backup.backup(db_path, self.root / "evidence", self.archive)
        self.assertEqual(self.archive.read_bytes(), b"other backup")
