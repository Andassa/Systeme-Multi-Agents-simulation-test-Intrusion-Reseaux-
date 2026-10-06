#!/usr/bin/env python3
"""Compare la transcription GAML de encoder_connexion au vecteur de preprocessing.py.

Un décalage d'indice dans un bloc one-hot laisse un vecteur de taille 122.
La forêt lit alors une autre variable. Contrôle sur les premières lignes de KDDTest+.
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
