"""Control GRC MVP: single-file, dependency-free web app and JSON API."""
import json
import base64
import hmac
import os
import sqlite3
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse
from html import escape

DB = os.getenv("CONTROL_DB", "control.db")
KEY = os.getenv("CONTROL_API_KEY", "")
UI_USER = os.getenv("CONTROL_UI_USER", "")
UI_PASSWORD = os.getenv("CONTROL_UI_PASSWORD", "")
HOST = os.getenv("CONTROL_HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8080"))

TABLES = {
    "standards": {"code": "TEXT NOT NULL", "name": "TEXT NOT NULL", "version": "TEXT", "description": "TEXT"},
    "clauses": {"standard_id": "INTEGER NOT NULL REFERENCES standards(id)", "code": "TEXT NOT NULL", "title": "TEXT NOT NULL", "parent_id": "INTEGER REFERENCES clauses(id)", "description": "TEXT"},
    "processes": {"code": "TEXT NOT NULL", "name": "TEXT NOT NULL", "owner": "TEXT", "description": "TEXT"},
    "objectives": {"code": "TEXT NOT NULL", "name": "TEXT NOT NULL", "description": "TEXT"},
    "controls": {"code": "TEXT NOT NULL", "name": "TEXT NOT NULL", "description": "TEXT", "execution_mode": "TEXT NOT NULL DEFAULT 'manual'", "nature": "TEXT NOT NULL DEFAULT 'detective'", "frequency": "TEXT NOT NULL DEFAULT 'on_demand'", "method": "TEXT", "expected_result": "TEXT", "owner": "TEXT", "active": "INTEGER NOT NULL DEFAULT 1"},
    "audits": {"name": "TEXT NOT NULL", "scope": "TEXT", "planned_start": "TEXT", "planned_end": "TEXT", "actual_start": "TEXT", "actual_end": "TEXT", "auditors": "TEXT", "auditees": "TEXT", "status": "TEXT NOT NULL DEFAULT 'planned'"},
    "evidence": {"title": "TEXT NOT NULL", "description": "TEXT", "reference_url": "TEXT", "collected_at": "TEXT", "source": "TEXT", "hash_sha256": "TEXT"},
    "executions": {"control_id": "INTEGER NOT NULL REFERENCES controls(id)", "audit_id": "INTEGER REFERENCES audits(id)", "status": "TEXT NOT NULL", "source": "TEXT NOT NULL DEFAULT 'manual'", "details": "TEXT", "executed_at": "TEXT NOT NULL"},
    "findings": {"title": "TEXT NOT NULL", "control_id": "INTEGER REFERENCES controls(id)", "execution_id": "INTEGER REFERENCES executions(id)", "audit_id": "INTEGER REFERENCES audits(id)", "description": "TEXT", "severity": "TEXT NOT NULL DEFAULT 'medium'", "status": "TEXT NOT NULL DEFAULT 'open'", "created_at": "TEXT NOT NULL"}
}
MAPPINGS = {"clauses": "control_clauses", "processes": "control_processes", "objectives": "control_objectives"}
TARGET_COLUMNS = {"clauses": "clause", "processes": "process", "objectives": "objective"}
ALLOWED_STATUS = {"pass", "fail", "not_applicable", "inconclusive"}
ALLOWED_MODES = {"manual", "automatic"}
ALLOWED_NATURE = {"preventive", "detective", "corrective", "directive", "compensating"}
LABELS = {"standards": "Standartlar", "clauses": "Maddeler", "processes": "Süreçler", "objectives": "Kontrol Hedefleri", "controls": "Kontroller", "audits": "Denetimler", "evidence": "Kanıtlar", "executions": "Kontrol Sonuçları", "findings": "Bulgular"}


def connect():
    db = sqlite3.connect(DB, timeout=15)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    db.execute("PRAGMA busy_timeout=15000")
    return db


