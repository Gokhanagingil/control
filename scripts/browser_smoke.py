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
    page.locator('[data-row]').first.locator('td').nth(1).click()
    expect(page.locator('#detail')).to_have_class('open')
    expect(page.locator('#detailTitle')).to_contain_text('KS-DEMO-CTL-001')
    page.screenshot(path=str(out/'02-control-relationships.png'),full_page=True)
    page.keyboard.press('Escape');expect(page.locator('#detail')).not_to_have_class('open')
    checks.append('control_relations_drawer_search_escape')
    page.locator('[data-nav="standards"]').click()
    page.locator('[data-row]').first.locator('td').nth(1).click()
    page.get_by_role('button',name='Bu standart için denetim başlat').click()
    page.locator('#auditName').fill('UAT Browser Audit')
    page.get_by_role('button',name='Denetimi oluştur',exact=True).click()
    expect(page.locator('#detailTitle')).to_contain_text('UAT Browser Audit')
    checks.append('create_audit_from_standard')
    page.locator('[data-nav="audits"]').click()
    page.get_by_role('button',name='+ Yeni denetim').click()
    page.locator('#auditName').fill('UAT ISO ve CIS kapsamı')
    standards=page.locator('#auditStandards input[type=checkbox]')
    standards.nth(0).check();standards.nth(1).check()
    scope=page.locator('#auditClauses [data-link]')
    assert scope.count()>2
    scope.first.uncheck()
    selected=page.locator('#auditClauses [data-link]:checked').count()
    page.get_by_role('button',name='Denetimi oluştur',exact=True).click()
    expect(page.locator('#auditCriteria .chip')).to_have_count(2)
    page.get_by_role('button',name='Düzenle',exact=True).click()
    expect(page.locator('#auditClauses [data-link]:checked')).to_have_count(selected)
    scope.first.check()
    page.get_by_role('button',name='Değişiklikleri kaydet').click()
    expect(page.locator('#detailTitle')).to_contain_text('UAT ISO ve CIS kapsamı')
    page.get_by_role('button',name='Düzenle',exact=True).click()
    expect(page.locator('#auditClauses [data-link]:checked')).to_have_count(selected+1)
    checks.append('create_and_edit_multistandard_scoped_audit')
    page.locator('[data-nav="risk_catalog"]').click()
    page.locator('[data-row]').first.locator('td').first.click()
    page.get_by_role('button',name='Bu şablondan risk aç').click()
    page.locator('[data-field=code]').fill('UAT-R-1')
    page.locator('[data-field=entity_name]').fill('UAT hizmeti')
    page.locator('[data-field=owner]').fill('UAT denetçi')
    page.locator('[data-field=appetite]').fill('5')
    page.locator('[data-field=review_date]').fill('2030-01-10')
    expect(page.locator('#riskPreview')).to_contain_text('→')
    page.get_by_role('button',name='Kaydet',exact=True).click()
    expect(page.locator('#detailTitle')).to_contain_text('UAT-R-1')
    page.get_by_role('button',name='Riski değerlendir').click()
    page.locator('#riskRationale').fill('Saha gözlemi, teyit edilmiş kontrol katkısı yok.')
    page.get_by_role('button',name='Değerlendirmeyi kaydet').click()
    expect(page.locator('#detailContent')).to_contain_text('İştah aşıldı')
    page.get_by_role('button',name='İşleme faaliyeti aç').click()
    page.locator('[data-field=code]').fill('UAT-RA-1')
    page.locator('[data-field=title]').fill('UAT risk azaltma')
    page.get_by_role('button',name='Kaydet',exact=True).click()
    expect(page.locator('#detailTitle')).to_contain_text('UAT risk azaltma')
    page.locator('[data-nav="risks"]').click()
    page.locator('#riskFilter').select_option('above')
    page.locator('[data-row]').filter(has_text='UAT-R-1').first.click()
    page.get_by_role('button',name='Kabul kararı').click()
    page.locator('#riskDecisionReason').fill('Geçici kabul ve aylık izleme.')
    page.locator('#riskException').fill('Pilot istisnası, sınırlı maruziyet ve yetkili takip.')
    page.get_by_role('button',name='Kararı kaydet').click()
    expect(page.locator('#detailContent')).to_contain_text('Pilot istisnası')
    expect(page.get_by_role('button',name='Riski değerlendir')).to_have_count(0)
    page.get_by_role('button',name='Yeniden aç').click()
    page.locator('#riskDecisionReason').fill('Varlık değişikliği nedeniyle yeniden değerlendirme.')
    page.get_by_role('button',name='Kararı kaydet').click()
    expect(page.get_by_role('button',name='Riski değerlendir')).to_be_visible()
    checks.append('above_appetite_decision_history_and_reopen')
    checks.append('catalog_statement_risk_assessment_treatment')
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
    with page.expect_response(lambda r: r.url.endswith('/api/executions') and r.request.method=='POST') as completed:
        page.get_by_role('button',name='Sonucu kaydet',exact=True).click()
    response=completed.value
    assert response.status==201,response.text()
    saved=response.json();assert saved['finding_id'] is not None
    expect(page.locator('#pageTitle')).to_have_text('Kontrol Sonuçları')
    expect(page.locator('#detailTitle')).to_have_text('Kontrol sonucu • #'+str(saved['execution_id']))
    with app.connect() as db:
        finding=db.execute('SELECT description FROM findings WHERE id=?',(saved['finding_id'],)).fetchone()
        assert finding and finding['description']=='UAT: controlled failure, not live source data'
        assert db.execute('SELECT COUNT(*) FROM findings WHERE execution_id=?',(saved['execution_id'],)).fetchone()[0]==1
    checks.append('manual_fail_creates_finding_with_evidence')
    page.locator('[data-nav="compliance"]').click()
    expect(page.locator('#content')).to_contain_text('ön')
    page.screenshot(path=str(out/'04-compliance.png'),full_page=True)
    page.locator('[data-nav="controls"]').click()
    with page.expect_download() as dl:
        page.locator('#tableExport').click()
    assert Path(dl.value.path()).read_bytes()[:2]==b'PK'
    checks.append('xlsx_browser_export')
    exercise_feedback(page,out,checks)
    page.set_viewport_size({'width':390,'height':844})
    page.locator('[data-nav="home"]').click()
    expect(page.locator('#pageTitle')).to_have_text('Genel Bakış')
    page.screenshot(path=str(out/'05-mobile.png'),full_page=True)
    page.locator('#signout').click();page.wait_for_url('**/login')
    checks.append('mobile_and_logout')


