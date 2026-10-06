#!/usr/bin/env python3
"""
Transpileur de forêt aléatoire — ADR-03 bis, double génération.

Entrée  : ml/artifacts/foret_export.json (format neutre produit à l'Étape 3)
Sorties : selon ClassifierResource.strategieGeneration
            TABLE  -> table de nœuds aplatie (CSV) + action GAML de parcours itératif
            INLINE -> cascade if/else lisible, sous-forêt réduite

Les deux cibles sont produites depuis la MÊME source. C'est le point de
variation qui rend la séparation modèle/implémentation observable plutôt
que revendiquée.

Point de sémantique à ne pas rater
----------------------------------
L'entraînement discrétise chaque variable en intervalles (quantiles du train)
et un nœud interne teste `bin(x) <= seuil_bin`. L'export a converti le seuil
en valeur réelle : `edges[f][b]`.

    bin(x) = searchsorted(edges, x, side='left')
           = plus petit indice i tel que edges[i] >= x

    donc   bin(x) <= b   <=>   edges[b] >= x   <=>   x <= edges[b]

La condition GAML est donc `x <= seuil`, comparaison LARGE. Le commentaire
de export_foret.py annonçait une comparaison stricte : c'est faux, et l'erreur
est invisible sauf sur les points exactement égaux à un seuil — c'est-à-dire
précisément sur les variables binaires one-hot, où la quasi-totalité des
valeurs valent 0 ou 1. La fonction verifier_equivalence() ci-dessous tranche
la question par la mesure plutôt que par le raisonnement.
"""
import json
import os
import sys

ICI = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.dirname(ICI)
SOURCE = os.path.join(RACINE, "ml", "artifacts", "foret_export.json")


# ==========================================================================
# Aplatissement : N arbres -> une table unique à indices absolus
# ==========================================================================
def aplatir(foret, n_arbres=None, profondeur_max=None):
    """
    Produit (lignes, racines).

    lignes : [feature, seuil, gauche, droite, p0..p4] par nœud, indices absolus.
             feature = -1 pour une feuille.
    racines : indice absolu de la racine de chaque arbre.

    Une table unique plutôt qu'une matrice à trois dimensions : GAML manipule
    beaucoup plus simplement une liste de listes qu'une matrice 3D, et le
    parcours devient une simple boucle d'indices.
    """
    arbres = foret["arbres"][: n_arbres or len(foret["arbres"])]
    K = len(foret["classes"])
    lignes, racines = [], []

    for arbre in arbres:
        base = len(lignes)
        racines.append(base)
        # correspondance indice local -> indice absolu, en tenant compte de
        # l'élagage éventuel en profondeur
        profondeur = _profondeurs(arbre)
        garde = (lambda i: profondeur[i] >= profondeur_max) if profondeur_max \
            else (lambda i: False)

        remap, n = {}, 0
        for i in range(arbre["n_noeuds"]):
            remap[i] = base + n
            n += 1

        for i in range(arbre["n_noeuds"]):
            est_feuille = arbre["gauche"][i] == -1 or garde(i)
            if est_feuille:
                lignes.append([-1, 0.0, -1, -1] + list(arbre["valeur"][i]))
            else:
                lignes.append([
                    arbre["feature"][i],
                    arbre["seuil"][i] if arbre["seuil"][i] is not None else 0.0,
                    remap[arbre["gauche"][i]],
                    remap[arbre["droite"][i]],
                ] + list(arbre["valeur"][i]))
        assert len(lignes) - base == arbre["n_noeuds"]
        _ = K
    return lignes, racines


def _profondeurs(arbre):
    """Profondeur de chaque nœud, par parcours depuis la racine."""
    prof = [0] * arbre["n_noeuds"]
    pile = [(0, 0)]
    while pile:
        i, d = pile.pop()
        prof[i] = d
        if arbre["gauche"][i] != -1:
            pile.append((arbre["gauche"][i], d + 1))
            pile.append((arbre["droite"][i], d + 1))
    return prof


# ==========================================================================
# Cible TABLE
# ==========================================================================
def ecrire_csv(lignes, classes, chemin):
    entetes = ["feature", "seuil", "gauche", "droite"] + \
              ["p_" + c for c in classes]
    os.makedirs(os.path.dirname(chemin), exist_ok=True)
    with open(chemin, "w", encoding="utf-8") as f:
        f.write(",".join(entetes) + "\n")
        for L in lignes:
            f.write("%d,%.6f,%d,%d," % (L[0], L[1], L[2], L[3]))
            f.write(",".join("%.6f" % v for v in L[4:]) + "\n")
    return chemin


# ==========================================================================
# Cible INLINE — cascade if/else lisible
# ==========================================================================
def cascade_gaml(foret, n_arbres, profondeur_max, noms_features, indent="        "):
    """
    Cascade if/else pour une sous-forêt réduite.

    Cette cible est un modèle DIFFÉRENT, moins performant, non un rendu
    alternatif du même modèle. Le mémoire doit le dire : prétendre le
    contraire se verrait à la première question du jury.
    """
    K = len(foret["classes"])
    lignes = []
    for t, arbre in enumerate(foret["arbres"][:n_arbres]):
        lignes.append(f"{indent}// ---- arbre {t} ----")
        lignes += _cascade_noeud(arbre, 0, 0, profondeur_max, K,
                                 noms_features, indent)
    return "\n".join(lignes)


