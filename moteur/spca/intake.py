"""Module 1 — Document Intake  &  Module 2 — Payroll Data Extractor (normalisation)."""
from __future__ import annotations

import hashlib
import uuid
from pathlib import Path

from .common import D, Field, norm_txt

# ------------------------------------------------------------------ MODULE 1
PAYSLIP_KEYS = ("payslip",)


def intake(req: dict) -> dict:
    """Identifie les documents, contrôle lisibilité/doublons, applique la matrice des données minimales (§26)."""
    audit = req.get("audit", {})
    docs_in = req.get("documents", {}) or {}
    docs, seen, stops, partial, notes = [], {}, [], [], []
    for dtype, items in docs_in.items():
        for d in items or []:
            d = d if isinstance(d, dict) else {"path": d}
            p = Path(d.get("path", "")) if d.get("path") else None
            h = None
            exists = bool(p and p.exists())
            if exists:
                h = hashlib.sha256(p.read_bytes()).hexdigest()
            doc = {
                "document_id": (h[:16] if h else d.get("document_id") or uuid.uuid4().hex[:16]),
                "document_type": dtype, "name": d.get("name") or (p.name if p else None),
                "path": str(p) if p else None, "sha256": h, "file_exists": exists,
                "file_quality": d.get("quality", "non évaluée"),
                "employer_id": req.get("employer", {}).get("legal_name"),
                "employee_id": req.get("employee", {}).get("employee_id"),
                "payroll_period": d.get("period") or audit.get("payroll_period"),
                "processing_status": "RECEIVED",
            }
            if h and h in seen:
                doc["processing_status"] = "DUPLICATE"
                notes.append(f"Doublon : {doc['name']} identique à {seen[h]}")
            elif h:
                seen[h] = doc["name"]
            if doc["file_quality"] in ("illisible", "unreadable"):
                doc["processing_status"] = "UNREADABLE"
            docs.append(doc)

    payslips = [d for d in docs if d["document_type"] == "payslip" and d["processing_status"] != "DUPLICATE"]
    if not payslips:
        stops.append("STOP 1 — Bulletin de salaire non fourni (EVD-001)")
    elif all(d["processing_status"] == "UNREADABLE" for d in payslips):
        stops.append("STOP 1 — Bulletin illisible")
    if not audit.get("payroll_period"):
        stops.append("STOP 3 — Période de paie indéterminée (AUD-004)")
    if norm_txt(audit.get("jurisdiction")) not in {"CI", "CIV", "COTE DIVOIRE"}:
        stops.append("STOP 2 — Juridiction inconnue ou non ivoirienne (AUD-005)")
    return {"documents": docs, "stops": stops, "partial": partial, "notes": notes}


# ------------------------------------------------------------------ MODULE 2
def to_field(name, raw, default_source=None) -> Field:
    if isinstance(raw, dict) and "value" in raw:
        f = Field(name=name, value=raw.get("value"), source=raw.get("source", default_source),
                  page=raw.get("page"), zone=raw.get("zone") or raw.get("line"),
                  confidence=raw.get("confidence"), status=raw.get("status") or "UNVERIFIED")
    else:
        f = Field(name=name, value=raw, source=default_source, status="UNVERIFIED")
    if f.value in (None, "", []):
        f.value, f.status = None, "MISSING" if f.status != "NOT_APPLICABLE" else f.status
    return f


# Tableau d'entrée -> nature comptable
ARRAY_NATURE = {
    "earnings": "gain", "bonuses": "gain", "allowances": "gain", "overtime": "gain", "leave": "gain",
    "benefits_in_kind": "avantage_nature", "absences": "autre_retenue", "deductions": "autre_retenue",
    "advances": "autre_retenue", "contributions": "retenue_salariale", "taxes": "retenue_fiscale",
}


def extract(req: dict) -> dict:
    """Normalise l'audit_request (§29) en champs à 5 dimensions + lignes de paie typées."""
    fields: dict[str, Field] = {}
    payslip_src = None
    for d in (req.get("documents", {}) or {}).get("payslip", []) or []:
        payslip_src = (d.get("name") or d.get("path")) if isinstance(d, dict) else str(d)
        break

    def add(prefix, obj):
        for k, v in (obj or {}).items():
            if isinstance(v, list) and prefix == "payroll":
                continue
            if isinstance(v, dict) and "value" not in v:
                add(f"{prefix}.{k}", v)
                continue
            fields[f"{prefix}.{k}"] = to_field(f"{prefix}.{k}", v, payslip_src)

    for sec in ("audit", "employer", "employee", "payroll", "working_time", "contract_data", "termination",
                "leave_data", "mission", "payslip_mentions", "additional_context"):
        add(sec, req.get(sec))

    lines = []
    payroll = req.get("payroll", {}) or {}
    for arr, nature in ARRAY_NATURE.items():
        for i, it in enumerate(payroll.get(arr, []) or []):
            amt = to_field(f"{arr}[{i}]", it.get("amount") if "amount" in it else it.get("value"), payslip_src)
            lines.append({
                "type": it.get("type") or arr, "label": it.get("label", it.get("type", arr)), "nature": it.get("nature", nature),
                "array": arr, "amount": D(amt.value), "quantity": D(it.get("quantity")), "base": D(it.get("base")),
                "rate": D(it.get("rate")), "employer_rate": D(it.get("employer_rate")), "employer_amount": D(it.get("employer_amount")),
                "source": it.get("source", payslip_src), "page": it.get("page"), "zone": it.get("line") or it.get("zone"),
                "confidence": it.get("confidence"), "status": it.get("status", "UNVERIFIED"),
                "justification": it.get("justification_doc"),
                "employee_contribution": D(it.get("employee_contribution")),
            })
    # scalaires de synthèse (§29) sans ligne détaillée correspondante
    for key, typ, nat in (("cnps_employee", "cnps_employee_total", "retenue_salariale"),
                          ("cmu", "cmu_employee", "retenue_salariale"), ("its", "its", "retenue_fiscale")):
        f = fields.get(f"payroll.{key}")
        if f and f.present and not any(l["type"] == typ for l in lines):
            lines.append({"type": typ, "label": key.upper(), "nature": nat, "array": "payroll", "amount": D(f.value),
                          "quantity": None, "base": None, "rate": None, "employer_rate": None, "employer_amount": None, "source": f.source,
                          "page": f.page, "zone": f.zone, "confidence": f.confidence, "status": f.status, "justification": None,
                          "employee_contribution": None})

    if not fields.get("employee.employee_id") or not fields["employee.employee_id"].present:
        fields["employee.employee_id"] = Field("employee.employee_id", "SAL-" + uuid.uuid4().hex[:8].upper(),
                                               "généré (SAL-001)", status="CALCULATED", confidence=1.0)

    missing = [n for n, f in fields.items() if f.status == "MISSING"]
    confs = [f.confidence for f in fields.values() if f.present and f.confidence is not None]
    confs += [l["confidence"] for l in lines if l["confidence"] is not None]
    docs_idx = {k: len(v or []) for k, v in (req.get("documents", {}) or {}).items()}
    return {"fields": fields, "lines": lines, "missing_data": missing, "documents_index": docs_idx,
            "extraction_confidence": min(confs) if confs else None}


def fval(ex: dict, name: str):
    f = ex["fields"].get(name)
    return f.value if f and f.present else None