def exercise_feedback(page,out,checks):
    """Acceptance of the five specific user feedback items."""
    page.set_viewport_size({'width':1440,'height':980})
    page.locator('[data-nav="controls"]').click()
    expect(page.locator('#content [data-open]')).to_have_count(0)
    row=page.locator('#content [data-row]').first
    row.locator('td').nth(1).click()
    expect(page.locator('#detail')).to_have_class('open')
    expect(row).to_have_attribute('aria-current','true')
    grip=page.locator('#detailResize')
    expect(grip).to_be_visible()
    grip.hover()  # Wait for opening transition to settle before using coordinates.
    before=page.locator('#detail').bounding_box()['width']
    rect=grip.bounding_box();x=rect['x']+rect['width']/2;y=300
    page.mouse.move(x,y);page.mouse.down()
    expect(page.locator('body')).to_have_class('resizing-detail')
    page.mouse.move(x-160,y,steps=12);page.mouse.up()
    after=page.locator('#detail').bounding_box()['width']
    assert after>before+120,(before,after)
    expect(grip).to_have_attribute('aria-valuenow',str(round(after)))
    page.screenshot(path=str(out/'06-resized-split-view.png'),full_page=False)
    page.reload()
    row=page.locator('#content [data-row]').first;row.focus();row.press('Enter')
    expect(page.locator('#detail')).to_have_class('open')
    expect(grip).to_have_attribute('aria-valuenow',str(round(after)))
    grip.focus();grip.press('Home');expect(grip).to_have_attribute('aria-valuenow','360')
    grip.press('ArrowLeft');expect(grip).to_have_attribute('aria-valuenow','384')
    grip.press('End');expect(grip).to_have_attribute('aria-valuenow','806')
    max_width=page.locator('#detail').bounding_box()['width']
    assert abs(max_width-806)<1,max_width  # Browser geometry may include subpixel rounding.
    grip.press('Enter');expect(grip).to_have_attribute('aria-valuenow','540')
    checks.append('whole_row_keyboard_resize_mouse_limits_and_persistence')
    with app.connect() as db:
        ins=lambda table,**v:app.insert(db,table,v)
        st=ins('standards',code='UAT-REL-ST',name='UAT relational standard')
        cl=ins('clauses',standard_id=st,code='1',title='UAT relational clause')
        obj=ins('objectives',code='UAT-REL-OBJ',name='UAT relational objective')
        process=ins('processes',code='UAT-REL-PROC',name='UAT relational process')
        control=ins('controls',code='UAT-REL-CONTROL',name='UAT relational control')
        for table,fid in [('control_clauses',cl),('control_processes',process),('control_objectives',obj)]:
            db.execute('INSERT INTO '+table+' VALUES(?,?)',(control,fid))
        audit=ins('audits',name='UAT REL Current audit')
        other=ins('audits',name='UAT REL Other audit')
        db.execute('INSERT INTO audit_clauses VALUES(?,?)',(audit,cl))
        current_run=app.execute(db,{'control_id':control,'audit_id':audit,'status':'fail'})
        other_run=app.execute(db,{'control_id':control,'audit_id':other,'status':'fail'})
        ins('findings',title='UAT closed current finding',audit_id=audit,status='closed')
    page.locator('[data-nav="objectives"]').click()
    page.locator('#tableSearch').fill('UAT-REL-OBJ')
    page.locator('#content [data-row]').first.click()
    expect(page.locator('#objectiveControls')).to_contain_text('UAT-REL-CONTROL')
    expect(page.locator('#objectiveClauses')).to_contain_text('UAT relational clause')
    expect(page.locator('#objectiveClauses')).to_contain_text('Kontroller üzerinden')
    expect(page.locator('#objectiveProcesses')).to_contain_text('UAT relational process')
    page.screenshot(path=str(out/'07-objective-relationships.png'),full_page=True)
    page.locator('#objectiveControls [data-related-table="controls"]').click()
    expect(page.locator('#detailTitle')).to_contain_text('UAT-REL-CONTROL')
    page.get_by_role('button',name='← Önceki kayıt',exact=True).click()
    expect(page.locator('#detailTitle')).to_contain_text('UAT-REL-OBJ')
    page.get_by_role('button',name='Kontrol bağlantılarını düzenle',exact=True).click()
    page.get_by_role('button',name='Bağlantıları kaydet',exact=True).click()
    expect(page.locator('#objectiveControls')).to_contain_text('UAT-REL-CONTROL')
    checks.append('objective_direct_controls_derived_clauses_processes_edit_and_back')
    page.locator('[data-nav="audits"]').click()
    page.locator('#tableSearch').fill('UAT REL Current audit')
    page.locator('#content [data-row]').first.click()
    expect(page.locator('#auditFindings [data-related-table="findings"]')).to_have_count(2)
    expect(page.locator('#auditOtherFindings [data-related-table="findings"]')).to_have_count(1)
    expect(page.locator('#auditFindings')).to_contain_text('UAT closed current finding')
    expect(page.locator('#auditOtherFindings')).to_contain_text('UAT REL Other audit')
    page.screenshot(path=str(out/'08-audit-finding-groups.png'),full_page=True)
    page.locator('#auditFindings [data-related-table="findings"][data-related-id="'+str(current_run['finding_id'])+'"]').click()
    expect(page.locator('#detailTitle')).to_have_text('Bulgu • #'+str(current_run['finding_id']))
    page.get_by_role('button',name='← Önceki kayıt',exact=True).click()
    expect(page.locator('#auditOtherFindings')).to_contain_text('UAT REL Other audit')
    checks.append('audit_current_and_other_open_findings_separated_and_clickable')
    page.locator('[data-nav="architecture"]').click()
    expect(page.locator('#relationshipMap')).to_be_visible()
    for name in ['Standart / otorite','Standart maddesi','Kontrol hedefi','Süreç','Denetim','Kontrol tanımı','Kontrol çalışması','Kanıt','Bulgu','Düzeltici faaliyet']:
        expect(page.locator('#relationshipMap')).to_contain_text(name)
    page.locator('#mapZoomIn').click();expect(page.locator('#mapScale')).to_have_text('125%')
    page.locator('#mapFit').click();expect(page.locator('#mapScale')).to_have_text('100%')
    with page.expect_download() as download:
        page.locator('#mapExport').click()
    raw=Path(download.value.path()).read_bytes()
    from xml.etree import ElementTree as ET
    ET.fromstring(raw);assert b'<script' not in raw
    (out/'09-relationship-map.svg').write_bytes(raw)
    page.screenshot(path=str(out/'09-relationship-map.png'),full_page=True)
    page.locator('#relationshipMap [data-map-route="objectives"]').click()
    expect(page.locator('#pageTitle')).to_have_text('Kontrol Hedefleri')
    checks.append('single_relationship_map_zoom_export_and_link_navigation')
    page.set_viewport_size({'width':390,'height':844})
    page.locator('#content [data-row]').first.click()
    expect(page.locator('#detail')).to_have_class('open')
    expect(page.locator('#detailResize')).to_be_hidden()
    assert abs(page.locator('#detail').bounding_box()['width']-390)<2
    page.keyboard.press('Escape')
    checks.append('mobile_detail_has_no_horizontal_resize_trap')


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
