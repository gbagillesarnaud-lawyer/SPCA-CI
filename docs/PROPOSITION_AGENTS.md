# Espace de travail SPCA-CI — SOLEX Payroll Compliance Auditor

Spécification de référence : `docs/SPEC_SPCA-CI.md` (fait foi en cas de doute).

## Arborescence
| Dossier | Contenu | Droits de l'agent |
|---|---|---|
| `docs/` | Spécification, cahier des charges | Lecture |
| `referentiel/PAYROLL_RULES/` | Fiches de règles JSON versionnées (seules `"statut": "validee"` sont utilisées) | Lecture seule — propositions dans `referentiel/propositions/` |
| `referentiel/sources/` | Textes officiels | Lecture |
| `moteur/` | Moteur v0.2 `spca_audit.py` + package `spca/` (10 modules) + `config_spca.json` | Exécution uniquement |
| `dossiers/<ID_AUDIT>/` | Pièces d'origine + `audit_request.json` normalisé | Pièces : lecture seule ; `audit_request.json` : écriture |
| `rapports/<ID_AUDIT>/` | Résultats JSON + rapport | Écriture |
| `escalades/` | File de revue humaine | Écriture |
| `journal/` | Journal d'audit (ajout uniquement) | Ajout |
| `tests/` | Jeu de recette — règles FICTIVES | Exécution |

## Commandes
```bash
python moteur/spca_audit.py --input dossiers/<ID>/audit_request.json
python -m unittest discover -s tests -v
```

## Interdits
- Ne jamais supprimer ni écraser une pièce d'origine, un rapport validé ou une entrée de journal.
- Ne jamais modifier `referentiel/PAYROLL_RULES/` ni `moteur/`.
- Ne jamais placer de données réelles non anonymisées dans `tests/`.
- Ne jamais transmettre un rapport hors de cet espace sans validation humaine.
