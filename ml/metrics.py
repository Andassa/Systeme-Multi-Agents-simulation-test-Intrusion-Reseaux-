"""Métriques 5 classes + vue binaire — source unique pour eval / fusion / sweep."""
from __future__ import annotations

import numpy as np

from constants import CLASSES, NB_CLASSES


def confusion(y, yp, k: int = NB_CLASSES) -> np.ndarray:
    m = np.zeros((k, k), dtype=int)
    for a, b in zip(y, yp):
        m[a, b] += 1
    return m


def measures(m: np.ndarray) -> dict:
    total = int(m.sum())
    vn, fp = int(m[0, 0]), int(m[0, 1:].sum())
    fn, vp = int(m[1:, 0].sum()), int(m[1:, 1:].sum())
    return {
        "exactitude_5_classes": float(np.trace(m) / total) if total else 0.0,
        "exactitude_binaire": float((vn + vp) / total) if total else 0.0,
        "rappel": float(vp / (vp + fn)) if vp + fn else 0.0,
        "taux_fp": float(fp / (fp + vn)) if fp + vn else 0.0,
        "rappel_par_classe": [
            float(m[k, k] / m[k].sum()) if m[k].sum() else 0.0
            for k in range(m.shape[0])
        ],
    }


def rapport(y, yp, titre: str = ""):
    """Compte-rendu lisible (sweep / debug). Retourne (texte, matrice, exactitude)."""
    m = confusion(y, yp)
    acc = float((np.asarray(y) == np.asarray(yp)).mean())
    lignes = [
        f"--- {titre} ---",
        f"Exactitude globale : {100 * acc:.2f}%",
        "",
        f"{'Classe':<8} {'Support':>8} {'Prec.':>8} {'Rappel':>8} {'F1':>8}",
    ]
    for k, nom in enumerate(CLASSES):
        tp = m[k, k]
        fp = m[:, k].sum() - tp
        fn = m[k, :].sum() - tp
        p = tp / (tp + fp) if tp + fp else 0.0
        r = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * p * r / (p + r) if p + r else 0.0
        lignes.append(
            f"{nom:<8} {m[k].sum():8d} {100 * p:7.1f}% {100 * r:7.1f}% {100 * f1:7.1f}%"
        )

    yb = (np.asarray(y) != 0).astype(int)
    ypb = (np.asarray(yp) != 0).astype(int)
    tp = int(((yb == 1) & (ypb == 1)).sum())
    fp = int(((yb == 0) & (ypb == 1)).sum())
    fn = int(((yb == 1) & (ypb == 0)).sum())
    tn = int(((yb == 0) & (ypb == 0)).sum())
    n = len(y)
    lignes += [
        "",
        f"Vue binaire  TP={tp} FP={fp} FN={fn} TN={tn}",
        "  Exactitude %.2f%%  Precision %.2f%%  Rappel %.2f%%  Taux FP %.2f%%"
        % (
            100 * (tp + tn) / n,
            100 * tp / (tp + fp) if tp + fp else 0,
            100 * tp / (tp + fn) if tp + fn else 0,
            100 * fp / (fp + tn) if fp + tn else 0,
        ),
        "",
        "Matrice (lignes=réel, colonnes=prédit) :",
        "        " + "".join(f"{c:>9}" for c in CLASSES),
    ]
    for k, nom in enumerate(CLASSES):
        lignes.append(f"{nom:<8}" + "".join(f"{v:9d}" for v in m[k]))
    return "\n".join(lignes), m, acc
