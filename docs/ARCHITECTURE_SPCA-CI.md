# SOLEX PAYROLL COMPLIANCE AUDITOR — CI  
## ARCHITECTURE FONCTIONNELLE POUR HERMES AGENT

---

# 1. ARCHITECTURE GÉNÉRALE

L’agent est organisé autour de **10 modules fonctionnels** :

1. **Document Intake**
2. **Payroll Data Extractor**
3. **Context & Applicability Resolver**
4. **Legal Rule Retriever**
5. **Payroll Calculation Engine**
6. **Compliance Checker**
7. **Risk Scoring Engine**
8. **Human Gate & Escalation**
9. **Report Generator**
10. **Audit Log & Evidence Store**

Architecture logique :

**INPUTS → EXTRACTION → CONTEXTE → DROIT APPLICABLE → CALCUL → CONTRÔLE → SCORING → HUMAN GATE → RAPPORT → ARCHIVAGE**

---

# 2. MODULE 1 — DOCUMENT INTAKE

## Rôle

Recevoir, identifier et préparer les documents nécessaires à l’audit.

## Inputs

- bulletin de salaire PDF ;
- bulletin image ;
- fichier Excel de paie ;
- journal de paie ;
- contrat de travail ;
- avenant ;
- grille salariale ;
- relevé CNPS ;
- déclaration fiscale ;
- fiche de présence ;
- fiche d’heures supplémentaires ;
- convention collective ;
- politique de rémunération ;
- règlement intérieur ;
- tout document complémentaire utile.

## Traitements

- identification du type de document ;
- contrôle de lisibilité ;
- rattachement au dossier ;
- rattachement à l’entreprise ;
- rattachement au salarié ;
- identification de la période ;
- détection des doublons ;
- préparation pour extraction.

## Outputs

```text
document_id
document_type
employer_id
employee_id
payroll_period
file_quality
processing_status
```

## Règles

Ne jamais lancer un audit complet si :

- le bulletin est illisible ;
- la période n’est pas identifiable ;
- le document principal est incomplet au point d’empêcher toute analyse.

Cependant, les contrôles partiels restent possibles lorsque certaines données seulement sont absentes.

---

# 3. MODULE 2 — PAYROLL DATA EXTRACTOR

## Rôle

Transformer le bulletin et les documents associés en données structurées.

## Inputs attendus

### Identité employeur

- raison sociale ;
- secteur ;
- établissement ;
- localisation ;
- convention collective.

### Identité salarié

- nom ou identifiant ;
- matricule ;
- fonction ;
- emploi ;
- classification ;
- catégorie ;
- échelon ;
- date d’embauche ;
- type de contrat.

### Données de paie

- période ;
- salaire de base ;
- nombre d’heures ;
- primes ;
- indemnités ;
- avantages ;
- heures supplémentaires ;
- heures de nuit ;
- dimanches ;
- jours fériés ;
- absences ;
- congés ;
- avances ;
- acomptes ;
- retenues ;
- CNPS ;
- CMU ;
- ITS ;
- brut ;
- base sociale ;
- base fiscale ;
- net.

Le document de référence exige précisément l’extraction de ces catégories de données lorsqu’elles sont disponibles.

## Output structuré recommandé

```json
{
  "employer": {},
  "employee": {},
  "payroll_period": "",
  "earnings": [],
  "deductions": [],
  "social_contributions": [],
  "taxes": [],
  "gross_salary": 0,
  "social_base": 0,
  "tax_base": 0,
  "net_salary": 0,
  "missing_data": [],
  "extraction_confidence": 0
}
```

## Règles

Chaque champ extrait doit avoir :

- valeur ;
- source documentaire ;
- page ;
- zone ou ligne ;
- niveau de confiance.

Exemple :

```json
{
  "field": "base_salary",
  "value": 250000,
  "source": "bulletin_janvier_2026.pdf",
  "page": 1,
  "confidence": 0.98
}
```

---

# 4. MODULE 3 — CONTEXT & APPLICABILITY RESOLVER

## Rôle

Déterminer le contexte juridique réel du bulletin avant tout calcul.

## Inputs

- période de paie ;
- secteur d’activité ;
- type de salarié ;
- contrat ;
- fonction ;
- classification ;
- temps de travail ;
- convention collective ;
- localisation ;
- textes disponibles.

