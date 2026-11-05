"""Transactional execution receipts and immutable evidence-version references.

No source-system query runs here. External MCP orchestration owns collection.
"""
import hashlib
import json
import re
from datetime import datetime, timezone


class Conflict(ValueError):
    """An idempotency key was reused with a different request."""


def setup(db):
    db.executescript("""
      CREATE TABLE IF NOT EXISTS execution_receipts (
        request_key TEXT PRIMARY KEY, payload_hash TEXT NOT NULL,
        execution_id INTEGER NOT NULL REFERENCES executions(id), created_at TEXT NOT NULL);
      CREATE TABLE IF NOT EXISTS execution_snapshots (
        execution_id INTEGER PRIMARY KEY REFERENCES executions(id),
        definition_json TEXT NOT NULL, provenance_json TEXT NOT NULL);
      CREATE TABLE IF NOT EXISTS execution_evidence_versions (
        execution_id INTEGER NOT NULL REFERENCES executions(id),
        evidence_id INTEGER NOT NULL REFERENCES evidence(id),
        version INTEGER, sha256 TEXT, file_name TEXT,
        PRIMARY KEY(execution_id,evidence_id));
    """)


def record(db, data, create):
    import app
    import grc_plus
    key=data.get("idempotency_key")
    if key is not None and (not isinstance(key,str) or not re.fullmatch(r"[A-Za-z0-9_.:-]{8,160}",key)):
        raise ValueError("idempotency_key 8–160 güvenli karakter olmalı")
    canonical=json.dumps(data,ensure_ascii=False,sort_keys=True,separators=(",",":"))
    digest=hashlib.sha256(canonical.encode()).hexdigest()
    # Serialize duplicate requests before reading the receipt; a retry never creates a second finding.
    if not db.in_transaction:
        db.execute("BEGIN IMMEDIATE")
    if key:
        receipt=db.execute("SELECT * FROM execution_receipts WHERE request_key=?",(key,)).fetchone()
        if receipt:
            if receipt["payload_hash"]!=digest:
                raise Conflict("Bu işlem anahtarı farklı bir sonuç için zaten kullanılmış")
            finding=db.execute("SELECT id FROM findings WHERE execution_id=?",(receipt["execution_id"],)).fetchone()
            return {"execution_id":receipt["execution_id"],"finding_id":finding["id"] if finding else None,"replayed":True}
    cid=data.get("control_id")
    control=app.context(db,cid) if type(cid)is int else None
    if not control or not control["active"]:
        raise ValueError("Aktif ve geçerli kontrol gerekli")
    status=data.get("status")
    if status not in app.ALLOWED_STATUS:
        raise ValueError("Geçersiz kontrol sonucu")
    provenance=data.get("provenance",{})
    if not isinstance(provenance,dict) or len(json.dumps(provenance))>32768:
        raise ValueError("provenance en fazla 32 KB JSON nesnesi olmalı")
    collection=provenance.get("collection_status")
    if collection is not None and collection not in ("complete","partial","error"):
        raise ValueError("collection_status complete, partial veya error olmalı")
    if collection in ("partial","error") and status!="inconclusive":
        raise ValueError("Eksik veya hatalı veri toplama yalnızca belirsiz sonuç olarak kaydedilebilir")
    if data.get("executed_at"):
        try:
            stamp=datetime.fromisoformat(data["executed_at"].replace("Z","+00:00"))
            if stamp.tzinfo is None or stamp.timestamp()>datetime.now(timezone.utc).timestamp()+300:
                raise ValueError
        except (ValueError,TypeError,AttributeError,OverflowError):
            raise ValueError("Kontrol zamanı saat dilimli ISO 8601 olmalı ve gelecekte olmamalı")
    ids=data.get("evidence_ids",[])
    versions=data.get("evidence_versions",{})
    if not isinstance(ids,list) or any(type(i)is not int or i<=0 for i in ids):
        raise ValueError("evidence_ids pozitif tam sayı listesi olmalı")
    if not isinstance(versions,dict) or set(versions)-{str(i) for i in ids}:
        raise ValueError("Sürüm seçimi yalnızca bağlı kanıtları içerebilir")
    snapshots=[]
    for eid in sorted(set(ids)):
        ev=db.execute("SELECT * FROM evidence WHERE id=?",(eid,)).fetchone()
        if not ev:
            raise ValueError("Kanıt bulunamadı")
        version=versions.get(str(eid))
        if version is not None and (type(version)is not int or version<1):
            raise ValueError("Kanıt sürümü pozitif tam sayı olmalı")
        if ev["hash_sha256"]:
            if version is None:
                row=db.execute("SELECT MAX(version) AS n FROM evidence_files WHERE evidence_id=?",(eid,)).fetchone()
                version=row["n"] or 1
            file=grc_plus.fetch_file(db,eid,version)
            if not file:
                raise ValueError("Seçilen kanıt dosyası veya sürümü bulunamadı")
            raw,name,_=file
            snapshots.append((eid,version,hashlib.sha256(raw).hexdigest(),name))
        elif version is not None:
            raise ValueError("Dosyasız kanıtta sürüm seçilemez")
        else:
            snapshots.append((eid,None,None,None))
    result=create(db,data)
    run=result["execution_id"]
    db.execute("INSERT INTO execution_snapshots VALUES(?,?,?)",(run,
        json.dumps(control,ensure_ascii=False),json.dumps(provenance,ensure_ascii=False)))
    db.executemany("INSERT INTO execution_evidence_versions VALUES(?,?,?,?,?)",[(run,*x) for x in snapshots])
    if key:
        db.execute("INSERT INTO execution_receipts VALUES(?,?,?,?)",(key,digest,run,app.utcnow()))
    return result


def enrich(db,result):
    if not result:
        return result
    row=db.execute("SELECT * FROM execution_snapshots WHERE execution_id=?",(result["id"],)).fetchone()
    # Never invent historical snapshots for runs created before this migration.
    result["definition_snapshot"]=json.loads(row["definition_json"]) if row else None
    result["provenance"]=json.loads(row["provenance_json"]) if row else None
    result["evidence_versions"]=[dict(x) for x in db.execute(
        "SELECT evidence_id,version,sha256,file_name FROM execution_evidence_versions WHERE execution_id=?",(result["id"],))]
    result["snapshot_available"]=bool(row)
    return result
