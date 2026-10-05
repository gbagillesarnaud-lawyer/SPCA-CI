SOLEX PAYROLL COMPLIANCE AUDITOR — CI
RULES REGISTRY — DROITS DU SALARIÉ, FORMULES DE CALCUL ET MINIMA CATÉGORIELS
Version de référence : septembre 2026

I. VARIABLES FONDAMENTALES À PARAMÉTRER DANS HERMES
SMIG_M = SMIG mensuel
SMIG_H = SMIG horaire

SMC = salaire minimum catégoriel mensuel du salarié
SMC_H = salaire minimum catégoriel horaire

SB = salaire de base contractuel
SR = salaire réel
SMM12 = salaire global mensuel moyen des 12 derniers mois

ANC = ancienneté en années révolues
MOIS_ANC = mois supplémentaires d'ancienneté

N_MOIS = nombre de mois de service
N_JOURS_CONGE = nombre de jours calendaires de congé
Au 29 septembre 2026 :
SMIG_M = 75 000 FCFA
Pour une durée mensuelle conventionnelle de 173,33 heures :
SMIG_H ≈ 75 000 / 173,33
SMIG_H ≈ 432,70 FCFA
Le SMIG de 75 000 FCFA résulte du décret n°2022-986 du 21 décembre 2022, applicable depuis le 1er janvier 2023.
II. PRIME D'ANCIENNETÉ
Règle
La prime d'ancienneté est calculée sur le salaire minimum de la catégorie de classement, et non nécessairement sur le salaire réel ou contractuel.
Taux :
ANC < 2 ans      → 0 %
ANC = 2 ans      → 2 %
ANC = 3 ans      → 3 %
ANC = 4 ans      → 4 %
...
ANC = 25 ans     → 25 %
ANC > 25 ans     → plafond = 25 %
La Convention collective prévoit 2 % après deux années d'ancienneté, puis 1 % supplémentaire par année de service jusqu'à la 25e année incluse.
Formule
TAUX_ANC =
0                           si ANC < 2
min(ANC %, 25 %)            si ANC ≥ 2
Puis :
PRIME_ANCIENNETE = SMC × TAUX_ANC
Exemple
SMC = 150 000 FCFA
Ancienneté = 8 ans
Taux = 8 %
Prime = 150 000 × 8 %
Prime = 12 000 FCFA
Rule ID
CI-PAY-ANC-001

III. PRIME / GRATIFICATION DE FIN D'ANNÉE
Règle
La gratification annuelle minimale est égale à :
75 % du salaire minimum conventionnel mensuel de la catégorie
La Convention collective prévoit une allocation minimale de 3/4 du salaire minimum conventionnel mensuel. Pour un salarié entré ou sorti en cours d'année, elle est proratisée au temps de service.
Salarié présent toute l'année
GRATIFICATION = SMC × 75 %
Salarié présent une partie de l'année
GRATIFICATION_PRORATA =
SMC × 75 % × N_MOIS_SERVICE / 12
Ou, si l'entreprise dispose d'un décompte journalier fiable :
GRATIFICATION_PRORATA =
GRATIFICATION_ANNUELLE × durée_service / durée_année
Rule ID
CI-PAY-GRAT-001

IV. PRIME DE PANIER
Le salarié bénéficie de la prime notamment lorsqu'il accomplit :
•	6 heures consécutives de travail de nuit ;
•	au moins 10 heures de jour prolongées d'au moins une heure dans la période de nuit ;
•	une séance ininterrompue de 10 heures dans la journée.
Formule opérationnelle
PRIME_PANIER = 3 × SMIG_H
Avec le SMIG actuel :
PRIME_PANIER ≈ 3 × 432,70
PRIME_PANIER ≈ 1 298,10 FCFA
par situation ouvrant droit à la prime.
La CNPS reprend également la limite de 3 fois le SMIG horaire pour la prime de panier.
Rule ID
CI-PAY-PAN-001

