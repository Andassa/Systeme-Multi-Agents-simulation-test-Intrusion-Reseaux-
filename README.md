# IDS multi-agents NSL-KDD

Détection sur les connexions NSL-KDD, sept agents, GAMA 2025.6.4. Capture lit le fichier, Extraction construit le vecteur, Règles et IA répondent en parallèle, Décision fusionne, Alertes et Journal enregistrent.

Le squelette GAML, l'encodage et la table de forêt sortent de `psm/` via `generator/`. Le métier est dans `gama/models/ids_sma.gaml`, entre `@user-begin` et `@user-end`.

## Temps

GAMA avance par cycle : `reflex`, messages FIPA (`request`, `query`, `inform`, `refuse`).

États d'une connexion : `design/puml/mc-cycle-vie-connexion.puml`. Messages e3 à e9 : `design/puml/mc-flux-evenements.puml`.

## DEVS

`devs/` reprend les sept agents en DEVS parallèle. L'unité de temps est le cycle. Chaque atome a un temps restant (`ta`). Une sortie est livrée dans le même instant : le délai est dans l'atome, pas dans le lien.

| Fichier | Rôle |
|---|---|
| `devs/atomique.py` | Atome et coordinateur (micro-pas à temps constant, puis avance du cycle) |
| `devs/reseau.py` | Capture, Extraction, Règles, IA, Décision, Alertes, Journal, couplages P1–P5 |

Règles et IA sont des fonctions `evaluer(idc)` qui rendent une distribution sur les cinq classes. La fusion est celle de la zone `calcul_utilite`. Ce module ne lit pas NSL-KDD et ne rejoue pas `foret_table.csv`. Le score 0,8102 reste celui de `ml/artifacts/resultats_fusion.json` et de GAMA.

Correspondance avec `ids_sma.gaml` :

| Situation | Effet |
|---|---|
| `latence = 0` | Réponse dans le pas, comme un reflex qui vide sa boîte |
| `latence = inf` | Pas de réponse. À `delai_garde`, dégradé s'il reste un verdict, abandon sinon |
| Panne (`taux_panne`) | `refuse` après le tirage. Dégradé immédiat si un autre verdict est déjà là (`nb_refus_recus > 0`) |
| Deux réponses exactement à l'échéance | Nominal. La confluence prend la fusion, pas le dégradé |
| Deux abstentions | Abandon, pas de P4 ni de P5 |
| File pleine | Rejet. Une connexion active plus `capacite` en attente |

`python -m devs` enchaîne cinq scénarios : nominal (trace P1→P5 dans le cycle 0), panne certaine, IA muette, les deux muets, file avec un service de 2 cycles. `tests/test_devs.py` fixe ces cas. Aucune dépendance hors la bibliothèque standard.

## Mesures

NSL-KDD. Train : 125 973 lignes, `data/KDDTrain+.txt`. Test : 22 544 lignes, `data/KDDTest+.txt`. Classes : NORMAL, DOS, PROBE, R2L, U2R. Une ligne est une connexion déjà agrégée (41 attributs).

Chiffres Python sur KDDTest+, `ml/artifacts/resultats_fusion.json`, poids IA 0,35 :

| Source | Exactitude, 5 classes | Rappel attaques |
|---|---:|---:|
| Règles RM1–RM11 | 0,6273 | 0,6288 |
| Forêt seule | 0,7646 | 0,6298 |
| Fusion | 0,8102 | 0,7224 |

`tests/test_baseline.py` fige la fusion à 0,8102377572746629 et 0,7223564248422037, tolérance 1e-3.

En simulation, même cible avec `taux_panne = 0`, `poids_ia = 0.35`, `lambda_fp = 0`, `limite_connexions = 0`. `nb_decisions` et le compteur du journal avancent ensemble. `nb_degradees` et `nb_abandons` restent à 0 si l'agent IA ne tombe pas en panne.

`verbose_alertes` vaut `false`. Le nombre de lignes `[ALERTE]` ne mesure pas le détecteur.

