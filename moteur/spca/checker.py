"""Module 6 — Compliance Checker.

Pour chaque règle applicable (ordre XXXII du Rules Registry) : applicabilité → prérequis →
valeur attendue (formule) → valeur constatée → comparaison → constat. Plus les contrôles
intrinsèques ne nécessitant aucun texte (arithmétique du bulletin, cohérence contrat, fondement des retenues).
"""
from __future__ import annotations

from decimal import Decimal

from .calc import CalcEnv
from .common import (CONFORME, MSG_INFO, MSG_NQ, MSG_REGLE, NA, NON_CONFORME, Control, D, fmt)
from .expr import MissingInput, RuleError
from .retriever import reference

LINE_REF = "Contrôle arithmétique interne (cohérence du bulletin)"


def _missing_label(name: str) -> str:
    return name.replace("rubrique:", "rubrique ").replace("quantité:", "quantité ").replace("part_patronale:", "part patronale ")


def _line_evidence(lines, types):
    types = [types] if isinstance(types, str) else types
    return [{"field": l["type"], "value": fmt(l["amount"]), "source": l["source"], "page": l["page"],
             "zone": l["zone"], "confidence": l["confidence"], "status": l["status"]}
            for l in lines if l["type"] in types]


def run_rule(r: dict, env: CalcEnv, cfg: dict) -> Control:
    c = Control(control_id=r["control_id"], order=r["order"], control_name=r["name"], status=NA,
                rule_id=r["rule_id"], rule_version=r["version"], legal_reference=reference(r),
                base_severity=r.get("severity_if_breach", "P2"), impact_type=r.get("impact_type"),
                error_code=r.get("error_code"))
    tol = D(r.get("tolerance", cfg.get("tolerance_fcfa", 1)))
    env.reserves = []
    env.touched = set()
    try:
        return _run_rule(r, env, cfg, c, tol)
    finally:
        c.evidence_fields = _line_evidence(env.lines, sorted(env.touched))


def _run_rule(r, env, cfg, c, tol):
    # 1. applicabilité
    try:
        ok, _ = env.run(r.get("applies_when", "True"))
    except MissingInput as e:
        if r.get("required"):
            c.status, c.finding = MSG_INFO, f"Applicabilité invérifiable : {_missing_label(e.name)} manquant(e)"
        else:
            c.finding = f"Non applicable en l'état (donnée d'applicabilité absente : {_missing_label(e.name)})"
        return c
    if not ok:
        c.finding = "Règle non applicable à la situation du salarié"
        return c
    # 2. prérequis
    if r.get("prerequisite"):
        try:
            pre, _ = env.run(r["prerequisite"])
        except MissingInput as e:
            c.status, c.finding = MSG_INFO, f"Prérequis invérifiable : {_missing_label(e.name)} manquant(e)"
            return c
        if not pre:
            c.status = MSG_NQ
            c.finding = r.get("prerequisite_message", "Prérequis de la règle non rempli")
            if r.get("prerequisite_flag"):
                c.human_flags.append(r["prerequisite_flag"])
            return c
    # 3. valeur attendue
    try:
        exp, tr = env.run(r["expected"], r.get("rounding", "unite"))
        c.expected_value = exp
        c.trace.append({"step": "valeur attendue", **tr})
    except MissingInput as e:
        c.status, c.finding = MSG_INFO, f"Donnée nécessaire au calcul absente : {_missing_label(e.name)}"
        return c
    except (RuleError, ArithmeticError, TypeError) as e:
        c.status, c.finding = MSG_NQ, f"Formule non évaluable : {e}"
        return c
    # 4. valeur constatée
    obs_expr = r.get("observed")
    if obs_expr:
        try:
            obs, tro = env.run(obs_expr)
            c.trace.append({"step": "valeur constatée", **tro})
        except MissingInput as e:
            if r.get("absent_as_zero"):
                obs = Decimal(0)
                c.trace.append({"step": "valeur constatée", "formula": obs_expr, "result": "0 (rubrique absente du bulletin)"})
            else:
                c.status, c.finding = MSG_INFO, f"Valeur constatée absente : {_missing_label(e.name)}"
                c.reserves += env.reserves
                return c
        c.observed_value = obs
    c.reserves += env.reserves + ([r["reserve"]] if r.get("reserve") else [])
    # 5. comparaison
    mode = r.get("compare", "equal")
    if not obs_expr:  # contrôle booléen (expected = condition de conformité)
        c.status = CONFORME if exp else NON_CONFORME
    else:
        diff = Decimal(obs) - Decimal(exp)
        c.difference = diff
        if mode == "at_least":
            breach = diff < -tol
        elif mode == "at_most":
            breach = diff > tol
        else:
            breach = abs(diff) > tol
        c.status = NON_CONFORME if breach else CONFORME
        if breach:
            c.favorable_to = "employeur" if diff < 0 else "salarie"
            if r.get("impact_type") in ("rappel_salarie",) and diff > 0:
                c.impact_type = "trop_percu"
    c.severity = c.base_severity if c.status == NON_CONFORME else None
    c.finding = (r.get("finding_breach") if c.status == NON_CONFORME else r.get("finding_ok")) or (
        f"Constaté {fmt(c.observed_value)} / attendu {fmt(c.expected_value)}" if obs_expr else "")
    c.recommendation = r.get("recommendation", "Régulariser selon la règle citée") if c.status == NON_CONFORME else "—"
    for f in r.get("human_flags_if_breach", []) if c.status == NON_CONFORME else []:
        c.human_flags.append(f)
    if r.get("human_review") and c.status == NON_CONFORME:
        c.human_flags.append("HUM-010")
    return c


