"""Independent API-key client exercises the GRC boundary, not ServiceNow/Dynamics."""
import base64
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


class MCPBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.old=(app.DB,app.EVIDENCE_DIR,app.KEY)
        app.DB=str(Path(self.tmp.name)/'test.db');app.EVIDENCE_DIR=str(Path(self.tmp.name)/'evidence')
        app.KEY=secrets.token_urlsafe(32);app.initialize()
        with app.connect() as db:
            self.cid=app.insert(db,'controls',{'code':'MCP-AUTO','name':'Boundary test','execution_mode':'automatic'})
            self.manual=app.insert(db,'controls',{'code':'MCP-MANUAL','name':'Manual test'})
        self.server=ThreadingHTTPServer(('127.0.0.1',0),app.Handler)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.url=f'http://127.0.0.1:{self.server.server_port}/api/'

    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.thread.join(5)
        app.DB,app.EVIDENCE_DIR,app.KEY=self.old;self.tmp.cleanup()

    def request(self,path,payload=None,method=None):
        req=Request(self.url+path,data=None if payload is None else json.dumps(payload).encode(),
            headers={'X-API-Key':app.KEY,'Content-Type':'application/json'},
            method=method or ('POST' if payload is not None else 'GET'))
        try:
            with urlopen(req,timeout=10) as response:
                raw=response.read()
                return response.status,json.loads(raw) if response.headers.get_content_type()=='application/json' else raw
        except HTTPError as error:
            return error.code,json.loads(error.read())

    def test_external_client_evidence_result_retry_and_conflict(self):
        status,ctx=self.request(f'controls/{self.cid}/context');self.assertEqual(status,200)
        self.assertEqual(ctx['execution_mode'],'automatic')
        binary=b'{"fixture":true,"missing_servers":["test-server"]}'
        status,evidence=self.request('evidence/upload',{'title':'Synthetic MCP query result','file_name':'result.json',
            'content_base64':base64.b64encode(binary).decode(),'source':'mcp','controls':[self.cid]})
        self.assertEqual(status,201,evidence)
        eid=evidence['id'];self.assertEqual(self.request(f'evidence/{eid}/download')[1],binary)
        data={'control_id':self.cid,'status':'fail','source':'mcp','evidence_ids':[eid],
            'idempotency_key':'mcp-external-fixture-001','provenance':{'collection_status':'complete',
            'source_system':'synthetic-fixture','query_reference':'fixture:cmdb-discovery','sample_size':1}}
        status,first=self.request('executions',data);self.assertEqual(status,201,first)
        self.assertIsNotNone(first['finding_id'])
        status,again=self.request('executions',data);self.assertEqual(status,200,again)
        self.assertTrue(again['replayed']);self.assertEqual(first['execution_id'],again['execution_id'])
        self.assertEqual(self.request('executions',{**data,'status':'pass'})[0],409)
        status,history=self.request(f"executions/{first['execution_id']}/context")
        self.assertEqual(status,200);self.assertEqual(history['evidence_versions'][0]['version'],1)
        self.assertEqual(history['provenance']['source_system'],'synthetic-fixture')
        self.assertEqual(self.request('executions',{**data,'idempotency_key':'mcp-next-success','status':'pass'})[0],201)
        _,finding=self.request(f"findings/{first['finding_id']}/context")
        self.assertEqual(finding['status'],'open')

    def test_machine_key_cannot_administer_or_execute_manual_control(self):
        for path,payload,method in [('admin/summary',None,None),('excel/export?table=all',None,None),
            ('controls',{'code':'Forbidden','name':'Forbidden'},None),
            (f'controls/{self.cid}',{'name':'Forbidden'},'PATCH'),
            ('executions',{'control_id':self.manual,'status':'pass','source':'mcp'},None),
            ('executions',{'control_id':self.cid,'status':'pass','source':'manual'},None)]:
            self.assertEqual(self.request(path,payload,method)[0],403,path)
        self.assertEqual(self.request('executions',{'control_id':self.cid,'status':'pass','source':'mcp',
            'provenance':{'collection_status':'error'}})[0],400)
