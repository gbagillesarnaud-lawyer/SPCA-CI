SOLEX PAYROLL COMPLIANCE AUDITOR — CI
REGISTRE DES INPUTS 

1. OBJECTIF DU REGISTRE
Ce registre définit toutes les données susceptibles d’être reçues, lues, déduites ou calculées par l’agent afin de réaliser un audit juridique, fiscal et social d’un bulletin de salaire.
Chaque input est décrit selon les champs suivants :
Champ	Signification
Input ID	Identifiant unique de la donnée
Donnée	Nom de l’information
Format	Type de donnée attendu
Statut	Obligatoire / recommandé / optionnel
Source	Document ou système d’origine
Module consommateur	Module qui utilise la donnée
Validation	Contrôle à effectuer
Si absent	Comportement attendu de l’agent


2. CATÉGORIE A — IDENTIFICATION DE L’AUDIT
Input ID	Donnée	Format	Statut	Source	Module consommateur	Validation	Si absent
AUD-001	Audit ID	Texte/UUID	Obligatoire système	Hermes	Tous	Unique	Générer automatiquement
AUD-002	Date de l’audit	Date/heure	Obligatoire	Système	Audit Log	Date valide	Générer automatiquement
AUD-003	Type d’audit	Enum	Obligatoire	Utilisateur	Workflow	Bulletin unique / mensuel / annuel / entreprise	Demander ou déduire du dossier
AUD-004	Période auditée	YYYY-MM	Obligatoire	Bulletin	Tous	Période identifiable	STOP si indéterminable
AUD-005	Juridiction	Texte	Obligatoire	Paramétrage	Context Resolver	Côte d’Ivoire	STOP si juridiction inconnue
AUD-006	Demandeur de l’audit	Texte	Recommandé	Utilisateur	Audit Log	Identité valide	Enregistrer « non renseigné »
AUD-007	Référence dossier SOLEX	Texte	Recommandé	SOLEX	Audit Log	Référence existante	Générer référence interne

3. CATÉGORIE B — IDENTIFICATION DE L’EMPLOYEUR
Input ID	Donnée	Format	Statut	Source	Module	Validation	Si absent
EMP-001	Raison sociale	Texte	Obligatoire	Bulletin / RCCM	Intake	Non vide	Demander
EMP-002	Nom commercial	Texte	Optionnel	Bulletin	Intake	—	Continuer
EMP-003	Forme juridique	Enum	Recommandé	RCCM	Context Resolver	SA/SARL/SAS/etc.	Continuer
EMP-004	Secteur d’activité	Texte	Obligatoire pour audit conventionnel	Employeur	Context Resolver	Secteur identifiable	Audit général uniquement
EMP-005	Activité principale	Texte	Recommandé	RCCM / employeur	Context Resolver	Cohérence secteur	Continuer
EMP-006	Établissement	Texte	Optionnel	Bulletin	Intake	—	Continuer
EMP-007	Localisation	Texte	Recommandé	Bulletin	Context Resolver	Côte d’Ivoire	Continuer
EMP-008	Numéro CNPS employeur	Texte	Recommandé	Bulletin / déclaration CNPS	Social Checker	Format	Signaler
EMP-009	Numéro contribuable	Texte	Optionnel	Bulletin	Tax Checker	Format	Continuer
EMP-010	Convention collective déclarée	Texte	Recommandé	RH	Context Resolver	Vérifier applicabilité	Ne pas conclure sans vérification
EMP-011	Grille salariale interne	Document	Optionnel	RH	Legal Checker	Version/date	Audit sans grille
EMP-012	Accord d’entreprise	Document	Optionnel	RH	Legal Checker	Applicabilité	Continuer
EMP-013	Règlement intérieur	Document	Optionnel	RH	Legal Checker	Date/version	Continuer
EMP-014	Politique de rémunération	Document	Optionnel	RH	Compliance Checker	Date/version	Continuer
EMP-015	Politique de primes	Document	Optionnel	RH	Compliance Checker	Date/version	Continuer
4. CATÉGORIE C — IDENTIFICATION DU SALARIÉ
Input ID	Donnée	Format	Statut	Source	Module	Validation	Si absent
SAL-001	Identifiant salarié	Texte	Obligatoire	Bulletin	Intake	Unique	Générer ID anonymisé
SAL-002	Nom et prénoms	Texte	Optionnel	Bulletin	Intake	—	Utiliser ID
SAL-003	Matricule	Texte	Recommandé	Bulletin	Intake	Unique	Continuer
SAL-004	Fonction	Texte	Obligatoire	Bulletin / contrat	Context Resolver	Cohérence	Signaler
SAL-005	Emploi	Texte	Recommandé	Contrat	Context Resolver	—	Continuer
SAL-006	Classification	Texte	Recommandé	Bulletin / contrat	Context Resolver	Vérifier convention	NON CONTRÔLABLE si indispensable
SAL-007	Catégorie	Texte	Recommandé	Bulletin	Context Resolver	Cohérence convention	Signaler
SAL-008	Échelon	Texte	Optionnel	Bulletin	Context Resolver	Cohérence	Continuer
SAL-009	Date d’embauche	Date	Recommandé	Contrat	Calculation Engine	Date valide	Prime ancienneté non contrôlable
SAL-010	Ancienneté	Nombre	Calculé	Date embauche	Calculation Engine	Recalculer	Non calculable
SAL-011	Type de contrat	Enum	Recommandé	Contrat	Legal Checker	CDI/CDD/etc.	Continuer avec réserve
SAL-012	Durée contractuelle du travail	Nombre	Recommandé	Contrat	Time Checker	Heures/semaine ou mois	HS non fiables sans régime
SAL-013	Temps plein / partiel	Enum	Recommandé	Contrat	Time Checker	Cohérence heures	Signaler
SAL-014	Statut cadre/non cadre	Enum	Optionnel	Contrat	Context Resolver	—	Continuer
SAL-015	Situation familiale	Structuré	Recommandé fiscal	Salarié/RH	Tax Engine	Cohérence justificatifs	RICF non contrôlable
SAL-016	Nombre de personnes à charge	Entier	Recommandé fiscal	RH	Tax Engine	≥0	RICF non contrôlable
SAL-017	Nationalité	Texte	Optionnel	RH	Context Resolver	—	Continuer
SAL-018	Situation particulière	Texte	Optionnel	RH	Legal Checker	Ex. expatrié, apprenti	Continuer