def initialize():
    with connect() as db:
        db.execute("PRAGMA journal_mode=WAL")
        for name, fields in TABLES.items():
            cols = ", ".join(f"{field} {definition}" for field, definition in fields.items())
            db.execute(f"CREATE TABLE IF NOT EXISTS {name} (id INTEGER PRIMARY KEY AUTOINCREMENT, {cols})")
        for target, table in MAPPINGS.items():
            db.execute(f"CREATE TABLE IF NOT EXISTS {table} (control_id INTEGER NOT NULL REFERENCES controls(id) ON DELETE CASCADE, {TARGET_COLUMNS[target]}_id INTEGER NOT NULL REFERENCES {target}(id) ON DELETE CASCADE, PRIMARY KEY(control_id, {TARGET_COLUMNS[target]}_id))")
        db.execute("CREATE TABLE IF NOT EXISTS execution_evidence (execution_id INTEGER REFERENCES executions(id) ON DELETE CASCADE, evidence_id INTEGER REFERENCES evidence(id) ON DELETE CASCADE, PRIMARY KEY(execution_id,evidence_id))")
        db.execute("CREATE TABLE IF NOT EXISTS evidence_clauses (evidence_id INTEGER REFERENCES evidence(id) ON DELETE CASCADE, clause_id INTEGER REFERENCES clauses(id) ON DELETE CASCADE, PRIMARY KEY(evidence_id,clause_id))")
        db.execute("CREATE TABLE IF NOT EXISTS evidence_processes (evidence_id INTEGER REFERENCES evidence(id) ON DELETE CASCADE, process_id INTEGER REFERENCES processes(id) ON DELETE CASCADE, PRIMARY KEY(evidence_id,process_id))")
        db.execute("CREATE TABLE IF NOT EXISTS audit_clauses (audit_id INTEGER REFERENCES audits(id) ON DELETE CASCADE, clause_id INTEGER REFERENCES clauses(id) ON DELETE CASCADE, PRIMARY KEY(audit_id,clause_id))")
        # Future identity/authorization schema. No login or permission enforcement yet.
        db.execute("""CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            email TEXT UNIQUE,
            display_name TEXT NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN (0,1)),
            created_at TEXT NOT NULL,
            updated_at TEXT
        )""")
        db.execute("""CREATE TABLE IF NOT EXISTS roles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            description TEXT
        )""")
        db.execute("""CREATE TABLE IF NOT EXISTS user_roles (
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            role_id INTEGER NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
            PRIMARY KEY(user_id,role_id)
        )""")
        for code, name, description in (
            ("ADMIN", "Yönetici", "Tam uygulama yetkisi (gelecekte uygulanacak)"),
            ("AUDITOR", "Denetçi", "Denetim ve kontrol çalışmaları (gelecekte uygulanacak)"),
            ("VIEWER", "Görüntüleyici", "Salt okunur erişim (gelecekte uygulanacak)")
        ):
            db.execute("INSERT OR IGNORE INTO roles(code,name,description) VALUES (?,?,?)", (code,name,description))


def utcnow():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def insert(db, table, payload):
    allowed = TABLES[table]
    data = {k: v for k, v in payload.items() if k in allowed}
    if not data:
        raise ValueError("No valid fields provided")
    if table == "controls":
        if data.get("execution_mode", "manual") not in ALLOWED_MODES:
            raise ValueError("Invalid execution_mode")
        if data.get("nature", "detective") not in ALLOWED_NATURE:
            raise ValueError("Invalid nature")
    if table == "executions":
        if data.get("status") not in ALLOWED_STATUS:
            raise ValueError("Invalid execution status")
        data.setdefault("executed_at", utcnow())
    if table == "findings":
        data.setdefault("created_at", utcnow())
    if table == "evidence":
        data.setdefault("collected_at", utcnow())
    columns = ", ".join(data)
    placeholders = ", ".join("?" for _ in data)
    cur = db.execute(f"INSERT INTO {table} ({columns}) VALUES ({placeholders})", tuple(data.values()))
    return cur.lastrowid


def rows(db, sql, args=()):
    return [dict(r) for r in db.execute(sql, args).fetchall()]


def mapping(db, table, parent_col, parent_id, target_col, ids):
    if not isinstance(ids, list) or any(type(i) is not int for i in ids):
        raise ValueError("Mapping must be a list of integer IDs")
    for item in ids:
        db.execute(f"INSERT OR IGNORE INTO {table} ({parent_col}, {target_col}) VALUES (?,?)", (parent_id, item))


def context(db, control_id):
    item = rows(db, "SELECT * FROM controls WHERE id=?", (control_id,))
    if not item:
        return None
    result = item[0]
    for target, table in MAPPINGS.items():
        result[target] = rows(db, f"SELECT t.* FROM {target} t JOIN {table} m ON m.{TARGET_COLUMNS[target]}_id=t.id WHERE m.control_id=?", (control_id,))
    return result


