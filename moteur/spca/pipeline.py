"""Orchestration SPCA-CI : EXTRACT → NORMALIZE → IDENTIFY CONTEXT → RETRIEVE RULE → VERIFY RULE DATE →
CALCULATE → COMPARE → FIND → SCORE → EXPLAIN → CITE → ESCALATE (architecture §21)
+ Module 10 — Audit Log & Evidence Store."""
from __future__ import annotations

import datetime as dt
import json
import uuid
from decimal import Decimal
from pathlib import Path

from .calc import CalcEnv, reconstruction
from .checker import intrinsic, mentions_check, required_families, run_rule, social_checks
from .common import (AGENT_VERSION, CONFORME, ESCALADE_TXT, FAMILLES, MSG_NQ, NA, NON_CONFORME,
                     RESULTATS_CONCLUSIFS, Control, periode_bornes)
from .context import resolve
from .intake import extract, fval, intake
from .registry import Registry
from .retriever import reference, retrieve
from .risk_gate import confidence, gate, score, write_queue

ICI = Path(__file__).resolve().parents[1]


def load_config(path: Path | None = None) -> dict:
    p = path or (ICI / "config_spca.json")
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def _jsonable(o):
    if isinstance(o, Decimal):
        return int(o) if o == o.to_integral() else float(o)
    if isinstance(o, (dt.date, dt.datetime)):
        return o.isoformat()
    if isinstance(o, set):
        return sorted(o)
    return str(o)


def _control_dict(c: Control) -> dict:
    return {"control_id": c.control_id, "family": FAMILLES.get(c.control_id), "order": c.order,
            "control_name": c.control_name, "status": c.status, "error_code": c.error_code, "rule_id": c.rule_id, "rule_version": c.rule_version,
            "observed_value": c.observed_value, "expected_value": c.expected_value, "difference": c.difference,
            "legal_reference": c.legal_reference, "finding": c.finding, "recommendation": c.recommendation,
            "severity": c.severity, "impact_type": c.impact_type, "favorable_to": c.favorable_to,
            "reserves": c.reserves, "trace": c.trace, "evidence_fields": c.evidence_fields,
            "risk_variables": c.risk_variables, "human_flags": c.human_flags}


