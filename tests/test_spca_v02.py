"""Recette SPCA-CI v0.2 — règles réelles du Rules Registry SOLEX + dossiers et table SMC FICTIFS."""
import copy
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

W = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(W / "moteur"))
from spca.expr import RuleError, evaluate  # noqa: E402
from spca.pipeline import audit, load_config, persist  # noqa: E402

FIX = Path(__file__).resolve().parent / "fixtures"
BASE = json.loads((FIX / "audit_request_test.json").read_text(encoding="utf-8"))
CFG = load_config()


class Env:
    def __init__(self, with_smc=True):
        self.tmp = Path(tempfile.mkdtemp())
        shutil.copytree(W / "referentiel" / "PAYROLL_RULES", self.tmp / "PAYROLL_RULES")
        if with_smc:
            shutil.copy(FIX / "smc_fictif.json", self.tmp / "PAYROLL_RULES" / "tables" / "smc.json")


ENV = Env()
ENV_NOSMC = Env(with_smc=False)


def req(**chg):
    r = copy.deepcopy(BASE)["audit_request"]
    for path, val in chg.items():
        node = r
        keys = path.split("__")
        for k in keys[:-1]:
            node = node[int(k)] if isinstance(node, list) else node.setdefault(k, {})
        if val is DEL:
            node.pop(keys[-1], None) if isinstance(node, dict) else node.pop(int(keys[-1]))
        else:
            node[keys[-1]] = val
    return r


DEL = object()


def run(r=None, env=ENV):
    return audit(r or req(), env.tmp, CFG)


def ctrl(res, rule_id=None, name=None):
    for c in res["controls"]:
        if (rule_id and c["rule_id"] == rule_id) or (name and name in c["control_name"]):
            return c
    raise AssertionError(f"contrôle introuvable {rule_id or name}")


