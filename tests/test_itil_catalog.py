"""ITIL draft catalog controls are meaningful, linked and never auto-passed."""
import os
import tempfile
import unittest

import app
import seed_reference
import seed_itil
import grc_plus

class ITILCatalogTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.old=(app.DB,app.EVIDENCE_DIR)
        app.DB=os.path.join(self.tmp.name,"itil-test.db")
        app.EVIDENCE_DIR=os.path.join(self.tmp.name,"files")
        seed_reference.seed()

    def tearDown(self):
        app.DB,app.EVIDENCE_DIR=self.old
        self.tmp.cleanup()

    def test_200_draft_controls_and_preserve_existing_results(self):
        result=seed_itil.run()
        self.assertFalse(result["skipped"])
        self.assertEqual(result["summary"]["controls"],200)
        self.assertGreaterEqual(result["summary"]["processes"],5)
        repeat=seed_itil.run()
        self.assertTrue(repeat["skipped"])
        with app.connect() as db:
            drafts=db.execute("SELECT COUNT(*) AS n FROM controls WHERE code LIKE 'KS-ITIL-%' AND active=0").fetchone()["n"]
            self.assertEqual(drafts,200)
            self.assertEqual(db.execute("SELECT COUNT(*) AS n FROM executions").fetchone()["n"],32)
            self.assertEqual(db.execute("SELECT COUNT(*) AS n FROM findings").fetchone()["n"],18)
            self.assertEqual(db.execute("SELECT COUNT(*) AS n FROM controls WHERE code LIKE 'KS-DEMO-%'").fetchone()["n"],28)
            self.assertGreater(db.execute("""SELECT COUNT(*) AS n FROM control_clauses
                JOIN controls ON controls.id=control_clauses.control_id
                WHERE controls.code LIKE 'KS-ITIL-%'""").fetchone()["n"],200)
            stats=grc_plus.compliance(db,{})
            self.assertEqual(stats["total_controls"],28)

    def test_controls_have_method_owner_expected_and_links(self):
        seed_itil.run()
        with app.connect() as db:
            items=app.rows(db,"SELECT * FROM controls WHERE code LIKE 'KS-ITIL-%'")
            self.assertEqual(len(items),200)
            for item in items:
                self.assertTrue(item["method"])
                self.assertTrue(item["expected_result"])
                self.assertTrue(item["owner"])
                self.assertIn(item["execution_mode"],("manual","automatic"))
                ctx=app.context(db,item["id"])
                self.assertGreater(len(ctx["processes"]),0)
                self.assertGreater(len(ctx["objectives"]),0)
                self.assertGreater(len(ctx["clauses"]),0)

if __name__=="__main__":
    unittest.main()
