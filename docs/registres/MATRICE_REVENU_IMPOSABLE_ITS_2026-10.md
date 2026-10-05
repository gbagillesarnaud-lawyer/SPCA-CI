Pour L’Agent SOLEX PAYROLL COMPLIANCE AUDITOR, je recommande de construire la matrice du revenu imposable ITS en deux couches, exactement comme pour le registre CNPS–CNAM :
1. PAYROLL_TAX_COMPONENT_RULES : L’Agent SOLEX PAYROLL COMPLIANCE AUDITOR qualifie chaque composante de paie comme imposable, exonérée ou partiellement exonérée.
2. ITS_CALCULATION_RULES : L’Agent SOLEX PAYROLL COMPLIANCE AUDITOR reconstitue ensuite le revenu brut imposable, applique le barème ITS et la RICF.
Le principe fiscal de départ est désormais très clair : le revenu brut imposable comprend le montant brut des traitements, indemnités, salaires, gratifications, heures supplémentaires et avantages en argent ou en nature, sauf ce qui bénéficie expressément d'une exonération.
I. Formule-mère à donner à L’Agent SOLEX PAYROLL COMPLIANCE AUDITOR
REVENU_BRUT_IMPOSABLE_ITS
=
Σ COMPOSANTES_IMPOSABLES_EN_NUMERAIRE
+
Σ VALEURS_IMPOSABLES_AVANTAGES_EN_NATURE
+
Σ FRACTIONS_IMPOSABLES_DES_COMPOSANTES_PARTIELLEMENT_EXONEREES
-
Σ EXONERATIONS_FISCALES_APPLICABLES
L’Agent SOLEX PAYROLL COMPLIANCE AUDITOR ne doit donc jamais partir de :
BRUT CNPS = REVENU FISCAL
ni de :
SALAIRE BRUT BULLETIN = REVENU IMPOSABLE
Le chemin doit être :
COMPOSANTE DE PAIE
        ↓
QUALIFICATION FISCALE
        ↓
CONDITION D'EXONÉRATION ?
        ↓
PLAFOND D'EXONÉRATION ?
        ↓
PREUVE REQUISE ?
        ↓
FRACTION IMPOSABLE
        ↓
REVENU BRUT IMPOSABLE ITS

II. Structure du PAYROLL_TAX_COMPONENT_RULES
Je retiendrais les colonnes suivantes, compatibles avec votre architecture L’Agent SOLEX PAYROLL COMPLIANCE AUDITOR :
Champ	Fonction
RULE_ID	Identifiant permanent de la règle
COMPONENT_CODE	Code de la composante de paie
COMPONENT_NAME	Libellé
CATEGORY	salaire / prime / indemnité / avantage / frais / rupture
DEFAULT_TAX_TREATMENT	TAXABLE / EXEMPT / PARTIAL / CONDITIONAL
INCLUSION_RULE	règle d'inclusion
EXEMPTION_RULE	règle d'exonération
EXEMPTION_LIMIT	plafond ou formule
TAXABLE_FORMULA	formule L’Agent SOLEX PAYROLL COMPLIANCE AUDITOR
LEGAL_SOURCE	source
LEGAL_ARTICLE	article/note
EFFECTIVE_FROM	date d'effet
EVIDENCE_REQUIRED	preuve
HUMAN_GATE	oui/non
ERROR_CODE	anomalie L’Agent SOLEX PAYROLL COMPLIANCE AUDITOR
SEVERITY	P1–P4
OUTPUT_VARIABLE	montant fiscal retenu
STATUS	VERIFIED / TO VERIFY
LAST_LEGAL_REVIEW	date de revue