V. PRIME / INDEMNITÉ DE TRANSPORT
Les minima actuellement applicables issus de l'arrêté n°2020-012/MEPS/CAB sont :
Localité	Minimum mensuel
District autonome d'Abidjan	30 000 FCFA
Bouaké	24 000 FCFA
Autres localités	20 000 FCFA
L'arrêté est applicable depuis le 1er août 2019.
Formule
TRANSPORT_MIN =
30 000 si ABIDJAN
24 000 si BOUAKE
20 000 sinon
Contrôle :
ECART_TRANSPORT =
TRANSPORT_MIN - TRANSPORT_VERSE
si le résultat est positif.
Pour les déplacements professionnels fréquents et habituels réalisés pour le compte de l'employeur :
INDEMNITE_TRANSPORT_PRO =
FRAIS_REELS_OCCASIONNES
La Convention collective prévoit que ces frais correspondent aux frais occasionnés par le déplacement.
Rule ID
CI-PAY-TRANS-001

VI. INDEMNITÉ D'EXPATRIATION INTERNATIONALE
Bénéficiaire : salarié recruté hors de Côte d'Ivoire et déplacé de sa résidence habituelle par l'employeur.
Formule
INDEMNITE_EXPATRIATION = SB × 40 %
La Convention collective fixe cette indemnité à 4/10 du salaire de base contractuel.
Rule ID
CI-PAY-EXPAT-001

VII. INDEMNITÉ D'ÉLOIGNEMENT / EXPATRIATION INTERNE OU RÉGIONALE
Lorsqu'un salarié recruté en Côte d'Ivoire est envoyé exécuter son contrat hors de sa résidence habituelle située à 500 km ou plus du lieu d'emploi :
N = nombre de tranches entières de 500 km
Puis :
INDEMNITE = SB × 5 % × N
Exemple :
Distance = 1 500 km
N = 3
Indemnité = SB × 15 %
Rule ID
CI-PAY-ELOIGN-001

VIII. INDEMNITÉ D'ÉQUIPEMENT
Pour un travailleur recruté en Côte d'Ivoire et déplacé hors du territoire par l'employeur :
Célibataire
INDEMNITE_EQUIPEMENT = 600 × SMIG_H
Marié
INDEMNITE_EQUIPEMENT = 700 × SMIG_H
Par enfant
SUPPLEMENT_ENFANT = 100 × SMIG_H
Avec un SMIG horaire indicatif de 432,70 FCFA :
Célibataire ≈ 259 620 FCFA
Marié ≈ 302 890 FCFA
Par enfant ≈ 43 270 FCFA
La Convention collective prévoit ces multiples du SMIG horaire.
Rule ID
CI-PAY-EQUIP-001

IX. INDEMNITÉ DE DÉPLACEMENT / MISSION
Pour les catégories auxquelles le barème forfaitaire conventionnel s'applique :
Un repas principal hors lieu habituel
INDEMNITE = 4 × SMC_H
Deux repas principaux
INDEMNITE = 8 × SMC_H
Deux repas + couchage
INDEMNITE = 12 × SMC_H
Pour plusieurs jours :
INDEMNITE_MISSION =
MULTIPLE × SMC_H × NOMBRE_JOURS
La Convention collective fixe respectivement les coefficients 4, 8 et 12.
Pour certains cadres et catégories supérieures, le remboursement s'effectue sur justificatifs selon les règles conventionnelles applicables.
Rule ID
CI-PAY-DEPL-001

X. HEURES SUPPLÉMENTAIRES
Depuis le décret n°2024-898 du 16 octobre 2024, la durée normale est notamment de 40 heures par semaine dans les entreprises non agricoles et 48 heures dans les entreprises agricoles, sous réserve des régimes particuliers.
Il faut d'abord calculer le salaire horaire réel :
TAUX_HORAIRE = rémunération servant de base / heures normales
Puis :
41e à 46e heure
HS_15 = TAUX_HORAIRE × 1,15 × NOMBRE_HS
Au-delà de la 46e heure
HS_50 = TAUX_HORAIRE × 1,50 × NOMBRE_HS
Travail supplémentaire de nuit
HS_NUIT = TAUX_HORAIRE × 1,75 × NOMBRE_HEURES
Dimanche ou jour férié de jour
HS_DIM_FERIE_JOUR =
TAUX_HORAIRE × 1,75 × NOMBRE_HEURES
Dimanche ou jour férié de nuit
HS_DIM_FERIE_NUIT =
TAUX_HORAIRE × 2,00 × NOMBRE_HEURES
Ces minima de majoration résultent du décret actuellement applicable.
Rule IDs
CI-PAY-HS-015
CI-PAY-HS-050
CI-PAY-HS-NIGHT
CI-PAY-HS-SUN
CI-PAY-HS-SUN-NIGHT

