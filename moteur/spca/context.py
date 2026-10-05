"""Module 3 — Context & Applicability Resolver.

Détermine, AVANT tout calcul, le contexte juridique du bulletin : juridiction, date de référence,
régime de durée du travail, convention, SMIG et minimum catégoriel applicables, ancienneté.
Aucune valeur juridique n'est codée ici : tout vient des paramètres et tables validés du référentiel.
"""
from __future__ import annotations

import datetime as dt
import re
from decimal import Decimal

from .common import D, norm_txt, periode_bornes
from .intake import fval

REGIMES = {"NON AGRICOLE": "MONTHLY_HOURS_NON_AGRICOLE", "NON_AGRICOLE": "MONTHLY_HOURS_NON_AGRICOLE",
           "AGRICOLE": "MONTHLY_HOURS_AGRICOLE"}


def _months_between(a: dt.date, b: dt.date) -> int:
    m = (b.year - a.year) * 12 + (b.month - a.month)
    if b.day < a.day:
        m -= 1
    return max(m, 0)


def resolve(ex: dict, reg, cfg: dict) -> dict:
    per = fval(ex, "audit.payroll_period")
    start, end = periode_bornes(per)
    params, pmeta, pconf = reg.params_at(end)
    flags, notes, used_params = [], [], {}
    penalty = 0.0

    ctx = {"jurisdiction": "Côte d'Ivoire", "payroll_period": per, "legal_reference_date": end.isoformat(),
           "period_start": start.isoformat(), "period_end": end.isoformat()}
    var = dict(params)
    var.update({"month": end.month, "year": end.year, "PERIOD_DAYS": (end - start).days + 1})

    # Convention / secteur / catégorie
    conv = fval(ex, "employer.collective_agreement")
    ctx["collective_agreement"] = conv
    ctx["collective_agreement_status"] = "DÉCLARÉE — applicabilité à vérifier" if conv else "NON RENSEIGNÉE"
    if not conv:
        penalty += 0.1
    sector = fval(ex, "employer.sector")
    cat = fval(ex, "employee.category")
    var["sector"] = norm_txt(sector) or None
    var["category"] = norm_txt(cat) or None
    m = re.search(r"\d+", str(cat or ""))
    var["category_num"] = int(m.group()) if m else None
    loc = fval(ex, "employee.work_location") or fval(ex, "employer.location")
    var["locality"] = norm_txt(loc) or None
    var["locality_known"] = bool(var["locality"])

    # Régime de durée du travail (TIM-001)
    regime = fval(ex, "employee.working_time_regime")
    ctx["working_time_regime"] = regime
    hp = REGIMES.get(norm_txt(regime).replace("-", " ")) if regime else None
    if regime and hp and hp in params:
        var["MONTHLY_HOURS"] = params[hp]
        used_params["MONTHLY_HOURS"] = pmeta[hp]
    else:
        if not regime:
            penalty += 0.1
        notes.append("Durée mensuelle de référence non déterminée (régime ou paramètre manquant)")

    # SMIG
    if "SMIG_M" in params:
        used_params["SMIG_M"] = pmeta["SMIG_M"]
        ref_h = params.get("MONTHLY_HOURS_NON_AGRICOLE")
        if ref_h:
            var["SMIG_H"] = (Decimal(str(params["SMIG_M"])) / Decimal(str(ref_h))).quantize(Decimal("0.01"))
    ctx["minimum_wage_rule"] = (f"SMIG {params['SMIG_M']} FCFA/mois — {pmeta['SMIG_M'].get('legal_source')}"
                                if "SMIG_M" in params else "SMIG non paramétré pour la période")

    # Minimum catégoriel (table SMC) — secteur → catégorie → groupe professionnel → variante → barème en vigueur
    ctx["categorical_minimum"] = None
    smc_tab = reg.tables.get("smc")
    _jg_raw = fval(ex, "employee.job_group")
    var["job_group"] = norm_txt(_jg_raw) or None
    var["smc_variant"] = norm_txt(fval(ex, "employee.smc_variant")) or None
    if smc_tab and var["sector"] and var["category"]:
        catn = var["category"].replace(" ", "")
        labels = {norm_txt(k): norm_txt(k) for k in (smc_tab.get("sectors") or {})}
        labels.update({norm_txt(v): norm_txt(k) for k, v in (smc_tab.get("sectors") or {}).items()})
        sect = labels.get(var["sector"], var["sector"])
        rows = [r for r in smc_tab.get("rows", [])
                if norm_txt(r.get("sector")) == sect and norm_txt(r.get("category")).replace(" ", "") == catn
                and dt.date.fromisoformat(r["effective_from"]) <= end
                and (not r.get("effective_to") or end <= dt.date.fromisoformat(r["effective_to"]))]
        if var["job_group"]:
            def _toks(g):
                return {norm_txt(x) for x in re.split(r"[_\s,/]+", str(g)) if x}
            jg = _toks(_jg_raw)
            rows = [r for r in rows if not r.get("job_group") or "TOUS" in _toks(r["job_group"])
                    or jg <= _toks(r["job_group"])]
        if var["smc_variant"]:
            rows = [r for r in rows if not r.get("variant") or norm_txt(r["variant"]) == var["smc_variant"]]
        def mval(r):
            v = D(r.get("new_smc") if r.get("new_smc") is not None else r.get("smc_monthly"))
            if v is None and D(r.get("base_smc")) is not None and D(r.get("revaluation_rate")) is not None:
                v = (D(r["base_smc"]) * (1 + D(r["revaluation_rate"]))).quantize(Decimal("1"))
            return v
        distinct = {(str(mval(r)), str(r.get("smc_hourly")), str(r.get("smc_daily"))) for r in rows}
        if len(distinct) > 1:
            opts = "; ".join(f"{r.get('job_group') or '—'}/{r.get('variant') or '—'} = {r.get('smc_monthly') or r.get('smc_hourly') or r.get('smc_daily')}"
                             for r in rows[:6])
            flags.append(("HUM-007", f"Plusieurs minima catégoriels possibles pour la catégorie {var['category']} ({opts}) — "
                                     "préciser employee.job_group et/ou employee.smc_variant"))
            notes.append("Minimum catégoriel ambigu : groupe professionnel ou variante à préciser")
        elif rows:
            r = sorted(rows, key=lambda x: x["effective_from"])[-1]
            smc = mval(r)
            basis = None
            if smc is None and r.get("smc_hourly") is not None and var.get("MONTHLY_HOURS"):
                smc = (D(r["smc_hourly"]) * Decimal(str(var["MONTHLY_HOURS"]))).quantize(Decimal("1"))
                basis = f"taux horaire {r['smc_hourly']} × {var['MONTHLY_HOURS']} h"
            if smc is not None:
                var["SMC"] = smc
                ctx["categorical_minimum"] = {"value": smc, "basis": basis,
                                              **{k: r.get(k) for k in ("sector", "job_group", "variant", "category", "category_label",
                                                                       "smc_hourly", "legal_source", "effective_from", "note")}}
                var["SMC_H"] = (D(r["smc_hourly"]) if r.get("smc_hourly") is not None else
                                ((smc / Decimal(str(var["MONTHLY_HOURS"]))).quantize(Decimal("0.01")) if var.get("MONTHLY_HOURS") else None))
            elif r.get("smc_daily") is not None:
                var["SMC_D"] = D(r["smc_daily"])
                notes.append(f"Minimum catégoriel journalier ({r['smc_daily']} F/jour) : comparaison mensuelle impossible sans nombre de jours travaillés")

    # Ancienneté (SAL-009/010)
    hire = fval(ex, "employee.hire_date")
    if hire:
        h = dt.date.fromisoformat(str(hire))
        mo = _months_between(h, end)
        var.update({"ANC": mo // 12, "ANC_MONTHS": mo, "ANC_DEC": Decimal(mo) / 12})
        y0 = max(h, dt.date(end.year, 1, 1))
        var["SERVICE_MONTHS_YEAR"] = min(12, _months_between(y0, end + dt.timedelta(days=1)))  # mois complets
    else:
        penalty += 0.1

    # Temps de travail, situation familiale, divers
    ratio = D(fval(ex, "employee.working_time_ratio"))
    tt = norm_txt(fval(ex, "employee.time_type"))
    var["full_time"] = (ratio == 100) if ratio is not None else ({"TEMPS PLEIN": True, "TEMPS PARTIEL": False}.get(tt))
    fam = {k.split(".")[-1]: f.value for k, f in ex["fields"].items() if k.startswith("employee.family_status.") and f.present}
    var["married"] = fam.get("married")
    var["children"] = fam.get("children")
    var["dependents"] = fam.get("dependents")
    var["cmu_spouse_covered"] = fam.get("cmu_spouse_covered")
    var["cmu_children_covered"] = D(fam.get("cmu_children_covered"))
    # Situation fiscale (CGI art. 120 2° — situation au 1er janvier, ou au 31 décembre si augmentation des charges)
    var["tax_status"] = norm_txt(fam.get("tax_status")) or None
    var["tax_children"] = D(fam.get("tax_children"))
    var["tax_children_infirm"] = D(fam.get("tax_children_infirm") if fam.get("tax_children_infirm") is not None else 0)
    var["tax_special_half"] = bool(fam.get("tax_special_half"))
    var["expatriate"] = fval(ex, "employee.expatriate")
    var["apprenticeship_months"] = D(fval(ex, "employee.apprenticeship_months"))
    var["distance_km"] = fval(ex, "employee.distance_km")
    var["pay_frequency"] = norm_txt(fval(ex, "employee.pay_frequency")) or None
    for k in ("base_salary", "gross_salary", "net_salary", "social_base", "tax_base"):
        var[k] = D(fval(ex, f"payroll.{k}"))
    var["contract_base_salary"] = D(fval(ex, "contract_data.base_salary"))
    for k, f in ex["fields"].items():
        if k.startswith(("termination.", "leave_data.", "working_time.", "mission.")) and f.present:
            v = f.value if isinstance(f.value, bool) else (norm_txt(f.value) if isinstance(f.value, str) else D(f.value))
            var[k.replace(".", "_")] = v
    if any(k.startswith("leave_data_") for k in var):   # CT art. 25.2 (ord. 2021-902) — suppléments non déclarés = 0 (réserve de la règle)
        for k, d0 in (("leave_data_children_under_21", Decimal(0)), ("leave_data_children_over_18_from_4th", Decimal(0)),
                      ("leave_data_work_medal", False), ("leave_data_resident_guard", False)):
            var.setdefault(k, d0)
    # Prescription biennale des salaires (CT art. 33.5) : ancienneté de la période à la date d'audit
    ad = fval(ex, "audit.audit_date")
    try:
        ad = dt.date.fromisoformat(str(ad)[:10]) if ad else dt.date.today()
    except ValueError:
        ad = dt.date.today()
    var["months_since_period"] = (ad.year - end.year) * 12 + (ad.month - end.month) - (1 if ad.day < end.day else 0)
    var["timesheet_provided"] = bool((ex.get("documents_index") or {}).get("timesheets"))
    var["atmp_rate"] = D(fval(ex, "employer.atmp_rate"))
    var["centrale_des_bilans"] = fval(ex, "employer.centrale_des_bilans")
    var["mentions"] = {k.split(".", 1)[1]: f.value for k, f in ex["fields"].items()
                       if k.startswith("payslip_mentions.") and f.present}
    special = [s for s in (fval(ex, "employee.special_situation"),) if s]
    ctx["special_regime"] = special
    if special:
        flags.append(("HUM-010", f"Situation particulière déclarée : {special[0]} — régime à confirmer"))

    for pid in pconf:
        flags.append(("HUM-007", f"Paramètre {pid} : deux valeurs concurrentes à la même date"))
    score = max(0.5, 1.0 - penalty)
    ctx["context_confidence"] = round(score, 2)
    ctx["parameters_in_force"] = {k: {"value": v["value"], "source": v.get("legal_source"), "from": v.get("effective_from")}
                                  for k, v in pmeta.items()}
    return {"context": ctx, "vars": var, "flags": flags, "notes": notes, "param_meta": pmeta}