III. MATRICE DU REVENU IMPOSABLE — RÉMUNÉRATIONS EN NUMÉRAIRE
Rule ID	Composante	Traitement ITS	Règle L’Agent SOLEX PAYROLL COMPLIANCE AUDITOR
CI-TAX-001	Salaire de base	100 % imposable	taxable = amount
CI-TAX-002	Rappel de salaire	100 % imposable	taxable = amount
CI-TAX-003	Sursalaire / complément salarial	100 % imposable	taxable = amount
CI-TAX-004	Heures supplémentaires	100 % imposable	taxable = amount
CI-TAX-005	Majoration travail de nuit	100 % imposable	taxable = amount
CI-TAX-006	Majoration dimanche / jour férié	100 % imposable	taxable = amount
CI-TAX-007	Prime d'ancienneté	100 % imposable	taxable = amount
CI-TAX-008	Gratification	100 % imposable	taxable = amount
CI-TAX-009	13e mois	100 % imposable	taxable = amount
CI-TAX-010	Prime de rendement	100 % imposable	taxable = amount
CI-TAX-011	Prime de performance	100 % imposable	taxable = amount
CI-TAX-012	Prime d'objectif	100 % imposable	taxable = amount
CI-TAX-013	Prime de fonction	100 % imposable	taxable = amount
CI-TAX-014	Prime de responsabilité	100 % imposable	taxable = amount
CI-TAX-015	Bonus	100 % imposable	taxable = amount
CI-TAX-016	Commission	100 % imposable	taxable = amount
CI-TAX-017	Prime exceptionnelle	100 % imposable par défaut	taxable = amount unless exemption_rule_id exists
CI-TAX-018	Indemnité de logement versée en espèces	100 % imposable	taxable = amount
CI-TAX-019	Indemnité de téléphone forfaitaire	Imposable par défaut	sauf qualification de frais professionnels prouvés
CI-TAX-020	Prime de panier	Imposable par défaut	sauf texte fiscal spécial applicable
CI-TAX-021	Indemnité de salissure	Imposable par défaut	sauf texte fiscal spécial applicable
CI-TAX-022	Prime de risque / pénibilité	100 % imposable par défaut	taxable = amount
CI-TAX-023	Prime d'expatriation	100 % imposable	taxable = amount
CI-TAX-024	Indemnité de déplacement non justifiée	Imposable	taxable = amount
La DGI précise que la base comprend les salaires, indemnités, gratifications, heures supplémentaires et tous les avantages en argent ou en nature non exonérés. DGI

IV. ALLOCATIONS SPÉCIALES POUR FRAIS D'EMPLOI
C'est ici que L’Agent SOLEX PAYROLL COMPLIANCE AUDITOR doit être particulièrement strict.
L'article 116 du CGI permet d'exonérer les allocations spéciales réellement destinées à couvrir des frais inhérents à la fonction ou à l'emploi, mais dans la limite de 10 % de la rémunération totale, indemnités comprises, hors avantages en nature. La DGI exige notamment que les dépenses soient professionnelles, spécifiques, exposées dans l'intérêt direct de l'employeur, justifiées et qu'elles ne fassent pas double emploi avec un remboursement réel. DGI
Règle-mère
SPECIAL_EXPENSE_ALLOWANCE_EXEMPT_LIMIT
=
10% × REFERENCE_CASH_REMUNERATION
avec :
REFERENCE_CASH_REMUNERATION
=
TOTAL REMUNERATION IN CASH
en excluant notamment de la base de calcul de cette limite :
•	indemnités à caractère familial ;
•	prime légale de transport exonérée ;
•	prise en charge du transport collectif ;
•	avantages en nature. DGI
Matrice
Rule ID	Frais	Traitement	Conditions
CI-TAX-FE-001	Frais de mission	Exonération conditionnelle	intérêt entreprise + justificatifs
CI-TAX-FE-002	Déplacement professionnel	Exonération conditionnelle	déplacement professionnel réel
CI-TAX-FE-003	Indemnité kilométrique professionnelle	Exonération conditionnelle	fonction nécessitant déplacements + preuve
CI-TAX-FE-004	Représentation	Exonération conditionnelle	inhérente à la fonction + preuve
CI-TAX-FE-005	Vêtements spéciaux professionnels	Exonération conditionnelle	indispensables à l'activité
CI-TAX-FE-006	Hébergement en mission	Exonération conditionnelle	mission professionnelle
CI-TAX-FE-007	Restauration en mission	Exonération conditionnelle	mission professionnelle
Formule L’Agent SOLEX PAYROLL COMPLIANCE AUDITOR :
IF
    expense_is_special = TRUE
