"""KS GRC extensions: audit evidence, risks, actions, governance and compliance analytics.

Kept separate from the legacy prototype router for migration safety.
"""
import base64
import binascii
import hashlib
import io
import json
import mimetypes
import risk_management
import os
from pathlib import Path
import re
import sqlite3
import threading
from datetime import date, datetime, timezone
from urllib.parse import parse_qs, urlparse
from zipfile import ZipFile, BadZipFile

SCHEMA = {
    "risks": {
        "code": "TEXT NOT NULL", "title": "TEXT NOT NULL",
        "description": "TEXT", "category": "TEXT NOT NULL DEFAULT 'operational'",
        "likelihood": "INTEGER NOT NULL DEFAULT 3", "impact": "INTEGER NOT NULL DEFAULT 3",
        "owner": "TEXT", "status": "TEXT NOT NULL DEFAULT 'open'",
        "treatment": "TEXT", "due_date": "TEXT", "created_at": "TEXT NOT NULL"
    },
    "actions": {
        "code": "TEXT NOT NULL", "title": "TEXT NOT NULL",
        "finding_id": "INTEGER REFERENCES findings(id)",
        "control_id": "INTEGER REFERENCES controls(id)",
        "description": "TEXT", "owner": "TEXT", "due_date": "TEXT",
        "priority": "TEXT NOT NULL DEFAULT 'medium'",
        "status": "TEXT NOT NULL DEFAULT 'open'",
        "resolution": "TEXT", "closed_at": "TEXT", "created_at": "TEXT NOT NULL"
    },
    "documents": {
        "code": "TEXT NOT NULL", "title": "TEXT NOT NULL",
        "category": "TEXT NOT NULL DEFAULT 'instruction'",
        "version": "TEXT", "owner": "TEXT",
        "status": "TEXT NOT NULL DEFAULT 'active'",
        "reference_url": "TEXT", "description": "TEXT",
        "created_at": "TEXT NOT NULL"
    }
}
NEW_LABELS = {"risks": "Riskler", "actions": "Düzeltici Faaliyetler", "documents": "Dokümanlar"}
CHOICES = {
    "controls": {
        "execution_mode": {"manual":"Manuel","automatic":"Otomatik"},
        "nature": {"preventive":"Önleyici","detective":"Tespit edici","corrective":"Düzeltici",
                   "directive":"Yönlendirici","compensating":"Telafi edici"},
        "frequency": {"on_demand":"İhtiyaca göre","continuous":"Sürekli","daily":"Günlük",
                      "weekly":"Haftalık","monthly":"Aylık","quarterly":"Üç aylık",
                      "semiannual":"Altı aylık","yearly":"Yıllık"},
        "active": {"1":"Aktif","0":"Pasif"},
        "criticality": {"low":"Düşük","medium":"Orta","high":"Yüksek","critical":"Kritik"},
        "method_type": {"query":"MCP sorgusu","sampling":"Örnekleme","inspection":"İnceleme",
                        "interview":"Görüşme","observation":"Gözlem"}
    },
    "audits": {"status":{"planned":"Planlandı","in_progress":"Devam ediyor",
                         "completed":"Tamamlandı","closed":"Kapalı","cancelled":"İptal"}},
    "executions": {"status":{"pass":"Başarılı","fail":"Başarısız",
                             "inconclusive":"Belirsiz","not_applicable":"Uygulanamaz"},
                   "source":{"manual":"Manuel","mcp":"MCP","demo_seed":"Örnek veri"}},
    "findings": {"severity":{"low":"Düşük","medium":"Orta","high":"Yüksek","critical":"Kritik"},
                 "status":{"open":"Açık","in_progress":"Üzerinde çalışılıyor",
                           "closed":"Kapalı","accepted":"Risk kabul edildi"}},
    "evidence": {"source":{"manual":"Manuel","mcp":"MCP","demo_seed":"Örnek veri","system":"Sistem"},
                 "confidentiality":{"internal":"Kurum içi","confidential":"Gizli","restricted":"Kısıtlı"},
                 "status":{"current":"Güncel","expired":"Süresi dolmuş","archived":"Arşiv"}},
    "risks": {"category":{"operational":"Operasyonel","compliance":"Uyum","security":"Bilgi güvenliği",
                          "continuity":"İş sürekliliği","financial":"Finansal","supplier":"Tedarikçi",
                          "privacy":"Kişisel veri"},
              "status":{"open":"Açık","in_treatment":"Aksiyon alınıyor",
                        "accepted":"Kabul edildi","closed":"Kapalı"}},
    "actions": {"priority":{"low":"Düşük","medium":"Orta","high":"Yüksek","critical":"Kritik"},
                "status":{"open":"Açık","in_progress":"Üzerinde çalışılıyor",
                          "validation":"Etkinlik doğrulaması","completed":"Tamamlandı","cancelled":"İptal"}},
    "documents": {"category":{"policy":"Politika","procedure":"Prosedür",
                               "instruction":"Talimat","standard":"İç standart","guideline":"Rehber"},
                  "status":{"draft":"Taslak","active":"Yürürlükte","retired":"Yürürlükten kaldırıldı"}}
}
# All labels exposed to the browser and XLSX exports are in Turkish.
FIELD_LABELS = {
    "id":"Kayıt No", "code":"Kod", "name":"Ad", "title":"Başlık",
    "description":"Açıklama", "version":"Sürüm", "standard_id":"Standart",
    "parent_id":"Üst madde", "owner":"Sorumlu", "created_at":"Oluşturulma",
    "updated_at":"Güncellenme", "auditors":"Denetçiler", "auditees":"Denetlenenler",
    "audit_objective":"Denetim amacı","conclusion":"Denetim sonucu","revision":"Kayıt sürümü",
    "scope":"Kapsam", "planned_start":"Planlanan başlangıç","planned_end":"Planlanan bitiş",
    "actual_start":"Gerçekleşen başlangıç","actual_end":"Gerçekleşen bitiş",
    "status":"Durum","execution_mode":"Uygulama şekli","nature":"Kontrol yaklaşımı",
    "frequency":"Sıklık","method":"Kontrol yöntemi","expected_result":"Beklenen sonuç",
    "active":"Aktif","audit_id":"Denetim","control_id":"Kontrol",
    "executed_at":"Kontrol zamanı","source":"Kaynak","details":"Test sonucu",
    "severity":"Önem","reference_url":"Referans bağlantısı",
    "collected_at":"Toplanma tarihi","hash_sha256":"SHA-256","file_name":"Dosya adı",
    "file_size":"Dosya boyutu (bayt)","mime_type":"İçerik türü",
    "confidentiality":"Gizlilik","period_start":"Kanıt dönem başlangıcı",
    "period_end":"Kanıt dönem bitişi","expires_at":"Kanıt geçerlilik sonu",
    "category":"Kategori", "likelihood":"Olasılık (1–5)","impact":"Etki (1–5)",
    "treatment":"Risk işleme","due_date":"Hedef tarih","priority":"Öncelik",
    "resolution":"Çözüm açıklaması","closed_at":"Kapanış zamanı",
    "criticality":"Kritiklik","method_type":"Kontrol test yöntemi",
}
SCHEMA["risk_catalog"]=risk_management.CATALOG_FIELDS
SCHEMA["risks"].update(risk_management.REGISTER_FIELDS)
SCHEMA["actions"]["risk_id"]="INTEGER REFERENCES risks(id)"
NEW_LABELS["risk_catalog"]="Risk Kataloğu"
CHOICES["risk_catalog"]={"category":CHOICES["risks"]["category"]}
CHOICES["risks"]["response_strategy"]=risk_management.STRATEGIES
FIELD_LABELS.update({"inherent_score":"İçsel risk","residual_score":"Son artık risk","catalog_id":"Katalog şablonu","entity_name":"Etkilenen varlık / hizmet","cause":"Neden",
    "risk_event":"Risk olayı","consequence":"İş etkisi","review_date":"Gözden geçirme tarihi",
    "response_strategy":"Yanıt stratejisi","appetite":"Risk iştahı eşiği (1–25)","risk_id":"İlgili risk"})
