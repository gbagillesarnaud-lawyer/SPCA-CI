#!/usr/bin/env python
"""SPCA-CI — Moteur de calcul et de contrôle déterministe (SOLEX).

Principe : le moteur ne contient AUCUNE valeur juridique (taux, plafond, barème, minimum).
Toutes les valeurs proviennent des fiches de règles du référentiel SOLEX, et seules les
règles au statut "validee", en vigueur à la période auditée, sont appliquées.

Usage :
  python spca_engine.py --bulletin bulletin.json --referentiel <dossier_regles> --sortie <dossier>
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

VERSION_MOTEUR = "0.1.0"
ICI = Path(__file__).resolve().parent

MSG_INFO = "NON CONTRÔLABLE — INFORMATION MANQUANTE"
MSG_REGLE = "RÈGLE APPLICABLE NON DÉTERMINÉE"
MSG_NQ = "ÉCART NON QUANTIFIABLE EN L'ÉTAT"
ESCALADE_TXT = "ESCALADE REQUISE — VALIDATION PAR JURISTE / EXPERT FISCAL / EXPERT SOCIAL AVANT CORRECTION."

NATURES = {"gain", "retenue_salariale", "retenue_fiscale", "autre_retenue", "charge_patronale", "information"}


# ----------------------------------------------------------------- utilitaires
def D(x) -> Decimal | None:
    if x is None or x == "":
        return None
    return Decimal(str(x))


def arrondir(v: Decimal, mode: str = "unite") -> Decimal:
    if mode == "aucun":
        return v
    pas = {"unite": Decimal("1"), "dizaine": Decimal("10"), "centime": Decimal("0.01")}.get(mode, Decimal("1"))
    return (v / pas).quantize(Decimal("1"), rounding=ROUND_HALF_UP) * pas


def fmt(v) -> str:
    if v is None:
        return "—"
    v = Decimal(v)
    if v == v.to_integral():
        return f"{int(v):,}".replace(",", " ")
    return f"{v:,.2f}".replace(",", " ")


def periode_date(periode: str) -> dt.date:
    """'AAAA-MM' -> premier jour du mois."""
    a, m = periode.split("-")[:2]
    return dt.date(int(a), int(m), 1)


def charger_config() -> dict:
    p = ICI / "config_moteur.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def charger_regles(dossier: Path) -> tuple[list[dict], list[str]]:
    regles, ignorees = [], []
    if not dossier.exists():
        return regles, [f"Dossier référentiel absent : {dossier}"]
    for f in sorted(dossier.rglob("*.json")):  # récursif : PAYROLL_RULES/<famille>/*.json
        if f.name.startswith("_"):
            continue  # modèles
        try:
            r = json.loads(f.read_text(encoding="utf-8"))
        except Exception as e:  # noqa: BLE001
            ignorees.append(f"{f.name} : JSON invalide ({e})")
            continue
        if r.get("statut") != "validee":
            ignorees.append(f"{r.get('id', f.name)} : statut '{r.get('statut')}' (non validée)")
            continue
        manquants = [k for k in ("id", "version", "famille", "type", "validite", "source", "parametres") if k not in r]
        if manquants:
            ignorees.append(f"{r.get('id', f.name)} : champs manquants {manquants}")
            continue
        regles.append(r)
    return regles, ignorees


def en_vigueur(r: dict, date: dt.date) -> bool:
    v = r["validite"]
    debut = dt.date.fromisoformat(v["debut"])
    fin = dt.date.fromisoformat(v["fin"]) if v.get("fin") else None
    return debut <= date and (fin is None or date <= fin)


# ---------------------------------------------------------------- moteur
class Audit:
    def __init__(self, bulletin: dict, regles: list[dict], ignorees: list[str], config: dict):
        self.b = bulletin
        self.cfg = config
        self.tol = D(config.get("tolerance_ecart", 1))
        self.crit_def = config.get("criticite_par_defaut", {})
        self.toutes_regles = regles
        self.ignorees = list(ignorees)
        self.controles: list[dict] = []
        self.stops: list[str] = []
        self.escalades: list[dict] = []
        self.regles_utilisees: dict[str, dict] = {}
        self.theorique: dict[str, Decimal] = {}  # famille -> montant salarial théorique
        self.theorique_patronal: dict[str, Decimal] = {}
        self.rubriques = bulletin.get("rubriques", [])
        self.idx = {r.get("code"): r for r in self.rubriques if r.get("code")}

    # -- helpers
    def ajouter(self, **c):
        c.setdefault("ecart", None)
        c.setdefault("criticite", None)
        c.setdefault("trace", [])
        c.setdefault("reference", "—")
        c.setdefault("correction", "—")
        self.controles.append(c)
        return c

    def escalader(self, motif: str, expert: str = "Juriste droit social"):
        self.escalades.append({"motif": motif, "expert": expert, "statut": "EN ATTENTE"})

    def somme(self, natures=None, codes=None, exclure=()) -> tuple[Decimal, list[str]]:
        tot, lignes = Decimal(0), []
        for r in self.rubriques:
            if r.get("code") in exclure:
                continue
            ok = (codes is not None and r.get("code") in codes) or (natures is not None and r.get("nature") in natures)
            if ok and D(r.get("montant")) is not None:
                tot += D(r["montant"])
                lignes.append(f"{r.get('code')} {r.get('libelle', '')} = {fmt(r['montant'])}")
        return tot, lignes

    # -- étape 0 : stops préalables
    def preconditions(self) -> dt.date | None:
        a = self.b.get("audit", {})
        if (a.get("juridiction") or "").upper() not in {"CI", "CIV", "COTE D'IVOIRE", "CÔTE D'IVOIRE"}:
            self.stops.append("STOP 2 — Juridiction inconnue ou non ivoirienne")
        per = a.get("periode")
        date = None
        try:
            date = periode_date(per)
        except Exception:  # noqa: BLE001
            self.stops.append("STOP 3 — Période de paie indéterminée")
        if not self.rubriques:
            self.stops.append("STOP 1 — Aucune donnée de paie exploitable")
        for r in self.rubriques:
            if r.get("nature") not in NATURES:
                self.ignorees.append(f"Rubrique {r.get('code')} : nature '{r.get('nature')}' inconnue")
        return date

    # -- étape 3a : contrôles arithmétiques (ne nécessitent aucune règle juridique)
    def arithmetique(self):
        for r in self.rubriques:
            base, taux, mt = D(r.get("base")), D(r.get("taux")), D(r.get("montant"))
            if base is None or taux is None or mt is None:
                continue
            attendu = arrondir(base * taux / 100)
            ecart = mt - attendu
            anomalie = abs(ecart) > self.tol
            self.ajouter(
                code="CT-A02", element=f"Ligne {r.get('code')} — {r.get('libelle', '')} : base × taux",
                famille="ARITHMETIQUE", statut="ANOMALIE" if anomalie else "CONFORME",
                constate=mt, attendu=attendu, ecart=ecart,
                criticite=self.crit_def.get("CT-A02", "P3") if anomalie else None,
                trace=[f"{fmt(base)} × {taux} % = {fmt(attendu)} → bulletin {fmt(mt)} → écart {fmt(ecart)}"],
                reference="Contrôle arithmétique interne", source_doc=r.get("source"),
                correction="Corriger le montant de la ligne" if anomalie else "—",
            )
        tot = self.b.get("totaux", {})
        gains, lg = self.somme(natures={"gain"})
        if D(tot.get("brut")) is not None and lg:
            ec = D(tot["brut"]) - gains
            an = abs(ec) > self.tol
            self.ajouter(code="CT-A01", element="Salaire brut = somme des gains", famille="ARITHMETIQUE",
                         statut="ANOMALIE" if an else "CONFORME", constate=D(tot["brut"]), attendu=gains, ecart=ec,
                         criticite=self.crit_def.get("CT-A01", "P2") if an else None,
                         trace=[" + ".join(lg) + f" = {fmt(gains)}"], reference="Contrôle arithmétique interne",
                         correction="Reconstituer le brut" if an else "—")
        elif D(tot.get("brut")) is None:
            self.ajouter(code="CT-A01", element="Salaire brut = somme des gains", famille="ARITHMETIQUE",
                         statut=MSG_INFO, constate=None, attendu=gains or None, trace=["Brut absent du bulletin"])
        ret, lr = self.somme(natures={"retenue_salariale", "retenue_fiscale", "autre_retenue"})
        if D(tot.get("net_a_payer")) is not None and lg:
            net_th = gains - ret
            ec = D(tot["net_a_payer"]) - net_th
            an = abs(ec) > self.tol
            self.ajouter(code="CT-A03", element="Net à payer = brut − retenues (valeurs du bulletin)",
                         famille="ARITHMETIQUE", statut="ANOMALIE" if an else "CONFORME",
                         constate=D(tot["net_a_payer"]), attendu=net_th, ecart=ec,
                         criticite=self.crit_def.get("CT-A03", "P2") if an else None,
                         trace=[f"{fmt(gains)} − ({' + '.join(lr) or '0'}) = {fmt(net_th)}"],
                         reference="Contrôle arithmétique interne", correction="Recalculer le net" if an else "—")
        else:
            self.ajouter(code="CT-A03", element="Net à payer", famille="ARITHMETIQUE", statut=MSG_INFO,
                         constate=None, attendu=None, trace=["Net à payer absent du bulletin"])

    # -- étape 2 + 3b : règles du référentiel
    def champ_ok(self, r: dict) -> tuple[bool, str | None]:
        ca = r.get("champ_application") or {}
        sal = self.b.get("salarie", {})
        for cle, attr in (("categories", "categorie"), ("types_contrat", "type_contrat")):
            if ca.get(cle):
                val = sal.get(attr)
                if val in (None, ""):
                    return False, f"donnée salarié '{attr}' manquante"
                if val not in ca[cle]:
                    return False, "hors champ"
        return True, None

    def assiette(self, r: dict) -> tuple[Decimal, list[str]]:
        a = r.get("assiette") or {}
        if a.get("rubriques"):
            return self.somme(codes=set(a["rubriques"]))
        return self.somme(natures=set(a.get("natures", ["gain"])), exclure=set(a.get("exclure", [])))

    def reference(self, r: dict) -> str:
        s = r["source"]
        return (f"{r['id']} v{r['version']} — {s.get('texte', '?')}, {s.get('article', '?')} "
                f"({s.get('autorite', '?')}), en vigueur du {r['validite']['debut']}"
                f"{' au ' + r['validite']['fin'] if r['validite'].get('fin') else ''}")

    def appliquer_regles(self, date: dt.date):
        applicables = [r for r in self.toutes_regles if en_vigueur(r, date)]
        for r in self.toutes_regles:
            if r not in applicables:
                self.ignorees.append(f"{r['id']} v{r['version']} : hors période de validité pour {date:%Y-%m}")
        familles_req = self.cfg.get("familles_requises", [])
        fam_presentes = {r["famille"] for r in applicables}
        for fam in familles_req:
            if fam not in fam_presentes:
                self.ajouter(code=f"REF-{fam}", element=f"Référentiel {fam} pour {date:%Y-%m}", famille=fam,
                             statut=MSG_REGLE, constate=None, attendu=None,
                             trace=["Aucune règle validée en vigueur à la période"],
                             correction="Juriste référent : saisir et valider la règle")
        if familles_req and not (fam_presentes & set(familles_req)):
            self.stops.append("STOP 4 — Référentiel juridique indisponible pour la période auditée")
            self.escalader("Référentiel juridique indisponible pour la période", "Direction juridique SOLEX")

        for r in applicables:
            ok, raison = self.champ_ok(r)
            if not ok:
                if raison != "hors champ":
                    self.ajouter(code=r.get("controle", r["id"]), element=r.get("intitule", r["id"]),
                                 famille=r["famille"], statut=MSG_INFO, constate=None, attendu=None,
                                 trace=[raison], reference=self.reference(r))
                continue
            self.regles_utilisees[r["id"]] = r
            getattr(self, f"regle_{r['type']}", self.regle_inconnue)(r)

    def cible(self, r: dict):
        code = (r.get("cible") or {}).get("rubrique")
        return code, self.idx.get(code) if code else None

    def comparer(self, r, element, constate, attendu, trace, patronal=False):
        crit = r.get("criticite_si_ecart", "P2")
        if constate is None:
            return self.ajouter(code=r.get("controle", r["id"]), element=element, famille=r["famille"],
                                statut=MSG_INFO, constate=None, attendu=attendu,
                                trace=trace + ["Rubrique absente du bulletin — absence à qualifier"],
                                reference=self.reference(r),
                                correction="Vérifier l'absence de la retenue / cotisation")
        ec = constate - attendu
        an = abs(ec) > self.tol
        return self.ajouter(code=r.get("controle", r["id"]), element=element, famille=r["famille"],
                            statut="ANOMALIE" if an else "CONFORME", constate=constate, attendu=attendu, ecart=ec,
                            criticite=crit if an else None, trace=trace, reference=self.reference(r),
                            correction=(r.get("correction") or "Régulariser selon la règle citée") if an else "—")

    def regle_taux_sur_assiette(self, r):
        p = r["parametres"]
        base, lignes = self.assiette(r)
        trace = [f"Assiette {r['famille']} = " + (" + ".join(lignes) or "0") + f" = {fmt(base)}"]
        if D(p.get("plafond")) is not None and base > D(p["plafond"]):
            trace.append(f"Plafonnement : {fmt(base)} > plafond {fmt(p['plafond'])} → assiette retenue {fmt(p['plafond'])}")
            base = D(p["plafond"])
        code, rub = self.cible(r)
        mode = p.get("arrondi", "unite")
        if D(p.get("taux_salarial")) is not None:
            att = arrondir(base * D(p["taux_salarial"]) / 100, mode)
            self.theorique[r["famille"]] = self.theorique.get(r["famille"], Decimal(0)) + att
            t = trace + [f"{fmt(base)} × {p['taux_salarial']} % = {fmt(att)} (part salariale)"]
            self.comparer(r, f"{r.get('intitule', r['id'])} — part salariale", D(rub.get("montant")) if rub else None, att, t)
        if D(p.get("taux_patronal")) is not None:
            att = arrondir(base * D(p["taux_patronal"]) / 100, mode)
            self.theorique_patronal[r["famille"]] = self.theorique_patronal.get(r["famille"], Decimal(0)) + att
            t = trace + [f"{fmt(base)} × {p['taux_patronal']} % = {fmt(att)} (part patronale)"]
            self.comparer(r, f"{r.get('intitule', r['id'])} — part patronale",
                          D(rub.get("montant_patronal")) if rub else None, att, t)

    def regle_bareme_progressif(self, r):
        p = r["parametres"]
        base, lignes = self.assiette(r)
        trace = [f"Assiette {r['famille']} = " + (" + ".join(lignes) or "0") + f" = {fmt(base)}"]
        if D(p.get("abattement_pct")) is not None:
            ab = arrondir(base * D(p["abattement_pct"]) / 100, "aucun")
            trace.append(f"Abattement {p['abattement_pct']} % : {fmt(base)} − {fmt(ab)} = {fmt(base - ab)}")
            base -= ab
        impot = Decimal(0)
        for tr in p["tranches"]:
            de, a, tx = D(tr["de"]), D(tr.get("a")), D(tr["taux"])
            if base <= de:
                break
            haut = min(base, a) if a is not None else base
            part = (haut - de) * tx / 100
            impot += part
            trace.append(f"Tranche {fmt(de)}–{fmt(a) if a is not None else '∞'} : ({fmt(haut)} − {fmt(de)}) × {tx} % = {fmt(part)}")
        impot = arrondir(impot, p.get("arrondi", "unite"))
        trace.append(f"Total barème = {fmt(impot)}")
        if p.get("donnees_requises"):
            manq = [k for k in p["donnees_requises"] if self.b.get("salarie", {}).get(k) in (None, "")]
            if manq:
                self.ajouter(code=r.get("controle", r["id"]), element=r.get("intitule", r["id"]), famille=r["famille"],
                             statut=MSG_INFO, constate=None, attendu=None, trace=trace + [f"Données manquantes : {manq}"],
                             reference=self.reference(r))
                return
        self.theorique[r["famille"]] = self.theorique.get(r["famille"], Decimal(0)) + impot
        code, rub = self.cible(r)
        self.comparer(r, r.get("intitule", r["id"]), D(rub.get("montant")) if rub else None, impot, trace)

    def regle_minimum(self, r):
        p = r["parametres"]
        code, rub = self.cible(r)
        mini = D(p["montant_minimum"])
        if rub is None or D(rub.get("montant")) is None:
            self.ajouter(code=r.get("controle", r["id"]), element=r.get("intitule", r["id"]), famille=r["famille"],
                         statut=MSG_INFO, constate=None, attendu=mini, trace=[f"Rubrique {code} absente"],
                         reference=self.reference(r))
            return
        tp = D(self.b.get("salarie", {}).get("taux_temps_travail"))
        if tp is not None and tp != 100:
            self.ajouter(code=r.get("controle", r["id"]), element=r.get("intitule", r["id"]), famille=r["famille"],
                         statut=MSG_NQ, constate=D(rub["montant"]), attendu=mini,
                         trace=[f"Temps de travail {tp} % : proratisation non définie dans la règle"],
                         reference=self.reference(r))
            self.escalader(f"{r['id']} : minimum à apprécier pour un temps partiel", "Juriste droit social")
            return
        mt = D(rub["montant"])
        an = mt + self.tol < mini
        self.ajouter(code=r.get("controle", r["id"]), element=r.get("intitule", r["id"]), famille=r["famille"],
                     statut="ANOMALIE" if an else "CONFORME", constate=mt, attendu=mini,
                     ecart=(mt - mini) if an else Decimal(0), criticite=r.get("criticite_si_ecart", "P1") if an else None,
                     trace=[f"{code} = {fmt(mt)} {'<' if an else '≥'} minimum {fmt(mini)}"], reference=self.reference(r),
                     correction=(r.get("correction") or "Porter le salaire au minimum applicable et calculer le rappel") if an else "—")

    def regle_inconnue(self, r):
        self.ajouter(code=r.get("controle", r["id"]), element=r.get("intitule", r["id"]), famille=r["famille"],
                     statut=MSG_NQ, constate=None, attendu=None, trace=[f"Type de règle '{r['type']}' non pris en charge"],
                     reference=self.reference(r))

    # -- étape 4 : synthèse
    def reconstitution(self) -> dict:
        gains, _ = self.somme(natures={"gain"})
        tot = self.b.get("totaux", {})

        def bulletin_famille(fam):
            codes = {(r.get("cible") or {}).get("rubrique") for r in self.regles_utilisees.values() if r["famille"] == fam}
            s, l = self.somme(codes=codes)
            return s if l else None

        def assiette_fam(fam):
            for r in self.regles_utilisees.values():
                if r["famille"] == fam:
                    return self.assiette(r)[0]
            return None

        autres, _ = self.somme(natures={"autre_retenue"})
        net_th = None
        if all(f in self.theorique for f in ("CNPS", "CMU", "ITS")):
            net_th = gains - self.theorique["CNPS"] - self.theorique["CMU"] - self.theorique["ITS"] - autres
        net_b = D(tot.get("net_a_payer"))
        return {
            "brut_bulletin": D(tot.get("brut")), "brut_recalcule": gains,
            "assiette_cnps": assiette_fam("CNPS"), "cnps_theorique": self.theorique.get("CNPS"),
            "cnps_bulletin": bulletin_famille("CNPS"),
            "cmu_theorique": self.theorique.get("CMU"), "cmu_bulletin": bulletin_famille("CMU"),
            "assiette_fiscale": assiette_fam("ITS"), "its_theorique": self.theorique.get("ITS"),
            "its_bulletin": bulletin_famille("ITS"),
            "autres_retenues": autres, "net_theorique": net_th, "net_bulletin": net_b,
            "ecart_net": (net_b - net_th) if (net_b is not None and net_th is not None) else None,
        }

    def confiance(self) -> str:
        confs = [float(r["confiance"]) for r in self.rubriques if r.get("confiance") is not None]
        mini = min(confs) if confs else 0.0
        nc = sum(1 for c in self.controles if c["statut"] not in ("CONFORME", "ANOMALIE"))
        ratio = nc / len(self.controles) if self.controles else 1
        if self.stops or mini < 0.6 or ratio > 0.5:
            return "FAIBLE"
        if mini < 0.85 or nc:
            return "MOYEN"
        return "ÉLEVÉ"

    def executer(self) -> dict:
        date = self.preconditions()
        if not any(s.startswith(("STOP 1",)) for s in self.stops):
            self.arithmetique()
        if date and not any(s.startswith(("STOP 2", "STOP 1")) for s in self.stops):
            self.appliquer_regles(date)
        crit = {k: sum(1 for c in self.controles if c.get("criticite") == k) for k in ("P1", "P2", "P3", "P4")}
        for c in self.controles:
            if c.get("criticite") == "P1":
                self.escalader(f"Anomalie P1 : {c['element']}", "Juriste droit social")
        conf = self.confiance()
        if conf == "FAIBLE":
            self.escalader("Niveau de confiance faible", "Spécialiste paie")
        anomalies = [c for c in self.controles if c["statut"] == "ANOMALIE"]
        non_ctrl = [c for c in self.controles if c["statut"] not in ("CONFORME", "ANOMALIE")]
        if self.stops:
            statut = "ESCALADE REQUISE" if self.escalades else "AUDIT INCOMPLET"
            if any(s.startswith(("STOP 1", "STOP 2", "STOP 3", "STOP 4")) for s in self.stops):
                statut = "AUDIT INCOMPLET"
        elif self.escalades:
            statut = "ESCALADE REQUISE"
        elif anomalies:
            statut = "NON CONFORME"
        elif non_ctrl:
            statut = "CONFORME SOUS RÉSERVE"
        else:
            statut = "CONFORME"
        return {
            "meta": {"moteur": VERSION_MOTEUR, "horodatage": dt.datetime.now().isoformat(timespec="seconds"),
                     "referentiel": sorted(f"{r['id']} v{r['version']}" for r in self.regles_utilisees.values()),
                     "statut_rapport": "PROVISOIRE — À VALIDER PAR UN EXPERT SOLEX"},
            "identification": {**self.b.get("audit", {}), **{k: self.b.get("salarie", {}).get(k) for k in
                               ("id", "fonction", "classification", "categorie", "date_embauche")},
                               "convention_collective": self.b.get("employeur", {}).get("convention_collective")},
            "conclusion": {"statut": statut, **crit, "confiance": conf, "stops": self.stops},
            "controles": self.controles,
            "reconstitution": self.reconstitution(),
            "escalades": self.escalades,
            "regles_ignorees": self.ignorees,
            "sources": [{"id": r["id"], "version": r["version"], **r["source"], "validite": r["validite"]}
                        for r in self.regles_utilisees.values()],
        }


# ---------------------------------------------------------------- rapport
def rapport_md(res: dict) -> str:
    i, c, rc = res["identification"], res["conclusion"], res["reconstitution"]
    L = [f"# Rapport d'audit de paie — {i.get('id_audit', '')}",
         f"**{res['meta']['statut_rapport']}** · moteur SPCA-CI v{res['meta']['moteur']} · {res['meta']['horodatage']}", "",
         "## A. Identification", "| Élément | Valeur |", "|---|---|"]
    for k, lib in (("entreprise", "Entreprise"), ("id", "Salarié (ID anonymisé)"), ("fonction", "Fonction"),
                   ("classification", "Classification"), ("categorie", "Catégorie"),
                   ("convention_collective", "Convention collective"), ("periode", "Période"),
                   ("date_embauche", "Date d'embauche"), ("date_reference", "Date de référence de l'audit")):
        L.append(f"| {lib} | {i.get(k) or MSG_INFO} |")
    L += ["", "## B. Conclusion générale", f"**Statut : {c['statut']}**", "",
          f"P1 : {c['P1']} · P2 : {c['P2']} · P3 : {c['P3']} · P4 : {c['P4']} · Niveau de confiance : **{c['confiance']}**"]
    for s in c["stops"]:
        L.append(f"- ⛔ {s}")
    L += ["", "## C. Tableau des contrôles",
          "| Élément contrôlé | Valeur constatée | Valeur attendue | Écart | Référence | Statut / Criticité | Correction |",
          "|---|---|---|---|---|---|---|"]
    for x in res["controles"]:
        st = x["statut"] + (f" — {x['criticite']}" if x.get("criticite") else "")
        L.append(f"| {x['element']} | {fmt(x['constate'])} | {fmt(x['attendu'])} | {fmt(x['ecart'])} | {x['reference']} | {st} | {x['correction']} |")
    L += ["", "### Traces de calcul (Input → formule → taux → résultat → comparaison)"]
    for x in res["controles"]:
        L.append(f"- **{x['code']} — {x['element']}** : " + " ; ".join(x["trace"]))
    L += ["", "## D. Reconstitution de la paie", "| Poste | Montant |", "|---|---|"]
    for k, lib in (("brut_bulletin", "Brut bulletin"), ("brut_recalcule", "Brut recalculé"),
                   ("assiette_cnps", "Assiette CNPS"), ("cnps_theorique", "CNPS théorique (part salariale)"),
                   ("cmu_theorique", "CMU théorique"), ("assiette_fiscale", "Assiette fiscale"),
                   ("its_theorique", "ITS théorique"), ("autres_retenues", "Autres retenues"),
                   ("net_theorique", "Net théorique"), ("net_bulletin", "Net bulletin"), ("ecart_net", "Écart net")):
        v = rc.get(k)
        L.append(f"| {lib} | {fmt(v) if v is not None else MSG_NQ} |")
    L += ["", "## E. Synthèse financière (écarts mensuels constatés — aucune extrapolation)",
          "| Poste | Écart (bulletin − attendu) |", "|---|---|"]
    for fam, lib in (("CNPS", "Écart CNPS"), ("CMU", "Écart CMU"), ("ITS", "Écart fiscal (ITS)"), ("MINIMUM", "Rappel potentiel salarié (minimum)")):
        ecs = [x["ecart"] for x in res["controles"] if x["famille"] == fam and x["statut"] == "ANOMALIE" and x["ecart"] is not None]
        L.append(f"| {lib} | {fmt(sum(ecs)) if ecs else ('0' if any(x['famille'] == fam and x['statut'] == 'CONFORME' for x in res['controles']) else MSG_NQ)} |")
    nq = [x["element"] for x in res["controles"] if x["statut"] not in ("CONFORME", "ANOMALIE")]
    L.append(f"| Montants non quantifiables | {len(nq)} point(s) |")
    L += ["", "## F. Plan correctif",
          "| Anomalie | Correction | Responsable | Priorité | Échéance | Régularisation rétroactive |", "|---|---|---|---|---|---|"]
    an = [x for x in res["controles"] if x["statut"] == "ANOMALIE"]
    for x in sorted(an, key=lambda y: y.get("criticite") or "P9"):
        L.append(f"| {x['element']} | {x['correction']} | À désigner | {x['criticite']} | À fixer par SOLEX | À examiner par l'expert (périodes antérieures non auditées) |")
    if not an:
        L.append("| Aucune anomalie détectée sur les points contrôlés | — | — | — | — | — |")
    L += ["", "## G. Escalades"]
    if res["escalades"]:
        L.append(f"**{ESCALADE_TXT}**")
        for e in res["escalades"]:
            L.append(f"- {e['motif']} → {e['expert']} ({e['statut']})")
    else:
        L.append("Aucune escalade automatique déclenchée par le moteur.")
    if nq:
        L += ["", "Points non contrôlés :"] + [f"- {n}" for n in nq]
    L += ["", "## H. Sources"]
    for s in res["sources"]:
        L.append(f"- {s['id']} v{s['version']} — {s.get('texte')}, {s.get('article')} — {s.get('autorite')} — "
                 f"version {s.get('version_texte', '?')} — effet {s['validite']['debut']}")
    if not res["sources"]:
        L.append("- Aucune règle du référentiel appliquée.")
    if res["regles_ignorees"]:
        L += ["", "Règles écartées :"] + [f"- {g}" for g in res["regles_ignorees"]]
    L += ["", "---", "_Rapport d'aide à la décision généré automatiquement. L'absence d'anomalie détectée ne vaut pas "
          "certification de conformité. Validation obligatoire par un expert SOLEX avant toute utilisation._"]
    return "\n".join(L)


def _json_default(o):
    return str(o) if isinstance(o, Decimal) else o


def main(argv=None):
    ap = argparse.ArgumentParser(description="SPCA-CI — moteur de contrôle de paie")
    ap.add_argument("--bulletin", required=True)
    ap.add_argument("--referentiel", required=True)
    ap.add_argument("--sortie", required=True)
    ap.add_argument("--journal", default=str(ICI.parent / "journal" / "journal_audit.jsonl"))
    a = ap.parse_args(argv)
    bulletin = json.loads(Path(a.bulletin).read_text(encoding="utf-8"))
    regles, ignorees = charger_regles(Path(a.referentiel))
    res = Audit(bulletin, regles, ignorees, charger_config()).executer()
    out = Path(a.sortie); out.mkdir(parents=True, exist_ok=True)
    (out / "resultat.json").write_text(json.dumps(res, ensure_ascii=False, indent=2, default=_json_default), encoding="utf-8")
    (out / "rapport.md").write_text(rapport_md(res), encoding="utf-8")
    if a.journal:
        jp = Path(a.journal); jp.parent.mkdir(parents=True, exist_ok=True)
        with jp.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"horodatage": res["meta"]["horodatage"], "moteur": VERSION_MOTEUR,
                                "audit": res["identification"].get("id_audit"), "bulletin": str(Path(a.bulletin).resolve()),
                                "referentiel": res["meta"]["referentiel"], "statut": res["conclusion"]["statut"],
                                "confiance": res["conclusion"]["confiance"]}, ensure_ascii=False) + "\n")
    print(json.dumps(res["conclusion"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