## Lancer

Python 3.10 ou plus récent.

```bash
pip install pyecore jinja2 numpy pandas lxml scikit-learn
python tests/test_baseline.py
python tests/test_devs.py
python verifier_tout.py
```

`verifier_tout.py` n'ouvre pas GAMA et ne compile pas le GAML.

GAMA 2025.6.4 : importer le dossier `gama/`, ouvrir `models/ids_sma.gaml`, expérience `ids_gui`. Retirer du workspace un éventuel projet `06-gama`.

`limite_connexions = 5000` coupe le fichier pour un passage court. La mesure ci-dessus se fait avec `0`.

```bash
cd generator
python generer.py
```

Sans `--forcer`, `generer.py` n'écrase pas `ids_sma.gaml`. Avec `--forcer`, les corps `@user-begin` / `@user-end` sont relus puis réécrits. `gama/models/generated/` vient du générateur.

## Agents

| Agent | Rôle |
|---|---|
| Capture | Lit `debit_capture` lignes par cycle. S'arrête quand la file de Décision atteint `capacite_file`. |
| Extraction | 122 composantes : 38 numériques ramenées au min-max du train, puis one-hot. Bornes et vocabulaires dans `generated/encodage.gaml`. |
| Règles | RM1–RM11, peut s'abstenir. Zone `signatures_rm1_rm11`. |
| IA | Parcours de `generated/foret_table.csv`. États ACTIF et EN_PANNE. `foret_demo.gaml` est une cascade courte, distincte de cette table. |
| Décision | File, requêtes FIPA, fusion, émission. Nominal, dégradé après `delai_garde` cycles, ou abandon. Zone `calcul_utilite`. |
| Alertes | Compte une alerte si gravité × menace dépasse `seuil_alerte`. |
| Journal | Seul agent qui lit l'étiquette. Matrice 5×5, exactitude, rappel. Zone `mise_a_jour_matrice_confusion`. |

La fusion mélange les deux distributions avec `poids_ia`, puis applique `lambda_fp` selon `niveau_menace`.

## Dossiers

```
data/          NSL-KDD
design/puml/   cas d'utilisation, états, flux
pim/puml/      classes, séquences, états de Décision
psm/           gaml-psm.ecore, instances XMI
generator/     chargement PyEcore ou xml.etree, gabarits Jinja2
ml/            règles, forêt, fusion ; JSON dans ml/artifacts/
gama/          projet GAMA ; modèle models/ids_sma.gaml
devs/          même protocole, DEVS parallèle (cycle = unité de temps)
tests/         test_baseline.py, test_devs.py
paths.py       chemins des dossiers
```

Git ignore les autres fichiers `.md`.

## Paramètres `ids_gui`

| Paramètre | Défaut | Rôle |
|---|---:|---|
| poids_ia | 0.35 | Poids de la forêt dans la fusion |
| lambda_fp | 0.0 | Pénalité sur les classes d'attaque |
| delai_garde | 3 | Cycles avant dégradé ou abandon |
| seuil_alerte | 0.5 | Seuil de comptage |
| verbose_alertes | false | Affiche `[ALERTE]` |
| debit_capture | 10 | Lignes lues par cycle |
| capacite_file | 200 | Taille de la file de Décision |
| limite_connexions | 0 | 0 lit tout le test |
| taux_panne | 0.0 | Panne de l'IA, par cycle |
| taux_reprise | 0.20 | Reprise de l'IA, par cycle |

## Commandes

```bash
python tests/test_baseline.py
python verifier_tout.py
python ml/evaluer_fusion.py
python generator/oracle_simulation.py
python -m devs
python tests/test_devs.py
cd generator && python generer.py
```

`oracle_simulation.py` rejoue en Python les trois zones métier sur KDDTest+. Il ne démarre pas GAMA.

`python -m devs` non plus. Il imprime les cinq scénarios de protocole (nominal, panne, IA muette, silence, file).