def execute(db, data):
    control_id = data.get("control_id")
    if not isinstance(control_id, int) or not context(db, control_id):
        raise ValueError("Valid control_id required")
    execution_id = insert(db, "executions", data)
    mapping(db, "execution_evidence", "execution_id", execution_id, "evidence_id", data.get("evidence_ids", []))
    finding_id = None
    if data["status"] == "fail":
        control = context(db, control_id)
        finding_id = insert(db, "findings", {
            "title": f"Kontrol başarısız: {control['code']} - {control['name']}",
            "control_id": control_id,
            "execution_id": execution_id,
            "audit_id": data.get("audit_id"),
            "description": data.get("details", ""),
            "severity": data.get("severity", "medium")
        })
    return {"execution_id": execution_id, "finding_id": finding_id}


STYLE = """
body{margin:0;background:#f5f7fb;color:#18253b;font:15px system-ui,Arial}
header{background:#15243e;color:white;padding:22px 32px}header h1{margin:0;font-size:25px}
header small{color:#b8c8e0}.layout{display:flex;min-height:calc(100vh - 88px)}
nav{width:215px;background:white;border-right:1px solid #e4e9f2;padding:18px;flex-shrink:0}
nav a{display:block;padding:10px 12px;color:#41506b;text-decoration:none;border-radius:8px;margin:3px 0}
nav a:hover,nav a.active{background:#e8effb;color:#1857ac}
main{padding:30px;flex:1;min-width:0}h2{margin:0 0 18px}section{background:white;border:1px solid #e3e8f0;border-radius:12px;padding:20px;margin:0 0 20px}
table{border-collapse:collapse;width:100%;font-size:13px}th,td{text-align:left;padding:10px;border-bottom:1px solid #e8edf4;vertical-align:top;overflow-wrap:anywhere}
th{color:#65728b;background:#f8fafc}input,select,textarea{padding:10px;border:1px solid #cbd5e1;border-radius:7px;font:inherit;max-width:100%;box-sizing:border-box}
form{display:flex;flex-wrap:wrap;gap:9px;align-items:center}button{background:#1764c0;border:0;border-radius:7px;color:white;padding:11px 16px;cursor:pointer}
.muted{color:#6b7890}.scroll{overflow-x:auto}.note{font-size:13px;color:#64748b}
@media(max-width:750px){.layout{display:block}nav{width:auto;display:flex;overflow:auto;padding:6px}nav a{white-space:nowrap}main{padding:15px}}
"""


def page(db, table):
    items = rows(db, f"SELECT * FROM {table} ORDER BY id DESC LIMIT 200")
    fields = TABLES[table]
    inputs = []
    for field, definition in fields.items():
        if field in {"executed_at", "created_at", "collected_at"}:
            continue
        required = "NOT NULL" in definition and "DEFAULT" not in definition
        if field == "execution_mode":
            widget = "<select name='execution_mode'><option value='manual'>Manuel</option><option value='automatic'>Otomatik</option></select>"
        elif field == "nature":
            widget = "<select name='nature'>" + "".join(f"<option>{escape(x)}</option>" for x in sorted(ALLOWED_NATURE)) + "</select>"
        elif field == "status" and table == "executions":
            widget = "<select name='status'><option value='pass'>Başarılı</option><option value='fail'>Başarısız</option><option value='inconclusive'>Belirsiz</option><option value='not_applicable'>Uygulanamaz</option></select>"
        else:
            widget = f"<input name='{field}' placeholder='{field}' {'required' if required else ''}>"
        inputs.append(widget)
    headers = "<tr>" + "".join(f"<th>{escape(k)}</th>" for k in ["id", *fields]) + "</tr>"
    body = "".join("<tr>" + "".join(f"<td>{escape(str(item.get(k) if item.get(k) is not None else ''))}</td>" for k in ["id", *fields]) + "</tr>" for item in items)
    menu = "".join(f"<a class={'active' if table == name else 'inactive'} href='/?view={name}'>{label}</a>" for name, label in LABELS.items())
    note = "<p class='note'>Kontrol ilişkileri ve kanıt eşleştirmeleri REST API üzerinden yönetilir. Bu ilk sürüm temel kayıt arayüzüdür.</p>"
    script = """<script>
document.querySelector('form').addEventListener('submit', async e=>{
e.preventDefault();let data=Object.fromEntries(new FormData(e.target));
for(let k of Object.keys(data)){if(data[k]==='')delete data[k];else if(k.endsWith('_id'))data[k]=Number(data[k]);}
let r=await fetch('/api/REPLACE',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
let v=await r.json();if(r.ok)location.reload();else alert(v.error||'Hata');
});
</script>""".replace("REPLACE", table)
    return f"<!doctype html><html lang='tr'><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>Control GRC</title><style>{STYLE}</style><header><h1>Control GRC</h1><small>Kontrol • Denetim • Kanıt • Uyum</small></header><div class='layout'><nav>{menu}</nav><main><h2>{LABELS[table]}</h2><section><h3>Yeni kayıt</h3><form>{''.join(inputs)}<button type='submit'>Kaydet</button></form>{note}</section><section><h3>Kayıtlar ({len(items)})</h3><div class='scroll'><table>{headers}{body}</table></div></section></main></div>{script}</html>"