5. CATÉGORIE D — DOCUMENTS CONTRACTUELS
Input ID	Donnée	Format	Statut	Source	Module	Validation	Si absent
DOC-001	Contrat de travail	PDF/DOCX	optionnel	RH	Legal Checker	Lisible/signé	Audit bulletin possible
DOC-002	Avenant salaire	Document	Optionnel	RH	Compliance Checker	Date d’effet	Continuer
DOC-003	Avenant fonction	Document	Optionnel	RH	Context Resolver	Date d’effet	Continuer
DOC-004	Décision de rémunération	Document	Optionnel	Direction	Compliance Checker	Autorité/date	Continuer
DOC-005	Lettre de promotion	Document	Optionnel	RH	Context Resolver	Date	Continuer
DOC-006	Politique avantages	Document	Optionnel	Employeur	Compliance Checker	Version applicable	Continuer
DOC-007	Convention collective	PDF	Recommandé	Base SOLEX	Legal Retriever	Validité/applicabilité	Human Gate si indispensable
DOC-008	Accord collectif	Document	Optionnel	RH	Legal Retriever	Champ d’application	Continuer

6. CATÉGORIE E — DONNÉES DE PÉRIODE DE PAIE
Input ID	Donnée	Format	Statut	Source	Module	Validation	Si absent
PAY-001	Mois de paie	YYYY-MM	Obligatoire	Bulletin	Tous	Date	STOP
PAY-002	Nombre de jours du mois	Entier	Calculé	Calendrier	Calculation Engine	Automatique	Calculer
PAY-003	Jours travaillés	Nombre	Recommandé	Bulletin/pointage	Time Checker	≤ jours période	Signaler
PAY-004	Jours payés	Nombre	Recommandé	Bulletin	Calculation Engine	Cohérence	Continuer
PAY-005	Jours d’absence	Nombre	Optionnel	RH	Time Checker	≥0	Absence non contrôlable
PAY-006	Jours de congés	Nombre	Optionnel	RH	Leave Checker	≥0	Continuer
PAY-007	Heures normales	Nombre	Recommandé	Bulletin	Time Checker	Cohérence régime	Signaler
PAY-008	Heures réellement travaillées	Nombre	Recommandé	Pointage	Time Checker	Cohérence	HS non contrôlables précisément