def intrinsic(lines: list, var: dict, recon: dict, cfg: dict) -> list[Control]:
    out, tol = [], D(cfg.get("tolerance_fcfa", 1))
    crit = cfg.get("intrinsic_severity", {})
    # base × taux par ligne
    for l in lines:
        if str(l["type"]).startswith("overtime"):
            # HS : la ligne se lit « heures × taux horaire majoré » ; le taux de majoration (%) n'est pas un taux d'assiette.
            q, rt = l.get("quantity"), l["rate"]
            if l["amount"] is not None and q is not None and rt is not None and rt > 100:
                att = (D(q) * rt).quantize(Decimal("1"))
                diff = l["amount"] - att
                br = abs(diff) > max(tol, D(q))   # tolérance : arrondi du taux horaire affiché
                out.append(Control("C09", 19, f"Ligne « {l['label']} » : heures × taux horaire", NON_CONFORME if br else CONFORME,
                                   observed_value=l["amount"], expected_value=att, difference=diff, legal_reference=LINE_REF,
                                   finding="Montant de ligne incohérent avec les heures et le taux horaire" if br else "",
                                   recommendation="Corriger le calcul de la ligne" if br else "—",
                                   trace=[{"step": "heures × taux horaire", "formula": f"{fmt(q)} × {fmt(rt)}", "result": fmt(att)}],
                                   evidence_fields=_line_evidence(lines, l["type"]), base_severity=crit.get("line", "P3"),
                                   severity=crit.get("line", "P3") if br else None))
            continue
        if l["base"] is not None and l["rate"] is not None and l["amount"] is not None:
            att = (l["base"] * l["rate"] / 100).quantize(Decimal("1"))
            diff = l["amount"] - att
            br = abs(diff) > tol
            out.append(Control("C09", 19, f"Ligne « {l['label']} » : base × taux", NON_CONFORME if br else CONFORME,
                               observed_value=l["amount"], expected_value=att, difference=diff, legal_reference=LINE_REF,
                               finding="Montant de ligne incohérent avec sa base et son taux" if br else "",
                               recommendation="Corriger le calcul de la ligne" if br else "—",
                               trace=[{"step": "base × taux", "formula": f"{fmt(l['base'])} × {l['rate']} %", "result": fmt(att)}],
                               evidence_fields=_line_evidence(lines, l["type"]), base_severity=crit.get("line", "P3"),
                               severity=crit.get("line", "P3") if br else None))
    # brut
    g_rep, g_rec = recon["gross_reported"], recon["gross_recalculated"]
    if g_rep is None:
        out.append(Control("C09", 19, "Salaire brut = somme des gains", MSG_INFO, finding="Brut absent du bulletin (NET-001) — STOP partiel"))
    elif g_rec is not None:
        diff = g_rep - g_rec
        br = abs(diff) > tol
        out.append(Control("C09", 19, "Salaire brut = somme des gains", NON_CONFORME if br else CONFORME,
                           observed_value=g_rep, expected_value=g_rec, difference=diff, legal_reference=LINE_REF,
                           finding="Brut affiché différent de la somme des gains" if br else "",
                           recommendation="Reconstituer le brut" if br else "—",
                           trace=[{"step": "brut", "formula": " + ".join(f"{l['type']} {fmt(l['amount'])}" for l in lines if l['nature'] == 'gain' and l['amount'] is not None), "result": fmt(g_rec)}],
                           base_severity=crit.get("gross", "P2"), severity=crit.get("gross", "P2") if br else None))
    # net arithmétique
    n_rep, n_ar = recon["net_reported"], recon["net_arithmetic"]
    if n_rep is None:
        out.append(Control("C09", 19, "Net à payer — cohérence arithmétique", MSG_INFO, finding="Net absent du bulletin (NET-004) — STOP partiel"))
    elif n_ar is not None:
        diff = n_rep - n_ar
        br = abs(diff) > tol
        out.append(Control("C09", 19, "Net à payer — cohérence arithmétique (valeurs du bulletin)", NON_CONFORME if br else CONFORME,
                           observed_value=n_rep, expected_value=n_ar, difference=diff, legal_reference=LINE_REF,
                           finding="Net affiché ≠ brut − retenues affichées" if br else "",
                           recommendation="Recalculer le net" if br else "—",
                           trace=[{"step": "net", "formula": "gains − retenues salariales − retenues fiscales − autres retenues", "result": fmt(n_ar)}],
                           reserves=(["Avantages en nature présents : exclus du net payé, inclus selon les règles fiscales/sociales"] if recon["benefits_in_kind"] else []),
                           base_severity=crit.get("net", "P2"), severity=crit.get("net", "P2") if br else None))
    # salaire contractuel (ordre 03)
    cb, bs = var.get("contract_base_salary"), var.get("base_salary")
    if cb is not None and bs is not None:
        diff = bs - cb
        br = abs(diff) > tol
        c = Control("C01", 3, "Salaire de base bulletin = salaire contractuel", NON_CONFORME if br else CONFORME,
                    observed_value=bs, expected_value=cb, difference=diff, legal_reference="Contrat de travail / avenant (DOC-001/002)",
                    finding="Incohérence entre bulletin et contrat" if br else "", impact_type="rappel_salarie" if diff < 0 else "trop_percu",
                    recommendation="Vérifier avenant ou décision de rémunération ; régulariser" if br else "—",
                    base_severity=crit.get("contract", "P2"), severity=crit.get("contract", "P2") if br else None,
                    favorable_to=("employeur" if diff < 0 else "salarie") if br else None)
        if br:
            c.human_flags.append("HUM-003")
        out.append(c)
    # retenues : fondement (C08)
    for l in lines:
        if l["nature"] != "autre_retenue" or l["amount"] is None:
            continue
        sensible = l["type"] in ("disciplinary_deduction", "garnishment")
        if l["justification"]:
            st, sev, fnd = CONFORME, None, "Justificatif fourni (à apprécier par l'expert si retenue sensible)"
        else:
            st, sev = NON_CONFORME, ("P2" if sensible else "P4")
            fnd = "Retenue sans justificatif identifié — fondement à établir"
        c = Control("C08", 15, f"Retenue « {l['label']} » : fondement", st, observed_value=l["amount"],
                    legal_reference="Pièce justificative requise (DED-008 / EVD-005)", finding=fnd,
                    recommendation="Produire le justificatif (accord écrit, titre, décision)" if st == NON_CONFORME else "—",
                    evidence_fields=_line_evidence(lines, l["type"]), base_severity=sev, severity=sev)
        if sensible and st == NON_CONFORME:
            c.human_flags.append("HUM-004")
        out.append(c)
    # HS sans pointage
    if any(l["type"].startswith("overtime") for l in lines) and not var.get("timesheet_provided"):
        out.append(Control("C03", 12, "Heures supplémentaires : justificatif de temps", MSG_INFO,
                           legal_reference="TIM-011 / TIM-012", finding="Aucune fiche de pointage ou HS validée fournie — quantités non vérifiables",
                           recommendation="Fournir pointage et fiches HS validées"))
    # Prescription biennale (CT art. 33.5)
    m = var.get("months_since_period")
    if m is not None and m >= cfg.get("prescription_salaires_mois", 24):
        out.append(Control("C11", 20, "Prescription des rappels de salaire", "INDICE NÉCESSITANT INVESTIGATION",
                           legal_reference="Code du travail (loi n°2015-532), art. 33.5 et 33.6",
                           finding=f"Période échue depuis {m} mois : l'action en paiement du salaire se prescrit par deux ans, "
                                   "sauf interruption (reconnaissance écrite de l'employeur mentionnant le montant dû, lettre recommandée "
                                   "du salarié, requête à l'inspection du travail, requête au tribunal du travail)",
                           recommendation="Vérifier les actes interruptifs avant de chiffrer un rappel au profit du salarié ; "
                                          "la prescription ne couvre pas les cotisations CNPS ni l'ITS (régimes propres)"))
    return out


