from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ml"))

from constants import CAT, COLS, label_to_class  # noqa: E402
from data_paths import artifact, find_nslkdd  # noqa: E402
from regles import evaluer as evaluer_regles  # noqa: E402


def charger():
    prm = json.loads(artifact("parametres_encodage.json").read_text(encoding="utf-8"))
    foret = json.loads(artifact("foret_export.json").read_text(encoding="utf-8"))
    df = pd.read_csv(find_nslkdd("KDDTest+.txt"), names=COLS)
    y = df["label"].map(label_to_class).to_numpy(dtype=np.int64)
    x = _encoder(df.drop(columns=["label", "difficulty"]), prm)
    p_rg, _rid, _fire = evaluer_regles(df)
    p_ia = _predire(foret["arbres"], x)
    return y, np.asarray(p_rg, dtype=np.float64), np.asarray(p_ia, dtype=np.float64)


def _encoder(x: pd.DataFrame, prm: dict) -> np.ndarray:
    vocab = prm["vocabulaires"]
    num = prm["colonnes_numeriques"]
    parts = [x[c].to_numpy(dtype=np.float64).reshape(-1, 1) for c in num]
    for c in CAT:
        mods = vocab[c]
        idx = {m: i for i, m in enumerate(mods)}
        oh = np.zeros((len(x), len(mods)), dtype=np.float64)
        for r, m in enumerate(x[c].to_numpy()):
            j = idx.get(m, -1)
            if j >= 0:
                oh[r, j] = 1.0
        parts.append(oh)
    brut = np.hstack(parts)
    mn = np.asarray(prm["min"], dtype=np.float64)
    mx = np.asarray(prm["max"], dtype=np.float64)
    rng = np.where(mx - mn == 0, 1.0, mx - mn)
    return np.clip((brut - mn) / rng, 0.0, 1.0)


def _predire(arbres, x: np.ndarray) -> np.ndarray:
    n = x.shape[0]
    acc = np.zeros((n, 5), dtype=np.float64)
    for arbre in arbres:
        feat = np.asarray(arbre["feature"], dtype=np.int32)
        seuil = np.asarray(
            [0.0 if s is None else s for s in arbre["seuil"]], dtype=np.float64
        )
        gauche = np.asarray(arbre["gauche"], dtype=np.int32)
        droite = np.asarray(arbre["droite"], dtype=np.int32)
        valeur = np.asarray(arbre["valeur"], dtype=np.float64)
        node = np.zeros(n, dtype=np.int32)
        actif = feat[node] >= 0
        while actif.any():
            ii = np.flatnonzero(actif)
            f = feat[node[ii]]
            go_l = x[ii, f] <= seuil[node[ii]]
            node[ii] = np.where(go_l, gauche[node[ii]], droite[node[ii]])
            actif[ii] = feat[node[ii]] >= 0
        acc += valeur[node]
    return acc / len(arbres)
