"""Risk statements are reusable scenarios. Assessments are dated decisions for one exposure."""
from datetime import date
import json
from decimal import Decimal

CATALOG_FIELDS = {
    "code":"TEXT NOT NULL UNIQUE", "title":"TEXT NOT NULL", "category":"TEXT NOT NULL DEFAULT 'operational'",
    "cause":"TEXT NOT NULL", "risk_event":"TEXT NOT NULL", "consequence":"TEXT NOT NULL",
    "likelihood":"INTEGER NOT NULL DEFAULT 3", "impact":"INTEGER NOT NULL DEFAULT 3",
}
REGISTER_FIELDS = {
    "catalog_id":"INTEGER REFERENCES risk_catalog(id)", "entity_name":"TEXT", "cause":"TEXT",
    "risk_event":"TEXT", "consequence":"TEXT", "review_date":"TEXT",
    "response_strategy":"TEXT", "appetite":"INTEGER"
}
STRATEGIES={"mitigate":"Azalt","avoid":"Kaçın","transfer":"Devret / paylaş","accept":"Kabul et"}
# Starting scenarios for the register, with no claim of actual exposure.
EXAMPLES=[
    ("EOS","Destek süresi biten bileşen","security","Üretici desteği sona erdiği için","kritik bir zafiyet yamalanamayabilir","hizmette kesinti veya veri ihlali yaşanabilir"),
    ("PATCH","Kritik yamada gecikme","security","Kritik güvenlik yamaları hedef sürede uygulanmadığı için","bilinen bir zafiyet istismar edilebilir","müşteri verisinin gizliliği zarar görebilir"),
    ("CHANGE","Yetkisiz üretim değişikliği","operational","Üretim erişimi ile onay yetkisi ayrılmadığı için","test edilmemiş bir değişiklik devreye alınabilir","hizmet seviyesi taahhüdü ihlal edilebilir"),
    ("RESTORE","Yedekten geri dönüş","continuity","Geri yükleme provaları temsili veriyle yapılmadığı için","kritik bir hizmet hedef sürede kurtarılamayabilir","veri kaybı ve sözleşmesel kesinti oluşabilir"),
    ("SUPPLIER","Tek tedarikçiye bağımlılık","supplier","Kritik hizmette alternatif tedarikçi bulunmadığı için","tedarikçi kesintisi hizmeti durdurabilir","müşteriye taahhüt edilen süre aşılabilir"),
    ("CMDB","Eksik hizmet bağımlılıkları","operational","CMDB ilişki bilgileri güncel tutulmadığı için","değişiklikten etkilenecek bir hizmet gözden kaçabilir","plansız kesinti yaşanabilir"),
    ("CAPACITY","Veri merkezi kapasitesi","continuity","Kapasite tahmininde büyüme dikkate alınmadığı için","yoğun dönemde kapasite tükenebilir","kritik uygulamaların erişilebilirliği düşebilir"),
    ("PRIVACY","Kanıtlarda kişisel veri","privacy","Kanıt toplarken veri minimizasyonu uygulanmadığı için","gereksiz kişisel veriler denetim paketine girebilir","kişisel veriler yetkisiz kişilerle paylaşılabilir"),
]
def setup(db):
    db.execute("""CREATE TABLE IF NOT EXISTS risk_assessments(
      id INTEGER PRIMARY KEY, risk_id INTEGER NOT NULL REFERENCES risks(id),
      assessed_at TEXT NOT NULL, assessor TEXT NOT NULL, rationale TEXT NOT NULL,
      inherent INTEGER NOT NULL, residual REAL NOT NULL, appetite INTEGER NOT NULL,
      snapshot TEXT NOT NULL)""")
    db.execute("CREATE INDEX IF NOT EXISTS risk_assessment_risk ON risk_assessments(risk_id,id DESC)")
    db.executemany("""INSERT INTO risk_catalog(code,title,category,cause,risk_event,consequence)
        VALUES(?,?,?,?,?,?) ON CONFLICT(code) DO NOTHING""",EXAMPLES)

