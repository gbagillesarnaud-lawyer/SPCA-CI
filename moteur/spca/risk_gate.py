"""Module 7 — Risk Scoring Engine  &  Module 8 — Human Gate & Escalation."""
from __future__ import annotations

import datetime as dt
import json
from decimal import Decimal
from pathlib import Path

from .common import ESCALADE_TXT, NON_CONFORME, RESULTATS_CONCLUSIFS

# ------------------------------------------------------------------ MODULE 7
LEVELS = ["P1", "P2", "P3", "P4"]


def _up(level: str) -> str:
    i = LEVELS.index(level)
    return LEVELS[max(0, i - 1)]


def score(controls: list, audit_ctx: dict, cfg: dict) -> dict:
    """Criticité finale : gravité de l'obligation (règle) ajustée par exposition, récurrence, population,
    rétroactivité, intention et confiance — jamais par le seul montant (§8 architecture)."""
    rc = cfg.get("risk", {})
    seuil_fin = Decimal(str(rc.get("financial_impact_upgrade_fcfa"))) if rc.get("financial_impact_upgrade_fcfa") else None
    workers = int(audit_ctx.get("number_of_workers_affected") or 1)
    recurrence = bool(audit_ctx.get("recurrence"))
    retro = bool(audit_ctx.get("retroactivity"))
    for c in controls:
        if c.status != NON_CONFORME:
            continue
        base = c.base_severity or "P3"
        impact = abs(Decimal(c.difference)) if c.difference is not None else None
        v = {"severity": base, "financial_impact": str(impact) if impact is not None else "non quantifiable",
             "legal_exposure": c.control_id in ("C01", "C03", "C08"), "social_exposure": c.control_id in ("C05", "C06"),
             "tax_exposure": c.control_id == "C07", "number_of_workers_affected": workers, "recurrence": recurrence,
             "retroactivity": retro, "intent_indicator": "HUM-001" in c.human_flags, "data_confidence": c.confidence}
        final, why = base, []
        if seuil_fin is not None and impact is not None and impact >= seuil_fin and final != "P1":
            final = _up(final); why.append(f"impact ≥ {seuil_fin} FCFA")
        if (workers > 1 or recurrence) and final != "P1":
            final = _up(final); why.append("récurrence / pluralité de salariés")
        if v["intent_indicator"] or "HUM-002" in c.human_flags:
            final = "P1"; why.append("indice d'intention / travail non déclaré")
        v["adjustments"] = why or ["aucun ajustement"]
        c.severity, c.risk_variables = final, v
    counts = {k: sum(1 for c in controls if c.severity == k and c.status == NON_CONFORME) for k in LEVELS}
    return counts


# ------------------------------------------------------------------ MODULE 8
HUM = {
    "HUM-001": ("Indice de fraude — " + "INDICE NÉCESSITANT INVESTIGATION", "Juriste droit social", "P1"),
    "HUM-002": ("Travailleur potentiellement non déclaré", "Expert CNPS", "P1"),
    "HUM-003": ("Conflit documentaire majeur (bulletin / contrat)", "Juriste droit social", "P2"),
    "HUM-004": ("Retenue importante ou sensible sans fondement identifiable", "Juriste droit social", "P2"),
    "HUM-005": ("Risque systémique", "Direction juridique SOLEX", "P1"),
    "HUM-006": ("Exposition rétroactive élevée", "Spécialiste paie", "P2"),
    "HUM-007": ("Conflit de sources juridiques", "Direction juridique SOLEX", "P2"),
    "HUM-008": ("Jurisprudence incertaine", "Avocat", "P2"),
    "HUM-009": ("Convention collective indispensable indisponible", "Juriste droit social", "P2"),
    "HUM-010": ("Interprétation juridique complexe", "Juriste droit social", "P2"),
    "HUM-011": ("Niveau de confiance faible", "Spécialiste paie", "P2"),
    "HUM-012": ("Qualification fiscale d'une composante à valider (exonération conditionnelle, rupture, dommages-intérêts)", "Expert fiscal", "P2"),
    "P1": ("Anomalie critique P1", "Juriste droit social", "P1"),
    "P2": ("Anomalie majeure P2 — validation humaine avant correction", "Spécialiste paie", "P2"),
    "STOP": ("Arrêt de l'exécution automatique", "Spécialiste paie", "P2"),
}
BLOCKED = {"P1": ["publication du rapport", "transmission client", "correction de paie"],
           "P2": ["publication du rapport", "correction de paie"]}


def gate(controls: list, ctx_flags: list, stops: list, confidence_label: str, cfg: dict) -> dict:
    esc = []

    def add(code, reason_detail, control=None):
        lib, expert, prio = HUM[code]
        esc.append({"escalation_required": True, "escalation_type": code, "reason": f"{lib} : {reason_detail}" if reason_detail else lib,
                    "priority": prio, "recommended_expert": expert, "control": control,
                    "blocked_actions": BLOCKED.get(prio, []), "status": "EN ATTENTE", "decision": None,
                    "expert_assigned": None, "decided_on": None})

    for code, detail in ctx_flags:
        add(code, detail)
    for c in controls:
        for f in dict.fromkeys(c.human_flags):
            add(f, c.control_name, c.control_name)
        if c.status == NON_CONFORME and c.severity == "P1" and cfg.get("human_gate_p1", True):
            add("P1", c.control_name, c.control_name)
        elif c.status == NON_CONFORME and c.severity == "P2" and cfg.get("human_gate_p2", True):
            add("P2", c.control_name, c.control_name)
    for s in stops:
        add("STOP", s)
    if confidence_label == "FAIBLE":
        add("HUM-011", "confiance globale FAIBLE")
    return {"escalations": esc, "required": bool(esc), "formula": ESCALADE_TXT if esc else None}


def write_queue(escalations: list, audit_id: str, folder: Path):
    folder.mkdir(parents=True, exist_ok=True)
    paths = []
    for i, e in enumerate(escalations, 1):
        p = folder / f"{audit_id}-{i:02d}.json"
        if not p.exists():  # jamais d'écrasement : piste d'audit
            p.write_text(json.dumps({**e, "audit_id": audit_id, "created": dt.datetime.now().isoformat(timespec="seconds")},
                                    ensure_ascii=False, indent=2), encoding="utf-8")
        paths.append(str(p))
    return paths


def confidence(extraction: float | None, context: float, controls: list, cfg: dict) -> tuple[float, str]:
    """Score global (0–1) et catégorie ÉLEVÉ / MOYEN / FAIBLE (seuils CFG-007 / CFG-008)."""
    relevant = [c for c in controls if c.status != "NON_APPLICABLE"]
    nc = sum(1 for c in relevant if c.status not in RESULTATS_CONCLUSIFS)
    ratio = nc / len(relevant) if relevant else 1.0
    base = min(extraction if extraction is not None else 0.8, context)
    s = round(base * (1 - 0.5 * ratio), 2)
    hi, mid = cfg.get("confidence_high", 0.90), cfg.get("confidence_medium", 0.70)
    return s, ("ÉLEVÉ" if s >= hi else "MOYEN" if s >= mid else "FAIBLE")

