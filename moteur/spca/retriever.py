"""Module 4 — Legal Rule Retriever.

Sélectionne les règles du registre applicables au dossier : statut validé, juridiction, période
(date d'effet vérifiée AVANT tout calcul), secteur, catégorie et présence d'une source juridique.
"""
from __future__ import annotations

import datetime as dt

from .common import MSG_REGLE, MSG_SOURCE, norm_txt
from .registry import in_force


def _match(scope, value) -> bool | None:
    if scope in (None, "*", [], ["*"]):
        return True
    if value is None:
        return None
    scope = [scope] if isinstance(scope, str) else scope
    return norm_txt(value) in {norm_txt(s) for s in scope}


def retrieve(reg, date: dt.date, var: dict) -> dict:
    applicable, excluded, undetermined = [], [], []
    for r in reg.rules:
        rid = f"{r['rule_id']} v{r['version']}"
        if norm_txt(r.get("jurisdiction", "CI")) not in ("CI", "COTE DIVOIRE"):
            excluded.append(f"{rid} : juridiction {r.get('jurisdiction')}")
            continue
        f = in_force(r, date)
        if f is None:
            undetermined.append({"rule": r, "status": MSG_REGLE, "reason": "date d'effet non renseignée dans le registre"})
            continue
        if not f:
            excluded.append(f"{rid} : hors période de validité ({r.get('effective_from')} → {r.get('effective_to') or 'en vigueur'})")
            continue
        if not r.get("legal_source"):
            undetermined.append({"rule": r, "status": MSG_SOURCE, "reason": "aucune source juridique renseignée"})
            continue
        s = _match(r.get("sector"), var.get("sector"))
        c = _match(r.get("employee_category"), var.get("category"))
        if s is False or c is False:
            excluded.append(f"{rid} : hors champ (secteur/catégorie)")
            continue
        if s is None or c is None:
            undetermined.append({"rule": r, "status": "NON CONTRÔLABLE — INFORMATION MANQUANTE",
                                 "reason": "secteur ou catégorie du salarié non renseigné(e) — champ d'application invérifiable"})
            continue
        applicable.append(r)
    # une seule version par rule_id (la plus récente en vigueur)
    best = {}
    for r in applicable:
        k = r["rule_id"]
        if k not in best or r["effective_from"] > best[k]["effective_from"]:
            best[k] = r
    conflicts = [k for k in best if sum(1 for r in applicable if r["rule_id"] == k and r["effective_from"] == best[k]["effective_from"]) > 1]
    return {"applicable": sorted(best.values(), key=lambda r: (r["order"], r["rule_id"])),
            "excluded": excluded, "undetermined": undetermined, "conflicts": conflicts}


def reference(r: dict) -> str:
    parts = [f"{r['rule_id']} v{r['version']}", r.get("legal_source")]
    if r.get("article"):
        parts.append(f"art. {r['article']}")
    ref = " — ".join(p for p in parts if p)
    ref += f" (en vigueur depuis {r.get('effective_from')}"
    ref += f" jusqu'au {r['effective_to']})" if r.get("effective_to") else ")"
    return ref
