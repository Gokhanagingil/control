"""Reference seed integration/regression: realistic cross-standards UAT paths."""
import hashlib
import os
from pathlib import Path
import tempfile
import unittest

import app
import seed_reference


class ReferenceSeedTests(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.old_db = app.DB
        self.old_files = app.EVIDENCE_DIR
        app.DB = os.path.join(self.root.name, "uat.db")
        app.EVIDENCE_DIR = os.path.join(self.root.name, "evidence")
        app.initialize()

    def tearDown(self):
        app.DB = self.old_db
        app.EVIDENCE_DIR = self.old_files
        self.root.cleanup()

    def test_data_catalog_and_idempotency(self):
        result = seed_reference.seed()
        summary = result["summary"]
        self.assertFalse(result["skipped"])
        self.assertEqual(summary["standards"], 2)
        self.assertEqual(summary["clauses"], 144)
        self.assertEqual(summary["processes"], 19)
        self.assertEqual(summary["objectives"], 10)
        self.assertEqual(summary["controls"], 28)
        self.assertEqual(summary["audits"], 3)
        self.assertEqual(summary["evidence"], 28)
        self.assertEqual(summary["executions"], 32)
        self.assertGreaterEqual(summary["findings"], 12)
        repeat = seed_reference.seed()
        self.assertTrue(repeat["skipped"])
        self.assertEqual(repeat["summary"], summary)
        with app.connect() as db:
            self.assertEqual(len(app.rows(db, "SELECT * FROM controls WHERE code LIKE 'KS-DEMO-%'")), 28)
            self.assertEqual(len(app.rows(db, "SELECT * FROM users")), 0)
            self.assertEqual(len(app.rows(db, "SELECT * FROM standards")), 2)

    def test_audit_scope_and_multi_framework_control(self):
        seed_reference.seed()
        with app.connect() as db:
            control_id = app.rows(db, "SELECT id FROM controls WHERE code='KS-DEMO-CTL-001'")[0]["id"]
            ctx = app.context(db, control_id)
            self.assertEqual(len(ctx["processes"]), 3)
            self.assertEqual(len(ctx["objectives"]), 2)
            self.assertGreaterEqual(len(ctx["clauses"]), 5)
            iso_id = db.execute("SELECT id FROM audits WHERE name LIKE '%20000-1%'").fetchone()["id"]
            iso_scope = app.audit_scope(db, iso_id)
            self.assertEqual(len(iso_scope["clauses"]), 75)
            cis_id = db.execute("SELECT id FROM audits WHERE name LIKE '%CIS Controls%'").fetchone()["id"]
            self.assertEqual(len(app.audit_scope(db, cis_id)["clauses"]), 69)

    def test_evidence_files_and_cross_audit_history(self):
        seed_reference.seed()
        with app.connect() as db:
            evidence = db.execute("SELECT id,hash_sha256 FROM evidence WHERE title LIKE '%KS-DEMO-CTL-001%'").fetchone()
            evidence_file = Path(app.EVIDENCE_DIR) / str(evidence["id"])
            self.assertTrue(evidence_file.is_file())
            raw = evidence_file.read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(), evidence["hash_sha256"])
            content = raw.decode("utf-8")
            self.assertIn("SYNTHETIC_TEST_ONLY", content)
            self.assertIn("ServiceNow", content.lower().replace("servicenow", "ServiceNow"))
            usage = app.evidence_context(db, evidence["id"])
            self.assertGreaterEqual(len(usage["executions"]), 2)
            self.assertGreaterEqual(len(usage["clauses"]), 4)
            self.assertEqual(len(usage["processes"]), 3)

    def test_non_pilot_data_is_never_overwritten(self):
        app.initialize()
        with app.connect() as db:
            custom = app.insert(db, "controls", {"code": "OWN-CTL-1", "name": "Gerçek kurum kontrolü"})
            self.assertGreater(custom, 0)
        seed_reference.seed()
        with app.connect() as db:
            custom_again = db.execute("SELECT name FROM controls WHERE id=?", (custom,)).fetchone()
            self.assertEqual(custom_again["name"], "Gerçek kurum kontrolü")


if __name__ == "__main__":
    unittest.main()
