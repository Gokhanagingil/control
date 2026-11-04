# Control GRC

Lightweight, Turkish-first GRC MVP. Python 3.11+ standard library only, SQLite persistence, no direct ServiceNow connection.

## Run

```bash
python app.py
```

Open http://localhost:8080. Set `CONTROL_API_KEY` and separate `CONTROL_UI_USER` / `CONTROL_UI_PASSWORD` credentials. No anonymous access is allowed. Never expose HTTP Basic credentials over unencrypted public HTTP. Use `CONTROL_DB` to override the SQLite path.

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
- `GET /api/controls/{id}/context`
- `POST /api/audits/from-standard` with `{"name":"Audit 1","standard_id":1}`; links all current clauses of the standard to the audit
- `GET /api/audits/{id}/scope`
- `GET /api/evidence/{id}/context` for linked clauses, processes and historical executions
- `POST /api/evidence/upload` with `{"title":"CMDB screenshot","content_base64":"...","clauses":[1],"processes":[1]}` (max 600 KB decoded)
- `GET /api/evidence/{id}/download`
- `POST /api/controls/{id}/mappings` with `{"clauses":[1],"processes":[2],"objectives":[3]}`
- `POST /api/executions` with `{"control_id":1,"status":"fail","source":"mcp","details":"...","evidence_ids":[1]}`

POST execution with status `fail` automatically creates a finding, linked to the execution. Findings inherit the control's mapped requirements and processes through its relationships. Passing status `pass` does not close prior findings.

Use header `X-API-Key` for MCP API calls. The browser uses HTTP Basic authentication with `CONTROL_UI_USER` and `CONTROL_UI_PASSWORD`. This is a bootstrap prototype; add authentication, HTTPS, backups and role controls before production use.