AND business_interest = TRUE
AND actual_use_verified = TRUE
AND supporting_evidence = TRUE
AND no_duplicate_reimbursement = TRUE
THEN
    exempt =
        MIN(
            eligible_allowance,
            remaining_10_percent_exemption_capacity
        )
    taxable = amount - exempt
ELSE
    taxable = amount
La DGI précise également qu'une allocation forfaitaire ne doit pas être cumulée avec le remboursement réel des mêmes frais. DGI

V. PRIME DE TRANSPORT
La prime légale de transport bénéficie d'une exonération particulière distincte de la règle générale des 10 %.
La doctrine DGI actuelle retient une exonération jusqu'à 30 000 FCFA par mois et par salarié dans le régime visé. DGI
L’Agent SOLEX PAYROLL COMPLIANCE AUDITOR
RULE_ID = CI-TAX-TRANSPORT-001

EXEMPT_AMOUNT = MIN(TRANSPORT_ALLOWANCE, 30000)

TAXABLE_AMOUNT =
MAX(TRANSPORT_ALLOWANCE - 30000, 0)
Attention : les frais ordinaires domicile–travail constituent normalement des dépenses personnelles/professionnelles courantes du salarié ; l'exonération de la prime légale constitue donc une règle spécifique, et non l'application générale des frais d'emploi. DGI

VI. TRANSPORT COLLECTIF ORGANISÉ PAR L'EMPLOYEUR
Lorsque l'entreprise transporte son personnel au moyen de ses propres cars, la DGI considère en principe qu'il existe un avantage, calculé à partir des frais engagés, mais admet l'exonération à hauteur de 30 000 FCFA mensuels par salarié. DGI
TOTAL_BUS_COST =
FUEL
+ MAINTENANCE
+ INSURANCE
+ VEHICLE_TAXES
+ TECHNICAL_INSPECTION
+ OTHER_DIRECT_COSTS

EMPLOYEE_TRANSPORT_BENEFIT =
TOTAL_BUS_COST / BENEFICIARY_COUNT

EXEMPT =
MIN(EMPLOYEE_TRANSPORT_BENEFIT, 30000)

TAXABLE =
MAX(EMPLOYEE_TRANSPORT_BENEFIT - 30000, 0)

VII. RESTAURATION
Les dépenses supportées par l'employeur pour la restauration du salarié sont exonérées jusqu'à 30 000 FCFA par mois et par salarié. Si le service est fourni à l'extérieur de l'entreprise, la doctrine DGI exige notamment un contrat avec le prestataire et la preuve de l'effectivité de la dépense. DGI
EXEMPT_RESTAURATION =
MIN(RESTAURATION_VALUE, 30000)

TAXABLE_RESTAURATION =
MAX(RESTAURATION_VALUE - 30000, 0)
Statut L’Agent SOLEX PAYROLL COMPLIANCE AUDITOR :
IF external_restaurant = TRUE
AND contract_missing = TRUE
THEN HUMAN_GATE = TRUE
VIII. AVANTAGES EN NATURE
Le principe est :
AVANTAGE_EN_NATURE
→ IMPOSABLE
sauf exception expresse.
La DGI définit l'avantage en nature comme le bien ou la prestation supporté totalement ou partiellement par l'employeur pour le salarié et précise que le remboursement effectué par le salarié vient diminuer la valeur imposable. DGI
Formule
TAXABLE_BENEFIT =
MAX(
    GROSS_BENEFIT_VALUE
    - EMPLOYEE_REIMBURSEMENT
    - SPECIFIC_EXEMPTION,
    0
)