class TestBaseline(unittest.TestCase):
    def test_bulletin_conforme_sous_reserve(self):
        res = run()
        self.assertEqual(res["status"], "CONFORME SOUS RÉSERVE")  # ITS / mentions non déterminées
        for rid in ("CI-PAY-SMIG-001", "CI-PAY-SMC-001", "CI-PAY-ANC-001", "CI-PAY-TRANS-001", "CI-PAY-HS-015",
                    "CI-CNPS-RET-SAL-001", "CI-CNPS-RET-EMP-001", "CI-CNPS-PF-COT-001", "CI-CNPS-AM-COT-001", "CI-CNPS-ATMP-COT-001",
                    "CI-CMU-SAL-001", "CI-CMU-EMP-001"):
            self.assertEqual(ctrl(res, rid)["status"], "CONFORME", rid)
        self.assertEqual(ctrl(res, "CI-PAY-ANC-001")["expected_value"], 9600)   # 120 000 × 8 %
        self.assertEqual(ctrl(res, "CI-PAY-HS-015")["expected_value"], 3981)    # 150 000 / 173,33 × 1,15 × 4

    def test_familles_non_determinees_signalees(self):
        res = run()
        self.assertFalse(any(c["status"] == "RÈGLE APPLICABLE NON DÉTERMINÉE" for c in res["controls"]))
        rc = res["payroll_reconstruction"]
        self.assertEqual((rc["net_theoretical"], rc["net_difference"]), (162775, 0))  # 193 581 − 10 306 − 500 − 0 − 20 000

    def test_its_marie_2_enfants_ricf_absorbe(self):
        c = ctrl(run(), "CI-ITS-001")
        self.assertEqual((c["expected_value"], c["status"]), (0, "CONFORME"))   # 14 172,96 − RICF 22 000 (3 parts) < 0

    def test_its_celibataire_sans_enfant(self):
        res = run(req(employee__family_status__tax_status="célibataire", employee__family_status__tax_children=0))
        c = ctrl(res, "CI-ITS-001")
        self.assertEqual((c["expected_value"], c["difference"], c["error_code"]), (14173, -14173, "ITS-001"))  # (163 581 − 75 000) × 16 %

    def test_its_barème_multi_tranches(self):
        r = req(payroll__base_salary=1000000, payroll__gross_salary=1000000, payroll__tax_base=1000000)
        r["payroll"]["earnings"][0]["amount"] = 1000000
        r["payroll"]["bonuses"] = []; r["payroll"]["allowances"] = []; r["payroll"]["overtime"] = []
        r["payroll"]["taxes"][0]["amount"] = 170000
        c = ctrl(run(r), "CI-ITS-001")
        self.assertEqual((c["expected_value"], c["status"]), (170000, "CONFORME"))  # 26 400 + 117 600 + 48 000 − 22 000

    def test_its_parts_plafonnees_a_5(self):
        r = req(payroll__base_salary=1000000, payroll__gross_salary=1000000, employee__family_status__tax_children=8)
        r["payroll"]["earnings"][0]["amount"] = 1000000
        r["payroll"]["bonuses"] = []; r["payroll"]["allowances"] = []; r["payroll"]["overtime"] = []
        self.assertEqual(ctrl(run(r), "CI-ITS-001")["expected_value"], 148000)  # 192 000 − 44 000

    def test_its_situation_fiscale_manquante(self):
        r = req(employee__family_status__tax_status=DEL)
        self.assertTrue(ctrl(run(r), "CI-ITS-001")["status"].startswith("NON CONTRÔLABLE"))

    def test_revenu_imposable_pay_003(self):
        r = req(payroll__tax_base=150000)
        c = ctrl(run(r), name="Revenu imposable ITS déclaré vs recalculé")
        self.assertEqual((c["status"], c["error_code"], c["difference"]), ("NON_CONFORME", "PAY-003", -13581))

    def test_its_exemple_note_dgi_veuf_3_enfants(self):
        r = req(payroll__base_salary=1000000, payroll__gross_salary=1000000, employee__family_status__tax_status="veuf",
                employee__family_status__tax_children=3)
        r["payroll"]["earnings"][0]["amount"] = 1000000
        r["payroll"]["bonuses"] = []; r["payroll"]["allowances"] = []; r["payroll"]["overtime"] = []
        self.assertEqual(ctrl(run(r), "CI-ITS-001")["expected_value"], 164500)  # note DGI 00026 p. 4 : 192 000 − 27 500 (3,5 parts)

    def test_contribution_employeur(self):
        c = ctrl(run(), "CI-ITS-CE-001")
        self.assertEqual((c["expected_value"], c["status"]), (4580, "CONFORME"))   # 163 581 × 2,8 %
        c = ctrl(run(req(employee__expatriate=True)), "CI-ITS-CE-001")
        self.assertEqual((c["expected_value"], c["error_code"]), (19630, "ITS-CE-001"))  # × 12 %

    def test_rbi_panier_imposable_its(self):
        r = req(); r["payroll"]["bonuses"].append({"type": "panier_bonus", "label": "Panier", "amount": 5000, "quantity": 2})
        c = ctrl(run(r), name="Revenu imposable ITS déclaré vs recalculé")
        self.assertEqual((c["expected_value"], c["difference"], c["status"]), (168581, -5000, "NON_CONFORME"))  # imposable en ITS

    def test_rbi_frais_emploi_justifies_sous_limite(self):
        r = req(); r["payroll"]["allowances"].append({"type": "mission_expenses", "label": "Frais de mission", "amount": 10000, "justification_doc": "OM-12"})
        c = ctrl(run(r), name="Revenu imposable ITS déclaré vs recalculé")
        self.assertEqual((c["expected_value"], c["status"]), (163581, "CONFORME"))  # 10 000 ≤ 10 % × 173 581

    def test_rbi_frais_non_justifies_tax_e006(self):
        r = req(); r["payroll"]["allowances"].append({"type": "mission_expenses", "label": "Frais de mission", "amount": 10000})
        c = ctrl(run(r), name="Revenu imposable ITS déclaré vs recalculé")
        self.assertEqual((c["expected_value"], c["error_code"]), (173581, "TAX-E006"))

    def test_rbi_frais_au_dela_10pct_tax_e015(self):
        r = req(); r["payroll"]["allowances"].append({"type": "mission_expenses", "label": "Frais de mission", "amount": 30000, "justification_doc": "OM-12"})
        c = ctrl(run(r), name="Revenu imposable ITS déclaré vs recalculé")
        self.assertAlmostEqual(c["expected_value"], 174222.9)   # 163 581 + 30 000 − 10 % × (223 581 − 30 000 transport exonéré)
        self.assertEqual(c["error_code"], "TAX-E015")

    def test_rbi_cotisations_deduites_tax_e013(self):
        c = ctrl(run(req(payroll__tax_base=152775)), name="Revenu imposable ITS déclaré vs recalculé")
        self.assertEqual((c["error_code"], c["difference"]), ("TAX-E013", -10806))  # 163 581 − 10 306 − 500

    def test_rbi_restauration_tax_e009(self):
        r = req(); r["payroll"]["benefits_in_kind"] = [{"type": "meal_benefit", "label": "Restauration", "amount": 40000}]
        c = ctrl(run(r), name="Revenu imposable ITS déclaré vs recalculé")
        self.assertEqual((c["expected_value"], c["error_code"]), (173581, "TAX-E009"))

    def test_rbi_indemnite_licenciement_moitie(self):
        r = req(); r["payroll"]["allowances"].append({"type": "severance_pay", "label": "Indemnité de licenciement", "amount": 545000})
        res = run(r)
        c = ctrl(res, name="Revenu imposable ITS déclaré vs recalculé")
        self.assertEqual(c["expected_value"], 436081)                      # 163 581 + 545 000 × 50 %
        self.assertIn("HUM-012", c["human_flags"])

    def test_rbi_retraite_complementaire_double_limite(self):
        r = req(); r["payroll"]["contributions"].append({"type": "complementary_pension_employer", "label": "Retraite complémentaire",
                                                         "amount": 0, "employer_amount": 50000})
        c = ctrl(run(r), name="Revenu imposable ITS déclaré vs recalculé")
        self.assertAlmostEqual(c["expected_value"], 197222.9)              # 163 581 + 50 000 − min(50 000, 16 358,1, 320 000)
        self.assertEqual(c["error_code"], "TAX-E004")

    def test_transport_its_30000_partout(self):
        r = req(employer__location="Korhogo", payroll__allowances__0__amount=25000)
        res = run(r)
        self.assertEqual(ctrl(res, name="Revenu imposable ITS")["expected_value"], 163581)       # ITS : 25 000 ≤ 30 000 exonéré
        self.assertEqual(ctrl(res, name="Assiette CNPS déclarée")["expected_value"], 168581)    # CNPS : 25 000 − 20 000 réintégré

    def test_ce_indemnite_depart_totalite(self):
        r = req(); r["payroll"]["allowances"].append({"type": "severance_pay", "label": "Indemnité de licenciement", "amount": 545000})
        res = run(r)
        self.assertEqual(ctrl(res, name="Revenu imposable ITS")["expected_value"], 436081)  # salarié : moitié
        self.assertEqual(ctrl(res, "CI-ITS-CE-001")["expected_value"], 19840)            # employeur : (163 581 + 545 000) × 2,8 %

    def test_indemnite_retraite_tolerance_smig(self):
        r = req(); r["payroll"]["allowances"].append({"type": "retirement_pay", "label": "Indemnité de départ à la retraite", "amount": 70000})
        self.assertEqual(ctrl(run(r), name="Revenu imposable ITS")["expected_value"], 163581)  # ≤ SMIG : négligée (note 01224)

    def test_nourriture_gratuite_plafond_30000(self):
        r = req(); r["payroll"]["benefits_in_kind"] = [{"type": "food_benefit", "label": "Repas fournis", "amount": 35000}]
        c = ctrl(run(r), name="Revenu imposable ITS")
        self.assertEqual((c["expected_value"], c["error_code"]), (168581, "TAX-E009"))
        self.assertIn("01536", c["legal_reference"])

    def test_smc_reel_commerce_cat4(self):
        r = req(employer__sector="Commerce, distribution, négoce et professions libérales", employee__job_group="EMPLOYES")
        c = ctrl(run(r, ENV_NOSMC), "CI-PAY-SMC-001")
        self.assertEqual((c["expected_value"], c["status"]), (99506, "CONFORME"))        # barème 2023 : 89 645 × 1,11
        r = req(employer__sector="COMMERCE", payroll__base_salary=95000); r["payroll"]["earnings"][0]["amount"] = 95000
        c = ctrl(run(r, ENV_NOSMC), "CI-PAY-SMC-001")
        self.assertEqual((c["status"], c["difference"]), ("NON_CONFORME", -4506))

    def test_smc_nettoyage_salubrite(self):
        r = req(employer__sector="Nettoyage et salubrité", employee__category="5", employee__job_group="EMPLOYES")
        self.assertEqual(ctrl(run(r, ENV_NOSMC), "CI-PAY-SMC-001")["expected_value"], 110206)     # 98 398 × 1,12
        r = req(employer__sector="NETTOYAGE_SALUBRITE", employee__category="5", employee__job_group="OUVRIERS")
        self.assertEqual(ctrl(run(r, ENV_NOSMC), "CI-PAY-SMC-001")["expected_value"], 110238)     # 636 F/h × 173,33 h

    def test_smc_reel_ambiguite_groupe(self):
        r = req(employer__sector="INDUSTRIE_MECANIQUE_ALIMENTAIRE_CHIMIQUE_TRANSPORT", employee__category="2")
        res = run(r, ENV_NOSMC)
        self.assertTrue(any("HUM-007" in str(e) for e in res["human_escalations"]) or
                        ctrl(res, "CI-PAY-SMC-001")["status"].startswith(("NON CONTRÔLABLE", "RÈGLE")))
        r = req(employer__sector="INDUSTRIE_MECANIQUE_ALIMENTAIRE_CHIMIQUE_TRANSPORT", employee__category="2", employee__job_group="OUVRIERS")
        self.assertEqual(ctrl(run(r, ENV_NOSMC), "CI-PAY-SMC-001")["expected_value"], 77825)   # 449 F/h × 173,33 h

    def test_conges_ct_25_2_ordonnance_2021(self):
        r = req(); r["leave_data"] = {"acquired_days": 26.4, "service_months": 12, "children_under_21": 2}
        c = ctrl(run(r), "CI-LEAVE-001")
        self.assertEqual((c["rule_version"], c["expected_value"], c["status"]), (2, 31.4, "NON_CONFORME"))  # 26,4 + 1 (ancienneté ≥ 5 ans) + 2 × 2 enfants
        r["leave_data"]["acquired_days"] = 31.4
        self.assertEqual(ctrl(run(r), "CI-LEAVE-001")["status"], "CONFORME")

    def test_conges_v1_avant_ordonnance(self):
        r = req(audit__payroll_period="2021-06"); r["leave_data"] = {"acquired_days": 26.4, "service_months": 12, "children_under_21": 2}
        c = ctrl(run(r), "CI-LEAVE-001")
        self.assertEqual((c["rule_version"], c["status"]), (1, "CONFORME"))

    def test_conges_bascule_au_24_janvier_2022(self):
        r = req(audit__payroll_period="2022-01"); r["leave_data"] = {"acquired_days": 26.4, "service_months": 12, "children_under_21": 2}
        self.assertEqual(ctrl(run(r), "CI-LEAVE-001")["rule_version"], 2)   # période se terminant le 31/01/2022

    def test_prescription_biennale(self):
        res = run(req(audit__payroll_period="2024-06"))
        self.assertTrue(any(c["control_name"] == "Prescription des rappels de salaire" for c in res["controls"]))
        self.assertFalse(any(c["control_name"] == "Prescription des rappels de salaire" for c in run()["controls"]))

    def test_mentions_art46_conformes(self):
        c = ctrl(run(), "CI-PAY-MENTIONS-001")
        self.assertEqual(c["status"], "CONFORME")
        self.assertIn("en nature", c["finding"])          # 7° nature sans objet (aucun avantage en nature)
        self.assertIn("Centrale des bilans", c["finding"])  # 13° sans objet (employeur non inscrit)

    def test_mention_absente_p4(self):
        r = req(); r["payslip_mentions"]["cnps_contribution_number"]["value"] = False
        c = ctrl(run(r), "CI-PAY-MENTIONS-001")
        self.assertEqual((c["status"], c["severity"], c["error_code"]), ("NON_CONFORME", "P4", "MENT-001"))
        self.assertIn("12°", c["finding"])

    def test_mentions_non_verifiees(self):
        r = req(); r.pop("payslip_mentions")
        self.assertTrue(ctrl(run(r), "CI-PAY-MENTIONS-001")["status"].startswith("NON CONTRÔLABLE"))
        r = req(employer__centrale_des_bilans=DEL)
        c = ctrl(run(r), "CI-PAY-MENTIONS-001")
        self.assertIn("condition invérifiable", c["finding"])

    def test_mention_hs_conditionnelle(self):
        r = req(); r["payroll"]["overtime"] = []; r["payslip_mentions"].pop("overtime")
        self.assertEqual(ctrl(run(r), "CI-PAY-MENTIONS-001")["status"], "CONFORME")

    def test_plafonds_cnps(self):
        res = run()
        self.assertEqual(ctrl(res, "CI-CNPS-PF-COT-001")["expected_value"], 3750)   # 75 000 × 5 %
        self.assertEqual(ctrl(res, "CI-CNPS-AM-COT-001")["expected_value"], 563)    # 75 000 × 0,75 %
        self.assertEqual(ctrl(res, "CI-CNPS-ATMP-COT-001")["expected_value"], 1500) # 75 000 × 2 %
        c = ctrl(res, "CI-CNPS-RET-SAL-001")
        self.assertFalse(any("CNPS_RET_PLAFOND" in x or "CNPS_RET_PLANCHER" in x for x in c["reserves"]))

    def test_exemple_matrice_4_200_000(self):
        r = req(payroll__base_salary=4200000, payroll__social_base=4200000, payroll__gross_salary=4200000)
        r["payroll"]["earnings"][0]["amount"] = 4200000
        r["payroll"]["bonuses"] = []; r["payroll"]["allowances"] = []; r["payroll"]["overtime"] = []
        r["payroll"]["contributions"][0].update({"base": 4200000, "rate": 6.3, "employer_rate": 7.7,
                                                 "amount": 264600, "employer_amount": 323400})  # 14 % sur 4,2 M
        res = run(r)
        sal, emp = ctrl(res, "CI-CNPS-RET-SAL-001"), ctrl(res, "CI-CNPS-RET-EMP-001")
        self.assertEqual((sal["expected_value"], emp["expected_value"]), (212625, 259875))
        self.assertEqual((sal["status"], emp["status"]), ("NON_CONFORME", "NON_CONFORME"))
        self.assertTrue(any(c["error_code"] == "CNPS-001" for c in res["controls"]))  # base retraite > plafond
        self.assertEqual(ctrl(res, "CI-CNPS-PF-COT-001")["expected_value"], 3750)

    def test_cmu_conjoint_et_enfants(self):
        r = req(employee__family_status__cmu_spouse_covered=True, employee__family_status__cmu_children_covered=2)
        c = ctrl(run(r), "CI-CMU-SAL-001")
        self.assertEqual((c["expected_value"], c["difference"], c["error_code"]), (2000, -1500, "CMU-002"))  # 4 × 500

    def test_cmu_au_dela_de_6_enfants(self):
        res = run(req(employee__family_status__cmu_spouse_covered=True, employee__family_status__cmu_children_covered=8))
        self.assertEqual(ctrl(res, "CI-CMU-SAL-001")["expected_value"], 6000)  # 8 × 500 + 2 × 1 000
        self.assertEqual(ctrl(res, "CI-CMU-EMP-001")["expected_value"], 4000)  # 8 × 500

    def test_cmu_donnees_manquantes(self):
        r = req(employee__family_status__cmu_children_covered=DEL)
        self.assertTrue(ctrl(run(r), "CI-CMU-SAL-001")["status"].startswith("NON CONTRÔLABLE"))

    def test_taux_errone_cnps_005(self):
        r = req(); r["payroll"]["contributions"][0]["rate"] = 6
        self.assertTrue(any(c["error_code"] == "CNPS-005" for c in run(r)["controls"]))

    def test_assiette_pay_001_p1(self):
        c = ctrl(run(), name="Assiette CNPS déclarée vs recalculée")
        self.assertEqual(c["status"], "CONFORME")                         # transport Abidjan 30 000 = plafond
        r = req(); r["payroll"]["social_base"]["value"] = 150000           # ancienneté + HS exclues à tort
        res = run(r)
        c = ctrl(res, name="Assiette CNPS déclarée vs recalculée")
        self.assertEqual((c["status"], c["error_code"], c["difference"], c["severity"]), ("NON_CONFORME", "PAY-001", -13581, "P1"))
        self.assertEqual(res["status"], "ESCALADE REQUISE")

    def test_transport_excedent_reintegre(self):
        r = req(employer__location="Bouaké", payroll__allowances__0__amount=30000)
        c = ctrl(run(r), name="Assiette CNPS déclarée vs recalculée")
        self.assertEqual(c["expected_value"], 169581)                     # 163 581 + (30 000 − 24 000)
        r = req(employer__location=DEL)
        c = ctrl(run(r), name="Assiette CNPS déclarée vs recalculée")
        self.assertTrue(any("par défaut" in x for x in c["reserves"]))

    def test_panier_exclusion_plafonnee(self):
        r = req(); r["payroll"]["bonuses"].append({"type": "panier_bonus", "label": "Panier", "amount": 5000, "quantity": 2})
        c = ctrl(run(r), name="Assiette CNPS déclarée vs recalculée")
        self.assertAlmostEqual(c["expected_value"], 165984.8)               # 163 581 + (5 000 − 2 × 3 × 432,70)

    def test_score_conformite(self):
        cs = run()["compliance_score"]
        self.assertEqual((cs["score"], cs["qualification"]), (100.0, "Conforme"))
        r = req(); r["payroll"]["bonuses"] = []
        self.assertLess(run(r)["compliance_score"]["score"], 95)

    def test_trace_complete(self):
        t = ctrl(run(), "CI-PAY-ANC-001")["trace"][0]
        for k in ("formula", "inputs", "rounding", "result"):
            self.assertIn(k, t)
        self.assertIn("SMC", t["inputs"])


