"""Recette du moteur SPCA-CI — règles et bulletin FICTIFS (aucune valeur juridique réelle)."""
import copy
import json
import sys
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

W = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(W / "moteur"))
import spca_engine as E  # noqa: E402

FIX = Path(__file__).resolve().parent / "fixtures"
CFG = {"tolerance_ecart": 1, "familles_requises": ["MINIMUM", "CNPS", "CMU", "ITS"],
       "criticite_par_defaut": {"CT-A01": "P2", "CT-A02": "P3", "CT-A03": "P2"}}


def bulletin():
    return json.loads((FIX / "bulletin_test.json").read_text(encoding="utf-8"))


def run(b, regles_dir=FIX / "regles", cfg=CFG):
    regles, ign = E.charger_regles(Path(regles_dir))
    return E.Audit(b, regles, ign, cfg).executer()


def ctrl(res, code, contient=""):
    return [c for c in res["controles"] if c["code"] == code and contient in c["element"]]


class TestMoteur(unittest.TestCase):
    def test_temporalite_version_de_regle(self):
        res = run(bulletin())  # période 2025-06 -> T-CNPS v2 (6 %), pas v1 (5 %)
        self.assertIn("T-CNPS v2", res["meta"]["referentiel"])
        self.assertNotIn("T-CNPS v1", res["meta"]["referentiel"])
        c = ctrl(res, "CT-S01", "salariale")[0]
        self.assertEqual(c["statut"], "ANOMALIE")
        self.assertEqual(c["attendu"], Decimal(15000))
        self.assertEqual(c["ecart"], Decimal(-2500))

    def test_regle_historique_appliquee_a_paie_ancienne(self):
        b = bulletin(); b["audit"]["periode"] = "2024-06"
        res = run(b)
        self.assertIn("T-CNPS v1", res["meta"]["referentiel"])
        self.assertEqual(ctrl(res, "CT-S01", "salariale")[0]["statut"], "CONFORME")

    def test_exclusion_assiette_et_patronal(self):
        res = run(bulletin())
        self.assertEqual(ctrl(res, "CT-S01", "patronale")[0]["statut"], "CONFORME")  # 250000 x 10 %
        self.assertEqual(res["reconstitution"]["assiette_cnps"], Decimal(250000))  # transport exclu

    def test_bareme_progressif(self):
        c = ctrl(run(bulletin()), "CT-F01")[0]
        self.assertEqual(c["attendu"], Decimal(15000))
        self.assertEqual(c["statut"], "CONFORME")

    def test_arithmetique_et_net(self):
        res = run(bulletin())
        self.assertEqual(ctrl(res, "CT-A01")[0]["statut"], "CONFORME")
        self.assertEqual(ctrl(res, "CT-A03")[0]["statut"], "CONFORME")
        self.assertEqual(res["reconstitution"]["net_theorique"], Decimal(228000))
        self.assertEqual(res["reconstitution"]["ecart_net"], Decimal(2500))

    def test_statut_non_conforme(self):
        res = run(bulletin())
        self.assertEqual(res["conclusion"]["statut"], "NON CONFORME")
        self.assertEqual(res["conclusion"]["P2"], 1)
        self.assertEqual(res["conclusion"]["confiance"], "ÉLEVÉ")

    def test_minimum_p1_declenche_escalade(self):
        b = bulletin(); b["rubriques"][0]["montant"] = 90000
        res = run(b)
        self.assertEqual(ctrl(res, "CT-J03")[0]["criticite"], "P1")
        self.assertEqual(res["conclusion"]["statut"], "ESCALADE REQUISE")
        self.assertTrue(any("P1" in e["motif"] for e in res["escalades"]))

    def test_brouillon_ignore(self):
        res = run(bulletin())
        self.assertTrue(any("T-BR" in g and "non validée" in g for g in res["regles_ignorees"]))

    def test_referentiel_vide_stop4(self):
        with tempfile.TemporaryDirectory() as d:
            res = run(bulletin(), d)
        self.assertIn("STOP 4", " ".join(res["conclusion"]["stops"]))
        self.assertEqual(res["conclusion"]["statut"], "AUDIT INCOMPLET")
        self.assertTrue(any(c["statut"] == E.MSG_REGLE for c in res["controles"]))

    def test_periode_et_juridiction(self):
        b = bulletin(); b["audit"]["periode"] = None; b["audit"]["juridiction"] = "FR"
        stops = " ".join(run(b)["conclusion"]["stops"])
        self.assertIn("STOP 2", stops); self.assertIn("STOP 3", stops)

    def test_rubrique_absente_non_controlable(self):
        b = bulletin(); b["rubriques"] = [r for r in b["rubriques"] if r["code"] != "CMU"]
        c = ctrl(run(b), "CT-S02")[0]
        self.assertEqual(c["statut"], E.MSG_INFO)

    def test_temps_partiel_minimum_non_quantifiable(self):
        b = bulletin(); b["salarie"]["taux_temps_travail"] = 50
        res = run(b)
        self.assertEqual(ctrl(res, "CT-J03")[0]["statut"], E.MSG_NQ)

    def test_confiance_faible(self):
        b = bulletin(); b["rubriques"][1]["confiance"] = 0.4
        self.assertEqual(run(b)["conclusion"]["confiance"], "FAIBLE")

    def test_rapport_sections_A_a_H(self):
        md = E.rapport_md(run(bulletin()))
        for s in ("## A.", "## B.", "## C.", "## D.", "## E.", "## F.", "## G.", "## H."):
            self.assertIn(s, md)
        self.assertIn("PROVISOIRE", md)

    def test_cli_ecrit_sorties_et_journal(self):
        with tempfile.TemporaryDirectory() as d:
            rc = E.main(["--bulletin", str(FIX / "bulletin_test.json"), "--referentiel", str(FIX / "regles"),
                         "--sortie", d, "--journal", str(Path(d) / "j.jsonl")])
            self.assertEqual(rc, 0)
            for f in ("resultat.json", "rapport.md", "j.jsonl"):
                self.assertTrue((Path(d) / f).exists(), f)


if __name__ == "__main__":
    unittest.main()
