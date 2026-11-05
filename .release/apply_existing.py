"""One-shot, reviewed repairs for PR #7. Applies only to the exact reviewed files."""
from pathlib import Path
import subprocess
EXPECTED={'app.py':'0f0621f2e5ccc36dbcc3cda723c1f377a3768749','grc_plus.py':'0efe6447dd5402f29080391b601660571b01c01e','ksgrc.js':'24f1cfa56b2f46814cf1d4f8d9e14e2c99dc102c','seed_reference.py':'22f4f394b72f2b0c104041bbc99bf3ea36b1993b','Dockerfile':'87d42ab45917e3f04bea8a9d247091126866dc0f','tests/test_http.py':'66c52437943c5ec9d9da346f57ca2c20b8b6d040'}
for name,digest in EXPECTED.items():
    assert subprocess.check_output(['git','hash-object',name],text=True).strip()==digest,name+' changed; review before retry'
p=Path('ksgrc.js');s=p.read_text()
s=s.replace('const [controls,audits,findings,evidence,risks,actions,standards,processes]','const [controls,audits,findings,evidence,risks,correctiveActions,standards,processes]')
s=s.replace("actions.filter(a=>a.status!=='completed')","correctiveActions.filter(a=>a.status!=='completed')")
for f in ['home()','compliancePage()','architecturePage()','adminPage()','renderTable(view)']:
    s=s.replace('return '+f+';','return await '+f+';')
s=s.replace("b.textContent=name;b.onclick=callback;$('detailFooter').append(b)","b.textContent=name;b.onclick=async()=>{if(b.disabled)return;b.disabled=true;try{await callback()}catch(e){toast(e.message,false)}finally{b.disabled=false}};$('detailFooter').append(b)")
s=s.replace("invalidate(table);toast('Kayıt oluşturuldu');await renderTable(table);await openRecord(table,result.id)","invalidate(table);toast('Kayıt oluşturuldu');await navigate(table);await openRecord(table,result.id)")
s=s.replace('async function executionForm(preselect=null){','async function executionForm(preselect=null){\n const requestId=crypto.randomUUID();')
s=s.replace("const payload={control_id:Number($('runControl').value)","const payload={idempotency_key:requestId,control_id:Number($('runControl').value)")
p.write_text(s)
p=Path('grc_plus.py');s=p.read_text();s=s.replace('''    if version==1 and legacy.exists():
        version=2''','''    if version==1 and legacy.exists():
        prior=db.execute("SELECT * FROM evidence WHERE id=?",(eid,)).fetchone()
        legacy_bytes=legacy.read_bytes()
        digest=hashlib.sha256(legacy_bytes).hexdigest()
        if not prior["hash_sha256"] or digest!=prior["hash_sha256"]:
            raise ValueError("Eski kanıtın bütünlük doğrulaması başarısız")
        db.execute("""INSERT INTO evidence_files
          (evidence_id,version,storage_key,file_name,file_size,mime_type,sha256,created_at)
          VALUES(?,?,?,?,?,?,?,?)""",(eid,1,str(eid),prior["file_name"] or f"kanit-{eid}.bin",
          len(legacy_bytes),prior["mime_type"] or "application/octet-stream",digest,
          prior["collected_at"] or now()))
        version=2''')
s=s.replace('''    details=_write_file(db,eid,filename,binary)
    mappings(db,eid,payload,replace=False)''','''    mappings(db,eid,payload,replace=False)
    details=_write_file(db,eid,filename,binary)''');p.write_text(s)
p=Path('app.py');s=p.read_text().replace('import grc_plus','import execution_service\nimport grc_plus',1)
s=s.replace('        grc_plus.setup(db)','        grc_plus.setup(db)\n        execution_service.setup(db)',1)
s=s.replace('    return result\n\n\ndef finding_context','    return execution_service.enrich(db,result)\n\n\ndef finding_context',1)
s=s.replace('def execute(db, data):','def _execute_base(db, data):',1)
s=s.replace('\nSTYLE = """','\ndef execute(db, data):\n    return execution_service.record(db,data,_execute_base)\n\n\nSTYLE = """',1)
s=s.replace('''                    if table == "executions":
                        return self.committed_response(db, 201, execute(db, payload))''','''                    if table == "executions":
                        if getattr(self,"auth_type",None)=="api_key":
                            control=context(db,payload.get("control_id"))
                            if not control or control["execution_mode"]!="automatic" or payload.get("source")!="mcp":
                                return self.respond(403,{"error":"MCP yalnızca otomatik kontrole MCP kaynaklı sonuç yazabilir"})
                        result=execute(db,payload)
                        if not result.get("replayed"):
                            grc_plus.log(db,self,"EXECUTE","controls",payload.get("control_id"))
                        return self.committed_response(db,200 if result.get("replayed") else 201,result)''')
s=s.replace('''        except (ValueError, KeyError, sqlite3.Error, json.JSONDecodeError) as exc:''','''        except execution_service.Conflict as exc:
            self.respond(409, {"error":str(exc)})
        except (ValueError, KeyError, sqlite3.Error, json.JSONDecodeError) as exc:''')
s=s.replace('def connect():\n    db = sqlite3.connect(DB, timeout=15)','''class ClosingConnection(sqlite3.Connection):
    def __exit__(self, *args):
        try:
            return super().__exit__(*args)
        finally:
            self.close()


def connect():
    db = sqlite3.connect(DB, timeout=15, factory=ClosingConnection)''',1);p.write_text(s)
p=Path('seed_reference.py');s=p.read_text();start=s.index('        # Evidence files are synthetic JSON artifacts');end=s.index('        db.execute("INSERT INTO seed_runs',start);block=s[start:end];s=s[:start]+s[end:];loc=s.index('        # Demonstrate that a single evidence');s=s[:loc]+block+'\n'+s[loc:];p.write_text(s)
p=Path('Dockerfile');s=p.read_text().replace('bootstrap.py seed_reference.py','bootstrap.py backup.py seed_reference.py').replace('seed_reference.py grc_plus.py','seed_reference.py seed_itil.py execution_service.py grc_plus.py');p.write_text(s)
p=Path('tests/test_http.py');s=p.read_text().replace('created=controls[0] if controls else None','created=next((c for c in controls if c["execution_mode"]=="automatic"),None)');p.write_text(s)
