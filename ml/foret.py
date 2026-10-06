"""
Forêt aléatoire numpy (CART / Gini) — structure d'arbres maîtrisée pour
la transpilation GAML (ADR-03). Pas de scikit-learn.
"""
from __future__ import annotations

import numpy as np


class Arbre:
    __slots__ = ("feature", "threshold", "left", "right", "value", "n_nodes")


def _binner(x, n_bins):
    edges = []
    for j in range(x.shape[1]):
        q = np.unique(np.quantile(x[:, j], np.linspace(0, 1, n_bins + 1)[1:-1]))
        edges.append(q)
    b = np.empty(x.shape, dtype=np.uint8)
    for j in range(x.shape[1]):
        b[:, j] = np.searchsorted(edges[j], x[:, j], side="left")
    return b, edges


def _bin_test(x, edges):
    b = np.empty(x.shape, dtype=np.uint8)
    for j in range(x.shape[1]):
        b[:, j] = np.searchsorted(edges[j], x[:, j], side="left")
    return b


def _grow(bx, y, w, idx, depth, max_depth, min_leaf, n_feat, k, nb, rs, nodes):
    node_id = len(nodes["feature"])
    nodes["feature"].append(-1)
    nodes["threshold"].append(-1)
    nodes["left"].append(-1)
    nodes["right"].append(-1)
    cnt = np.bincount(y[idx], weights=w[idx], minlength=k)
    nodes["value"].append(cnt)

    if depth >= max_depth or len(idx) < 2 * min_leaf or (cnt > 0).sum() <= 1:
        return node_id

    feats = rs.choice(bx.shape[1], size=n_feat, replace=False)
    best = (np.inf, -1, -1)
    yb, wb = y[idx], w[idx]
    for f in feats:
        b = bx[idx, f]
        h = np.bincount(b * k + yb, weights=wb, minlength=nb * k).reshape(nb, k)
        c = np.bincount(b, minlength=nb).astype(np.float64)
        cum, cumc = h.cumsum(0), c.cumsum()
        tot, totc = cum[-1], cumc[-1]
        left, right = cum[:-1], tot - cum[:-1]
        lc, rc = cumc[:-1], totc - cumc[:-1]
        nl, nr = left.sum(1), right.sum(1)
        ok = (lc >= min_leaf) & (rc >= min_leaf) & (nl > 0) & (nr > 0)
        if not ok.any():
            continue
        gl = 1.0 - ((left / np.where(nl[:, None] == 0, 1, nl[:, None])) ** 2).sum(1)
        gr = 1.0 - ((right / np.where(nr[:, None] == 0, 1, nr[:, None])) ** 2).sum(1)
        sc = np.where(ok, (nl * gl + nr * gr) / (nl + nr), np.inf)
        bi = int(np.argmin(sc))
        if sc[bi] < best[0]:
            best = (sc[bi], int(f), bi)

    if best[1] < 0:
        return node_id
    _, f, bi = best
    mask = bx[idx, f] <= bi
    li, ri = idx[mask], idx[~mask]
    if len(li) < min_leaf or len(ri) < min_leaf:
        return node_id
    nodes["feature"][node_id] = f
    nodes["threshold"][node_id] = bi
    nodes["left"][node_id] = _grow(
        bx, y, w, li, depth + 1, max_depth, min_leaf, n_feat, k, nb, rs, nodes
    )
    nodes["right"][node_id] = _grow(
        bx, y, w, ri, depth + 1, max_depth, min_leaf, n_feat, k, nb, rs, nodes
    )
    return node_id


def entrainer(
    x, y, n_arbres=30, max_depth=12, min_leaf=2, n_bins=32,
    equilibrer=True, graine=42, verbose=True,
):
    rs = np.random.RandomState(graine)
    k = int(y.max()) + 1
    bx, edges = _binner(x, n_bins)
    nb = n_bins + 1
    if equilibrer:
        cnt = np.bincount(y, minlength=k).astype(np.float64)
        cw = len(y) / (k * np.where(cnt == 0, 1, cnt))
    else:
        cw = np.ones(k)
    w = cw[y]
    n_feat = max(1, int(np.sqrt(x.shape[1])))
    arbres = []
    for t in range(n_arbres):
        idx = rs.randint(0, len(y), len(y))
        nodes = {"feature": [], "threshold": [], "left": [], "right": [], "value": []}
        _grow(bx, y, w, idx, 0, max_depth, min_leaf, n_feat, k, nb, rs, nodes)
        a = Arbre()
        a.feature = np.array(nodes["feature"], dtype=np.int32)
        a.threshold = np.array(nodes["threshold"], dtype=np.int32)
        a.left = np.array(nodes["left"], dtype=np.int32)
        a.right = np.array(nodes["right"], dtype=np.int32)
        v = np.array(nodes["value"], dtype=np.float64)
        a.value = v / np.where(v.sum(1, keepdims=True) == 0, 1, v.sum(1, keepdims=True))
        a.n_nodes = len(a.feature)
        arbres.append(a)
        if verbose:
            print(f"  arbre {t + 1:2d}/{n_arbres} : {a.n_nodes:5d} noeuds", flush=True)
    return {"arbres": arbres, "edges": edges, "K": k, "cw": cw, "n_bins": n_bins}


def _pred_arbre(a, bx):
    n = bx.shape[0]
    node = np.zeros(n, dtype=np.int32)
    actif = np.ones(n, dtype=bool)
    while actif.any():
        f = a.feature[node]
        interne = (f >= 0) & actif
        if not interne.any():
            break
        ii = np.where(interne)[0]
        b = bx[ii, a.feature[node[ii]]]
        go_l = b <= a.threshold[node[ii]]
        node[ii] = np.where(go_l, a.left[node[ii]], a.right[node[ii]])
        actif[ii] = a.feature[node[ii]] >= 0
    return a.value[node]


def predire_proba(m, x):
    bx = _bin_test(x, m["edges"])
    p = np.zeros((x.shape[0], m["K"]))
    for a in m["arbres"]:
        p += _pred_arbre(a, bx)
    return p / len(m["arbres"])
