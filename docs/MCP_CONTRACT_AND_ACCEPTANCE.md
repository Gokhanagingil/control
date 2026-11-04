# KS GRC — MCP contract and acceptance checklist

The existing MCP platform is the orchestration layer. KS GRC never calls ServiceNow or Dynamics directly.

## API access

- Use \`X-API-Key: <CONTROL_API_KEY>\` for machine-to-machine access.
- Run the service on a trusted network. Initial Docker binding is **127.0.0.1:18080** on the host.
- Browser HTTP Basic authentication is a **test-only** measure. Reach the UI through an SSH tunnel or TLS-protected reverse proxy; **never** expose Basic auth over plain public HTTP.
- All dates are ISO 8601 or YYYY-MM-DD, depending on field; backend does not yet enforce date formats.
- IDs are database-generated integers. Treat mappings as many-to-many.
- This version has no automated scheduler. The MCP application schedules and invokes controls.

## Control orchestration flow

1. Fetch available controls: \`GET /api/controls\`.
2. Fetch one control and mappings: \`GET /api/controls/{id}/context\`. Read \`execution_mode\`, \`nature\`, \`frequency\`, \`method\` and \`expected_result\`.
3. Execute the query using the MCP-enabled application and its existing authorized access to ServiceNow/Dynamics.
4. Record collected evidence metadata: \`POST /api/evidence\`, or upload a binary (max 600,000 decoded bytes) to \`POST /api/evidence/upload\` with base64 JSON. Link it to relevant \`clauses\` and \`processes\`.
5. Record the check: \`POST /api/executions\`:
   \`\`\`json
   {
     "control_id": 1,
     "audit_id": 2,
     "status": "fail",
     "source": "mcp",
     "details": "Discovered server is not recorded in CMDB",
     "evidence_ids": [3],
     "severity": "high"
   }
   \`\`\`
6. \`fail\` creates a finding and returns \`{"execution_id": ..., "finding_id": ...}\`. \`pass\` does not automatically close existing findings. \`inconclusive\` / \`not_applicable\` do not create findings.
7. Inspect the immutable mappings attached to a run: \`GET /api/executions/{id}/context\`; inspect finding with \`GET /api/findings/{id}/context\`. Updating a control's current mapping will not rewrite its historical execution context.
8. Inspect evidence's past uses: \`GET /api/evidence/{id}/context\`. Original evidence hash is checked on download.

## Scope and standards

- Add the actual licensed/authorized content of ISO/IEC 20000-1 or other standards via the standards + clauses endpoints; **the application does not bundle a full licensed standard**.
- \`POST /api/audits/from-standard\` accepts \`{"name":"2026 Internal Audit","standard_id":1}\` and links all clauses *currently present* in that standard to the new audit.
- Read the captured audit scope via \`GET /api/audits/{id}/scope\`.
- Add and revise control's standard/process/objective relationships via \`POST /api/controls/{id}/mappings\` with any subset of \`clauses\`, \`processes\`, and \`objectives\` (arrays of IDs).
- Update evidence's standard/process links via \`POST /api/evidence/{id}/mappings\`.

## Acceptance cases

| Scenario | Expected result |
| --- | --- |
| No credentials, GET /api/health | HTTP 401 |
| Valid API key, GET /api/health | HTTP 200, status ok |
| Create a standard with 2 clauses, then a standard-based audit | Audit contains exactly 2 clauses |
| One control mapped to 2 clauses and 2 processes | Control context contains all four links |
| Execute a failed automatic MCP control | Execution and one linked finding created |
| Supply a related evidence ID | Control run links the evidence; evidence reuse history lists the run |
| Change mappings after an execution | Historical execution keeps its original mappings |
| Upload a binary and download it | Download matches original bytes and SHA-256 digest |
| Mark a later run as pass | The earlier finding remains open, pending a deliberate closure |
| Deploy isolated Compose project | NILES Compose, NILES DB and NILES container lifecycle unchanged |

## Known MVP limitations

- User and role tables exist but role enforcement is not implemented; UI uses separate Basic credentials for prototype use.
- Evidence file upload limit 600 KB; no malware scan, retention policy, encryption at rest, legal hold or evidence versioning.
- User-facing editing, finding remediation workflow and standards imports are limited; do not use as a certified production audit system yet.
- HTTPS/VPN access, tested restore, durable backups, and stronger identity integration are preconditions for production.
- No direct ServiceNow integration or MCP calls originate from this repository.

## Deployment

\`Deploy KS GRC (isolated)\` has both manual dispatch and a one-shot push trigger on \`.control-deploy-request\`. All seven \`CONTROL_*\` secrets must be in GitHub Actions environment \`control-grc\` or available as repository secrets. The workflow compiles Python, checks the UI JavaScript, runs unit+HTTP integration tests, builds the image, then copies only KS GRC files to \`/opt/control-grc\`.

GitHub Actions must report success and the server health check must pass before claiming the service has been deployed. The host port remains loopback-only; test from a workstation with an SSH tunnel:

\`\`\`powershell
ssh -N -L 18080:127.0.0.1:18080 root@46.224.99.150
\`\`\`

Open http://127.0.0.1:18080 in a local browser and authenticate with the configured \`CONTROL_UI_USER\` / \`CONTROL_UI_PASSWORD\`. Direct access to http://PUBLIC_IP:18080 is deliberately not enabled.
