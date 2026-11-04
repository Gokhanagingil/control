# KS GRC

Lightweight, Turkish-first GRC MVP. Python 3.11+ standard library only, SQLite persistence, no direct ServiceNow connection.

## Run

```bash
python app.py
```

Open http://localhost:8080. Set `CONTROL_API_KEY`. The browser now authenticates against a real `users` database table with salted PBKDF2-SHA256 password hashes, 12-hour HttpOnly sessions, and an enforced first-login password change. Set `CONTROL_UI_USER` to choose the initial username. No role distinctions are enforced in this MVP. Use `CONTROL_DB` to override the SQLite path.

## Architecture

- Authority documents and clauses, processes, control objectives, controls
- Many-to-many control mappings to clauses, processes and objectives
- Manual/automatic execution classification, preventive/detective/corrective control nature
- Control executions, reusable evidence metadata, findings, audits
- REST JSON endpoints for the existing MCP-enabled orchestration application
- Small evidence attachments (up to 600 KB per file) can be stored in the private persistent volume using base64 JSON, and downloaded with SHA-256 integrity verification. Larger attachments, retention controls, malware scanning, and a browser upload widget remain future work.

## API

- `GET /api/health`
- `GET /api/{standards,clauses,processes,objectives,controls,audits,findings,evidence,executions}`
- `POST /api/{standards,clauses,processes,objectives,controls,audits,findings,evidence,executions}`
- `POST /api/standards/{id}/clauses/import` with `{"csv_base64":"..."}`. Upload UTF-8 CSV (header: `code,title,description,parent_code`) up to 700 KB / 1,000 clauses, safely skipping existing codes. See `examples/clauses_demo.csv` (synthetic example, not ISO text).
- `PATCH /api/audits/{id}` / `PATCH /api/findings/{id}` / `PATCH /api/controls/{id}` to update allowed fields. Findings cannot be remapped to a different control via PATCH.
- `GET /api/controls/{id}/context`
- `POST /api/audits/from-standard` with `{"name":"Audit 1","standard_id":1}`; links all current clauses of the standard to the audit
- `GET /api/audits/{id}/scope`
- `GET /api/evidence/{id}/context` for linked clauses, processes and historical executions
- `POST /api/evidence/upload` with `{"title":"CMDB screenshot","content_base64":"...","clauses":[1],"processes":[1]}` (max 600 KB decoded)
- `GET /api/evidence/{id}/download`
- `POST /api/controls/{id}/mappings` with `{"clauses":[1],"processes":[2],"objectives":[3]}`
- `POST /api/executions` with `{"control_id":1,"status":"fail","source":"mcp","details":"...","evidence_ids":[1]}`

POST execution with status `fail` automatically creates a finding, linked to the execution. Findings inherit the control's mapped requirements and processes through its relationships. Passing status `pass` does not close prior findings.

Use header `X-API-Key` for MCP API calls. The browser uses user records and password-backed sessions; it does not read the old `CONTROL_UI_PASSWORD` secret. This is a prototype; add a trusted TLS certificate, backups, and role controls before production use.

## First browser session

The server bind is intentionally `127.0.0.1:18080` to avoid transmitting Basic credentials over public HTTP. In **Windows PowerShell on your own PC** (not the remote Ubuntu shell), run:

```powershell
ssh -N -L 18080:127.0.0.1:18080 root@46.224.99.150
```

Keep that terminal open, then visit `http://127.0.0.1:18080` and sign in with `CONTROL_UI_USER` / `CONTROL_UI_PASSWORD`. All future production publishing must be HTTPS-backed and have stronger identity controls. No direct public IP:port exposure exists yet.

## First login

The isolated deployment action creates one database-backed user named by `CONTROL_UI_USER` (initially `grcadmin`) and generates a one-time temporary password on the server. It does NOT use the unreadable GitHub `CONTROL_UI_PASSWORD` secret.

To view the new credentials without exposing them in GitHub Actions logs, SSH into the Ubuntu host and run:

```bash
sudo cat /opt/control-grc/.first-login
```

The file is root-readable only. Do not paste credentials into chat. On the first sign-in the user is forced to set a new password. Delete this temporary file afterward: `sudo rm -f /opt/control-grc/.first-login`.

If a reset is ever needed, run as root on the server (redirect output to a private file, never to CI logs):

```bash
umask 077
cd /opt/control-grc
docker compose -p control-grc exec -T app python /app/bootstrap.py reset grcadmin --force > /opt/control-grc/.first-login
```

See `DEPLOYMENT.md` for network access restrictions. User and role tables are present, but all signed-in users have the same application capabilities in this MVP.

## Örnek veri kataloğu (staging)

`seed/catalog.json`: ISO/IEC 20000-1:2018 (75 madde) ve CIS Controls v8.1 (18 aile + 51 seçili Safeguard); madde metinleri değil, özgün Türkçe kısa konu etiketleri.

`seed/operational_scenarios.json`: 28 gerçekçi ancak tamamen **SİMÜLASYON** kontrolü, 19 süreç, 10 hedef, 3 denetim, 28 indirilebilir JSON kanıtı, 32 kontrol çalışması ve otomatik bulgular. ServiceNow veya Dynamics'e herhangi bir canlı sorgu yapılmaz. Gerçek üretim verileriyle karıştırılmamalıdır.

```bash
python seed_reference.py --apply
```

Bu içeri aktarma işleminde `seed_runs` işareti kullanılır; aynı paket iki kez çalıştırıldığında veri çoğaltılmaz ve kullanıcı tarafından oluşturulan kontrol kayıtları üzerine yazılmaz. Test amaçlıdır.
