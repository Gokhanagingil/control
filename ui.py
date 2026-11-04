"""Single-page Turkish GRC interface for the prototype API."""

HTML = r"""<!doctype html>
<html lang="tr">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>KS GRC</title>
<style>
:root{font-family:Inter,ui-sans-serif,system-ui,-apple-system,"Segoe UI",Arial;--navy:#14243a;--muted:#64748b;--blue:#2563eb;--line:#e5eaf1;--bg:#f5f7fb}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:#1e293b}
button,input,select,textarea{font:inherit}button{cursor:pointer}
aside{position:fixed;top:0;bottom:0;left:0;width:244px;background:#122239;color:#dce7f7;padding:27px 14px;overflow:auto}
.brand{font-size:22px;font-weight:800;color:#fff;padding:0 15px}.brand span{color:#60a5fa}
.brand small{font-size:11px;display:block;color:#9db3cd;letter-spacing:.06em;font-weight:500;padding-top:6px}
.nav-head{font-size:10px;letter-spacing:.17em;color:#8199b8;padding:25px 15px 8px}
nav button{display:block;width:100%;text-align:left;color:#c6d2e4;border:0;background:transparent;padding:11px 14px;border-radius:10px;margin:2px 0}
nav button:hover,nav button.active{background:#223b5b;color:white}.logout{background:transparent;border:1px solid #526883;color:#cbd5e1;padding:10px 14px;border-radius:9px;margin:24px 14px 0;cursor:pointer}nav button.active{box-shadow:inset 3px 0 #60a5fa}
main{margin-left:244px;padding:35px;max-width:1680px}
.top{display:flex;align-items:center;justify-content:space-between;gap:16px;margin-bottom:26px}
.top h1{font-size:27px;margin:0 0 5px;letter-spacing:-.025em}.sub{color:var(--muted);font-size:14px}
.btn{background:var(--blue);color:white;border:0;border-radius:9px;padding:10px 17px;font-weight:600}
.btn.secondary{background:#fff;color:#264361;border:1px solid #dbe3ef}
.btn.ghost{background:transparent;color:#2563eb;padding:5px 6px}
.btn:disabled{opacity:.55;cursor:wait}
.cards{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:15px;margin-bottom:20px}
.card,.panel{background:#fff;border:1px solid var(--line);border-radius:14px;box-shadow:0 4px 18px #1f35500a}
.card{padding:18px 20px}.card label{display:block;color:var(--muted);font-size:12px;margin-bottom:12px}.card b{font-size:30px;font-weight:750}
.panel{padding:21px;margin-bottom:17px}.panel-top{display:flex;justify-content:space-between;align-items:center;gap:14px;margin-bottom:19px}.panel-top h2{font-size:17px;margin:0}
.tools{display:flex;gap:9px;flex-wrap:wrap}.search{width:250px;max-width:100%}
input,textarea,select{color:#26354c;background:#fff;border:1px solid #cdd7e5;border-radius:9px;padding:10px 11px;min-height:41px;width:100%;outline-offset:2px}
input:focus,textarea:focus,select:focus{outline:2px solid #bed8ff;border-color:#60a5fa}
label.field{font-size:12px;color:#465b76;font-weight:600;display:block}
label.field input,label.field select,label.field textarea{margin-top:7px;font-size:14px;font-weight:400}
textarea{resize:vertical;min-height:74px}.formgrid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}
.field.wide{grid-column:1/-1}
.actions{display:flex;justify-content:flex-end;gap:10px;margin-top:18px}
.tablewrap{overflow:auto}table{border-collapse:collapse;width:100%;font-size:13px}th{color:#718099;background:#f7f9fc;font-size:11px;letter-spacing:.055em;font-weight:700;text-transform:uppercase}
td,th{padding:12px 11px;text-align:left;border-bottom:1px solid #edf0f5;vertical-align:middle}td{max-width:280px;overflow-wrap:anywhere}td strong{color:#183555}
.pill{display:inline-block;padding:4px 9px;border-radius:999px;font-size:11px;font-weight:700;background:#ecf3ff;color:#1d56a6}
.pill.fail{background:#feeceb;color:#b42318}.pill.pass{background:#ddf7ed;color:#127753}.pill.manual{background:#f2edff;color:#6544b7}
.empty{padding:38px;text-align:center;color:#7b8799}.hint{color:#718098;font-size:12px;margin:12px 0 0}
#toast{position:fixed;right:24px;bottom:24px;background:#173855;color:#fff;padding:13px 18px;border-radius:11px;box-shadow:0 10px 40px #0003;display:none;z-index:10}
dialog{width:min(720px,calc(100vw - 24px));border:1px solid #d5e0ed;border-radius:16px;padding:0;box-shadow:0 35px 100px #10263b50}
dialog::backdrop{background:#0e223b90}.dialoghead{display:flex;justify-content:space-between;align-items:center;padding:20px 23px;border-bottom:1px solid #ebeff5}.dialoghead h2{margin:0;font-size:20px}
.dialogbody{padding:21px 23px;max-height:70vh;overflow:auto}.close{border:0;background:#edf2f9;padding:6px 10px;border-radius:8px}
.selectlist{height:140px;padding:8px}.selectlist option{padding:4px}.muted{color:#738099}
@media(max-width:950px){aside{position:static;width:auto;padding:15px}nav{display:flex;overflow:auto;gap:5px}nav button{white-space:nowrap}main{margin:0;padding:18px}.cards{grid-template-columns:repeat(2,1fr)}.formgrid{grid-template-columns:1fr}}
@media(max-width:530px){.top{align-items:flex-start;flex-direction:column}.cards{grid-template-columns:1fr 1fr}.card{padding:13px}.card b{font-size:24px}}
</style>
</head>
<body>
<aside><div class="brand">KS<span> GRC</span><small>GOVERNANCE • RISK • COMPLIANCE</small></div><div class="nav-head">ÇALIŞMA ALANI</div><nav id="nav"></nav><button id="logout" class="logout">Oturumu kapat</button></aside>
<main>
  <div class="top"><div><h1 id="heading">Genel Bakış</h1><div class="sub" id="subtitle">Denetim, kontrol ve kanıt yönetimi</div></div>
  <button class="btn" id="newBtn" style="display:none">+ Yeni kayıt</button></div>
  <section id="dashboard"></section>
  <section id="content"></section>
</main>
<dialog id="dialog"><div class="dialoghead"><h2 id="dialogtitle">Yeni kayıt</h2><button id="close" class="close" aria-label="Kapat">✕</button></div><div class="dialogbody" id="dialogbody"></div></dialog>
<div id="toast" role="status"></div>
<script>
'use strict';
const $=id=>document.getElementById(id);
const labels={controls:'Kontroller',objectives:'Kontrol Hedefleri',standards:'Standartlar',clauses:'Standart Maddeleri',processes:'Süreçler',audits:'Denetimler',executions:'Kontrol Sonuçları',evidence:'Kanıt Kütüphanesi',findings:'Bulgular'};
const meta={
standards:[['code','Kod','text',1],['name','Standart / Otorite Dokümanı','text',1],['version','Versiyon'],['description','Açıklama','textarea']],
clauses:[['standard_id','Standart','ref:standards',1],['code','Madde numarası','text',1],['title','Madde başlığı','text',1],['description','Madde içeriği','textarea'],['parent_id','Üst madde','ref:clauses']],
processes:[['code','Süreç kodu','text',1],['name','Süreç adı','text',1],['owner','Süreç sahibi'],['description','Açıklama','textarea']],
objectives:[['code','Kontrol hedefi kodu','text',1],['name','Kontrol hedefi','text',1],['description','Açıklama','textarea']],
controls:[['code','Kontrol kodu','text',1],['name','Kontrol adı','text',1],['description','Tanım','textarea'],
 ['execution_mode','Uygulama','choice:manual|Manuel,automatic|Otomatik',1],['nature','Kontrol türü','choice:preventive|Önleyici,detective|Tespit edici,corrective|Düzeltici,directive|Yönlendirici,compensating|Telafi edici'],
 ['frequency','Sıklık','choice:on_demand|İhtiyaca göre,daily|Günlük,weekly|Haftalık,monthly|Aylık,quarterly|Üç aylık,yearly|Yıllık,continuous|Sürekli'],
 ['method','Kontrol yöntemi / MCP sorgu yönergesi','textarea'],['expected_result','Beklenen sonuç / kabul kriteri','textarea'],['owner','Kontrol sorumlusu']],
audits:[['name','Denetim adı','text',1],['scope','Kapsam','textarea'],['planned_start','Planlanan başlangıç','date'],['planned_end','Planlanan bitiş','date'],['actual_start','Gerçek başlangıç','date'],['actual_end','Gerçek bitiş','date'],['auditors','Denetçiler'],['auditees','Denetlenenler'],['status','Durum','choice:planned|Planlandı,in_progress|Devam ediyor,completed|Tamamlandı,closed|Kapalı']],
evidence:[['title','Kanıt adı','text',1],['description','Açıklama','textarea'],['reference_url','Harici kanıt referansı / URL'],['source','Kaynak']],
findings:[['title','Bulgu başlığı','text',1],['control_id','Kontrol','ref:controls'],['audit_id','Denetim','ref:audits'],['description','Bulgu detayı','textarea'],['severity','Önem','choice:low|Düşük,medium|Orta,high|Yüksek,critical|Kritik'],['status','Durum','choice:open|Açık,in_progress|Üzerinde çalışılıyor,closed|Kapalı']]
};
const columns={
controls:['code','name','execution_mode','nature','frequency','owner'],
objectives:['code','name','description'],
standards:['code','name','version'],
clauses:['code','title','standard_id'],
processes:['code','name','owner'],
audits:['name','planned_start','planned_end','status'],
executions:['control_id','status','source','executed_at'],
evidence:['title','source','collected_at','hash_sha256'],
findings:['title','severity','status','created_at']
};
let state={view:'home',items:{},filter:''}; const cache={};
const escapeHtml=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const titleOf=x=>x.name||x.title||x.code||('#'+x.id);
async function api(path, opts){
 const r=await fetch('/api/'+path,{...opts,headers:{'Content-Type':'application/json',...(opts?.headers||{})}});
 if(!r.ok){let e;try{e=await r.json()}catch{};throw Error(e?.error||'Sunucu hatası ('+r.status+')')}
 return r.headers.get('Content-Type')?.includes('application/json')?r.json():r.blob();
}
async function list(table){return api(table)}
function toast(message){$('toast').textContent=message;$('toast').style.display='block';setTimeout(()=>$('toast').style.display='none',3800)}
function modal(title,html){$('dialogtitle').textContent=title;$('dialogbody').innerHTML=html;$('dialog').showModal()}
function nav(){const groups=[['home','Genel Bakış'],['controls','Kontroller'],['objectives','Kontrol Hedefleri'],['standards','Standartlar'],['clauses','Standart Maddeleri'],['processes','Süreçler'],['audits','Denetimler'],['evidence','Kanıt Kütüphanesi'],['executions','Kontrol Sonuçları'],['findings','Bulgular']];
 $('nav').innerHTML=groups.map(([v,t])=>'<button data-view="'+v+'" class="'+(v===state.view?'active':'')+'">'+t+'</button>').join('');
 $('nav').querySelectorAll('button').forEach(b=>b.onclick=()=>show(b.dataset.view));
}
function displayValue(key,value){if(value==null)return '<span class="muted">—</span>';if(key==='status'||key==='execution_mode'||key==='severity')return '<span class="pill '+(value==='fail'?'fail':value==='pass'?'pass':value==='manual'?'manual':'')+'">'+escapeHtml(value)+'</span>';return escapeHtml(String(value).slice(0,140))}
async function show(view,preserveFilter=false){
 state.view=view;if(!preserveFilter)state.filter='';nav();$('heading').textContent=view==='home'?'Genel Bakış':labels[view];$('subtitle').textContent=view==='home'?'Denetim, kontrol ve kanıt yönetimi':'Kayıtlar, ilişkiler ve işlemler';$('newBtn').style.display=view==='home'||view==='executions'?'none':'block';
 $('dashboard').innerHTML='';$('content').innerHTML='<div class="panel">Yükleniyor…</div>';
 try{
  if(view==='home')return dashboard();
  let items=await list(view);state.items[view]=items;
  const keys=columns[view]||[];
  const visible=items.filter(x=>Object.values(x).some(v=>String(v??'').toLocaleLowerCase('tr').includes(state.filter.toLocaleLowerCase('tr'))));
  let actions='<button class="btn" id="createAction">+ Yeni kayıt</button>';
  if(view==='audits')actions+='<button class="btn secondary" id="newStandardAudit">Standarttan denetim oluştur</button>';
  if(view==='evidence')actions+='<button class="btn secondary" id="uploadEvidence">Dosya yükle</button>';
  if(view==='controls')actions+='<button class="btn secondary" id="runControl">Kontrol çalıştır</button>';
  if(view==='executions')actions='<button class="btn" id="runControl">Kontrol çalıştır</button>';
  $('content').innerHTML='<div class="panel"><div class="panel-top"><h2>'+labels[view]+' · '+visible.length+' kayıt</h2><div class="tools">'+actions+'</div></div><input id="search" class="search" aria-label="Kayıt ara" placeholder="Kayıt ara…"><div class="tablewrap" id="table"></div></div>';
  $('search').value=state.filter;$('search').oninput=e=>{state.filter=e.target.value;show(view,true).then(()=>$('search')?.focus())};
  if($('createAction'))$('createAction').onclick=()=>form(view);
  if($('runControl'))$('runControl').onclick=()=>runControl();
  if($('newStandardAudit'))$('newStandardAudit').onclick=()=>auditWizard();
  if($('uploadEvidence'))$('uploadEvidence').onclick=()=>uploadWizard();
  const header='<thead><tr>'+keys.map(k=>'<th>'+escapeHtml(k.replaceAll('_',' '))+'</th>').join('')+'<th></th></tr></thead>';
  const body=visible.map(x=>'<tr>'+keys.map((key,i)=>'<td>'+(i===0?'<strong>':'')+displayValue(key,x[key])+(i===0?'</strong>':'')+'</td>').join('')+
      '<td><button class="btn ghost" data-id="'+x.id+'">Detay</button></td></tr>').join('');
  $('table').innerHTML='<table>'+header+'<tbody>'+body+'</tbody></table>'+(visible.length?'':'<div class="empty">Henüz kayıt yok. Yeni bir kayıt ekleyebilirsin.</div>');
  $('table').querySelectorAll('button[data-id]').forEach(b=>b.onclick=()=>detail(view,Number(b.dataset.id)));
 }catch(e){$('content').innerHTML='<div class="panel">'+escapeHtml(e.message)+'</div>'}
}
async function dashboard(){
 try{
  const [cs,au,fi,ev,st,pr]=await Promise.all(['controls','audits','findings','evidence','standards','processes'].map(list));
  const nums=[['Toplam kontrol',cs.length],['Denetim',au.length],['Açık bulgu',fi.filter(f=>f.status!=='closed').length],['Kanıt kaydı',ev.length]];
  $('dashboard').innerHTML='<div class="cards">'+nums.map(([k,v])=>'<div class="card"><label>'+k+'</label><b>'+v+'</b></div>').join('')+'</div>'+
   '<div class="panel"><div class="panel-top"><h2>Başlangıç ve çalışma sırası</h2></div>'+
   '<p><b>1.</b> Standartlar ve maddeleri oluştur. <b>2.</b> Süreçleri ve kontrol hedeflerini tanımla. <b>3.</b> Kontrol oluşturup ilişkilerini bağla.</p>'+
   '<p><b>4.</b> Standarttan denetim başlat. <b>5.</b> Manuel veya MCP üzerinden kontrol sonucu gir. <b>6.</b> Kanıtları sakla ve tekrar kullan.</p>'+
   '<p class="hint">'+st.length+' standart, '+pr.length+' süreç kayıtlı. ServiceNow bağlantısını mevcut MCP uygulaman yönetecek.</p></div>';
  $('content').innerHTML='';
 }catch(e){$('content').innerHTML='<div class="panel">'+escapeHtml(e.message)+'</div>'}
}
async function options(ref,multiple){const data=await list(ref);return '<option value="">Seçiniz</option>'+data.map(x=>'<option value="'+x.id+'">'+escapeHtml(titleOf(x))+'</option>').join('')}
async function fieldMarkup(field){let [key,label,type,required]=field;type=type||'text';let content='',attrs=' data-field="'+key+'" '+(required?'required':'');
 if(type.startsWith('ref:')){content='<select '+attrs+'>'+await options(type.slice(4))+'</select>'}
 else if(type.startsWith('choice:'))content='<select '+attrs+'>'+type.slice(7).split(',').map(opt=>{let [v,t]=opt.split('|');return '<option value="'+escapeHtml(v)+'">'+escapeHtml(t||v)+'</option>'}).join('')+'</select>';
 else if(type==='textarea')content='<textarea '+attrs+'></textarea>';
 else content='<input type="'+(type==='date'?'date':'text')+'" '+attrs+'>';
 return '<label class="field '+(type==='textarea'?'wide':'')+'">'+escapeHtml(label)+content+'</label>';
}
async function form(view){
 if(!meta[view])return;
 try{
  const html=(await Promise.all(meta[view].map(fieldMarkup))).join('');
  modal('Yeni '+labels[view]+' kaydı','<div class="formgrid">'+html+'</div><div class="actions"><button class="btn" id="submitRecord">Kaydet</button></div>');
  $('submitRecord').onclick=async()=>{
   const data={}, invalid=[];
   meta[view].forEach(([key,label,type,req])=>{
    const el=document.querySelector('[data-field="'+key+'"]');const val=el.value.trim();
    if(req&&!val)invalid.push(label);
    if(val)data[key]=type?.startsWith('ref:')?Number(val):val;
   });
   if(invalid.length){toast('Zorunlu alanlar: '+invalid.join(', '));return}
   try{await api(view,{method:'POST',body:JSON.stringify(data)});$('dialog').close();toast('Kayıt oluşturuldu');show(view)}catch(e){toast(e.message)}
  };
 }catch(e){toast(e.message)}
}
async function detail(view,id){
 const x=(state.items[view]||[]).find(a=>a.id===id);if(!x)return;
 let html='<div class="panel"><h3>'+escapeHtml(titleOf(x))+'</h3><table>'+Object.entries(x).map(([k,v])=>'<tr><th>'+escapeHtml(k)+'</th><td>'+escapeHtml(v)+'</td></tr>').join('')+'</table>'+(meta[view]?'<div class="actions"><button class="btn secondary" id="editRecord">Kaydı düzenle</button></div>':'')+'</div>';
 if(view==='controls'){
  const context=await api('controls/'+id+'/context');
  html+='<div class="panel"><h3>İlişkili kontrol hedefleri, standart maddeleri ve süreçler</h3><p class="hint">Bir kontrol birden fazla süreç, hedef ve maddeyi kapsayabilir.</p><div id="mappings"></div><div class="actions"><button class="btn" id="saveMappings">İlişkileri kaydet</button></div></div>';
  modal('Kontrol detayları',html);
  for(const target of ['objectives','clauses','processes']){
    const optionsList=await list(target); const chosen=new Set((context[target]||[]).map(a=>a.id));
    const label={objectives:'Kontrol Hedefleri',clauses:'Standart Maddeleri',processes:'Süreçler'}[target];
    let parent=document.createElement('label');parent.className='field wide';parent.textContent=label;
    const sel=document.createElement('select');sel.multiple=true;sel.className='selectlist';sel.dataset.mapping=target;
    optionsList.forEach(item=>{let opt=document.createElement('option');opt.value=item.id;opt.textContent=titleOf(item);opt.selected=chosen.has(item.id);sel.append(opt)});
    parent.append(sel);$('mappings').append(parent);
  }
  $('saveMappings').onclick=async()=>{
   const data={};document.querySelectorAll('[data-mapping]').forEach(s=>data[s.dataset.mapping]=Array.from(s.selectedOptions).map(o=>Number(o.value)));
   try{await api('controls/'+id+'/mappings',{method:'POST',body:JSON.stringify(data)});$('dialog').close();toast('İlişkiler kaydedildi');show(view)}catch(e){toast(e.message)}
  };
 }else if(view==='standards'){
  html+='<div class="panel"><h3>Standart maddelerini CSV ile içe aktar</h3>'+
   '<p class="hint">CSV başlıkları: code,title,description,parent_code. Yalnızca kullanım hakkın bulunan standart metinlerini yükle. Tek seferde en fazla 1.000 madde.</p>'+
   '<label class="field wide">CSV dosyası (UTF-8, 700 KB sınırı)<input type="file" accept=".csv,text/csv" id="standardCSV"></label>'+
   '<div class="actions"><button class="btn" id="importStandard">Maddeleri içe aktar</button></div></div>';
  modal('Standart ayrıntıları',html);
  $('importStandard').onclick=async()=>{
   const file=$('standardCSV').files?.[0];
   if(!file||!file.size||file.size>700000)return toast('En fazla 700 KB boyutunda CSV seçmelisin');
   try{
    const encoded=await new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(String(reader.result).split(',')[1]);reader.onerror=reject;reader.readAsDataURL(file)});
    const result=await api('standards/'+id+'/clauses/import',{method:'POST',body:JSON.stringify({csv_base64:encoded})});
    $('dialog').close();toast(result.imported+' yeni madde eklendi; '+result.skipped+' zaten mevcut');show('clauses');
   }catch(e){toast(e.message)}
  };
 }else if(view==='evidence'){
  const context=await api('evidence/'+id+'/context');
  const [clauses,processes]=await Promise.all([list('clauses'),list('processes')]);
  html+='<div class="panel"><h3>Kanıtın kullanım geçmişi</h3><p>İlgili maddeler: '+(context.clauses.map(x=>escapeHtml(x.code)).join(', ')||'—')+'</p><p>Süreçler: '+(context.processes.map(x=>escapeHtml(x.name)).join(', ')||'—')+'</p><p>İlişkili kontrol çalışmaları: '+context.executions.length+'</p>'+(x.hash_sha256?'<button class="btn secondary" id="download">Dosyayı indir</button>':'')+'</div>';
  html+='<div class="panel"><h3>Kanıtın kapsadığı süreç ve standart maddeleri</h3><p class="hint">Kanıt birden fazla madde ve süreci destekleyebilir.</p>'+
    '<div class="formgrid"><label class="field">Standart maddeleri<select id="evMapClauses" multiple class="selectlist">'+clauses.map(c=>'<option value="'+c.id+'" '+(context.clauses.some(x=>x.id===c.id)?'selected':'')+'>'+escapeHtml(c.code+' — '+c.title)+'</option>').join('')+'</select></label>'+
    '<label class="field">Süreçler<select id="evMapProcesses" multiple class="selectlist">'+processes.map(p=>'<option value="'+p.id+'" '+(context.processes.some(x=>x.id===p.id)?'selected':'')+'>'+escapeHtml(p.name)+'</option>').join('')+'</select></label></div>'+
    '<div class="actions"><button class="btn" id="saveEvidenceMaps">İlişkileri kaydet</button></div></div>';
  modal('Kanıt ayrıntıları',html);
  $('saveEvidenceMaps').onclick=async()=>{
   const payload={clauses:Array.from($('evMapClauses').selectedOptions).map(o=>Number(o.value)),processes:Array.from($('evMapProcesses').selectedOptions).map(o=>Number(o.value))};
   try{await api('evidence/'+id+'/mappings',{method:'POST',body:JSON.stringify(payload)});$('dialog').close();toast('Kanıt ilişkileri güncellendi');show(view)}catch(e){toast(e.message)}
  };
  if($('download'))$('download').onclick=async()=>{
   try{const blob=await api('evidence/'+id+'/download');const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download='evidence-'+id+'.bin';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)}catch(e){toast(e.message)}
  };
 }else if(view==='audits'){
  const scope=await api('audits/'+id+'/scope');
  html+='<div class="panel"><h3>Denetim kapsamındaki standart maddeleri ('+scope.clauses.length+')</h3><div class="tablewrap"><table>'+scope.clauses.map(x=>'<tr><td>'+escapeHtml(x.standard_code)+'</td><td>'+escapeHtml(x.code)+'</td><td>'+escapeHtml(x.title)+'</td></tr>').join('')+'</table></div></div>';
  modal('Denetim ayrıntıları',html);
 }else modal(labels[view]+' ayrıntıları',html);
 if($('editRecord'))$('editRecord').onclick=()=>editForm(view,id,x);
}
async function editForm(view,id,entry){
 if(!meta[view])return;
 const fields=meta[view].filter(([key])=>!(view==='clauses'&&key==='standard_id')&&!(view==='evidence'&&key==='source')&&!(view==='findings'&&['control_id','audit_id'].includes(key)));
 const html=(await Promise.all(fields.map(fieldMarkup))).join('');
 modal(labels[view]+' kaydını düzenle','<div class="formgrid">'+html+'</div><div class="actions"><button class="btn" id="saveEdit">Değişiklikleri kaydet</button></div>');
 fields.forEach(([key])=>{
  const element=document.querySelector('[data-field="'+key+'"]');
  element.value=entry[key]===null||entry[key]===undefined?'':String(entry[key]);
 });
 $('saveEdit').onclick=async()=>{
  const payload={};const invalid=[];
  fields.forEach(([key,label,type,required])=>{
   const value=document.querySelector('[data-field="'+key+'"]').value.trim();
   if(required&&!value)invalid.push(label);
   payload[key]=type?.startsWith('ref:')?(value?Number(value):null):value;
  });
  if(invalid.length)return toast('Zorunlu alanlar: '+invalid.join(', '));
  try{await api(view+'/'+id,{method:'PATCH',body:JSON.stringify(payload)});$('dialog').close();toast('Değişiklikler kaydedildi');show(view)}catch(e){toast(e.message)}
 };
}
async function auditWizard(){
 const data=await list('standards');
 modal('Standarttan denetim oluştur','<div class="formgrid"><label class="field">Standart<select id="auditStandard">'+data.map(x=>'<option value="'+x.id+'">'+escapeHtml(x.code+' — '+x.name)+'</option>').join('')+'</select></label><label class="field">Denetim adı<input id="auditName" required placeholder="2026 İç Denetim"></label><label class="field">Planlanan başlangıç<input type="date" id="auditStart"></label><label class="field">Planlanan bitiş<input type="date" id="auditEnd"></label></div><p class="hint">Seçilen standardın mevcut tüm maddeleri denetime bağlanır.</p><div class="actions"><button class="btn" id="createAudit">Denetimi oluştur</button></div>');
 $('createAudit').onclick=async()=>{
  if(!$('auditName').value.trim())return toast('Denetim adı gerekli');
  try{const result=await api('audits/from-standard',{method:'POST',body:JSON.stringify({standard_id:Number($('auditStandard').value),name:$('auditName').value.trim(),planned_start:$('auditStart').value,planned_end:$('auditEnd').value})});$('dialog').close();toast(result.clause_count+' maddeyle denetim oluşturuldu');show('audits')}catch(e){toast(e.message)}
 };
}
async function runControl(){
 const [controls,evidence,audits]=await Promise.all(['controls','evidence','audits'].map(list));
 modal('Kontrol sonucu kaydet', '<div class="formgrid"><label class="field">Kontrol<select id="execControl">'+controls.map(x=>'<option value="'+x.id+'">'+escapeHtml(x.code+' — '+x.name)+'</option>').join('')+'</select></label><label class="field">Sonuç<select id="execStatus"><option value="pass">Başarılı</option><option value="fail">Başarısız → Bulgu oluştur</option><option value="inconclusive">Belirsiz</option><option value="not_applicable">Uygulanamaz</option></select></label><label class="field">Denetim<select id="execAudit"><option value="">Denetim dışı</option>'+audits.map(x=>'<option value="'+x.id+'">'+escapeHtml(x.name)+'</option>').join('')+'</select></label><label class="field">Kaynak<select id="execSource"><option value="manual">Manuel</option><option value="mcp">MCP</option></select></label><label class="field wide">Kanıtlar (Ctrl ile çoklu seçilebilir)<select id="execEvidence" multiple class="selectlist">'+evidence.map(x=>'<option value="'+x.id+'">'+escapeHtml(x.title)+'</option>').join('')+'</select></label><label class="field wide">Kontrol değerlendirmesi<textarea id="execDetails"></textarea></label></div><div class="actions"><button class="btn" id="saveExecution">Sonucu kaydet</button></div>');
 $('saveExecution').onclick=async()=>{
  const data={control_id:Number($('execControl').value),status:$('execStatus').value,source:$('execSource').value,details:$('execDetails').value,evidence_ids:Array.from($('execEvidence').selectedOptions).map(x=>Number(x.value))};
  if($('execAudit').value)data.audit_id=Number($('execAudit').value);
  try{const result=await api('executions',{method:'POST',body:JSON.stringify(data)});$('dialog').close();toast(result.finding_id?'Kontrol başarısız: bulgu oluşturuldu':'Kontrol sonucu kaydedildi');show('executions')}catch(e){toast(e.message)}
 };
}
async function uploadWizard(){
 const [clauses,processes]=await Promise.all([list('clauses'),list('processes')]);
 const options=(items)=>items.map(x=>'<option value="'+x.id+'">'+escapeHtml(x.code?x.code+' — '+titleOf(x):titleOf(x))+'</option>').join('');
 modal('Kanıt dosyası yükle','<div class="formgrid"><label class="field wide">Kanıt başlığı<input id="evTitle" placeholder="Örn. CMDB keşif raporu"></label>'+
  '<label class="field wide">Dosya (en fazla 600 KB)<input id="evFile" type="file"></label>'+
  '<label class="field wide">Açıklama<textarea id="evDescription"></textarea></label>'+
  '<label class="field">İlişkili standart maddeleri<select id="evClauses" multiple class="selectlist">'+options(clauses)+'</select></label>'+
  '<label class="field">İlişkili süreçler<select id="evProcesses" multiple class="selectlist">'+options(processes)+'</select></label></div>'+
  '<div class="actions"><button class="btn" id="saveEvidence">Kanıtı kaydet</button></div>');
 $('saveEvidence').onclick=async()=>{
  const file=$('evFile').files?.[0];if(!file||file.size>600000||!file.size)return toast('1–600 KB arasında dosya seçmelisin');
  if(!$('evTitle').value.trim())return toast('Kanıt başlığı gerekli');
  try{
   const encoded=await new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(String(reader.result).split(',')[1]);reader.onerror=reject;reader.readAsDataURL(file)});
   const payload={title:$('evTitle').value.trim(),description:$('evDescription').value,source:'manual',content_base64:encoded,
     clauses:Array.from($('evClauses').selectedOptions).map(o=>Number(o.value)),
     processes:Array.from($('evProcesses').selectedOptions).map(o=>Number(o.value))};
   await api('evidence/upload',{method:'POST',body:JSON.stringify(payload)});
   $('dialog').close();toast('Kanıt ve ilişkileri kaydedildi');show('evidence');
  }catch(e){toast(e.message)}
 };
}
$('newBtn').onclick=()=>form(state.view);$('close').onclick=()=>$('dialog').close();$('logout').onclick=async()=>{try{await api('logout',{method:'POST',body:'{}'});location.replace('/login')}catch(e){toast(e.message)}};show('home');
</script>
</body>
</html>
"""

def page_html():
    return HTML
