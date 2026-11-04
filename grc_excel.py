"""Localized Excel round-trip for core KS GRC records and relationships.

No user credentials or binary evidence files are included in workbook exports.
"""
import base64
import binascii
import hashlib
import json
import re
from collections import OrderedDict

import xlsx_io

TABLE_ORDER = ("standards", "processes", "objectives", "clauses", "controls",
               "audits", "evidence", "risks", "actions", "documents",
               "executions", "findings")
SHEETS = {
    "standards":"Standartlar",
    "processes":"Süreçler",
    "objectives":"Kontrol Hedefleri",
    "clauses":"Standart Maddeleri",
    "controls":"Kontroller",
    "audits":"Denetimler",
    "evidence":"Kanıtlar",
    "risks":"Riskler",
    "actions":"Düzeltici Faaliyetler",
    "documents":"Dokümanlar",
    "executions":"Kontrol Sonuçları",
    "findings":"Bulgular"
}
RELATIONS = (
    ("Kontrol - Madde", "control_clauses", "controls", "clauses", "control_id", "clause_id"),
    ("Kontrol - Süreç", "control_processes", "controls", "processes", "control_id", "process_id"),
    ("Kontrol - Hedef", "control_objectives", "controls", "objectives", "control_id", "objective_id"),
    ("Denetim - Madde", "audit_clauses", "audits", "clauses", "audit_id", "clause_id"),
    ("Kanıt - Denetim", "evidence_audits", "evidence", "audits", "evidence_id", "audit_id"),
    ("Kanıt - Kontrol", "evidence_controls", "evidence", "controls", "evidence_id", "control_id"),
    ("Kanıt - Madde", "evidence_clauses", "evidence", "clauses", "evidence_id", "clause_id"),
    ("Kanıt - Süreç", "evidence_processes", "evidence", "processes", "evidence_id", "process_id"),
    ("Risk - Kontrol", "control_risks", "risks", "controls", "risk_id", "control_id"),
    ("Doküman - Kontrol", "document_controls", "documents", "controls", "document_id", "control_id"),
    ("Kontrol Çalışması - Kanıt", "execution_evidence", "executions", "evidence", "execution_id", "evidence_id")
)
MAX_ROWS_IMPORT = 3000
STRING_LIMIT = 10000


def columns(table):
    import app
    return ["id"]+list(app.TABLES[table])


def export(db, table):
    import app
    import grc_plus
    if table != "all" and table not in TABLE_ORDER:
        raise ValueError("Bilinmeyen Excel kaydı")
    target = TABLE_ORDER if table == "all" else (table,)
    sheets=OrderedDict()
    for name in target:
        fields=columns(name)
        header=[grc_plus.FIELD_LABELS.get(x,x.replace("_"," ").title()) for x in fields]
        records=db.execute(f"SELECT * FROM {name} ORDER BY id LIMIT ?",(5000,)).fetchall()
        sheets[SHEETS[name]]=[header]+[[rec[field] for field in fields] for rec in records]
    if table=="all":
        values=[["İlişki Türü","Kaynak Anahtar","Hedef Anahtar"]]
        for label, link, source, target_name, parent_col, target_col in RELATIONS:
            links=db.execute(f"SELECT {parent_col} AS parent, {target_col} AS target FROM {link} ORDER BY {parent_col},{target_col}").fetchall()
            for l in links[:15000]:
                source_key=key_for_id(db,source,l["parent"])
                target_key=key_for_id(db,target_name,l["target"])
                if source_key is not None and target_key is not None:
                    values.append([label,source_key,target_key])
        if len(values)>xlsx_io.MAX_ROWS:
            # Split over multiple 5000-line sheets without losing relations.
            chunks=[values[1+i:1+i+4998] for i in range(0,len(values)-1,4998)]
            for i, chunk in enumerate(chunks,1):
                sheets[f"Bağlantılar {i}"]=[values[0]]+chunk
        else:
            sheets["Bağlantılar"]=values
    return xlsx_io.make_xlsx(sheets)


