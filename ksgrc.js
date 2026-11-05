'use strict';
/* KS GRC v2: Turkish-only browser, authenticated same-origin API, no external dependencies. */
const $=id=>document.getElementById(id);
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const LABELS={home:'Genel Bakış',compliance:'Uyumluluk Panosu',architecture:'Mimari Harita',admin:'Yönetim',
 controls:'Kontroller',objectives:'Kontrol Hedefleri',audits:'Denetimler',findings:'Bulgular',
 evidence:'Kanıt Kütüphanesi',executions:'Kontrol Sonuçları',standards:'Standartlar',
 clauses:'Standart Maddeleri',processes:'Süreçler',risks:'Riskler',actions:'Düzeltici Faaliyetler',documents:'Dokümanlar'};
const MENU=[
 ['GENEL',[['home','▦'],['compliance','◉']]],
 ['KONTROL VE GÜVENCE',[['controls','☑'],['objectives','◇'],['audits','▤'],['findings','⚑'],['evidence','▱'],['executions','✓']]],
 ['KURUMSAL KATALOG',[['standards','◫'],['clauses','≡'],['processes','⇄'],['risks','△'],['actions','↗'],['documents','▧']]],
 ['SİSTEM',[['architecture','⌘'],['admin','⚙']]]
];
const COLUMNS={
 controls:['code','name','execution_mode','nature','frequency','owner'],
 objectives:['code','name','description'],audits:['name','planned_start','planned_end','status'],
 findings:['title','control_id','severity','status'],evidence:['title','file_name','source','status','collected_at'],
 executions:['control_id','status','source','executed_at'],standards:['code','name','version'],
 clauses:['code','title','standard_id'],processes:['code','name','owner'],
 risks:['code','title','likelihood','impact','status'],actions:['code','title','finding_id','due_date','status'],
 documents:['code','title','category','version','status']};
const FORM={
 standards:['code','name','version','description'],clauses:['standard_id','code','title','parent_id','description'],
 processes:['code','name','owner','description'],objectives:['code','name','description'],
 controls:['code','name','description','execution_mode','nature','frequency','criticality','method_type','method','expected_result','owner','active'],
 audits:['name','scope','planned_start','planned_end','actual_start','actual_end','auditors','auditees','status'],
 evidence:['title','description','reference_url','source','confidentiality','status','period_start','period_end','expires_at'],
 findings:['title','control_id','audit_id','severity','status','description'],
 risks:['code','title','description','category','likelihood','impact','owner','status','treatment','due_date'],
 actions:['code','title','description','finding_id','control_id','owner','due_date','priority','status','resolution'],
 documents:['code','title','description','category','version','owner','status','reference_url']};
const REQUIRED={standards:['code','name'],clauses:['standard_id','code','title'],processes:['code','name'],
 objectives:['code','name'],controls:['code','name'],audits:['name'],evidence:['title'],findings:['title'],
 risks:['code','title'],actions:['code','title'],documents:['code','title']};
const REFS={standard_id:'standards',parent_id:'clauses',control_id:'controls',audit_id:'audits',finding_id:'findings'};
const DATES=new Set(['planned_start','planned_end','actual_start','actual_end','due_date','period_start','period_end','expires_at']);
const TEXTAREAS=new Set(['description','scope','method','expected_result','treatment','resolution']);
const STATE={view:'home',cache:{},meta:{fields:{},choices:{}},search:'',page:0,detail:null};
const PER_PAGE=40;
async function api(path,init={}){
 const r=await fetch('/api/'+path,{credentials:'same-origin',...init,headers:{'Content-Type':'application/json',...(init.headers||{})}});
 if(r.status===401){window.location.assign('/login');throw Error('Oturum süresi doldu')}
 if(!r.ok){let m='İşlem başarısız';try{m=(await r.json()).error||m}catch{}throw Error(m+' ('+r.status+')')}
 return (r.headers.get('Content-Type')||'').includes('application/json')?r.json():r.blob();
}
async function list(table,refresh=false){if(!refresh&&STATE.cache[table])return STATE.cache[table];
 const result=await api(table);STATE.cache[table]=result;return result}
function invalidate(){for(const x of arguments)delete STATE.cache[x]}
function toast(value,ok=true){const x=$('toast');x.textContent=value;x.style.background=ok?'#1e3b59':'#a43b35';
 x.style.display='block';clearTimeout(window.ksTimer);window.ksTimer=setTimeout(()=>x.style.display='none',4200)}
function label(field){return STATE.meta.fields?.[field]||field.replaceAll('_',' ')}
function chosen(table,field,v){return STATE.meta.choices?.[table]?.[field]?.[String(v)]||String(v??'')}
function titleOf(r){return r?.name||r?.title||r?.code||('Kayıt #'+r?.id)}
function showValue(table,field,value){
 if(value===null||value===undefined||value==='')return '<span class="muted">—</span>';
 if(REFS[field]&&Number.isFinite(Number(value))){
  const item=STATE.cache[REFS[field]]?.find(x=>x.id===Number(value));
  if(item)return esc(titleOf(item));
 }
 const text=chosen(table,field,value);
 if(['status','severity','execution_mode','priority','active'].includes(field)){
  const tone=['pass','completed','current','active','1','closed'].includes(String(value))?'pass':
   ['fail','critical','high','0','expired'].includes(String(value))?'fail':
   ['open','in_progress','inconclusive'].includes(String(value))?'pending':'';
  return '<span class="pill '+tone+'">'+esc(text)+'</span>';
 }
 return esc(text.length>145?text.slice(0,142)+'…':text);
}
function drawer(title,html,buttons=[]){
 $('detailTitle').textContent=title;$('detailContent').innerHTML=html;
 $('detailFooter').innerHTML='';
 for(const [name,callback,variant] of buttons){
  const b=document.createElement('button');b.type='button';b.className='btn '+(variant||'');
  b.textContent=name;b.onclick=async()=>{if(b.disabled)return;b.disabled=true;try{await callback()}catch(e){toast(e.message,false)}finally{b.disabled=false}};$('detailFooter').append(b)
 }
 $('detail').classList.add('open');$('main').classList.add('details-open');
 $('detail').setAttribute('aria-hidden','false');STATE.detail={title};
}
function closeDetail(){
 $('detail').classList.remove('open');$('main').classList.remove('details-open');
 $('detail').setAttribute('aria-hidden','true');STATE.detail=null
}
function actions(buttons){$('topActions').innerHTML='';for(const [text,handler,variant] of buttons){
 const b=document.createElement('button');b.className='btn '+(variant||'');b.textContent=text;b.onclick=handler;
 $('topActions').append(b)}}