## Questions que l’agent doit résoudre

1. Le droit ivoirien est-il applicable ?
2. Quelle est la période juridique de référence ?
3. Quelle convention collective s’applique ?
4. Existe-t-il un régime sectoriel particulier ?
5. Quel régime de durée du travail s’applique ?
6. Existe-t-il une classification catégorielle ?
7. Quel minimum salarial doit être utilisé ?
8. Quels taux et plafonds étaient applicables à cette date ?

## Output

```json
{
  "jurisdiction": "Côte d'Ivoire",
  "legal_reference_date": "",
  "collective_agreement": "",
  "working_time_regime": "",
  "minimum_wage_rule": "",
  "special_regime": [],
  "context_confidence": ""
}
```

## Règle majeure

**Aucun calcul juridique, social ou fiscal ne doit utiliser un taux avant vérification de sa période d’application.**

Le référentiel de l’agent impose précisément d’auditer selon les textes, taux, plafonds et barèmes applicables à la période du bulletin.

---

# 5. MODULE 4 — LEGAL RULE RETRIEVER

## Rôle

Rechercher les règles applicables au dossier.

## Sources prioritaires

1. Constitution ;
2. lois ;
3. ordonnances ;
4. décrets ;
5. Code du travail ;
6. textes d’application ;
7. Code général des impôts ;
8. annexes fiscales ;
9. doctrine DGI ;
10. Code de Prévoyance Sociale ;
11. textes CNPS ;
12. textes CNAM / CMU ;
13. Convention Collective Interprofessionnelle ;
14. conventions sectorielles ;
15. arrêtés salariaux ;
16. jurisprudence ;
17. doctrine professionnelle complémentaire.

Cette hiérarchie des sources est expressément fixée dans le référentiel existant.

## Inputs

```text
control_type
payroll_period
employee_category
sector
collective_agreement
jurisdiction
```

## Output

Pour chaque règle :

```json
{
  "rule_id": "",
  "subject": "",
  "legal_text": "",
  "article": "",
  "authority": "",
  "effective_from": "",
  "effective_to": "",
  "population": "",
  "calculation_rule": "",
  "source_url": "",
  "confidence": ""
}
```

## Règle anti-hallucination

Si aucune source valide n’est retrouvée :

```text
SOURCE NON VÉRIFIÉE
```

et aucune règle ne doit être inventée.

---

# 6. MODULE 5 — PAYROLL CALCULATION ENGINE

## Rôle

Reconstituer mathématiquement les éléments contrôlables du bulletin.

## Sous-moteurs

### A. Gross Salary Engine

Calcule :

- salaire de base ;
- primes ;
- heures supplémentaires ;
- majorations ;
- indemnités ;
- avantages ;
- rémunération brute théorique.

### B. Social Base Engine

Calcule :

- assiette CNPS ;
- éléments inclus ;
- éléments exclus ;
- plafond applicable.

### C. Social Contribution Engine

Calcule :

- part salariale ;
- part patronale ;
- risques professionnels ;
- cotisations applicables.

### D. CMU Engine

Calcule la contribution CMU applicable.

### E. Tax Engine

Calcule :

- base fiscale ;
- éléments imposables ;
- éléments exonérés ;
- ITS ;
- réduction pour charges de famille ;
- autres mécanismes applicables.

### F. Net Salary Engine

Formule :

```text
Brut recalculé
– cotisations salariales
– impôts
– autres retenues autorisées
= net théorique
```

Le référentiel exige que brut, assiette sociale, assiette fiscale, retenues salariales et charges patronales soient distingués.

## Output

```json
{
  "gross_reported": 0,
  "gross_recalculated": 0,
  "social_base": 0,
  "employee_social_contribution": 0,
  "employer_social_contribution": 0,
  "cmu": 0,
  "tax_base": 0,
  "its": 0,
  "other_deductions": 0,
  "net_theoretical": 0,
  "net_reported": 0,
  "net_difference": 0
}
```

## Calculation Trace

Chaque calcul doit être conservé ainsi :

```text
variable
base
rate
formula
rounding
result
source_rule
```

Exemple :

```text
Base × taux = résultat
```

---

# 7. MODULE 6 — COMPLIANCE CHECKER