7. CATÉGORIE F — RÉMUNÉRATION FIXE
Input ID	Donnée	Format	Statut	Source	Module	Validation	Si absent
REM-001	Salaire de base	FCFA	Obligatoire	Bulletin	Calculation Engine	≥0	STOP partiel
REM-002	Salaire contractuel	FCFA	Recommandé	Contrat	Compliance Checker	Comparer bulletin	Continuer
REM-003	Salaire catégoriel	FCFA	Calculé/référentiel	Convention collective	Legal Retriever	Période et catégorie	Non contrôlable si inconnue
REM-004	SMIG applicable	FCFA	Calculé/référentiel	Texte légal	Legal Retriever	Date d’effet	Escalade si inconnu
REM-005	Taux horaire	FCFA	Calculé	Salaire/régime	Calculation Engine	Formule validée	Non calculable

8. CATÉGORIE G — PRIMES ET BONUS
Input ID	Donnée	Format	Statut	Source	Module	Validation	Si absent
PRI-001	Prime d’ancienneté	FCFA	Optionnel	Bulletin	Compliance Checker	Recalcul	Contrôler obligation
PRI-002	Prime de rendement	FCFA	Optionnel	Bulletin	Compliance Checker	Base prévue	Continuer
PRI-003	Prime de fonction	FCFA	Optionnel	Bulletin	Compliance Checker	Fondement	Continuer
PRI-004	Prime de responsabilité	FCFA	Optionnel	Bulletin	Compliance Checker	Fondement	Continuer
PRI-005	Prime exceptionnelle	FCFA	Optionnel	Bulletin	Tax/Social Checker	Qualification	Continuer
PRI-006	Bonus	FCFA	Optionnel	Bulletin	Tax/Social Checker	Qualification	Continuer
PRI-007	Gratification	FCFA	Optionnel	Bulletin	Compliance Checker	Vérifier obligation	Continuer
PRI-008	Prime conventionnelle	FCFA	Optionnel	Convention	Compliance Checker	Applicabilité	Non contrôlable sans convention
PRI-009	Autre prime	Structuré	Optionnel	Bulletin	Compliance Checker	Nature/fondement	Signaler si ambigu

9. CATÉGORIE H — INDEMNITÉS
Input ID	Donnée	Format	Statut	Source	Module	Validation	Si absent
IND-001	Indemnité transport	FCFA	Optionnel	Bulletin	Compliance Checker	Fondement/plafond	Continuer
IND-002	Indemnité logement	FCFA	Optionnel	Bulletin	Tax/Social Checker	Qualification	Continuer
IND-003	Indemnité repas	FCFA	Optionnel	Bulletin	Tax/Social Checker	Qualification	Continuer
IND-004	Indemnité déplacement	FCFA	Optionnel	Bulletin	Tax/Social Checker	Justificatifs	Continuer
IND-005	Indemnité représentation	FCFA	Optionnel	Bulletin	Tax/Social Checker	Fondement	Continuer
IND-006	Indemnité salissure	FCFA	Optionnel	Bulletin	Compliance Checker	Convention	Continuer
IND-007	Autre indemnité	Structuré	Optionnel	Bulletin	Compliance Checker	Nature/fondement	Signaler
10. CATÉGORIE I — AVANTAGES EN NATURE
Input ID	Donnée	Format	Statut	Source	Module	Validation	Si absent
AVN-001	Logement	FCFA/nature	Optionnel	Bulletin	Tax Engine	Valorisation	Continuer
AVN-002	Véhicule	FCFA/nature	Optionnel	Bulletin	Tax Engine	Valorisation	Continuer
AVN-003	Téléphone	FCFA/nature	Optionnel	Bulletin	Tax Engine	Usage pro/perso	Continuer
AVN-004	Nourriture	FCFA/nature	Optionnel	Bulletin	Tax Engine	Valorisation	Continuer
AVN-005	Électricité/eau	FCFA	Optionnel	Bulletin	Tax Engine	Valorisation	Continuer
AVN-006	Autre avantage	Structuré	Optionnel	Bulletin	Tax/Social Engine	Qualification	Signaler