def required_families(applicable: list, cfg: dict, extra=()) -> list[Control]:
    present = {r["control_id"] for r in applicable} | set(extra)
    out = []
    for cid, (order, name) in cfg.get("required_families", {}).items():
        if cid not in present:
            out.append(Control(cid, order, f"{name} — règle applicable", MSG_REGLE,
                               finding="Aucune règle validée en vigueur à la période dans le registre",
                               recommendation="Juriste référent : saisir et valider la règle (Rules Registry)"))
    return out


# Contrôles sociaux transverses (matrice CNPS–CMU SOLEX §10)
LINE_PARAMS = {  # type: (param taux, code taux, param plafond, code plafond, champ taux)
    "cnps_retirement_employee": [("CNPS_RET_SAL_RATE", "CNPS-005", "CNPS_RET_PLAFOND", "CNPS-001", "rate"),
                                 ("CNPS_RET_EMP_RATE", "CNPS-006", None, None, "employer_rate")],
    "cnps_family_employer": [("CNPS_PF_RATE", "CNPS-007", "CNPS_AUTRES_PLAFOND", "CNPS-002", "rate")],
    "cnps_maternity_employer": [("CNPS_AM_RATE", "CNPS-008", "CNPS_AUTRES_PLAFOND", "CNPS-003", "rate")],
    "cnps_atmp_employer": [(None, "CNPS-009", "CNPS_AUTRES_PLAFOND", "CNPS-004", "rate")],
}