IX. MATRICE DES AVANTAGES EN NATURE
Rule ID	Avantage	Traitement
CI-TAX-AIN-001	Logement personnel	Imposable — valeur forfaitaire
CI-TAX-AIN-002	Mobilier	Imposable — valeur forfaitaire
CI-TAX-AIN-003	Électricité logement	Imposable — valeur forfaitaire
CI-TAX-AIN-004	Eau logement	Imposable — valeur forfaitaire
CI-TAX-AIN-005	Climatisation	Imposable — valeur forfaitaire
CI-TAX-AIN-006	Piscine	Imposable — valeur forfaitaire
CI-TAX-AIN-007	Gardien/domesticité	Imposable — valeur forfaitaire
CI-TAX-AIN-008	Jardinier	Imposable — valeur forfaitaire
CI-TAX-AIN-009	Cuisinier / gens de maison	Imposable — valeur forfaitaire
CI-TAX-AIN-010	Hôtel temporaire payé par employeur	Imposable à la valeur réelle
CI-TAX-AIN-011	Téléphone privé à domicile	Imposable à la valeur réelle
CI-TAX-AIN-012	Internet privé à domicile	Imposable à la valeur réelle
CI-TAX-AIN-013	Voyage congé salarié recruté localement	Imposable à la valeur réelle
CI-TAX-AIN-014	Gardiennage domicile par entreprise tierce	Imposable à la valeur réelle
CI-TAX-AIN-015	Travaux locatifs pris en charge	Imposable à la valeur réelle
CI-TAX-AIN-016	Produit/service employeur fourni gratuitement	Imposable à la valeur réelle
CI-TAX-AIN-017	Produit vendu au salarié sous prix client	Écart de prix imposable
Les avantages logement, mobilier, eau, électricité, climatisation, piscine et domesticité relèvent de l'évaluation forfaitaire prévue par l'arrêté du 7 novembre 1996 ; les autres avantages sont en principe évalués à leur valeur réelle. DGI
Important pour L’Agent SOLEX PAYROLL COMPLIANCE AUDITOR : les coefficients exacts de l'arrêté de 1996 doivent être placés dans un registre distinct :
AIN_VALUATION_RULES
et non codés en dur dans cette matrice tant que le texte primaire n'a pas été intégré au LEGAL_SOURCES_REGISTRY.

X. AVANTAGES EN NATURE NON IMPOSABLES
Véhicule de fonction ou de service
La DGI indique que le véhicule de fonction ou de service mis à disposition du salarié n'est pas considéré comme un avantage en nature imposable. DGI
CI-TAX-AIN-VEH-001

IF vehicle_type IN ["FUNCTION", "SERVICE"]
THEN taxable = 0
Il faudra toutefois distinguer un véritable véhicule de fonction/service d'un véhicule constituant en réalité un avantage personnel.
Logement d'astreinte
Non imposable lorsque :
•	il répond réellement à une nécessité de service ;
•	il permet au salarié d'intervenir rapidement ;
•	il ne constitue pas son domicile personnel. DGI
IF
    housing_type = "ON_CALL"
AND service_necessity = TRUE
AND personal_residence = FALSE
THEN taxable = 0
ELSE HUMAN_GATE
Voyage annuel de congé — expatrié
Les frais de transport pour congé annuel du salarié expatrié et de sa famille jusqu'au domicile d'origine sont traités par la DGI comme liés au coût de recrutement et non comme un supplément salarial imposable. DGI
IF expatriate_contract = TRUE
AND travel = annual_leave_home_travel
THEN taxable = 0
Pour le salarié recruté localement :
taxable = actual_cost
``` :chatgpt-content-reference{index="15"}


---

# XI. ALLOCATIONS FAMILIALES

Les allocations familiales bénéficiant d'une exonération légale doivent être sorties de la base ITS. La documentation DGI les cite parmi les revenus exonérés. :chatgpt-content-reference{index="16"}

```text
CI-TAX-FAMILY-001

IF benefit_is_statutory_family_allowance = TRUE
THEN taxable = 0
ELSE
    verify_legal_basis