11. CATÉGORIE J — TEMPS DE TRAVAIL ET HEURES SUPPLÉMENTAIRES
Le référentiel impose de contrôler la durée normale, les régimes particuliers, les équivalences, les heures supplémentaires, le travail de nuit, le dimanche, les jours fériés et leurs majorations, sans qualifier une heure de supplémentaire avant d’avoir déterminé le régime applicable.
Input ID	Donnée	Format	Statut	Source	Module	Validation	Si absent
TIM-001	Régime durée du travail	Texte	Obligatoire pour HS	Contrat/convention	Context Resolver	Applicable au salarié	HS non contrôlables
TIM-002	Durée hebdomadaire normale	Nombre	Recommandé	Contrat/loi	Time Checker	Règle applicable	Non contrôlable
TIM-003	HS déclarées	Nombre	Optionnel	Bulletin	Time Checker	≥0	Continuer
TIM-004	HS réellement effectuées	Nombre	Recommandé	Pointage	Time Checker	Justifiées	Signaler
TIM-005	Taux majoration HS	%	Calculé	Règle	Calculation Engine	Vérifier période	Ne pas calculer
TIM-006	Heures de nuit	Nombre	Optionnel	Pointage	Time Checker	≥0	Continuer
TIM-007	Heures dimanche	Nombre	Optionnel	Pointage	Time Checker	≥0	Continuer
TIM-008	Heures jours fériés	Nombre	Optionnel	Pointage	Time Checker	≥0	Continuer
TIM-009	Régime d’équivalence	Texte	Optionnel	Convention/texte	Context Resolver	Applicabilité	Ne pas supposer
TIM-010	Autorisation HS	Document	Optionnel	RH	Compliance Checker	Date/périmètre	Continuer
TIM-011	Fiche de pointage	Document	Recommandé	RH	Time Checker	Correspondance période	Confiance réduite
TIM-012	Fiche HS validée	Document	Recommandé	Manager	Time Checker	Signée/validée	Signaler

12. CATÉGORIE K — CONGÉS ET ABSENCES
Input ID	Donnée	Format	Statut	Source	Module	Validation	Si absent
LEA-001	Jours congés pris	Nombre	Optionnel	RH	Leave Checker	≥0	Continuer
LEA-002	Allocation congés	FCFA	Optionnel	Bulletin	Calculation Engine	Recalcul	Continuer
LEA-003	Solde congés	Nombre	Optionnel	RH	Leave Checker	Cohérence	Continuer
LEA-004	Absence justifiée	Nombre	Optionnel	RH	Leave Checker	Justificatif	Continuer
LEA-005	Absence injustifiée	Nombre	Optionnel	RH	Leave Checker	≥0	Continuer
LEA-006	Retenue absence	FCFA	Optionnel	Bulletin	Compliance Checker	Formule	Continuer
LEA-007	Arrêt maladie	Document	Optionnel	RH	Legal Checker	Période	Continuer

13. CATÉGORIE L — RETENUES, AVANCES ET ACOMPTES
Input ID	Donnée	Format	Statut	Source	Module	Validation	Si absent
DED-001	Avance sur salaire	FCFA	Optionnel	Bulletin	Net Engine	Justificatif	Continuer
DED-002	Acompte	FCFA	Optionnel	Bulletin	Net Engine	Justificatif	Continuer
DED-003	Prêt salarié	FCFA	Optionnel	Bulletin	Compliance Checker	Convention prêt	Continuer
DED-004	Retenue disciplinaire	FCFA	Optionnel	Bulletin	Legal Checker	Vérifier licéité	Escalade si doute
DED-005	Saisie-arrêt	FCFA	Optionnel	Acte judiciaire	Legal Checker	Titre/quotité	Escalade si doute
DED-006	Retenue absence	FCFA	Optionnel	Bulletin	Calculation Engine	Base/formule	Continuer
DED-007	Autre retenue	Structuré	Optionnel	Bulletin	Compliance Checker	Fondement	Signaler
DED-008	Justificatif retenue	Document	Recommandé	RH	Legal Checker	Validité	Retenue à vérifier

14. CATÉGORIE M — CNPS
Le référentiel exige de distinguer l’assiette CNPS, les cotisations salariales et patronales, les plafonds et les risques professionnels.
Input ID	Donnée	Format	Statut	Source	Module	Validation	Si absent
SOC-001	Assiette CNPS bulletin	FCFA	Recommandé	Bulletin	Social Engine	≥0	Recalculer
SOC-002	Taux CNPS salarié	%	Calculé	Référentiel	Social Engine	Période vérifiée	STOP calcul concerné
SOC-003	Cotisation salarié bulletin	FCFA	Recommandé	Bulletin	Compliance Checker	Comparer théorique	Signaler
SOC-004	Taux patronal	%	Calculé	Référentiel	Social Engine	Période/risque	Non calculable
SOC-005	Cotisation patronale	FCFA	Optionnel	État paie	Social Engine	Recalcul	Continuer
SOC-006	Plafond CNPS	FCFA	Calculé	Référentiel	Social Engine	Date d’effet	Ne pas inventer
SOC-007	Taux AT/MP	%	Recommandé	CNPS	Social Engine	Secteur	Non calculable
SOC-008	Numéro CNPS salarié	Texte	Optionnel	Bulletin	Compliance Checker	Format	Continuer
SOC-009	Déclaration CNPS	Document	Recommandé audit étendu	CNPS	Compliance Checker	Période	Audit bulletin seul
SOC-010	Preuve paiement CNPS	Document	Optionnel	Employeur	Compliance Checker	Montant/période	Continuer

