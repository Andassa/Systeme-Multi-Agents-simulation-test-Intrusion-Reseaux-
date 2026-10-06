#!/usr/bin/env python3
"""Référence fusion règles + IA → ml/artifacts/resultats_fusion.json."""
from __future__ import annotations

import json
import pickle
import sys

import pandas as pd

import foret as F
import regles as R
from constants import CLASSES, COLS
from data_paths import ROOT, artifact, find_nslkdd
from metrics import confusion, measures


def main(poids_ia: float = 0.35) -> int:
    data = __import__("numpy").load(artifact("donnees.npz"))
    xte, yte = data["Xte"], data["yte"]
    modele = pickle.load(open(artifact("modele_final.pkl"), "rb"))
    df = pd.read_csv(find_nslkdd("KDDTest+.txt"), names=COLS)

    p_ia = F.predire_proba(modele, xte)
    p_rg, _ids, tirs = R.evaluer(df)
    p_fu = poids_ia * p_ia + (1.0 - poids_ia) * p_rg

    resultats = {}
    for nom, p in (("regles", p_rg), ("ia", p_ia), ("fusion", p_fu)):
        m = confusion(yte, p.argmax(1))
        resultats[nom] = measures(m)
        resultats[nom]["matrice"] = m.tolist()

    resultats["meta"] = {
        "n": int(len(yte)),
        "poids_ia": poids_ia,
        "abstentions": int((~tirs).sum()),
        "taux_abstention": float((~tirs).mean()),
        "base_regles": "v4 — RM1-RM11, confiances = précision train, poids_ia=0.35",
    }

    sortie = artifact("resultats_fusion.json")
    sortie.write_text(json.dumps(resultats, indent=1), encoding="utf-8")

    print("Référence fusion (v4)")
    print(f"  n={len(yte)}  abstentions={resultats['meta']['abstentions']}")
    for nom in ("regles", "ia", "fusion"):
        r = resultats[nom]
        print(
            f"  {nom:<8} exact5={100 * r['exactitude_5_classes']:.2f}%  "
            f"rappel={100 * r['rappel']:.2f}%"
        )
    print(f"  → {sortie.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