L’Agent SOLEX PAYROLL COMPLIANCE AUDITOR ne doit surtout pas appliquer :
"libellé contient famille" → exonéré
La note DGI de juillet 2024 précise que les allocations d'assistance à la famille ne bénéficient de l'affranchissement que lorsque leur versement est prévu par un texte légal. DGI
XII. DÉPENSES DE SANTÉ ET ASSURANCE MALADIE
La documentation DGI identifie notamment comme exonérées certaines dépenses de santé engagées par l'entreprise ainsi que certaines sommes versées dans le cadre de contrats groupe d'assurance maladie ou mutuelles de santé du personnel. DGI
Pour L’Agent SOLEX PAYROLL COMPLIANCE AUDITOR :
IF health_benefit IN AUTHORIZED_EXEMPT_HEALTH_CATEGORY
AND statutory_conditions_met = TRUE
THEN taxable = 0
ELSE HUMAN_GATE
Je déconseille une règle générale :
toute dépense médicale = exonérée
car elle serait trop large.

XIII. CONTRAT D'APPRENTISSAGE
La documentation fiscale DGI prévoit une exonération des indemnités d'apprentissage :
•	pendant une durée maximale de deux ans ;
•	pour la fraction mensuelle ≤ 100 000 FCFA. DGI
IF apprenticeship_contract = TRUE
AND contract_duration <= 24_months
THEN
    exempt = MIN(amount, 100000)
    taxable = MAX(amount - 100000, 0)
ELSE
    taxable = amount

XIV. RETRAITE ET PRÉVOYANCE COMPLÉMENTAIRE
Les cotisations patronales aux organismes de retraite/prévoyance complémentaire sont affranchies d'ITS dans une double limite :
10% × rémunération mensuelle brute imposable hors avantages en nature
et :
320 000 FCFA
La fraction exonérée est donc :
EXEMPT_COMPLEMENTARY_PENSION =
MIN(
    CONTRIBUTION,
    10% × TAXABLE_GROSS_CASH_REMUNERATION,
    320000
)
et :
TAXABLE_EXCESS =
CONTRIBUTION - EXEMPT_COMPLEMENTARY_PENSION
La DGI a confirmé ce plafond après la réforme de 2023. DGI

XV. COTISATIONS SOCIALES SALARIALES OBLIGATOIRES
Pour L’Agent SOLEX PAYROLL COMPLIANCE AUDITOR, il faut absolument éviter de faire :
REVENU_IMPOSABLE =
BRUT - CNPS_SALARIE - CMU
La documentation actuelle définit le revenu brut imposable à partir de la rémunération brute et des avantages non exonérés ; elle ne pose pas une déduction générale des cotisations CNPS/CMU salariales pour déterminer cette base ITS. L'exonération expressément documentée concerne notamment certaines cotisations de retraite/prévoyance complémentaire dans les limites précitées. DGI
Donc :
CNPS_EMPLOYEE_DEDUCTION
→ NET PAY CALCULATION
≠ TAXABLE_INCOME_DEDUCTION
et de même pour la CMU, sauf règle fiscale expresse contraire à intégrer ultérieurement.

XVI. INDEMNITÉS DE LICENCIEMENT ET DE DÉPART
C'est une catégorie qui doit avoir son propre sous-moteur.
La doctrine DGI pose comme principe que les indemnités versées à l'occasion du départ définitif sont imposables, sauf notamment celles ayant le caractère de dommages-intérêts. DGI
Indemnité légale de licenciement
Si :
INDEMNITY <= SMIG
la doctrine administrative la néglige fiscalement.
taxable = 0
Si :
INDEMNITY > SMIG
la fraction imposable est :
TAXABLE = 50% × INDEMNITY
La DGI précise que l'indemnité de licenciement et l'indemnité de départ à la retraite sont soumises à l'impôt à hauteur de la moitié de leur montant dans ce régime. DGI
Préavis
INDEMNITE_PREAVIS
→ 100 % imposable
La doctrine la classe parmi les indemnités légales imposables. DGI
Départ à la retraite
TAXABLE =
50 % × LEGAL_RETIREMENT_INDEMNITY
sous les conditions prévues par la doctrine DGI. DGI
Dommages-intérêts
IF genuine_damages = TRUE
THEN taxable = 0
notamment lorsqu'ils indemnisent véritablement un préjudice. La DGI cite notamment les dommages-intérêts judiciaires et, sous conditions, certaines indemnités transactionnelles ou de départ négocié. DGI
Ici :
HUMAN_GATE = TRUE
doit être obligatoire.

