"""Audit planning, lifecycle and frozen scope regressions."""
import base64
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest

import app
import grc_excel
import grc_plus as grc
import xlsx_io


class AuditWorkspaceTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.addCleanup(setattr,app,"DB",app.DB)
        self.addCleanup(setattr,app,"EVIDENCE_DIR",app.EVIDENCE_DIR)
        app.EVIDENCE_DIR=str(Path(temp.name)/"files")
        app.DB=str(Path(temp.name)/"audit.sqlite")
        app.initialize()
        self.actor=SimpleNamespace(current_user={"username":"test-auditor"})
        with app.connect() as db:
            self.one=app.insert(db,"standards",{"name":"First","code":"A"})
            self.two=app.insert(db,"standards",{"name":"Second","code":"B"})
            self.a,self.b,self.c=[app.insert(db,"clauses",{"standard_id":s,"code":c,"title":"Clause "+c})
                for s,c in ((self.one,"a"),(self.two,"b"),(self.two,"c"))]

    def create(self,db,**changes):
        return grc.save_audit(db,{"name":"Assurance","standard_ids":[self.one,self.two],
            "clause_ids":[self.a,self.b],**changes},self.actor)["id"]

    def test_multistandard_scope_is_explicit_partial_and_migrates_from_legacy(self):
        with app.connect() as db:
            audit=self.create(db,clause_ids=[self.a])
            context=grc.audit_context(db,audit)
            self.assertEqual([s["id"] for s in context["standards"]],[self.one,self.two])
            self.assertEqual([c["id"] for c in context["clauses"]],[self.a])
            self.assertEqual(context["revision"],0)
            # Simulate only the relationships available on the last deployed schema.
            db.execute("DROP TRIGGER audit_clause_parent")
            db.execute("DELETE FROM audit_standards")
        app.initialize()
        app.initialize()
        with app.connect() as db:
            self.assertEqual([s["id"] for s in app.audit_scope(db,audit)["standards"]],[self.one])

    def test_bad_scope_stale_edit_and_log(self):
        with app.connect() as db:
            audit=self.create(db)
            for st,cl in (([self.one],[self.b]),([self.one],[900]),([900],[]),([True],[]),([],["1"])):
                with self.assertRaises(ValueError):
                    grc.save_audit(db,{"name":"corrupt","expected_revision":0,"standard_ids":st,"clause_ids":cl},self.actor,audit)
                self.assertEqual(app.audit_scope(db,audit)["name"],"Assurance")
            result=grc.save_audit(db,{"audit_objective":"Test coverage","standard_ids":[self.one],
                    "clause_ids":[self.a],"expected_revision":0},self.actor,audit)
            self.assertEqual((result["revision"],result["audit_objective"]),(1,"Test coverage"))
            for bad in (False,0,None):
                with self.assertRaises(grc.StaleAudit):
                    grc.save_audit(db,{"expected_revision":bad,"scope":"stale"},self.actor,audit)
            log=db.execute("SELECT * FROM activity_log WHERE method='UPDATE' AND object_type='audits'").fetchone()
            self.assertEqual(log["actor"],"test-auditor")
            self.assertIn('"madde_çıkarılan":['+str(self.b)+']',log["description"])

    def test_lifecycle_rules_and_internal_audit(self):
        with app.connect() as db:
            audit=self.create(db,clause_ids=[self.a])
            for data in ({"status":"in_progress","actual_start":"2026-11-02"},  # missing selected standard's clause
                         {"status":"completed","actual_end":"2026-11-02"},
                         {"planned_start":"2026-03-09","planned_end":"2026-03-08"},
                         {"planned_start":"2026-02-30"}, {"planned_end":"20261102"},
                         {"status":"planned","actual_start":"2026-11-02"}, {"status":[]}):
                with self.assertRaises(ValueError):
                    grc.save_audit(db,data,self.actor,audit)
            internal=self.create(db,standard_ids=[],clause_ids=[],scope="Tedarikçi süreci")
            grc.save_audit(db,{"status":"in_progress","actual_start":"2026-11-01"},self.actor,internal)
            done=grc.save_audit(db,{"status":"completed","actual_end":"2026-11-03","conclusion":"Reviewed"},
                                self.actor,internal)
            self.assertEqual((done["status"],done["conclusion"]),("completed","Reviewed"))
            for data in ({"scope":"changed"},{"status":"in_progress","actual_end":None}):
                with self.assertRaises(ValueError):grc.save_audit(db,data,self.actor,internal)
            grc.save_audit(db,{"status":"closed"},self.actor,internal)

    def test_plan_intersection_distinguishes_outside_tests_and_freezes_on_completion(self):
        with app.connect() as db:
            audit=self.create(db,standard_ids=[self.one,self.two],clause_ids=[self.a,self.b])
            def ctl(code):
                return app.insert(db,"controls",{"code":code,"name":"Control "+code})
            planned,other,untested = map(ctl,("first","second","third"))
            db.executemany("INSERT INTO control_clauses VALUES(?,?)",
                           [(planned,self.a),(planned,self.c),(other,self.c),(untested,self.a)])
            run={"control_id":other,"audit_id":audit,"status":"fail","idempotency_key":"case-10001"}
            first=app.execute(db,run)
            app.execute(db,{"control_id":planned,"audit_id":audit,"status":"pass"})
            ctx=grc.audit_context(db,audit)
            self.assertEqual({c["id"] for c in ctx["planned_controls"]},{planned,untested})
            self.assertEqual([c["id"] for c in ctx["tested_outside_scope"]],[other])
            self.assertEqual(len(ctx["findings"]),1)
            query={"audit_id":[str(audit)]}
            result=grc.compliance(db,query)
            self.assertEqual((result["total_controls"],result["counts"]["untested"],result["clause_count"]),(2,1,2))
            filtered=grc.compliance(db,{**query,"standard_id":[str(self.two)]})
            self.assertEqual((filtered["total_controls"],filtered["clause_count"],filtered["mapped_clauses"]),(0,1,0))
            grc.save_audit(db,{"status":"completed","actual_start":"2026-11-01","actual_end":"2026-11-02"},
                           self.actor,audit)
            db.execute("DELETE FROM control_clauses")
            db.execute("UPDATE controls SET active=0")
            ctx=grc.audit_context(db,audit)
            self.assertTrue(ctx["plan_captured_at"])
            self.assertEqual(grc.compliance(db,query),result)
            self.assertEqual(app.execute(db,run)["execution_id"],first["execution_id"])
            with self.assertRaisesRegex(ValueError,"Sonuçlandırılmış"):
                app.execute(db,{**run,"idempotency_key":"case-10002"})

    def test_workbook_cannot_change_closed_scope_and_keeps_standard_only_drafts(self):
        with app.connect() as db:
            audit=self.create(db,clause_ids=[self.a,self.b],status="closed",
                    actual_start="2026-11-01",actual_end="2026-11-02")
            self.create(db,name="Draft",clause_ids=[])
            pages=xlsx_io.read_xlsx(grc_excel.export(db,"all"))
            self.assertIn(["Denetim - Standart","Draft","B"],pages["Bağlantılar"])
            pages["Bağlantılar"].append(["Denetim - Madde","Assurance","B :: c"])
            with self.assertRaisesRegex(ValueError,"Excel"):
                grc_excel.import_xlsx(db,{"content_base64":base64.b64encode(xlsx_io.make_xlsx(pages)).decode()},"all")
            self.assertEqual(len(app.audit_scope(db,audit)["clauses"]),2)

    def test_workbook_history_is_report_only_and_must_match(self):
        with app.connect() as db:
            control=app.insert(db,"controls",{"code":"CTL","name":"Control"})
            evidence=grc.save_file(db,{"title":"Snapshot","source":"manual","file_name":"snapshot.txt",
                    "content_base64":base64.b64encode(b"Observation").decode()})
            other=app.insert(db,"evidence",{"title":"Other","source":"manual"})
            app.execute(db,{"status":"fail","control_id":control,"evidence_ids":[evidence["id"]]})
            def load(pages):
                payload={"content_base64":base64.b64encode(xlsx_io.make_xlsx(pages)).decode()}
                return grc_excel.import_xlsx(db,payload,"all")
            original=xlsx_io.read_xlsx(grc_excel.export(db,"all"))
            self.assertEqual(load(original)["executions"]["skipped"],1)
            for sheet, field, replacement in (("Kontrol Sonuçları","Durum","pass"),("Kontrol Sonuçları","Kayıt No","54321"),
                                           ("Kanıtlar","SHA-256","aaaa"),("Bulgular",grc.FIELD_LABELS.get("execution_id","Execution Id"),"555")):
                pages={k:[list(row) for row in v] for k,v in original.items()}
                header=pages[sheet][0]
                pages[sheet][1][header.index(field)]=replacement
                with self.assertRaisesRegex(ValueError,"Excel"):load(pages)
            original["Bağlantılar"].append(["Kontrol Çalışması - Kanıt","1","Other :: manual"])
            with self.assertRaisesRegex(ValueError,"bağlantısı"):load(original)
            self.assertEqual(db.execute("SELECT count(*) FROM execution_evidence WHERE evidence_id=?",(other,)).fetchone()[0],0)

    def test_risk_import_resolves_portable_catalog_code_and_validates_appetite(self):
        with app.connect() as db:
            catalog=app.insert(db,"risk_catalog",{"code":"CUSTOM","title":"Custom","cause":"Power cut",
                  "risk_event":"Overheat","consequence":"Loss of service","likelihood":2,"impact":4})
            pages={"Riskler":[["Kod","Başlık","catalog_id","Kaynak katalog kodu","appetite","cause","risk_event","consequence"],
                ["R-90","Server power","987654","CUSTOM","4","Power cut","Overheat","Loss of service"]]}
            def load():
                return grc_excel.import_xlsx(db,{"content_base64":base64.b64encode(xlsx_io.make_xlsx(pages)).decode()},"risks")
            self.assertEqual(load()["risks"]["inserted"],1)
            stored=db.execute("SELECT catalog_id,appetite FROM risks WHERE code='R-90'").fetchone()
            self.assertEqual(tuple(stored),(catalog,4))
            pages["Riskler"][1][0]="R-91"
            pages["Riskler"][1][3]=""
            with self.assertRaisesRegex(ValueError,"katalog kodu"):load()
            pages["Riskler"][0].append("Durum")
            pages["Riskler"][1][3]="CUSTOM"
            for state in ("accepted","closed"):
                pages["Riskler"][1][8:]=[state]
                with self.assertRaisesRegex(ValueError,"karar"):load()