## Rôle

Comparer la situation observée à la situation juridiquement attendue.

## Familles de contrôles

### C01 — Salaire minimum

- SMIG ;
- minimum catégoriel ;
- cohérence classification / salaire.

### C02 — Primes et indemnités

- ancienneté ;
- transport ;
- gratification ;
- autres obligations.

### C03 — Temps de travail

- durée normale ;
- heures supplémentaires ;
- nuit ;
- dimanche ;
- jours fériés ;
- majorations.

### C04 — Congés et absences

- congés payés ;
- absences ;
- retenues.

### C05 — CNPS

- assiette ;
- plafond ;
- taux ;
- part salariale ;
- part patronale.

### C06 — CMU

- assujettissement ;
- contribution ;
- cohérence.

### C07 — Fiscalité

- imposabilité ;
- exonérations ;
- base ;
- ITS ;
- charges de famille.

### C08 — Retenues

- avances ;
- acomptes ;
- retenues diverses ;
- fondement légal.

### C09 — Net à payer

- cohérence arithmétique ;
- comparaison net théorique / net bulletin.

### C10 — Mentions du bulletin

- mentions obligatoires ;
- cohérence documentaire.

## Output de chaque contrôle

```json
{
  "control_id": "C05",
  "control_name": "Assiette CNPS",
  "status": "NON_CONFORME",
  "observed_value": 0,
  "expected_value": 0,
  "difference": 0,
  "legal_reference": "",
  "finding": "",
  "recommendation": "",
  "confidence": ""
}
```

---

# 8. MODULE 7 — RISK SCORING ENGINE

## Rôle

Attribuer une criticité uniforme à chaque anomalie.

## Niveau P1 — CRITIQUE

Exemples :

- rémunération sous minimum obligatoire ;
- salarié non déclaré ;
- absence substantielle de cotisations ;
- retenue manifestement illicite ;
- anomalie systémique ;
- indice de falsification ;
- indice de fraude.

Action :

```text
ESCALADE EXPERT HUMAIN IMMÉDIATE
```

## Niveau P2 — MAJEUR

Impact :

- financier important ;
- réglementaire important ;
- récurrence significative.

Action :

```text
CORRECTION PRIORITAIRE
```

## Niveau P3 — MODÉRÉ

Anomalie isolée ou exposition limitée.

## Niveau P4 — MINEUR

Défaut essentiellement formel ou documentaire.

La criticité ne doit pas être fondée uniquement sur le montant ; la nature de l’obligation, la répétition et l’exposition réglementaire doivent être prises en compte.

## Variables de scoring recommandées

```text
severity
financial_impact
legal_exposure
social_exposure
tax_exposure
number_of_workers_affected
recurrence
retroactivity
intent_indicator
data_confidence
```

---

# 9. MODULE 8 — HUMAN GATE & ESCALATION

## Rôle

Empêcher l’agent de produire une conclusion autonome lorsqu’une intervention experte est nécessaire.

## Conditions d’escalade

```text
P1
fraud_indicator
undeclared_worker
material_document_conflict
large_unexplained_deduction
systemic_issue
major_retroactive_exposure
legal_source_conflict
uncertain_case_law
missing_collective_agreement
substantial_legal_interpretation
low_confidence
```

Ces situations correspondent aux règles d’escalade définies dans le cahier existant.

## Output

```json
{
  "escalation_required": true,
  "escalation_type": "",
  "reason": "",
  "priority": "",
  "recommended_expert": "",
  "blocked_actions": []
}
```

## Profils d’experts

- juriste droit social ;
- fiscaliste ;
- spécialiste CNPS ;
- spécialiste paie ;
- expert-comptable ;
- avocat ;
- responsable SOLEX.

---

# 10. MODULE 9 — REPORT GENERATOR

## Rôle

Transformer l’analyse en livrable professionnel SOLEX.

## Statuts possibles

```text
CONFORME
CONFORME SOUS RÉSERVE
NON CONFORME
AUDIT INCOMPLET
ESCALADE REQUISE
```

## Structure obligatoire

### A. Identification

### B. Conclusion exécutive

### C. Tableau des contrôles

### D. Reconstitution de la paie

### E. Synthèse financière

### F. Plan correctif