class Handler(BaseHTTPRequestHandler):
    def respond(self, code, data, content_type="application/json; charset=utf-8"):
        raw = data.encode("utf-8") if isinstance(data, str) else json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)

    def authorized(self):
        # Require an explicit credential even on loopback; never expose anonymous writes.
        api_key = self.headers.get("X-API-Key", "")
        if KEY and api_key and hmac.compare_digest(api_key, KEY):
            return True
        authorization = self.headers.get("Authorization", "")
        if UI_USER and UI_PASSWORD and authorization.startswith("Basic "):
            try:
                credentials = base64.b64decode(authorization[6:], validate=True).decode("utf-8")
                username, password = credentials.split(":", 1)
                if hmac.compare_digest(username, UI_USER) and hmac.compare_digest(password, UI_PASSWORD):
                    return True
            except (ValueError, UnicodeDecodeError):
                pass
        self.send_response(401)
        self.send_header("WWW-Authenticate", 'Basic realm="Control GRC"')
        self.send_header("Content-Length", "0")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        return False

    def do_GET(self):
        if not self.authorized():
            return
        path = urlparse(self.path)
        parts = path.path.strip("/").split("/")
        try:
            with connect() as db:
                if path.path == "/api/health":
                    return self.respond(200, {"status": "ok"})
                if len(parts) == 4 and parts[:2] == ["api", "controls"] and parts[3] == "context":
                    result = context(db, int(parts[2]))
                    return self.respond(200 if result else 404, result or {"error": "Not found"})
                if len(parts) == 2 and parts[0] == "api" and parts[1] in TABLES:
                    return self.respond(200, rows(db, f"SELECT * FROM {parts[1]} ORDER BY id DESC LIMIT 1000"))
                if path.path in {"/", "/index.html"}:
                    from urllib.parse import parse_qs
                    table = parse_qs(path.query).get("view", ["controls"])[0]
                    if table not in TABLES:
                        table = "controls"
                    return self.respond(200, page(db, table), "text/html; charset=utf-8")
            self.respond(404, {"error": "Not found"})
        except (ValueError, sqlite3.Error) as exc:
            self.respond(400, {"error": str(exc)})

    def do_POST(self):
        if not self.authorized():
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length < 1 or length > 1024 * 1024:
                return self.respond(413, {"error": "Body must be between 1 byte and 1 MB"})
            payload = json.loads(self.rfile.read(length))
            if not isinstance(payload, dict):
                raise ValueError("JSON object required")
            parts = urlparse(self.path).path.strip("/").split("/")
            with connect() as db:
                if len(parts) == 4 and parts[:2] == ["api", "controls"] and parts[3] == "mappings":
                    control_id = int(parts[2])
                    if not context(db, control_id):
                        return self.respond(404, {"error": "Control not found"})
                    for target, table in MAPPINGS.items():
                        if target in payload:
                            db.execute(f"DELETE FROM {table} WHERE control_id=?", (control_id,))
                            mapping(db, table, "control_id", control_id, f"{TARGET_COLUMNS[target]}_id", payload[target])
                    return self.respond(200, context(db, control_id))
                if len(parts) == 2 and parts[0] == "api" and parts[1] in TABLES:
                    table = parts[1]
                    if table == "executions":
                        return self.respond(201, execute(db, payload))
                    record_id = insert(db, table, payload)
                    if table == "evidence":
                        for target in ("clauses", "processes"):
                            if target in payload:
                                mapping(db, f"evidence_{target}", "evidence_id", record_id, f"{TARGET_COLUMNS[target]}_id", payload[target])
                    if table == "audits" and "clause_ids" in payload:
                        mapping(db, "audit_clauses", "audit_id", record_id, "clause_id", payload["clause_ids"])
                    return self.respond(201, {"id": record_id})
            self.respond(404, {"error": "Not found"})
        except (ValueError, KeyError, sqlite3.Error, json.JSONDecodeError) as exc:
            self.respond(400, {"error": str(exc)})


if __name__ == "__main__":
    initialize()
    print(f"Control GRC running at http://{HOST}:{PORT}")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
