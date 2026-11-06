"""Authenticated ZAP DAST. Accepts a scanner executable, never a target URL."""
import argparse
import collections
import json
import os
from pathlib import Path
import secrets
import ssl
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from http.server import ThreadingHTTPServer
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
# Seed the Sites tree from known authenticated application paths. No crawler or IdP traffic.
PATHS = ["/", "/login", "/ksgrc.js", "/architecture.svg", "/api/architecture/data", "/api/me", "/api/admin/summary",
         "/api/controls", "/api/controls/1/context", "/api/objectives/1/context",
         "/api/audits", "/api/audits/1/context", "/api/audits/1/evidence",
         "/api/risks", "/api/risk_catalog", "/api/findings", "/api/evidence/1/context",
         "/api/evidence/1/download", "/api/compliance?standard_id=1&audit_id=1",
         "/api/excel/export?table=controls"]
ACTIVE = {6: "Path traversal", 40012: "Reflected XSS", 40018: "SQL injection"}


def run(scanner, output, temp):
    tenant = str(uuid.uuid4())
    os.environ.update(CONTROL_DB=str(temp / "test.db"), CONTROL_EVIDENCE_DIR=str(temp / "files"),
                      CONTROL_COOKIE_SECURE="1", CONTROL_AUTH_MODE="entra",
                      CONTROL_ENTRA_TENANT_ID=tenant, CONTROL_ENTRA_CLIENT_ID=str(uuid.uuid4()),
                      CONTROL_API_KEY=secrets.token_urlsafe(32), CONTROL_ENTRA_AUTH_CONTEXT="c1",
                      CONTROL_ENTRA_REDIRECT_URI="https://127.0.0.1/auth/entra/callback",
                      CONTROL_ENTRA_CLIENT_SECRET=secrets.token_urlsafe(32))
    import app
    import entra_auth
    import identity
    import seed_reference
    seed_reference.seed()
    with app.connect() as db:
        uid = identity.entra_account(db, tenant, str(uuid.uuid4()), "DAST fixture")
        session = identity.new_session(db, uid, scope=app.ENTRA.config.session_scope,
                                       role=entra_auth.ADMIN, expires=int(time.time()) + 900)
    cookie = identity.ENTERPRISE_COOKIE + "=" + session
    responses = collections.Counter()
    active = collections.Counter()
    lock = threading.Lock()

    class Target(app.Handler):
        def log_message(self, *args):
            pass

        def log_request(self, code="-", size="-"):
            with lock:
                if self.headers.get("Cookie") == cookie:
                    responses[(self.command, self.path, int(code))] += 1
                    rule = self.headers.get("X-ZAP-Scan-ID")
                    if rule:
                        active[rule] += 1

    with ThreadingHTTPServer(("127.0.0.1", 0), Target) as target:
        url = f"https://127.0.0.1:{target.server_port}"
        app.ENTRA = entra_auth.configure({**os.environ, "CONTROL_ENTRA_REDIRECT_URI": url + "/auth/entra/callback"})
        # The disposable app is behind TLS; no company keys/URLs are accepted.
        subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "1",
                        "-subj", "/CN=127.0.0.1", "-addext", "subjectAltName=IP:127.0.0.1",
                        "-keyout", str(temp / "tls.key"), "-out", str(temp / "tls.crt")],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(temp / "tls.crt", temp / "tls.key")
        target.socket = context.wrap_socket(target.socket, server_side=True)
        threading.Thread(target=target.serve_forever, daemon=True).start()
        scan = {"env": {"contexts": [{"name": "disposable", "urls": [url],
                                      "excludePaths": [url + "/auth/.*"]}],
                        "parameters": {"failOnError": True, "failOnWarning": False}},
                "jobs": [
                    {"type": "passiveScan-config", "parameters": {"scanOnlyInScope": True}},
                    {"type": "requestor", "requests": [
                        *[{"url": url + p, "responseCode": 200} for p in PATHS],
                        {"url": url + "/api/evidence", "method": "POST", "responseCode": 201,
                         "headers": ["Content-Type: application/json", "Origin: " + url],
                         "data": json.dumps({"title": "DAST disposable evidence", "source": "manual"})}]},
                    {"type": "activeScan", "parameters": {"context": "disposable", "threadPerHost": 2,
                      "maxRuleDurationInMins": 1, "maxScanDurationInMins": 3,
                      "injectPluginIdInHeader": True},
                     "policyDefinition": {"defaultThreshold": "Off", "defaultStrength": "Low",
                                          "rules": [{"id": k, "threshold": "Medium"} for k in ACTIVE]}},
                    {"type": "passiveScan-wait", "parameters": {"maxDuration": 2}},
                    {"type": "report", "parameters": {"template": "traditional-json", "reportDir": str(temp),
                                                      "reportFile": "zap.json"}, "sites": [url]}
                ]}
        (temp / "plan.yaml").write_text(json.dumps(scan))
        try:
            result = subprocess.run(
                [str(scanner.resolve()), "-Xmx768m", "-silent", "-cmd", "-host", "127.0.0.1",
                 "-port", "0", "-dir", str(temp / "zap"), "-autorun", str(temp / "plan.yaml")],
                env={**{k: v for k, v in os.environ.items() if not k.startswith("CONTROL_")},
                     "ZAP_AUTH_HEADER": "Cookie", "ZAP_AUTH_HEADER_VALUE": cookie,
                     "ZAP_AUTH_HEADER_SITE": "127.0.0.1"},
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=480)
        finally:
            target.shutdown()
    # Persist metadata only. Do not artifact scanner sessions, cookie headers, query values or bodies.
    if result.returncode not in (0, 2) or not (temp / "zap.json").exists():
        lines = result.stdout.replace(cookie, "[redacted]").splitlines()
        raise SystemExit("ZAP failed:\n" + "\n".join(lines[-25:]))
    raw = json.loads((temp / "zap.json").read_text())
    alerts = []
    for site in raw["site"]:
        if site["@name"] != url:
            raise ValueError("Unexpected DAST site")
        for a in site["alerts"]:
            alerts.append({"id": a["alertRef"], "name": a["name"], "risk": int(a["riskcode"]),
                           "confidence": int(a["confidence"]), "instances": len(a["instances"]),
                           "paths": sorted({urlsplit(i["uri"]).path for i in a["instances"]})})
    summary = {"scanner": "ZAP " + raw["@version"], "environment": "disposable HTTPS localhost",
               "identity": "synthetic server-issued Entra admin session; no tenant sign-in",
               "requested_paths": PATHS, "authenticated_200_paths": [p for p in PATHS if responses["GET", p, 200]],
               "authenticated_evidence_post_201": bool(responses["POST", "/api/evidence", 201]),
               "authenticated_requests": sum(responses.values()), "active_rule_requests": dict(active),
               "alerts": alerts}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n")
    print("Authenticated paths:", len(summary["authenticated_200_paths"]), "/", len(PATHS),
          "requests:", summary["authenticated_requests"], "active:", dict(active))
    print("Alert types by risk (3=High, 2=Medium, 1=Low, 0=Info):", dict(collections.Counter(a["risk"] for a in alerts)))
    if (len(summary["authenticated_200_paths"]) != len(PATHS)
            or not {str(i) for i in ACTIVE} <= set(active)
            or not summary["authenticated_evidence_post_201"]
            or any(a["risk"] >= 2 or a["id"] in {"10035-1", "10036-2"} for a in alerts)):
        raise SystemExit("DAST severity, transport/header regression, or coverage gate failed; inspect the report")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("zap_sh", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    # Isolate the process even when started from an administrator shell.
    for key in list(os.environ):
        if key.startswith("CONTROL_") or key.startswith("ZAP_AUTH_"):
            del os.environ[key]
    with tempfile.TemporaryDirectory(prefix="ks-grc-dast-") as tmp:
        run(args.zap_sh, args.output, Path(tmp))
