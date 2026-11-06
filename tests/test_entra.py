"""Adversarial Entra web sign-in tests. RSA keys, accounts and tokens are synthetic."""
import base64
import hashlib
import http.client
import io
import json
import os
import tempfile
import threading
import time
import unittest
from contextlib import redirect_stderr
from http.server import ThreadingHTTPServer
from unittest.mock import patch
from urllib.parse import parse_qs, urlencode, urlsplit

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa

import app
import entra_auth
import identity

TENANT = "10000000-0000-4000-8000-000000000001"
CLIENT = "20000000-0000-4000-8000-000000000002"
OID = "30000000-0000-4000-8000-000000000003"
ORIGIN = "https://grc.example.test"
ENV = dict(CONTROL_AUTH_MODE="entra", CONTROL_COOKIE_SECURE="1",
           CONTROL_ENTRA_TENANT_ID=TENANT, CONTROL_ENTRA_CLIENT_ID=CLIENT,
           CONTROL_ENTRA_CLIENT_SECRET="synthetic-client-secret-only",
           CONTROL_ENTRA_REDIRECT_URI=ORIGIN + entra_auth.CALLBACK, CONTROL_ENTRA_AUTH_CONTEXT="c7")


class EntraTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        cls.public = jwt.algorithms.RSAAlgorithm.to_jwk(cls.private.public_key(), as_dict=True)
        cls.public.update(kid="fixture-key", use="sig")

    def setUp(self):
        self.provider = entra_auth.configure(ENV)
        signing = patch.object(self.provider.jwks, "fetch_data", return_value={"keys": [self.public]})
        signing.start()
        self.addCleanup(signing.stop)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        app_settings = patch.multiple(app, ENTRA=self.provider, COOKIE_SECURE=True,
                                      DB=os.path.join(self.temp.name, "test.db"))
        app_settings.start()
        self.addCleanup(app_settings.stop)
        app.initialize()

    def token(self, nonce, **overrides):
        now = int(time.time())
        claims = dict(iss=self.provider.config.issuer, aud=CLIENT, sub="user", ver="2.0", oid=OID,
                      tid=TENANT, nonce=nonce, iat=now, nbf=now-1, exp=now+5000,
                      roles=[entra_auth.AUDITOR], acrs=["c7"], name="Kurumsal denetçi")
        claims.update(overrides)
        return jwt.encode(claims, self.private, algorithm="RS256", headers={"kid": "fixture-key"})

    def test_startup_rejects_incomplete_or_ambiguous_identity_config(self):
        for key, value in [("CONTROL_AUTH_MODE", "entraa"), ("CONTROL_AUTH_MODE", "local"),
                           ("CONTROL_COOKIE_SECURE", "0"), ("CONTROL_ENTRA_AUTH_CONTEXT", ""),
                           ("CONTROL_ENTRA_TENANT_ID", "common"), ("CONTROL_ENTRA_CLIENT_ID", ""),
                           ("CONTROL_ENTRA_CLIENT_SECRET_FILE", "/unknown"), ("CONTROL_ENTRA_CLIENT_SECRET", ""),
                           ("CONTROL_ENTRA_REDIRECT_URI", "http://example.org/auth/entra/callback"),
                           ("CONTROL_ENTRA_REDIRECT_URI", "https://expected@attacker/auth/entra/callback")]:
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                entra_auth.configure({**ENV, key: value})

    def test_wrong_signatures_and_algorithms_are_rejected(self):
        claims = jwt.decode(self.token("test-nonce"), options={"verify_signature": False})
        attacker = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        for alg, key in [("none", None), ("HS256", b"X"*32), ("RS256", attacker)]:
            token = jwt.encode(claims, key, algorithm=alg, headers={"kid": "fixture-key"})
            with self.subTest(algorithm=alg), self.assertRaises(entra_auth.Denied):
                self.provider.verify(token, "test-nonce")

    def test_signed_tokens_without_required_claims_or_assignment_are_rejected(self):
        now = int(time.time())
        for field, value in [("iss", "https://other"), ("tid", CLIENT), ("aud", TENANT), ("aud", [CLIENT]),
                             ("azp", TENANT), ("sub", ""), ("ver", "1.0"), ("oid", "user@example.test"),
                             ("exp", now-20), ("nbf", now+120), ("iat", now+120), ("roles", []),
                             ("roles", "KS.GRC.Admin"), ("acrs", ["c1"]), ("acrs", "c7"),
                             ("nonce", "wrong")]:
            with self.subTest(field=field, value=value), self.assertRaises(entra_auth.Denied):
                self.provider.verify(self.token("n", **{field: value}) if field != "nonce"
                                     else self.token(value), "n")

    def test_callback_is_bound_to_tenant_browser_pkce_and_single_use_state(self):
        destination, cookie = self.provider.begin()
        params = parse_qs(urlsplit(destination).query)
        self.assertEqual(urlsplit(destination).netloc, "login.microsoftonline.com")
        self.assertIn(TENANT, urlsplit(destination).path)
        self.assertEqual(params["scope"], ["openid profile"])
        self.assertEqual(params["code_challenge_method"], ["S256"])
        self.assertEqual(json.loads(params["claims"][0])["id_token"]["acrs"]["value"], "c7")
        self.assertIn("SameSite=Lax", cookie)
        self.assertIn("Secure", cookie)
        self.assertIn("HttpOnly", cookie)
        header = cookie.split(";")[0]
        query = urlencode({"state": params["state"][0], "code": "test-code"})
        _, other = self.provider.begin()
        for body, browser in [(query, ""), (query, other.split(";")[0]), (query+"&state=x", header),
                              (query+"&code=duplicate", header), ("state=other&code=x", header)]:
            with self.assertRaises(entra_auth.Denied):
                self.provider.finish(body, browser)
        def exchange(code, verifier):
            self.assertEqual(code, "test-code")
            digest = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
            self.assertEqual(digest, params["code_challenge"][0])
            return self.token(params["nonce"][0])
        with patch.object(self.provider, "exchange", side_effect=exchange) as exchange_mock:
            oid, role, _, display = self.provider.finish(query, header)
            self.assertEqual((oid, role, display), (OID, entra_auth.AUDITOR, "Kurumsal denetçi"))
            with self.assertRaises(entra_auth.Denied):
                self.provider.finish(query, header)
            self.assertEqual(exchange_mock.call_count, 1)

    def test_expired_and_tampered_flow_cookie_is_rejected(self):
        destination, cookie = self.provider.begin()
        query = urlencode({"state":parse_qs(urlsplit(destination).query)["state"][0], "code":"x"})
        with patch("time.time", return_value=time.time()+601), self.assertRaises(entra_auth.Denied):
            self.provider.finish(query, cookie.split(";")[0])
        with self.assertRaises(entra_auth.Denied):
            self.provider.finish(query, cookie.split(";")[0]+"X")

    def test_oidc_exchange_pins_destination_and_uses_no_redirects(self):
        response = io.BytesIO(json.dumps({"id_token": "synthetic"}).encode())
        with patch("entra_auth.build_opener") as opener:
            opener.return_value.open.return_value = response
            self.assertEqual(self.provider.exchange("code123", "test-verifier"), "synthetic")
            self.assertIs(opener.call_args.args[0], entra_auth.NoRedirect)
            req = opener.return_value.open.call_args.args[0]
            self.assertEqual(req.full_url, self.provider.config.endpoint+"/token")
            payload = parse_qs(req.data.decode())
            self.assertEqual(payload["code_verifier"], ["test-verifier"])
            self.assertEqual(payload["redirect_uri"], [ENV["CONTROL_ENTRA_REDIRECT_URI"]])
            self.assertEqual(payload["client_id"], [CLIENT])

    def test_http_success_and_denials_in_enterprise_mode(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        def request(path, method="GET", cookie="", host="grc.example.test", origin=ORIGIN):
            conn = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=3)
            try:
                conn.request(method, path, body=b"{}" if method=="POST" else None,
                             headers={"Host": host, "Cookie": cookie, "Origin":origin, "Content-Type":"application/json"})
                response = conn.getresponse()
                return response.status, dict(response.getheaders()), response.read()
            finally:
                conn.close()
        with app.connect() as db:
            identity.provision(db, "local", "synthetic-only-password")
            uid = db.execute("SELECT id FROM users WHERE username='local'").fetchone()[0]
            old_cookie = identity.COOKIE_NAME+"="+identity.new_session(db, uid)
        self.assertEqual(request("/api/me", cookie=old_cookie)[0],401)
        self.assertEqual(request("/api/login","POST")[0],403)
        self.assertEqual(request("/api/change-password","POST")[0],403)
        self.assertEqual(request("/auth/entra/start",host="evil.example.test")[0],400)
        self.assertNotIn(b'type="password"',request("/login")[2])

        def login(role, expected_status):
            code, head, _ = request("/auth/entra/start")
            self.assertEqual(code,303)
            dest = parse_qs(urlsplit(head["Location"]).query)
            query = urlencode({"state":dest["state"][0],"code":"test-nonlogged-authorization-code"})
            with patch.object(self.provider,"exchange",return_value=self.token(dest["nonce"][0],roles=[role])):
                status, headers, _ = request(entra_auth.CALLBACK+"?"+query,cookie=head["Set-Cookie"].split(";")[0])
            self.assertEqual(status,expected_status)
            return headers.get("Set-Cookie","").split(";")[0]

        log = io.StringIO()
        with redirect_stderr(log):
            auditor = login(entra_auth.AUDITOR, 200)
        self.assertNotIn("test-nonlogged-authorization-code",log.getvalue())
        self.assertEqual(request("/api/me",cookie=auditor)[0],200)
        self.assertEqual(request("/api/admin/summary",cookie=auditor)[0],403)
        self.assertEqual(request("/api/excel/export",cookie=auditor)[0],403)
        self.assertEqual(request("/api/logout","POST",cookie=auditor,origin="https://other.test")[0],403)
        admin = login(entra_auth.ADMIN, 200)
        self.assertEqual(request("/api/me",cookie=auditor)[0],401)
        self.assertEqual(request("/api/admin/summary",cookie=admin)[0],200)
        self.assertEqual(request("/api/admin/users","POST",cookie=admin)[0],403)
        with app.connect() as db:
            row = db.execute("SELECT u.id,u.password_hash FROM users u JOIN entra_subjects e ON e.user_id=u.id").fetchone()
            self.assertNotEqual(row["id"],uid)
            self.assertIsNone(row["password_hash"])
            db.execute("UPDATE users SET is_active=0 WHERE id=?",(row["id"],))
        self.assertEqual(request("/api/me",cookie=admin)[0],401)
        self.assertFalse(login(entra_auth.ADMIN,403))