15. CATÉGORIE N — CMU
Input ID	Donnée	Format	Statut	Source	Module	Validation	Si absent
CMU-001	Assujettissement CMU	Booléen	Recommandé	Référentiel	CMU Engine	Vérifier	Déterminer juridiquement
CMU-002	Base CMU	FCFA	Calculé	Règle	CMU Engine	Formule	Non calculable
CMU-003	Cotisation CMU salarié	FCFA	Recommandé	Bulletin	Compliance Checker	Recalcul	Signaler
CMU-004	Cotisation employeur	FCFA	Optionnel	Bulletin	Compliance Checker	Recalcul	Continuer
CMU-005	Taux/montant applicable	%/FCFA	Calculé	Référentiel	CMU Engine	Période	Ne pas inventer
CMU-006	Déclaration CMU	Document	Optionnel	Employeur	Compliance Checker	Période	Continuer

16. CATÉGORIE O — FISCALITÉ / ITS
Le référentiel impose le contrôle des éléments imposables, exonérés, avantages en nature, ITS, barème progressif et réduction pour charges de famille.
Input ID	Donnée	Format	Statut	Source	Module	Validation	Si absent
TAX-001	Salaire imposable bulletin	FCFA	Recommandé	Bulletin	Tax Engine	≥0	Recalculer
TAX-002	Revenu imposable recalculé	FCFA	Calculé	Agent	Tax Engine	Trace calcul	Générer
TAX-003	ITS bulletin	FCFA	Recommandé	Bulletin	Tax Engine	Comparer	Signaler
TAX-004	Barème fiscal applicable	Référentiel	Obligatoire calcul	CGI	Legal Retriever	Période	STOP calcul fiscal
TAX-005	RICF applicable	FCFA/formule	Recommandé	CGI	Tax Engine	Situation familiale	Non contrôlable
TAX-006	Éléments exonérés	Liste	Calculé	CGI	Tax Engine	Source juridique	Ne pas inventer
TAX-007	Avantages imposables	Liste	Calculé	CGI	Tax Engine	Qualification	Escalade si ambigu
TAX-008	Déclaration ITS	Document	Optionnel	DGI	Compliance Checker	Période	Audit bulletin seul
TAX-009	Contributions patronales	FCFA	Optionnel	État paie	Tax Engine	Si périmètre inclus	Hors périmètre

17. CATÉGORIE P — NET À PAYER
Input ID	Donnée	Format	Statut	Source	Module	Validation	Si absent
NET-001	Brut bulletin	FCFA	Obligatoire	Bulletin	Net Engine	≥0	STOP partiel
NET-002	Brut recalculé	FCFA	Calculé	Agent	Net Engine	Trace	Calculer
NET-003	Total retenues	FCFA	Recommandé	Bulletin	Net Engine	Somme	Recalculer
NET-004	Net bulletin	FCFA	Obligatoire	Bulletin	Net Engine	≥0	STOP partiel
NET-005	Net théorique	FCFA	Calculé	Agent	Net Engine	Formule	Calculer
NET-006	Écart net	FCFA	Calculé	Agent	Compliance Checker	Théorique - constaté	Calculer