class TestAnomalies(unittest.TestCase):
    def test_smig_p1_escalade(self):
        res = run(req(payroll__base_salary=70000, payroll__earnings__0__amount=70000))
        c = ctrl(res, "CI-PAY-SMIG-001")
        self.assertEqual((c["status"], c["severity"]), ("NON_CONFORME", "P1"))
        self.assertEqual(res["status"], "ESCALADE REQUISE")
        self.assertTrue(any(e["escalation_type"] == "P1" and "transmission client" in e["blocked_actions"] for e in res["human_escalations"]))

    def test_prime_anciennete_absente_rappel(self):
        r = req(); r["payroll"]["bonuses"] = []
        res = run(r)
        c = ctrl(res, "CI-PAY-ANC-001")
        self.assertEqual((c["status"], c["difference"], c["severity"]), ("NON_CONFORME", -9600, "P2"))
        self.assertEqual(res["financial_summary"]["rappel_potentiel_salarie"], 9600)

    def test_transport_bouake(self):
        res = run(req(employer__location="Bouaké", payroll__allowances__0__amount=20000))
        c = ctrl(res, "CI-PAY-TRANS-001")
        self.assertEqual((c["expected_value"], c["difference"]), (24000, -4000))

    def test_cnps_ecart(self):
        r = req(); r["payroll"]["contributions"][0]["amount"] = 9000
        c = ctrl(run(r), "CI-CNPS-RET-SAL-001")
        self.assertEqual((c["status"], c["difference"]), ("NON_CONFORME", -1306))

    def test_licenciement_bareme_tranches(self):
        r = req(termination={"type": "licenciement", "smm12": 200000})
        r["payroll"]["earnings"].append({"type": "severance_pay", "label": "Indemnité de licenciement", "amount": 500000})
        c = ctrl(run(r), "CI-TERM-LIC-001")
        self.assertEqual(c["expected_value"], 545000)  # 200 000 × (5 × 30 % + 3,5 × 35 %)
        self.assertEqual(c["status"], "NON_CONFORME")

    def test_preavis_decret_2026(self):
        r = req(termination={"type": "licenciement", "smm12": 200000, "notice_not_worked": True, "monthly_reference": 193581})
        c = ctrl(run(r), "CI-TERM-PREAVIS-001")
        self.assertEqual(c["expected_value"], 387162)  # cat. 4, 8,5 ans → 2 mois

    def test_retenue_disciplinaire_sans_fondement(self):
        r = req(); r["payroll"]["deductions"] = [{"type": "disciplinary_deduction", "label": "Retenue disciplinaire", "amount": 15000}]
        res = run(r)
        self.assertTrue(any(e["escalation_type"] == "HUM-004" for e in res["human_escalations"]))

    def test_incoherence_contrat(self):
        res = run(req(contract_data={"base_salary": 180000}))
        self.assertTrue(any(e["escalation_type"] == "HUM-003" for e in res["human_escalations"]))


