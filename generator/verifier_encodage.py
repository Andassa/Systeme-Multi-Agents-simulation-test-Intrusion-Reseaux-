#!/usr/bin/env python3
"""
Vérification croisée de l'encodage généré.

Question posée : l'action GAML `encoder_connexion` produit-elle EXACTEMENT le
vecteur que preprocessing.py a présenté à la forêt pendant l'apprentissage ?

Pourquoi cette question est la plus importante de l'Étape 6
------------------------------------------------------------
Un décalage d'un seul indice dans les blocs one-hot donnerait un vecteur
parfaitement valide et parfaitement faux : la forêt lirait « service=http »
là où le modèle a appris « flag=SF ». La simulation tournerait, afficherait
des courbes, produirait des alertes — avec des performances dégradées et
aucune erreur d'exécution pour le signaler.

C'est la même famille d'erreur que la comparaison stricte/large trouvée à
l'Étape 5, et elle se vérifie de la même façon : sur données réelles, contre
la référence.
"""
import os
import sys

import numpy as np
import pandas as pd

ICI = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.dirname(ICI)
sys.path.insert(0, ICI)

import generateur_encodage as GE  # noqa: E402


def chemin_test():
    for base in (os.path.join(RACINE, "data"),
                 os.path.join(RACINE, "gama", "models", "data")):
        p = os.path.join(base, "KDDTest+.txt")
        if os.path.exists(p):
            return p
    raise FileNotFoundError("KDDTest+.txt introuvable")


def main(n=500):
    params = GE.charger_parametres()
    ctx = GE.contexte([0], "-")

    brut = pd.read_csv(chemin_test(), names=GE.COLONNES_BRUTES, nrows=n)
    reference = np.load(os.path.join(RACINE, "ml", "artifacts", "donnees.npz"))["Xte"][:n]

    ecart_max, lignes_fausses, total_inconnues = 0.0, 0, 0
    premiere_faute = None

    for i in range(len(brut)):
        ligne = brut.iloc[i].tolist()
        v, inconnues = GE.encoder_python(ligne, ctx, params)
        total_inconnues += inconnues
        d = np.abs(np.array(v) - reference[i])
        if d.max() > 1e-9:
            lignes_fausses += 1
            if premiere_faute is None:
                j = int(d.argmax())
                premiere_faute = (i, j, params["features"][j],
                                  v[j], float(reference[i][j]))
        ecart_max = max(ecart_max, float(d.max()))

    print("Vérification croisée de l'encodage")
    print("-" * 70)
    print(f"  lignes comparées            : {len(brut)}")
    print(f"  composantes par vecteur     : {len(params['features'])}")
    print(f"  écart max |gaml - reference| : {ecart_max:.3e}")
    print(f"  lignes divergentes          : {lignes_fausses}")
    print(f"  modalités inconnues du train: {total_inconnues}")
    if premiere_faute:
        i, j, nom, a, b = premiere_faute
        print()
        print(f"  première divergence : ligne {i}, composante {j} ({nom})")
        print(f"    encodage GAML : {a}")
        print(f"    référence     : {b}")
    print()
    ok = lignes_fausses == 0 and ecart_max < 1e-9
    print("  =>", "ENCODAGE CONFORME AU MODÈLE ENTRAÎNÉ" if ok
          else "DIVERGENCE — la simulation ne verrait pas les mêmes vecteurs")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
