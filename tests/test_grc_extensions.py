"""Security, relational GRC, XLSX and compliance regression suite."""
import base64
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
import zipfile

import app
import grc_plus
import grc_excel
import xlsx_io


class ModelTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.old_db,self.old_files=app.DB,app.EVIDENCE_DIR
        app.DB=os.path.join(self.temp.name,"grc.db")
        app.EVIDENCE_DIR=os.path.join(self.temp.name,"evidence-files")
        app.initialize()

    def tearDown(self):
        app.DB,self.old_db=self.old_db,app.DB
        app.EVIDENCE_DIR=self.old_files
        self.temp.cleanup()

    def fixtures(self):
        with app.connect() as db:
            standard=app.insert(db,"standards",{"code":"T-ISO","name":"Test standard","version":"1"})
            other=app.insert(db,"standards",{"code":"T-OTHER","name":"Cross standard","version":"1"})
            clause=app.insert(db,"clauses",{"standard_id":standard,"code":"8.1","title":"Configuration"})
            other_clause=app.insert(db,"clauses",{"standard_id":other,"code":"4.1","title":"Configuration"})
            p=app.insert(db,"processes",{"code":"CONFIG","name":"Konfigürasyon yönetimi"})
            c1=app.insert(db,"controls",{"code":"T1","name":"Kontrol 1","frequency":"daily"})
            c2=app.insert(db,"controls",{"code":"T2","name":"Kontrol 2","frequency":"weekly"})
            c3=app.insert(db,"controls",{"code":"T3","name":"Kontrol 3","frequency":"monthly"})
            for cid in (c1,c2,c3):
                db.execute("INSERT INTO control_clauses(control_id,clause_id) VALUES (?,?)",(cid,clause))
                db.execute("INSERT INTO control_processes(control_id,process_id) VALUES (?,?)",(cid,p))
            db.execute("INSERT INTO control_clauses(control_id,clause_id) VALUES (?,?)",(c1,other_clause))
            aid=app.insert(db,"audits",{"name":"ISO test"})
            db.execute("INSERT INTO audit_clauses(audit_id,clause_id) VALUES (?,?)",(aid,clause))
            app.execute(db,{"control_id":c1,"status":"pass","source":"manual","audit_id":aid})
            app.execute(db,{"control_id":c2,"status":"fail","source":"mcp","audit_id":aid})
            return standard,other,p,(c1,c2,c3),aid

    def test_compliance_truthful_denominators_and_cross_framework(self):
        st,other,p,ids,audit=self.fixtures()
        with app.connect() as db:
            report=grc_plus.compliance(db,{"standard_id":[str(st)]})
            self.assertEqual(report["total_controls"],3)
            self.assertEqual(report["completed"],2)
            self.assertEqual(report["counts"]["pass"],1)
            self.assertEqual(report["counts"]["fail"],1)
            self.assertEqual(report["counts"]["untested"],1)
            self.assertEqual(report["completion_pct"],66.7)
            self.assertEqual(report["pass_pct"],50.0)
            self.assertEqual(report["indicative_pct"],33.3)
            self.assertEqual(report["clause_count"],1)
            cross=grc_plus.compliance(db,{"standard_id":[str(other)]})
            self.assertEqual(cross["total_controls"],1)
            self.assertEqual(cross["pass_pct"],100.0)
            self.assertEqual(cross["evaluation_type"],"Çapraz kapsam ön değerlendirmesi")
            audit_report=grc_plus.compliance(db,{"audit_id":[str(audit)]})
            self.assertEqual(audit_report["completed"],2)
            self.assertEqual(audit_report["total_controls"],3)
            self.assertEqual(grc_plus.compliance(db,{"process_id":[str(p)]})["total_controls"],3)
            empty=grc_plus.compliance(db,{"process_id":["99999"]})
            self.assertIsNone(empty["pass_pct"])
            self.assertIsNone(empty["completion_pct"])

    def test_evidence_links_versions_and_file_safety(self):
        st,_,_,ids,audit=self.fixtures()
        original=b"%PDF-1.7\n% GRC audit example\n"
        with app.connect() as db:
            document=grc_plus.save_file(db,{"title":"Denetim PDF","source":"manual",
                "file_name":"denetim-raporu.pdf",
                "content_base64":base64.b64encode(original).decode(),
                "audits":[audit],"controls":[ids[0]],"clauses":[],
                "period_start":"2026-10-01","period_end":"2026-10-31"})
            eid=document["id"]
            ctx=grc_plus.extended_context(db,eid)
            self.assertEqual(ctx["audits"][0]["id"],audit)
            self.assertEqual(ctx["controls"][0]["id"],ids[0])
            self.assertEqual(ctx["file_name"],"denetim-raporu.pdf")
            self.assertEqual(grc_plus.fetch_file(db,eid)[0],original)
            version=grc_plus.save_file(db,{
                "file_name":"rapor-v2.pdf",
                "content_base64":base64.b64encode(b"%PDF-2.0\nNew report").decode()},eid)
            self.assertEqual(version["version"],2)
            self.assertEqual(grc_plus.fetch_file(db,eid,1)[0],original)
            self.assertEqual(grc_plus.fetch_file(db,eid,2)[0],b"%PDF-2.0\nNew report")
        with self.assertRaises(ValueError):
            grc_plus._valid_file("../etc/passwd",b"data")
        with self.assertRaises(ValueError):
            grc_plus._valid_file("code.exe",b"MZ")
        with self.assertRaises(ValueError):
            grc_plus._valid_file("fake.pdf",b"invalid")
        with self.assertRaises(ValueError):
            grc_plus._valid_file("image.png",b"<script>alert(1)</script>")

    def test_enums_and_risks(self):
        with app.connect() as db:
            with self.assertRaises(ValueError):
                app.insert(db,"controls",{"code":"BAD","name":"Bad","frequency":"every_two_hours"})
            with self.assertRaises(ValueError):
                grc_plus.validate_record("risks",{"code":"R1","title":"Risk","likelihood":6})
            with self.assertRaises(ValueError):
                grc_plus.validate_record("evidence",{"source":"malware"})
            risk=app.insert(db,"risks",{"code":"R-1","title":"Yetkisiz CI","created_at":app.utcnow()})
            self.assertGreater(risk,0)

    def test_xlsx_roundtrip_and_formula_rejection(self):
        st,*_=self.fixtures()
        with app.connect() as db:
            data=grc_excel.export(db,"all")
            pages=xlsx_io.read_xlsx(data)
            self.assertIn("Standartlar",pages)
            self.assertIn("Kontrol Bağlantıları" if False else "Bağlantılar",pages)
            self.assertEqual(len(pages["Kontroller"]),4)
            self.assertIn("Standart Maddeleri",pages)
            single=grc_excel.export(db,"controls")
            self.assertEqual(len(xlsx_io.read_xlsx(single)["Kontroller"]),4)
            result=grc_excel.import_xlsx(db,{"content_base64":base64.b64encode(data).decode()},"all")
            self.assertEqual(result["controls"]["skipped"],3)
        malicious=xlsx_io.make_xlsx({"Kontroller":[["Kod","Ad"],["=HYPERLINK(\"https://evil\",\"test\")","Test"]]})
        text=xlsx_io.read_xlsx(malicious)["Kontroller"][1][0]
        self.assertTrue(text.startswith("'="))
        zipped=io.BytesIO()
        with zipfile.ZipFile(zipped,"w") as z:
            z.writestr("xl/workbook.xml","X"*44_000_000)
        with self.assertRaises(ValueError):
            xlsx_io.read_xlsx(zipped.getvalue())

    def test_original_data_survives_migrations(self):
        with app.connect() as db:
            prior=app.insert(db,"evidence",{"title":"Legacy evidence","source":"manual"})
        app.initialize()
        with app.connect() as db:
            self.assertEqual(db.execute("SELECT title FROM evidence WHERE id=?",(prior,)).fetchone()["title"],"Legacy evidence")
            self.assertIn("file_name", [r["name"] for r in db.execute("PRAGMA table_info(evidence)")])
            self.assertIn("activity_log", [r["name"] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")])


if __name__=="__main__":
    unittest.main()
