"""Hostile HTTP probes against an isolated enterprise-mode listener and synthetic SQLite DB."""
import http.client
import json
import os
import secrets
import tempfile
import threading
import time
import unittest
from http.server import ThreadingHTTPServer
from unittest.mock import patch

import app
import entra_auth
import identity
from test_entra import ENV, OID, ORIGIN, TENANT


class EnterpriseBoundary(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        cls.key = secrets.token_urlsafe(32)
        provider = entra_auth.configure(ENV)
        cls.settings = patch.multiple(app, ENTRA=provider, COOKIE_SECURE=True, KEY=cls.key,
                                    DB=os.path.join(cls.temp.name, "probe.db"))
        cls.settings.start()
        cls.addClassCleanup(cls.settings.stop)
        app.initialize()
        with app.connect() as db:
            uid = identity.entra_account(db, TENANT, OID, "Fixture")
            cls.cookie = identity.ENTERPRISE_COOKIE + "=" + identity.new_session(
                db, uid, scope=provider.config.session_scope, role=entra_auth.AUDITOR, expires=int(time.time()+300))
            cls.username = db.execute("SELECT username FROM users WHERE id=?", (uid,)).fetchone()[0]
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.addClassCleanup(cls.server.server_close)
        cls.addClassCleanup(cls.server.shutdown)

    def request(self, method, path, headers=None, data=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=3)
        defaults = {"Host":"grc.example.test", "Content-Type":"application/json"}
        try:
            conn.request(method, path, body=json.dumps(data).encode() if data is not None else None,
                         headers={**defaults, **(headers or {})})
            r = conn.getresponse()
            return r.status, r.headers, r.read()
        finally:
            conn.close()

    def test_anonymous_and_header_impersonation_fail(self):
        for path in ("/api/me","/api/controls","/api/audits/1/context","/api/risks","/api/risks/1/context",
                     "/api/risk_catalog","/api/evidence/1/download","/api/admin/summary","/api/excel/export"):
            for headers in ({}, {"X-Forwarded-User":"admin","X-MS-CLIENT-PRINCIPAL-NAME":"test-admin",
                                 "X-Auth-Request-Groups":"KS.GRC.Admin","Authorization":"Bearer pretend",
                                 "Cookie":"control_grc_session=pretend-token; role=KS.GRC.Admin"}):
                with self.subTest(path=path, spoof=bool(headers)):
                    self.assertEqual(self.request("GET",path,headers)[0],401)
        self.assertEqual(self.request("POST","/api/risks/1/assessments",data={"rationale":"x"})[0],401)

    def test_browser_cross_origin_cors_and_administration(self):
        hostile = "https://outside.example.test"
        status, headers, _ = self.request("GET","/api/risk_catalog",{"Cookie":self.cookie,"Origin":hostile})
        self.assertEqual(status,200)
        self.assertNotIn("Access-Control-Allow-Origin",headers)
        self.assertNotIn("Access-Control-Allow-Credentials",headers)
        _, headers, _ = self.request("OPTIONS","/api/risks",{"Origin":hostile,
                                                "Access-Control-Request-Method":"POST"})
        self.assertNotIn("Access-Control-Allow-Origin",headers)
        for origin in (None, hostile, "null", ORIGIN+".outside.test", "http://grc.example.test"):
            h = {"Cookie":self.cookie}
            if origin:
                h["Origin"] = origin
            for method,path in (("POST","/api/risks"),("PATCH","/api/risks/1"),("POST","/api/logout")):
                with self.subTest(origin=origin,method=method,path=path):
                    self.assertEqual(self.request(method,path,h,{})[0],403)
        for path in ("/api/admin/summary","/api/excel/export?table=all","/api/admin/users/1"):
            h = {"Cookie":self.cookie, "Origin":ORIGIN,"X-Role":"KS.GRC.Admin","X-Forwarded-For":"127.0.0.1"}
            with self.subTest(path=path):
                self.assertEqual(self.request("GET",path,h)[0],403)

    def test_machine_principal_cannot_read_or_change_risk_decisions(self):
        for method,path in (("GET","/api/risks/1/context"),("GET","/api/risks"),("GET","/api/admin/summary"),
                            ("GET","/api/excel/export?table=all"),("POST","/api/risks/1/assessments"),
                            ("POST","/api/risks/1/controls"),("PATCH","/api/risks/1"),
                            ("POST","/api/admin/users"),("GET","/")):
            with self.subTest(method=method,path=path):
                status, _, _ = self.request(method,path,{"X-API-Key":self.key},{} if method!="GET" else None)
                self.assertEqual(status,403)

    def test_risk_assessment_identity_and_score_are_server_owned(self):
        h = {"Cookie":self.cookie,"Origin":ORIGIN}
        data = {"code":"SEC-PROBE","title":"Synthetic exposure","owner":"GRC","entity_name":"fixture",
                "cause":"c","risk_event":"e","consequence":"i","appetite":1,"review_date":"2030-01-01",
                "likelihood":4,"impact":4}
        status, _, body = self.request("POST","/api/risks", h, data)
        self.assertEqual(status,201)
        rid = json.loads(body)["id"]
        path = "/api/risks/"+str(rid)
        proposal = {"assessor":"forged-admin","residual":0,"rationale":"Synthetic rationale","credits":[]}
        self.assertEqual(self.request("POST",path+"/assessments", h, proposal)[0],201)
        status, _, body = self.request("GET",path+"/context", h)
        self.assertEqual(status,200)
        result = json.loads(body)["assessments"][0]
        self.assertEqual(result["assessor"],self.username)
        self.assertEqual(result["residual"],16)
        proposal["credits"] = [{"control_id":98765,"run_id":1,"weight":"high","effectiveness":"effective"}]
        self.assertEqual(self.request("POST",path+"/assessments",h,proposal)[0],400)
        self.assertEqual(self.request("PATCH",path,h,{"assessor":"forged","residual":0})[0],400)
        status, _, body = self.request("GET",path+"/context", h)
        self.assertEqual(len(json.loads(body)["assessments"]),1)