def social_checks(env, var: dict, lines: list, cfg: dict) -> list[Control]:
    out = []
    src = "Paramètres CNPS validés (Rules Registry SOLEX)"
    for l in lines:
        for prm, code_r, ceil, code_c, fld in LINE_PARAMS.get(l["type"], []):
            rate = l.get(fld)
            if rate is not None:
                if prm is None:
                    lo, hi = var.get("CNPS_ATMP_RATE_MIN"), var.get("CNPS_ATMP_RATE_MAX")
                    if lo is not None and hi is not None:
                        ok = D(lo) <= rate <= D(hi)
                        out.append(Control("C05", 16, f"Taux AT/MP appliqué ({fmt(rate)} %) dans l'intervalle autorisé",
                                           CONFORME if ok else NON_CONFORME, observed_value=rate, legal_reference=src,
                                           expected_value=f"{fmt(lo)}–{fmt(hi)} %", error_code=code_r if not ok else None,
                                           finding="" if ok else "Taux AT/MP hors intervalle", base_severity="P2", severity=None if ok else "P2",
                                           recommendation="—" if ok else "Vérifier le taux notifié par la CNPS"))
                elif var.get(prm) is not None:
                    ok = rate == D(var[prm])
                    out.append(Control("C05", 16, f"Taux appliqué « {l['label']} » ({'employeur' if fld == 'employer_rate' else 'ligne'})",
                                       CONFORME if ok else NON_CONFORME, observed_value=rate, expected_value=D(var[prm]),
                                       difference=rate - D(var[prm]), legal_reference=f"{src} — {prm}",
                                       error_code=None if ok else code_r, finding="" if ok else "Taux de cotisation erroné",
                                       base_severity="P2", severity=None if ok else "P2", impact_type="cnps",
                                       recommendation="—" if ok else "Appliquer le taux réglementaire"))
            if ceil and l["base"] is not None and var.get(ceil) is not None and fld == "rate":
                ok = l["base"] <= D(var[ceil])
                out.append(Control("C05", 16, f"Base « {l['label']} » ≤ plafond {fmt(var[ceil])}",
                                   CONFORME if ok else NON_CONFORME, observed_value=l["base"], expected_value=D(var[ceil]),
                                   difference=None if ok else l["base"] - D(var[ceil]), legal_reference=f"{src} — {ceil}",
                                   error_code=None if ok else code_c, finding="" if ok else "Base de cotisation supérieure au plafond de la branche",
                                   base_severity="P2", severity=None if ok else "P2", impact_type="cnps",
                                   recommendation="—" if ok else "Plafonner la base de la branche"))
    # PAY-001 : assiette déclarée vs recalculée
    r = env.compute_assiette()
    sb = var.get("social_base")
    if r is not None and sb is not None:
        v, detail, a_qual, res, caps_missing = r
        if a_qual or caps_missing:
            c = Control("C05", 16, "Assiette CNPS déclarée vs recalculée", MSG_NQ, observed_value=sb, expected_value=v,
                        legal_reference="Code de prévoyance sociale, art. 23 — matrice d'assiette SOLEX",
                        finding=("Éléments à qualifier juridiquement : " + ", ".join(a_qual) + ". " if a_qual else "")
                                + ("Plafond d'exclusion non paramétré pour : " + ", ".join(caps_missing) if caps_missing else ""),
                        reserves=res, trace=[{"step": "assiette recalculée", "formula": " ; ".join(detail), "result": fmt(v)}])
            if a_qual:
                c.human_flags.append("HUM-010")
        else:
            diff = D(sb) - v
            br = abs(diff) > D(cfg.get("tolerance_fcfa", 1))
            sev = cfg.get("intrinsic_severity", {}).get("assiette_cnps", "P1")
            c = Control("C05", 16, "Assiette CNPS déclarée vs recalculée", NON_CONFORME if br else CONFORME,
                        observed_value=sb, expected_value=v, difference=diff, error_code="PAY-001" if br else None,
                        legal_reference="Code de prévoyance sociale, art. 23 — matrice d'assiette SOLEX", reserves=res,
                        finding=("Assiette sous-évaluée (élément soumis exclu, fraction plafonnée totalement exonérée ou avantage en nature omis : CNPS-010/012/013)"
                                 if diff < 0 else "Assiette surévaluée (élément exclu intégré)") if br else "",
                        trace=[{"step": "assiette recalculée", "formula": " ; ".join(detail), "result": fmt(v)}],
                        base_severity=sev, severity=sev if br else None, impact_type="cnps",
                        recommendation="Reconstituer l'assiette selon la matrice CNPS" if br else "—")
        out.append(c)
    # PAY-003 : revenu imposable déclaré vs recalculé (matrice fiscale composante par composante)
    r = env.compute_assiette("its_assiette")
    tb = var.get("tax_base")
    if r is not None:
        v, detail, a_qual, res, caps_missing = r
        codes = getattr(env, "assiette_codes", {}).get("its_assiette", [])
        hflags = getattr(env, "assiette_flags", {}).get("its_assiette", [])
        ref = "CGI art. 116 et 118–119 (ordonnance n°2023-719) — matrice SOLEX du revenu imposable"
        used = getattr(env, "assiette_sources", {}).get("its_assiette", [])
        if used:
            ref += " ; sources des composantes : " + " | ".join(used)
        tr = [{"step": "revenu imposable recalculé", "formula": " ; ".join(detail), "result": fmt(v)}]
        diag = " ; ".join(f"{c} {m}" for c, m in codes)
        if tb is None:
            if codes:
                c = Control("C07", 18, "Revenu imposable ITS — qualification des composantes", "INDICE NÉCESSITANT INVESTIGATION",
                            expected_value=v, legal_reference=ref, reserves=res, trace=tr, finding=diag, error_code=codes[0][0],
                            recommendation="Qualifier / justifier les composantes signalées")
                c.human_flags += [h for h, _ in hflags]
                out.append(c)
        elif a_qual or caps_missing:
            c = Control("C07", 18, "Revenu imposable ITS déclaré vs recalculé", MSG_NQ, observed_value=tb, expected_value=v,
                        legal_reference=ref, reserves=res, trace=tr, error_code=codes[0][0] if codes else "TAX-E001",
                        finding="Éléments à qualifier fiscalement : " + ", ".join(a_qual + caps_missing) + (f" — {diag}" if diag else ""))
            c.human_flags += [h for h, _ in hflags]
            out.append(c)
        else:
            diff = D(tb) - v
            tol = D(cfg.get("tolerance_fcfa", 1))
            br = abs(diff) > tol
            sev = cfg.get("intrinsic_severity", {}).get("assiette_its", "P2")
            soc = sum((l["amount"] for l in lines if l["nature"] == "retenue_salariale" and l["amount"] is not None), Decimal(0))
            code = None
            if br:
                code = "TAX-E013" if soc and abs(diff + soc) <= tol else (codes[0][0] if codes else "PAY-003")
            find = ""
            if br:
                find = ("Cotisations sociales salariales (CNPS/CMU) déduites à tort du revenu imposable" if code == "TAX-E013"
                        else ("Revenu imposable sous-évalué" if diff < 0 else "Revenu imposable surévalué"))
                if diag:
                    find += " — " + diag
            elif diag:
                find = "Diagnostic : " + diag
            c = Control("C07", 18, "Revenu imposable ITS déclaré vs recalculé", NON_CONFORME if br else CONFORME,
                        observed_value=tb, expected_value=v, difference=diff, error_code=code,
                        legal_reference=ref, reserves=res, trace=tr, base_severity=sev, severity=sev if br else None,
                        impact_type="fiscal", finding=find, recommendation="Reconstituer le revenu imposable" if br else "—")
            c.human_flags += [h for h, _ in hflags]
            out.append(c)
    return out


