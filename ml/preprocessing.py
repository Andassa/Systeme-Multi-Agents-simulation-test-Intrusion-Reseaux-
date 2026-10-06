#!/usr/bin/env python3
"""Prétraitement NSL-KDD → artifacts/donnees.npz + parametres_encodage.json."""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd

from constants import CAT, CLASSES, COLS, label_to_class
from data_paths import artifact, find_nslkdd


def load_split(filename: str):
    df = pd.read_csv(find_nslkdd(filename), names=COLS)
    y = df["label"].map(label_to_class).values.astype(np.int64)
    x = df.drop(columns=["label", "difficulty"])
    return x, y


def build_encoder(x_train: pd.DataFrame):
    vocab = {c: sorted(x_train[c].unique().tolist()) for c in CAT}
    num = [c for c in x_train.columns if c not in CAT]
    return vocab, num


def encode(x: pd.DataFrame, vocab: dict, num: list):
    parts, names = [], []
    for c in num:
        parts.append(x[c].values.astype(np.float64).reshape(-1, 1))
        names.append(c)
    for c in CAT:
        mods = vocab[c]
        idx = {m: i for i, m in enumerate(mods)}
        oh = np.zeros((len(x), len(mods)), dtype=np.float64)
        for r, m in enumerate(x[c].values):
            j = idx.get(m, -1)
            if j >= 0:
                oh[r, j] = 1.0
        parts.append(oh)
        names += [f"{c}={m}" for m in mods]
    return np.hstack(parts), names


def main() -> int:
    xtr_raw, ytr = load_split("KDDTrain+.txt")
    xte_raw, yte = load_split("KDDTest+.txt")
    vocab, num = build_encoder(xtr_raw)
    xtr, feats = encode(xtr_raw, vocab, num)
    xte, _ = encode(xte_raw, vocab, num)

    mn, mx = xtr.min(0), xtr.max(0)
    rng = np.where(mx - mn == 0, 1.0, mx - mn)
    xtr_s = (xtr - mn) / rng
    xte_s = np.clip((xte - mn) / rng, 0.0, 1.0)

    np.savez_compressed(
        artifact("donnees.npz"), Xtr=xtr_s, ytr=ytr, Xte=xte_s, yte=yte
    )
    artifact("parametres_encodage.json").write_text(
        json.dumps(
            {
                "vocabulaires": vocab,
                "colonnes_numeriques": num,
                "features": feats,
                "min": mn.tolist(),
                "max": mx.tolist(),
                "classes": CLASSES,
            },
            indent=1,
        ),
        encoding="utf-8",
    )

    print(f"dim={xtr.shape[1]}  train={xtr_s.shape}  test={xte_s.shape}")
    for i, c in enumerate(CLASSES):
        print(
            f"  {c:<6} train {(ytr == i).sum():6d}  test {(yte == i).sum():6d}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