def key_for_id(db,table,rid):
    import app
    row=db.execute(f"SELECT * FROM {table} WHERE id=?",(rid,)).fetchone()
    if not row:
        return None
    if table=="clauses":
        standard=db.execute("SELECT code FROM standards WHERE id=?",(row["standard_id"],)).fetchone()
        return (standard["code"] if standard else "")+" :: "+row["code"]
    if table=="executions":
        return str(row["id"])
    if table=="evidence":
        return row["title"]+" :: "+(row["source"] or "")
    if table=="audits":
        return row["name"]
    if table=="findings":
        return str(row["id"])
    if "code" in row.keys():
        return row["code"]
    return row["title"] if "title" in row.keys() else str(row["id"])


def id_for_key(db,table,key):
    import app
    key=str(key).strip()
    if not key:
        return None
    if table=="clauses":
        if " :: " not in key:
            return None
        scode, clause=key.split(" :: ",1)
        row=db.execute("""SELECT c.id FROM clauses c JOIN standards s ON s.id=c.standard_id
                            WHERE s.code=? AND c.code=? LIMIT 1""",(scode,clause)).fetchone()
    elif table=="evidence":
        title,sep,source=key.rpartition(" :: ")
        if not sep:
            return None
        row=db.execute("SELECT id FROM evidence WHERE title=? AND source=? LIMIT 1",
                       (title,source)).fetchone()
    elif table=="audits":
        row=db.execute("SELECT id FROM audits WHERE name=? LIMIT 1",(key,)).fetchone()
    elif table in ("executions","findings"):
        try:
            number=int(key)
        except ValueError:
            return None
        row=db.execute(f"SELECT id FROM {table} WHERE id=?",(number,)).fetchone()
    else:
        row=db.execute(f"SELECT id FROM {table} WHERE code=? LIMIT 1",(key,)).fetchone()
    return row["id"] if row else None


def _as_text(value):
    if value is None:
        return None
    if isinstance(value,(int,float)):
        return str(value)
    return str(value).strip()


def _parse_records(db, table, sheet):
    import app, grc_plus
    if not sheet or len(sheet)<2:
        return {"inserted":0,"skipped":0}
    if len(sheet)>MAX_ROWS_IMPORT+1:
        raise ValueError(f"{SHEETS[table]}: tek seferde en fazla 3.000 kayıt")
    headers=[_as_text(h) or "" for h in sheet[0]]
    aliases={}
    for field in columns(table):
        aliases[field.casefold()]=field
        aliases[grc_plus.FIELD_LABELS.get(field,field).casefold()]=field
    mapping=[]
    for label in headers:
        key=aliases.get(label.casefold())
        if not key and label:
            raise ValueError(f"{SHEETS[table]}: tanınmayan alan: {label}")
        mapping.append(key)
    if "id" in mapping:
        # ID is exported for traceability but never imported as a primary key.
        pass
    stats={"inserted":0,"skipped":0}
    for index,row in enumerate(sheet[1:],2):
        data={}
        for col,field in enumerate(mapping):
            if not field or field=="id" or col>=len(row):
                continue
            raw=_as_text(row[col])
            if raw is None or raw=="":
                continue
            if len(raw)>STRING_LIMIT:
                raise ValueError(f"{SHEETS[table]} satır {index}: hücre çok uzun")
            if field.endswith("_id") or field in ("likelihood","impact","active","file_size"):
                try:
                    data[field]=int(raw)
                except ValueError:
                    raise ValueError(f"{SHEETS[table]} satır {index}: {field} sayı olmalı")
            else:
                data[field]=raw
        if not data:
            continue
        for field in ("status","frequency","nature","execution_mode","source",
                      "criticality","method_type","confidentiality","category","priority"):
            if field in data and field in grc_plus.CHOICES.get(table,{}):
                choices=grc_plus.CHOICES[table][field]
                inverted={v.casefold():k for k,v in choices.items()}
                if str(data[field]).casefold() in inverted:
                    data[field]=inverted[str(data[field]).casefold()]
        # Secure import: no arbitrary fields, no login data or binary file payload.
        grc_plus.validate_record(table,data)
        natural=None
        if table=="clauses":
            if "standard_id" not in data or "code" not in data:
                raise ValueError("Standart maddesi için Standart ve Kod zorunlu")
            natural=("standard_id=? AND code=?",(data["standard_id"],data["code"]))
        elif table in ("audits",):
            if not data.get("name"):
                raise ValueError("Denetim adı gerekli")
            natural=("name=?",(data["name"],))
        elif table=="evidence":
            if not data.get("title"):
                raise ValueError("Kanıt başlığı gerekli")
            data.setdefault("source","manual")
            natural=("title=? AND source=?",(data["title"],data["source"]))
        elif table in ("executions",):
            if not data.get("control_id") or not data.get("status"):
                raise ValueError("Kontrol sonucu için Kontrol ve Durum gerekli")
            if data.get("executed_at"):
                natural=("control_id=? AND executed_at=?",(data["control_id"],data["executed_at"]))
        elif table=="findings":
            if not data.get("title"):
                raise ValueError("Bulgu başlığı gerekli")
            natural=("title=? AND IFNULL(execution_id,0)=?",(data["title"],data.get("execution_id",0)))
        elif "code" in app.TABLES[table]:
            if not data.get("code"):
                raise ValueError(f"{SHEETS[table]} kodu gerekli")
            natural=("code=?",(data["code"],))
        if natural is not None and db.execute(f"SELECT id FROM {table} WHERE {natural[0]} LIMIT 1",natural[1]).fetchone():
            stats["skipped"]+=1
            continue
        for field in app.TABLES[table]:
            definition=app.TABLES[table][field]
            if "NOT NULL" in definition and "DEFAULT" not in definition and field not in data and field not in ("created_at","executed_at","collected_at"):
                raise ValueError(f"{SHEETS[table]} satır {index}: zorunlu alan eksik: {field}")
        if table in ("risks","actions","documents") and "created_at" not in data:
            data["created_at"]=app.utcnow()
        app.insert(db,table,data)
        stats["inserted"]+=1
    return stats