function navigation(){
 $('nav').innerHTML=MENU.map(([group,items])=>'<div class="nav-title">'+esc(group)+'</div>'+
 items.map(([v,ico])=>'<button class="nav-button '+(v===STATE.view?'active':'')+'" data-nav="'+v+'"><span class="nav-icon">'+ico+'</span>'+LABELS[v]+'</button>').join('')).join('');
 $('nav').querySelectorAll('[data-nav]').forEach(b=>b.onclick=()=>navigate(b.dataset.nav));
}
async function navigate(view){
 if(!LABELS[view])view='home';closeDetail();STATE.view=view;STATE.search='';STATE.page=0;
 history.replaceState({},'', '#/'+view);navigation();$('pageTitle').textContent=LABELS[view];
 $('pageSub').textContent=view==='compliance'?'Denetim, standart ve süreç bazında dinamik değerlendirme':
 view==='architecture'?'Kontrol yaşam döngüsü ve entegrasyon bileşenleri':
 view==='admin'?'Kullanıcı, veri ve sistem yönetimi':'Güvenilir kayıtlar ve izlenebilir ilişkiler';
 actions([]);$('content').innerHTML='<div class="panel">Veriler hazırlanıyor…</div>';
 try{
  if(view==='home')return await home();
  if(view==='compliance')return await compliancePage();
  if(view==='architecture')return await architecturePage();
  if(view==='admin')return await adminPage();
  return await renderTable(view);
 }catch(e){$('content').innerHTML='<div class="notice warn">'+esc(e.message)+'</div>'}
}
function tableHTML(table,source){
 const term=STATE.search.toLocaleLowerCase('tr');
 const results=source.filter(x=>Object.values(x).some(v=>String(v??'').toLocaleLowerCase('tr').includes(term)));
 STATE.page=Math.min(STATE.page,Math.max(0,Math.ceil(results.length/PER_PAGE)-1));
 const items=results.slice(STATE.page*PER_PAGE,(STATE.page+1)*PER_PAGE);
 const cols=COLUMNS[table]||['code','title','status'];
 return '<div class="panel"><div class="panel-title"><h2>'+LABELS[table]+' <span class="muted">('+results.length+')</span></h2>'+
 '<span class="badge-note">Ayrıntılar sağ panelde açılır</span></div><div class="toolbar">'+
 '<input id="tableSearch" class="searchbar" placeholder="Kayıt, kod veya açıklama ara…" value="'+esc(STATE.search)+'" aria-label="Kayıtlarda ara">'+
 '<div class="toolbar"><button class="btn secondary small" id="tableExport">Excel’e aktar</button>'+
 '<button class="btn secondary small" id="tableImport">Excel’den aktar</button></div></div>'+
 '<div class="tablewrap"><table><thead><tr>'+cols.map(c=>'<th>'+esc(label(c))+'</th>').join('')+'<th></th></tr></thead><tbody>'+
 items.map(x=>'<tr class="clickable" data-row="'+x.id+'">'+cols.map((c,i)=>'<td'+(i===0?' class="cell-primary"':'')+'>'+showValue(table,c,x[c])+'</td>').join('')+
 '<td><button class="btn ghost small" data-open="'+x.id+'">Aç ›</button></td></tr>').join('')+
 '</tbody></table>'+(results.length?'':'<div class="empty">Kayıt bulunamadı. Yeni bir kayıt ekleyebilir veya arama filtresini temizleyebilirsin.</div>')+'</div>'+
 '<div class="pager"><span>'+(results.length?STATE.page*PER_PAGE+1:0)+'–'+Math.min(results.length,(STATE.page+1)*PER_PAGE)+
 ' / '+results.length+'</span><div><button class="btn ghost small" id="prev" '+(STATE.page===0?'disabled':'')+'>Önceki</button>'+
 '<button class="btn ghost small" id="next" '+((STATE.page+1)*PER_PAGE>=results.length?'disabled':'')+'>Sonraki</button></div></div></div>';
}
function bindTable(table){
 const input=$('tableSearch');input.oninput=e=>{
  const position=e.target.selectionStart;STATE.search=e.target.value;STATE.page=0;
  $('content').innerHTML=tableHTML(table,STATE.cache[table]);bindTable(table);
  $('tableSearch').focus();$('tableSearch').setSelectionRange(position,position);
 };
 $('tableExport').onclick=()=>exportExcel(table);$('tableImport').onclick=()=>importExcel(table);
 $('prev').onclick=()=>{STATE.page--;refreshTable(table)};$('next').onclick=()=>{STATE.page++;refreshTable(table)};
 $('content').querySelectorAll('[data-row]').forEach(r=>r.onclick=()=>openRecord(table,Number(r.dataset.row)));
 $('content').querySelectorAll('[data-open]').forEach(r=>r.onclick=ev=>{ev.stopPropagation();openRecord(table,Number(r.dataset.open))});
}
function refreshTable(table){$('content').innerHTML=tableHTML(table,STATE.cache[table]||[]);bindTable(table)}
async function renderTable(table){
 const records=await list(table,true);
 $('content').innerHTML=tableHTML(table,records);bindTable(table);
 actions(table==='executions'?[['Kontrol sonucu kaydet',()=>executionForm()]]:
  table==='evidence'?[['Kanıt yükle',()=>evidenceForm()]]:
  [['+ Yeni kayıt',()=>createForm(table)],['Excel’e aktar',()=>exportExcel(table),'secondary']]);
}
async function exportExcel(table='all'){
 try{const blob=await api('excel/export?table='+encodeURIComponent(table));
 const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;
 a.download='ks-grc-'+table+'.xlsx';a.click();setTimeout(()=>URL.revokeObjectURL(url),2000);
 toast('Excel dosyası hazırlandı')}catch(e){toast(e.message,false)}
}
const fileToBase64=f=>new Promise((resolve,reject)=>{
 const reader=new FileReader();reader.onerror=reject;reader.onload=()=>resolve(String(reader.result).split(',')[1]);reader.readAsDataURL(f)});