class TestTemporaliteEtLimites(unittest.TestCase):
    def test_paie_2024_regles_non_retroactives(self):
        res = run(req(audit__payroll_period="2024-06"))
        self.assertTrue(any("CI-PAY-HS-015" in x and "hors période" in x for x in res["rules_excluded"]))
        self.assertEqual(ctrl(res, "CI-CNPS-RET-SAL-001")["status"], "CONFORME")   # taux CNPS en vigueur depuis 2023
        self.assertEqual(ctrl(res, "CI-PAY-SMIG-001")["status"], "CONFORME")

    def test_sans_table_smc_et_sans_convention(self):
        res = run(req(employer__collective_agreement=DEL), ENV_NOSMC)
        self.assertTrue(ctrl(res, "CI-PAY-SMC-001")["status"].startswith("NON CONTRÔLABLE"))
        self.assertTrue(any(e["escalation_type"] == "HUM-009" for e in res["human_escalations"]))

    def test_temps_partiel(self):
        res = run(req(employee__working_time_ratio=50))
        c = ctrl(res, "CI-PAY-SMIG-001")
        self.assertEqual(c["status"], "ÉCART NON QUANTIFIABLE EN L'ÉTAT")
        self.assertTrue(any(e["escalation_type"] == "HUM-010" for e in res["human_escalations"]))

    def test_stops(self):
        self.assertIn("STOP 1", " ".join(run(req(documents={}))["stops"]))
        res = run(req(audit__payroll_period=DEL, audit__jurisdiction="FR"))
        s = " ".join(res["stops"])
        self.assertIn("STOP 2", s); self.assertIn("STOP 3", s)
        self.assertEqual(res["status"], "AUDIT INCOMPLET")

    def test_confiance_faible(self):
        r = req(); r["payroll"]["bonuses"][0]["confidence"] = 0.5
        res = run(r)
        self.assertTrue(any(e["escalation_type"] == "HUM-011" for e in res["human_escalations"]))

    def test_regles_incompletes_rejetees(self):
        self.assertTrue(any("CI-CNPS-AF-001" in x for x in run()["registry_rejected"]))

    def test_expression_securisee(self):
        with self.assertRaises(RuleError):
            evaluate("__import__('os').system('dir')", {}, {})


