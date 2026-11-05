"""MCP retry safety, immutable evidence, legacy upgrades and invalid input."""
import base64
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import app
import execution_service
import grc_plus


class ReleaseAcceptance(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.old=(app.DB,app.EVIDENCE_DIR)
        app.DB=str(Path(self.tmp.name)/'app.db')
        app.EVIDENCE_DIR=str(Path(self.tmp.name)/'files')
        app.initialize()
        with app.connect() as db:
            self.cid=app.insert(db,'controls',{'code':'UAT-AUTO','name':'Test kontrolü','execution_mode':'automatic'})

    def tearDown(self):
        app.DB,app.EVIDENCE_DIR=self.old
        self.tmp.cleanup()

    def evidence(self,db,content=b'original'):
        return grc_plus.save_file(db,{'title':'UAT kanıt','file_name':'uat.txt',
            'content_base64':base64.b64encode(content).decode(),'source':'mcp'})['id']

    def test_retry_is_one_execution_and_one_finding(self):
        payload={'control_id':self.cid,'status':'fail','source':'mcp','idempotency_key':'uat-repeat-0001'}
        with app.connect() as db:
            first=app.execute(db,payload)
        with app.connect() as db:
            repeat=app.execute(db,payload)
            self.assertTrue(repeat['replayed'])
            self.assertEqual(first['execution_id'],repeat['execution_id'])
            self.assertEqual(db.execute('SELECT count(*) FROM executions').fetchone()[0],1)
            self.assertEqual(db.execute('SELECT count(*) FROM findings').fetchone()[0],1)
            with self.assertRaises(execution_service.Conflict):
                app.execute(db,{**payload,'status':'pass'})

    def test_snapshot_keeps_original_definition_and_evidence_version(self):
        with app.connect() as db:
            eid=self.evidence(db)
            r=app.execute(db,{'control_id':self.cid,'status':'pass','evidence_ids':[eid]})
            grc_plus.save_file(db,{'file_name':'uat-v2.txt','content_base64':base64.b64encode(b'changed').decode()},eid)
            db.execute('UPDATE controls SET name=? WHERE id=?',('Renamed',self.cid))
            context=app.execution_context(db,r['execution_id'])
            self.assertEqual(context['definition_snapshot']['name'],'Test kontrolü')
            self.assertEqual(context['evidence_versions'][0]['version'],1)
            self.assertEqual(context['evidence_versions'][0]['sha256'],hashlib.sha256(b'original').hexdigest())
            self.assertEqual(grc_plus.fetch_file(db,eid,1)[0],b'original')

    def test_legacy_file_stays_downloadable_after_new_version(self):
        with app.connect() as db:
            eid=app.insert(db,'evidence',{'title':'Legacy','hash_sha256':hashlib.sha256(b'legacy').hexdigest()})
            Path(app.EVIDENCE_DIR).mkdir()
            (Path(app.EVIDENCE_DIR)/str(eid)).write_bytes(b'legacy')
            result=grc_plus.save_file(db,{'file_name':'updated.txt','content_base64':base64.b64encode(b'new').decode()},eid)
            self.assertEqual(result['version'],2)
            self.assertEqual(grc_plus.fetch_file(db,eid,1)[0],b'legacy')
            self.assertEqual(grc_plus.fetch_file(db,eid,2)[0],b'new')

    def test_incomplete_collection_cannot_pass_or_create_finding(self):
        with app.connect() as db:
            for status in ('pass','fail','not_applicable'):
                with self.assertRaises(ValueError):
                    app.execute(db,{'control_id':self.cid,'status':status,'provenance':{'collection_status':'error'}})
            result=app.execute(db,{'control_id':self.cid,'status':'inconclusive','provenance':{'collection_status':'partial'}})
            self.assertIsNone(result['finding_id'])
            self.assertEqual(app.execution_context(db,result['execution_id'])['provenance']['collection_status'],'partial')

    def test_inactive_control_and_future_date_rejected(self):
        with app.connect() as db:
            with self.assertRaises(ValueError):
                app.execute(db,{'control_id':self.cid,'status':'pass','executed_at':'2999-01-01T00:00:00Z'})
            db.execute('UPDATE controls SET active=0 WHERE id=?',(self.cid,))
            with self.assertRaises(ValueError):
                app.execute(db,{'control_id':self.cid,'status':'pass'})

    def test_invalid_evidence_link_leaves_no_file(self):
        try:
            with app.connect() as db:
                grc_plus.save_file(db,{'title':'Invalid','file_name':'bad.txt','content_base64':'YQ==','controls':[999999]})
        except Exception:
            pass
        with app.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM evidence').fetchone()[0],0)
        self.assertFalse(Path(app.EVIDENCE_DIR).exists() and list(Path(app.EVIDENCE_DIR).iterdir()))

    def test_legacy_execution_does_not_invent_snapshot(self):
        with app.connect() as db:
            rid=app.insert(db,'executions',{'control_id':self.cid,'status':'pass'})
            ctx=app.execution_context(db,rid)
            self.assertFalse(ctx['snapshot_available'])
            self.assertIsNone(ctx['definition_snapshot'])

    def test_parallel_retries_are_serialized(self):
        from concurrent.futures import ThreadPoolExecutor
        data={'control_id':self.cid,'status':'fail','idempotency_key':'parallel-uat-key'}
        def write(_):
            with app.connect() as db:
                return app.execute(db,data)['execution_id']
        with ThreadPoolExecutor(max_workers=6) as pool:
            results=list(pool.map(write,range(8)))
        self.assertEqual(len(set(results)),1)
        with app.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM findings').fetchone()[0],1)

    def test_backup_restore_preserves_database_files_and_roles(self):
        import backup
        import sqlite3
        with app.connect() as db:
            eid=self.evidence(db)
            app.execute(db,{'control_id':self.cid,'status':'fail','evidence_ids':[eid]})
        archive=Path(self.tmp.name)/'backups'/'snapshot.zip'
        backup.backup(app.DB,app.EVIDENCE_DIR,archive)
        restored=Path(self.tmp.name)/'restored'
        backup.restore(archive,restored)
        db=sqlite3.connect(restored/'control.db')
        try:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM roles').fetchone()[0],3)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM findings').fetchone()[0],1)
            self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0],'ok')
        finally:db.close()
        self.assertEqual((restored/'evidence-files'/str(eid)).read_bytes(),b'original')
        with self.assertRaises(ValueError):backup.restore(archive,restored)