function importExcel(table='all'){
 drawer('Excel’den içe aktar','<div class="notice">Excel’den gelen mevcut kodlar atlanır, yenileri eklenir. Tüm kayıtların Excel dosyasında ilişki sayfaları da bulunur. Kullanıcı parolaları ve kanıt dosyası içerikleri hariçtir.</div>'+
 '<label class="field">Excel çalışma kitabı (.xlsx)<input id="excelUpload" type="file" accept=".xlsx"></label>',
 [['İçe aktar',async()=>{
  const f=$('excelUpload').files?.[0];if(!f)return toast('Excel dosyası seç',false);
  if(f.size>12*1024*1024)return toast('Excel boyutu 12 MB sınırını aşıyor',false);
  try{const result=await api('excel/import?table='+table,{method:'POST',body:JSON.stringify({content_base64:await fileToBase64(f)})});
   invalidate(...Object.keys(COLUMNS));
   drawer('İçe aktarma sonucu','<div class="notice success">İçe aktarma tamamlandı.</div><ul class="mini-list">'+
   Object.entries(result).map(([k,v])=>'<li>'+esc(LABELS[k]||k)+': '+esc(v.inserted||0)+' yeni, '+esc(v.skipped||0)+' mevcut</li>').join('')+'</ul>',
   [['Tamam',()=>navigate(table==='all'?'home':table)]]);
  }catch(e){toast(e.message,false)}
 }],['Vazgeç',closeDetail,'secondary']]);
}
async function fieldInput(table,key,value){
 const required=(REQUIRED[table]||[]).includes(key)?' required':'';
 const options=STATE.meta.choices?.[table]?.[key];
 let inner='';
 if(options){
  inner='<select data-field="'+key+'"'+required+'>'+Object.entries(options).map(([v,t])=>
   '<option value="'+esc(v)+'"'+(String(value??'')===v?' selected':'')+'>'+esc(t)+'</option>').join('')+'</select>';
 }else if(REFS[key]){
  const refs=await list(REFS[key]);
  inner='<select data-field="'+key+'"'+required+'><option value="">Seçiniz</option>'+
   refs.map(x=>'<option value="'+x.id+'"'+(Number(value)===x.id?' selected':'')+'>'+esc((x.code?x.code+' — ':'')+titleOf(x))+'</option>').join('')+'</select>';
 }else if(TEXTAREAS.has(key)){
  inner='<textarea data-field="'+key+'">'+esc(value||'')+'</textarea>';
 }else if(key==='impact'||key==='likelihood'){
  inner='<select data-field="'+key+'">'+[1,2,3,4,5].map(i=>'<option value="'+i+'"'+(Number(value||3)===i?' selected':'')+'>'+i+'</option>').join('')+'</select>';
 }else inner='<input data-field="'+key+'" type="'+(DATES.has(key)?'date':'text')+'" value="'+esc(value??'')+'"'+required+'>';
 return '<label class="field '+(TEXTAREAS.has(key)?'wide':'')+'">'+esc(label(key))+inner+'</label>';
}
function formValues(table,keys){
 const result={},missing=[];
 for(const key of keys){
  const el=$('detailContent').querySelector('[data-field="'+key+'"]');if(!el)continue;
  let value=el.value.trim();
  if((REQUIRED[table]||[]).includes(key)&&!value)missing.push(label(key));
  if(REFS[key])value=value?Number(value):null;
  if(['active','likelihood','impact'].includes(key)&&value!=='')value=Number(value);
  if(value!==''&&value!==null)result[key]=value;
 }
 if(missing.length)throw Error('Zorunlu alanlar: '+missing.join(', '));
 return result;
}
async function createForm(table,defaults={}){
 if(table==='evidence')return evidenceForm();
 if(table==='executions')return executionForm();
 const names=FORM[table];if(!names)return;
 try{
 const html='<div class="notice">Kaydı oluşturduktan sonra süreç, madde ve kanıt bağlantılarını sağ panelde düzenleyebilirsin.</div>'+
 '<div class="formgrid">'+(await Promise.all(names.map(key=>fieldInput(table,key,defaults[key])))).join('')+'</div>';
 drawer('Yeni '+LABELS[table]+' kaydı',html,[['Kaydet',async()=>{
  try{const result=await api(table,{method:'POST',body:JSON.stringify(formValues(table,names))});
   invalidate(table);toast('Kayıt oluşturuldu');await navigate(table);await openRecord(table,result.id)
  }catch(e){toast(e.message,false)}
 }],['Vazgeç',closeDetail,'secondary']]);
 }catch(e){toast(e.message,false)}
}
async function editForm(table,record){
 const blocked=table==='findings'?['control_id','audit_id']:table==='clauses'?['standard_id']:
 table==='evidence'?['source']:[];
 const keys=(FORM[table]||[]).filter(k=>!blocked.includes(k));
 const html='<div class="formgrid">'+(await Promise.all(keys.map(k=>fieldInput(table,k,record[k])))).join('')+'</div>';
 drawer(LABELS[table]+' • Düzenle',html,[['Değişiklikleri kaydet',async()=>{
  try{await api(table+'/'+record.id,{method:'PATCH',body:JSON.stringify(formValues(table,keys))});
   invalidate(table);await renderTable(table);await openRecord(table,record.id);toast('Kayıt güncellendi')
  }catch(e){toast(e.message,false)}
 }],['Vazgeç',()=>openRecord(table,record.id),'secondary']]);
}
function values(table,rec){
 return '<dl class="keyvalues">'+Object.entries(rec).filter(([k,v])=>typeof v!=='object'&&k!=='password_hash')
 .map(([k,v])=>'<dt>'+esc(label(k))+'</dt><dd>'+showValue(table,k,v)+'</dd>').join('')+'</dl>';
}
function chips(items,fn){
 return '<div class="chips">'+(items?.length?items.map(x=>'<span class="chip">'+esc(fn(x))+'</span>').join(''):
 '<span class="muted">Henüz ilişki bulunmuyor.</span>')+'</div>';
}
function checks(group,title,items,selected,fmt){
 const ids=new Set((selected||[]).map(x=>Number(x.id??x)));
 return '<div class="detail-section"><h3>'+esc(title)+'</h3><input data-filter="'+group+'" placeholder="Bu grupta ara…" class="filter-row" aria-label="'+esc(title)+' ara">'+
 '<div class="link-box" data-container="'+group+'">'+items.map(x=>'<label class="link-option">'+
 '<input type="checkbox" data-link="'+group+'" value="'+x.id+'"'+(ids.has(x.id)?' checked':'')+'><span>'+esc(fmt(x))+'</span></label>').join('')+'</div></div>';
}
function bindChecks(){
 $('detailContent').querySelectorAll('[data-filter]').forEach(el=>el.oninput=()=>{
  const query=el.value.toLocaleLowerCase('tr');
  $('detailContent').querySelectorAll('[data-container="'+el.dataset.filter+'"] .link-option')
   .forEach(x=>x.style.display=x.textContent.toLocaleLowerCase('tr').includes(query)?'flex':'none');
 });
}
function selected(group){return [...$('detailContent').querySelectorAll('input[data-link="'+group+'"]:checked')].map(x=>Number(x.value))}
async function openRecord(table,id){
 try{
  const record=(await list(table,true)).find(x=>x.id===id);
  if(!record)throw Error('Kayıt bulunamadı');
  const html='<div class="detail-section"><h3>Kayıt bilgileri</h3>'+values(table,record)+'</div>';
  const footer=FORM[table]?[['Düzenle',()=>editForm(table,record),'secondary'],['Kapat',closeDetail,'secondary']]:
   [['Kapat',closeDetail,'secondary']];
  if(table==='controls')return detailControl(record,html,footer);
  if(table==='audits')return detailAudit(record,html,footer);
  if(table==='evidence')return detailEvidence(record,html,footer);
  if(table==='findings'||table==='executions')return detailExecution(table,record,html,footer);
  if(table==='risks'||table==='documents')return detailLinked(table,record,html,footer);
  if(table==='standards')return detailStandard(record,html,footer);
  drawer(LABELS[table]+' • '+titleOf(record),html,footer);
 }catch(e){toast(e.message,false)}
}