def mentions_check(env, var: dict, tables: dict, fields: dict) -> list[Control]:
    """C10 — mentions obligatoires du bulletin (CCI 1977, art. 46)."""
    tab = (tables or {}).get("mentions_bulletin")
    if not tab:
        return []
    ref = f"{tab['rule_id']} v{tab['version']} — {tab['legal_source']}, art. {tab['article']} (en vigueur depuis {tab['effective_from']})"
    seen = var.get("mentions") or {}
    absent, unknown, present, na = [], [], [], []
    for m in tab["mentions"]:
        lib = f"{m['n']} {m['label']}"
        try:
            required, _ = env.run(m.get("condition", "True"))
        except MissingInput as e:
            unknown.append(f"{lib} (condition invérifiable : {e.name})")
            continue
        if not required:
            na.append(lib)
            continue
        v = seen.get(m["key"])
        if v is True:
            present.append(lib)
        elif v is False:
            absent.append(lib)
        else:
            unknown.append(f"{lib} (non vérifiée)")
    ev = [f.as_dict() for k, f in fields.items() if k.startswith("payslip_mentions.")]
    trace = [{"step": "mentions art. 46", "formula": f"{len(present)} présentes / {len(absent)} absentes / {len(unknown)} non vérifiées / {len(na)} sans objet",
              "result": "; ".join(f"ABSENTE : {a}" for a in absent) or "aucune mention absente"}]
    sev = tab.get("default_severity", "P4")
    if absent:
        c = Control("C10", 19, "Mentions obligatoires du bulletin (CCI art. 46)", NON_CONFORME, rule_id=tab["rule_id"],
                    rule_version=tab["version"], legal_reference=ref, observed_value=f"{len(absent)} mention(s) absente(s)",
                    expected_value=f"{len(absent) + len(present) + len(unknown)} mentions requises",
                    finding="Mentions absentes : " + " ; ".join(absent), recommendation="Compléter le modèle de bulletin de paie",
                    base_severity=sev, severity=sev, error_code=tab.get("error_code"), trace=trace, evidence_fields=ev)
        if unknown:
            c.reserves.append("Non vérifiées : " + " ; ".join(unknown))
    elif unknown:
        c = Control("C10", 19, "Mentions obligatoires du bulletin (CCI art. 46)", MSG_INFO, rule_id=tab["rule_id"],
                    rule_version=tab["version"], legal_reference=ref, finding="Mentions non vérifiées : " + " ; ".join(unknown),
                    recommendation="Relever chaque mention sur le bulletin (payslip_mentions)", trace=trace, evidence_fields=ev)
    else:
        c = Control("C10", 19, "Mentions obligatoires du bulletin (CCI art. 46)", CONFORME, rule_id=tab["rule_id"],
                    rule_version=tab["version"], legal_reference=ref, observed_value=f"{len(present)} présentes",
                    expected_value=f"{len(present)} requises", base_severity=sev, trace=trace, evidence_fields=ev,
                    finding=(f"Sans objet : {' ; '.join(na)}" if na else ""))
    return [c]