def validate(table,data):
    if table=="risk_catalog" or any(data.get(k) for k in ("catalog_id","cause","risk_event","consequence")):
        for k in ("cause","risk_event","consequence"):
            if not isinstance(data.get(k),str) or not data[k].strip():
                raise ValueError("Risk ifadesi için neden, olay ve etkiyi birlikte girin")
    if table=="risks":
        a=data.get("appetite")
        if a is not None and (type(a) is not int or not 1<=a<=25):
            raise ValueError("Risk iştahı eşiği 1–25 arasında olmalı")
        for k in ("due_date","review_date"):
            if data.get(k):
                try:
                    if date.fromisoformat(data[k]).isoformat()!=data[k]:raise ValueError
                except (ValueError,TypeError):raise ValueError("Geçerli bir tarih girin") from None

def context(db,rid):
    from grc_plus import rows
    risk=db.execute("SELECT * FROM risks WHERE id=?",(rid,)).fetchone()
    if not risk:return None
    controls=rows(db,"""SELECT c.id,c.code,c.name,c.active,x.id AS run_id,x.status AS test_status,x.executed_at,
       EXISTS(SELECT 1 FROM execution_evidence_versions v JOIN evidence e ON e.id=v.evidence_id
         WHERE v.execution_id=x.id AND v.sha256 IS NOT NULL AND e.source!='demo_seed'
         AND e.status='current' AND (NULLIF(e.expires_at,'') IS NULL OR e.expires_at >= DATE('now'))
         AND x.source!='demo_seed') AS has_evidence
       FROM controls c JOIN control_risks cr ON cr.control_id=c.id
       LEFT JOIN executions x ON x.id=(SELECT id FROM executions WHERE control_id=c.id
          ORDER BY julianday(executed_at) DESC,id DESC LIMIT 1)
       WHERE cr.risk_id=? ORDER BY c.code""",(rid,))
    history=rows(db,"SELECT * FROM risk_assessments WHERE risk_id=? ORDER BY id DESC",(rid,))
    for assessment in history:assessment["snapshot"]=json.loads(assessment["snapshot"])
    return {"controls":controls,"assessments":history,
            "actions":rows(db,"SELECT * FROM actions WHERE risk_id=? ORDER BY id DESC",(rid,))}

def decision(db,rid,previous,proposal):
    status=proposal.get("status","open")
    if status not in ("accepted","closed"):return
    if previous.get("status")==status:
        if any(proposal.get(k)!=v for k,v in previous.items()):
            raise ValueError("Karar verilmiş riski değiştirmeden önce yeniden açın")
        return
    if not rid or not (proposal.get("treatment") or "").strip() or not (proposal.get("owner") or "").strip():
        raise ValueError("Kabul veya kapanış için kayıtlı değerlendirme, risk sahibi ve karar gerekçesi gerekir")
    latest=db.execute("SELECT * FROM risk_assessments WHERE risk_id=? ORDER BY id DESC LIMIT 1",(rid,)).fetchone()
    if not latest:raise ValueError("Önce artık risk değerlendirmesi kaydedilmeli")
    snapshot=json.loads(latest["snapshot"])
    if any(proposal.get(k)!=snapshot.get(k) for k in
           ("entity_name","cause","risk_event","consequence","likelihood","impact","owner")) or latest["appetite"]!=proposal.get("appetite"):
        raise ValueError("Risk değişti. Kabul veya kapanıştan önce yeniden değerlendirin")
    current={c["id"]:c for c in context(db,rid)["controls"]}
    for c in snapshot["credits"]:
        now=current.get(c["id"])
        if not now or not now["active"] or now["run_id"]!=c["run_id"] or not now["has_evidence"]:
            raise ValueError("Kontrol kanıtı değişti. Yeniden değerlendirin")
    if status=="accepted":
        if proposal.get("response_strategy")!="accept" or not proposal.get("review_date") or proposal["review_date"]<date.today().isoformat():
            raise ValueError("Kabul stratejisini ve geçerli bir gözden geçirme tarihini seçin")
    if status=="closed" and db.execute("SELECT 1 FROM actions WHERE risk_id=? AND status NOT IN ('completed','cancelled')",(rid,)).fetchone():
        raise ValueError("Açık işleme faaliyeti olan risk kapatılamaz")