### G. Escalade

### H. Sources

Cette architecture reprend exactement les huit blocs attendus dans le rapport d’audit du référentiel SOLEX.

---

# 11. MODULE 10 — AUDIT LOG & EVIDENCE STORE

## Rôle

Créer la piste d’audit.

## Données à conserver

```text
audit_id
agent_version
ruleset_version
audit_date
payroll_period
documents_used
data_extracted
rules_applied
calculations
findings
risk_scores
human_interventions
final_status
```

## Evidence Chain

Chaque conclusion doit être reliée à :

```text
DOCUMENT
↓
DONNÉE
↓
RÈGLE
↓
CALCUL
↓
CONSTAT
↓
RISQUE
↓
RECOMMANDATION
```

---

# 12. INPUT CONTRACT GLOBAL

Hermes devra accepter au minimum l’objet logique suivant :

```json
{
  "audit_request": {
    "employer": {},
    "employee": {},
    "payroll_period": "",
    "documents": [],
    "sector": "",
    "collective_agreement": "",
    "contract_data": {},
    "working_time_data": {},
    "payroll_data": {},
    "social_data": {},
    "tax_data": {},
    "additional_context": {}
  }
}
```

---

# 13. OUTPUT CONTRACT GLOBAL

```json
{
  "audit_id": "",
  "status": "",
  "confidence": "",
  "employee": {},
  "payroll_period": "",
  "applicable_context": {},
  "controls": [],
  "payroll_reconstruction": {},
  "financial_summary": {},
  "risk_summary": {
    "P1": 0,
    "P2": 0,
    "P3": 0,
    "P4": 0
  },
  "corrective_actions": [],
  "human_escalations": [],
  "sources": [],
  "evidence": [],
  "audit_log": {}
}
```

---

# 14. VARIABLES DE CONFIANCE

Chaque module doit produire un `confidence_score`.

Échelle recommandée :

```text
0.90 – 1.00 = ÉLEVÉ
0.70 – 0.89 = MOYEN
< 0.70 = FAIBLE
```

Mais le score chiffré ne doit jamais remplacer l’analyse qualitative.

Le rapport final conserve les catégories prévues par le référentiel :

```text
ÉLEVÉ
MOYEN
FAIBLE
```

---

# 15. SYSTEM PROMPT LOGIC

Hermes doit recevoir comme principe central :

> Tu es un auditeur de conformité de la paie ivoirienne. Tu ne produis pas la paie. Tu vérifies les informations disponibles, identifies le droit applicable à la période auditée, reconstitues les calculs contrôlables, compares la situation constatée à la situation attendue, qualifies les anomalies, mesures les écarts et proposes des corrections. Tu ne dois jamais inventer une règle, un taux, une donnée ou une référence juridique. Lorsque les informations ou les sources ne permettent pas une conclusion fiable, tu identifies explicitement la limite et déclenches une escalade humaine lorsque nécessaire.

---

# 16. DECISION TREE PRINCIPALE

```text
START
│
├── Bulletin disponible ?
│       └── NON → STOP / document requis
│
├── Bulletin lisible ?
│       └── NON → HUMAN REVIEW
│
├── Période identifiable ?
│       └── NON → STOP
│
├── Données essentielles disponibles ?
│       ├── PARTIELLEMENT → audit partiel
│       └── OUI
│
├── Contexte juridique déterminé ?
│       └── NON → audit limité + human review
│
├── Règles vérifiées ?
│       └── NON → ne pas calculer la règle concernée
│
├── Reconstitution des calculs
│
├── Contrôles
│
├── Anomalies ?
│       ├── NON → CONFORME
│       └── OUI
│
├── Criticité
│       ├── P4
│       ├── P3
│       ├── P2
│       └── P1 → HUMAN GATE
│
├── Synthèse financière
│
├── Plan correctif
│
├── Rapport
│
└── END
```

---

# 17. HUMAN-IN-THE-LOOP MATRIX