XI. DROIT AUX CONGÉS PAYÉS
Le Code du travail prévoit :
DROIT_CONGE = 2,2 jours ouvrables × mois de service effectif
Pour 12 mois :
12 × 2,2 = 26,4 jours ouvrables
auxquels s'ajoutent les jours supplémentaires prévus par l'ancienneté.
Majoration pour ancienneté
≥ 5 ans  → +1 jour
≥ 10 ans → +2 jours
≥ 15 ans → +3 jours
≥ 20 ans → +5 jours
≥ 25 ans → +7 jours
≥ 30 ans → +8 jours
Rule ID
CI-LEAVE-001

XII. ALLOCATION DE CONGÉ PAYÉ
Assiette
Inclure notamment :
•	salaire brut ;
•	primes ;
•	commissions ;
•	pourboires comptabilisés ;
•	gratification ;
•	heures supplémentaires ;
•	avantages en nature.
Exclure les remboursements de frais tels que :
•	transport ;
•	panier ;
•	déplacement.
La Convention collective précise cette assiette.
Formule
REMUNERATION_MOYENNE =
TOTAL_REMUNERATION_REFERENCE / NOMBRE_MOIS_REFERENCE
Puis :
SALAIRE_MOYEN_JOURNALIER =
REMUNERATION_MOYENNE / 30
Et :
ALLOCATION_CONGE =
SALAIRE_MOYEN_JOURNALIER × NOMBRE_JOURS_CALENDAIRES_CONGE
Rule ID
CI-LEAVE-PAY-001

XIII. INDEMNITÉ COMPENSATRICE DE CONGÉ
En cas de rupture avant jouissance des congés acquis :
ICC =
SALAIRE_MOYEN_JOURNALIER
× JOURS_CALENDAIRES_DE_CONGE_ACQUIS_NON_PRIS
La Convention collective prévoit que l'indemnité compensatrice est calculée sur les mêmes bases que l'allocation de congé.
Rule ID
CI-LEAVE-COMP-001

XIV. INDEMNITÉ DE LICENCIEMENT
Le texte de référence actuellement applicable est le décret n°2017-210 du 30 mars 2017.
Salaire de référence
SMM12 =
TOTAL DES REMUNERATIONS CONTREPARTIE DU TRAVAIL SUR 12 MOIS / 12
Exclure les remboursements de frais.
Barème
Années 1 à 5
INDEMNITE_1_5 =
SMM12 × 30 % × ancienneté correspondante
Années 6 à 10
INDEMNITE_6_10 =
SMM12 × 35 % × ancienneté correspondante
Au-delà de 10 ans
INDEMNITE_11_PLUS =
SMM12 × 40 % × ancienneté correspondante
Total
INDEMNITE_LICENCIEMENT =
INDEMNITE_1_5
+ INDEMNITE_6_10
+ INDEMNITE_11_PLUS
Les fractions d'année sont retenues en mois.
Exemple : 12 ans
SMM12 × 30 % × 5
+
SMM12 × 35 % × 5
+
SMM12 × 40 % × 2
Rule ID
CI-TERM-LIC-001

XV. INDEMNITÉ DE DÉPART À LA RETRAITE
Le décret n°2017-210 prévoit le même mécanisme que pour l'indemnité de licenciement.
Donc :
INDEMNITE_RETRAITE =
SMM12 × 30 % × années_1_5
+
SMM12 × 35 % × années_6_10
+
SMM12 × 40 % × années_11_plus
Rule ID
CI-TERM-RET-001

XVI. INDEMNITÉ COMPENSATRICE DE PRÉAVIS
En 2026, le décret n°2026-198 du 15 avril 2026 a remplacé l'ancien régime général du préavis.
Exemples pour les salariés mensualisés des cinq premières catégories :
ancienneté < 6 ans       → 1 mois
6 ans à < 11 ans         → 2 mois
11 ans à < 16 ans        → 3 mois
≥ 16 ans                 → 4 mois
Pour les catégories 6 et supérieures :
≤ 16 ans → 3 mois
> 16 ans → 4 mois
Lorsque le préavis n'est pas exécuté alors qu'il est dû :
INDEMNITE_PREAVIS =
REMUNERATION_QUE_LE_SALARIE_AURAIT_PERCUE
PENDANT_LA_DUREE_DU_PREAVIS
Dans un cas mensuel simple :
INDEMNITE_PREAVIS =
REMUNERATION_MENSUELLE_DE_REFERENCE
× NOMBRE_MOIS_PREAVIS
Les conventions ou contrats plus favorables doivent prévaloir.
Rule ID
CI-TERM-PREAVIS-001