def _cascade_noeud(arbre, i, prof, prof_max, K, noms, indent):
    pad = indent + "    " * prof
    feuille = arbre["gauche"][i] == -1 or prof >= prof_max
    if feuille:
        v = arbre["valeur"][i]
        aff = " ".join("acc[%d] <- acc[%d] + %.4f;" % (k, k, v[k])
                       for k in range(K))
        return [f"{pad}{aff}"]

    f = arbre["feature"][i]
    s = arbre["seuil"][i]
    nom = noms[f] if f < len(noms) else f"f{f}"
    out = [f"{pad}// {nom}",
           f"{pad}if (v[{f}] <= {s:.6f}) {{"]
    out += _cascade_noeud(arbre, arbre["gauche"][i], prof + 1, prof_max, K,
                          noms, indent)
    out.append(f"{pad}}} else {{")
    out += _cascade_noeud(arbre, arbre["droite"][i], prof + 1, prof_max, K,
                          noms, indent)
    out.append(f"{pad}}}")
    return out


# ==========================================================================
# VÉRIFICATION — la transpilation est-elle exacte ?
# ==========================================================================
def parcourir(lignes, racines, x, strict=False):
    """
    Réimplémentation en Python de l'algorithme que le GAML généré exécutera.
    Volontairement écrite en boucles explicites, sans numpy : c'est une
    transcription du GAML, pas une seconde implémentation numpy qui pourrait
    masquer un écart par des raccourcis vectoriels.

    strict=True reproduit la comparaison `<` (annoncée à tort par le
    commentaire de export_foret.py). Conservé pour que le test de non-régression
    puisse montrer l'écart, plutôt que d'affirmer que la comparaison large est
    la bonne.
    """
    K = len(lignes[0]) - 4
    acc = [0.0] * K
    for r in racines:
        n = r
        while lignes[n][0] >= 0:
            f, s, g, d = lignes[n][0], lignes[n][1], lignes[n][2], lignes[n][3]
            va_gauche = (x[f] < s) if strict else (x[f] <= s)
            n = g if va_gauche else d
        for k in range(K):
            acc[k] += lignes[n][4 + k]
    return [a / len(racines) for a in acc]


def verifier_equivalence(foret, lignes, racines, n_echantillons=2000):
    """
    Compare la table transpilée à la forêt d'origine sur des données réelles.

    C'est LA vérification qui compte : elle établit que le GAML exécutera le
    même classifieur que celui mesuré à l'Étape 3. Sans elle, toutes les
    métriques du rapport ML seraient sans rapport avec la simulation.
    """
    import numpy as np
    sys.path.insert(0, os.path.join(RACINE, "ml"))
    import pickle
    import foret as mod_foret

    d = np.load(os.path.join(RACINE, "ml", "artifacts", "donnees.npz"))
    Xte = d["Xte"][:n_echantillons]
    modele = pickle.load(
        open(os.path.join(RACINE, "ml", "artifacts", "modele_final.pkl"), "rb"))

    reference = mod_foret.predire_proba(modele, Xte)

    resultats = {}
    for strict in (False, True):
        ecart_max, desaccords = 0.0, 0
        for i in range(Xte.shape[0]):
            p = parcourir(lignes, racines, Xte[i], strict=strict)
            ecart_max = max(ecart_max, max(abs(p[k] - reference[i][k])
                                           for k in range(len(p))))
            if int(np.argmax(p)) != int(np.argmax(reference[i])):
                desaccords += 1
        resultats["strict" if strict else "large"] = (ecart_max, desaccords)
    return resultats, Xte.shape[0]


# ==========================================================================
def charger(chemin=SOURCE):
    with open(chemin, encoding="utf-8") as f:
        return json.load(f)


if __name__ == "__main__":
    foret = charger()
    lignes, racines = aplatir(foret)
    print("Forêt source : %d arbres, %d nœuds, %d classes, %d variables"
          % (foret["n_arbres"], foret["n_noeuds_total"],
             len(foret["classes"]), foret["n_features"]))
    print("Table aplatie : %d lignes, %d racines" % (len(lignes), len(racines)))

    # Même destination que generer.py. Deux chemins divergents produisaient
    # deux tables : GAMA lisait celle de models/generated/, tandis que le
    # lancement autonome du transpileur en écrivait une autre à côté, jamais
    # lue et jamais mise à jour ensemble.
    csv = ecrire_csv(lignes, foret["classes"],
                     os.path.join(RACINE, "gama", "models", "generated",
                                  "foret_table.csv"))
    print("CSV écrit    :", os.path.relpath(csv, RACINE),
          "(%.2f Mo)" % (os.path.getsize(csv) / 1e6))

    src = cascade_gaml(foret, n_arbres=3, profondeur_max=4,
                       noms_features=foret["features"])
    print("Cascade INLINE : %d lignes GAML (3 arbres, profondeur 4)"
          % len(src.splitlines()))

    print()
    print("Vérification d'équivalence sur données réelles (KDDTest+)")
    print("-" * 62)
    res, n = verifier_equivalence(foret, lignes, racines)
    print("  échantillons : %d" % n)
    for nom, (ecart, desac) in res.items():
        cmp_ = "x <= seuil" if nom == "large" else "x <  seuil"
        print("  %-6s (%s) : écart max %.3e, désaccords d'argmax %4d (%.1f %%)"
              % (nom, cmp_, ecart, desac, 100.0 * desac / n))

    ecart_l, desac_l = res["large"]
    # Seuil à 1e-6 et non 0 : export_foret.py arrondit les distributions de
    # feuilles à 6 décimales. L'écart résiduel est cet arrondi, pas une erreur
    # de transpilation — vérifié par max|somme(valeur) - 1| = 1.0e-06.
    exact = desac_l == 0 and ecart_l < 1e-6
    print()
    print("  =>", "TRANSPILATION EXACTE (aux 6 décimales de l'export)" if exact
          else "ÉCART DÉTECTÉ — ne pas générer")
