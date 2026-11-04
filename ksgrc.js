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
  b.textContent=name;b.onclick=callback;$('detailFooter').append(b)
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
  if(view==='home')return home();
  if(view==='compliance')return compliancePage();
  if(view==='architecture')return architecturePage();
  if(view==='admin')return adminPage();
  return renderTable(view);
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
   invalidate(table);toast('Kayıt oluşturuldu');await renderTable(table);await openRecord(table,result.id)
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