class TestSorties(unittest.TestCase):
    def test_output_contract_et_rapport(self):
        res = run()
        for k in ("audit_id", "status", "confidence", "employee", "payroll_period", "applicable_context", "controls",
                  "payroll_reconstruction", "financial_summary", "risk_summary", "corrective_actions", "human_escalations",
                  "sources", "evidence", "audit_log"):
            self.assertIn(k, res)
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            persist(res, d / "out", d / "j.jsonl", d / "esc")
            md = (d / "out" / "rapport.md").read_text(encoding="utf-8")
            for s in "ABCDEFGH":
                self.assertIn(f"## {s}.", md)
            self.assertTrue((d / "out" / "rapport.docx").exists())
            self.assertTrue((d / "j.jsonl").exists())

    def test_escalades_jamais_ecrasees(self):
        res = run(req(payroll__base_salary=70000, payroll__earnings__0__amount=70000))
        with tempfile.TemporaryDirectory() as d:
            q = Path(d)
            persist(res, q / "o", None, q / "esc")
            f = sorted((q / "esc").glob("*.json"))[0]
            f.write_text('{"decision": "VALIDÉ PAR EXPERT"}', encoding="utf-8")
            persist(res, q / "o", None, q / "esc")
            self.assertIn("VALIDÉ PAR EXPERT", f.read_text(encoding="utf-8"))

    def test_chaine_de_preuve(self):
        r = req(); r["payroll"]["bonuses"] = []
        ev = run(r)["evidence"][0]
        for k in ("document", "data", "rule", "calculation", "finding", "risk", "recommendation"):
            self.assertIn(k, ev)


if __name__ == "__main__":
    unittest.main()