async function detailControl(rec,basic,footer){
 const [ctx,evidence,clauses,processes,objectives,standards]=await Promise.all([
  api('controls/'+rec.id+'/context'),api('controls/'+rec.id+'/evidence'),
  list('clauses'),list('processes'),list('objectives'),list('standards')]);
 const std=id=>standards.find(s=>s.id===id)?.code||'Standart';
 const detail='<div class="notice">Bir kontrolün birden çok standart maddesi, süreç ve hedefi olabilir. Güncel bağlantı değişiklikleri eski denetim sonuçlarını değiştirmez.</div>'+
 '<div class="detail-section"><h3>Kontrole bağlı kanıtlar ('+evidence.length+')</h3>'+
 chips(evidence,x=>x.title)+'</div>'+
 checks('clause','Standart maddeleri',clauses,ctx.clauses,x=>std(x.standard_id)+' • '+x.code+' — '+x.title)+
 checks('process','Süreçler',processes,ctx.processes,x=>x.code+' — '+x.name)+
 checks('objective','Kontrol hedefleri',objectives,ctx.objectives,x=>x.code+' — '+x.name);
 drawer('Kontrol • '+rec.code,basic+detail,
 [['Bağlantıları kaydet',async()=>{
  try{await api('controls/'+rec.id+'/mappings',{method:'POST',body:JSON.stringify({
   clauses:selected('clause'),processes:selected('process'),objectives:selected('objective')})});
   toast('Kontrol bağlantıları kaydedildi');openRecord('controls',rec.id)
  }catch(e){toast(e.message,false)}
 }],['Kontrol sonucu gir',()=>executionForm(rec.id),'secondary'],...footer]);
 bindChecks();
}
async function detailAudit(rec,basic,footer){
 const [scope,evidence,all]=await Promise.all([
  api('audits/'+rec.id+'/scope'),api('audits/'+rec.id+'/evidence'),list('evidence')]);
 const scopeHtml='<div class="detail-section"><h3>Kapsamdaki standart maddeleri ('+scope.clauses.length+')</h3>'+
  '<div class="link-box">'+scope.clauses.map(c=>'<div class="link-option">'+esc(c.standard_code+' '+c.code+' — '+c.title)+'</div>').join('')+
  '</div></div>';
 const linked=checks('audit_evidence','Bu denetimin kanıtları',all,evidence,x=>x.title);
 drawer('Denetim • '+rec.name,basic+scopeHtml+
 '<div class="notice">Denetim kanıtı doğrudan veya kontrol çalışması üzerinden ilişkilendirilebilir. İki tür bağlantı birlikte görüntülenir.</div>'+linked,
 [['Kanıtları kaydet',async()=>{
  try{await api('audits/'+rec.id+'/evidence',{method:'POST',body:JSON.stringify({
   evidence_ids:selected('audit_evidence')})});
   toast('Denetim kanıtları kaydedildi');openRecord('audits',rec.id)
  }catch(e){toast(e.message,false)}
 }],['Uyumluluğunu göster',()=>navigate('compliance').then(()=>setCompliance('audit',rec.id)),'secondary'],...footer]);
 bindChecks();
}
async function detailEvidence(rec,basic,footer){
 const [ctx,clauses,processes,audits,controls,standards]=await Promise.all([
  api('evidence/'+rec.id+'/context'),list('clauses'),list('processes'),
  list('audits'),list('controls'),list('standards')]);
 const std=id=>standards.find(x=>x.id===id)?.code||'Standart';
 const versions='<div class="detail-section"><h3>Dosya sürümleri ('+ctx.files.length+')</h3>'+
  '<ul class="mini-list">'+ctx.files.map(f=>'<li>'+esc(f.file_name)+' • Sürüm '+f.version+
   ' <button class="btn secondary small" data-file-version="'+f.version+'">İndir</button></li>').join('')+'</ul>'+
  '<button class="btn secondary small" id="addVersion">Yeni dosya sürümü</button></div>';
 const history='<div class="detail-section"><h3>Geçmiş denetimlerde kullanım</h3>'+
  '<ul class="mini-list">'+(ctx.audit_history.length?
    ctx.audit_history.map(x=>'<li>'+esc(x.name)+' • '+esc(x.control_code)+
    ' • '+esc(chosen('executions','status',x.status))+' • '+esc(x.executed_at)+'</li>').join(''):
    '<li>Denetim kullanım geçmişi henüz yok.</li>')+'</ul></div>';
 const links=checks('ev_clauses','İlgili standart maddeleri',clauses,ctx.clauses,
  x=>std(x.standard_id)+' • '+x.code+' — '+x.title)+
 checks('ev_processes','İlgili süreçler',processes,ctx.processes,x=>x.code+' — '+x.name)+
 checks('ev_audits','İlişkili denetimler',audits,ctx.audits,x=>x.name)+
 checks('ev_controls','İlişkili kontroller',controls,ctx.controls,x=>x.code+' — '+x.name);
 drawer('Kanıt • '+rec.title,basic+versions+history+
 '<div class="notice">Aynı dosya birden fazla kontrol, süreç, madde ve denetimi destekleyebilir. Önceki sürümleri saklanır.</div>'+links,
 [['Bağlantıları kaydet',async()=>{
  try{await api('evidence/'+rec.id+'/mappings',{method:'POST',body:JSON.stringify({
   clauses:selected('ev_clauses'),processes:selected('ev_processes'),
   audits:selected('ev_audits'),controls:selected('ev_controls')})});
   toast('Kanıt bağlantıları güncellendi');openRecord('evidence',rec.id)
  }catch(e){toast(e.message,false)}
 }],...footer]);
 bindChecks();
 $('detailContent').querySelectorAll('[data-file-version]').forEach(b=>b.onclick=()=>{
  const v=Number(b.dataset.fileVersion);
  const file=ctx.files.find(f=>f.version===v);
  downloadEvidence(rec.id,v,file?.file_name);
 });
 $('addVersion').onclick=()=>evidenceForm(rec.id);
}
async function downloadEvidence(id,version,name){
 try{const blob=await api('evidence/'+id+'/download?version='+version);
  const url=URL.createObjectURL(blob);const a=document.createElement('a');
  a.href=url;a.download=name||('kanit-'+id+'.bin');a.click();
  setTimeout(()=>URL.revokeObjectURL(url),1600)
 }catch(e){toast(e.message,false)}
}
async function detailExecution(table,rec,basic,footer){
 const ctx=await api(table+'/'+rec.id+'/context');
 const run=table==='findings'?ctx.execution:ctx;
 if(!run)return drawer('Bulgu • '+rec.title,basic,footer);
 const standards=await list('standards');const std=id=>standards.find(s=>s.id===id)?.code||'Standart';
 const trace='<div class="detail-section"><h3>Kontrol testi anındaki sabit bağlantılar</h3>'+
 '<p class="intro">Geçmiş denetim izi sonradan değiştirilemez; bağlantılar çalıştırma anından alınır.</p>'+
 '<h4>Standart maddeleri</h4>'+chips(run.clauses,x=>std(x.standard_id)+' '+x.code+' — '+x.title)+
 '<h4>Süreçler</h4>'+chips(run.processes,x=>x.code+' — '+x.name)+
 '<h4>Kontrol hedefleri</h4>'+chips(run.objectives,x=>x.code+' — '+x.name)+
 '<h4>Kanıtlar</h4>'+chips(run.evidence,x=>x.title)+'</div>';
 let actionsPart='';
 if(table==='findings'){
  const acts=(await list('actions')).filter(a=>a.finding_id===rec.id);
  actionsPart='<div class="detail-section"><h3>Düzeltici faaliyetler ('+acts.length+')</h3>'+
   chips(acts,x=>x.code+' — '+x.title)+'</div>';
  footer.unshift(['Düzeltici faaliyet aç',()=>createForm('actions',{
   code:'KS-DF-'+rec.id+'-'+String(Date.now()).slice(-6),
   title:'Bulgu için düzeltici faaliyet: '+rec.title,
   finding_id:rec.id,control_id:rec.control_id})]);
 }
 drawer((table==='findings'?'Bulgu':'Kontrol sonucu')+' • #'+rec.id,basic+trace+actionsPart,footer);
}
async function detailStandard(rec,basic,footer){
 const clauses=(await list('clauses')).filter(c=>c.standard_id===rec.id);
 drawer('Standart • '+rec.code,basic+
  '<div class="detail-section"><h3>Madde kataloğu ('+clauses.length+')</h3><div class="link-box">'+
  clauses.map(c=>'<div class="link-option">'+esc(c.code+' — '+c.title)+'</div>').join('')+
  '</div></div><div class="notice">Maddeler çalışma başlığıdır; telifli resmî gereklilik metninin yerini tutmaz.</div>',
 [['Bu standart için denetim başlat',()=>auditWizard(rec.id)],...footer]);
}
async function detailLinked(table,rec,basic,footer){
 const linked=await api(table+'/'+rec.id+'/controls');
 const controls=await list('controls');
 drawer(LABELS[table]+' • '+rec.code,basic+
 checks('related_controls','İlgili kontroller',controls,linked,x=>x.code+' — '+x.name),
 [['Kontrolleri kaydet',async()=>{
  try{await api(table+'/'+rec.id+'/controls',{method:'POST',body:JSON.stringify({
   control_ids:selected('related_controls')})});
   toast('Kontrol bağlantıları kaydedildi');openRecord(table,rec.id)
  }catch(e){toast(e.message,false)}
 }],...footer]);
 bindChecks();
}
async function evidenceForm(existingId=null){
 const version=Number.isInteger(existingId);
 const [audits,controls,clauses,processes,standards]=version?[[],[],[],[],[]]:
  await Promise.all(['audits','controls','clauses','processes','standards'].map(x=>list(x)));
 const std=id=>standards.find(s=>s.id===id)?.code||'';
 let html='<div class="notice">'+(version?'Yeni dosya sürümü eklenecek; eski sürüm saklanır.':
  'Kanıtı istediğin denetime, sürece, kontrole ve maddeye bağlayabilirsin.')+
  '<br>PDF, resim, Office dosyası, CSV, TXT, JSON, XML, ZIP ve EML; azami 20 MB.</div>';
 if(!version)html+='<div class="formgrid">'+(await Promise.all(
  ['title','description','source','confidentiality','period_start','period_end','expires_at'].map(k=>fieldInput('evidence',k))
 )).join('')+'</div>';
 html+='<label class="field">Dosya seç<input id="evidenceFile" type="file"></label>';
 if(!version)html+=checks('ev_audits','Denetimler',audits,[],x=>x.name)+
  checks('ev_controls','Kontroller',controls,[],x=>x.code+' — '+x.name)+
  checks('ev_clauses','Standart maddeleri',clauses,[],x=>std(x.standard_id)+' '+x.code+' — '+x.title)+
  checks('ev_processes','Süreçler',processes,[],x=>x.code+' — '+x.name);
 drawer(version?'Kanıt • Yeni sürüm':'Yeni kanıt yükle',html,[['Kaydet',async()=>{
  const f=$('evidenceFile')?.files?.[0];if(!f)return toast('Dosya seçmelisin',false);
  if(!f.size||f.size>20*1024*1024)return toast('Dosya 1 bayt–20 MB arasında olmalı',false);
  try{
   const payload={file_name:f.name,content_base64:await fileToBase64(f)};
   if(!version){
    Object.assign(payload,formValues('evidence',['title','description','source','confidentiality','period_start','period_end','expires_at']));
    payload.audits=selected('ev_audits');payload.controls=selected('ev_controls');
    payload.clauses=selected('ev_clauses');payload.processes=selected('ev_processes');
   }
   const res=await api(version?'evidence/'+existingId+'/versions':'evidence/upload',
    {method:'POST',body:JSON.stringify(payload)});
   invalidate('evidence');toast('Kanıt dosyası saklandı');await navigate('evidence');openRecord('evidence',res.id)
  }catch(e){toast(e.message,false)}
 }],['Vazgeç',closeDetail,'secondary']]);
 bindChecks();
}
async function executionForm(preselect=null){
 const requestId=crypto.randomUUID();
 const [controls,audits,evidence]=await Promise.all(['controls','audits','evidence'].map(x=>list(x)));
 const results=STATE.meta.choices?.executions?.status||{pass:'Başarılı',fail:'Başarısız',inconclusive:'Belirsiz',not_applicable:'Uygulanamaz'};
 const html='<div class="formgrid"><label class="field">Kontrol<select id="runControl">'+controls.map(x=>
 '<option value="'+x.id+'"'+(x.id===preselect?' selected':'')+'>'+esc(x.code+' — '+x.name)+'</option>').join('')+'</select></label>'+
 '<label class="field">Denetim<select id="runAudit"><option value="">Sürekli kontrol / denetim dışı</option>'+
 audits.map(x=>'<option value="'+x.id+'">'+esc(x.name)+'</option>').join('')+'</select></label>'+
 '<label class="field">Kontrol sonucu<select id="runStatus">'+Object.entries(results).map(([k,v])=>
 '<option value="'+k+'">'+esc(v)+'</option>').join('')+'</select></label>'+
 '<label class="field">Kaynak<select id="runSource"><option value="manual">Manuel</option><option value="mcp">MCP</option></select></label>'+
 '<label class="field wide">Gözlem ve gerekçe<textarea id="runDetails" placeholder="Kriter, örneklem ve kontrol sonucunu kaydet…"></textarea></label></div>'+
 checks('runEvidence','Kullanılan kanıtlar',evidence,[],x=>x.title);
 drawer('Kontrol sonucu oluştur',html,[['Sonucu kaydet',async()=>{
  try{const payload={idempotency_key:requestId,control_id:Number($('runControl').value),status:$('runStatus').value,
   source:$('runSource').value,details:$('runDetails').value,evidence_ids:selected('runEvidence')};
   if($('runAudit').value)payload.audit_id=Number($('runAudit').value);
   const saved=await api('executions',{method:'POST',body:JSON.stringify(payload)});
   invalidate('executions','findings');toast(saved.finding_id?'Başarısız kontrol için bulgu oluşturuldu':'Kontrol sonucu kaydedildi');
   await navigate('executions');openRecord('executions',saved.execution_id);
  }catch(e){toast(e.message,false)}
 }],['Vazgeç',closeDetail,'secondary']]);bindChecks();
}
async function auditWizard(selectedStandard=null){
 const standards=await list('standards');
 const html='<div class="notice">Seçilen standardın mevcut tüm maddeleri yeni denetimin kapsamına otomatik eklenecek.</div>'+
 '<label class="field">Standart<select id="auditStandard">'+standards.map(s=>
  '<option value="'+s.id+'"'+(s.id===selectedStandard?' selected':'')+'>'+esc(s.code+' — '+s.name)+'</option>').join('')+'</select></label>'+
 '<label class="field">Denetim adı<input id="auditName" placeholder="2026 İç Denetim"></label>'+
 '<div class="formgrid"><label class="field">Planlanan başlangıç<input id="auditStart" type="date"></label>'+
 '<label class="field">Planlanan bitiş<input id="auditEnd" type="date"></label></div>';
 drawer('Standarttan denetim oluştur',html,[['Denetimi oluştur',async()=>{
  if(!$('auditName').value.trim())return toast('Denetim adı gerekli',false);
  try{const saved=await api('audits/from-standard',{method:'POST',body:JSON.stringify({
    standard_id:Number($('auditStandard').value),name:$('auditName').value.trim(),
    planned_start:$('auditStart').value,planned_end:$('auditEnd').value})});
   invalidate('audits');toast(saved.clause_count+' maddeyle denetim oluşturuldu');
   await navigate('audits');openRecord('audits',saved.audit_id)
  }catch(e){toast(e.message,false)}
 }],['Vazgeç',closeDetail,'secondary']]);
}