18. CATÉGORIE Q — SOURCES JURIDIQUES
Input ID	Donnée	Format	Statut	Source	Module	Validation	Si absent
LEG-001	Texte juridique	Document	Obligatoire si utilisé	Base SOLEX	Legal Retriever	Authentique	Ne pas utiliser
LEG-002	Type de texte	Enum	Obligatoire	Métadonnée	Legal Retriever	Loi/décret/etc.	Signaler
LEG-003	Référence	Texte	Obligatoire	Texte	Legal Retriever	Exactitude	Source non vérifiée
LEG-004	Article/disposition	Texte	Recommandé	Texte	Report Generator	Exactitude	Citer disposition générale
LEG-005	Date publication	Date	Recommandé	Journal officiel	Context Resolver	Date valide	Confiance réduite
LEG-006	Date d’effet	Date	Obligatoire règle calculée	Texte	Context Resolver	Vérifier	Ne pas appliquer
LEG-007	Date de fin	Date	Optionnel	Texte	Context Resolver	Cohérence	Considérer en vigueur jusqu’à preuve contraire avec réserve
LEG-008	Population concernée	Texte	Recommandé	Texte	Context Resolver	Applicabilité	Validation humaine si doute
LEG-009	Secteur concerné	Texte	Optionnel	Texte	Context Resolver	Applicabilité	Continuer
LEG-010	Version du texte	Texte	Recommandé	KB	Audit Log	Version	Signaler
LEG-011	URL/source officielle	URL	Recommandé	Source officielle	Evidence Store	Accessible	Conserver référence
19. CATÉGORIE R — CONVENTIONS COLLECTIVES
Input ID	Donnée	Format	Statut	Source	Module	Validation	Si absent
COL-001	Convention applicable	Texte	Recommandé	KB	Context Resolver	Secteur/salarié	Human Gate si indispensable
COL-002	Date convention	Date	Recommandé	Convention	Legal Retriever	Version	Confiance réduite
COL-003	Classification conventionnelle	Texte	Recommandé	Convention	Context Resolver	Correspondance fonction	Non contrôlable
COL-004	Minimum catégoriel	FCFA	Recommandé	Convention	Compliance Checker	Catégorie/période	Non contrôlable
COL-005	Prime obligatoire	Structuré	Optionnel	Convention	Compliance Checker	Condition	Continuer
COL-006	Indemnité obligatoire	Structuré	Optionnel	Convention	Compliance Checker	Condition	Continuer
COL-007	Durée travail spécifique	Nombre	Optionnel	Convention	Time Checker	Applicabilité	Régime général sous réserve

20. CATÉGORIE S — PREUVES ET JUSTIFICATIFS
Input ID	Donnée	Format	Statut	Source	Module	Validation	Si absent
EVD-001	Bulletin original	PDF/Image	Obligatoire	Client	Evidence Store	Lisible	STOP
EVD-002	Contrat	PDF	Recommandé	RH	Evidence Store	Authenticité	Continuer
EVD-003	Pointage	Excel/PDF	Recommandé pour HS	RH	Evidence Store	Période	HS avec réserve
EVD-004	Justificatif prime	Document	Optionnel	RH	Evidence Store	Lien salarié/période	Continuer
EVD-005	Justificatif retenue	Document	Recommandé	RH	Evidence Store	Fondement	Signaler
EVD-006	Déclaration sociale	Document	Optionnel	CNPS	Evidence Store	Période	Continuer
EVD-007	Déclaration fiscale	Document	Optionnel	DGI	Evidence Store	Période	Continuer
EVD-008	Preuve paiement	Document	Optionnel	Banque	Evidence Store	Montant/date	Continuer

21. CATÉGORIE T — PARAMÈTRES DE CALCUL
Input ID	Donnée	Format	Statut	Source	Module	Validation	Si absent
CAL-001	Taux applicable	%	Calculé	Référentiel	Calculation Engine	Date d’effet	Pas de calcul
CAL-002	Base de calcul	FCFA	Calculé	Données	Calculation Engine	Trace	Non calculable
CAL-003	Plafond	FCFA	Référentiel	Texte	Calculation Engine	Période	Ne pas appliquer
CAL-004	Seuil	FCFA	Référentiel	Texte	Calculation Engine	Période	Ne pas appliquer
CAL-005	Formule	Expression	Obligatoire calcul	Rules Engine	Validée	Pas de calcul	
CAL-006	Règle d’arrondi	Texte	Recommandé	Référentiel	Calculation Engine	Définie	Arrondi explicite
CAL-007	Hypothèse de calcul	Texte	Si nécessaire	Agent	Evidence Store	Explicitée	Interdit d’utiliser silencieusement

22. CATÉGORIE U — DONNÉES DE CONTRÔLE
Input ID	Donnée	Format	Statut	Source	Module
CTL-001	Valeur constatée	Nombre/texte	Calculé	Bulletin	Compliance Checker
CTL-002	Valeur attendue	Nombre/texte	Calculé	Rules Engine	Compliance Checker
CTL-003	Écart	Nombre	Calculé	Agent	Compliance Checker
CTL-004	Type d’écart	Enum	Calculé	Agent	Risk Engine
CTL-005	Favorable/défavorable salarié	Enum	Calculé	Agent	Report Generator
CTL-006	Impact social	FCFA	Calculé	Agent	Risk Engine
CTL-007	Impact fiscal	FCFA	Calculé	Agent	Risk Engine
CTL-008	Impact employeur	FCFA	Calculé	Agent	Risk Engine
CTL-009	Récurrence	Booléen	Calculé	Historique	Risk Engine
CTL-010	Nombre salariés concernés	Entier	Calculé	Audit collectif	Risk Engine