EVIDENCE_EXT = {".pdf",".png",".jpg",".jpeg",".webp",".tif",".tiff",".txt",".csv",".json",".jsonl",".log",
                ".xlsx",".docx",".pptx",".zip",".eml",".msg",".xml",".md"}
FILE_METADATA = {"hash_sha256","file_size","file_name","mime_type"}
MAX_FILE = 20 * 1024 * 1024
MAX_BODY = 29 * 1024 * 1024
SAFE_NAME = re.compile(r"^[^/\\\x00-\x1f]{1,160}$")
API_LIMIT = 5000
SCHEMA_VERSION = 4


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def setup(db):
    for name, fields in SCHEMA.items():
        columns = ", ".join(f"{key} {val}" for key,val in fields.items())
        db.execute(f"CREATE TABLE IF NOT EXISTS {name} (id INTEGER PRIMARY KEY AUTOINCREMENT, {columns})")
    migrations = {
        "risks":risk_management.REGISTER_FIELDS, "actions":{"risk_id":"INTEGER REFERENCES risks(id)"},
        "audits":{"audit_objective":"TEXT","conclusion":"TEXT","revision":"INTEGER NOT NULL DEFAULT 0"},
        "controls":{"criticality":"TEXT NOT NULL DEFAULT 'medium'",
                    "method_type":"TEXT NOT NULL DEFAULT 'query'"},
        "evidence":{"file_name":"TEXT","file_size":"INTEGER","mime_type":"TEXT",
                    "confidentiality":"TEXT NOT NULL DEFAULT 'internal'",
                    "status":"TEXT NOT NULL DEFAULT 'current'",
                    "period_start":"TEXT","period_end":"TEXT","expires_at":"TEXT"},
    }
    for table, fields in migrations.items():
        present = {row["name"] for row in db.execute(f"PRAGMA table_info({table})")}
        for col, definition in fields.items():
            if col not in present:
                db.execute(f"ALTER TABLE {table} ADD COLUMN {col} {definition}")
    # Save latest choices into the common table model for existing CRUD routes.
    import app
    app.TABLES["audits"].update({"audit_objective":"TEXT","conclusion":"TEXT"})
    app.TABLES["controls"].update(migrations["controls"])
    app.TABLES["evidence"].update(migrations["evidence"])
    app.PATCHABLE["controls"].update(migrations["controls"])
    app.PATCHABLE["evidence"].update(
        {"title","description","reference_url","confidentiality","status",
         "period_start","period_end","expires_at"})
    app.PATCHABLE["findings"].update({"status","severity"})
    app.ALLOWED_STATUS.update(CHOICES["executions"]["status"])
    app.ALLOWED_NATURE.update(CHOICES["controls"]["nature"])
    for name, fields in SCHEMA.items():
        app.TABLES[name] = fields
        app.LABELS[name] = NEW_LABELS[name]
        app.PATCHABLE[name] = set(fields) - {"created_at"}
    db.execute("""CREATE TABLE IF NOT EXISTS evidence_audits (
        evidence_id INTEGER NOT NULL REFERENCES evidence(id) ON DELETE CASCADE,
        audit_id INTEGER NOT NULL REFERENCES audits(id) ON DELETE CASCADE,
        PRIMARY KEY(evidence_id,audit_id))""")
    db.execute("""CREATE TABLE IF NOT EXISTS evidence_controls (
        evidence_id INTEGER NOT NULL REFERENCES evidence(id) ON DELETE CASCADE,
        control_id INTEGER NOT NULL REFERENCES controls(id) ON DELETE CASCADE,
        PRIMARY KEY(evidence_id,control_id))""")
    db.execute("""CREATE TABLE IF NOT EXISTS control_risks (
        control_id INTEGER NOT NULL REFERENCES controls(id) ON DELETE CASCADE,
        risk_id INTEGER NOT NULL REFERENCES risks(id) ON DELETE CASCADE,
        PRIMARY KEY(control_id,risk_id))""")
    db.execute("""CREATE TABLE IF NOT EXISTS document_controls (
        document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
        control_id INTEGER NOT NULL REFERENCES controls(id) ON DELETE CASCADE,
        PRIMARY KEY(document_id,control_id))""")
    db.execute("""CREATE TABLE IF NOT EXISTS evidence_files (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        evidence_id INTEGER NOT NULL REFERENCES evidence(id) ON DELETE CASCADE,
        version INTEGER NOT NULL, storage_key TEXT NOT NULL UNIQUE,
        file_name TEXT NOT NULL, file_size INTEGER NOT NULL,
        mime_type TEXT NOT NULL, sha256 TEXT NOT NULL,
        created_at TEXT NOT NULL, UNIQUE(evidence_id,version))""")
    db.execute("""CREATE TABLE IF NOT EXISTS activity_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        actor TEXT NOT NULL, method TEXT NOT NULL, object_type TEXT NOT NULL,
        object_id TEXT, description TEXT, occurred_at TEXT NOT NULL)""")
    db.execute("CREATE INDEX IF NOT EXISTS activity_log_time ON activity_log(occurred_at)")
    db.execute("CREATE INDEX IF NOT EXISTS executions_control_date ON executions(control_id,executed_at DESC,id DESC)")
    db.execute("CREATE INDEX IF NOT EXISTS executions_audit ON executions(audit_id)")
    db.execute("CREATE INDEX IF NOT EXISTS evidence_files_eid ON evidence_files(evidence_id,version)")
    db.execute("CREATE INDEX IF NOT EXISTS evidence_audits_audit ON evidence_audits(audit_id)")
    db.execute("CREATE INDEX IF NOT EXISTS actions_finding ON actions(finding_id)")
    db.execute("""CREATE TABLE IF NOT EXISTS audit_standards (
        audit_id INTEGER NOT NULL REFERENCES audits(id) ON DELETE CASCADE,
        standard_id INTEGER NOT NULL REFERENCES standards(id), PRIMARY KEY (audit_id,standard_id))""")
    # Existing explicit clauses are the only reliable basis for migrating the old scope.
    db.execute("""INSERT OR IGNORE INTO audit_standards
        SELECT DISTINCT ac.audit_id,cl.standard_id FROM audit_clauses ac JOIN clauses cl ON cl.id=ac.clause_id""")
    db.execute("""CREATE TRIGGER IF NOT EXISTS audit_clause_parent AFTER INSERT ON audit_clauses
        BEGIN INSERT OR IGNORE INTO audit_standards(audit_id,standard_id)
            SELECT NEW.audit_id,standard_id FROM clauses WHERE id=NEW.clause_id; END""")
    db.execute("""CREATE TABLE IF NOT EXISTS audit_plan_snapshots (
        audit_id INTEGER PRIMARY KEY REFERENCES audits(id) ON DELETE CASCADE, captured_at TEXT NOT NULL)""")
    db.execute("""CREATE TABLE IF NOT EXISTS audit_plan_links (
        audit_id INTEGER NOT NULL REFERENCES audit_plan_snapshots(audit_id) ON DELETE CASCADE,
        clause_id INTEGER NOT NULL REFERENCES clauses(id), control_id INTEGER NOT NULL REFERENCES controls(id),
        PRIMARY KEY(audit_id,clause_id,control_id))""")
    db.execute("""CREATE VIEW IF NOT EXISTS audit_planned_mappings AS
        SELECT * FROM audit_plan_links UNION ALL
        SELECT ac.audit_id,ac.clause_id,cc.control_id FROM audit_clauses ac
        JOIN control_clauses cc ON cc.clause_id=ac.clause_id
        JOIN controls c ON c.id=cc.control_id AND c.active=1
        WHERE NOT EXISTS (SELECT 1 FROM audit_plan_snapshots s WHERE s.audit_id=ac.audit_id)""")
    risk_management.setup(db)
    db.execute("PRAGMA user_version=4")


def log(db, handler, method, table, rid=None, description=""):
    user = getattr(handler, "current_user", None)
    actor = user.get("username", "mcp") if user else "mcp"
    db.execute("INSERT INTO activity_log(actor,method,object_type,object_id,description,occurred_at) VALUES (?,?,?,?,?,?)",
        (actor, method, table, str(rid) if rid else None, str(description)[:600], now()))


def rows(db, query, args=()):
    return [dict(row) for row in db.execute(query, args)]