async function home(){
 const [controls,audits,findings,evidence,risks,correctiveActions,standards,processes]=await Promise.all([
 'controls','audits','findings','evidence','risks','actions','standards','processes'].map(x=>list(x)));
 const metrics=[
  ['Kontrol',controls.length,'controls','Kontrolleri aç'],
  ['Denetim',audits.length,'audits','Denetimleri aç'],
  ['Açık bulgu',findings.filter(f=>!['closed','accepted'].includes(f.status)).length,'findings','Bulguları incele'],
  ['Kanıt',evidence.length,'evidence','Kanıt kütüphanesi']
 ];
 $('content').innerHTML='<div class="cards">'+metrics.map(([name,n,route,sub])=>
  '<button class="metric" data-go="'+route+'"><span class="metric-label">'+name+'</span>'+
  '<span class="metric-number">'+n+'</span><span class="metric-foot">'+sub+' ›</span></button>').join('')+'</div>'+
 '<div class="panel"><div class="panel-title"><h2>Kontrolden güvenceye</h2><span class="pill">'+standards.length+' standart · '+processes.length+' süreç</span></div>'+
 '<div class="audit-grid"><div><h3>İzlenebilir kontrol zinciri</h3>'+
 '<p class="intro">Standart maddesi → kontrol hedefi → kontrol → kanıt → test → bulgu → düzeltici faaliyet. İlişkiler geriye dönük incelenebilir.</p>'+
 '<button class="btn secondary small" data-go="architecture">Mimari haritayı aç</button></div>'+
 '<div><h3>Çapraz standart değerlendirmesi</h3>'+
 '<p class="intro">Bir standart denetimi yapılmadan da o standartla ilişkili kontrollerin başka çalışmalardaki sonuçlarını görebilirsin. Test edilmeyenler uygun kabul edilmez.</p>'+
 '<button class="btn small" data-go="compliance">Uyumluluk panosuna git</button></div></div></div>'+
 (controls.some(c=>c.code?.startsWith('KS-DEMO-'))?'<div class="notice warn"><b>Örnek kayıt uyarısı:</b> KS-DEMO kayıtlarındaki ölçümler, bulgular ve kanıt dosyaları simüledir. Canlı sistemden elde edilmiş değildir.</div>':'')+
 '<div class="panel"><h2>Güncel takip alanları</h2><div class="cards">'+[
  ['Risk kaydı',risks.length,'risks'],['Açık düzeltici faaliyet',correctiveActions.filter(a=>a.status!=='completed').length,'actions'],
  ['Otomatik kontrol',controls.filter(c=>c.execution_mode==='automatic').length,'controls'],
  ['Manuel kontrol',controls.filter(c=>c.execution_mode==='manual').length,'controls']
 ].map(([name,n,route])=>
 '<button class="metric" data-go="'+route+'"><span class="metric-label">'+name+'</span><span class="metric-number">'+n+'</span></button>').join('')+
 '</div></div>';
 $('content').querySelectorAll('[data-go]').forEach(b=>b.onclick=()=>navigate(b.dataset.go));
 actions([['Uyumluluğa git',()=>navigate('compliance')],['Kontrol oluştur',()=>createForm('controls'),'secondary']]);
}
function ring(value,color){
 const valid=typeof value==='number'&&Number.isFinite(value);
 const n=valid?Math.max(0,Math.min(100,value)):0;
 return '<div class="ring" style="background:conic-gradient('+color+' '+n+'%,#e9eef6 '+n+'%)">'+
 '<div class="ring-inner">'+(valid?n.toFixed(1).replace('.0','')+'%':'—')+'</div></div>';
}
async function compliancePage(){
 const [std,pr,au]=await Promise.all(['standards','processes','audits'].map(list));
 const opts=(arr,fn)=>'<option value="">Tümü</option>'+
  arr.map(x=>'<option value="'+x.id+'">'+esc(fn(x))+'</option>').join('');
 $('content').innerHTML='<div class="panel"><h2>Kapsamı seç</h2>'+
 '<div class="choice-row"><label>Standart / çerçeve<select id="stdFilter">'+opts(std,x=>x.code+' — '+x.name)+'</select></label>'+
 '<label>Denetim<select id="auditFilter">'+opts(au,x=>x.name)+'</select></label>'+
 '<label>Süreç<select id="procFilter">'+opts(pr,x=>x.code+' — '+x.name)+'</select></label></div>'+
 '<p class="intro">Aynı kontrol farklı standartlara bağlı olabilir. Denetim seçmediğinde en son kontrol sonucu, başka bir denetimden gelmiş olsa bile <b>ön değerlendirme</b> için kullanılır. Bu sonuç resmî standarda uygunluk kararı değildir.</p></div>'+
 '<div id="complianceResult"><div class="panel">Oranlar hesaplanıyor…</div></div>';
 const update=async()=>{
  try{
   const q=new URLSearchParams();
   [['standard_id','stdFilter'],['audit_id','auditFilter'],['process_id','procFilter']].forEach(
   ([key,id])=>{if($(id).value)q.set(key,$(id).value)});
   displayCompliance(await api('compliance?'+q.toString()));
  }catch(e){$('complianceResult').innerHTML='<div class="notice warn">'+esc(e.message)+'</div>'}
 };
 ['stdFilter','auditFilter','procFilter'].forEach(id=>$(id).onchange=update);
 await update();
 actions([['Kontrol kataloğunu aç',()=>navigate('controls')],['Tüm verileri Excel’e aktar',()=>exportExcel('all'),'secondary']]);
}
function setCompliance(which,id){
 const key=which==='audit'?'auditFilter':which==='standard'?'stdFilter':'procFilter';
 if($(key)){$(key).value=String(id);$(key).dispatchEvent(new Event('change'))}
}
function displayCompliance(data){
 const safeNum=n=>Number.isFinite(n)?n:0;
 const chart=[
  ['Testlerin tamamlanması',data.completion_pct,'#297bdf',data.completed+' / '+data.total_controls+' kontrol değerlendirildi'],
  ['Başarılı test oranı',data.pass_pct,'#20a08e',data.counts.pass+' başarılı · '+data.counts.fail+' başarısız'],
  ['Olumlu kontrol göstergesi',data.indicative_pct,'#8064cd','Başarılı kontrol / tüm kapsamdaki kontrol']
 ];
 const results=data.controls||[];
 const statText=code=>
  code==='untested'?'Test edilmedi':chosen('executions','status',code);
 $('complianceResult').innerHTML='<div class="notice"><b>'+esc(data.evaluation_type)+'</b> — '+
 esc(data.disclaimer)+'</div>'+
 '<div class="kpirow">'+chart.map(([name,val,color,sub])=>
 '<div class="panel kpi">'+ring(val,color)+'<div><div class="kpi-label">'+esc(name)+'</div>'+
 '<p class="kpi-text">'+esc(sub)+'</p></div></div>').join('')+'</div>'+
 '<div class="cards">'+[
  ['Toplam kontrol',data.total_controls],['Başarılı',data.counts.pass],
  ['Başarısız',data.counts.fail],['Test edilmedi / belirsiz',
    data.counts.untested+data.counts.inconclusive+data.counts.not_applicable]
 ].map(([name,n])=>'<div class="metric"><span class="metric-label">'+esc(name)+'</span>'+
 '<span class="metric-number">'+safeNum(n)+'</span></div>').join('')+'</div>'+
 (typeof data.framework_coverage_pct==='number'?
 '<div class="panel"><h2>Standart maddesi eşleştirmesi</h2>'+
 '<p class="intro">'+data.mapped_clauses+' / '+data.clause_count+
 ' maddede en az bir aktif kontrol var. Eşleştirme tek başına uygunluk anlamına gelmez.</p>'+
 '<div class="progress"><div class="progress-fill" style="width:'+data.framework_coverage_pct+'%"></div></div></div>':'')+
 '<div class="panel"><div class="panel-title"><h2>Kontrol bazında ölçüm</h2>'+
 '<span class="muted">'+data.total_controls+' kontrol</span></div>'+
 '<div class="tablewrap"><table><thead><tr><th>Kontrol kodu</th><th>Kontrol adı</th><th>Son sonuç</th><th>Son kontrol zamanı</th></tr></thead>'+
 '<tbody>'+results.map(x=>'<tr class="clickable" data-control="'+x.id+'"><td class="cell-primary">'+esc(x.code)+'</td>'+
 '<td>'+esc(x.name)+'</td><td>'+esc(statText(x.status))+'</td><td>'+esc(x.executed_at||'—')+'</td></tr>').join('')+
 '</tbody></table>'+(results.length?'':'<div class="empty">Seçilen kapsamda eşleştirilmiş kontrol bulunamadı.</div>')+'</div></div>';
 $('complianceResult').querySelectorAll('[data-control]').forEach(x=>x.onclick=()=>openRecord('controls',Number(x.dataset.control)));
}
function architecturePage(){
 const nodes=[
  {x:24,w:190,title:'Kaynak Sistemler',items:['ServiceNow ITSM','Dynamics 365','CMDB ve keşif','SIEM / altyapı'],color:'#244263'},
  {x:260,w:188,title:'MCP Katmanı',items:['Yetkili sorgulama','Zamanlama','Sonuç üretme'],color:'#116e77'},
  {x:492,w:218,title:'KS GRC Çekirdeği',items:['Standart / maddeler','Kontrol hedefleri','Kontroller / süreçler','Riskler / dokümanlar'],color:'#2856a4'},
  {x:755,w:204,title:'Kanıt Kütüphanesi',items:['Dosya ve SHA-256','Sürüm geçmişi','Çoklu bağlantı','Denetim geçmişi'],color:'#264663'},
  {x:1003,w:195,title:'Güvence ve Takip',items:['Denetimler','Kontrol sonuçları','Bulgular','Düzeltici faaliyet'],color:'#264663'}
 ];
 const svg='<svg viewBox="0 0 1222 540" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">'+
 '<defs><filter id="nodeShadow"><feDropShadow dx="0" dy="8" stdDeviation="8" flood-color="#051729" flood-opacity=".35"/></filter>'+
 '<marker id="headArrow" markerWidth="9" markerHeight="9" refX="8" refY="3" orient="auto">'+
 '<path d="M0 0 L8 3 L0 6 Z" fill="#70c6d8"/></marker></defs>'+
 '<text x="27" y="43" fill="#fff" font-size="28" font-weight="750">KS GRC • Mantıksal Mimari</text>'+
 '<text x="27" y="69" fill="#b6cde0" font-size="13">Sürekli süreç kontrolü, kanıt ve denetim izlenebilirliği</text>'+
 nodes.map(n=>'<g filter="url(#nodeShadow)"><rect x="'+n.x+'" y="120" rx="16" width="'+n.w+'" height="250" fill="'+n.color+
 '" stroke="#7ea7c0"/></g><text x="'+(n.x+n.w/2)+'" y="157" fill="#fff" text-anchor="middle" font-weight="750" font-size="16">'+
 esc(n.title)+'</text>'+n.items.map((item,i)=>'<text x="'+(n.x+n.w/2)+'" y="'+(205+i*32)+
 '" text-anchor="middle" fill="#d7e6f5" font-size="13">'+esc(item)+'</text>').join('')).join('')+
 nodes.slice(0,-1).map((n,i)=>{
  const x1=n.x+n.w+5,x2=nodes[i+1].x-8;
  return '<path d="M'+x1+' 249 L'+x2+' 249" stroke="#70c6d8" stroke-width="3" marker-end="url(#headArrow)"/>';
 }).join('')+
 '<rect x="26" y="421" width="1170" height="85" rx="15" fill="#081c30" stroke="#3c6886"/>'+
 '<text x="46" y="447" fill="#add7e7" font-size="12" font-weight="700">ALTIN KONTROL VE DENETİM ZİNCİRİ</text>'+
 ['Gereklilik','Kontrol hedefi','Kontrol','Kanıt','Test','Bulgu','Düzeltici faaliyet'].map((txt,i)=>
 '<text x="'+(114+i*164)+'" y="483" fill="#f1f9ff" font-size="12" font-weight="650" text-anchor="middle">'+txt+'</text>'+
 (i<6?'<text x="'+(196+i*164)+'" y="483" fill="#5fc4d6" font-size="20" text-anchor="middle">→</text>':'')).join('')+
 '</svg>';
 $('content').innerHTML='<div class="notice"><b>Entegrasyon sınırı:</b> KS GRC, ServiceNow ve Dynamics ile doğrudan bağlantı kurmaz. MCP uygulaması kontrol tarifini okur, ilgili sistemi sorgular ve sonucu API üzerinden GRC’ye yazar.</div>'+
 '<div class="architecture" role="img" aria-label="KS GRC veri akışı mimari şeması">'+svg+'</div>'+
 '<div class="arch-cards">'+[
 ['Bağımsızlık','KS GRC veritabanı, kanıtları ve Docker yaşam döngüsü NILES’tan ayrıdır.'],
 ['Çoktan çoğa ilişki','Bir kontrol birden fazla standart maddesi, süreç ve kontrol hedefini kapsar.'],
 ['Denetim izi','Her kontrol çalışmasındaki ilişkiler saklanır; güncel eşleştirme geçmişi bozmaz.'],
 ['Kanıt zinciri','Kanıt dosyaları sürümlenir, SHA-256 ile doğrulanır, denetime ve kontrollere bağlanır.'],
 ['Uyumluluk','Tamamlanma, başarılı test ve madde kapsaması farklı oranlar olarak gösterilir.'],
 ['Gelişime açık','Risk, talimat, bulgu ve DÖF üzerine iş akışı ve ayrıntılı rol yetkileri eklenebilir.']
 ].map(([t,d])=>'<div class="arch-card"><strong>'+t+'</strong>'+d+'</div>').join('')+'</div>';
 actions([['Uyumluluk panosu',()=>navigate('compliance')],['Kontrol kataloğu',()=>navigate('controls'),'secondary']]);
}
async function adminPage(){
 const data=await api('admin/summary');
 const users=data.users||[];
 $('content').innerHTML='<div class="notice">Şimdilik tüm aktif GRC kullanıcıları eşit uygulama yetkilerine sahiptir. Kullanıcı ve rol tabloları hazır; ayrıntılı rol yetkileri daha sonra etkinleştirilebilir. MCP API erişimi ayrıdır.</div>'+
 '<div class="cards">'+[
 ['Kullanıcı',data.user_count],['Aktif kullanıcı',data.active_users],
 ['Veri şeması',data.schema_version],['Son etkinlik',data.activity.length]
 ].map(([name,value])=>'<div class="metric"><span class="metric-label">'+name+
 '</span><span class="metric-number">'+value+'</span></div>').join('')+'</div>'+
 '<div class="panel"><div class="panel-title"><h2>Kullanıcı yönetimi</h2><button class="btn small" id="newUser">+ Yeni kullanıcı</button></div>'+
 '<div class="tablewrap"><table><thead><tr><th>Kullanıcı adı</th><th>Görünen ad</th><th>Durum</th><th>Son giriş</th><th>İşlem</th></tr></thead>'+
 '<tbody>'+users.map(u=>'<tr><td class="cell-primary">'+esc(u.username)+'</td><td>'+esc(u.display_name)+'</td>'+
 '<td>'+showValue('controls','active',u.is_active)+'</td><td>'+esc(u.last_login_at||'—')+'</td>'+
 '<td><button class="btn secondary small" data-user="'+u.id+'" data-active="'+u.is_active+'">'+
 (u.is_active?'Devre dışı bırak':'Etkinleştir')+'</button></td></tr>').join('')+'</tbody></table></div></div>'+
 '<div class="panel"><h2>Excel ile veri taşıma</h2>'+
 '<p class="intro">Kontrol, denetim, standart, bulgu, risk ve ilişkileri tek XLSX dosyasında aktar. Hesap parolaları ve yüklenen dosyaların ikili içerikleri güvenlik nedeniyle hariçtir.</p>'+
 '<div class="toolbar"><button class="btn secondary" id="allExport">Tümünü Excel’e aktar</button>'+
 '<button class="btn secondary" id="allImport">Excel’den içeri al</button></div></div>'+
 '<div class="panel"><h2>Son yönetim işlemleri</h2><div class="tablewrap"><table>'+
 '<thead><tr><th>İşlemi yapan</th><th>İşlem</th><th>Kayıt türü</th><th>Zaman</th></tr></thead><tbody>'+
 data.activity.map(x=>'<tr><td>'+esc(x.actor)+'</td><td>'+esc(x.method)+'</td><td>'+esc(x.object_type)+'</td>'+
 '<td>'+esc(x.occurred_at)+'</td></tr>').join('')+'</tbody></table></div></div>';
 $('newUser').onclick=userForm;$('allExport').onclick=()=>exportExcel('all');
 $('allImport').onclick=()=>importExcel('all');
 $('content').querySelectorAll('[data-user]').forEach(b=>b.onclick=async()=>{
  const active=b.dataset.active==='0';
  if(!confirm(active?'Kullanıcı etkinleştirilsin mi?':'Kullanıcı devre dışı bırakılsın mı?'))return;
  try{await api('admin/users/'+b.dataset.user,{method:'PATCH',
   body:JSON.stringify({is_active:active?1:0})});
   toast('Kullanıcı güncellendi');adminPage()
  }catch(e){toast(e.message,false)}
 });
 actions([['Yeni kullanıcı',userForm],['Excel yedeği',()=>exportExcel('all'),'secondary']]);
}
function userForm(){
 drawer('Yeni GRC kullanıcısı','<div class="notice">Tüm kullanıcıların yetkisi şimdilik eşittir. Geçici parola yalnızca bir defa görüntülenir ve ilk girişte değiştirilmesi zorunludur.</div>'+
 '<label class="field">Kullanıcı adı<input id="newUsername" placeholder="ad.soyad"></label>',
 [['Kullanıcı oluştur',async()=>{
  try{const data=await api('admin/users',{method:'POST',
   body:JSON.stringify({username:$('newUsername').value.trim()})});
   drawer('Kullanıcı oluşturuldu','<div class="notice success">'+esc(data.username)+' kaydedildi.</div>'+
   '<p class="intro">Geçici parolayı kurumun güvenli kanalıyla ilet. Bir daha görüntülenemez.</p>'+
   '<label class="field">Geçici parola<input id="newPassword" readonly value="'+esc(data.temporary_password)+'"></label>',
   [['Parolayı kopyala',async()=>{
    try{await navigator.clipboard.writeText(data.temporary_password);toast('Parola kopyalandı')}
    catch{toast('Panoya kopyalanamadı',false)}},
   ],['Kapat',()=>{closeDetail();adminPage()},'secondary']]);
  }catch(e){toast(e.message,false)}
 }],['Vazgeç',closeDetail,'secondary']]);
}
async function start(){
 try{
  STATE.meta=await api('metadata');
  const user=await api('me');$('identity').textContent='Oturum • '+(user.username||'GRC');
  $('signout').onclick=async()=>{try{await api('logout',{method:'POST',body:'{}'});location.assign('/login')}
   catch(e){toast(e.message,false)}};
  $('closeDetail').onclick=closeDetail;
  document.addEventListener('keydown',event=>{if(event.key==='Escape'&&STATE.detail)closeDetail()});
  const route=decodeURIComponent((location.hash||'#/home').replace('#/','')).split('/')[0];
  await navigate(LABELS[route]?route:'home');
 }catch(e){$('content').innerHTML='<div class="notice warn">'+esc(e.message)+'</div>'}
}
start();
