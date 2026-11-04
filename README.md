# Control GRC

Lightweight, Turkish-first GRC MVP. Python 3.11+ standard library only, SQLite persistence, no direct ServiceNow connection.

## Run

```bash
python app.py
```

Open http://localhost:8080. Set `CONTROL_API_KEY` in the environment before exposing the application beyond localhost. Use `CONTROL_DB` to override the SQLite path.

## Architecture

- Authority documents and clauses, processes, control objectives, controls
- Many-to-many control mappings to clauses, processes and objectives
- Manual/automatic execution classification, preventive/detective/corrective control nature
- Control executions, reusable evidence metadata, findings, audits
- REST JSON endpoints for the existing MCP-enabled orchestration application
- Evidence attachments are intentionally NOT implemented in this first bootstrap; evidence metadata and external references are supported.

## API

- `GET /api/health`
- `GET /api/{standards,clauses,processes,objectives,controls,audits,findings,evidence,executions}`
- `POST /api/{standards,clauses,processes,objectives,controls,audits,findings,evidence,executions}`
- `GET /api/controls/{id}/context`
- `POST /api/controls/{id}/mappings` with `{"clauses":[1],"processes":[2],"objectives":[3]}`
- `POST /api/executions` with `{"control_id":1,"status":"fail","source":"mcp","details":"...","evidence_ids":[1]}`

POST execution with status `fail` automatically creates a finding, linked to the execution. Findings inherit the control's mapped requirements and processes through its relationships. Passing status `pass` does not close prior findings.

Use header `X-API-Key` if `CONTROL_API_KEY` is configured. This is a bootstrap prototype; add authentication, HTTPS, backups and role controls before production use.
