'use strict';
/* KS GRC v2: Turkish-only browser, authenticated same-origin API, no external dependencies. */
const $=id=>document.getElementById(id);
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const LABELS={home:'Genel Bakış',compliance:'Uyumluluk Panosu',architecture:'Mimari Harita',admin:'Yönetim',
 controls:'Kontroller',objectives:'Kontrol Hedefleri',audits:'Denetimler',findings:'Bulgular',
 evidence:'Kanıt Kütüphanesi',executions:'Kontrol Sonuçları',standards:'Standartlar',
 clauses:'Standart Maddeleri',processes:'Süreçler',risks:'Riskler',risk_catalog:'Risk Kataloğu',actions:'Düzeltici Faaliyetler',documents:'Dokümanlar'};
const MENU=[
 ['GENEL',[['home','▦'],['compliance','◉']]],
 ['KONTROL VE GÜVENCE',[['controls','☑'],['objectives','◇'],['audits','▤'],['findings','⚑'],['evidence','▱'],['executions','✓']]],
 ['KURUMSAL KATALOG',[['standards','◫'],['clauses','≡'],['processes','⇄'],['risk_catalog','◈'],['risks','△'],['actions','↗'],['documents','▧']]],
 ['SİSTEM',[['architecture','⌘'],['admin','⚙']]]
];
const COLUMNS={
 controls:['code','name','execution_mode','nature','frequency','owner'],
 objectives:['code','name','description'],audits:['name','planned_start','planned_end','status'],
 findings:['title','control_id','severity','status'],evidence:['title','file_name','source','status','collected_at'],
 executions:['control_id','status','source','executed_at'],standards:['code','name','version'],
 clauses:['code','title','standard_id'],processes:['code','name','owner'],
 risk_catalog:['code','title','category'],risks:['code','title','entity_name','owner','inherent_score','residual_score','review_date','status'],actions:['code','title','finding_id','due_date','status'],
 documents:['code','title','category','version','status']};
const FORM={
 standards:['code','name','version','description'],clauses:['standard_id','code','title','parent_id','description'],
 processes:['code','name','owner','description'],objectives:['code','name','description'],
 controls:['code','name','description','execution_mode','nature','frequency','criticality','method_type','method','expected_result','owner','active'],
 audits:['name','audit_objective','conclusion','scope','planned_start','planned_end','actual_start','actual_end','auditors','auditees','status'],
 evidence:['title','description','reference_url','source','confidentiality','status','period_start','period_end','expires_at'],
 findings:['title','control_id','audit_id','severity','status','description'],
 risk_catalog:['code','title','category','cause','risk_event','consequence','likelihood','impact'],
 risks:['code','title','description','catalog_id','entity_name','category','cause','risk_event','consequence','likelihood','impact','appetite','owner','status','response_strategy','treatment','due_date','review_date'],
 actions:['code','title','description','finding_id','risk_id','control_id','owner','due_date','priority','status','resolution'],
 documents:['code','title','description','category','version','owner','status','reference_url']};
const REQUIRED={standards:['code','name'],clauses:['standard_id','code','title'],processes:['code','name'],
 objectives:['code','name'],controls:['code','name'],audits:['name'],evidence:['title'],findings:['title'],
 risk_catalog:['code','title','cause','risk_event','consequence'],risks:['code','title'],actions:['code','title'],documents:['code','title']};
const REFS={catalog_id:'risk_catalog',risk_id:'risks',standard_id:'standards',parent_id:'clauses',control_id:'controls',audit_id:'audits',finding_id:'findings'};
const DATES=new Set(['review_date','planned_start','planned_end','actual_start','actual_end','due_date','period_start','period_end','expires_at']);
const TEXTAREAS=new Set(['cause','risk_event','consequence','description','scope','audit_objective','conclusion','method','expected_result','treatment','resolution']);
const STATE={view:'home',cache:{},meta:{fields:{},choices:{}},search:'',page:0,detail:null,record:null,trail:[]};
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
 $('detailTitle').textContent=title;$('detailContent').innerHTML=html;$('detailContent').scrollTop=0;
 $('detailFooter').innerHTML='';
 for(const [name,callback,variant] of buttons){
  const b=document.createElement('button');b.type='button';b.className='btn '+(variant||'');
  b.textContent=name;b.onclick=async()=>{if(b.disabled)return;b.disabled=true;try{await callback()}catch(e){toast(e.message,false)}finally{b.disabled=false}};$('detailFooter').append(b)
 }
 $('detail').classList.add('open');$('main').classList.add('details-open');
 $('detail').setAttribute('aria-hidden','false');$('detail').inert=false;STATE.detail={title};
 applyDetailWidth();markSelectedRow();
}
function closeDetail(){
 $('detail').classList.remove('open');$('main').classList.remove('details-open');
 $('detail').setAttribute('aria-hidden','true');$('detail').inert=true;STATE.detail=null;STATE.record=null;STATE.trail=[];markSelectedRow()
}

