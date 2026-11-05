"""User feedback: truthful reverse relationships and distinct audit finding groups."""
import json
from pathlib import Path
import secrets
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from urllib.request import Request, urlopen
from urllib.error import HTTPError
import app
import grc_plus
import identity


class FeedbackTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.previous=(app.DB,app.EVIDENCE_DIR,app.KEY,app.COOKIE_SECURE)
        app.DB=str(Path(self.tmp.name)/'db.sqlite');app.EVIDENCE_DIR=str(Path(self.tmp.name)/'files')
        app.KEY=secrets.token_urlsafe(24);app.COOKIE_SECURE=False;app.initialize()
        with app.connect() as db:
            ins=lambda t,**v:app.insert(db,t,v)
            self.st=ins('standards',code='TEST',name='Test standard')
            self.cl=ins('clauses',standard_id=self.st,code='1',title='Clause 1')
            self.cl2=ins('clauses',standard_id=self.st,code='2',title='Clause 2')
            self.p=ins('processes',code='CFG',name='Configuration')
            self.obj=ins('objectives',code='O1',name='Objective 1')
            self.obj2=ins('objectives',code='O2',name='Other objective')
            self.c=ins('controls',code='C1',name='First control')
            self.c2=ins('controls',code='C2',name='Second control')
            self.c3=ins('controls',code='C3',name='Out of scope')
            for cid in [self.c,self.c2]:
                db.execute('INSERT INTO control_objectives VALUES(?,?)',(cid,self.obj))
                db.execute('INSERT INTO control_clauses VALUES(?,?)',(cid,self.cl))
                db.execute('INSERT INTO control_processes VALUES(?,?)',(cid,self.p))
            db.execute('INSERT INTO control_objectives VALUES(?,?)',(self.c,self.obj2))
            db.execute('INSERT INTO control_clauses VALUES(?,?)',(self.c,self.cl2))
            self.audit=ins('audits',name='Current audit')
            self.old=ins('audits',name='Other audit')
            db.execute('INSERT INTO audit_clauses VALUES(?,?)',(self.audit,self.cl))
            db.execute('INSERT INTO audit_clauses VALUES(?,?)',(self.audit,self.cl2))
            self.run=app.execute(db,{'control_id':self.c,'audit_id':self.audit,'status':'fail'})
            self.other=app.execute(db,{'control_id':self.c,'audit_id':self.old,'status':'fail'})
            self.external=app.execute(db,{'control_id':self.c2,'status':'fail'})
            self.unrelated=app.execute(db,{'control_id':self.c3,'audit_id':self.old,'status':'fail'})
            self.closed=ins('findings',title='Closed in current audit',audit_id=self.audit,status='closed')
            self.accepted=ins('findings',title='Accepted elsewhere',audit_id=self.old,control_id=self.c,status='accepted')

    def tearDown(self):
        app.DB,app.EVIDENCE_DIR,app.KEY,app.COOKIE_SECURE=self.previous
        self.tmp.cleanup()

    def test_objective_has_direct_controls_and_deduplicated_derived_links(self):
        with app.connect() as db:
            ctx=grc_plus.objective_context(db,self.obj)
            self.assertEqual([x['id'] for x in ctx['controls']],[self.c,self.c2])
            self.assertEqual(len(ctx['clauses']),2);self.assertEqual(len(ctx['processes']),1)
            self.assertEqual(ctx['clauses'][0]['standard_code'],'TEST')
            self.assertEqual(ctx['relationship_basis']['clauses'],'via_controls')
            self.assertIsNone(grc_plus.objective_context(db,999999))

    def test_objective_mapping_preserves_other_objectives_and_historical_snapshot(self):
        with app.connect() as db:
            grc_plus.set_objective_controls(db,self.obj,[self.c2,self.c2])
            self.assertEqual(len(grc_plus.objective_context(db,self.obj)['controls']),1)
            self.assertEqual(len(grc_plus.objective_context(db,self.obj2)['controls']),1)
            history=app.execution_context(db,self.run['execution_id'])
            self.assertEqual({x['id'] for x in history['objectives']},{self.obj,self.obj2})
            cleared=grc_plus.set_objective_controls(db,self.obj,[])
            self.assertEqual(cleared['clauses'],[]);self.assertEqual(cleared['processes'],[])

    def test_invalid_objective_mapping_is_atomic(self):
        with app.connect() as db:
            for ids in [[self.c,999999],[True],['1'],None]:
                with self.assertRaises(ValueError):grc_plus.set_objective_controls(db,self.obj,ids)
                self.assertEqual(len(grc_plus.objective_context(db,self.obj)['controls']),2)

    def test_audit_groups_do_not_mix_sources_and_include_closed_current_findings(self):
        with app.connect() as db:
            ctx=grc_plus.audit_context(db,self.audit)
            self.assertEqual({f['id'] for f in ctx['findings']},{self.run['finding_id'],self.closed})
            self.assertEqual({f['id'] for f in ctx['other_open_findings']},{self.other['finding_id'],self.external['finding_id']})
            self.assertEqual(ctx['finding_summary'],{'total':2,'open':1,'other_open':2})
            self.assertEqual(len(ctx['controls']),2)
            self.assertIsNone(grc_plus.audit_context(db,999999))

    def test_legacy_finding_derives_audit_from_run_and_survives_control_remapping(self):
        with app.connect() as db:
            db.execute('UPDATE findings SET audit_id=NULL,control_id=NULL WHERE id=?',(self.run['finding_id'],))
            db.execute('DELETE FROM control_clauses WHERE control_id=?',(self.c,))
            ctx=grc_plus.audit_context(db,self.audit)
            item=next(f for f in ctx['findings'] if f['id']==self.run['finding_id'])
            self.assertEqual(item['audit_link_source'],'via_execution')
            self.assertEqual(item['control_code'],'C1')
            self.assertIn(self.other['finding_id'],[f['id'] for f in ctx['other_open_findings']])
            self.assertEqual(app.execution_context(db,self.run['execution_id'])['clauses'][0]['id'],self.cl)

    def test_audit_query_does_not_truncate_at_1000_records(self):
        with app.connect() as db:
            db.executemany('INSERT INTO findings(title,audit_id,created_at) VALUES(?,?,?)',
                [('Bulk '+str(i),self.audit,app.utcnow()) for i in range(1005)])
            self.assertEqual(len(grc_plus.audit_context(db,self.audit)['findings']),1007)

    def test_http_relationship_routes_require_auth_and_machine_key_cannot_change_links(self):
        with app.connect() as db:
            identity.provision(db,'test.operator',secrets.token_urlsafe(24))
            uid=db.execute("SELECT id FROM users WHERE username='test.operator'").fetchone()[0]
            db.execute('UPDATE users SET must_change_password=0 WHERE id=?',(uid,))
            token=identity.new_session(db,uid)
        server=ThreadingHTTPServer(('127.0.0.1',0),app.Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        base='http://127.0.0.1:'+str(server.server_port)
        def req(path,payload=None,mode='key'):
            headers={'Content-Type':'application/json'}
            if mode=='key':headers['X-API-Key']=app.KEY
            elif mode in ('session','bad-origin'):
                headers.update({'Cookie':identity.COOKIE_NAME+'='+token,'Origin':base if mode=='session' else 'https://other.invalid'})
            request=Request(base+'/api/'+path,headers=headers,data=None if payload is None else json.dumps(payload).encode())
            try:
                with urlopen(request,timeout=5) as response:return response.status,json.loads(response.read())
            except HTTPError as error:return error.code,None
        try:
            self.assertEqual(req(f'objectives/{self.obj}/context',mode='none')[0],401)
            self.assertEqual(req(f'audits/{self.audit}/context')[1]['finding_summary']['total'],2)
            self.assertEqual(req(f'objectives/{self.obj}/context')[0],200)
            self.assertEqual(req('objectives/999999/context')[0],404)
            self.assertEqual(req(f'objectives/{self.obj}/controls',{'control_ids':[]})[0],403)
            self.assertEqual(req(f'objectives/{self.obj}/controls',{'control_ids':[]},'bad-origin')[0],403)
            self.assertEqual(req(f'objectives/{self.obj}/controls',{'control_ids':[self.c]},'session')[0],200)
            self.assertEqual(req(f'objectives/{self.obj}/context')[1]['controls'][0]['id'],self.c)
        finally:
            server.shutdown();server.server_close();thread.join(5)
