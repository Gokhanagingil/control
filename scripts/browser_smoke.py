"""Real Chromium acceptance in a temporary synthetic database; never mutates staging."""
import os
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import json
import secrets
import tempfile
import threading
from http.server import ThreadingHTTPServer
import app
import identity
import seed_reference
import seed_itil
from playwright.sync_api import sync_playwright, expect


def exercise(page,out,checks):
    expect(page.locator('#pageTitle')).to_have_text('Genel Bakış')
    expect(page.locator('#topActions button')).to_have_count(2)
    checks.append('login_first_password_change_dashboard')
    page.screenshot(path=str(out/'01-dashboard.png'),full_page=True)
    for view in ['controls','objectives','audits','findings','evidence','executions','standards','clauses','processes','risks','actions','documents','compliance','architecture','admin']:
        page.locator(f'[data-nav="{view}"]').click()
        expect(page.locator('#content')).not_to_contain_text('Veriler hazırlanıyor')
        expect(page.locator('#content')).not_to_contain_text('İşlem başarısız')
        checks.append('navigate_'+view)
    page.locator('[data-nav="controls"]').click()
    page.locator('#tableSearch').fill('KS-DEMO-CTL-001')
    page.locator('[data-open]').first.click()
    expect(page.locator('#detail')).to_have_class('open')
    expect(page.locator('#detailTitle')).to_contain_text('KS-DEMO-CTL-001')
    page.screenshot(path=str(out/'02-control-relationships.png'),full_page=True)
    page.keyboard.press('Escape');expect(page.locator('#detail')).not_to_have_class('open')
    checks.append('control_relations_drawer_search_escape')
    page.locator('[data-nav="standards"]').click()
    page.locator('[data-open]').first.click()
    page.get_by_role('button',name='Bu standart için denetim başlat').click()
    page.locator('#auditName').fill('UAT Browser Audit')
    page.get_by_role('button',name='Denetimi oluştur',exact=True).click()
    expect(page.locator('#detailTitle')).to_contain_text('UAT Browser Audit')
    checks.append('create_audit_from_standard')
    page.locator('[data-nav="evidence"]').click()
    page.get_by_role('button',name='Kanıt yükle',exact=True).click()
    page.locator('[data-field=title]').fill('UAT Browser Evidence')
    page.locator('#evidenceFile').set_input_files({'name':'uat.txt','mimeType':'text/plain','buffer':b'UAT evidence original'})
    page.locator('#detailFooter').get_by_role('button',name='Kaydet',exact=True).click()
    expect(page.locator('#detailTitle')).to_contain_text('UAT Browser Evidence')
    with page.expect_download() as dl:
        page.locator('[data-file-version="1"]').click()
    assert Path(dl.value.path()).read_bytes()==b'UAT evidence original'
    page.locator('#addVersion').click()
    page.locator('#evidenceFile').set_input_files({'name':'uat-v2.txt','mimeType':'text/plain','buffer':b'UAT evidence revised'})
    page.locator('#detailFooter').get_by_role('button',name='Kaydet',exact=True).click()
    expect(page.locator('[data-file-version]')).to_have_count(2)
    with page.expect_download() as dl:
        page.locator('[data-file-version="1"]').click()
    assert Path(dl.value.path()).read_bytes()==b'UAT evidence original'
    checks.append('upload_download_version_original_preserved')
    page.screenshot(path=str(out/'03-evidence-history.png'),full_page=True)
    page.locator('[data-nav="executions"]').click()
    page.get_by_role('button',name='Kontrol sonucu kaydet').click()
    with app.connect() as db:
        cid=db.execute("SELECT id FROM controls WHERE code='KS-DEMO-CTL-001'").fetchone()[0]
    page.locator('#runControl').select_option(str(cid))
    page.locator('#runStatus').select_option('fail')
    page.locator('#runDetails').fill('UAT: controlled failure, not live source data')
    page.locator('input[data-link="runEvidence"]').first.check()
    page.get_by_role('button',name='Sonucu kaydet',exact=True).click()
    expect(page.locator('#pageTitle')).to_have_text('Kontrol Sonuçları')
    expect(page.locator('#detailTitle')).to_contain_text('Kontrol')
    with app.connect() as db:
        assert db.execute("SELECT COUNT(*) FROM findings WHERE description LIKE 'UAT: controlled%'").fetchone()[0]==1
    checks.append('manual_fail_creates_finding_with_evidence')
    page.locator('[data-nav="compliance"]').click()
    expect(page.locator('#content')).to_contain_text('ön')
    page.screenshot(path=str(out/'04-compliance.png'),full_page=True)
    page.locator('[data-nav="controls"]').click()
    with page.expect_download() as dl:
        page.locator('#tableExport').click()
    assert Path(dl.value.path()).read_bytes()[:2]==b'PK'
    checks.append('xlsx_browser_export')
    page.set_viewport_size({'width':390,'height':844})
    page.locator('[data-nav="home"]').click()
    expect(page.locator('#pageTitle')).to_have_text('Genel Bakış')
    page.screenshot(path=str(out/'05-mobile.png'),full_page=True)
    page.locator('#signout').click();page.wait_for_url('**/login')
    checks.append('mobile_and_logout')


def run():
    out=Path(os.environ.get('UAT_OUTPUT','verification/browser'));out.mkdir(parents=True,exist_ok=True)
    checks=[];errors=[]
    with tempfile.TemporaryDirectory() as tmp:
        app.DB=str(Path(tmp)/'uat.db');app.EVIDENCE_DIR=str(Path(tmp)/'files')
        app.KEY=secrets.token_urlsafe(32);app.COOKIE_SECURE=False
        seed_reference.seed();seed_itil.run()
        password=secrets.token_urlsafe(20);new_password=secrets.token_urlsafe(24)
        with app.connect() as db:identity.provision(db,'uat.browser',password)
        server=ThreadingHTTPServer(('127.0.0.1',0),app.Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        base=f'http://127.0.0.1:{server.server_address[1]}'
        try:
            with sync_playwright() as p:
                options={'headless':True}
                if os.environ.get('CHROMIUM_PATH'):options['executable_path']=os.environ['CHROMIUM_PATH']
                browser=p.chromium.launch(**options)
                context=browser.new_context(viewport={'width':1440,'height':980},accept_downloads=True)
                page=context.new_page();page.set_default_timeout(10000)
                page.on('pageerror',lambda error:errors.append(str(error)))
                page.goto(base+'/login')
                page.locator('[name=username]').fill('uat.browser');page.locator('[name=password]').fill(password)
                page.get_by_role('button',name='Oturum aç').click();page.wait_for_url('**/change-password')
                page.locator('[name=current_password]').fill(password);page.locator('[name=new_password]').fill(new_password)
                page.get_by_role('button',name='Parolayı değiştir ve devam et').click()
                try:
                    exercise(page,out,checks)
                    assert not errors,errors
                except Exception as exc:
                    page.screenshot(path=str(out/'failure.png'),full_page=True)
                    (out/'report.json').write_text(json.dumps({'status':'FAIL','checks':checks,'error':str(exc),'console_errors':errors},ensure_ascii=False,indent=2))
                    raise
                finally:browser.close()
        finally:
            server.shutdown();server.server_close();thread.join(timeout=5)
    report={'status':'PASS','checks':checks,'check_count':len(checks),'console_errors':errors,'data':'synthetic temporary DB only'}
    (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False))

if __name__=='__main__':run()