def audit(req: dict, referentiel: Path, cfg: dict | None = None) -> dict:
    cfg = cfg or load_config()
    started = dt.datetime.now().isoformat(timespec="seconds")
    req = req.get("audit_request", req)
    req.setdefault("audit", {})
    audit_id = req["audit"].get("audit_id") or f"AUD-{uuid.uuid4().hex[:10].upper()}"
    req["audit"]["audit_id"] = audit_id

    m1 = intake(req)                                    # MODULE 1
    ex = extract(req)                                   # MODULE 2
    reg = Registry(referentiel)
    stops, notes = list(m1["stops"]), list(m1["notes"])
    for k, lib in (("payroll.base_salary", "salaire de base (REM-001)"), ("payroll.gross_salary", "brut (NET-001)"),
                   ("payroll.net_salary", "net (NET-004)")):
        if fval(ex, k) is None:
            notes.append(f"STOP PARTIEL — {lib} absent : contrôles dépendants non réalisés")
    if fval(ex, "employer.legal_name") is None:
        notes.append("Raison sociale employeur absente (EMP-001) — à demander")

    blocking = [s for s in stops if s.startswith(("STOP 1", "STOP 2", "STOP 3"))]
    controls, ctx_flags, rules_info, ctxr = [], [], {"applicable": [], "excluded": [], "undetermined": [], "conflicts": []}, None
    var = {k.split(".", 1)[1]: v.value for k, v in ex["fields"].items() if k.startswith("payroll.") and v.present}
    recon = reconstruction(ex["lines"], {k: Decimal(str(v)) if isinstance(v, (int, float)) else v for k, v in var.items()})
    if not blocking:
        ctxr = resolve(ex, reg, cfg)                    # MODULE 3
        var = ctxr["vars"]
        ctx_flags += ctxr["flags"]
        notes += ctxr["notes"]
        recon = reconstruction(ex["lines"], var)
        _, end = periode_bornes(fval(ex, "audit.payroll_period"))
        rules_info = retrieve(reg, end, var)            # MODULE 4
        for k in rules_info["conflicts"]:
            ctx_flags.append(("HUM-007", f"Deux versions concurrentes de la règle {k}"))
        env = CalcEnv(ex["lines"], var, ctxr["param_meta"], reg.tables)   # MODULE 5
        for r in rules_info["applicable"]:              # MODULE 6
            controls.append(run_rule(r, env, cfg))
        controls += social_checks(env, var, ex["lines"], cfg)
        controls += mentions_check(env, var, reg.tables, ex["fields"])
        for u in rules_info["undetermined"]:
            r = u["rule"]
            controls.append(Control(r["control_id"], r["order"], r["name"], u["status"], rule_id=r["rule_id"],
                                    rule_version=r["version"], legal_reference=r.get("legal_source") or "—",
                                    finding=u["reason"], recommendation="Juriste référent : compléter la fiche de règle"))
        controls += required_families(rules_info["applicable"] + [u["rule"] for u in rules_info["undetermined"]], cfg,
                                      extra=[c.control_id for c in controls if c.rule_id == "CI-PAY-MENTIONS-001"])
        if not rules_info["applicable"]:
            stops.append("STOP 4 — Référentiel juridique indisponible pour la période auditée")
        # convention indispensable absente ?
        if any(c.status.startswith("NON CONTRÔLABLE") and "SMC" in c.finding for c in controls) and not ctxr["context"]["collective_agreement"]:
            ctx_flags.append(("HUM-009", "minimum catégoriel non déterminable sans convention collective"))
    controls += intrinsic(ex["lines"], var, recon, cfg)
    for c in controls:
        if c.confidence is None:
            confs = [e["confidence"] for e in c.evidence_fields if e.get("confidence") is not None]
            c.confidence = min(confs) if confs else ex["extraction_confidence"]

    # Net théorique (NET-005)
    comp = {}
    for c in controls:
        r = next((x for x in rules_info["applicable"] if x["rule_id"] == c.rule_id), None)
        if r and r.get("net_component") and c.expected_value is not None and c.status in RESULTATS_CONCLUSIFS:
            comp[r["net_component"]] = comp.get(r["net_component"], Decimal(0)) + Decimal(c.expected_value)
    needed = cfg.get("net_components", ["cnps_employee", "cmu_employee", "its"])
    if recon["gross_recalculated"] is not None and all(k in comp for k in needed):
        recon["net_theoretical"] = recon["gross_recalculated"] - sum(comp.values()) - recon["other_deductions"]
        recon["net_difference"] = (recon["net_reported"] - recon["net_theoretical"]) if recon["net_reported"] is not None else None
    else:
        recon["net_theoretical"] = None
        recon["net_difference"] = None
        recon["net_theoretical_status"] = MSG_NQ + " — composantes manquantes : " + ", ".join(k for k in needed if k not in comp)
    recon.update({f"{k}_theoretical": v for k, v in comp.items()})

    audit_ctx = req.get("additional_context", {}) or {}
    counts = score(controls, audit_ctx, cfg)            # MODULE 7
    ext_conf = ex["extraction_confidence"]
    ctx_conf = ctxr["context"]["context_confidence"] if ctxr else 0.5
    cscore, clabel = confidence(ext_conf, ctx_conf, controls, cfg)
    if ext_conf is not None and ext_conf < cfg.get("confidence_medium", 0.70):
        ctx_flags.append(("HUM-011", f"confiance d'extraction {ext_conf}"))
    g = gate(controls, ctx_flags, [s for s in stops], clabel, cfg)   # MODULE 8

    anomalies = [c for c in controls if c.status == NON_CONFORME]
    sc = cfg.get("compliance_score", {})
    w = sc.get("weights", {"P1": 4, "P2": 3, "P3": 2, "P4": 1})
    concl = [c for c in controls if c.status in RESULTATS_CONCLUSIFS]
    tot_w = sum(w.get(c.base_severity or "P4", 1) for c in concl)
    ok_w = sum(w.get(c.base_severity or "P4", 1) for c in concl if c.status == CONFORME)
    score_pct = round(100 * ok_w / tot_w, 1) if tot_w else None
    band = None
    if score_pct is not None:
        for lim, lab in sc.get("bands", [[95, "Conforme"], [80, "Conforme sous réserve"], [60, "Non-conformités significatives"], [0, "Risque social élevé"]]):
            if score_pct >= lim:
                band = lab
                break
    compliance = {"score": score_pct, "qualification": band, "controls_counted": len(concl),
                  "method": sc.get("method", "Indicateur méthodologique SOLEX (non légal)")}
    open_pts = [c for c in controls if c.status not in RESULTATS_CONCLUSIFS and c.status != NA]
    if blocking or any(s.startswith("STOP 4") for s in stops):
        status = "AUDIT INCOMPLET"
    elif g["required"]:
        status = "ESCALADE REQUISE"
    elif anomalies:
        status = "NON CONFORME"
    elif open_pts or any(c.reserves for c in controls if c.status == CONFORME):
        status = "CONFORME SOUS RÉSERVE"
    else:
        status = "CONFORME"

    # Synthèse financière (écarts mensuels constatés, aucune extrapolation)
    fin = {}
    for c in anomalies:
        if c.difference is None:
            continue
        key = c.impact_type or "autre"
        if key == "rappel_salarie":
            fin["rappel_potentiel_salarie"] = fin.get("rappel_potentiel_salarie", Decimal(0)) + max(Decimal(0), -Decimal(c.difference))
        elif key == "trop_percu":
            fin["trop_percu"] = fin.get("trop_percu", Decimal(0)) + max(Decimal(0), Decimal(c.difference))
        else:
            fin[f"ecart_{key}"] = fin.get(f"ecart_{key}", Decimal(0)) + Decimal(c.difference)
    fin["non_quantifiables"] = [c.control_name for c in anomalies if c.difference is None] + \
                               [c.control_name for c in open_pts if c.status == MSG_NQ]
    fin["note"] = "Écarts du mois audité uniquement — toute projection doit être étiquetée ESTIMATION."

    corrective = [{"anomaly": c.control_name, "correction": c.recommendation, "owner": "À désigner",
                   "priority": c.severity, "due_date": "À fixer par SOLEX",
                   "retroactive_regularisation": "À examiner par l'expert (périodes antérieures non auditées)"}
                  for c in sorted(anomalies, key=lambda x: (x.severity or "P9", x.order))]

    # MODULE 10 — chaîne de preuve
    docs = {d["name"]: d for d in m1["documents"]}
    evidence = []
    for c in anomalies:
        evidence.append({"control": c.control_name, "document": sorted({e.get("source") for e in c.evidence_fields if e.get("source")}) or list(docs)[:1],
                         "data": c.evidence_fields, "rule": {"rule_id": c.rule_id, "version": c.rule_version, "reference": c.legal_reference},
                         "calculation": c.trace, "finding": c.finding, "risk": {"severity": c.severity, **c.risk_variables},
                         "recommendation": c.recommendation})
    used_rules = [r for r in rules_info["applicable"] if any(c.rule_id == r["rule_id"] and c.status != NA for c in controls)]
    sources = [{"rule_id": r["rule_id"], "version": r["version"], "legal_source": r.get("legal_source"), "article": r.get("article"),
                "authority": r.get("authority"), "effective_from": r.get("effective_from"), "effective_to": r.get("effective_to"),
                "source_url": r.get("source_url"), "last_verified": r.get("last_verified")} for r in used_rules]
    if ctxr:
        for pid, pm in ctxr["param_meta"].items():
            if any(pid in json.dumps(c.trace, default=str) for c in controls):
                sources.append({"parameter": pid, "value": pm["value"], "legal_source": pm.get("legal_source"),
                                "article": pm.get("article"), "effective_from": pm.get("effective_from"),
                                "effective_to": pm.get("effective_to"), "source_url": pm.get("source_url")})

    emp = {k.split(".", 1)[1]: f.value for k, f in ex["fields"].items() if k.startswith("employee.") and f.present
           and k.split(".", 1)[1] in ("employee_id", "position", "job", "classification", "category", "grade", "hire_date", "contract_type")}
    result = {
        "audit_id": audit_id, "status": status, "confidence": clabel, "confidence_score": cscore,
        "report_status": "PROVISOIRE — À VALIDER PAR UN EXPERT SOLEX", "compliance_score": compliance,
        "employer": {k.split(".", 1)[1]: f.value for k, f in ex["fields"].items() if k.startswith("employer.") and f.present
                     and k.split(".", 1)[1] in ("legal_name", "sector", "collective_agreement", "location")},
        "employee": emp, "payroll_period": fval(ex, "audit.payroll_period"),
        "applicable_context": ctxr["context"] if ctxr else {}, "stops": stops, "notes": notes,
        "controls": [_control_dict(c) for c in sorted(controls, key=lambda x: (x.order, x.control_id))],
        "payroll_reconstruction": recon, "financial_summary": fin, "risk_summary": counts,
        "corrective_actions": corrective, "human_escalations": g["escalations"], "escalation_formula": g["formula"],
        "sources": sources, "evidence": evidence,
        "inputs": {"documents": m1["documents"], "fields": [f.as_dict() for f in ex["fields"].values()],
                   "lines": ex["lines"], "missing_data": ex["missing_data"], "extraction_confidence": ext_conf},
        "rules_excluded": rules_info["excluded"], "registry_rejected": reg.rejected,
        "audit_log": {"audit_id": audit_id, "agent_version": AGENT_VERSION,
                      "ruleset_version": cfg.get("ruleset_version", reg.version()), "audit_date": started,
                      "payroll_period": fval(ex, "audit.payroll_period"),
                      "documents_used": [d["name"] for d in m1["documents"]],
                      "rules_applied": [f"{r['rule_id']} v{r['version']}" for r in used_rules],
                      "findings": len(anomalies), "risk_scores": counts, "human_interventions": [],
                      "final_status": status},
    }
    return json.loads(json.dumps(result, default=_jsonable))


def persist(result: dict, out_dir: Path, journal: Path | None, escalades: Path | None):
    from .report import to_docx, to_markdown
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "resultat.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "rapport.md").write_text(to_markdown(result), encoding="utf-8")
    to_docx(result, out_dir / "rapport.docx")
    if escalades and result["human_escalations"]:
        result["audit_log"]["escalation_files"] = write_queue(result["human_escalations"], result["audit_id"], escalades)
    if journal:
        journal.parent.mkdir(parents=True, exist_ok=True)
        with journal.open("a", encoding="utf-8") as f:
            f.write(json.dumps(result["audit_log"], ensure_ascii=False) + "\n")


__all__ = ["audit", "persist", "load_config", "ESCALADE_TXT", "reference"]
