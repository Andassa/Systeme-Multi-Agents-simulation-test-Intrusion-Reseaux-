#!/usr/bin/env python3
"""Sélection d'hyperparamètres sur validation (train split). KDDTest+ réservé à la fin."""
from __future__ import annotations

import json
import sys
import time

import numpy as np

import foret
from data_paths import artifact
from metrics import rapport


def main() -> int:
    d = np.load(artifact("donnees.npz"))
    xtr, ytr = d["Xtr"], d["ytr"]
    rs = np.random.RandomState(0)
    perm = rs.permutation(len(ytr))
    ncut = int(0.8 * len(ytr))
    xa, ya = xtr[perm[:ncut]], ytr[perm[:ncut]]
    xv, yv = xtr[perm[ncut:]], ytr[perm[ncut:]]
    print(f"apprentissage {len(ya)} / validation {len(yv)}", flush=True)

    res = []
    for prof in (6, 8, 10, 12, 14):
        t0 = time.time()
        m = foret.entrainer(xa, ya, n_arbres=20, max_depth=prof, verbose=False)
        nn = sum(a.n_nodes for a in m["arbres"])
        acc_v = (foret.predire_proba(m, xv).argmax(1) == yv).mean()
        acc_a = (foret.predire_proba(m, xa).argmax(1) == ya).mean()
        res.append({
            "type": "profondeur", "n_arbres": 20, "profondeur": prof,
            "noeuds": int(nn), "acc_appr": float(acc_a),
            "acc_valid": float(acc_v), "secondes": time.time() - t0,
        })
        print(
            f"prof={prof:2d}  noeuds={nn:6d}  appr={acc_a:.4f}  "
            f"valid={acc_v:.4f}",
            flush=True,
        )

    best = max(res, key=lambda r: r["acc_valid"])["profondeur"]
    print("profondeur retenue :", best, flush=True)

    for na in (10, 20, 30, 50):
        t0 = time.time()
        m = foret.entrainer(xa, ya, n_arbres=na, max_depth=best, verbose=False)
        nn = sum(a.n_nodes for a in m["arbres"])
        acc_v = (foret.predire_proba(m, xv).argmax(1) == yv).mean()
        res.append({
            "type": "n_arbres", "n_arbres": na, "profondeur": best,
            "noeuds": int(nn), "acc_valid": float(acc_v),
            "secondes": time.time() - t0,
        })
        print(f"arbres={na:2d}  noeuds={nn:6d}  valid={acc_v:.4f}", flush=True)

    for eq in (True, False):
        m = foret.entrainer(
            xa, ya, n_arbres=20, max_depth=best, equilibrer=eq, verbose=False
        )
        yp = foret.predire_proba(m, xv).argmax(1)
        texte, _m, acc = rapport(yv, yp, f"VALIDATION ponderation={eq}")
        print("\n" + texte, flush=True)
        res.append({"type": "ponderation", "equilibrer": eq, "acc_valid": float(acc)})

    artifact("sweep_resultats.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print("=== SWEEP TERMINE ===", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