| Situation | Agent autonome | Validation humaine | Blocage |
|---|---:|---:|---:|
| Extraction bulletin | Oui | Si confiance faible | Non |
| Calcul simple | Oui | Non | Non |
| Application taux vérifié | Oui | Non | Non |
| Convention collective ambiguë | Non | Oui | Oui |
| Interprétation juridique complexe | Non | Oui | Oui |
| P4 | Oui | Optionnelle | Non |
| P3 | Oui | Selon politique SOLEX | Non |
| P2 | Oui pour pré-analyse | Oui | Publication |
| P1 | Non | Obligatoire | Oui |
| Suspicion de fraude | Non | Obligatoire | Oui |
| Rapport client définitif | Préparation | Validation selon workflow | Selon règle SOLEX |

---

# 18. STRUCTURE DE LA KNOWLEDGE BASE HERMES

Je recommande de ne pas déposer tous les textes en vrac.

La base doit être organisée ainsi :

```text
/LEGAL_KNOWLEDGE
    /LABOUR
    /TAX
    /CNPS
    /CMU
    /COLLECTIVE_AGREEMENTS
    /MINIMUM_WAGES
    /WORKING_TIME
    /CASE_LAW

/PAYROLL_RULES
    /EARNINGS
    /DEDUCTIONS
    /SOCIAL_BASE
    /TAX_BASE
    /ITS
    /CNPS
    /CMU
    /OVERTIME

/SOLEX_METHOD
    /AUDIT_RULES
    /RISK_MATRIX
    /REPORT_TEMPLATES
    /ESCALATION_RULES
    /CHECKLISTS
```

Chaque fichier juridique devrait comporter ses métadonnées :

```text
title
source
authority
type
publication_date
effective_from
effective_to
jurisdiction
sector
employee_category
version
status
```

---

# 19. REGISTRY DES RÈGLES

Pour Hermes, SOLEX gagnerait à transformer progressivement son droit de la paie en règles structurées.

Exemple générique :

```json
{
  "rule_id": "PAY-CI-001",
  "category": "minimum_wage",
  "jurisdiction": "CI",
  "effective_from": "",
  "effective_to": "",
  "condition": "",
  "formula": "",
  "legal_source": "",
  "article": "",
  "priority": "",
  "human_review_required": false
}
```

Cela permettra à l’agent de ne pas seulement « lire du droit », mais d’utiliser un **référentiel de règles calculables**.

---

# 20. ARCHITECTURE CIBLE

À terme, l’agent SOLEX doit fonctionner comme une chaîne contrôlée :

```text
DOCUMENTS CLIENT
        ↓
DOCUMENT INTAKE
        ↓
DATA EXTRACTION
        ↓
CONTEXT RESOLVER
        ↓
LEGAL KNOWLEDGE
        ↓
RULE ENGINE
        ↓
CALCULATION ENGINE
        ↓
COMPLIANCE CHECKER
        ↓
RISK ENGINE
        ↓
        ├────────── HUMAN REVIEW
        ↓
REPORT GENERATOR
        ↓
SOLEX PAYROLL COMPLIANCE DASHBOARD
        ↓
EVIDENCE STORE
```

---

# 21. PRINCIPE TECHNIQUE DE CONCEPTION

Le moteur ne doit pas fonctionner selon :

```text
« Lis le bulletin et dis s'il est conforme. »
```

Il doit fonctionner selon :

```text
EXTRACT
→ NORMALIZE
→ IDENTIFY CONTEXT
→ RETRIEVE RULE
→ VERIFY RULE DATE
→ CALCULATE
→ COMPARE
→ FIND
→ SCORE
→ EXPLAIN
→ CITE
→ ESCALATE
```

C’est ce découpage qui permettra à SOLEX d’obtenir un agent réellement auditable, maintenable et industrialisable.

---

# 22. POSITIONNEMENT FINAL DE L’AGENT

Le SOLEX PAYROLL COMPLIANCE AUDITOR doit être conçu non comme un chatbot juridique mais comme un :

**AI PAYROLL COMPLIANCE AUDIT SYSTEM**

combinant :

- IA documentaire ;
- moteur de règles ;
- moteur de calcul ;
- RAG juridique ;
- système de scoring ;
- workflows d’escalade ;
- génération de rapports ;
- piste d’audit.

Sa fonction centrale peut être résumée par :

**DOCUMENT → DATA → LAW → CALCULATION → CONTROL → RISK → EVIDENCE → DECISION SUPPORT**

La décision finale reste humaine lorsque le niveau de risque ou d’incertitude le justifie.