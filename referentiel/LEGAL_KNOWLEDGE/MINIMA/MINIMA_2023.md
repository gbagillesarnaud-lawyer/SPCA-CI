---
title: "Salaires minima catégoriels conventionnels 2023 et SMIG"
sources: "Arrêté n°0050/MEPS/CAB du 19 mai 2023 (scan, 5 p.) ; décret n°2022-986 du 21 décembre 2022 (copie certifiée conforme, 2 p.) ; barème SOLEX 2023 (Word + PDF)"
effective_from: "2023-01-01"
status: "validee"
validated_by: "Gilles Arnaud (CEO SOLEX)"
validated_on: "2026-10-03"
---

# Minima 2023

- **SMIG** : 75 000 F CFA/mois à compter du 1er janvier 2023 (décret n°2022-986, art. 1 ; abroge le décret n°2013-791). Horaire de référence 432,7 F (arrêté n°0050, ligne 18).
- **Arrêté n°0050/MEPS/CAB du 19 mai 2023** (Me Adama KAMARA) : revalorisation par secteur, effet au 1er janvier 2023 ; art. 2 : les augmentations accordées depuis 2015 et les « à valoir » s'imputent ; art. 3 : extension aux secteurs non régis par la CCI ; art. 4 : abroge l'arrêté n°2015-855 du 30 décembre 2015.
- **Table moteur** : `PAYROLL_RULES/tables/smc.json` — 1 524 lignes, 27 secteurs, extraites des 127 tableaux du barème SOLEX.

## Points relevés pendant l'intégration
- **Thon : 15 %** (arrêté, ligne 15), et non 18 % comme dans la table de revalorisation du Rules Registry : corrigé.
- Industrie mécanique, agents de maîtrise : colonnes « Mensuel 2023 » et « Horaire 2023 » inversées dans le document ; valeurs remises en ordre (MNP = 118 365 F/mois, 683 F/h).
- BTP ouvriers : le mensuel du barème (mensuel 2015 × 1,15) diffère de 13 à 150 F du produit horaire 2023 × 173,33 (cat. 1A à HC) ; **arbitrage SOLEX du 2026-10-03 : la méthode mensuel 2015 × 1,15 fait foi** (application directe de l'arrêté, sans effet d'arrondi horaire).
- Agriculture (café-cacao, plantations, élevage, forestier) : grilles journalières et mensuelles « calcul mécanique » inférieures au SMIG ; le SMIG/SMAG reste le plancher. Grille « Chauffeur – salaires journaliers » de nature incertaine : non intégrée.
- Production agricole (ouvriers) : mesure de l'arrêté (écarts cat. 2 à 5A avec abattement de 50 %) non modélisable faute de grille 2015.
- Nettoyage et salubrité (12 %, ligne 23) : grille ajoutée le 2026-10-03 (barème complété) — ouvriers et conducteurs en taux horaires, employés en mensuel ; 20 montants, tous conformes au calcul 2015 × 1,12.
