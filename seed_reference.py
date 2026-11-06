"""Idempotent, non-production KS GRC reference/demo dataset.

Never overwrites or deletes manually-entered data. No ServiceNow/Dynamics connection.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path

import app

CATALOG_PATH = Path(__file__).parent / "seed" / "catalog.json"
SCENARIOS_PATH = Path(__file__).parent / "seed" / "operational_scenarios.json"
SEED_KEY = "ks-grc-reference-2026-11-04-v1"
ISO_CODE = "ISO/IEC 20000-1"
CIS_CODE = "CIS Controls"


def clause_ref(token):
    prefix, code = token.split(":", 1)
    if prefix == "ISO":
        return ISO_CODE, code
    if prefix == "CIS":
        return CIS_CODE, code
    raise ValueError("Unknown standard prefix: " + prefix)


def existing_id(db, table, where, args):
    value = db.execute(f"SELECT id FROM {table} WHERE {where} LIMIT 1", args).fetchone()
    return value["id"] if value else None


def seed():
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    scenario = json.loads(SCENARIOS_PATH.read_text(encoding="utf-8"))
    if catalog["data_classification"] != "SIMULATED_NON_PRODUCTION":
        raise ValueError("Refusing to run non-simulation catalog")
    if scenario["classification"] != "SIMULATED":
        raise ValueError("Refusing to run non-simulation scenario data")
    app.initialize()
    counters = {"standards": 0, "clauses": 0, "processes": 0, "objectives": 0,
                "controls": 0, "audits": 0, "evidence": 0, "executions": 0, "findings": 0}
    evidence_files = []
    with app.connect() as db:
        db.execute("""CREATE TABLE IF NOT EXISTS seed_runs (
            key TEXT PRIMARY KEY, applied_at TEXT NOT NULL, summary_json TEXT NOT NULL)""")
        prev = db.execute("SELECT summary_json FROM seed_runs WHERE key=?", (SEED_KEY,)).fetchone()
        if prev:
            return {"skipped": True, "summary": json.loads(prev["summary_json"])}
        standard_ids = {}
        clause_ids = {}
        for record in catalog["standards"]:
            sid = existing_id(db, "standards", "code=? AND version=?", (record["code"], record["version"]))
            if sid is None:
                sid = app.insert(db, "standards", {key: record[key] for key in ("code", "name", "version", "description")})
                counters["standards"] += 1
            standard_ids[record["code"]] = sid
            clauses_by_code = {}
            for row in record["clauses"]:
                cid = existing_id(db, "clauses", "standard_id=? AND code=?", (sid, row["code"]))
                if cid is None:
                    cid = app.insert(db, "clauses", {
                        "standard_id": sid, "code": row["code"],
                        "title": row["title"], "description": row.get("description", "")})
                    counters["clauses"] += 1
                clauses_by_code[row["code"]] = cid
                clause_ids[(record["code"], row["code"])] = cid
            for row in record["clauses"]:
                key = row["code"]
                if "." in key:
                    parent = key.rsplit(".", 1)[0]
                    if parent in clauses_by_code:
                        db.execute("""UPDATE clauses SET parent_id=?
                            WHERE id=? AND parent_id IS NULL""",
                            (clauses_by_code[parent], clauses_by_code[key]))

        process_ids = {}
        for code, name, owner, description in scenario["processes"]:
            ident = existing_id(db, "processes", "code=?", (code,))
            if ident is None:
                ident = app.insert(db, "processes", {
                    "code": code, "name": name, "owner": owner, "description": description})
                counters["processes"] += 1
            process_ids[code] = ident

        objective_ids = {}
        for code, name in scenario["objectives"]:
            ident = existing_id(db, "objectives", "code=?", (code,))
            if ident is None:
                ident = app.insert(db, "objectives", {
                    "code": code, "name": name,
                    "description": "Örnek yönetilen hizmetler kontrol hedefi."})
                counters["objectives"] += 1
            objective_ids[code] = ident

        control_ids = {}
        for control in scenario["controls"]:
            ident = existing_id(db, "controls", "code=?", (control["code"],))
            if ident is None:
                fields = ("code", "name", "description", "execution_mode", "nature",
                          "frequency", "method", "expected_result", "owner")
                ident = app.insert(db, "controls", {f: control[f] for f in fields})
                counters["controls"] += 1
            control_ids[control["code"]] = ident
            mapped_clauses = [clause_ids[clause_ref(code)] for code in control["clauses"]]
            app.mapping(db, "control_clauses", "control_id", ident, "clause_id", mapped_clauses)
            app.mapping(db, "control_processes", "control_id", ident, "process_id",
                        [process_ids[k] for k in control["processes"]])
            app.mapping(db, "control_objectives", "control_id", ident, "objective_id",
                        [objective_ids[k] for k in control["objectives"]])

        audit_ids = {}
        finish_after_runs = {}
        for audit in scenario["audits"]:
            aid = existing_id(db, "audits", "name=?", (audit["name"],))
            if aid is None:
                payload = {k: audit.get(k) for k in ("name", "scope", "planned_start", "planned_end",
                   "actual_start", "actual_end", "status", "auditors", "auditees")}
                terminal = payload["status"] in ("completed","closed","cancelled")
                if terminal:
                    payload["status"]="in_progress"
                aid = app.insert(db, "audits", payload)
                if terminal:
                    finish_after_runs[aid]=audit["status"]
                counters["audits"] += 1
            audit_ids[audit["key"]] = aid
            if audit.get("standard"):
                target = [ident for (standard, code), ident in clause_ids.items()
                          if standard == audit["standard"]]
            else:
                target = [clause_ids[clause_ref(x)] for x in audit["clauses"]]
            app.mapping(db, "audit_clauses", "audit_id", aid, "clause_id", target)

        evidence_ids = {}
        for control in scenario["controls"]:
            sample = control["example"]
            name = "[SİMÜLASYON] {} — {}".format(control["code"], control["name"])
            evidence_id = existing_id(db, "evidence", "title=? AND source=?", (name, "demo_seed"))
            evidence_blob = {
                "schema": "ks-grc-evidence-demo-v1",
                "classification": "SYNTHETIC_TEST_ONLY",
                "notice": "Bu belge GERÇEK ServiceNow, Dynamics, SIEM veya altyapı sorgusu değildir.",
                "control_code": control["code"],
                "control_title": control["name"],
                "generated_for": "KS GRC / entegrasyon UAT",
                "test_observation_at": "2026-10-24T10:15:00+03:00",
                "reported_source": sample["source_system"],
                "sample_record_reference": sample["reference"],
                "sample_size": sample["checked"],
                "sample_nonconformities": sample["failed"],
                "assessment": "PASS" if sample["status"] == "pass" else "FAIL",
                "sample_description": sample["details"],
                "audit_evidence_note": "Örnek çıktı: gerçek bir denetimin kanıtı olarak sunulamaz.",
            }
            blob = (json.dumps(evidence_blob, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
            digest = hashlib.sha256(blob).hexdigest()
            if evidence_id is None:
                evidence_id = app.insert(db, "evidence", {
                    "title": name,
                    "description": "[SİMÜLASYON] Yapay veri ile oluşturulmuş, gerçek denetim kanıtı değildir.",
                    "reference_url": "urn:ks-grc:simulation:" + control["code"].lower(),
                    "collected_at": "2026-10-24T10:15:00+03:00",
                    "source": "demo_seed",
                    "hash_sha256": digest})
                counters["evidence"] += 1
            evidence_ids[control["code"]] = evidence_id
            app.mapping(db, "evidence_clauses", "evidence_id", evidence_id, "clause_id",
                        [clause_ids[clause_ref(x)] for x in control["clauses"]])
            app.mapping(db, "evidence_processes", "evidence_id", evidence_id, "process_id",
                        [process_ids[x] for x in control["processes"]])
            evidence_files.append((evidence_id, blob, digest))

        # Evidence files are synthetic JSON artifacts, not references to non-existent screenshots.
        folder = Path(app.EVIDENCE_DIR)
        folder.mkdir(parents=True, exist_ok=True, mode=0o700)
        for evidence_id, blob, digest in evidence_files:
            path = folder / str(evidence_id)
            if path.exists():
                if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                    raise ValueError("Existing evidence file differs; refusing overwrite: " + str(path))
            else:
                with path.open("xb") as out:
                    out.write(blob)
                path.chmod(0o600)


        # Demonstrate that a single evidence item can substantiate several controls.
        shared = {"KS-DEMO-CTL-021": ["KS-DEMO-CTL-001"],
                  "KS-DEMO-CTL-022": ["KS-DEMO-CTL-001"],
                  "KS-DEMO-CTL-008": ["KS-DEMO-CTL-002"]}

        for index, control in enumerate(scenario["controls"]):
            sample = control["example"]
            code = control["code"]
            categories = set(control["processes"])
            audit_key = ("AUD-CROSS" if ("CFG" in categories or "CHG" in categories)
                         else "AUD-CIS-Q4" if categories.intersection(
                             {"SEC", "IAM", "VULN", "LOG", "BCM", "ASSET", "SDLC"})
                         else "AUD-ISO-Q4")
            ids = [evidence_ids[code]] + [evidence_ids[prior] for prior in shared.get(code, [])]
            payload = {
                "control_id": control_ids[code], "audit_id": audit_ids[audit_key],
                "status": sample["status"],
                "source": "mcp" if control["execution_mode"] == "automatic" else "manual",
                "details": "[SİMÜLASYON] " + sample["details"],
                "executed_at": "2026-11-0{}T{:02d}:30:00+03:00".format(
                    1 + (index % 3), 9 + (index % 8)),
                "severity": sample["severity"],
                "evidence_ids": ids
            }
            result = app.execute(db, payload)
            counters["executions"] += 1
            if result["finding_id"]:
                counters["findings"] += 1

            # The same evidence is reused in an older cross-audit run, for audit-history UAT.
            if code in {"KS-DEMO-CTL-001", "KS-DEMO-CTL-002",
                        "KS-DEMO-CTL-008", "KS-DEMO-CTL-009"}:
                historical = dict(payload)
                historical["audit_id"] = audit_ids["AUD-CROSS"]
                historical["executed_at"] = "2026-10-24T14:30:00+03:00"
                historical["details"] = "[SİMÜLASYON / ÖNCEKİ DENETİM] " + sample["details"]
                result = app.execute(db, historical)
                counters["executions"] += 1
                if result["finding_id"]:
                    counters["findings"] += 1

        for aid, status in finish_after_runs.items():
            db.execute("UPDATE audits SET status=? WHERE id=?", (status,aid))
            app.grc_plus.capture_audit_plan(db,aid)
        db.execute("INSERT INTO seed_runs(key,applied_at,summary_json) VALUES(?,?,?)",
                   (SEED_KEY, app.utcnow(), json.dumps(counters, ensure_ascii=False)))
        db.commit()
        return {"skipped": False, "summary": counters}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import synthetic KS GRC UAT catalog/data once")
    parser.add_argument("--apply", action="store_true", help="Required explicit opt-in")
    args = parser.parse_args()
    if not args.apply:
        parser.error("Add --apply to import the synthetic reference dataset")
    print(json.dumps(seed(), ensure_ascii=False))
