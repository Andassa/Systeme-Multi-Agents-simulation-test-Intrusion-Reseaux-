#!/usr/bin/env python3
"""Export forêt → artifacts/foret_export.json (entrée transpileur GAML)."""
from __future__ import annotations

import json
import pickle
import sys

from data_paths import artifact


def arbre_vers_dict(a, edges) -> dict:
    seuils = []
    for i in range(a.n_nodes):
        f = int(a.feature[i])
        if f < 0:
            seuils.append(None)
            continue
        b = int(a.threshold[i])
        e = edges[f]
        # bin <= b  <=>  valeur <= edges[f][b] (comparaison large)
        seuils.append(float(e[b]) if b < len(e) else float("inf"))
    return {
        "feature": [int(v) for v in a.feature],
        "seuil": seuils,
        "gauche": [int(v) for v in a.left],
        "droite": [int(v) for v in a.right],
        "valeur": [[round(float(x), 6) for x in v] for v in a.value],
        "n_noeuds": int(a.n_nodes),
    }


def main() -> int:
    m = pickle.load(open(artifact("modele_final.pkl"), "rb"))
    prm = json.loads(artifact("parametres_encodage.json").read_text(encoding="utf-8"))
    arbres = [arbre_vers_dict(a, m["edges"]) for a in m["arbres"]]
    tot = sum(t["n_noeuds"] for t in arbres)
    internes = sum(sum(1 for f in t["feature"] if f >= 0) for t in arbres)

    payload = {
        "classes": prm["classes"],
        "features": prm["features"],
        "n_features": len(prm["features"]),
        "n_arbres": len(arbres),
        "profondeur_max": 12,
        "n_noeuds_total": tot,
        "n_internes": internes,
        "n_feuilles": tot - internes,
        "arbres": arbres,
    }
    sortie = artifact("foret_export.json")
    sortie.write_text(json.dumps(payload), encoding="utf-8")
    print(f"arbres={len(arbres)}  noeuds={tot}  → {sortie}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
