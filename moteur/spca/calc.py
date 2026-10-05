"""Module 5 — Payroll Calculation Engine.

Exécute les formules du registre de manière déterministe avec trace complète :
variable → base → taux → formule → arrondi → résultat → règle source.
"""
from __future__ import annotations

from decimal import Decimal, ROUND_FLOOR

from .common import D, arrondir, fmt
from .expr import MissingInput, evaluate


class Recorder(dict):
    """Dictionnaire qui mémorise les variables lues par une formule (pour la trace)."""

    def __init__(self, base):
        super().__init__(base)
        self.used = {}

    def __getitem__(self, k):
        v = super().__getitem__(k)
        self.used[k] = v
        return v


class CalcEnv:
    def __init__(self, lines: list, var: dict, param_meta: dict, tables: dict | None = None):
        self.tables = tables or {}
        self.lines = lines
        self.var = var
        self.param_meta = param_meta
        self.reserves: list[str] = []
        self.calls: list[str] = []
        self.touched: set[str] = set()

    # -- accès aux lignes de paie
    def _sel(self, types):
        types = [types] if isinstance(types, str) else list(types)
        self.touched.update(types)
        return [l for l in self.lines if l["type"] in types]

    def amount(self, types):
        ls = [l for l in self._sel(types) if l["amount"] is not None]
        if not ls:
            raise MissingInput(f"rubrique:{types}")
        v = sum((l["amount"] for l in ls), Decimal(0))
        self.calls.append(f"montant({types}) = {fmt(v)}")
        return v

    def qty(self, types):
        ls = [l for l in self._sel(types) if l["quantity"] is not None]
        if not ls:
            raise MissingInput(f"quantité:{types}")
        v = sum((l["quantity"] for l in ls), Decimal(0))
        self.calls.append(f"quantité({types}) = {fmt(v)}")
        return v

    def employer(self, types):
        ls = [l for l in self._sel(types) if l["employer_amount"] is not None]
        if not ls:
            raise MissingInput(f"part_patronale:{types}")
        v = sum((l["employer_amount"] for l in ls), Decimal(0))
        self.calls.append(f"part_patronale({types}) = {fmt(v)}")
        return v

    def present(self, types):
        return any(l["amount"] is not None for l in self._sel(types))

    def has_array(self, arr):
        return any(l["array"] == arr and l["amount"] is not None for l in self.lines)

    def has_nature(self, nature):
        return any(l["nature"] == nature and l["amount"] is not None for l in self.lines)

    def sum_nature(self, nature):
        return sum((l["amount"] for l in self.lines if l["nature"] == nature and l["amount"] is not None), Decimal(0))

    # -- paramètres optionnels (plafond/plancher) : jamais inventés, réserve si absents
    def plafonner(self, x, pid):
        p = self.var.get(pid)
        if p is None:
            self.reserves.append(f"Plafond {pid} non paramétré pour la période — calcul sans plafonnement, à confirmer")
            return x
        r = min(Decimal(x), Decimal(str(p)))
        self.calls.append(f"plafond {pid} = {fmt(p)} → {fmt(r)}")
        return r

    def plancher(self, x, pid):
        p = self.var.get(pid)
        if p is None:
            self.reserves.append(f"Plancher {pid} non paramétré pour la période — calcul sans plancher, à confirmer")
            return x
        r = max(Decimal(x), Decimal(str(p)))
        self.calls.append(f"plancher {pid} = {fmt(p)} → {fmt(r)}")
        return r

    def compute_assiette(self, table_id: str = "cnps_assiette", employer: bool = False):
        """Assiette par matrice, composante par composante (CNPS : CPS art. 23 ; ITS : CGI art. 116 et 118).
        Traitements : inclus, exclu, exclu_plafonne (cap), formule (taxable = f(A)), conditionnel (condition → si_vrai / si_faux),
        frais_reels, frais_emploi (limite globale), retraite_comp (double plafond), a_qualifier.
        Retourne (montant, détail, à qualifier, réserves, plafonds manquants) ou None ; codes et drapeaux humains dans
        self.assiette_codes[table_id] / self.assiette_flags[table_id]."""
        tab = (self.tables or {}).get(table_id)
        if not tab:
            return None
        treat = tab.get("types", {})
        total, detail, a_qual, res, caps_missing = Decimal(0), [], [], [], []
        codes, flags, srcs = [], [], []
        frais_pool, frais_ref_excl, pension = [], Decimal(0), []
        fn = self.functions()

        def ev(expr, extra=None):
            v = dict(self.var); v.update(extra or {})
            return evaluate(expr, v, fn)

        def apply(l, t_, amt):
            nonlocal total, frais_ref_excl
            tr = t_["treatment"]
            if t_.get("source") and t_["source"] not in srcs:
                srcs.append(t_["source"])
            if t_.get("human_gate"):
                flags.append(("HUM-012", f"« {l['label']} » : {t_.get('human_gate_reason', 'qualification à valider par un expert')}"))
            if t_.get("requires_justification") and not l["justification"]:
                codes.append((t_["requires_justification"], f"« {l['label']} » sans justificatif"))
            if tr == "inclus":
                total += amt; detail.append(f"{l['type']} {fmt(amt)} → soumis")
            elif tr == "exclu":
                frais_ref_excl += amt if t_.get("hors_reference_10pct") else 0
                detail.append(f"{l['type']} {fmt(amt)} → exclu ({t_.get('motif', '')})")
            elif tr == "exclu_plafonne":
                try:
                    cap = Decimal(ev(t_["cap"]))
                except MissingInput as e:
                    caps_missing.append(l["label"])
                    res.append(f"Plafond d'exclusion de « {l['label']} » non calculable ({e.name}) — fraction soumise non déterminée")
                    detail.append(f"{l['type']} {fmt(amt)} → plafond d'exclusion non calculable")
                    return
                if t_.get("reserve_if_false") and not self.var.get(t_["reserve_if_false"]):
                    res.append(t_.get("reserve_text", "Plafond d'exclusion par défaut appliqué"))
                part = max(Decimal(0), amt - cap)
                if part > 0 and t_.get("code_if_exceeded"):
                    codes.append((t_["code_if_exceeded"], f"« {l['label']} » : {fmt(amt)} > plafond {fmt(cap)} — {fmt(part)} imposable"))
                frais_ref_excl += min(amt, cap) if t_.get("hors_reference_10pct") else 0
                total += part
                detail.append(f"{l['type']} {fmt(amt)} − exclusion min({fmt(amt)}, {fmt(cap)}) → soumis {fmt(part)}")
            elif tr == "formule":
                try:
                    part = Decimal(ev(t_["taxable"], {"A": amt}))
                except MissingInput as e:
                    caps_missing.append(l["label"]); res.append(f"Fraction imposable de « {l['label']} » non calculable ({e.name})")
                    return
                total += part
                detail.append(f"{l['type']} {fmt(amt)} → {t_['taxable']} = {fmt(part)} soumis ({t_.get('motif', '')})")
            elif tr == "conditionnel":
                try:
                    ok = ev(t_["condition"])
                except MissingInput as e:
                    a_qual.append(l["label"]); codes.append(("TAX-E001", f"« {l['label']} » : condition invérifiable ({e.name})"))
                    detail.append(f"{l['type']} {fmt(amt)} → condition invérifiable ({e.name})")
                    return
                apply(l, t_["si_vrai"] if ok else t_["si_faux"], amt)
            elif tr == "frais_reels":
                if l["justification"]:
                    detail.append(f"{l['type']} {fmt(amt)} → exclu (frais réels justifiés)")
                else:
                    total += amt; codes.append(("TAX-E006", f"« {l['label']} » : frais sans justificatif — réintégrés"))
                    detail.append(f"{l['type']} {fmt(amt)} → soumis (frais non justifiés)")
            elif tr == "frais_emploi":
                if l["justification"]:
                    frais_pool.append((l, amt))
                else:
                    total += amt; codes.append(("TAX-E006", f"« {l['label']} » : allocation pour frais sans justificatif — réintégrée"))
                    detail.append(f"{l['type']} {fmt(amt)} → soumis (frais d'emploi non justifiés)")
            elif tr == "retraite_comp":
                pension.append((l, amt))
            else:  # a_qualifier
                a_qual.append(l["label"]); codes.append(("TAX-E001" if table_id == "its_assiette" else "QUAL", f"« {l['label']} » non qualifiée"))
                detail.append(f"{l['type']} {fmt(amt)} → à qualifier juridiquement (non intégré)")

        for l in self.lines:
            t_ = treat.get(l["type"])
            if employer and t_ and t_.get("employer_override"):   # base des contributions employeurs
                t_ = t_["employer_override"]
            if l["nature"] not in ("gain", "avantage_nature") and not (t_ and t_["treatment"] == "retraite_comp"):
                continue
            if t_ is not None and t_["treatment"] == "retraite_comp":
                amt = l["employer_amount"]
            else:
                amt = l["amount"]
            if t_ is None and l["nature"] == "avantage_nature":
                t_ = {"treatment": "inclus"}
            if amt is None:
                if l["nature"] == "avantage_nature" and table_id == "its_assiette":
                    a_qual.append(l["label"]); codes.append(("TAX-E005", f"« {l['label']} » : avantage en nature non valorisé"))
                continue
            if l["nature"] == "avantage_nature" and l.get("employee_contribution"):
                amt = max(Decimal(0), amt - l["employee_contribution"])
                detail.append(f"{l['type']} : participation du salarié {fmt(l['employee_contribution'])} déduite")
            if t_ is None:
                a_qual.append(l["label"]); detail.append(f"{l['type']} {fmt(amt)} → non qualifié (exclu en attente)")
                if table_id == "its_assiette":
                    codes.append(("TAX-E001", f"« {l['label']} » ({l['type']}) : composante non qualifiée"))
                continue
            apply(l, t_, amt)

        rules = tab.get("global_rules", {})
        if frais_pool:
            fr = rules.get("frais_emploi")
            pool = sum((a for _, a in frais_pool), Decimal(0))
            cash = sum((l["amount"] for l in self.lines if l["nature"] == "gain" and l["amount"] is not None), Decimal(0))
            try:
                rate = Decimal(ev(fr["rate"]))
                ref = cash - frais_ref_excl
                cap = (ref * rate / 100)
                ex = min(pool, cap)
                total += pool - ex
                detail.append(f"frais d'emploi justifiés {fmt(pool)} ; limite {fmt(rate)} % × {fmt(ref)} = {fmt(cap)} → exonéré {fmt(ex)}, soumis {fmt(pool - ex)}")
                if pool > cap:
                    codes.append(("TAX-E015", f"Allocations pour frais d'emploi {fmt(pool)} > limite de {fmt(rate)} % ({fmt(cap)}) — {fmt(pool - cap)} imposable"))
                res.append(fr.get("reserve", ""))
            except (MissingInput, TypeError, KeyError):
                caps_missing += [l["label"] for l, _ in frais_pool]
                res.append("Limite globale des frais d'emploi non calculable")
        if pension:
            pr = rules.get("retraite_comp")
            contrib = sum((a for _, a in pension), Decimal(0))
            cash_taxable = total - sum((l["amount"] or 0 for l in self.lines if l["nature"] == "avantage_nature"), Decimal(0))
            try:
                c1 = cash_taxable * Decimal(ev(pr["rate"])) / 100
                c2 = Decimal(ev(pr["cap"]))
                ex = min(contrib, c1, c2)
                total += contrib - ex
                detail.append(f"retraite/prévoyance complémentaire patronale {fmt(contrib)} ; exonéré min({fmt(contrib)}, {fmt(c1)}, {fmt(c2)}) = {fmt(ex)} → soumis {fmt(contrib - ex)}")
                if contrib > ex:
                    codes.append(("TAX-E004", f"Cotisations complémentaires {fmt(contrib)} > double limite ({fmt(ex)}) — {fmt(contrib - ex)} imposable"))
            except (MissingInput, TypeError, KeyError):
                caps_missing.append("retraite complémentaire"); res.append("Double limite des cotisations complémentaires non calculable")
        if a_qual:
            res.append("Éléments à qualifier avant intégration à l'assiette : " + ", ".join(a_qual))
        if not hasattr(self, "assiette_codes"):
            self.assiette_codes, self.assiette_flags = {}, {}
        if not employer:
            self.assiette_codes[table_id], self.assiette_flags[table_id] = codes, flags
            if not hasattr(self, "assiette_sources"):
                self.assiette_sources = {}
            self.assiette_sources[table_id] = srcs
        return total, detail, a_qual, [r for r in res if r], caps_missing

    def assiette_cnps(self):
        """Assiette CNPS recalculée par la matrice d'assiette ; à défaut, reprise du bulletin avec réserve."""
        r = self.compute_assiette()
        if r is not None:
            v, detail, _, res, _ = r
            self.reserves += res
            self.calls.append(f"assiette sociale brute recalculée = {fmt(v)} [" + " ; ".join(detail) + "]")
            return v
        sb = self.var.get("social_base")
        if sb is not None:
            self.reserves.append("Assiette CNPS reprise du bulletin : matrice d'assiette (table cnps_assiette) non disponible")
            self.calls.append(f"assiette CNPS (bulletin) = {fmt(sb)}")
            return sb
        raise MissingInput("assiette CNPS (bulletin) ou table cnps_assiette")

    def assiette_fiscale(self):
        """Revenu imposable ITS recalculé par la matrice its_assiette ; à défaut, base imposable du bulletin avec réserve."""
        r = self.compute_assiette("its_assiette")
        if r is not None:
            v, detail, _, res, _ = r
            self.reserves += res
            self.calls.append(f"revenu imposable recalculé = {fmt(v)} [" + " ; ".join(detail) + "]")
            return v
        tb = self.var.get("tax_base")
        if tb is not None:
            self.reserves.append("Revenu imposable repris du bulletin : matrice its_assiette non disponible")
            self.calls.append(f"revenu imposable (bulletin) = {fmt(tb)}")
            return tb
        raise MissingInput("revenu imposable (bulletin) ou table its_assiette")

    def assiette_fiscale_employeur(self):
        """Base des contributions à la charge des employeurs : revenu imposable sans les allègements propres au salarié
        (indemnités de départ retenues pour leur totalité — note DGI n°01224 du 12 avril 2022, §2.2)."""
        r = self.compute_assiette("its_assiette", employer=True)
        if r is None:
            raise MissingInput("table its_assiette")
        v, detail, _, res, _ = r
        self.reserves += [x for x in res if x not in self.reserves]
        self.calls.append(f"base contributions employeur = {fmt(v)} [" + " ; ".join(detail) + "]")
        return v

    def tiers(self, x, *bornes_taux):
        """Barème progressif par tranches : tiers(x, borne1, taux1, borne2, taux2, …) → Σ part de tranche × taux %."""
        x, total, prev = Decimal(x), Decimal(0), Decimal(0)
        it = list(bornes_taux)
        for i in range(0, len(it), 2):
            borne, taux = Decimal(it[i]), Decimal(it[i + 1])
            part = max(Decimal(0), min(x, borne) - prev)
            if part > 0:
                total += part * taux / 100
                self.calls.append(f"tranche {fmt(prev)}–{fmt(borne)} : {fmt(part)} × {taux} % = {fmt(part * taux / 100)}")
            prev = borne
        return total

    def functions(self):
        return {"amount": self.amount, "qty": self.qty, "employer": self.employer, "present": self.present,
                "has_array": self.has_array, "has_nature": self.has_nature,
                "sum_nature": self.sum_nature, "plafonner": self.plafonner, "plancher": self.plancher,
                "assiette_cnps": self.assiette_cnps, "assiette_fiscale": self.assiette_fiscale,
                "assiette_fiscale_employeur": self.assiette_fiscale_employeur, "tiers": self.tiers,
                "min": min, "max": max, "abs": abs,
                "contient": lambda a, b: str(b).upper() in str(a).upper(),
                "floor": lambda x: Decimal(x).to_integral_value(rounding=ROUND_FLOOR),
                "round2": lambda x: Decimal(x).quantize(Decimal("0.01"))}

    def run(self, expr: str, rounding: str | None = None):
        rec = Recorder(self.var)
        self.calls = []
        v = evaluate(expr, rec, self.functions())
        raw = v
        if rounding and isinstance(v, Decimal):
            v = arrondir(v, rounding)
        used = {k: rec.used[k] for k in rec.used}
        return v, {"formula": expr, "inputs": {k: (fmt(x) if isinstance(x, Decimal) else x) for k, x in used.items()},
                   "steps": list(self.calls), "raw_result": fmt(raw) if isinstance(raw, Decimal) else raw,
                   "rounding": rounding or "aucun", "result": fmt(v) if isinstance(v, Decimal) else v}


def reconstruction(lines: list, var: dict) -> dict:
    gains = [l for l in lines if l["nature"] == "gain" and l["amount"] is not None]
    gross = sum((l["amount"] for l in gains), Decimal(0)) if gains else None
    ret = {n: sum((l["amount"] for l in lines if l["nature"] == n and l["amount"] is not None), Decimal(0))
           for n in ("retenue_salariale", "retenue_fiscale", "autre_retenue")}
    return {"gross_reported": var.get("gross_salary"), "gross_recalculated": gross,
            "employee_social_reported": ret["retenue_salariale"], "tax_reported": ret["retenue_fiscale"],
            "other_deductions": ret["autre_retenue"],
            "benefits_in_kind": sum((l["amount"] for l in lines if l["nature"] == "avantage_nature" and l["amount"] is not None), Decimal(0)),
            "net_reported": var.get("net_salary"),
            "net_arithmetic": (gross - sum(ret.values())) if gross is not None else None}