XVII. INDEMNITÉ JOURNALIÈRE DE MATERNITÉ — CNPS
La femme salariée bénéficie normalement de 14 semaines :
6 semaines avant accouchement
+
8 semaines après accouchement
avec possibilité de prolongation médicale jusqu'à 21 jours.
La CNPS indique que le salaire de référence correspond au salaire brut du mois précédant le congé, hors éléments exceptionnels, remboursements de frais et avantages en nature.
Pour le moteur :
SALAIRE_REFERENCE_MATERNITE =
SALAIRE_BRUT_REGULIER_MOIS_PRECEDENT
- ELEMENTS_EXCEPTIONNELS
- REMBOURSEMENTS_FRAIS
- AVANTAGES_NATURE
Puis :
IJ_JOURNALIERE =
SALAIRE_REFERENCE_MATERNITE / diviseur réglementaire applicable
et :
IJ_TOTALE =
IJ_JOURNALIERE × JOURS_INDEMNISABLES
Le moteur devra récupérer le diviseur CNPS applicable de la table réglementaire avant calcul définitif.
Rule ID
CI-CNPS-MAT-IJ-001

XVIII. ALLOCATIONS PRÉNATALES CNPS
Montants forfaitaires actuellement publiés par la CNPS :
1er examen : 3 000 FCFA
2e examen  : 6 000 FCFA
3e examen  : 4 500 FCFA
Total maximal :
ALLOC_PRENATALE = 13 500 FCFA
sous réserve du respect des conditions médicales.
Rule ID
CI-CNPS-PRENAT-001

XIX. ALLOCATION DE MATERNITÉ CNPS
Montant :
18 000 FCFA par enfant
fractionné :
9 000 FCFA à la naissance
4 500 FCFA à 6 mois
4 500 FCFA à 12 mois
Pour des naissances multiples :
ALLOCATION =
18 000 × nombre_enfants
Rule ID
CI-CNPS-MAT-ALLOC-001

XX. ALLOCATION AU FOYER DU TRAVAILLEUR
Montant :
18 000 FCFA par enfant éligible
pour chacun des trois premiers enfants répondant aux conditions réglementaires.
ALLOCATION_FOYER =
18 000 × nombre_enfants_eligibles
avec :
nombre_enfants_eligibles ≤ 3
Rule ID
CI-CNPS-FOYER-001

XXI. ALLOCATIONS FAMILIALES CNPS
Montant actuellement publié :
5 000 FCFA par enfant et par mois
payable trimestriellement.
Formule mensuelle
ALLOC_FAMILIALE_M =
5 000 × NOMBRE_ENFANTS_ELIGIBLES
Formule trimestrielle
ALLOC_FAMILIALE_T =
5 000 × 3 × NOMBRE_ENFANTS_ELIGIBLES
Rule ID
CI-CNPS-AF-001

XXII. ACCIDENT DU TRAVAIL / MALADIE PROFESSIONNELLE — RENTE
Salaire utile
SALAIRE_UTILE =
salaire annuel de référence
corrigé selon le plancher et les plafonds réglementaires
Taux utile
Si IPP ≤ 50 % :
TAUX_UTILE = IPP / 2
Si IPP > 50 % :
TAUX_UTILE =
25 % + ((IPP - 50 %) × 1,5)
Exemple IPP = 70 % :
25 % + (20 % × 1,5)
= 55 %
Rente annuelle
RENTE_ATMP =
SALAIRE_UTILE × TAUX_UTILE
La CNPS publie cette méthode.
Assistance d'une tierce personne
En cas d'incapacité totale remplissant les conditions :
MAJORATION_TIERCE_PERSONNE =
RENTE × 40 %
sous réserve du minimum réglementaire applicable.
Rule ID
CI-CNPS-ATMP-RENTE-001


