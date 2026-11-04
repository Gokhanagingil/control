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

    def test_roles_seed_idempotent(self):
        app.initialize()
        with app.connect() as db:
            roles = app.rows(db, "SELECT * FROM roles")
            self.assertEqual({r["code"] for r in roles}, {"ADMIN", "AUDITOR", "VIEWER"})

    def test_reject_invalid_execution(self):
        with app.connect() as db:
            with self.assertRaises(ValueError):
                app.execute(db, {"control_id": 999, "status": "fail"})
            control = app.insert(db, "controls", {"code": "C2", "name": "Test"})
            with self.assertRaises(ValueError):
                app.execute(db, {"control_id": control, "status": "invalid"})


if __name__ == "__main__":
    unittest.main()