XVII. FRAIS FUNÉRAIRES / SECOURS AU DÉCÈS
Les frais funéraires et indemnités assimilées versés à raison du décès d'un salarié ne sont pas imposables lorsqu'ils constituent, compte tenu de leur montant et de leurs conditions d'attribution, un véritable secours. DGI
IF payment_reason = "DEATH"
AND payment_nature = "GENUINE_RELIEF"
THEN taxable = 0
ELSE HUMAN_GATE

XVIII. PENSIONS ET RENTES — À TENIR DANS UN SOUS-REGISTRE
Ce n'est pas de la paie active, mais le moteur fiscal peut le prévoir.
Pour les pensions de retraite et rentes viagères :
MONTHLY_EXEMPTION = 320000
TAXABLE_PENSION =
MAX(GROSS_PENSION - 320000, 0)
``` :chatgpt-content-reference{index="28"}


Les rentes et indemnités temporaires attribuées aux victimes d'accidents du travail font également partie des revenus bénéficiant d'un traitement exonéré selon la documentation DGI. :chatgpt-content-reference{index="29"}

---

# XIX. MATRICE SYNTHÉTIQUE L’AGENT SOLEX PAYROLL COMPLIANCE AUDITOR

Voici la table centrale que je chargerais réellement dans le moteur :

| Component | Default | Exemption | Exempt limit | Taxable formula | Human Gate |
|---|---|---|---:|---|---|
| Salaire base | TAXABLE | — | 0 | `amount` | Non |
| HS | TAXABLE | — | 0 | `amount` | Non |
| Gratification | TAXABLE | — | 0 | `amount` | Non |
| Prime ancienneté | TAXABLE | — | 0 | `amount` | Non |
| Bonus / performance | TAXABLE | — | 0 | `amount` | Non |
| Prime fonction | TAXABLE | — | 0 | `amount` | Non |
| Transport légal | PARTIAL | spécifique | 30 000 | `MAX(A-30000,0)` | Non |
| Transport collectif | PARTIAL | spécifique | 30 000 | `MAX(V-30000,0)` | Oui si valorisation |
| Frais de mission | CONDITIONAL | art. 116 | limite globale 10 % | `A-exempt` | Oui si preuve absente |
| Frais professionnels spéciaux | CONDITIONAL | art. 116 | limite globale 10 % | `A-exempt` | Oui |
| Panier | TAXABLE défaut | — | 0 | `amount` | Oui si texte spécial invoqué |
| Salissure | TAXABLE défaut | — | 0 | `amount` | Oui si texte spécial invoqué |
| Restauration | PARTIAL | spécifique | 30 000 | `MAX(V-30000,0)` | Oui si externe sans pièces |
| Allocation familiale légale | EXEMPT | légale | totalité | `0` | Oui si nature incertaine |
| Logement personnel | TAXABLE | — | forfait | `AIN_VALUE` | Oui si valeur absente |
| Domesticité | TAXABLE | — | forfait | `AIN_VALUE` | Non après valorisation |
| Téléphone/internet domicile | TAXABLE | — | 0 | `actual_value` | Oui si usage professionnel invoqué |
| Véhicule fonction/service | EXEMPT | doctrine DGI | totalité | `0` | Oui si usage ambigu |
| Logement astreinte | CONDITIONAL_EXEMPT | nécessité service | totalité | `0 or value` | Oui |
| Voyage congé expatrié | EXEMPT | expatriation | totalité | `0` | Oui sur statut expatrié |
| Voyage congé local | TAXABLE | — | 0 | `actual_cost` | Non |
| Retraite complémentaire | PARTIAL | double plafond | MIN(10 %, 320k) | `excess` | Oui |
| Indemnité apprentissage | PARTIAL | ≤2 ans | 100 000/mois | `MAX(A-100000,0)` | Non |
| Préavis | TAXABLE | — | 0 | `amount` | Non |
| Licenciement | PARTIAL | doctrine DGI | règle SMIG/50 % | formule dédiée | Oui |
| Retraite départ | PARTIAL | doctrine DGI | 50 % | `amount*0.50` | Oui |
| Dommages-intérêts | EXEMPT conditionnel | préjudice réel | totalité | `0` | **Obligatoire** |

---

# XX. Formule finale du moteur

Je recommande à L’Agent SOLEX PAYROLL COMPLIANCE AUDITOR de calculer ainsi :

```text
CASH_TAXABLE =
Σ taxable_cash_components