function markSelectedRow(){
 $('content')?.querySelectorAll('[data-row]').forEach(row=>{
  const selected=!!STATE.detail&&STATE.record?.table===STATE.view&&Number(row.dataset.row)===STATE.record.id;
  row.classList.toggle('selected-row',selected);
  if(selected)row.setAttribute('aria-current','true');else row.removeAttribute('aria-current');
 });
}
let detailPreference=null;
try{const n=Number(localStorage.getItem('ksgrc.detailWidth'));if(n>=360&&n<=4000)detailPreference=n}catch{}
function detailBounds(){
 const sidebar=window.innerWidth>800?244:0;
 return {min:360,max:Math.max(360,window.innerWidth-sidebar-390)};
}
function applyDetailWidth(value=detailPreference,persist=false){
 const {min,max}=detailBounds();
 const width=Math.round(Math.min(max,Math.max(min,value??540)));
 document.documentElement.style.setProperty('--detail-width',width+'px');
 const grip=$('detailResize');
 if(grip){
  grip.setAttribute('aria-valuemin',String(min));grip.setAttribute('aria-valuemax',String(max));
  grip.setAttribute('aria-valuenow',String(width));grip.setAttribute('aria-valuetext',width+' piksel genişlik');
 }
 if(persist){detailPreference=width;try{localStorage.setItem('ksgrc.detailWidth',String(width))}catch{}}
 return width;
}
function setupDetailResize(){
 const grip=$('detailResize');if(!grip)return;
 let drag=null;
 const finish=()=>{drag=null;document.body.classList.remove('resizing-detail')};
 grip.addEventListener('pointerdown',event=>{
  if(event.button!==0||window.innerWidth<=1000)return;
  event.preventDefault();grip.focus();
  drag={id:event.pointerId,x:event.clientX,width:$('detail').getBoundingClientRect().width};
  grip.setPointerCapture(event.pointerId);document.body.classList.add('resizing-detail');
 });
 grip.addEventListener('pointermove',event=>{
  if(drag&&event.pointerId===drag.id)applyDetailWidth(drag.width+drag.x-event.clientX,true);
 });
 grip.addEventListener('pointerup',event=>{
  if(drag&&grip.hasPointerCapture(event.pointerId))grip.releasePointerCapture(event.pointerId);finish();
 });
 grip.addEventListener('pointercancel',finish);grip.addEventListener('lostpointercapture',finish);
 grip.addEventListener('dblclick',()=>applyDetailWidth(540,true));
 grip.addEventListener('keydown',event=>{
  const current=$('detail').getBoundingClientRect().width,step=event.shiftKey?80:24;
  const {min,max}=detailBounds();
  const value={ArrowLeft:current+step,ArrowRight:current-step,Home:min,End:max,Enter:540}[event.key];
  if(value!==undefined){event.preventDefault();applyDetailWidth(value,true)}
 });
 window.addEventListener('resize',()=>{finish();applyDetailWidth()});
 applyDetailWidth();
}
function relatedRecords(table,items,format=titleOf){
 return items?.length?'<ul class="relationship-list">'+items.map(item=>
  '<li><button type="button" class="record-link" data-related-table="'+table+'" data-related-id="'+item.id+'">'+
  '<span>'+esc(format(item))+'</span><span aria-hidden="true">›</span></button></li>').join('')+'</ul>':
  '<p class="muted relationship-empty">Henüz ilişki bulunmuyor.</p>';
}
function setupRelatedNavigation(){
 $('detailContent').addEventListener('click',event=>{
  const link=event.target.closest('[data-related-table]');if(!link)return;
  const table=link.dataset.relatedTable,id=Number(link.dataset.relatedId);
  if(!LABELS[table]||!Number.isInteger(id)||id<1)return;
  event.preventDefault();
  if(STATE.record)STATE.trail.push({...STATE.record});
  openRecord(table,id,true);
 });
}
async function detailObjective(rec,basic,footer){
 const ctx=await api('objectives/'+rec.id+'/context');
 const html='<div class="notice">Kontroller bu hedefe <b>doğrudan</b> bağlıdır. Standart maddeleri ve süreçler, bu kontrollerin güncel eşlemelerinden türetilir; ayrı bir doğrudan hedef–madde veya hedef–süreç kaydı değildir.</div>'+basic+
 '<section class="detail-section" id="objectiveControls"><h3>Bağlı kontroller ('+ctx.controls.length+') <span class="pill">Doğrudan</span></h3>'+
 relatedRecords('controls',ctx.controls,x=>x.code+' — '+x.name)+'</section>'+
 '<section class="detail-section" id="objectiveClauses"><h3>Standart maddeleri ('+ctx.clauses.length+') <span class="pill">Kontroller üzerinden</span></h3>'+
 relatedRecords('clauses',ctx.clauses,x=>x.standard_code+' • '+x.code+' — '+x.title)+'</section>'+
 '<section class="detail-section" id="objectiveProcesses"><h3>Süreçler ('+ctx.processes.length+') <span class="pill">Kontroller üzerinden</span></h3>'+
 relatedRecords('processes',ctx.processes,x=>x.code+' — '+x.name)+'</section>';
 drawer('Kontrol hedefi • '+rec.code,html,[['Kontrol bağlantılarını düzenle',()=>objectiveLinks(rec.id)],...footer]);
}
async function objectiveLinks(id){
 const [ctx,controls]=await Promise.all([api('objectives/'+id+'/context'),list('controls',true)]);
 drawer('Hedefin kontrol bağlantıları',
  '<div class="notice">Yalnızca bu hedefin kontrol bağlantıları değişir. Geçmiş kontrol çalışmalarının kayıtları korunur.</div>'+
  checks('objective_controls','Bağlı kontroller',controls,ctx.controls,x=>x.code+' — '+x.name),
 [['Bağlantıları kaydet',async()=>{
  await api('objectives/'+id+'/controls',{method:'POST',body:JSON.stringify({control_ids:selected('objective_controls')})});
  toast('Kontrol hedefi bağlantıları kaydedildi');await openRecord('objectives',id,true);
 }],['Vazgeç',()=>openRecord('objectives',id,true),'secondary']]);bindChecks();
}
function auditFindingsSection(id,title,items,note){
 return '<section class="detail-section" id="'+id+'"><h3>'+title+' ('+items.length+')</h3>'+
 '<p class="intro">'+esc(note)+'</p>'+(items.length?'<ul class="relationship-list">'+items.map(f=>
 '<li class="finding-card"><button type="button" class="record-link" data-related-table="findings" data-related-id="'+f.id+'">'+
 '<span>#'+f.id+' — '+esc(f.title)+'</span><span aria-hidden="true">›</span></button>'+
 '<div class="finding-meta">'+showValue('findings','severity',f.severity)+' '+showValue('findings','status',f.status)+'</div>'+
 '<div class="finding-origin">Kontrol: '+(f.effective_control_id?'<button class="inline-record-link" data-related-table="controls" data-related-id="'+f.effective_control_id+'">'+esc(f.control_code||('#'+f.effective_control_id))+'</button>':'Bağlı kontrol yok')+
 ' · Kaynak: '+(f.origin_audit_id?'<button class="inline-record-link" data-related-table="audits" data-related-id="'+f.origin_audit_id+'">'+esc(f.origin_audit_name||('#'+f.origin_audit_id))+'</button>':'Denetim dışı')+'</div></li>').join('')+'</ul>':
 '<p class="muted relationship-empty">Bu grupta bulgu bulunmuyor.</p>')+'</section>';
}

function actions(buttons){$('topActions').innerHTML='';for(const [text,handler,variant] of buttons){
 const b=document.createElement('button');b.className='btn '+(variant||'');b.textContent=text;b.onclick=handler;
 $('topActions').append(b)}}
