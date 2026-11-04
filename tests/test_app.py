import os
import tempfile
import unittest

import app


class ControlTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        app.DB = os.path.join(self.tmp.name, "test.db")
        app.initialize()

    def tearDown(self):
        self.tmp.cleanup()

    def test_control_execution_and_many_to_many(self):
        with app.connect() as db:
            standard = app.insert(db, "standards", {"code": "ISO20000", "name": "ISO/IEC 20000-1"})
            clause = app.insert(db, "clauses", {"standard_id": standard, "code": "8.2", "title": "Configuration management"})
            process = app.insert(db, "processes", {"code": "CFG", "name": "Configuration Management"})
            objective = app.insert(db, "objectives", {"code": "CO1", "name": "All servers recorded"})
            control = app.insert(db, "controls", {"code": "C1", "name": "Unregistered servers", "execution_mode": "automatic"})
            for target, table in app.MAPPINGS.items():
                ids = {"clauses": [clause], "processes": [process], "objectives": [objective]}[target]
                app.mapping(db, table, "control_id", control, app.TARGET_COLUMNS[target] + "_id", ids)
            ctx = app.context(db, control)
            self.assertEqual(ctx["clauses"][0]["id"], clause)
            self.assertEqual(ctx["processes"][0]["id"], process)
            self.assertEqual(ctx["objectives"][0]["id"], objective)
            evidence = app.insert(db, "evidence", {"title": "CMDB scan", "reference_url": "urn:example:scan:1"})
            result = app.execute(db, {"control_id": control, "status": "fail", "source": "mcp", "details": "One server missing", "evidence_ids": [evidence]})
            self.assertIsNotNone(result["finding_id"])
            self.assertEqual(len(app.rows(db, "SELECT * FROM execution_evidence")), 1)
            self.assertEqual(len(app.rows(db, "SELECT * FROM findings")), 1)
            passed = app.execute(db, {"control_id": control, "status": "pass", "source": "mcp"})
            self.assertIsNone(passed["finding_id"])
            self.assertEqual(len(app.rows(db, "SELECT * FROM findings")), 1)

    def test_audit_scope_and_evidence_history(self):
        with app.connect() as db:
            standard = app.insert(db, "standards", {"code": "ISO", "name": "Example"})
            c1 = app.insert(db, "clauses", {"standard_id": standard, "code": "1", "title": "First"})
            c2 = app.insert(db, "clauses", {"standard_id": standard, "code": "2", "title": "Second"})
            audit = app.insert(db, "audits", {"name": "Example audit"})
            app.mapping(db, "audit_clauses", "audit_id", audit, "clause_id", [c1, c2])
            self.assertEqual(len(app.audit_scope(db, audit)["clauses"]), 2)
            control = app.insert(db, "controls", {"code": "T", "name": "Test"})
            evidence = app.insert(db, "evidence", {"title": "Log reference"})
            app.mapping(db, "evidence_clauses", "evidence_id", evidence, "clause_id", [c1, c2])
            app.execute(db, {"control_id": control, "audit_id": audit, "status": "pass", "evidence_ids": [evidence]})
            app.execute(db, {"control_id": control, "status": "pass", "evidence_ids": [evidence]})
            history = app.evidence_context(db, evidence)
            self.assertEqual(len(history["clauses"]), 2)
            self.assertEqual(len(history["executions"]), 2)

    def test_roles_seed_idempotent(self):
        app.initialize()
        with app.connect() as db:
            roles = app.rows(db, "SELECT * FROM roles")
            self.assertEqual({r["code"] for r in roles}, {"ADMIN", "AUDITOR", "VIEWER"})

    def test_evidence_integrity_and_persistence(self):
        import hashlib
        from pathlib import Path
        binary = b"example evidence"
        with app.connect() as db:
            evidence_id = app.insert(db, "evidence", {
                "title": "Immutable test evidence",
                "hash_sha256": hashlib.sha256(binary).hexdigest()
            })
            folder = Path(self.tmp.name) / "evidence-files"
            folder.mkdir()
            (folder / str(evidence_id)).write_bytes(binary)
            metadata = app.rows(db, "SELECT hash_sha256 FROM evidence WHERE id=?", (evidence_id,))[0]
            self.assertEqual(hashlib.sha256((folder / str(evidence_id)).read_bytes()).hexdigest(), metadata["hash_sha256"])
            self.assertNotEqual(hashlib.sha256(b"tampered").hexdigest(), metadata["hash_sha256"])

    def test_reject_invalid_execution(self):
        with app.connect() as db:
            with self.assertRaises(ValueError):
                app.execute(db, {"control_id": 999, "status": "fail"})
            control = app.insert(db, "controls", {"code": "C2", "name": "Test"})
            with self.assertRaises(ValueError):
                app.execute(db, {"control_id": control, "status": "invalid"})


if __name__ == "__main__":
    unittest.main()
