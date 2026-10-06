# IDS multi-agents NSL-KDD

Système de détection d’intrusions à **sept agents**, conçu par **ingénierie dirigée par les modèles** (IDM) et exécuté sous **GAMA 2025.6.4**.

Ce dépôt produit une simulation démontrable : les connexions NSL-KDD traversent une chaîne Capture → Extraction → (Règles ∥ IA) → Décision → Alertes + Journal. Le code métier n’est pas écrit « à côté » des modèles : il s’inscrit dans une hiérarchie CIM → PIM → PSM → GAML, avec des règles d’édition strictes.

| | |
|---|---|
| **Données** | NSL-KDD : 125 973 connexions train / 22 544 test |
| **Plateforme** | GAMA 2025.6.4 |
| **Modèle** | `gama/models/ids_sma.gaml` |
| **Expérience** | `ids_gui` |
| **Classes** | NORMAL, DOS, PROBE, R2L, U2R |
| **Cible validée** | exactitude ≈ **81,0 %** · rappel attaques ≈ **72,2 %** |

## Sommaire

1. [Pourquoi ce projet](#1-pourquoi-ce-projet)
2. [Hiérarchie du projet](#2-hiérarchie-du-projet)
3. [Directives de projet](#3-directives-de-projet)
4. [Architecture multi-agents](#4-architecture-multi-agents)
5. [Problèmes, décisions, solutions](#5-problèmes-décisions-solutions)
6. [Cible et lecture des résultats](#6-cible-et-lecture-des-résultats)
7. [Ce qui a été construit](#7-ce-qui-a-été-construit)
8. [Démarrage](#8-démarrage)
9. [Structure détaillée du dépôt](#9-structure-détaillée-du-dépôt)
10. [Paramètres de simulation](#10-paramètres-de-simulation)
11. [Commandes de référence](#11-commandes-de-référence)

---

## 1. Pourquoi ce projet

L’objectif n’est pas seulement d’obtenir un score sur NSL-KDD. C’est de montrer qu’on peut :

- **cadrer** un IDS multi-agents sans ambiguïté (connexion vs paquet, rôle de chaque agent) ;
- **descendre** du concept à la plateforme (CIM → PIM → PSM → GAML) ;
- **générer** le squelette GAML et l’encodage / la forêt depuis les modèles ;
- **compléter** uniquement le métier dans des zones protégées ;
- **valider** la simulation sur des métriques stables (exactitude, rappel), pas sur le bruit console.

Le jeu de données NSL-KDD fournit des **connexions déjà agrégées** (41 attributs), pas des paquets bruts. La simulation lit donc des enregistrements de connexion. Le niveau « paquet » peut figurer dans le modèle conceptuel pour la compréhension du domaine ; il n’est pas l’unité exécutée.

---

## 2. Hiérarchie du projet

Le dépôt suit la descente IDM. Chaque couche a un rôle ; on ne saute pas une couche pour « gagner du temps » sans documenter pourquoi.

```
Niveau 0   data/          Jeu NSL-KDD (source de vérité des connexions)
#if ↓
Niveau 1   design/        CIM : cadrage, modèle conceptuel, PlantUML
                ↓
Niveau 2   pim/           PIM : agents et contrats indépendants de GAMA
                ↓
Niveau 3   psm/           PSM : métamodèle Ecore GAML + instance XMI
                ↓
Niveau 4   generator/     Transformation : PyEcore + Jinja2 → artefacts GAML
                ↓
Niveau 5   gama/          Exécution : projet GAMA, ids_sma.gaml, ids_gui
                ↑
Transverse ml/            Apprentissage (règles, forêt, fusion) → artefacts injectés
Transverse tests/         Garde-fous de non-régression (cible 0,810, invariants)
```

### Rôle de chaque niveau

| Niveau | Dossier | Question à laquelle il répond |
|---|---|---|
| 0 | `data/` | Quelles connexions alimentent train / test ? |
| 1 | `design/` | Que signifie le domaine ? Quels cas d’usage ? Quelles tensions tranchées ? |
| 2 | `pim/` | Comment les agents collaborent, sans parler GAML ? |
| 3 | `psm/` | Comment ces concepts se projettent sur un métamodèle GAML restreint ? |
| 4 | `generator/` | Comment produire GAML, encodage et forêt sans écrire le squelette à la main ? |
| 5 | `gama/` | Comment exécuter et observer la simulation ? |
| T | `ml/` | Comment obtenir règles, forêt et score de fusion reproductibles ? |
| T | `tests/` | Comment savoir qu’on n’a pas cassé le contrat de validation ? |

### Flux de production

```
design ──► pim ──► psm ──► generator ──► gama/models/
                              ▲              │
                              │              ├─ ids_sma.gaml      (modèle + agents)
                              │              ├─ generated/        (encodage, forêt)
                              │              └─ data/             (copie KDD pour Capture)
                         ml/artifacts/
```

Les chemins Python passent par `paths.py` : une seule référence pour `data/`, `ml/artifacts/`, `gama/models/`, etc.

---

## 3. Directives de projet

Ces règles sont opposables. Elles évitent que la chaîne IDM se dissolve en bricolage.

### 3.1 Édition du GAML

| Zone | Qui écrit | Règle |
|---|---|---|
| Hors `@user-*` | Générateur / maintenance contrôlée | Ne pas « bidouiller » au hasard : toute évolution structurelle passe par PSM ou gabarit, ou est assumée dans le monolithe documenté |
| `@user-begin` … `@user-end` | Humain | **Seul endroit** pour le métier (signatures, utilité, matrice de confusion) |
| `gama/models/generated/*` | Générateur uniquement | **Interdit** d’éditer à la main |

Zones métier actuelles dans `ids_sma.gaml` :

- `@user-begin(signatures_rm1_rm11)` : règles de détection (RM1–RM11)
- `@user-begin(calcul_utilite)` : fusion / utilité de décision
- `@user-begin(mise_a_jour_matrice_confusion)` : journal et métriques

### 3.2 Organisation du modèle GAMA

- Le modèle exécutable est un **monolithe** : `gama/models/ids_sma.gaml`.
- Sous GAMA 2025, découper en sous-`model` importés **ne partage pas** le `global` ni les types parent. Ce découpage a été tenté puis retiré.
- Projet à importer dans GAMA : **`gama/`** uniquement. Ignorer tout vestige `06-gama`.

### 3.3 Générateur

```bash
cd generator && python generer.py
```

- Par défaut, le générateur **refuse** d’écraser le monolithe maintenu à la main.
- L’option `forcer` existe pour les cas exceptionnels : elle peut détruire des correctifs hors zones `@user-*`.
- Avant / après régénération : `python tests/test_baseline.py`.

### 3.4 Machine learning

- Entraînement et évaluation vivent dans `ml/`.
- Les sorties stables sont dans `ml/artifacts/` (JSON de fusion, export forêt, paramètres d’encodage).
- La forêt de production est une **table de nœuds** (`foret_table.csv`) + parcours en GAML. Une démo `if/else` courte existe pour la lisibilité (`foret_demo.gaml`), ce n’est **pas** le même pouvoir prédictif.

### 3.5 Git et fichiers locaux

- Seul `README.md` est versionné parmi les `.md` (rapports locaux ignorés).
- Ne pas committer `.metadata/`, workspace Eclipse, ni `06-gama/`.
- Ne pas committer les gros binaires ML régénérables (voir `.gitignore`).

### 3.6 Validation

- Contrat Python : `python tests/test_baseline.py` (exactitude fusion ≈ 0,7885, invariants GAML).
- Contrat simulation : moniteurs GAMA, cible ≈ 81,0 % / 72,2 %, `taux_panne = 0`, `poids_ia = 0,35`, `lambda_fp = 0`.
- Les `[ALERTE]` console **ne valident pas** le système.

---

## 4. Architecture multi-agents

```
┌──────────┐   P1    ┌────────────┐   P2    ┌──────────┐
│ Capture  │ ──────► │ Extraction │ ──────► │ Décision │
└──────────┘         └────────────┘         └────┬─────┘
                                                 │ P3 query
                                    ┌────────────┼────────────┐
                                    ▼                         ▼
                               ┌─────────┐              ┌──────────┐
                               │ Règles  │              │    IA    │
                               └────┬────┘              └────┬─────┘
                                    │ inform                 │ inform / refuse
                                    └────────────┬───────────┘
                                                 ▼
                                            fusion / émission
                                      ┌──────────┴──────────┐
                                      ▼                     ▼
                                 ┌─────────┐          ┌──────────┐
                                 │ Alertes │          │ Journal  │
                                 └─────────┘          └──────────┘
```

| Agent | Responsabilité | Point d’attention |
|---|---|---|
| **Capture** | Lit N connexions / cycle depuis le CSV | Respecte la capacité de file Décision |
| **Extraction** | Encode vers ~122 features | Paramètres issus de `generated/encodage.gaml` |
| **Règles** | Signatures ; peut s’abstenir | Métier dans zone `@user-*` |
| **IA** | Parcourt la forêt (table CSV) | FSM ACTIF / EN_PANNE |
| **Décision** | File, consultation FIPA, fusion, émission | Modes nominal, dégradé, abandon |
| **Alertes** | Seuil de gravité × menace | Bruit console optionnel (`verbose_alertes`) |
| **Journal** | Matrice de confusion, exactitude, rappel | Seul agent qui voit l’étiquette réelle |

Communication métier : skill **FIPA** (`request`, `query`, `inform`, `refuse`). Compteurs et paramètres globaux : section `global`.

---

## 5. Problèmes, décisions, solutions

### 5.1 Tensions de cadrage (tranchées tôt)

| Problème | Risque si on ignore | Solution retenue |
|---|---|---|
| Énoncé « paquet » vs dataset connexions | Incohérence devant un jury | Unité simulée = **connexion** ; paquet hors périmètre d’exécution |
| Extraction « vide » (41 attributs déjà là) | Agent décoratif | Extraction = **préprocesseur** (one-hot, min-max, modalités inconnues) |
| « Ne pas écrire le GAML » vs métier à la main | Frontière floue | Zones `@user-*` préservées à la génération |
| PSM photocopie de la grammaire GAML | Peu de valeur IDM | Métamodèle **restreint** + projections PIM argumentées |
| Périmètre trop large en peu de temps | Chaîne cassée | Chaîne **étroite mais complète** |

### 5.2 Décisions d’implémentation (ce qu’on a réellement fait)

| Problème rencontré | Observation | Solution |
|---|---|---|
| Forêt en `if/else` géant | ~20 k lignes illisibles | Table CSV + parcours + démo INLINE séparée |
| Imports `species/*.gaml` | `AgentVue`, `donnees_nslkdd`, FIPA non résolus | Monolithe `ids_sma.gaml` |
| `do enregistrer_prediction` depuis Journal | Action globale introuvable sur l’espèce | `ask world { do enregistrer_prediction(...) }` |
| Spam `[ALERTE]` | Confusion avec la métrique | `verbose_alertes = false` ; valider sur moniteurs |
| Workspace Eclipse | Projet fantôme `06-gama` | Importer uniquement `gama/` |
| Régénération dangereuse | Écrase le monolithe corrigé | Garde dans `generer.py` (refus sauf `forcer`) |
| Plafond ~78,9 % sur R2L/U2R | Peu de signatures rares | RM9–RM11 + `poids_ia = 0,35` → ≈ 81,0 % |

### 5.3 Fusion décisionnelle

La Décision combine les distributions Règles et IA (poids `poids_ia`), applique une pénalité de faux positifs modulée par le niveau de menace, puis émet vers Alertes et Journal. Si un avis manque (panne / délai), mode **dégradé**. Si rien d’exploitable : **abandon** (compté, pas inventé).

---

## 6. Cible et lecture des résultats

Mesures de référence (Python, `ml/artifacts/resultats_fusion.json`), jeu `KDDTest+` :

| Source | Exactitude 5 classes | Rappel attaques |
|---|---|---|
| Règles seules (RM1–RM11) | ≈ 62,7 % | ≈ 62,9 % |
| IA seule | ≈ 76,5 % | ≈ 63,0 % |
| **Fusion (cible)** | **≈ 81,0 %** | **≈ 72,2 %** |

### Critères d’acceptation simulation

1. `taux_panne = 0` (mode nominal).
2. `poids_ia = 0,35` et `lambda_fp = 0` (alignés sur la référence Python).
3. Moniteur exactitude stabilisé vers **≈ 0,810**.
4. Moniteur rappel vers **≈ 0,722**.
5. Compteurs `decisions` et `journal` progressent **ensemble** (écart durable = bug de chaîne).
6. `degradees` et `abandons` restent à 0 en nominal (sauf paramétrage panne volontaire).

Ce qui **ne** constitue **pas** une validation : volume de lignes `[ALERTE]`, warnings des Toy Models GAMA, exactitude binaire seule.

Garde-fou sans ouvrir GAMA :

```bash
python tests/test_baseline.py
```

---

## 7. Ce qui a été construit

| Livrable | Contenu |
|---|---|
| Cadrage + CIM | Décisions d’architecture, diagrammes PlantUML (`design/`) |
| PIM | Agents, séquences nominal / dégradé, états Décision (`pim/`) |
| PSM | `gaml-psm.ecore`, `psm-ids-complet.xmi`, validateurs (`psm/`) |
| Générateur | Chargeur, gabarits Jinja2, zones protégées, oracle, transpileur forêt |
| ML | Prétraitement, règles, forêt, fusion, sweep, export artefacts |
| GAMA | Modèle exécutable, expérience GUI, CSV forêt, encodage généré |
| Qualité | `verifier_tout.py`, `tests/test_baseline.py` |

Le modèle GAMA actuel est **maintenu comme monolithe** (comportement validé à ~81,0 %). Le générateur reste la voie structurante pour encodage / forêt / squelette ; il ne doit pas écraser ce monolithe sans intention explicite.

---

## 8. Démarrage

### Prérequis

- Python 3.10 ou plus récent
- GAMA 2025.6.4
- Dépendances :

```bash
pip install pyecore jinja2 numpy pandas lxml scikit-learn
```

### Vérifier avant de simuler

```bash
python verifier_tout.py
python tests/test_baseline.py
python ml/evaluer_fusion.py
```

### Lancer GAMA

1. Ouvrir GAMA 2025.6.4.
2. Importer le projet **`gama/`** (File → Import → Existing Projects).
3. Ouvrir `models/ids_sma.gaml`.
4. Lancer l’expérience **`ids_gui`**.
5. Observer les moniteurs 6 (exactitude) et 7 (rappel).

Astuce : pour un smoke test UI, `Limite (0=tout)` ≈ `5000`. Pour la validation complète, laisser `0`.

Si GAMA propose encore `06-gama` : le fermer / le retirer du workspace, puis utiliser uniquement `gama/`.

---

## 9. Structure détaillée du dépôt

```
.
├── README.md                 # Documentation du dépôt (seul .md versionné)
├── .gitignore
├── paths.py                  # Racines : DATA, DESIGN, PIM, PSM, ML, GAMA…
├── verifier_tout.py          # Smoke test de la chaîne Python / artefacts
│
├── data/                     # [N0] NSL-KDD brut
│   ├── KDDTrain+.txt
│   ├── KDDTest+.txt
│   └── …
│
├── design/                   # [N1] CIM + cadrage
│   ├── 00-CADRAGE-….md       # (local, non versionné si *.md ignoré)
│   └── puml/                 # cas d’utilisation, états, flux
│
├── pim/                      # [N2] modèle indépendant de plateforme
│   └── puml/                 # classes, séquences, états décision
│
├── psm/                      # [N3] métamodèle + instance
│   ├── gaml-psm.ecore
│   ├── psm-ids-complet.xmi
│   └── puml/
│
├── generator/                # [N4] transformation vers GAML
│   ├── generer.py            # point d’entrée (garde monolithe)
│   ├── chargeur.py
│   ├── zones_protegees.py
│   ├── transpileur_foret.py
│   ├── oracle_simulation.py
│   └── gabarits/             # Jinja2
│
├── ml/                       # [T] apprentissage & évaluation
│   ├── constants.py
│   ├── preprocessing.py
│   ├── regles.py
│   ├── foret.py
│   ├── evaluer_fusion.py
│   ├── export_foret.py
│   └── artifacts/            # résultats figés (fusion, forêt, encodage)
│
├── gama/                     # [N5] projet à importer dans GAMA
│   └── models/
│       ├── ids_sma.gaml      # global + agents + expérience
│       ├── generated/        # encodage.gaml, foret_*. , CSV
│       └── data/             # copie lue par AgentCapture
│
└── tests/
    └── test_baseline.py      # contrat exactitude + invariants GAML
```

Les dossiers ne sont **pas** numérotés « tuto 00…07 » dans Git : la hiérarchie ci-dessus (N0…N5) est la directive d’organisation. Les documents locaux peuvent garder d’anciens préfixes de fichiers ; le dépôt public, lui, parle par **rôle**.

---

## 10. Paramètres de simulation

Expérience `ids_gui` :

| Paramètre | Rôle |
|---|---|
| Poids IA | Part de la forêt dans la fusion (0 = règles seules, 1 = IA seule) |
| Pénalité FP | Frein sur les classes d’attaque quand la menace est basse |
| Délai garde | Cycles avant mode dégradé / abandon |
| Seuil alerte | Gravité minimale pour compter une alerte |
| Log alertes | Active le spam console `[ALERTE]` |
| Débit capture | Connexions lues par cycle |
| Capacité file | Taille de file devant Décision |
| Limite | Sous-échantillon (`0` = tout le test) |
| p_panne / p_reprise | Panne et reprise de l’agent IA |

Défaut recommandé pour la cible 81,0 % : panne à **0**, limite à **0**, poids IA à **0,35**, pénalité FP à **0**.

---

## 11. Commandes de référence

```bash
# Contrat de non-régression (sans GAMA)
python tests/test_baseline.py

# Vérification large de la chaîne
python verifier_tout.py

# Mesures fusion Python
python ml/evaluer_fusion.py

# Oracle : transcription Python du métier des zones GAML
python generator/oracle_simulation.py

# Régénération (souvent refusée si monolithe maintenu)
cd generator && python generer.py
```

---

## Auteur

**Andassa**

Projet de démonstration : IDM + systèmes multi-agents + apprentissage, appliqués à la détection d’intrusions sur NSL-KDD.
