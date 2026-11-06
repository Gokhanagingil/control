"""KS GRC v2 — self-contained Turkish administration interface."""
HTML = r"""<!doctype html>
<html lang="tr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="KS GRC • Kontrol, denetim ve kanıt yönetimi">
<title>KS GRC | Yönetim Paneli</title>
<style>
:root{font-family:Inter,system-ui,-apple-system,"Segoe UI",Arial,sans-serif;color:#23334d;
--bg:#f5f7fb;--side:#14243b;--side2:#1b304e;--text:#23334d;--muted:#718099;
--stroke:#dfe6f0;--blue:#2667db;--hover:#eaf2ff;--teal:#168c86;--shadow:0 5px 24px #21385c09}
*{box-sizing:border-box}body{margin:0;background:var(--bg)}
button,input,select,textarea{font:inherit}button{cursor:pointer}
button:focus-visible,a:focus-visible,input:focus-visible,select:focus-visible,textarea:focus-visible{outline:3px solid #93b9f5;outline-offset:2px}
a{color:var(--blue)}.hidden{display:none!important}.muted{color:var(--muted)}
#sidebar{position:fixed;top:0;bottom:0;left:0;width:244px;padding:22px 12px 17px;background:linear-gradient(165deg,#102239,#1b3150);color:#c8d8eb;display:flex;flex-direction:column;z-index:10}
.brand{color:white;font-size:24px;letter-spacing:-.7px;font-weight:800;margin:0 11px 25px}
.brand strong{color:#64e0ce}.brand small{display:block;font-size:10px;letter-spacing:1.65px;color:#a2b8d3;font-weight:500;margin-top:6px}
#nav{overflow-y:auto;flex:1;padding:0 3px}
.nav-title{font-size:10px;letter-spacing:1.5px;text-transform:uppercase;color:#8aa2be;font-weight:700;margin:21px 12px 9px}
.nav-title:first-child{margin-top:0}.nav-button{width:100%;display:flex;align-items:center;gap:11px;text-align:left;color:#c8d8eb;border:none;background:transparent;border-radius:10px;padding:11px 13px;margin:2px 0;font-size:13px}
.nav-button.active{background:#315277;color:#fff;box-shadow:inset 3px 0 #5ccef4}
.nav-button:hover{background:#263f60;color:#fff}.nav-icon{width:21px;text-align:center;font-size:17px;opacity:.8}
.nav-bottom{padding:11px 3px 0;border-top:1px solid #334963}
#identity{font-size:11px;color:#cbdaf0;padding:13px 12px}
#signout{width:100%;border:1px solid #53718f;color:#dce8f8;background:transparent;border-radius:9px;padding:9px}
#main{margin-left:244px;padding:31px 35px;transition:padding-right .22s,max-width .22s;min-height:100vh;overflow:hidden}
#main.details-open{padding-right:calc(min(540px,46vw) + 45px)}
#topline{display:flex;align-items:flex-start;justify-content:space-between;gap:20px;margin-bottom:23px;min-height:54px}
#pageTitle{font-size:27px;letter-spacing:-.6px;margin:0;font-weight:780;color:#1a304d}
#pageSub{color:var(--muted);font-size:13px;margin-top:7px}
#topActions{display:flex;gap:8px;flex-wrap:wrap;justify-content:flex-end}
.btn{border-radius:9px;background:var(--blue);border:1px solid var(--blue);color:#fff;padding:10px 14px;font-size:12px;font-weight:650;line-height:1.15;white-space:nowrap}
.btn:hover{filter:brightness(.95)}.btn.secondary{background:#fff;color:#29476c;border-color:#d7e0ec}
.btn.ghost{background:transparent;border-color:transparent;color:var(--blue);padding:7px 9px}
.btn.danger{background:#fff1f2;border-color:#fecdd3;color:#be123c}
.btn.small{font-size:11px;padding:7px 10px}.btn:disabled{opacity:.55;cursor:not-allowed}
.panel{background:white;border:1px solid var(--stroke);border-radius:15px;box-shadow:var(--shadow);padding:21px;margin-bottom:16px}
.panel h2,.panel h3{margin:0 0 15px;font-size:16px;color:#233a56}
.panel-title{display:flex;align-items:center;justify-content:space-between;gap:13px;margin-bottom:17px}
.panel-title h2{margin:0}.intro{font-size:13px;line-height:1.7;color:#566a84}
.cards{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:15px;margin-bottom:17px}
.metric{padding:20px;border:1px solid var(--stroke);border-radius:13px;background:white;box-shadow:var(--shadow);text-align:left;color:inherit;display:block;width:100%;transition:transform .12s,border-color .12s}
.metric:hover{transform:translateY(-2px);border-color:#9dc7fb}.metric-label{color:var(--muted);font-size:12px;font-weight:550}
.metric-number{display:block;font-size:29px;font-weight:800;margin:14px 0 0;color:#1b355a;letter-spacing:-.7px}
.metric-foot{font-size:11px;color:#7d8aa0;margin-top:9px}.metric.wide{background:linear-gradient(120deg,#f4fffc,#f5faff)}
.toolbar{display:flex;gap:10px;align-items:center;flex-wrap:wrap;justify-content:space-between;margin-bottom:17px}
.searchbar{max-width:340px;width:100%;min-width:180px}
input,select,textarea{width:100%;background:white;border:1px solid #d0dbe9;border-radius:9px;color:#223d5d;font-size:13px;padding:10px 11px;min-height:39px}
textarea{min-height:90px;resize:vertical;line-height:1.55}input::placeholder{color:#98a8bc}
.field{display:block;color:#415b79;font-size:12px;font-weight:650;line-height:1.6;margin:0 0 12px}.field input,.field select,.field textarea{display:block;font-size:13px;font-weight:450;margin:6px 0 0}
.formgrid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:0 14px}.wide{grid-column:1/-1}
.tablewrap{overflow:auto;border-radius:10px;border:1px solid #e9edf4}
table{border-collapse:collapse;width:100%;font-size:12px;min-width:610px}td,th{text-align:left;padding:12px 12px;border-bottom:1px solid #ecf0f5;vertical-align:middle}
th{font-size:10px;font-weight:730;text-transform:uppercase;letter-spacing:.5px;background:#f8fafd;color:#72839b}
td{max-width:330px;overflow-wrap:anywhere}tr:last-child td{border-bottom:0}tr:hover td{background:#f9fbff}
tr.clickable{cursor:pointer}td a{font-weight:650}.cell-primary{font-weight:690;color:#224568}
.pill{display:inline-flex;align-items:center;gap:5px;padding:4px 9px;border-radius:999px;background:#edf3fd;color:#315c96;font-size:11px;font-weight:690}
.pill.fail,.pill.critical{color:#b42318;background:#fff0ee}.pill.pass,.pill.active,.pill.completed{color:#127663;background:#e2f7f0}
.pill.pending{color:#8f641e;background:#fff5da}.pill.manual{color:#6e47a4;background:#f2eafd}
.empty{color:#8190a7;text-align:center;padding:40px 15px;line-height:1.6}
.pager{display:flex;justify-content:space-between;align-items:center;padding:13px 0;color:#7a8ca2;font-size:12px}
.notice{background:#f0f7ff;border:1px solid #d5e8ff;padding:14px;border-radius:10px;color:#406188;font-size:12px;line-height:1.6;margin-bottom:16px}
.notice.warn{background:#fffbeb;border-color:#fde68a;color:#8e5b0f}
.notice.success{background:#eafaf3;border-color:#b5e8d0;color:#176652}
.kpirow{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:15px;margin-bottom:17px}
.kpi{display:flex;align-items:center;gap:16px}.ring{width:82px;height:82px;border-radius:50%;display:grid;place-items:center;flex-shrink:0}
.ring-inner{width:65px;height:65px;border-radius:50%;background:white;display:grid;place-items:center;font-size:17px;font-weight:800}
.kpi-label{font-size:12px;color:#718099}.kpi-text{font-size:12px;color:#50657e;line-height:1.6}
.progress{background:#e9eff6;border-radius:999px;height:9px;overflow:hidden}.progress-fill{height:100%;background:#3390de;border-radius:999px}
#detail{position:fixed;z-index:30;right:0;top:0;bottom:0;width:min(540px,46vw);background:#fff;border-left:1px solid #d6e0ee;
box-shadow:-10px 0 30px #1a365314;transform:translateX(105%);transition:transform .22s;display:flex;flex-direction:column}
#detail.open{transform:translateX(0)}.detail-head{border-bottom:1px solid #e5ebf4;padding:23px 24px 17px;display:flex;align-items:flex-start;gap:12px}
.detail-head h2{font-size:20px;letter-spacing:-.4px;margin:0;flex:1;color:#1f3858;overflow-wrap:anywhere}
.detail-content{overflow:auto;flex:1;padding:23px}.detail-footer{padding:13px 23px;border-top:1px solid #e8edf3;background:#fafbfd;display:flex;gap:8px;justify-content:flex-end;flex-wrap:wrap}
.detail-section{padding:0 0 19px;margin-bottom:20px;border-bottom:1px solid #edf1f6}.detail-section:last-child{border:0}
.detail-section h3{font-size:14px;margin:0 0 13px;color:#34506e}
.keyvalues{display:grid;grid-template-columns:1fr 1.5fr;gap:11px 10px;margin:0}.keyvalues dt{color:#718099;font-size:12px}.keyvalues dd{margin:0;font-size:12px;color:#304760;overflow-wrap:anywhere;white-space:pre-wrap}
.mini-list{margin:8px 0 0;padding:0;list-style:none}.mini-list li{margin:6px 0;padding:9px;border:1px solid #e8edf3;background:#f8fafc;border-radius:8px;font-size:12px}
.link-box{max-height:185px;overflow:auto;border:1px solid #d9e4f1;border-radius:9px;padding:7px;background:#fafcff}
.link-option{display:flex;align-items:flex-start;gap:8px;padding:7px 4px;font-size:12px;line-height:1.5;border-bottom:1px solid #ecf0f7}
.link-option:last-child{border:0}.link-option input{width:15px;height:15px;min-height:15px;margin:2px 0 0;flex-shrink:0}
.link-title{font-weight:700;color:#455e7b;font-size:12px;margin:12px 0 7px}.filter-row{margin:6px 0 10px}
.chips{display:flex;flex-wrap:wrap;gap:6px;margin:8px 0}.chip{font-size:11px;border-radius:8px;padding:6px 9px;background:#eff5fd;color:#3a5d8c}
.audit-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:13px}
.architecture{background:linear-gradient(140deg,#0b2039,#193b5b);border-radius:16px;padding:22px;overflow:auto;color:white;box-shadow:0 20px 50px #1c355622}
.architecture svg{width:100%;height:auto;display:block;min-width:900px}
.arch-cards{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin:16px 0}.arch-card{padding:15px;background:#fff;border:1px solid var(--stroke);border-radius:13px;font-size:12px;line-height:1.6}
.arch-card strong{display:block;margin-bottom:5px;color:#244e83;font-size:14px}
.choice-row{display:flex;gap:12px;flex-wrap:wrap;margin-bottom:19px}.choice-row label{flex:1;min-width:190px;font-size:12px;color:#59708a;font-weight:650}
.choice-row select{margin-top:7px}
.badge-note{font-size:11px;color:#8aa1b8}.copy{border:0;color:var(--blue);background:transparent;padding:4px 6px}
#toast{position:fixed;z-index:100;bottom:22px;left:50%;transform:translateX(-50%);background:#1d395c;color:#fff;border-radius:11px;padding:12px 18px;font-size:13px;max-width:min(650px,90vw);box-shadow:0 15px 50px #13284f55;display:none}
.spin{animation:spinning 1s linear infinite;display:inline-block}@keyframes spinning{to{transform:rotate(360deg)}}
@media(max-width:1150px){#main.details-open{padding-right:calc(min(540px,50vw) + 20px)}#detail{width:min(540px,50vw)}.cards{grid-template-columns:repeat(2,1fr)}.kpirow{grid-template-columns:1fr}}
@media(max-width:800px){#sidebar{position:static;width:100%;padding:13px;max-height:none}.brand{margin:0 8px 8px;font-size:19px}.brand small{display:none}
#nav{display:flex;gap:6px;overflow:auto;flex-wrap:nowrap;flex:none}.nav-title{display:none}.nav-button{white-space:nowrap;font-size:11px;padding:9px 10px;width:auto;flex-shrink:0}
.nav-bottom{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:7px 3px 0;margin-top:7px}#identity{padding:4px;min-width:0;overflow-wrap:anywhere}#signout{width:auto;flex-shrink:0;font-size:11px;padding:8px 10px}
#main,#main.details-open{margin-left:0;padding:18px}#detail{width:min(600px,100vw)}.arch-cards{grid-template-columns:1fr}}
@media(max-width:560px){.cards{grid-template-columns:repeat(2,1fr)}.metric{padding:14px}.metric-number{font-size:23px}
#topline{display:block}#topActions{justify-content:flex-start;margin-top:14px}
.formgrid,.audit-grid{grid-template-columns:1fr}.detail-head{padding:17px}.detail-content{padding:18px}.detail-footer{padding:10px 18px}}

/* Resizable split view: reserve list space; keep the form readable on narrow screens. */
:root{--detail-width:540px}
#detail{width:var(--detail-width)}
#main.details-open{padding-right:calc(var(--detail-width) + 35px)}
#detailResize{position:absolute;top:0;bottom:0;left:-7px;width:14px;cursor:col-resize;touch-action:none;z-index:35;outline:none}
#detailResize:before{content:"";position:absolute;left:6px;top:0;bottom:0;width:2px;background:#c3d2e5}
#detailResize:after{content:"⋮";position:absolute;top:48%;left:0;width:14px;text-align:center;padding:12px 0;border-radius:6px;background:#dce8f7;color:#315c96}
#detailResize:hover:before,#detailResize:focus-visible:before{width:4px;left:5px;background:#2667db}
#detailResize:focus-visible:after{outline:3px solid #93b9f5}
#detail:not(.open) #detailResize{display:none}
body.resizing-detail,body.resizing-detail *{cursor:col-resize!important;user-select:none!important}
body.resizing-detail #main,body.resizing-detail #detail{transition:none}
.detail-resize-hint{padding:7px 24px;font-size:11px;color:#59708a;border-bottom:1px solid #e8edf3;background:#f8fafc}
tr.clickable:focus-visible{outline:2px solid #2667db;outline-offset:-2px}
tr.selected-row td{background:#edf5ff;box-shadow:inset 0 -1px #bad3f7}
.relationship-list{list-style:none;margin:10px 0;padding:0;display:grid;gap:8px}
.relationship-list li{border:1px solid #dfe7f1;border-radius:9px;background:#fbfcff;overflow:hidden}
.record-link{display:flex;gap:12px;align-items:center;justify-content:space-between;width:100%;padding:12px;text-align:left;background:none;border:0;color:#245481;font-size:13px;line-height:1.5;overflow-wrap:anywhere}
.record-link:hover{background:#eaf2ff}.record-link span:first-child{min-width:0}
.finding-meta,.finding-origin{padding:0 12px 10px;line-height:1.7;font-size:12px;color:#64748b}
.inline-record-link{border:0;background:none;color:#2667db;font:inherit;padding:0;text-decoration:underline;text-underline-offset:2px}
.relationship-empty{font-size:12px}.detail-section summary{font-size:14px;font-weight:650;cursor:pointer;line-height:1.7;color:#34506e}
.map-viewport{overflow:auto;background:#f8fbff;border:1px solid #dce6f3;border-radius:14px;max-height:calc(100vh - 240px);min-height:380px}
#relationshipMap{display:block;width:100%;height:auto;min-width:0}
.map-node{cursor:pointer}.map-node:hover rect,.map-node:focus-visible rect{stroke:#2563eb;stroke-width:3}
#mapExport{text-decoration:none}.map-viewport:focus-visible{outline:2px solid #2667db;outline-offset:2px}
.map-node:focus-visible{outline:none}.map-controls{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:12px}
.map-note{font-size:12px;line-height:1.7;color:#64748b}
@media(max-width:1150px) and (min-width:1001px){#main.details-open{padding-right:calc(var(--detail-width) + 20px)}}
@media(max-width:1000px){#detail{width:min(620px,100vw)}#main.details-open{padding-right:35px}#detailResize,.detail-resize-hint{display:none}}
@media(max-width:800px){#main.details-open{padding:18px}#detail{width:100vw}.map-viewport{min-height:300px;max-height:75vh}}

</style>
</head>
<body>
<aside id="sidebar">
 <div class="brand">KS <strong>GRC</strong><small>YÖNETİŞİM · RİSK · UYUM</small></div>
 <nav id="nav" aria-label="Ana menü"></nav>
 <div class="nav-bottom"><div id="identity">Kullanıcı hesabı</div>
   <button id="signout" type="button">Oturumu kapat</button></div>
</aside>
<main id="main">
 <header id="topline"><div><h1 id="pageTitle">Genel Bakış</h1><div id="pageSub">Denetim, kontrol ve kanıt yönetimi</div></div>
 <div id="topActions"></div></header>
 <div id="content" aria-live="polite"><div class="panel">İçerik hazırlanıyor…</div></div>
</main>
<aside id="detail" aria-label="Kayıt ayrıntısı" aria-hidden="true" inert>
 <div id="detailResize" role="separator" tabindex="0" aria-orientation="vertical" aria-label="Kayıt ayrıntısı genişliği" aria-controls="detail" aria-valuemin="360" aria-valuemax="900" aria-valuenow="540" title="Genişliği değiştirmek için sürükleyin; çift tıklama ile sıfırlayın"></div>
 <header class="detail-head"><h2 id="detailTitle">Kayıt</h2>
  <button class="btn secondary small" id="closeDetail" aria-label="Ayrıntıyı kapat">Kapat ✕</button></header>
 <div class="detail-resize-hint">Sol kenarı sürükleyerek genişliği değiştirin · Çift tıklama: varsayılan genişlik</div>
 <div id="detailContent" class="detail-content"></div>
 <footer id="detailFooter" class="detail-footer"></footer>
</aside>
<div id="toast" role="status"></div>
<script src="/ksgrc.js" defer></script>
</body></html>"""

def page_html():
    return HTML