def _relations(db,records):
    relations={label:(table,src,dest,src_col,dest_col)
               for label,table,src,dest,src_col,dest_col in RELATIONS}
    added=0
    for index,row in enumerate(records[1:],2):
        if len(row)<3 or not (row[0] and row[1] and row[2]):
            continue
        label,source,target=map(str,row[:3])
        if label not in relations:
            raise ValueError(f"Bağlantılar satır {index}: bilinmeyen ilişki türü {label}")
        table,src,dest,src_col,dest_col=relations[label]
        source_id=id_for_key(db,src,source)
        target_id=id_for_key(db,dest,target)
        if not source_id or not target_id:
            raise ValueError(f"Bağlantılar satır {index}: referans çözülemedi ({source} → {target})")
        cursor=db.execute(f"INSERT OR IGNORE INTO {table}({src_col},{dest_col}) VALUES(?,?)",
                          (source_id,target_id))
        added+=max(0,cursor.rowcount)
    return added


def import_xlsx(db,payload,table):
    import grc_plus
    if table!="all" and table not in TABLE_ORDER:
        raise ValueError("Excel içe aktarma türü geçersiz")
    encoded=payload.get("content_base64")
    if not isinstance(encoded,str) or len(encoded)>xlsx_io.MAX_UPLOAD*4//3+200:
        raise ValueError("XLSX dosyası en fazla 12 MB olmalı")
    try:
        binary=base64.b64decode(encoded,validate=True)
    except (ValueError,binascii.Error):
        raise ValueError("Geçerli XLSX base64 verisi gerekli")
    parsed=xlsx_io.read_xlsx(binary)
    stats={}
    wanted=TABLE_ORDER if table=="all" else (table,)
    found=False
    for name in wanted:
        if SHEETS[name] in parsed:
            found=True
            stats[name]=_parse_records(db,name,parsed[SHEETS[name]])
    if not found:
        raise ValueError("Excel içinde seçilen kayıt türüne ait sayfa yok")
    if table=="all":
        total=0
        for name, rows in parsed.items():
            if name=="Bağlantılar" or re.fullmatch(r"Bağlantılar [0-9]+",name):
                total+=_relations(db,rows)
        stats["relationships"]={"inserted":total}
    return stats