23. CATÉGORIE V — RISK SCORING
Input ID	Donnée	Format	Statut
RSK-001	Gravité juridique	Score	Calculé
RSK-002	Impact financier	Score	Calculé
RSK-003	Impact social	Score	Calculé
RSK-004	Impact fiscal	Score	Calculé
RSK-005	Récurrence	Score	Calculé
RSK-006	Nombre salariés affectés	Score	Calculé
RSK-007	Exposition rétroactive	Score	Calculé
RSK-008	Indice de dissimulation	Booléen	Calculé
RSK-009	Niveau de confiance	Score	Calculé
RSK-010	Criticité finale	P1/P2/P3/P4	Calculé
La criticité ne doit pas dépendre uniquement du montant ; le référentiel impose de prendre en compte la nature de l’obligation, la répétition et l’exposition réglementaire.
24. CATÉGORIE W — HUMAN GATE
Input ID	Donnée	Format	Déclenchement
HUM-001	Suspicion de fraude	Booléen	Escalade immédiate
HUM-002	Travailleur non déclaré	Booléen	Escalade immédiate
HUM-003	Conflit documentaire majeur	Booléen	Escalade
HUM-004	Retenue sans fondement	Booléen	Escalade
HUM-005	Risque systémique	Booléen	Escalade
HUM-006	Exposition rétroactive élevée	Booléen	Escalade
HUM-007	Conflit de sources	Booléen	Escalade
HUM-008	Jurisprudence incertaine	Booléen	Escalade
HUM-009	Convention indisponible	Booléen	Escalade si déterminante
HUM-010	Interprétation complexe	Booléen	Escalade
HUM-011	Confiance faible	Booléen	Escalade
Ces conditions correspondent aux cas dans lesquels le référentiel impose la validation par un juriste, un expert fiscal ou un expert social.
25. CATÉGORIE X — CONFIGURATION HERMES
Ces inputs ne concernent pas un salarié, mais la configuration permanente de l’agent.
Input ID	Paramètre	Format	Exemple
CFG-001	Nom agent	Texte	SOLEX PAYROLL COMPLIANCE AUDITOR — CI
CFG-002	Juridiction	Texte	Côte d’Ivoire
CFG-003	Mode	Enum	AUDIT
CFG-004	Langue	Texte	Français
CFG-005	Version agent	Texte	1.0
CFG-006	Version ruleset	Texte	CI-PAYROLL-2026.1
CFG-007	Seuil confiance élevé	Décimal	0.90
CFG-008	Seuil confiance moyen	Décimal	0.70
CFG-009	Human Gate P1	Booléen	true
CFG-010	Human Gate P2	Booléen	true
CFG-011	Citation source obligatoire	Booléen	true
CFG-012	Trace calcul obligatoire	Booléen	true
CFG-013	Autorisation envoi client	Booléen	false
CFG-014	Autorisation modification paie	Booléen	false
CFG-015	Autorisation déclaration externe	Booléen	false

26. MATRICE DES DONNÉES MINIMALES
Pour qu’un audit de premier niveau puisse commencer, les inputs minimaux sont :
Donnée	Exigence
Bulletin de salaire	Obligatoire
Employeur	Obligatoire
Identifiant salarié	Obligatoire
Période	Obligatoire
Salaire de base	Obligatoire
Brut	Obligatoire
Retenues	Recommandé
Net à payer	Obligatoire
Juridiction	Obligatoire

27. DONNÉES REQUISES POUR UN AUDIT COMPLET
Un audit complet nécessite idéalement :
•	bulletin ;
•	contrat ;
•	classification ;
•	convention collective ;
•	date d’embauche ;
•	durée du travail ;
•	pointage ;
•	justificatifs heures supplémentaires ;
•	situation familiale fiscale ;
•	déclaration CNPS ;
•	données CMU ;
•	déclaration ITS ;
•	politique primes ;
•	justificatifs retenues ;
•	référentiel juridique applicable.

28. COMPORTEMENT GLOBAL SI DONNÉE MANQUANTE
L’agent ne doit pas appliquer une logique binaire :
DONNÉE MANQUANTE → AUDIT IMPOSSIBLE
Il doit appliquer :
DONNÉE MANQUANTE
       ↓
Cette donnée affecte-t-elle tous les contrôles ?
       │
       ├── NON
       │      ↓
       │   Continuer les contrôles possibles
       │
       └── OUI
              ↓
           STOP PARTIEL