XXIII. COTISATION RETRAITE CNPS — UTILE AU CONTRÔLE DES BULLETINS
Taux total :
14 %
réparti entre :
Employeur = 7,7 %
Salarié   = 6,3 %
Part salariale
CNPS_RETRAITE_SALARIE =
ASSIETTE_RETRAITE × 6,3 %
Part patronale
CNPS_RETRAITE_EMPLOYEUR =
ASSIETTE_RETRAITE × 7,7 %
La base doit respecter le plancher et le plafond réglementaires applicables à la période auditée.
Rule IDs
CI-CNPS-RET-SAL-001
CI-CNPS-RET-EMP-001

XXIV. AUTRES COTISATIONS PATRONALES CNPS
La CNPS publie les taux suivants :
Prestations familiales = 5 %
Assurance maternité    = 0,75 %
AT/MP                   = 2 % à 5 %
Le taux AT/MP dépend du secteur ou niveau de risque.
Formules :
PF = assiette_PF × 5 %
MATERNITE = assiette_AM × 0,75 %
ATMP = assiette_ATMP × taux_ATMP
Rule IDs
CI-CNPS-PF-COT-001
CI-CNPS-AM-COT-001
CI-CNPS-ATMP-COT-001

XXV. NOUVEAU BARÈME DES SALAIRES MINIMA CATÉGORIELS
1. Principe
Le texte de référence est :
Arrêté n°0050/MEPS/CAB du 19 mai 2023 portant application du barème des salaires minima catégoriels conventionnels.
Il produit ses effets au 1er janvier 2023 et remplace le barème de 2015 contraire.
La règle générale pour Hermes est :
NOUVEAU_SMC =
ANCIEN_SMC_2015 × (1 + TAUX_REVALORISATION)
avec contrôle supplémentaire :
NOUVEAU_SMC ≥ SMIG applicable
sauf règle sectorielle spéciale prévue par l'arrêté.

XXVI. MATRICE DE REVALORISATION DES MINIMA CATÉGORIELS
N°	Secteur	Revalorisation applicable depuis 01/01/2023
1	Banque	18 %
2	Assurance	18 %
3	Agriculture, élevage, foresterie, haras, marais salants, entretien jardins	11 %
4	Production agricole	11 %, avec règles particulières ouvriers
5	Pétrole — distribution	10 %
6	Pétrole — exploration / production	10 %
7	Industrie polygraphique	12 %
8	Industrie mécanique, alimentaire, corps gras, chimique, transport et autres emplois concernés	12,5 %
9	Industrie du bois	12 %
10	Commerce, distribution, négoce, professions libérales	11 %
11	Gens de maison	14 %, sauf catégorie 2 : 18 %
12	Hôtellerie / tourisme	12 %
13	Industrie textile	13 %
14	Dockers	régime différencié
15	Transformation du thon	18 %
16	BTP et activités connexes	15 %
17	Sécurité privée	catégories 2-3 : 20 % ; catégories 4 à 11 : 9 %
18	Industrie du sucre	régime spécial
19	Instituts de recherche	12,5 % avec règles particulières
20	Transport de fonds et valeurs	10 %
21	Auxiliaires du transport	9 %
22	Transport aérien	14 %
23	Nettoyage et salubrité	12 %
24	Secteur maritime / pêche	régime différencié
25	Éducation / formation confessionnelle	10 %
26	Mines et carrières	12,5 %
27	Enseignement privé laïc	catégories spécifiques : 29 % / 24 %
Le détail sectoriel est celui de l'article 1er de l'arrêté de 2023.
XXVII. RÈGLES SPÉCIALES DU BARÈME
Gens de maison
Catégorie 2 :
SMC_NEW = SMC_OLD × 1,18

Autres catégories :
SMC_NEW = SMC_OLD × 1,14

Sécurité privée
Catégories 2 et 3 :
SMC_NEW = SMC_OLD × 1,20
Catégories 4 à 11 :
SMC_NEW = SMC_OLD × 1,09

Dockers
Catégories 2, 3, 4 → +18 %
Catégorie 5          → +17 %
Catégorie 6A         → +15 %
À partir de 6B       → +9 %

Secteur maritime — novices pont et machine
Catégorie 4  → +21 %
Catégorie 5  → +18 %
Catégorie 6  → +16 %
Catégorie 7  → +14 %
Catégorie 8  → +12 %
Catégories 9-10 → +9 %
Pour les élèves officiers pont et machine :
+9 %

Enseignement privé laïc
Référence : ancien barème sectoriel 1992.
Catégorie 2 :
OLD_SMC × 1,29
Catégories 3 à 6 :
OLD_SMC × 1,24