def assess(db,rid,data,actor,now):
    if not db.in_transaction:db.execute("BEGIN IMMEDIATE")
    ctx=context(db,rid)
    if ctx is None:raise ValueError("Risk bulunamadı")
    risk=dict(db.execute("SELECT * FROM risks WHERE id=?",(rid,)).fetchone())
    if not (risk.get("owner") or "").strip() or not (risk.get("entity_name") or "").strip() or not risk.get("appetite") or not risk.get("review_date"):
        raise ValueError("Önce risk sahibini, etkilenen varlığı/hizmeti, gözden geçirme tarihini ve risk iştahı eşiğini kaydedin")
    if not all(risk.get(k) for k in ("cause","risk_event","consequence")):
        raise ValueError("Değerlendirme için neden, olay ve etkiyi tanımlayın")
    rationale=data.get("rationale")
    if not isinstance(rationale,str) or not rationale.strip() or len(rationale)>5000:
        raise ValueError("Bir değerlendirme gerekçesi girin (en fazla 5.000 karakter)")
    proposals=data.get("credits",[])
    if not isinstance(proposals,list) or len(proposals)>len(ctx["controls"]):
        raise ValueError("Kontrol katkıları geçersiz")
    by_id={c["id"]:c for c in ctx["controls"]}
    credits=[];seen=set();total=Decimal(0)
    weights={"low":Decimal("0.2"),"medium":Decimal("0.4"),"high":Decimal("0.6")}
    for selection in proposals:
        if not isinstance(selection,dict):raise ValueError("Kontrol katkısı geçersiz")
        cid=selection.get("control_id")
        if type(cid) is not int or cid in seen or cid not in by_id:raise ValueError("İlişkisiz veya tekrarlanan kontrol")
        seen.add(cid);control=by_id[cid]
        weight=selection.get("weight");effect=selection.get("effectiveness")
        if not isinstance(weight,str) or weight not in weights or effect not in ("partial","effective"):raise ValueError("Kontrol değerlendirmesi geçersiz")
        if (not control["active"] or control["test_status"]!="pass" or not control["has_evidence"] or
                type(selection.get("run_id")) is not int or selection["run_id"]!=control["run_id"]):
            raise ValueError("Katkı için güncel, başarılı ve kanıta bağlı kontrol sonucu gerekli")
        contribution=weights[weight]*(Decimal("0.5") if effect=="partial" else 1)
        total+=contribution
        credits.append({**control,"weight":weight,"effectiveness":effect,"contribution":float(contribution)})
    inherent=risk["likelihood"]*risk["impact"]
    residual=float(inherent*(1-min(total,Decimal(1))))
    snapshot={k:risk.get(k) for k in ("code","title","owner","entity_name","cause","risk_event","consequence",
              "catalog_id","review_date","likelihood","impact","response_strategy","treatment")}
    snapshot.update({"method":"weighted-v1","credits":credits})
    aid=db.execute("""INSERT INTO risk_assessments(risk_id,assessed_at,assessor,rationale,inherent,residual,appetite,snapshot)
             VALUES(?,?,?,?,?,?,?,?)""",(rid,now,actor,rationale.strip(),inherent,residual,risk["appetite"],json.dumps(snapshot,ensure_ascii=False))).lastrowid
    return {"id":aid,"inherent":inherent,"residual":residual,"above_appetite":residual>risk["appetite"]}