Puis marquer :
NON CONTRÔLABLE — INFORMATION MANQUANTE
Ce comportement est expressément prévu dans le référentiel SOLEX.

29. SCHÉMA D’INPUT GLOBAL POUR HERMES
{
  "audit": {
    "audit_id": "",
    "audit_type": "",
    "audit_date": "",
    "payroll_period": "",
    "jurisdiction": "CI"
  },

  "employer": {
    "legal_name": "",
    "legal_form": "",
    "sector": "",
    "activity": "",
    "cnps_number": "",
    "tax_number": "",
    "collective_agreement": ""
  },

  "employee": {
    "employee_id": "",
    "position": "",
    "job": "",
    "classification": "",
    "category": "",
    "grade": "",
    "hire_date": "",
    "contract_type": "",
    "working_time_regime": "",
    "family_status": {}
  },

  "payroll": {
    "base_salary": 0,
    "earnings": [],
    "bonuses": [],
    "allowances": [],
    "benefits_in_kind": [],
    "overtime": [],
    "leave": [],
    "absences": [],
    "deductions": [],
    "advances": [],
    "gross_salary": 0,
    "social_base": 0,
    "tax_base": 0,
    "cnps_employee": 0,
    "cmu": 0,
    "its": 0,
    "net_salary": 0
  },

  "working_time": {
    "normal_hours": 0,
    "actual_hours": 0,
    "overtime_hours": 0,
    "night_hours": 0,
    "sunday_hours": 0,
    "holiday_hours": 0
  },

  "documents": {
    "payslip": [],
    "employment_contract": [],
    "amendments": [],
    "timesheets": [],
    "social_declarations": [],
    "tax_declarations": [],
    "supporting_documents": []
  },

  "legal_context": {
    "legal_sources": [],
    "collective_agreement": {},
    "minimum_wage": {},
    "social_rules": {},
    "tax_rules": {}
  },

  "system": {
    "agent_version": "",
    "ruleset_version": "",
    "confidence_thresholds": {},
    "permissions": {}
  }
}

30. RÈGLE FONDAMENTALE DE TRAITEMENT DES INPUTS
Aucune donnée ne doit passer directement de :
INPUT → CONCLUSION
Le chemin obligatoire est :
INPUT
↓
SOURCE
↓
VALIDATION
↓
NORMALISATION
↓
CONTEXTE
↓
RÈGLE APPLICABLE
↓
CALCUL
↓
COMPARAISON
↓
CONSTAT
↓
RISQUE
↓
CONCLUSION
31. STATUT DE CHAQUE INPUT
Chaque input doit porter un statut parmi :
VERIFIED
UNVERIFIED
MISSING
CONFLICTING
NOT_APPLICABLE
CALCULATED
HUMAN_VALIDATED
Exemple :
{
  "field": "hire_date",
  "value": "2022-06-15",
  "status": "VERIFIED",
  "source": "employment_contract.pdf",
  "confidence": 0.99
}

32. PRIORISATION DES INPUTS
Niveau 1 — CRITIQUE
Sans eux, l’audit est impossible ou très limité :
•	bulletin ;
•	période ;
•	employeur ;
•	salarié ;
•	salaire de base ;
•	brut ;
•	net.
Niveau 2 — IMPORTANT
Nécessaires aux contrôles principaux :
•	contrat ;
•	date d’embauche ;
•	fonction ;
•	classification ;
•	convention collective ;
•	assiettes ;
•	CNPS ;
•	ITS ;
•	CMU.
Niveau 3 — ENRICHISSEMENT
Améliorent la précision :
•	pointage ;
•	justificatifs ;
•	déclarations ;
•	politique de rémunération ;
•	accords d’entreprise.
Niveau 4 — AUDIT AVANCÉ
Nécessaires aux investigations :
•	historiques de paie ;
•	déclarations antérieures ;
•	données multi-salariés ;
•	pièces justificatives ;
•	historiques de régularisation.
33. PRINCIPE POUR HERMES
Hermes ne doit pas considérer tous les inputs comme équivalents.
Chaque donnée doit comporter cinq dimensions :
VALUE
SOURCE
DATE
CONFIDENCE
STATUS
Ainsi :
salary = 250 000 FCFA
est insuffisant.
L’input correct est :
{
  "field": "base_salary",
  "value": 250000,
  "currency": "XOF",
  "source": "bulletin_09_2026.pdf",
  "payroll_period": "2026-09",
  "status": "VERIFIED",
  "confidence": 0.99
}
Cette structure doit devenir le standard interne du SOLEX PAYROLL COMPLIANCE AUDITOR.