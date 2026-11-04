"""HTTP API smoke tests for MCP integration and basic security."""
import base64
import json
import os
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import app


class HTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old = (app.DB, app.EVIDENCE_DIR, app.KEY, app.UI_USER, app.UI_PASSWORD)
        cls.temp = tempfile.TemporaryDirectory()
        app.DB = os.path.join(cls.temp.name, "control.db")
        app.EVIDENCE_DIR = os.path.join(cls.temp.name, "files")
        app.KEY = "unit-test-api-key"
        app.UI_USER = "test"
        app.UI_PASSWORD = "different-test-password"
        app.initialize()
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f"http://127.0.0.1:{cls.server.server_address[1]}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)
        app.DB, app.EVIDENCE_DIR, app.KEY, app.UI_USER, app.UI_PASSWORD = cls.old
        cls.temp.cleanup()

    def request(self, path, payload=None, *, key=True, method=None):
        body = None if payload is None else json.dumps(payload).encode()
        headers = {"Content-Type": "application/json"}
        if key:
            headers["X-API-Key"] = app.KEY
        req = Request(
            self.base + "/api/" + path,
            data=body,
            headers=headers,
            method=method or ("POST" if payload is not None else "GET")
        )
        try:
            with urlopen(req, timeout=8) as response:
                body = response.read()
                if response.headers.get_content_type() == "application/json":
                    return response.status, json.loads(body)
                return response.status, body
        except HTTPError as error:
            return error.code, error.read().decode()

    def test_authorization_and_html(self):
        code, _ = self.request("health", key=False)
        self.assertEqual(code, 401)
        code, data = self.request("health")
        self.assertEqual((code, data["status"]), (200, "ok"))
        req = Request(self.base + "/", headers={
            "Authorization": "Basic " + base64.b64encode(b"test:different-test-password").decode()
        })
        with urlopen(req, timeout=8) as response:
            html = response.read().decode()
            self.assertEqual(response.status, 200)
            self.assertIn("Control GRC", html)
            self.assertIn("Standart Maddeleri", html)

    def test_complete_mcp_audit_flow(self):
        code, standard = self.request("standards", {"code": "DEMO-TEST", "name": "Example standard"})
        self.assertEqual(code, 201)
        sid = standard["id"]
        clauses = []
        for code_value in ("8.1", "8.2"):
            status, record = self.request("clauses", {"standard_id": sid, "code": code_value, "title": "Requirement " + code_value})
            self.assertEqual(status, 201)
            clauses.append(record["id"])
        _, process = self.request("processes", {"code": "CMDB", "name": "Configuration management"})
        _, objective = self.request("objectives", {"code": "OBJ-CMDB", "name": "Register all hosts"})
        _, control = self.request("controls", {
            "code": "CTL-CMDB", "name": "Discover unregistered servers",
            "execution_mode": "automatic", "nature": "detective",
            "frequency": "daily", "method": "MCP discovery query"
        })
        cid = control["id"]
        status, mappings = self.request(f"controls/{cid}/mappings", {
            "clauses": clauses, "processes": [process["id"]], "objectives": [objective["id"]]
        })
        self.assertEqual(status, 200)
        self.assertEqual(len(mappings["clauses"]), 2)
        status, audit = self.request("audits/from-standard", {"standard_id": sid, "name": "Audit test"})
        self.assertEqual((status, audit["clause_count"]), (201, 2))
        aid = audit["audit_id"]
        status, scoped = self.request(f"audits/{aid}/scope")
        self.assertEqual(len(scoped["clauses"]), 2)
        binary = b"CMDB host discovery evidence: server-example-01"
        status, evidence = self.request("evidence/upload", {
            "title": "CMDB discovery", "content_base64": base64.b64encode(binary).decode(),
            "clauses": clauses, "processes": [process["id"]], "source": "mcp"
        })
        self.assertEqual(status, 201)
        eid = evidence["id"]
        status, downloaded = self.request(f"evidence/{eid}/download")
        self.assertEqual(downloaded, binary)
        status, failure = self.request("executions", {
            "control_id": cid, "audit_id": aid, "status": "fail",
            "source": "mcp", "details": "One server missing from CMDB", "evidence_ids": [eid]
        })
        self.assertEqual(status, 201)
        self.assertIsNotNone(failure["finding_id"])
        status, finding_context = self.request(f"findings/{failure['finding_id']}/context")
        self.assertEqual(status, 200)
        self.assertEqual(len(finding_context["execution"]["clauses"]), 2)
        self.assertEqual(len(finding_context["execution"]["processes"]), 1)
        self.assertEqual(len(finding_context["execution"]["evidence"]), 1)
        # Removing the current mapping cannot rewrite historical audit execution context.
        status, _ = self.request(f"controls/{cid}/mappings", {"clauses": [], "processes": [], "objectives": []})
        self.assertEqual(status, 200)
        status, history = self.request(f"executions/{failure['execution_id']}/context")
        self.assertEqual(status, 200)
        self.assertEqual(len(history["clauses"]), 2)
        self.assertEqual(len(history["processes"]), 1)
        status, evidence_context = self.request(f"evidence/{eid}/context")
        self.assertEqual(status, 200)
        self.assertEqual(len(evidence_context["clauses"]), 2)
        self.assertEqual(len(evidence_context["executions"]), 1)

    def test_bulk_standard_csv_import_is_idempotent(self):
        status, standard = self.request("standards", {"code": "BULK-ISO", "name": "Authorized authority document"})
        self.assertEqual(status, 201)
        sid = standard["id"]
        csv_bytes = b"code,title,description,parent_code\n9,Top-level requirement,Description,\n9.1,Child requirement,Detail,9\n"
        encoded = base64.b64encode(csv_bytes).decode()
        status, result = self.request(f"standards/{sid}/clauses/import", {"csv_base64": encoded})
        self.assertEqual((status, result["imported"], result["total"]), (201, 2, 2))
        status, repeat = self.request(f"standards/{sid}/clauses/import", {"csv_base64": encoded})
        self.assertEqual((status, repeat["imported"], repeat["skipped"]), (201, 0, 2))
        status, audit = self.request("audits/from-standard", {"standard_id": sid, "name": "CSV audit"})
        self.assertEqual((status, audit["clause_count"]), (201, 2))
        status, scope = self.request(f"audits/{audit['audit_id']}/scope")
        self.assertEqual({c["code"] for c in scope["clauses"]}, {"9", "9.1"})

    def test_invalid_evidence_and_invalid_control(self):
        code, _ = self.request("evidence/upload", {
            "title": "Bad file", "content_base64": "&&not-valid-base64"
        })
        self.assertEqual(code, 400)
        code, _ = self.request("executions", {"control_id": 98765432, "status": "fail"})
        self.assertEqual(code, 400)


if __name__ == "__main__":
    unittest.main()