function canManage(){return STATE.user?.app_role !== 'KS.GRC.Auditor'}
function navigation(){
 $('nav').innerHTML=MENU.map(([group,items])=>'<div class="nav-title">'+esc(group)+'</div>'+
 items.filter(([v])=>v!=='admin'||canManage()).map(([v,ico])=>'<button class="nav-button '+(v===STATE.view?'active':'')+'" data-nav="'+v+'"><span class="nav-icon">'+ico+'</span>'+LABELS[v]+'</button>').join('')).join('');
 $('nav').querySelectorAll('[data-nav]').forEach(b=>b.onclick=()=>navigate(b.dataset.nav));
}
async function navigate(view){
 if(STATE.mapObserver){STATE.mapObserver.disconnect();STATE.mapObserver=null}
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
 const today=new Date().toLocaleDateString('sv-SE');
 const matchesRisk=r=>{switch(STATE.riskFilter){
  case 'above':return r.residual_score!=null&&r.residual_score>r.assessed_appetite;
  case 'pending':return r.residual_score==null;
  case 'late':return r.status!=='closed'&&r.review_date&&r.review_date<today;
  default:return true;
 }};
 const results=source.filter(r=>table!=='risks'||matchesRisk(r)).filter(x=>Object.values(x).some(v=>String(v??'').toLocaleLowerCase('tr').includes(term)));
 STATE.page=Math.min(STATE.page,Math.max(0,Math.ceil(results.length/PER_PAGE)-1));
 const items=results.slice(STATE.page*PER_PAGE,(STATE.page+1)*PER_PAGE);
 const cols=COLUMNS[table]||['code','title','status'];
 return '<div class="panel"><div class="panel-title"><h2>'+LABELS[table]+' <span class="muted">('+results.length+')</span></h2>'+
 '<span class="badge-note">Ayrıntı için satıra tıklayın · Enter ile de açılır</span></div><div class="toolbar">'+
 (table==='risks'?'<label class="field">Risk görünümü<select id="riskFilter">'+
  Object.entries({all:'Tüm riskler',above:'Son değerlendirmede iştahı aşanlar',pending:'Değerlendirme bekleyenler',late:'Gözden geçirmesi gecikenler'}).map(([v,t])=>
   '<option value="'+v+'" '+(v===STATE.riskFilter?'selected':'')+'>'+t+'</option>').join('')+'</select></label>':'')+
 '<input id="tableSearch" class="searchbar" placeholder="Kayıt, kod veya açıklama ara…" value="'+esc(STATE.search)+'" aria-label="Kayıtlarda ara">'+
 '<div class="toolbar"><button class="btn secondary small" id="tableExport"'+(canManage()?'':' hidden')+'>Excel’e aktar</button>'+
 '<button class="btn secondary small" id="tableImport"'+(canManage()?'':' hidden')+'>Excel’den aktar</button></div></div>'+
 '<div class="tablewrap"><table><thead><tr>'+cols.map(c=>'<th>'+esc(label(c))+'</th>').join('')+'</tr></thead><tbody>'+
 items.map(x=>'<tr class="clickable" tabindex="0" aria-label="'+esc(titleOf(x)+' — ayrıntı')+'" data-row="'+x.id+'">'+cols.map((c,i)=>'<td'+(i===0?' class="cell-primary"':'')+'>'+showValue(table,c,x[c])+'</td>').join('')+
 '</tr>').join('')+
 '</tbody></table>'+(results.length?'':'<div class="empty">Kayıt bulunamadı. Yeni bir kayıt ekleyebilir veya arama filtresini temizleyebilirsin.</div>')+'</div>'+
 '<div class="pager"><span>'+(results.length?STATE.page*PER_PAGE+1:0)+'–'+Math.min(results.length,(STATE.page+1)*PER_PAGE)+
 ' / '+results.length+'</span><div><button class="btn ghost small" id="prev" '+(STATE.page===0?'disabled':'')+'>Önceki</button>'+
 '<button class="btn ghost small" id="next" '+((STATE.page+1)*PER_PAGE>=results.length?'disabled':'')+'>Sonraki</button></div></div></div>';
}
function bindTable(table){
 if($('riskFilter'))$('riskFilter').onchange=e=>{STATE.riskFilter=e.target.value;STATE.page=0;refreshTable(table)};
 const input=$('tableSearch');input.oninput=e=>{
  const position=e.target.selectionStart;STATE.search=e.target.value;STATE.page=0;
  $('content').innerHTML=tableHTML(table,STATE.cache[table]);bindTable(table);
  $('tableSearch').focus();$('tableSearch').setSelectionRange(position,position);
 };
 $('tableExport').onclick=()=>exportExcel(table);$('tableImport').onclick=()=>importExcel(table);
 $('prev').onclick=()=>{STATE.page--;refreshTable(table)};$('next').onclick=()=>{STATE.page++;refreshTable(table)};
 $('content').querySelectorAll('[data-row]').forEach(row=>{
  const activate=()=>openRecord(table,Number(row.dataset.row));
  row.onclick=event=>{
   if(event.target.closest('button,a,input,select,textarea')||window.getSelection()?.toString())return;
   activate();
  };
  row.onkeydown=event=>{if(event.target===row&&(event.key==='Enter'||event.key===' ')){
   event.preventDefault();activate();
  }};
 });
 markSelectedRow();
}
function refreshTable(table){$('content').innerHTML=tableHTML(table,STATE.cache[table]||[]);bindTable(table)}
async function renderTable(table){
 const records=await list(table,true);
 $('content').innerHTML=tableHTML(table,records);bindTable(table);
 actions(table==='executions'?[['Kontrol sonucu kaydet',()=>executionForm()]]:
  table==='evidence'?[['Kanıt yükle',()=>evidenceForm()]]:
  [[table==='audits'?'+ Yeni denetim':'+ Yeni kayıt',()=>createForm(table)],...(canManage()?[['Excel’e aktar',()=>exportExcel(table),'secondary']]:[])]);
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
  inner='<select data-field="'+key+'"'+required+'>'+(key==='response_strategy'?'<option value="">Henüz seçilmedi</option>':'')+Object.entries(options).map(([v,t])=>
   '<option value="'+esc(v)+'"'+(String(value??'')===v?' selected':'')+'>'+esc(t)+'</option>').join('')+'</select>';
 }else if(REFS[key]){
  const refs=await list(REFS[key]);
  inner='<select data-field="'+key+'"'+required+'><option value="">Seçiniz</option>'+
   refs.map(x=>'<option value="'+x.id+'"'+(Number(value)===x.id?' selected':'')+'>'+esc((x.code?x.code+' — ':'')+titleOf(x))+'</option>').join('')+'</select>';
 }else if(TEXTAREAS.has(key)){
  inner='<textarea data-field="'+key+'">'+esc(value||'')+'</textarea>';
 }else if(key==='appetite'){
  inner='<input data-field="appetite" type="number" min="1" max="25" step="1" placeholder="1–25" value="'+esc(value??'')+'">';
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
  if(['active','likelihood','impact','appetite'].includes(key)&&value!=='')value=Number(value);
  if(value!==''&&value!==null)result[key]=value;
 }
 if(missing.length)throw Error('Zorunlu alanlar: '+missing.join(', '));
 return result;
}
async function createForm(table,defaults={}){
 if(table==='audits')return auditForm();
 if(table==='risks')return riskForm();
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
 if(table==='audits')return auditForm(record.id);
 if(table==='risks')return riskForm(record);
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
async function openRecord(table,id,keepTrail=false){
 try{
  if(!keepTrail)STATE.trail=[];
  STATE.record={table,id};
  const record=(await list(table,true)).find(x=>x.id===id);
  if(!record)throw Error('Kayıt bulunamadı');
  const html='<div class="detail-section"><h3>Kayıt bilgileri</h3>'+values(table,record)+'</div>';
  const footer=FORM[table]?[['Düzenle',()=>editForm(table,record),'secondary'],['Kapat',closeDetail,'secondary']]:
   [['Kapat',closeDetail,'secondary']];
  if(STATE.trail.length)footer.unshift(['← Önceki kayıt',()=>{const previous=STATE.trail.pop();return openRecord(previous.table,previous.id,true)},'secondary']);
  if(table==='objectives')return detailObjective(record,html,footer);
  if(table==='controls')return detailControl(record,html,footer);
  if(table==='audits')return detailAudit(record,html,footer);
  if(table==='evidence')return detailEvidence(record,html,footer);
  if(table==='findings'||table==='executions')return detailExecution(table,record,html,footer);
  if(table==='risk_catalog')return drawer('Katalog • '+record.title,html,[['Bu şablondan risk aç',()=>riskForm(null,record)],...footer]);
  if(table==='risks'){await list('risk_catalog');return riskDetail(record,footer)}
  if(table==='documents')return detailLinked(table,record,html,footer);
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
 const [ctx,evidence,all]=await Promise.all([
  api('audits/'+rec.id+'/context'),api('audits/'+rec.id+'/evidence'),list('evidence',true)]);
 const scopeHtml='<section class="detail-section" id="auditCriteria"><h3>Denetim kriterleri</h3>'+
  (ctx.standards.length?chips(ctx.standards,s=>s.code):'<p class="muted">Standart seçilmemiş.</p>')+'</section><details class="detail-section"><summary>Kapsamdaki standart maddeleri ('+ctx.clauses.length+')</summary>'+
  relatedRecords('clauses',ctx.clauses,c=>c.standard_code+' '+c.code+' — '+c.title)+'</details>';
 const findings=auditFindingsSection('auditFindings','Bu denetimin bulguları',ctx.findings,
  'Doğrudan bu denetime veya bu denetimdeki kontrol çalışmasına bağlı bulgular; kapalı kayıtlar da dahildir.')+
  auditFindingsSection('auditOtherFindings','Kapsamdaki kontrollerin diğer açık bulguları',ctx.other_open_findings,
  'Başka denetimlerden veya denetim dışı çalışmalardan gelen açık bulgular. Bu denetimde açılmış sayılmaz; kaynak bağlantısı korunur.');
 const planNote=ctx.plan_captured_at?'Kontrol kapsamı kaydedildi · '+esc(ctx.plan_captured_at):
  ['closed','completed','cancelled'].includes(rec.status)?'Kapanış anına ait kapsam kaydı bulunmuyor. Kontrol eşlemeleri güncel katalogdan gösterilir.':'Planlanan kontroller kapsam maddelerinin güncel eşlemelerinden gelir.';
 const linked=checks('audit_evidence','Bu denetimin kanıtları',all,evidence,x=>x.title);
 drawer('Denetim • '+rec.name,
 '<div class="notice"><b>'+ctx.finding_summary.total+' bulgu</b> · '+ctx.finding_summary.open+' açık · '+ctx.finding_summary.other_open+' diğer açık bulgu</div>'+scopeHtml+basic+findings+
 '<details class="detail-section"><summary>Kapsamdaki kontroller ('+ctx.planned_controls.length+')</summary>'+
 '<p class="intro">'+planNote+'</p>'+relatedRecords('controls',ctx.planned_controls,c=>c.code+' — '+c.name)+'</details>'+
 (ctx.tested_outside_scope.length?'<details class="detail-section"><summary>Kapsam dışında çalıştırılan kontroller ('+ctx.tested_outside_scope.length+')</summary>'+relatedRecords('controls',ctx.tested_outside_scope,c=>c.code+' — '+c.name)+'</details>':'')+linked,
 [['Kanıtları kaydet',async()=>{
  await api('audits/'+rec.id+'/evidence',{method:'POST',body:JSON.stringify({evidence_ids:selected('audit_evidence')})});
  toast('Denetim kanıtları kaydedildi');await openRecord('audits',rec.id,true);
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
 [['Bu standart için denetim başlat',()=>auditForm(null,rec.id)],...footer]);
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
async function auditForm(id=null,preselected=null){
 const [catalog,rec]=await Promise.all([api('audits/scope-catalog'),id?api('audits/'+id+'/context'):{}]);
 const locked=['completed','closed','cancelled'].includes(rec.status);
 const standards=new Set(rec.standards?.map(s=>s.id)||(preselected?[preselected]:[]));
 const clauses=new Set(rec.clauses?.map(c=>c.id)||catalog.clauses.filter(c=>c.standard_id===preselected).map(c=>c.id));
 const fields=async keys=>(await Promise.all(keys.map(k=>fieldInput('audits',k,rec[k])))).join('');
 const name=(await fields(['name'])).replace('data-field="name"','id="auditName" data-field="name"');
 const html='<div class="formgrid">'+name+await fields(['status','audit_objective'])+'</div>'+
  '<section class="detail-section"><h3>Denetim kriterleri</h3><p class="intro">'+
  (locked?'Bu aşamada denetim kapsamı kilitlidir.':'Bir veya birden fazla standart seçin. Seçilen standardın mevcut maddeleri kapsama eklenir. İsterseniz maddeleri tek tek çıkarabilirsiniz.')+'</p>'+
  '<div id="auditStandards">'+(catalog.standards.map(s=>'<label class="link-option"><input type="checkbox" data-std="'+s.id+'" '+
    (standards.has(s.id)?'checked ':'')+(locked?'disabled':'')+'><span>'+esc(s.code+' — '+s.name)+'</span></label>').join('')||'Standart kataloğu boş.')+'</div>'+
  '<div id="auditClauses"></div></section><div class="formgrid">'+await fields(['scope','planned_start','planned_end','actual_start','actual_end','auditors','auditees','conclusion'])+'</div>';
 drawer(id?'Denetim planını düzenle':'Yeni denetim',html,[[id?'Değişiklikleri kaydet':'Denetimi oluştur',async()=>{
  const payload=formValues('audits',FORM.audits);
  if(id){
   for(const k of FORM.audits)if(rec[k]&&!payload[k])payload[k]='';
   payload.expected_revision=rec.revision;
  }
  if(!locked){payload.standard_ids=[...standards];payload.clause_ids=[...clauses]}
  const result=await api(id?'audits/'+id:'audits',{method:id?'PATCH':'POST',body:JSON.stringify(payload)});
  invalidate('audits');await navigate('audits');await openRecord('audits',id||result.id);toast('Denetim kaydedildi');
 }],['Vazgeç',()=>id?openRecord('audits',id,true):closeDetail(),'secondary']]);
 if(locked)$('detailContent').querySelector('[data-field=scope]').disabled=true;
 const render=()=>{
  $('auditClauses').innerHTML=catalog.standards.filter(s=>standards.has(s.id)).map(s=>{
   const items=catalog.clauses.filter(c=>c.standard_id===s.id);
   return '<details class="detail-section" open><summary>'+esc(s.code)+' · <span data-count="'+s.id+'"></span></summary>'+
    (items.length?'<div class="toolbar"><button type="button" class="btn ghost small" data-all="'+s.id+'" '+(locked?'disabled':'')+'>Tümünü seç</button>'+
     '<button type="button" class="btn ghost small" data-none="'+s.id+'" '+(locked?'disabled':'')+'>Seçimi temizle</button></div>'+
     checks('scope_'+s.id,'Kapsamdaki maddeler',items,[...clauses],c=>c.code+' — '+c.title):'<p>Bu standardın katalogda maddesi yok.</p>')+'</details>';
  }).join('');
  if(locked)$('auditClauses').querySelectorAll('input[type=checkbox]').forEach(el=>el.disabled=true);
  bindChecks();count();
 };
 const count=()=>$('auditClauses').querySelectorAll('[data-count]').forEach(el=>{
  const items=catalog.clauses.filter(c=>c.standard_id===Number(el.dataset.count));
  el.textContent=items.filter(c=>clauses.has(c.id)).length+' / '+items.length+' madde seçildi';
 });
 $('auditStandards').onchange=e=>{
  const sid=Number(e.target.dataset.std);if(!sid||locked)return;
  if(e.target.checked)standards.add(sid);else standards.delete(sid);
  for(const c of catalog.clauses.filter(c=>c.standard_id===sid)){if(e.target.checked)clauses.add(c.id);else clauses.delete(c.id)}
  render();
 };
 $('auditClauses').onchange=e=>{if(!e.target.dataset.link||locked)return;
  const cid=Number(e.target.value);if(e.target.checked)clauses.add(cid);else clauses.delete(cid);count()};
 $('auditClauses').onclick=e=>{
  const {all,none}=e.target.dataset;if(!(all||none)||locked)return;
  const sid=Number(all||none);
  for(const c of catalog.clauses.filter(c=>c.standard_id===sid)){if(all)clauses.add(c.id);else clauses.delete(c.id)}
  render();
 };
 render();
}

async function riskForm(record=null,template=null){
 const catalogs=await list('risk_catalog',true);
 const rec=record||{}, seed=template||{};
 const defaults={...seed,code:'',catalog_id:template?.id,...rec};
 const keys=FORM.risks;
 const field=async k=>fieldInput('risks',k,defaults[k]);
 const group=async(title,items)=>'<section class="detail-section"><h3>'+title+'</h3><div class="formgrid">'+(await Promise.all(items.map(field))).join('')+'</div></section>';
 const html='<p class="intro">Katalogdan bir senaryo seçebilir veya bu varlığa özgü bir risk yazabilirsiniz.</p>'+
  await group('Risk kaydı',['catalog_id','code','title','entity_name','category','owner'])+
  await group('Risk ifadesi',['cause','risk_event','consequence'])+
  '<p id="riskPreview" class="notice" aria-live="polite"></p>'+
  await group('İçsel risk ve iştah',['likelihood','impact','appetite'])+
  await group('İşleme ve takip',['response_strategy','treatment','due_date','review_date','status','description']);
 const control=k=>$('detailContent').querySelector('[data-field="'+k+'"]');
 drawer(record?'Riski düzenle':'Yeni risk kaydı',html,[['Kaydet',async()=>{
  const data=formValues('risks',keys);
  for(const k of ['entity_name','cause','risk_event','consequence','owner'])
   if(!data[k])throw Error(label(k)+' gerekli');
  if(record)for(const k of keys)if(rec[k]!=null&&!(k in data))data[k]=['catalog_id','appetite'].includes(k)?null:'';
  const res=await api(record?'risks/'+record.id:'risks',{method:record?'PATCH':'POST',body:JSON.stringify(data)});
  invalidate('risks');await navigate('risks');await openRecord('risks',record?.id||res.id);toast('Risk kaydedildi');
 }],['Vazgeç',()=>record?openRecord('risks',record.id):closeDetail(),'secondary']]);
 for(const option of [...control('status').options])if(['accepted','closed'].includes(option.value))option.remove();
 if(!record&&!defaults.response_strategy)control('response_strategy').value='';
 const preview=()=>{$('riskPreview').textContent=['cause','risk_event','consequence'].map(k=>control(k).value.trim()).filter(Boolean).join(' → ')||'Neden, olay ve iş etkisini girince risk ifadesi burada görünür.'};
 for(const k of ['cause','risk_event','consequence'])control(k).oninput=preview;
 if(record)control('catalog_id').disabled=true;
 control('catalog_id').onchange=()=>{
  const t=catalogs.find(c=>c.id===Number(control('catalog_id').value));if(!t)return;
  for(const k of ['title','category','cause','risk_event','consequence','likelihood','impact'])control(k).value=t[k];
  preview();
 };
 preview();
}
async function riskDetail(rec,footer){
 const [ctx,all]=await Promise.all([api('risks/'+rec.id+'/context'),list('controls',true)]);
 const score=ctx.assessments[0], statement=[rec.cause,rec.risk_event,rec.consequence].filter(Boolean).map(esc).join(' → ');
 const panel='<section class="detail-section"><h3>'+esc(rec.title)+'</h3><p>'+ (statement||'Risk ifadesi henüz girilmedi.')+'</p>'+
  '<p>'+esc(rec.entity_name||'Varlık / hizmet belirtilmedi')+' · '+esc(rec.owner||'Risk sahibi atanmadı')+'</p>'+
  '<div class="notice"><b>Güncel içsel risk '+(rec.likelihood*rec.impact)+' / 25</b> · Son değerlendirilen artık risk '+
  (score?esc(score.residual)+' / 25':'henüz değerlendirilmedi')+'</div>'+
  (score?'<p>Değerlendirme tarihindeki iştah eşiği '+score.appetite+' · '+(score.residual>score.appetite?'İştah aşıldı':'Eşik içinde')+'</p>':'')+'</section>';
 const history=ctx.assessments.map(a=>'<details class="detail-section"><summary>'+esc(a.assessed_at)+' · Artık risk '+a.residual+' / 25</summary>'+
  '<p>'+esc(a.assessor)+' · '+esc(a.rationale)+'</p><p>İçsel '+a.inherent+' · İştah '+a.appetite+' · Varlık / hizmet '+esc(a.snapshot.entity_name)+'</p>'+
  '<p>'+esc([a.snapshot.cause,a.snapshot.risk_event,a.snapshot.consequence].join(' → '))+'</p>'+
  a.snapshot.credits.map(c=>'<div>'+esc(c.code)+' · Çalışma #'+c.run_id+' · Katkı %'+Math.round(100*c.contribution)+'</div>').join('')+'</details>').join('');
 const sealed=['accepted','closed'].includes(rec.status);
 const decisionHistory=(ctx.decisions||[]).map(d=>'<li><b>'+esc(chosen('risks','status',d.to_status))+'</b> · '+esc(d.actor)+' · '+esc(d.decided_at)+
  '<p>'+esc(d.rationale)+'</p>'+(d.exception_rationale?'<p>İştah istisnası · '+esc(d.exception_rationale)+'</p>':'')+
  (d.assessment_id?'<small>Dayanak değerlendirme #'+d.assessment_id+'</small>':'')+'</li>').join('');
 const decisionButtons=sealed?[['Yeniden aç',()=>riskDecision(rec,ctx,'open')]]:[
  ['Kabul kararı',()=>riskDecision(rec,ctx,'accepted'),'secondary'],['Kapanış kararı',()=>riskDecision(rec,ctx,'closed'),'secondary']];
 const k=['catalog_id','description','category','response_strategy','treatment','due_date','review_date','status'];
 const facts=Object.fromEntries(k.map(key=>[key,rec[key]]));
 drawer('Risk • '+rec.code,panel+values('risks',facts)+
  '<section class="detail-section"><h3>Karar geçmişi</h3>'+(decisionHistory?'<ul class="mini-list">'+decisionHistory+'</ul>':'<p>Henüz karar kaydı yok.</p>')+'</section>'+
  '<section class="detail-section"><h3>Risk işleme faaliyetleri</h3>'+relatedRecords('actions',ctx.actions)+'</section>'+
  '<section class="detail-section"><h3>Değerlendirme geçmişi</h3>'+(history||'<p>Kaydedilmiş değerlendirme yok.</p>')+'</section>'+
  (sealed?relatedRecords('controls',ctx.controls):checks('related_controls','Riski azaltan kontroller',all,ctx.controls,x=>x.code+' — '+x.name)),
  [...(sealed?[]:[
   ['Riski değerlendir',()=>riskAssess(rec)],['İşleme faaliyeti aç',()=>createForm('actions',{risk_id:rec.id,owner:rec.owner}),'secondary'],
   ['Kontrolleri kaydet',async()=>{
    await api('risks/'+rec.id+'/controls',{method:'POST',body:JSON.stringify({control_ids:selected('related_controls')})});
    await openRecord('risks',rec.id,true);toast('Kontroller kaydedildi');
   },'secondary']]),...decisionButtons,...footer.filter(b=>!sealed||b[0]!=='Düzenle')]);
 bindChecks();
}
function riskDecision(rec,ctx,status){
 const reopen=status==='open',accept=status==='accepted',last=ctx.assessments[0];
 const exception=accept&&last?.residual>last?.appetite;
 if(!reopen&&!last)return toast('Önce bir risk değerlendirmesi kaydedin.',false);
 drawer(chosen('risks','status',status)+' · '+rec.code,
  '<p class="intro">'+esc(rec.title)+'</p>'+
  (!reopen?'<p class="notice">Dayanak değerlendirme #'+last.id+' · Artık risk '+last.residual+' · İştah eşiği '+last.appetite+'</p>':'')+
  '<label class="field">Karar gerekçesi<textarea id="riskDecisionReason" required></textarea></label>'+
  (accept?'<label class="field">Sonraki gözden geçirme<input id="riskReview" type="date" value="'+esc(rec.review_date||'')+'"></label>':'')+
  (exception?'<label class="field">İştah üzeri kabulün istisna gerekçesi<textarea id="riskException" required></textarea></label><p>Kurumsal girişte bu istisnayı değerlendirmeyi yapan kişiden farklı bir yönetici onaylar.</p>':''),
  [['Kararı kaydet',async()=>{
   const body={status,decision_rationale:$('riskDecisionReason').value.trim()};
   if(!reopen)body.assessment_id=last.id;
   if(accept){body.response_strategy='accept';body.review_date=$('riskReview').value}
   if(exception)body.exception_rationale=$('riskException').value.trim();
   await api('risks/'+rec.id,{method:'PATCH',body:JSON.stringify(body)});
   await navigate('risks');await openRecord('risks',rec.id);toast('Risk kararı kaydedildi');
  }],['Vazgeç',()=>openRecord('risks',rec.id),'secondary']]);
}
async function riskAssess(rec){
 const ctx=await api('risks/'+rec.id+'/context');
 const controls=ctx.controls.map(c=>{
  const eligible=c.active&&c.test_status==='pass'&&c.has_evidence;
  return '<div class="detail-section" data-credit="'+c.id+'" data-run="'+(c.run_id||'')+'"><b>'+esc(c.code+' — '+c.name)+'</b>'+
   (eligible?'<p>Kanıtlı başarılı çalışma #'+c.run_id+' · '+esc(c.executed_at)+'</p>'+
    '<div class="formgrid"><label class="field">Etkinlik<select data-effect><option value="">Katkı kullanma</option><option value="partial">Kısmen etkili</option><option value="effective">Etkili</option></select></label>'+
    '<label class="field">Ağırlık<select data-weight><option value="low">Düşük (%20)</option><option value="medium">Orta (%40)</option><option value="high">Yüksek (%60)</option></select></label></div>':
    '<p>Katkı uygulanamıyor. Aktif kontrol ve kanıta bağlı başarılı son test gerekir.</p>')+'</div>';
 }).join('');
 drawer('Risk değerlendirmesi • '+rec.code,'<p class="intro">Son testin geçerliliğini ve kontrolün bu riske etkisini değerlendirin. Aynı korumayı sağlayan iki kontrol için çifte katkı vermeyin.</p>'+
  '<div class="notice">İçsel risk = olasılık × etki. Artık risk = içsel risk × (1 − toplam katkı). Kısmen etkili kontroller için ağırlığın yarısı kullanılır. Toplam katkı en fazla %100 olur.</div>'+
  (controls||'<p>Bağlı kontrol yok. Katkı uygulanmaz.</p>')+'<p class="notice" id="riskEstimate" aria-live="polite"></p>'+
  '<label class="field">Değerlendirme gerekçesi<textarea id="riskRationale" required></textarea></label>',
  [['Değerlendirmeyi kaydet',async()=>{
   const credits=read();
   await api('risks/'+rec.id+'/assessments',{method:'POST',body:JSON.stringify({credits,rationale:$('riskRationale').value})});
   await navigate('risks');await openRecord('risks',rec.id);toast('Değerlendirme kaydedildi');
  }],['Vazgeç',()=>openRecord('risks',rec.id),'secondary']]);
 function read(){return [...$('detailContent').querySelectorAll('[data-credit]')].filter(el=>el.querySelector('[data-effect]')?.value).map(el=>({
  control_id:Number(el.dataset.credit),run_id:Number(el.dataset.run),effectiveness:el.querySelector('[data-effect]').value,weight:el.querySelector('[data-weight]').value}))}
 function estimate(){
  const sum=read().reduce((v,c)=>v+({low:.2,medium:.4,high:.6}[c.weight])*(c.effectiveness==='effective'?1:.5),0);
  const residual=Number((rec.likelihood*rec.impact*(1-Math.min(1,sum))).toFixed(2));
  $('riskEstimate').textContent='Öngörülen artık risk '+residual+' / 25'+(rec.appetite?' · İştah eşiği '+rec.appetite+(residual>rec.appetite?' aşılıyor':' içinde'):' · İştah eşiği girilmemiş');
 }
 $('detailContent').querySelectorAll('select').forEach(el=>el.onchange=estimate);estimate();
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
 actions([['Kontrol kataloğunu aç',()=>navigate('controls')],...(canManage()?[['Tüm verileri Excel’e aktar',()=>exportExcel('all'),'secondary']]:[])]);
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
function relationshipMapSVG(){
 const nodes=[
  ['standards',50,100,'Standart / otorite',['Gereklilik kaynağı ve sürümü','Örnek: ISO 20000']],
  ['clauses',415,100,'Standart maddesi',['Standardın alt gerekliliği','Denetimin kapsam birimi']],
  ['objectives',780,100,'Kontrol hedefi',['Ulaşılmak istenen güvence','Birden fazla kontrolle sağlanır']],
  ['processes',1145,100,'Süreç',['Kontrolün ilişkili olduğu süreç','Örnek: konfigürasyon yönetimi']],
  ['audits',50,370,'Denetim',['Kapsam, tarih ve katılımcılar','Kendi bulguları ayrı izlenir']],
  ['controls',415,370,'Kontrol tanımı',['Yöntem, sıklık ve beklenen sonuç','Manuel / otomatik uygulama']],
  ['executions',780,370,'Kontrol çalışması',['Belirli tarih, kapsam ve sonuç','Tanım ve ilişkilerin anlık kaydı']],
  ['evidence',1145,370,'Kanıt',['Dosya, sürüm ve SHA-256','Birden fazla çalışmayı destekler']],
  ['documents',50,650,'Talimat / doküman',['İç hüküm veya uygulama kuralı','Kontrollere kaynak olur']],
  ['findings',780,650,'Bulgu',['Uygunsuzluk veya gözlem','Kontrol, çalışma ve denetim bağı']],
  ['actions',1145,650,'Düzeltici faaliyet',['Bulgunun giderilmesi ve takibi','Sorumlu, termin, etkinlik']]
 ];
 const node=([route,x,y,title,lines])=>'<g class="map-node" data-map-route="'+route+'" tabindex="0" role="link" aria-label="'+esc(title+' kayıtlarını aç')+'">'+
 '<rect x="'+x+'" y="'+y+'" width="245" height="105" rx="14" fill="#fff" stroke="#b8cce2"/>'+
 '<rect x="'+x+'" y="'+y+'" width="245" height="6" rx="3" fill="'+(['controls','executions'].includes(route)?'#2667db':'#168c86')+'"/>'+
 '<text x="'+(x+17)+'" y="'+(y+35)+'" font-size="19" font-weight="700" fill="#173755">'+esc(title)+'</text>'+
 lines.map((line,i)=>'<text x="'+(x+17)+'" y="'+(y+61+19*i)+'" font-size="13" fill="#536b84">'+esc(line)+'</text>').join('')+'</g>';
 const label=(x,y,text)=>'<g><text x="'+x+'" y="'+y+'" text-anchor="middle" font-size="13" font-weight="600" fill="#f8fbff" stroke="#f8fbff" stroke-width="6" stroke-linejoin="round">'+esc(text)+'</text><text x="'+x+'" y="'+y+'" text-anchor="middle" font-size="13" font-weight="600" fill="#3c5d7a">'+esc(text)+'</text></g>';
 const edge=(d,x,y,text,derived=false)=>'<path d="'+d+'" fill="none" stroke="'+(derived?'#8b93a2':'#6686a9')+'" stroke-width="2"'+(derived?' stroke-dasharray="6 5"':'')+' marker-end="url(#mapArrow)"/>'+label(x,y,text);
 let svg='<svg xmlns="http://www.w3.org/2000/svg" id="relationshipMap" viewBox="0 0 1440 1040" role="img" aria-labelledby="mapTitle mapDescription" style="font-family:system-ui,Segoe UI,Arial,sans-serif">'+
 '<title id="mapTitle">KS GRC kayıt ilişki haritası</title><desc id="mapDescription">Standart, madde, hedef, süreç, kontrol, denetim, çalışma, kanıt, bulgu ve düzeltici faaliyet ilişkileri. Düz çizgi doğrudan ilişki; kesikli çizgi kontroller üzerinden türetilen bağdır. Kanıtın ek doğrudan ilişkileri altta tekrar gösterilmiştir.</desc>'+
 '<defs><marker id="mapArrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 Z" fill="#6686a9"/></marker></defs>'+
 '<rect width="1440" height="1040" fill="#f8fbff" rx="16"/>'+
 '<text x="50" y="44" font-size="25" font-weight="750" fill="#163653">KS GRC • Kayıtların birbirine bağlantısı</text>'+
 '<text x="50" y="72" font-size="14" fill="#60778e">1:N = birden çoğa · M:N = çoktan çoğa · Kesikli çizgi = türetilmiş ilişki, doğrudan kayıt bağı değil</text>';
 svg+=edge('M295 152 H415',355,132,'1:N · içerir');
 svg+=edge('M660 152 H780',720,130,'kontrol üzerinden',true);
 svg+=edge('M535 205 V370',550,245,'M:N · karşılar');
 svg+=edge('M900 205 V270 H610 V370',765,258,'M:N · hedefi uygular');
 svg+=edge('M1267 205 V315 H650 V370',1050,303,'M:N · süreçte uygulanır');
 svg+=edge('M172 370 V278 H450 V205',315,265,'M:N · denetim kapsamı');
 svg+=edge('M660 422 H780',720,402,'1:N · test edilir');
 svg+=edge('M1145 422 H1025',1085,402,'M:N · destekler');
 svg+=edge('M245 475 V535 H830 V475',485,523,'1:N · denetimdeki çalışmalar');
 svg+=edge('M945 475 V650',1030,568,'0:N · sonuçtan bulgu');
 svg+=edge('M100 475 V595 H730 V700 H780',415,583,'1:N · denetime ait bulgular');
 svg+=edge('M295 700 H350 V450 H415',345,632,'M:N · kaynak');
 svg+=edge('M1025 702 H1145',1085,682,'1:N · giderilir');
 svg+=nodes.map(node).join('');
 svg+='<rect x="415" y="650" width="285" height="105" rx="12" fill="#eaf2ff"/>'+
 '<text x="431" y="676" font-size="14" font-weight="700" fill="#254e78">Geçmişi koruyan kayıt</text>'+
 ['Çalışma, o andaki kontrol tanımını ve','bağlantıları; kanıtın sürüm / hash’ini','saklar. Güncel tanım geçmişi değiştirmez.'].map((t,i)=>
 '<text x="431" y="'+(699+18*i)+'" font-size="12" fill="#3d6187">'+t+'</text>').join('');
 svg+='<text x="50" y="805" font-size="13" fill="#536b84">Kontrol çalışması denetim dışında da yapılabilir. Başarısız sonuç otomatik bir bulgu oluşturur; sonraki başarı eski bulguyu kapatmaz.</text>'+
 '<text x="50" y="848" font-size="15" font-weight="700" fill="#173755">KANITIN EK DOĞRUDAN BAĞLANTILARI</text>'+
 '<text x="50" y="871" font-size="12" fill="#64748b">Aşağıdaki kutular üstteki aynı kayıt türlerini temsil eder; ikinci bir veri modeli değildir.</text>';
 svg+='<g><rect x="50" y="902" width="205" height="60" rx="12" fill="#e2f7f0" stroke="#9fd5c8"/><text x="152" y="938" text-anchor="middle" font-size="17" font-weight="700" fill="#175e55">Kanıt</text></g>';
 svg+=edge('M255 932 H310 V889 H1260',305,918,'M:N');
 [['audits','Denetim',415],['controls','Kontrol',665],['clauses','Madde',915],['processes','Süreç',1165]].forEach(([route,title,x])=>{
  svg+='<path d="M'+(x+95)+' 889 V902" stroke="#6686a9" stroke-width="2" marker-end="url(#mapArrow)"/>'+
  '<g class="map-node" data-map-route="'+route+'" tabindex="0" role="link" aria-label="'+title+' kayıtlarını aç"><rect x="'+x+'" y="902" width="190" height="60" rx="12" fill="#fff" stroke="#b8cce2"/>'+label(x+95,938,title)+'</g>';
 });
 svg+='<text x="50" y="1005" font-size="13" fill="#536b84">Kanıt bağlantısı tek başına uygunluk kararı değildir. Dış MCP uygulaması kaynak sistemleri sorgular; bu uygulamaya kanıt ve sonuç yazar.</text></svg>';
 return svg;
}
function architecturePage(){
 $('pageSub').textContent='GRC kayıt türleri, doğrudan ilişkiler ve kontrol üzerinden türetilen bağlantılar';
 $('content').innerHTML='<div class="panel"><div class="panel-title"><h2>GRC ilişki haritası</h2><span class="pill">Gerçek veri modeli</span></div>'+
 '<div class="map-controls"><button class="btn secondary small" id="mapFit">Sığdır</button><button class="btn secondary small" id="mapZoomIn" aria-label="Haritayı yakınlaştır">+ Yakınlaştır</button>'+
 '<button class="btn secondary small" id="mapZoomOut" aria-label="Haritayı uzaklaştır">− Uzaklaştır</button><button class="btn secondary small" id="mapExport">SVG indir</button><span id="mapScale" class="map-note"></span></div>'+
 '<div class="map-viewport" id="mapViewport">'+relationshipMapSVG()+'</div>'+
 '<p class="map-note">Kutulara tıklayarak ilgili listeye geçebilirsiniz. Kontrol hedefinin madde ve süreç bağları, bağlı kontroller üzerinden türetilir. Denetim bulguları ile aynı kontrollerin diğer açık bulguları ayrı tutulur.</p></div>';
 let zoom=1;
 const resize=()=>{const width=$('mapViewport').clientWidth;$('relationshipMap').style.width=Math.round(width*zoom)+'px';$('mapScale').textContent=Math.round(zoom*100)+'%';};
 $('mapFit').onclick=()=>{zoom=1;resize()};$('mapZoomIn').onclick=()=>{zoom=Math.min(3,zoom+0.25);resize()};$('mapZoomOut').onclick=()=>{zoom=Math.max(0.5,zoom-0.25);resize()};
 $('mapExport').onclick=()=>{
  const svg=$('relationshipMap').cloneNode(true);svg.removeAttribute('id');svg.style.width='1440px';svg.setAttribute('width','1440');svg.setAttribute('height','1040');
  const url=URL.createObjectURL(new Blob([new XMLSerializer().serializeToString(svg)],{type:'image/svg+xml;charset=utf-8'}));
  const a=document.createElement('a');a.href=url;a.download='ks-grc-iliski-haritasi.svg';a.click();setTimeout(()=>URL.revokeObjectURL(url),2000);
 };
 $('content').querySelectorAll('[data-map-route]').forEach(node=>{
  node.onclick=()=>navigate(node.dataset.mapRoute);node.onkeydown=event=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();navigate(node.dataset.mapRoute)}};
 });
 // ResizeObserver is view-scoped and detached when navigation removes the viewport.
 const viewport=$('mapViewport'),observer=new ResizeObserver(()=>{if(viewport.isConnected)resize();else observer.disconnect()});STATE.mapObserver=observer;observer.observe(viewport);resize();
 actions([['Uyumluluk panosu',()=>navigate('compliance')],['Kontrol kataloğu',()=>navigate('controls'),'secondary']]);
}

async function adminPage(){
 const data=await api('admin/summary');
 const users=data.users||[], enterprise=Boolean(STATE.user.app_role);
 $('content').innerHTML='<div class="notice">'+(enterprise?'Kurumsal kullanıcı ve rol atamaları Microsoft Entra ID üzerinden yapılır.':'Yerel pilotta tüm aktif GRC kullanıcıları eşit uygulama yetkilerine sahiptir.')+'</div>'+
 '<div class="cards">'+[
 ['Kullanıcı',data.user_count],['Aktif kullanıcı',data.active_users],
 ['Veri şeması',data.schema_version],['Son etkinlik',data.activity.length]
 ].map(([name,value])=>'<div class="metric"><span class="metric-label">'+name+
 '</span><span class="metric-number">'+value+'</span></div>').join('')+'</div>'+
 '<div class="panel"><div class="panel-title"><h2>Kullanıcı yönetimi</h2>'+(enterprise?'':'<button class="btn small" id="newUser">+ Yeni kullanıcı</button>')+'</div>'+
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
 if(!enterprise)$('newUser').onclick=userForm;
 $('allExport').onclick=()=>exportExcel('all');
 $('allImport').onclick=()=>importExcel('all');
 $('content').querySelectorAll('[data-user]').forEach(b=>b.onclick=async()=>{
  const active=b.dataset.active==='0';
  if(!confirm(active?'Kullanıcı etkinleştirilsin mi?':'Kullanıcı devre dışı bırakılsın mı?'))return;
  try{await api('admin/users/'+b.dataset.user,{method:'PATCH',
   body:JSON.stringify({is_active:active?1:0})});
   toast('Kullanıcı güncellendi');adminPage()
  }catch(e){toast(e.message,false)}
 });
 actions([...(enterprise?[]:[['Yeni kullanıcı',userForm]]),['Excel yedeği',()=>exportExcel('all'),'secondary']]);
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
  setupDetailResize();setupRelatedNavigation();
  STATE.meta=await api('metadata');
  const user=STATE.user=await api('me');$('identity').textContent='Oturum • '+(user.app_role?user.display_name:user.username);
  $('signout').onclick=async()=>{try{await api('logout',{method:'POST',body:'{}'});location.assign('/login')}
   catch(e){toast(e.message,false)}};
  $('closeDetail').onclick=closeDetail;
  document.addEventListener('keydown',event=>{if(event.key==='Escape'&&STATE.detail)closeDetail()});
  const route=decodeURIComponent((location.hash||'#/home').replace('#/','')).split('/')[0];
  await navigate(LABELS[route]?route:'home');
 }catch(e){$('content').innerHTML='<div class="notice warn">'+esc(e.message)+'</div>'}
}
start();
