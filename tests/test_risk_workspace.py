import base64
import sqlite3
import tempfile
import unittest
from datetime import date,timedelta
from pathlib import Path

import app
import grc_plus
import risk_management as risk


class RiskWorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        original=app.DB,app.EVIDENCE_DIR
        self.addCleanup(lambda:setattr(app,'DB',original[0]))
        self.addCleanup(lambda:setattr(app,'EVIDENCE_DIR',original[1]))
        app.DB=str(Path(self.tmp.name)/'risk.db')
        app.EVIDENCE_DIR=str(Path(self.tmp.name)/'evidence')
        app.initialize()
        self.db=app.connect()
        self.addCleanup(self.db.close)
        self.template=dict(self.db.execute("SELECT * FROM risk_catalog WHERE code='RESTORE'").fetchone())
        self.data={**self.template,'catalog_id':self.template['id'],'code':'R-001',
                   'entity_name':'Ödeme platformu','owner':'Hizmet sahibi','likelihood':4,'impact':5,
                   'appetite':10,'review_date':(date.today()+timedelta(days=7)).isoformat(),'created_at':app.utcnow()}
        self.rid=app.insert(self.db,'risks',self.data)
        self.cid=app.insert(self.db,'controls',{'code':'C-1','name':'Yeniden yükleme provası'})
        self.db.execute('INSERT INTO control_risks VALUES(?,?)',(self.cid,self.rid))

    def evaluate(self,credits):
        return risk.assess(self.db,self.rid,{'credits':credits,'rationale':'Örnekleme kapsamı incelendi.'},'auditor',app.utcnow())

    def evidence(self):
        return grc_plus.save_file(self.db,{'title':'Kurtarma raporu','file_name':'rapor.txt',
                 'content_base64':base64.b64encode(b'fixture').decode()})['id']

    def test_catalog_is_a_reusable_snapshot_and_never_creates_exposures(self):
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM risks').fetchone()[0],1)
        self.db.execute("UPDATE risk_catalog SET cause='Yeni neden' WHERE id=?",(self.template['id'],))
        self.assertEqual(self.db.execute('SELECT cause FROM risks').fetchone()[0],self.template['cause'])
        result=self.evaluate([])
        self.assertEqual((result['inherent'],result['residual'],result['above_appetite']),(20,20,True))

    def test_effectiveness_requires_current_versioned_evidence_and_keeps_history(self):
        eid=self.evidence()
        run=app.execute(self.db,{'control_id':self.cid,'status':'pass','source':'manual','evidence_ids':[eid]})['execution_id']
        credit={'control_id':self.cid,'run_id':run,'weight':'high','effectiveness':'partial'}
        self.assertEqual(self.evaluate([credit])['residual'],14)
        self.db.execute("UPDATE evidence SET expires_at='2000-01-01' WHERE id=?",(eid,))
        with self.assertRaises(ValueError):self.evaluate([credit])
        self.db.execute("UPDATE evidence SET expires_at=NULL WHERE id=?",(eid,))
        app.execute(self.db,{'control_id':self.cid,'status':'fail','source':'manual'})
        with self.assertRaises(ValueError):self.evaluate([credit])
        history=risk.context(self.db,self.rid)['assessments']
        self.assertEqual(len(history),1)
        self.assertEqual(history[0]['snapshot']['credits'][0]['run_id'],run)
        self.assertEqual(history[0]['assessor'],'auditor')
        self.assertEqual(history[0]['residual'],14)

    def test_failed_untested_unrelated_and_unsubstantiated_credits(self):
        blank=app.insert(self.db,'evidence',{'title':'Dosyasız'})
        run=app.execute(self.db,{'control_id':self.cid,'status':'pass','source':'manual','evidence_ids':[blank]})['execution_id']
        credit={'control_id':self.cid,'run_id':run,'weight':'medium','effectiveness':'effective'}
        for value in (credit,{**credit,'weight':[]},{**credit,'control_id':9191}):
            with self.subTest(value=value),self.assertRaises(ValueError):self.evaluate([value])
        self.assertEqual(risk.context(self.db,self.rid)['assessments'],[])

    def test_decision_guards_and_explicit_independent_exception(self):
        previous=dict(self.db.execute('SELECT * FROM risks WHERE id=?',(self.rid,)).fetchone())
        accept={**previous,'status':'accepted','response_strategy':'accept'}
        options=dict(actor="auditor",role="KS.GRC.Admin",at=app.utcnow(),
                     details={"decision_rationale":"Management approved","exception_rationale":"Temporary exposure","assessment_id":1})
        def decide(proposal,**changes):
            risk.decision(self.db,self.rid,previous,proposal,**{**options,**changes})
        with self.assertRaises(ValueError):decide(accept)
        self.evaluate([])
        with self.assertRaises(risk.ApprovalDenied):decide(accept)  # same assessor
        with self.assertRaises(risk.ApprovalDenied):decide(accept,actor="other",role="KS.GRC.Auditor")
        for fields in ({"assessment_id":1,"decision_rationale":"ok"},
                       {"assessment_id":1234,"decision_rationale":"ok","exception_rationale":"why"}):
            with self.assertRaises(ValueError):decide(accept,actor="other",details=fields)
        for changes in ({'review_date':'2000-01-01'},{'impact':1}):
            with self.assertRaises(ValueError):decide({**accept,**changes},actor='other')
        app.insert(self.db,'actions',{'code':'A1','title':'Kurtarma testi','risk_id':self.rid,'created_at':app.utcnow()})
        with self.assertRaises(ValueError):decide({**accept,'status':'closed'},actor='other')
        self.assertEqual(risk.context(self.db,self.rid)["decisions"],[])
        decide(accept,actor="approving-admin")
        self.db.execute("UPDATE risks SET status='accepted',response_strategy='accept' WHERE id=?",(self.rid,))
        ctx=risk.context(self.db,self.rid)
        decision=ctx["decisions"][0]
        self.assertEqual((decision["actor"],decision["actor_role"],decision["residual"],decision["appetite"]),
                         ("approving-admin","KS.GRC.Admin",20,10))
        self.assertEqual((decision["from_status"],decision["to_status"],decision["assessment_id"],
                decision["exception_rationale"]),("open","accepted",1,"Temporary exposure"))
        with self.assertRaises(ValueError):self.evaluate([])
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute("DELETE FROM control_risks WHERE risk_id=?",(self.rid,))
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute("UPDATE actions SET risk_id=NULL WHERE code='A1'")
        for table in ("risk_decisions","risk_assessments"):
            with self.assertRaises(sqlite3.IntegrityError):self.db.execute(f"DELETE FROM {table}")
            with self.assertRaises(sqlite3.IntegrityError):self.db.execute(f"UPDATE {table} SET id=id")
        previous=accept
        reopen={**accept,"status":"open"}
        decide(reopen,details={"decision_rationale":"New incident"})
        self.db.execute("UPDATE risks SET status='open' WHERE id=?",(self.rid,))
        previous=reopen
        with self.assertRaisesRegex(ValueError,"yeni değerlendirme"):decide(accept,actor="approving-admin")
        self.assertEqual(len(risk.context(self.db,self.rid)["decisions"]),2)

    def test_closure_within_appetite_records_rationale_assessor_and_review(self):
        self.db.execute("UPDATE risks SET appetite=20 WHERE id=?",(self.rid,))
        assessment=self.evaluate([])
        row=dict(self.db.execute("SELECT * FROM risks WHERE id=?",(self.rid,)).fetchone())
        risk.decision(self.db,self.rid,row,{**row,"status":"closed"},actor="owner",
                      role="KS.GRC.Auditor",at="2026-11-06T09:00:00Z",
                      details={"assessment_id":assessment["id"],"decision_rationale":"Service retired"})
        decision=risk.context(self.db,self.rid)["decisions"][0]
        self.assertEqual((decision["actor"],decision["decided_at"],decision["rationale"],decision["assessment_id"]),
                         ("owner","2026-11-06T09:00:00Z","Service retired",assessment["id"]))
        self.assertIsNone(decision["exception_rationale"])