AIN_TAXABLE =
Σ taxable_benefit_values

PARTIAL_COMPONENT_TAXABLE =
Σ taxable_portions_of_partial_exemptions

RBI =
CASH_TAXABLE
+ AIN_TAXABLE
+ PARTIAL_COMPONENT_TAXABLE
ou conceptuellement :
RBI
=
GROSS_REMUNERATION
+ TAXABLE_AIN
- VALID_EXEMPTIONS
mais la première formule, composante par composante, est plus sûre pour un auditeur IA.

XXI. Barème ITS à relier au registre
Une fois le RBI déterminé, L’Agent SOLEX PAYROLL COMPLIANCE AUDITOR appelle un autre registre, et non cette matrice :
ITS_BRACKETS
Le barème mensuel actuel documenté par la DGI est :
Tranche mensuelle	Taux
0 – 75 000	0 %
75 001 – 240 000	16 %
240 001 – 800 000	21 %
800 001 – 2 400 000	24 %
2 400 001 – 8 000 000	28 %
> 8 000 000	32 %
Puis :
ITS_NET =
MAX(
    ITS_BRUT - RICF,
    0
)
La DGI applique actuellement une RICF mensuelle allant de 0 FCFA pour 1 part à 44 000 FCFA pour 5 parts. DGI

XXII. Codes d'erreur L’Agent SOLEX PAYROLL COMPLIANCE AUDITOR
Je créerais immédiatement :
TAX-E001 = COMPOSANTE NON QUALIFIÉE
TAX-E002 = EXONÉRATION SANS SOURCE
TAX-E003 = EXONÉRATION SANS JUSTIFICATIF
TAX-E004 = PLAFOND D'EXONÉRATION DÉPASSÉ
TAX-E005 = AVANTAGE EN NATURE NON VALORISÉ
TAX-E006 = FRAIS PROFESSIONNELS NON JUSTIFIÉS
TAX-E007 = DOUBLE REMBOURSEMENT DE FRAIS
TAX-E008 = PRIME TRANSPORT EXONÉRÉE AU-DELÀ DU PLAFOND
TAX-E009 = RESTAURATION EXONÉRÉE AU-DELÀ DU PLAFOND
TAX-E010 = INDEMNITÉ DE RUPTURE MAL QUALIFIÉE
TAX-E011 = DOMMAGES-INTÉRÊTS SANS PREUVE DU PRÉJUDICE
TAX-E012 = RÈGLE FISCALE HORS PÉRIODE
TAX-E013 = COTISATION SOCIALE DÉDUITE À TORT DU RBI
TAX-E014 = AIN REMBOURSÉ PAR SALARIÉ NON NETTÉ
TAX-E015 = DÉPASSEMENT LIMITE 10 % FRAIS D'EMPLOI
Architecture finale
Je structurerais donc le bloc fiscal L’Agent SOLEX PAYROLL COMPLIANCE AUDITOR ainsi :
PAYROLL_COMPONENT_RULES
        │
        ├── CNPS_ASSIETTE_RULES
        ├── CNAM_ASSIETTE_RULES
        └── TAX_COMPONENT_RULES
                  ↓
         TAX_EXEMPTION_RULES
                  ↓
         AIN_VALUATION_RULES
                  ↓
          TAXABLE_INCOME_ENGINE
                  ↓
             ITS_BRACKETS
                  ↓
               RICF
                  ↓
             ITS PAYABLE
C'est la séparation la plus robuste : la même prime peut être incluse dans l'assiette CNPS, exclue partiellement du revenu fiscal, et avoir encore un traitement différent pour la CMU. L’Agent SOLEX PAYROLL COMPLIANCE AUDITOR doit donc qualifier chaque composante séparément pour chaque régime, conformément au principe déjà retenu dans votre architecture SOLEX.