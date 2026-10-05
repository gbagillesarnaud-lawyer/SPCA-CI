# SPCA-CI — SOLEX Payroll Compliance Auditor (Côte d'Ivoire)

Agent d'audit juridique, fiscal et social des bulletins de salaire ivoiriens, conçu par SOLEX (pôle legaltech) sur Hermes Agent.
Principe : **l'IA explique, le code calcule, le juriste valide.** L'agent audite la paie ; il ne la produit pas.

## Contenu
| Dossier | Rôle |
|---|---|
| `moteur/` | Moteur déterministe (10 modules) — point d'entrée `spca_audit.py`, package `spca/`, configuration `config_spca.json` |
| `referentiel/PAYROLL_RULES/` | Rules Registry versionné et daté (règles, paramètres, tables : CNPS, CMU, ITS, SMIG, minima catégoriels 2023…) |
| `referentiel/LEGAL_KNOWLEDGE/` | Textes sources et fiches de synthèse (Code du travail, CCI 1977, ordonnance ITS, doctrine DGI, arrêté SMC…) |
| `docs/` | Spécification, architecture, registres des inputs et des règles |
| `tests/` | Recette (`python -m unittest discover -s tests`) — données **fictives** uniquement |

## Exclus du dépôt
Dossiers clients, rapports, escalades et journal d'audit (`.gitignore`) : données personnelles et confidentielles.

## Lancer un audit (moteur seul)
```
python moteur/spca_audit.py --input <audit_request.json> --sortie rapports/<ID>
```
