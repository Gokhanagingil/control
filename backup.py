"""Private, coherent SQLite + evidence backup and non-destructive restore.

Run inside the Control GRC container. No NILES files or services are accessed.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import tempfile
from datetime import datetime, timezone
from zipfile import ZipFile, ZIP_DEFLATED


def backup(db_path, evidence_dir, destination):
    source=Path(db_path).resolve();evidence=Path(evidence_dir).resolve();target=Path(destination).resolve()
    if not source.is_file() or target.exists():
        raise ValueError('Source DB must exist; backup destination must be new')
    target.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    lock=sqlite3.connect(source,timeout=30)
    try:
        lock.execute('BEGIN IMMEDIATE')
        with tempfile.TemporaryDirectory() as temp:
            snapshot=Path(temp)/'control.db'
            reader=sqlite3.connect(source)
            copied=sqlite3.connect(snapshot)
            try:reader.backup(copied)
            finally:reader.close();copied.close()
            entries=[('control.db',snapshot)]
            if evidence.exists():
                for path in sorted(evidence.iterdir()):
                    if path.is_symlink() or not path.is_file():
                        raise ValueError('Unexpected entry in evidence directory')
                    entries.append(('evidence-files/'+path.name,path))
            manifest={'created_at':datetime.now(timezone.utc).isoformat(),'format':1,'sha256':{}}
            with target.open('xb') as stream:
                os.chmod(target,0o600)
                with ZipFile(stream,'w',ZIP_DEFLATED) as archive:
                    for name,path in entries:
                        manifest['sha256'][name]=hashlib.sha256(path.read_bytes()).hexdigest()
                        archive.write(path,name)
                    archive.writestr('manifest.json',json.dumps(manifest,indent=2))
        return {'backup':str(target),'files':len(entries)}
    except Exception:
        target.unlink(missing_ok=True)
        raise
    finally:
        lock.rollback();lock.close()


def restore(archive_path,destination):
    dest=Path(destination)
    if dest.exists():raise ValueError('Restore destination must not exist; in-place overwrite is refused')
    with ZipFile(archive_path) as archive:
        manifest=json.loads(archive.read('manifest.json'))
        names=manifest['sha256']
        if set(archive.namelist())!=set(names)|{'manifest.json'} or 'control.db' not in names:
            raise ValueError('Unexpected backup contents')
        for name in names:
            if name!='control.db' and not (name.startswith('evidence-files/') and len(Path(name).parts)==2 and '..' not in Path(name).parts):
                raise ValueError('Unsafe backup path')
            if hashlib.sha256(archive.read(name)).hexdigest()!=names[name]:
                raise ValueError('Backup checksum mismatch')
        dest.mkdir(parents=True,mode=0o700)
        for name in names:
            path=dest/name;path.parent.mkdir(exist_ok=True,mode=0o700)
            path.write_bytes(archive.read(name));path.chmod(0o600)
    db=sqlite3.connect(dest/'control.db')
    try:
        if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok' or db.execute('PRAGMA foreign_key_check').fetchone():
            raise ValueError('Restored database validation failed')
    finally:db.close()
    return {'restored_to':str(dest),'files':len(names)}


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--restore');parser.add_argument('--destination')
    args=parser.parse_args()
    if args.restore:
        if not args.destination:parser.error('--destination is required for restore')
        result=restore(args.restore,args.destination)
    else:
        db=os.environ.get('CONTROL_DB','control.db')
        evidence=os.environ.get('CONTROL_EVIDENCE_DIR',str(Path(db).parent/'evidence-files'))
        timestamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        target=args.destination or str(Path(db).parent/'backups'/f'control-{timestamp}.zip')
        result=backup(db,evidence,target)
    print(json.dumps(result))
