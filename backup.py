"""Private, coherent SQLite + evidence backup and non-destructive restore.

Run inside the Control GRC container. No NILES files or services are accessed.
"""
import argparse
import hashlib
import json
import os
import re
import shutil
from pathlib import Path
import sqlite3
import tempfile
from datetime import datetime, timezone
from zipfile import ZipFile, ZIP_DEFLATED


# Operated restores accept large databases without reading whole members into RAM.
DEFAULT_RESTORE_LIMIT = 16 * 1024 ** 3
MAX_MEMBERS = 50_000
MAX_MANIFEST = 8 * 1024 ** 2


def copy_hashed(reader, writer, limit):
    digest = hashlib.sha256()
    count = 0
    while chunk := reader.read(1024 * 1024):
        count += len(chunk)
        if count > limit:
            raise ValueError("Backup member exceeds size limit")
        digest.update(chunk)
        writer.write(chunk)
    return digest.hexdigest()


def backup(db_path, evidence_dir, destination):
    source, evidence, target = Path(db_path), Path(evidence_dir), Path(destination)
    if not source.is_file() or os.path.lexists(target):
        raise ValueError("Source DB must exist; backup destination must be new")
    target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    lock = sqlite3.connect(source, timeout=30)
    try:
        lock.execute("BEGIN IMMEDIATE")
        # Keep private temporary files on persistent storage; /tmp is size-limited.
        with tempfile.TemporaryDirectory(dir=target.parent) as temp:
            snapshot = Path(temp) / "control.db"
            reader, copied = sqlite3.connect(source), sqlite3.connect(snapshot)
            try:
                reader.backup(copied)
            finally:
                reader.close()
                copied.close()
            entries = [("control.db", snapshot)]
            if evidence.exists():
                for path in sorted(evidence.iterdir()):
                    if path.is_symlink() or not path.is_file():
                        raise ValueError("Unexpected entry in evidence directory")
                    entries.append(("evidence-files/" + path.name, path))
            manifest = {"created_at": datetime.now(timezone.utc).isoformat(), "format": 1, "sha256": {}}
            private_zip = Path(temp) / "snapshot.zip"
            with ZipFile(private_zip, "x", ZIP_DEFLATED) as archive:
                for name, path in entries:
                    with path.open("rb") as inp, archive.open(name, "w", force_zip64=True) as out:
                        manifest["sha256"][name] = copy_hashed(inp, out, path.stat().st_size)
                archive.writestr("manifest.json", json.dumps(manifest, indent=2))
            private_zip.chmod(0o600)
            os.link(private_zip, target)  # Atomic publication; a competing file is preserved.
        return {"backup": str(target), "files": len(entries)}
    finally:
        lock.rollback()
        lock.close()


def restore(archive_path, destination, max_bytes=DEFAULT_RESTORE_LIMIT):
    dest = Path(destination)
    if max_bytes < 1 or os.path.lexists(dest):
        raise ValueError("Restore requires a positive limit and a new destination")
    with ZipFile(archive_path) as archive:
        infos = archive.infolist()
        files = {i.filename: i for i in infos}
        if (len(files) != len(infos) or len(infos) > MAX_MEMBERS or
                sum(i.file_size for i in infos) > max_bytes or
                "manifest.json" not in files or files["manifest.json"].file_size > MAX_MANIFEST):
            raise ValueError("Duplicate, missing or oversized backup members")
        manifest = json.loads(archive.read("manifest.json"))
        names = manifest.get("sha256") if isinstance(manifest, dict) and manifest.get("format") == 1 else None
        if not isinstance(names, dict) or set(files) != set(names) | {"manifest.json"} or "control.db" not in names:
            raise ValueError("Unexpected backup contents")
        for name, digest in names.items():
            if name != "control.db" and not re.fullmatch(r"evidence-files/[A-Za-z0-9][A-Za-z0-9._-]{0,254}", name):
                raise ValueError("Unsafe backup path")
            if not isinstance(digest, str) or not re.fullmatch(r"[a-f0-9]{64}", digest):
                raise ValueError("Invalid backup checksum")
        dest.mkdir(parents=True, mode=0o700)
        try:
            for name, expected in names.items():
                path = dest / name
                path.parent.mkdir(exist_ok=True, mode=0o700)
                with archive.open(name) as inp, path.open("xb") as out:
                    digest = copy_hashed(inp, out, files[name].file_size)
                path.chmod(0o600)
                if digest != expected:
                    raise ValueError("Backup checksum mismatch")
            db = sqlite3.connect((dest / "control.db").resolve().as_uri() + "?mode=ro", uri=True)
            try:
                db.execute("PRAGMA trusted_schema=OFF")
                if (db.execute("PRAGMA integrity_check(1)").fetchone()[0] != "ok"
                        or db.execute("PRAGMA foreign_key_check").fetchone()
                        or db.execute("SELECT count(*) FROM sqlite_master WHERE type='table' "
                                      "AND name IN ('audits','controls','evidence')").fetchone()[0] != 3):
                    raise ValueError("Restored GRC database validation failed")
            finally:
                db.close()
        except Exception:
            shutil.rmtree(dest)
            raise
    return {"restored_to": str(dest), "files": len(names)}


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--restore');parser.add_argument('--destination')
    parser.add_argument('--max-restore-bytes', type=int, default=DEFAULT_RESTORE_LIMIT)
    args=parser.parse_args()
    if args.restore:
        if not args.destination:parser.error('--destination is required for restore')
        result=restore(args.restore,args.destination,args.max_restore_bytes)
    else:
        db=os.environ.get('CONTROL_DB','control.db')
        evidence=os.environ.get('CONTROL_EVIDENCE_DIR',str(Path(db).parent/'evidence-files'))
        timestamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        target=args.destination or str(Path(db).parent/'backups'/f'control-{timestamp}.zip')
        result=backup(db,evidence,target)
    print(json.dumps(result))
