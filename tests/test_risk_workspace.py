import base64
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

    def test_decisions_require_assessment_and_review_and_closed_actions(self):
        previous=dict(self.db.execute('SELECT * FROM risks WHERE id=?',(self.rid,)).fetchone())
        accept={**previous,'status':'accepted','response_strategy':'accept','treatment':'Yetkili risk sahibi takip edecek.'}
        with self.assertRaises(ValueError):risk.decision(self.db,self.rid,previous,accept)
        self.evaluate([])
        risk.decision(self.db,self.rid,previous,accept)
        for data in ({'review_date':'2000-01-01'},{'impact':1}):
            with self.assertRaises(ValueError):risk.decision(self.db,self.rid,previous,{**accept,**data})
        app.insert(self.db,'actions',{'code':'A1','title':'Kurtarma testi','risk_id':self.rid,'created_at':app.utcnow()})
        with self.assertRaises(ValueError):risk.decision(self.db,self.rid,previous,{**accept,'status':'closed'})