XXVIII. RÈGLE HERMES POUR LE SALAIRE CATÉGORIEL
Le moteur ne doit jamais utiliser :
fonction → salaire catégoriel supposé
Il doit suivre :
SECTEUR
↓
CONVENTION / BARÈME APPLICABLE
↓
EMPLOI
↓
CATÉGORIE
↓
BARÈME HISTORIQUE DE BASE
↓
TAUX DE REVALORISATION
↓
SMC APPLICABLE
↓
COMPARAISON AVEC SMIG
Formule :
SMC_EXPECTED =
max(
    SMC_BASE × COEFFICIENT_REVALORISATION,
    PLANCHER_LEGAL_APPLICABLE
)
sous réserve des régimes sectoriels spéciaux.

XXIX. IMPORTANT — CE QU'IL FAUT CHARGER DANS HERMES POUR LES MONTANTS EXACTS
L'arrêté de 2023 fixe principalement les taux de revalorisation par secteur. Pour que l'agent retourne automatiquement le montant exact en FCFA correspondant à chaque catégorie, SOLEX doit intégrer une table de référence contenant :
SECTOR_ID
SECTOR_NAME
CATEGORY
JOB_CLASS
OLD_SMC
REVALUATION_RATE
NEW_SMC
EFFECTIVE_FROM
EFFECTIVE_TO
LEGAL_SOURCE
Exemple :
{
  "sector": "Commerce_Distribution_Negoce",
  "category": "X",
  "base_smc": 100000,
  "revaluation_rate": 0.11,
  "effective_from": "2023-01-01",
  "new_smc": 111000
}
Le calcul est alors :
100 000 × 1,11 = 111 000 FCFA

XXX. CONTRÔLE AUTOMATIQUE DU SALAIRE MINIMUM
Le moteur doit réaliser deux tests différents.
Test 1 — SMIG
IF salaire_legal_base < 75 000
→ NON CONFORME
→ P1
si le SMIG est applicable au cas examiné.
Test 2 — Minimum catégoriel
IF SALAIRE_BASE_REEL < SMC_APPLICABLE
→ NON CONFORME
→ RAPPEL =
SMC_APPLICABLE - SALAIRE_BASE_REEL
La distinction entre SMIG et minimum catégoriel est essentielle pour SOLEX.
XXXI. STRUCTURE RULE ENGINE RECOMMANDÉE
Chaque formule doit être transformée dans Hermes en objet de ce type :
{
  "rule_id": "CI-PAY-ANC-001",
  "name": "Prime d'ancienneté",
  "category": "earnings",
  "jurisdiction": "CI",
  "effective_from": "1977-07-19",
  "inputs": [
    "seniority_years",
    "categorical_minimum_salary"
  ],
  "condition": "seniority_years >= 2",
  "formula": "categorical_minimum_salary * min(seniority_years,25)/100",
  "legal_source": "Convention Collective Interprofessionnelle",
  "article": "55",
  "risk_if_missing": "P2",
  "human_review": false
}

XXXII. ORDRE DE PRIORITÉ DES RÈGLES DANS L'AUDIT
Pour chaque salarié, SOLEX PAYROLL COMPLIANCE AUDITOR devra tester successivement :
01. SMIG
02. Salaire minimum catégoriel
03. Salaire contractuel
04. Prime d'ancienneté
05. Gratification
06. Transport
07. Panier
08. Expatriation
09. Équipement
10. Déplacement
11. Temps de travail
12. Heures supplémentaires
13. Congés acquis
14. Allocation de congé
15. Retenues
16. CNPS
17. CMU
18. Fiscalité
19. Net à payer
20. Indemnités de rupture
21. Préavis
22. Prestations sociales

XXXIII. PRINCIPE DE FIABILITÉ
Pour chaque formule, Hermes doit stocker :
RULE_ID
FORMULA
INPUTS
LEGAL_SOURCE
ARTICLE
EFFECTIVE_FROM
EFFECTIVE_TO
SECTOR
CATEGORY
LAST_VERIFIED
Aucune règle ne doit être calculée uniquement parce qu'elle existe dans le knowledge base.
Le moteur doit d'abord vérifier :
DATE BULLETIN
+
SECTEUR
+
CATÉGORIE
+
CONVENTION APPLICABLE
+
DATE D'EFFET RÈGLE
avant toute application.