def json_body(handler, max_size=1024*1024):
    length = int(handler.headers.get("Content-Length", "0"))
    if length <= 0 or length > max_size:
        raise ValueError("İstek boyutu izin verilen aralık dışında")
    if "application/json" not in handler.headers.get("Content-Type","").lower():
        raise ValueError("JSON içerik türü gerekli")
    payload = json.loads(handler.rfile.read(length))
    if not isinstance(payload,dict):
        raise ValueError("JSON nesnesi gerekli")
    return payload


def validate_choice(table, data):
    if not isinstance(data,dict):
        raise ValueError("Geçersiz kayıt")
    for field, allowed in CHOICES.get(table, {}).items():
        if field not in data or data[field] is None or data[field] == "":
            continue
        if str(data[field]) not in allowed:
            raise ValueError(f"{FIELD_LABELS.get(field,field)}: geçersiz seçim")


def validate_record(table, data):
    validate_choice(table,data)
    if table in ("risks","risk_catalog"):
        risk_management.validate(table,data)
        for field in ("likelihood","impact"):
            value = data.get(field, 3)
            if type(value) is not int or value not in range(1,6):
                raise ValueError("Olasılık ve etki 1–5 arasında olmalı")
    if table in ("risk_catalog","risks","actions","documents"):
        code = data.get("code","")
        if not isinstance(code,str) or not code.strip() or len(code)>90:
            raise ValueError("Geçerli kod gerekli")
        if not isinstance(data.get("title"),str) or not data["title"].strip():
            raise ValueError("Başlık gerekli")
    if table == "evidence":
        for key in ("period_start","period_end","expires_at"):
            val = data.get(key)
            if val and (not isinstance(val,str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}",val)):
                raise ValueError("Kanıt tarihleri YYYY-AA-GG biçiminde olmalı")


def extended_context(db, eid):
    import app
    item=app.evidence_context(db,eid)
    if not item:
        return None
    item["audits"] = rows(db, """SELECT a.* FROM audits a JOIN evidence_audits m ON a.id=m.audit_id
                             WHERE m.evidence_id=? ORDER BY a.id DESC""",(eid,))
    item["controls"] = rows(db, """SELECT c.id,c.code,c.name FROM controls c
       JOIN evidence_controls m ON c.id=m.control_id WHERE m.evidence_id=?""",(eid,))
    item["audit_history"] = rows(db, """SELECT DISTINCT a.id,a.name,x.executed_at,x.status,c.code AS control_code
           FROM executions x JOIN audits a ON a.id=x.audit_id
           JOIN controls c ON c.id=x.control_id
           JOIN execution_evidence m ON m.execution_id=x.id WHERE m.evidence_id=?
           ORDER BY x.executed_at DESC""",(eid,))
    item["files"] = rows(db, """SELECT id,version,file_name,file_size,mime_type,sha256,created_at
          FROM evidence_files WHERE evidence_id=? ORDER BY version DESC""",(eid,))
    # Prior evidence files (including existing seeded synthetic examples) stay accessible.
    if not item["files"] and item["hash_sha256"]:
        item["files"] = [{"id":None,"version":1,
          "file_name":item.get("file_name") or
                      (f"ornek-uretim-{eid}.json" if item.get("source")=="demo_seed" else f"kanit-{eid}.bin"),
          "file_size":item.get("file_size"),"mime_type":item.get("mime_type"),
          "sha256":item["hash_sha256"],"created_at":item.get("collected_at")}]
    return item


def mappings(db, eid, payload, replace=True):
    import app
    allowed={"clauses":"evidence_clauses","processes":"evidence_processes",
             "audits":"evidence_audits","controls":"evidence_controls"}
    for target, table in allowed.items():
        if target not in payload:
            continue
        if not isinstance(payload[target],list) or any(type(i) is not int or i < 1 for i in payload[target]):
            raise ValueError("Bağlantılar pozitif tam sayı listesi olmalı")
        fk = app.TARGET_COLUMNS[target] + "_id" if target in ("clauses","processes") else target[:-1] + "_id"
        # Exception: 'audits' -> 'audit_id' and 'controls' -> 'control_id'
        if replace:
            db.execute(f"DELETE FROM {table} WHERE evidence_id=?",(eid,))
        app.mapping(db, table, "evidence_id", eid, fk, payload[target])


def _valid_file(filename, binary):
    if not isinstance(filename,str) or not SAFE_NAME.fullmatch(filename) or filename in {".",".."}:
        raise ValueError("Geçersiz dosya adı")
    extension = Path(filename).suffix.lower()
    if extension not in EVIDENCE_EXT:
        raise ValueError("Dosya türüne izin verilmiyor. PDF, Office, resim, metin ve ZIP desteklenir")
    if not 0 < len(binary) <= MAX_FILE:
        raise ValueError("Dosya boyutu 1 bayt–20 MB arasında olmalı")
    if extension==".pdf" and not binary.startswith(b"%PDF-"):
        raise ValueError("PDF dosya imzası doğrulanamadı")
    if extension==".png" and not binary.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("PNG dosya imzası doğrulanamadı")
    if extension in (".jpg",".jpeg") and not binary.startswith(b"\xff\xd8\xff"):
        raise ValueError("JPEG dosya imzası doğrulanamadı")
    if extension==".webp" and (binary[:4]!=b"RIFF" or binary[8:12]!=b"WEBP"):
        raise ValueError("WebP dosya imzası doğrulanamadı")
    if extension in (".zip",".xlsx",".docx",".pptx"):
        try:
            with ZipFile(io.BytesIO(binary)) as z:
                if len(z.infolist()) > 1200 or sum(item.file_size for item in z.infolist()) > 120*1024*1024:
                    raise ValueError("Arşiv genişletilmiş boyut sınırını aşıyor")
                if any(item.compress_size and item.file_size/item.compress_size > 300 for item in z.infolist()):
                    raise ValueError("Şüpheli arşiv sıkıştırma oranı")
                if extension in (".xlsx",".docx",".pptx") and "[Content_Types].xml" not in z.namelist():
                    raise ValueError("Office dosyası geçersiz")
        except BadZipFile:
            raise ValueError("Office/ZIP dosyası imzası geçersiz")
    if extension in (".txt",".csv",".log",".json",".md",".xml",".eml"):
        if b"\x00" in binary[:2048]:
            raise ValueError("Metin dosyasının içeriği geçersiz")
    return extension


def _write_file(db, eid, filename, binary):
    import app
    ext=_valid_file(filename,binary)
    folder=Path(app.EVIDENCE_DIR)
    folder.mkdir(parents=True,exist_ok=True,mode=0o700)
    row=db.execute("SELECT COALESCE(MAX(version),0) AS version FROM evidence_files WHERE evidence_id=?",(eid,)).fetchone()
    version=(row["version"] or 0)+1
    # Legacy evidence file may exist outside the version index.
    legacy=folder/str(eid)
    if version==1 and legacy.exists():
        prior=db.execute("SELECT * FROM evidence WHERE id=?",(eid,)).fetchone()
        legacy_bytes=legacy.read_bytes()
        digest=hashlib.sha256(legacy_bytes).hexdigest()
        if not prior["hash_sha256"] or digest!=prior["hash_sha256"]:
            raise ValueError("Eski kanıtın bütünlük doğrulaması başarısız")
        db.execute("""INSERT INTO evidence_files
          (evidence_id,version,storage_key,file_name,file_size,mime_type,sha256,created_at)
          VALUES(?,?,?,?,?,?,?,?)""",(eid,1,str(eid),prior["file_name"] or f"kanit-{eid}.bin",
          len(legacy_bytes),prior["mime_type"] or "application/octet-stream",digest,
          prior["collected_at"] or now()))
        version=2
    name=f"{eid}-v{version}" if version>1 else str(eid)
    location=folder/name
    with location.open("xb") as f:
        f.write(binary)
    location.chmod(0o600)
    digest=hashlib.sha256(binary).hexdigest()
    mime=mimetypes.guess_type(filename)[0] or "application/octet-stream"
    db.execute("""INSERT INTO evidence_files
      (evidence_id,version,storage_key,file_name,file_size,mime_type,sha256,created_at)
      VALUES(?,?,?,?,?,?,?,?)""",(eid,version,name,filename,len(binary),mime,digest,now()))
    db.execute("""UPDATE evidence SET hash_sha256=?,file_name=?,file_size=?,mime_type=?
                  WHERE id=?""",(digest,filename,len(binary),mime,eid))
    return {"evidence_id":eid,"version":version,"size":len(binary),"sha256":digest,"file_name":filename}


def save_file(db,payload,eid=None):
    import app
    encoded=payload.get("content_base64")
    if not isinstance(encoded,str):
        raise ValueError("content_base64 gerekli")
    if len(encoded)>MAX_BODY:
        raise ValueError("Dosya çok büyük")
    try:
        binary=base64.b64decode(encoded,validate=True)
    except (ValueError,binascii.Error):
        raise ValueError("Geçersiz dosya kodlaması")
    filename=payload.get("file_name") or payload.get("filename") or "kanit.json"
    _valid_file(filename,binary)
    if eid is None:
        title=payload.get("title")
        if not isinstance(title,str) or not title.strip() or len(title)>250:
            raise ValueError("Kanıt başlığı gerekli")
        fields={k:payload.get(k) for k in (
            "title","description","reference_url","source","confidentiality",
            "status","period_start","period_end","expires_at") if payload.get(k) is not None}
        fields.setdefault("source","manual")
        validate_record("evidence",fields)
        eid=app.insert(db,"evidence",fields)
    elif not db.execute("SELECT id FROM evidence WHERE id=?",(eid,)).fetchone():
        raise ValueError("Kanıt kaydı bulunamadı")
    mappings(db,eid,payload,replace=False)
    details=_write_file(db,eid,filename,binary)
    return {"id":eid, **details}


def fetch_file(db,eid,version=None):
    import app
    record=db.execute("SELECT id,title,source,hash_sha256 FROM evidence WHERE id=?",(eid,)).fetchone()
    if not record:
        return None
    if version is not None and (type(version)is not int or version<=0):
        raise ValueError("Geçersiz kanıt sürümü")
    if version is None:
        file=db.execute("SELECT * FROM evidence_files WHERE evidence_id=? ORDER BY version DESC LIMIT 1",(eid,)).fetchone()
    else:
        file=db.execute("SELECT * FROM evidence_files WHERE evidence_id=? AND version=?",(eid,version)).fetchone()
    if file:
        filename=file["file_name"]
        location=Path(app.EVIDENCE_DIR)/file["storage_key"]
        expected=file["sha256"]
    else:
        if version not in (None,1) or not record["hash_sha256"]:
            return None
        filename=f"ornek-uretim-{eid}.json" if record["source"]=="demo_seed" else f"kanit-{eid}.bin"
        location=Path(app.EVIDENCE_DIR)/str(eid)
        expected=record["hash_sha256"]
    if not location.is_file():
        return None
    if location.stat().st_size>MAX_FILE:
        raise ValueError("İndirme boyutu sınırı aşılıyor")
    raw=location.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=expected:
        raise ValueError("Kanıt bütünlük doğrulaması başarısız")
    ext=Path(filename).suffix.lower()
    return raw,filename,ext


def compliance(db, query):
    """Snapshot based on latest eligible control execution.

    For a standard or process: any historical audit's latest control execution is
    a preliminary indication. For a specific audit: only runs from that audit count.
    Completion excludes inconclusive/not_applicable. No score means no evidence.
    """
    def filt(name):
        val=query.get(name,[""])[0]
        if not val:
            return None
        try:
            number=int(val)
            if number<=0:
                raise ValueError
            return number
        except ValueError:
            raise ValueError("Filtre kimliği pozitif sayı olmalı")
    standard=filt("standard_id")
    process=filt("process_id")
    audit=filt("audit_id")
    params={"audit":audit,"standard":standard,"process":process}
    # Match standard AND audit on the same clause. Two independent EXISTS clauses
    # would count a cross-mapped control even when the relevant clause is excluded.
    where = ["EXISTS (SELECT 1 FROM control_processes p WHERE p.control_id=c.id AND p.process_id=:process)"
             ] if process else []
    if audit:
        where.append("""EXISTS (SELECT 1 FROM audit_planned_mappings pm JOIN clauses cl ON cl.id=pm.clause_id
            WHERE pm.audit_id=:audit AND pm.control_id=c.id AND (:standard IS NULL OR cl.standard_id=:standard))""")
    else:
        where.append("c.active=1")
        if standard:
            where.append("""EXISTS (SELECT 1 FROM control_clauses cc JOIN clauses cl ON cl.id=cc.clause_id
                WHERE cc.control_id=c.id AND cl.standard_id=:standard)""")
    candidates=rows(db,"SELECT c.id,c.code,c.name,c.frequency FROM controls c WHERE "+" AND ".join(where)+" ORDER BY c.code",params)
    results=[]
    counts={"pass":0,"fail":0,"inconclusive":0,"not_applicable":0,"untested":0}
    for c in candidates:
        if audit:
            x=db.execute("""SELECT id,status,executed_at,audit_id FROM executions WHERE control_id=? AND audit_id=?
                    ORDER BY julianday(executed_at) DESC,id DESC LIMIT 1""",(c["id"],audit)).fetchone()
        else:
            x=db.execute("""SELECT id,status,executed_at,audit_id FROM executions WHERE control_id=?
                    ORDER BY julianday(executed_at) DESC,id DESC LIMIT 1""",(c["id"],)).fetchone()
        status=x["status"] if x else "untested"
        if status not in counts:
            status="inconclusive"
        counts[status]+=1
        results.append({**c,"status":status,"executed_at":x["executed_at"] if x else None,
                        "execution_id":x["id"] if x else None,
                        "audit_id":x["audit_id"] if x else None})
    n=len(candidates)
    completed=counts["pass"]+counts["fail"]
    coverage=round(100*completed/n,1) if n else None
    pass_rate=round(100*counts["pass"]/completed,1) if completed else None
    indicative=round(100*counts["pass"]/n,1) if n else None
    clause_count=None; mapped_clauses=None
    if audit or standard:
        clause_filter = """(:standard IS NULL OR cl.standard_id=:standard)
            AND (:audit IS NULL OR EXISTS (SELECT 1 FROM audit_clauses ac
                WHERE ac.audit_id=:audit AND ac.clause_id=cl.id))"""
        mapped = ("""SELECT pm.control_id FROM audit_planned_mappings pm
                     WHERE pm.audit_id=:audit AND pm.clause_id=cl.id""" if audit else
                  """SELECT cc.control_id FROM control_clauses cc JOIN controls c ON c.id=cc.control_id
                     WHERE cc.clause_id=cl.id AND c.active=1""")
        if process:
            mapped += " AND " + ("pm" if audit else "cc") + """.control_id IN (
                SELECT control_id FROM control_processes WHERE process_id=:process)"""
        summary = db.execute(f"""SELECT COUNT(*) n, COALESCE(SUM(EXISTS ({mapped})),0) mapped
            FROM clauses cl WHERE {clause_filter}""",params).fetchone()
        clause_count,mapped_clauses = summary["n"],summary["mapped"]
    return {"filter":{"standard_id":standard,"process_id":process,"audit_id":audit},
            "total_controls":n,"completed":completed,"pending":n-completed,
            "completion_pct":coverage,"pass_pct":pass_rate,"indicative_pct":indicative,
            "counts":counts,"clause_count":clause_count,"mapped_clauses":mapped_clauses,
            "framework_coverage_pct":round(mapped_clauses*100/clause_count,1) if clause_count else None,
            "evaluation_type":"Denetim bazlı test" if audit else "Çapraz kapsam ön değerlendirmesi",
            "disclaimer":"Kontrol ve kanıta dayalı ön gösterge; sertifikasyon veya standart uygunluğu kararı değildir.",
            "controls":results}


def _respond_download(handler,raw,filename,content_type):
    from urllib.parse import quote
    safe=re.sub(r"[^a-zA-Z0-9._-]","_",filename)
    disposition=f"attachment; filename=\"{safe}\"; filename*=UTF-8''{quote(filename)}"
    handler.send_response(200)
    handler.send_header("Content-Type",content_type)
    handler.send_header("Content-Disposition",disposition)
    handler.send_header("Content-Length",str(len(raw)))
    handler.send_header("Cache-Control","no-store")
    handler.send_header("X-Content-Type-Options","nosniff")
    handler.send_header("X-Frame-Options","DENY")
    handler.end_headers()
    handler.wfile.write(raw)


def _error(handler,exc):
    if isinstance(exc,risk_management.ApprovalDenied):
        handler.respond(403,{"error":str(exc)})
    elif isinstance(exc,StaleAudit):
        handler.respond(409,{"error":str(exc)})
    elif isinstance(exc,(ValueError,sqlite3.IntegrityError,json.JSONDecodeError)):
        handler.respond(400,{"error":str(exc)[:350]})
    else:
        # Avoid leaking filesystem paths, SQL internals and authentication secrets.
        handler.respond(500,{"error":"Beklenmeyen işlem hatası"})



def objective_context(db, oid):
    """Direct controls; clauses/processes derived through CURRENT control mappings."""
    objective=db.execute("SELECT * FROM objectives WHERE id=?", (oid,)).fetchone()
    if not objective:
        return None
    result=dict(objective)
    result["controls"]=rows(db,"""SELECT c.* FROM controls c
        JOIN control_objectives co ON co.control_id=c.id
        WHERE co.objective_id=? ORDER BY c.code,c.id""",(oid,))
    result["clauses"]=rows(db,"""SELECT DISTINCT cl.*,s.code AS standard_code,s.name AS standard_name
        FROM control_objectives co JOIN control_clauses cc ON cc.control_id=co.control_id
        JOIN clauses cl ON cl.id=cc.clause_id JOIN standards s ON s.id=cl.standard_id
        WHERE co.objective_id=? ORDER BY s.code,cl.code,cl.id""",(oid,))
    result["processes"]=rows(db,"""SELECT DISTINCT p.* FROM control_objectives co
        JOIN control_processes cp ON cp.control_id=co.control_id JOIN processes p ON p.id=cp.process_id
        WHERE co.objective_id=? ORDER BY p.code,p.id""",(oid,))
    result["relationship_basis"]={"controls":"direct","clauses":"via_controls","processes":"via_controls"}
    return result


def set_objective_controls(db, oid, ids):
    """Replace this objective's links only; do not rewrite any execution snapshot."""
    if not isinstance(ids,list) or any(type(i)is not int or i<1 for i in ids):
        raise ValueError("Kontrol kimlikleri pozitif tam sayı listesi olmalı")
    if not db.execute("SELECT id FROM objectives WHERE id=?",(oid,)).fetchone():
        raise ValueError("Kontrol hedefi bulunamadı")
    for cid in set(ids):
        if not db.execute("SELECT id FROM controls WHERE id=?",(cid,)).fetchone():
            raise ValueError("Bağlanmak istenen kontrol bulunamadı")
    db.execute("DELETE FROM control_objectives WHERE objective_id=?",(oid,))
    db.executemany("INSERT INTO control_objectives(control_id,objective_id) VALUES(?,?)",
                   [(cid,oid) for cid in sorted(set(ids))])
    return objective_context(db,oid)


class StaleAudit(ValueError):
    pass


def _audit_ids(values):
    if not isinstance(values, list) or any(type(i) is not int or i <= 0 for i in values):
        raise ValueError("Kapsam kimlikleri pozitif tam sayı listesi olmalı")
    return set(values)


def validate_audit_fields(audit):
    name = audit.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("Denetim adı gerekli")
    for key in ("scope", "audit_objective", "conclusion", "auditors", "auditees"):
        if audit.get(key) is not None and not isinstance(audit[key], str):
            raise ValueError(f"{FIELD_LABELS[key]} metin olmalı")
    status = audit.get("status", "planned")
    if not isinstance(status,str) or status not in CHOICES["audits"]["status"]:
        raise ValueError("Denetim durumu geçersiz")
    for key in ("planned_start","planned_end","actual_start","actual_end"):
        raw = audit.get(key)
        if raw is None or raw == "":
            continue
        try:
            if date.fromisoformat(raw).isoformat() != raw:
                raise ValueError
        except (TypeError, ValueError):
            raise ValueError(f"{FIELD_LABELS[key]} geçerli bir YYYY-AA-GG tarihi olmalı") from None
    for start, end in (("planned_start","planned_end"),("actual_start","actual_end")):
        if audit.get(start) and audit.get(end) and audit[end] < audit[start]:
            raise ValueError("Bitiş tarihi başlangıçtan önce olamaz")
    if audit.get("actual_end") and not audit.get("actual_start"):
        raise ValueError("Gerçekleşen bitiş için gerçekleşen başlangıç gerekli")
    if status == "planned" and audit.get("actual_start"):
        raise ValueError("Planlanan denetimde gerçekleşen tarih bulunamaz")
    if status == "in_progress" and audit.get("actual_end"):
        raise ValueError("Devam eden denetimde gerçekleşen bitiş bulunamaz")
    if status in ("in_progress","completed","closed") and not audit.get("actual_start"):
        raise ValueError("Bu durum için gerçekleşen başlangıç gerekli")
    if status in ("completed","closed") and not audit.get("actual_end"):
        raise ValueError("Tamamlanan denetimde gerçekleşen bitiş gerekli")


def validate_audit_coverage(audit, standards, represented):
    if audit["status"] in ("in_progress","completed","closed"):
        if standards - represented:
            raise ValueError("Her standart için en az bir kapsam maddesi seçin")
        if not standards and not (audit.get("scope") or "").strip():
            raise ValueError("Standartsız denetimde iç kapsamı açıklayın")


def capture_audit_plan(db, aid):
    db.execute("INSERT INTO audit_plan_snapshots VALUES(?,?)", (aid,now()))
    db.execute("""INSERT INTO audit_plan_links
        SELECT ac.audit_id,ac.clause_id,cc.control_id FROM audit_clauses ac JOIN control_clauses cc
        ON cc.clause_id=ac.clause_id JOIN controls c ON c.id=cc.control_id AND c.active=1
        WHERE ac.audit_id=?""", (aid,))


def save_audit(db, data, handler, aid=None, from_standard=False):
    """Validate the full proposal before replacing the audit and its selected scope."""
    import app
    if not db.in_transaction:
        db.execute("BEGIN IMMEDIATE")
    previous = app.audit_scope(db,aid) if aid is not None else None
    if aid is not None and previous is None:
        return None
    fields = app.TABLES["audits"]
    if not data or set(data) - set(fields) - {"standard_ids","clause_ids","expected_revision"} - ({"standard_id"} if from_standard else set()):
        raise ValueError("Geçersiz denetim alanları")
    old_st = {s["id"] for s in previous["standards"]} if previous else set()
    old_cl = {c["id"] for c in previous["clauses"]} if previous else set()
    standards, clauses = old_st, old_cl
    if from_standard:
        standards = _audit_ids([data.get("standard_id")])
        clauses = {r[0] for r in db.execute("SELECT id FROM clauses WHERE standard_id=?", (data["standard_id"],))}
    elif "standard_ids" in data or "clause_ids" in data:
        clauses = _audit_ids(data.get("clause_ids"))
        if "standard_ids" in data:
            standards = _audit_ids(data["standard_ids"])
        elif previous is None:
            # Original create API accepts clause_ids without standard_ids.
            standards = {r[0] for r in db.execute(
                "SELECT DISTINCT standard_id FROM clauses WHERE id IN (SELECT value FROM json_each(?))",
                (json.dumps(sorted(clauses)),))}
        else:
            raise ValueError("Kapsam güncellemesinde standart ve madde listeleri birlikte gerekli")
    if previous and (("standard_ids" in data or "clause_ids" in data) or "expected_revision" in data):
        revision = data.get("expected_revision")
        if type(revision) is not int or revision != previous["revision"]:
            raise StaleAudit("Denetim değişmiş olabilir. Kaydı yenileyip tekrar deneyin.")
    updates = {key:value for key,value in data.items() if key in fields}
    merged = {"status":"planned", **(previous or {}), **updates}
    validate_audit_fields(merged)
    if previous and previous["status"] in ("completed","closed","cancelled"):
        if merged["status"] != previous["status"] and (previous["status"],merged["status"]) != ("completed","closed"):
            raise ValueError("Sonuçlandırılmış denetim tekrar açılamaz")
        if (old_st,old_cl) != (standards,clauses) or merged.get("scope") != previous["scope"]:
            raise ValueError("Sonuçlandırılmış denetimin kapsamı değiştirilemez")
    if standards != {r[0] for r in db.execute(
            "SELECT id FROM standards WHERE id IN (SELECT value FROM json_each(?))",
            (json.dumps(sorted(standards)),))}:
        raise ValueError("Seçilen standart bulunamadı")
    members = dict(db.execute(
        "SELECT id,standard_id FROM clauses WHERE id IN (SELECT value FROM json_each(?))",
        (json.dumps(sorted(clauses)),)))
    if set(members) != clauses or not set(members.values()) <= standards:
        raise ValueError("Her madde seçilen standartlardan birine ait olmalı")
    validate_audit_coverage(merged, standards, set(members.values()))
    if previous:
        setters = [f"{key}=?" for key in updates] + ["revision=revision+1"]
        db.execute("UPDATE audits SET " + ", ".join(setters) + " WHERE id=?", [*updates.values(), aid])
    else:
        aid = app.insert(db, "audits", updates)
    if (standards,clauses) != (old_st,old_cl):
        db.execute("DELETE FROM audit_clauses WHERE audit_id=?", (aid,))
        db.execute("DELETE FROM audit_standards WHERE audit_id=?", (aid,))
        db.executemany("INSERT INTO audit_standards VALUES(?,?)", ((aid,i) for i in sorted(standards)))
        db.executemany("INSERT INTO audit_clauses VALUES(?,?)", ((aid,i) for i in sorted(clauses)))
    if merged["status"] in ("completed","closed","cancelled") and (
            not previous or previous["status"] not in ("completed","closed","cancelled")):
        # Historical closed rows have no reliable closure snapshot; leave those explicitly unknown.
        capture_audit_plan(db,aid)
    delta = {"standart_eklenen":sorted(standards-old_st), "standart_çıkarılan":sorted(old_st-standards),
             "madde_eklenen":sorted(clauses-old_cl), "madde_çıkarılan":sorted(old_cl-clauses)}
    log(db, handler, "UPDATE" if previous else "CREATE", "audits", aid,
        json.dumps(delta, ensure_ascii=False, separators=(",",":")))
    return app.audit_scope(db,aid)


def audit_context(db, aid):
    """Keep this audit's findings distinct from other open findings in its control scope.

    An explicit finding.audit_id is authoritative; legacy rows can inherit the audit
    from their execution. Scope controls include current clause mappings AND controls
    actually tested in this audit, even if their current mappings later change.
    """
    import app
    result=app.audit_scope(db,aid)
    if result is None:
        return None
    scope_sql="""SELECT control_id FROM audit_planned_mappings WHERE audit_id=:aid
        UNION SELECT control_id FROM executions WHERE audit_id=:aid"""
    result["controls"]=rows(db,f"SELECT * FROM controls WHERE id IN ({scope_sql}) ORDER BY code,id",{"aid":aid})
    planned = {r[0] for r in db.execute("SELECT control_id FROM audit_planned_mappings WHERE audit_id=?", (aid,))}
    result["planned_controls"] = [c for c in result["controls"] if c["id"] in planned]
    result["tested_outside_scope"] = [c for c in result["controls"] if c["id"] not in planned]
    snapshot=db.execute("SELECT captured_at FROM audit_plan_snapshots WHERE audit_id=?", (aid,)).fetchone()
    result["plan_captured_at"] = snapshot[0] if snapshot else None
    finding_sql="""SELECT f.*,COALESCE(f.audit_id,x.audit_id) AS origin_audit_id,
        COALESCE(f.control_id,x.control_id) AS effective_control_id,
        c.code AS control_code,c.name AS control_name,a.name AS origin_audit_name,
        CASE WHEN f.audit_id IS NOT NULL THEN 'direct'
             WHEN x.audit_id IS NOT NULL THEN 'via_execution' ELSE 'outside_audit' END AS audit_link_source
        FROM findings f LEFT JOIN executions x ON x.id=f.execution_id
        LEFT JOIN controls c ON c.id=COALESCE(f.control_id,x.control_id)
        LEFT JOIN audits a ON a.id=COALESCE(f.audit_id,x.audit_id)"""
    result["findings"]=rows(db,finding_sql+"""
        WHERE COALESCE(f.audit_id,x.audit_id)=:aid ORDER BY f.created_at DESC,f.id DESC""",{"aid":aid})
    result["other_open_findings"]=rows(db,finding_sql+f"""
        WHERE (COALESCE(f.audit_id,x.audit_id) IS NULL OR COALESCE(f.audit_id,x.audit_id)<>:aid)
        AND f.status IN ('open','in_progress')
        AND COALESCE(f.control_id,x.control_id) IN ({scope_sql})
        ORDER BY f.created_at DESC,f.id DESC""",{"aid":aid})
    result["finding_summary"]={"total":len(result["findings"]),
        "open":sum(f["status"] in ("open","in_progress") for f in result["findings"]),
        "other_open":len(result["other_open_findings"])}
    return result


def get(handler):
    """Return True when a request is handled."""
    import app
    path=urlparse(handler.path)
    parts=path.path.strip("/").split("/")
    query=parse_qs(path.query)
    try:
        with app.connect() as db:
            if len(parts)==4 and parts[0]=="api" and parts[3]=="context" and parts[1] in ("objectives","audits"):
                result=(objective_context if parts[1]=="objectives" else audit_context)(db,int(parts[2]))
                return handler.respond(200 if result is not None else 404,
                    result if result is not None else {"error":"Kayıt bulunamadı"}) or True
            if path.path == "/api/audits/scope-catalog":
                return handler.respond(200, {
                    "standards":rows(db,"SELECT id,code,name,version FROM standards ORDER BY code,id"),
                    "clauses":rows(db,"SELECT id,standard_id,parent_id,code,title FROM clauses ORDER BY standard_id,code,id"),
                }) or True
            if path.path=="/api/metadata":
                return handler.respond(200,{"labels":{**app.LABELS,**NEW_LABELS},
                    "fields":FIELD_LABELS,"choices":CHOICES}) or True
            if path.path=="/api/compliance":
                return handler.respond(200,compliance(db,query)) or True
            if path.path=="/api/architecture/data":
                return handler.respond(200,{"models":[
                    {"id":"sources","label":"Kaynak sistemler","items":["ServiceNow ITSM","Dynamics 365","CMDB / keşif / SIEM"]},
                    {"id":"mcp","label":"Mevcut MCP orkestrasyon katmanı","items":["Yetkili sorgular","Zamanlama / otomasyon","Sonuç değerlendirme"]},
                    {"id":"controls","label":"KS GRC kontrol çekirdeği","items":["Standart ve maddeler","Kontrol hedefleri","Süreçler / Kontroller"]},
                    {"id":"evidence","label":"Kanıt ve izlenebilirlik","items":["Kanıt sürümleri","Çoklu eşleştirme","Denetim geçmişi"]},
                    {"id":"outcomes","label":"Güvence ve iyileştirme","items":["Denetimler","Bulgular / DÖF","Riskler / göstergeler"]}
                    ],"note":"ServiceNow ile KS GRC doğrudan konuşmaz; MCP katmanı okur ve yazar."}) or True
            if path.path=="/api/admin/summary":
                if getattr(handler,"auth_type",None)!="session":
                    return handler.respond(403,{"error":"Kullanıcı oturumu gerekli"}) or True
                users=rows(db,"SELECT id,username,display_name,email,is_active,created_at,last_login_at FROM users ORDER BY id")
                return handler.respond(200,{"users":users,"user_count":len(users),
                   "active_users":sum(x["is_active"] for x in users),
                   "roles":rows(db,"SELECT id,code,name FROM roles"),
                   "schema_version":SCHEMA_VERSION,
                   "activity":rows(db,"SELECT actor,method,object_type,object_id,occurred_at FROM activity_log ORDER BY id DESC LIMIT 30"),
                   "counts":{t:db.execute(f"SELECT COUNT(*) AS n FROM {t}").fetchone()["n"]
                             for t in list(app.TABLES) if t not in ("executions",) and t in app.TABLES}}) or True
            if len(parts)==4 and parts[:2]==["api","evidence"] and parts[3]=="context":
                eid=int(parts[2]);result=extended_context(db,eid)
                return handler.respond(200 if result else 404,result or {"error":"Kanıt bulunamadı"}) or True
            if len(parts)==4 and parts[:2]==["api","evidence"] and parts[3]=="download":
                eid=int(parts[2])
                v=query.get("version",[None])[0]
                result=fetch_file(db,eid,int(v) if v else None)
                if not result:
                    return handler.respond(404,{"error":"Kanıt dosyası bulunamadı"}) or True
                raw,filename,_=result
                _respond_download(handler,raw,filename,"application/octet-stream")
                return True
            if len(parts)==4 and parts[:2]==["api","risks"] and parts[3]=="context":
                result=risk_management.context(db,int(parts[2]))
                return handler.respond(200 if result else 404,result or {"error":"Risk bulunamadı"}) or True
            if parts==["api","risks"]:
                return handler.respond(200,rows(db,"""SELECT r.*, r.likelihood*r.impact AS inherent_score,
                    a.residual AS residual_score, a.appetite AS assessed_appetite, a.assessed_at
                    FROM risks r LEFT JOIN risk_assessments a ON a.id=(
                        SELECT id FROM risk_assessments WHERE risk_id=r.id ORDER BY id DESC LIMIT 1)
                    ORDER BY r.id DESC LIMIT 1000""")) or True
            if len(parts)==2 and parts[:1]==["api"] and parts[1] in SCHEMA:
                table=parts[1]
                return handler.respond(200,rows(db,f"SELECT * FROM {table} ORDER BY id DESC LIMIT 1000")) or True
            if len(parts)==4 and parts[:2]==["api","risks"] and parts[3]=="controls":
                rid=int(parts[2]);return handler.respond(200,rows(db, """SELECT c.id,c.code,c.name
                      FROM controls c JOIN control_risks m ON m.control_id=c.id
                      WHERE m.risk_id=?""",(rid,))) or True
            if len(parts)==4 and parts[:2]==["api","documents"] and parts[3]=="controls":
                did=int(parts[2]);return handler.respond(200,rows(db, """SELECT c.id,c.code,c.name
                     FROM controls c JOIN document_controls m ON m.control_id=c.id WHERE m.document_id=?""",(did,))) or True
            if len(parts)==4 and parts[:2]==["api","audits"] and parts[3]=="evidence":
                aid=int(parts[2]);return handler.respond(200,rows(db, """SELECT DISTINCT e.*
                    FROM evidence e LEFT JOIN evidence_audits ea ON ea.evidence_id=e.id
                    LEFT JOIN execution_evidence xe ON xe.evidence_id=e.id
                    LEFT JOIN executions x ON xe.execution_id=x.id
                    WHERE ea.audit_id=? OR x.audit_id=? ORDER BY e.id DESC""",(aid,aid))) or True
            if len(parts)==4 and parts[:2]==["api","controls"] and parts[3]=="evidence":
                cid=int(parts[2]);return handler.respond(200,rows(db, """SELECT DISTINCT e.* FROM evidence e
                    LEFT JOIN evidence_controls m ON e.id=m.evidence_id
                    LEFT JOIN execution_evidence ex ON e.id=ex.evidence_id
                    LEFT JOIN executions x ON x.id=ex.execution_id
                    WHERE m.control_id=? OR x.control_id=? ORDER BY e.id DESC""",(cid,cid))) or True
            if path.path.startswith("/api/excel/export"):
                import grc_excel
                sheet=query.get("table",["all"])[0]
                binary=grc_excel.export(db,sheet)
                _respond_download(handler,binary,f"ks-grc-{sheet}.xlsx",
                                  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                return True
    except (ValueError,sqlite3.Error) as exc:
        _error(handler,exc);return True
    return False


def post(handler):
    import app
    path=urlparse(handler.path)
    parts=path.path.strip("/").split("/")
    try:
        if parts in (["api","audits"],["api","audits","from-standard"]):
            data = json_body(handler)
            with app.connect() as db:
                result = save_audit(db, data, handler, from_standard=len(parts)==3)
                db.commit()
            return handler.respond(201, {"id":result["id"], "audit_id":result["id"],
                "clause_count":len(result["clauses"]), "revision":result["revision"]}) or True
        if len(parts)==4 and parts[:2]==["api","risks"] and parts[3]=="assessments":
            data=json_body(handler);rid=int(parts[2])
            with app.connect() as db:
                result=risk_management.assess(db,rid,data,handler.current_user["username"],now())
                log(db,handler,"ASSESS","risks",rid)
                db.commit()
            return handler.respond(201,result) or True
        if len(parts)==4 and parts[:2]==["api","objectives"] and parts[3]=="controls":
            if getattr(handler,"auth_type",None)!="session":
                return handler.respond(403,{"error":"Kullanıcı oturumu gerekli"}) or True
            oid=int(parts[2]);data=json_body(handler)
            with app.connect() as db:
                if not db.execute("SELECT id FROM objectives WHERE id=?",(oid,)).fetchone():
                    return handler.respond(404,{"error":"Kontrol hedefi bulunamadı"}) or True
                result=set_objective_controls(db,oid,data.get("control_ids"))
                log(db,handler,"MAP","objectives",oid,"Kontrol hedefi–kontrol bağlantıları")
                db.commit()
            handler.respond(200,result)
            return True
        if len(parts)==2 and parts[:1]==["api"] and parts[1] in SCHEMA:
            table=parts[1];data=json_body(handler)
            validate_record(table,data)
            with app.connect() as db:
                if table=="risks":risk_management.decision(db,None,{},data)
                fields={k:v for k,v in data.items() if k in SCHEMA[table]}
                if "created_at" in SCHEMA[table]: fields.setdefault("created_at",now())
                if db.execute(f"SELECT id FROM {table} WHERE code=?",(fields["code"],)).fetchone():
                    raise ValueError("Bu kod daha önce kullanılmış")
                rid=app.insert(db,table,fields)
                log(db,handler,"CREATE",table,rid)
                db.commit()
                handler.respond(201,{"id":rid})
            return True
        if len(parts)==3 and parts[:2]==["api","admin"] and parts[2]=="users":
            if getattr(handler,"auth_type",None)!="session":
                return handler.respond(403,{"error":"Yalnızca kullanıcı oturumundan işlem yapılabilir"}) or True
            import identity
            data=json_body(handler)
            username=data.get("username","")
            if not isinstance(username,str) or not re.fullmatch(r"[a-zA-Z0-9_.-]{3,60}",username):
                raise ValueError("Kullanıcı adı 3–60 karakter (harf, rakam, . _ -) olmalı")
            import secrets
            password=secrets.token_urlsafe(18)
            with app.connect() as db:
                if not identity.provision(db,username,password):
                    raise ValueError("Bu kullanıcı adı zaten kullanılıyor")
                row=db.execute("SELECT id FROM users WHERE username=?",(username,)).fetchone()
                if not row or not db.execute("SELECT password_hash FROM users WHERE id=?",(row["id"],)).fetchone()["password_hash"]:
                    raise ValueError("Kullanıcı oluşturulamadı veya zaten var")
                if db.execute("SELECT COUNT(*) AS n FROM users WHERE username=?",(username,)).fetchone()["n"]!=1:
                    raise ValueError("Kullanıcı kaydı geçersiz")
                log(db,handler,"CREATE","users",row["id"])
                db.commit()
            handler.respond(201,{"id":row["id"],"username":username,
                                 "temporary_password":password,"must_change_password":True})
            return True
        if len(parts)==4 and parts[:2]==["api","evidence"] and parts[3]=="mappings":
            eid=int(parts[2]);payload=json_body(handler)
            with app.connect() as db:
                if not db.execute("SELECT id FROM evidence WHERE id=?",(eid,)).fetchone():
                    return handler.respond(404,{"error":"Kanıt bulunamadı"}) or True
                mappings(db,eid,payload,True)
                log(db,handler,"MAP","evidence",eid)
                db.commit()
                handler.respond(200,extended_context(db,eid))
            return True
        if len(parts)==3 and parts==["api","evidence","upload"]:
            data=json_body(handler,MAX_BODY)
            if handler.auth_type=="api_key" and data.get("source")!="mcp":
                return handler.respond(403,{"error":"Makine anahtarı yalnız MCP kaynaklı kanıt yükleyebilir"}) or True
            with app.connect() as db:
                result=save_file(db,data)
                log(db,handler,"UPLOAD","evidence",result["id"],result["file_name"])
                db.commit()
            handler.respond(201,result)
            return True
        if len(parts)==4 and parts[:2]==["api","evidence"] and parts[3]=="versions":
            eid=int(parts[2]);data=json_body(handler,MAX_BODY)
            with app.connect() as db:
                if handler.auth_type=="api_key":
                    if not db.execute("SELECT id FROM evidence WHERE id=? AND source='mcp'",(eid,)).fetchone():
                        return handler.respond(403,{"error":"Yalnız MCP kaynaklı kanıta sürüm eklenebilir"}) or True
                result=save_file(db,data,eid)
                log(db,handler,"VERSION","evidence",eid,result["file_name"])
                db.commit()
            handler.respond(201,result)
            return True
        if len(parts)==4 and parts[:2]==["api","audits"] and parts[3]=="evidence":
            aid=int(parts[2]);data=json_body(handler)
            ids=data.get("evidence_ids")
            if not isinstance(ids,list) or any(type(n)is not int or n<1 for n in ids):
                raise ValueError("Kanıt kimlikleri listesi gerekli")
            with app.connect() as db:
                if not db.execute("SELECT id FROM audits WHERE id=?",(aid,)).fetchone():
                    return handler.respond(404,{"error":"Denetim bulunamadı"}) or True
                db.execute("DELETE FROM evidence_audits WHERE audit_id=?",(aid,))
                for eid in ids:
                    db.execute("INSERT INTO evidence_audits(evidence_id,audit_id) VALUES(?,?)",(eid,aid))
                log(db,handler,"MAP","audits",aid,"Denetim kanıtları")
                db.commit()
            handler.respond(200,{"audit_id":aid,"evidence_count":len(ids)})
            return True
        if len(parts)==4 and parts[:2]==["api","risks"] and parts[3]=="controls":
            rid=int(parts[2]);data=json_body(handler);ids=data.get("control_ids")
            if not isinstance(ids,list) or any(type(n)is not int for n in ids):
                raise ValueError("Kontrol kimlikleri listesi gerekli")
            with app.connect() as db:
                db.execute("BEGIN IMMEDIATE")
                risk=db.execute("SELECT status FROM risks WHERE id=?",(rid,)).fetchone()
                if not risk:
                    return handler.respond(404,{"error":"Risk bulunamadı"}) or True
                if risk["status"] in risk_management.TERMINAL:
                    raise ValueError("Bağlantıları değiştirmeden önce riski yeniden açın")
                db.execute("DELETE FROM control_risks WHERE risk_id=?",(rid,))
                for cid in ids:
                    db.execute("INSERT INTO control_risks(control_id,risk_id) VALUES(?,?)",(cid,rid))
                log(db,handler,"MAP","risks",rid)
                db.commit()
            handler.respond(200,{"id":rid,"control_count":len(ids)})
            return True
        if len(parts)==4 and parts[:2]==["api","documents"] and parts[3]=="controls":
            did=int(parts[2]);data=json_body(handler);ids=data.get("control_ids")
            if not isinstance(ids,list) or any(type(n)is not int for n in ids):
                raise ValueError("Kontrol kimlikleri listesi gerekli")
            with app.connect() as db:
                db.execute("DELETE FROM document_controls WHERE document_id=?",(did,))
                for cid in ids:
                    db.execute("INSERT INTO document_controls(document_id,control_id) VALUES(?,?)",(did,cid))
                log(db,handler,"MAP","documents",did)
                db.commit()
            handler.respond(200,{"id":did,"control_count":len(ids)})
            return True
        if path.path=="/api/excel/import":
            import grc_excel
            data=json_body(handler,MAX_BODY)
            table=parse_qs(path.query).get("table",["all"])[0]
            with app.connect() as db:
                result=grc_excel.import_xlsx(db,data,table)
                log(db,handler,"IMPORT","excel",None,str(result))
                db.commit()
            handler.respond(200,result)
            return True
    except (ValueError,sqlite3.IntegrityError,json.JSONDecodeError) as exc:
        _error(handler,exc);return True
    return False


def patch(handler):
    import app
    parts=urlparse(handler.path).path.strip("/").split("/")
    try:
        if len(parts)==3 and parts[:2]==["api","audits"]:
            data = json_body(handler)
            with app.connect() as db:
                result = save_audit(db, data, handler, aid=int(parts[2]))
                if result is None:
                    return handler.respond(404,{"error":"Denetim bulunamadı"}) or True
                db.commit()
            return handler.respond(200,result) or True
        if len(parts)==4 and parts[:3]==["api","admin","users"]:
            if getattr(handler,"auth_type",None)!="session":
                return handler.respond(403,{"error":"Yalnızca kullanıcı oturumundan işlem yapılabilir"}) or True
            user_id=int(parts[3]);data=json_body(handler)
            allowed={"is_active","display_name","email"}
            if not set(data) or set(data)-allowed:
                raise ValueError("Güncellenebilir kullanıcı alanları: is_active, display_name, email")
            with app.connect() as db:
                if "is_active" in data:
                    if data["is_active"] not in (0,1,False,True):
                        raise ValueError("Aktiflik 0 veya 1 olmalı")
                    if not data["is_active"] and user_id==handler.current_user["id"]:
                        raise ValueError("Kendi hesabınızı devre dışı bırakamazsınız")
                    data["is_active"]=int(bool(data["is_active"]))
                setter=", ".join(f"{k}=?" for k in data)
                cursor=db.execute(f"UPDATE users SET {setter},updated_at=? WHERE id=?",
                    list(data.values())+[now(),user_id])
                if not cursor.rowcount:
                    return handler.respond(404,{"error":"Kullanıcı bulunamadı"}) or True
                if data.get("is_active")==0:
                    db.execute("DELETE FROM auth_sessions WHERE user_id=?",(user_id,))
                log(db,handler,"UPDATE","users",user_id)
                db.commit()
                handler.respond(200,{"id":user_id,"updated":True})
            return True
        if len(parts)==3 and parts[0]=="api" and parts[1] in SCHEMA:
            table=parts[1];rid=int(parts[2]);data=json_body(handler)
            details = {key:data.pop(key) for key in risk_management.DECISION_INPUT if key in data} if table=="risks" else {}
            if not data or set(data)-(set(SCHEMA[table])-{"created_at"}):
                raise ValueError("Geçersiz güncelleme alanları")
            with app.connect() as db:
                db.execute("BEGIN IMMEDIATE")
                row=db.execute(f"SELECT * FROM {table} WHERE id=?",(rid,)).fetchone()
                if not row:return handler.respond(404,{"error":"Kayıt bulunamadı"}) or True
                proposal={**dict(row),**data}
                validate_record(table,proposal)
                if table=="risks":
                    if "catalog_id" in data and data["catalog_id"]!=row["catalog_id"]:
                        raise ValueError("Riskin kaynak şablonu değiştirilemez")
                    role = handler.current_user["app_role"] if app.ENTRA else "local-admin"
                    risk_management.decision(db,rid,dict(row),proposal,details=details,
                            actor=handler.current_user["username"],role=role,at=now())
                setters=", ".join(f"{k}=?" for k in data)
                cursor=db.execute(f"UPDATE {table} SET {setters} WHERE id=?",[*data.values(),rid])
                if not cursor.rowcount:
                    return handler.respond(404,{"error":"Kayıt bulunamadı"}) or True
                log(db,handler,"UPDATE",table,rid)
                db.commit()
                handler.respond(200,rows(db,f"SELECT * FROM {table} WHERE id=?",(rid,))[0])
            return True
    except (ValueError,sqlite3.IntegrityError,json.JSONDecodeError) as exc:
        _error(handler,exc);return True
    return False
