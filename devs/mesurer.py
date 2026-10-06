from __future__ import annotations

import json

import numpy as np

from devs.kdd import charger
from data_paths import artifact
from devs.reseau import CLASSES, Monde, executer

CIBLE_EXACT = 0.8102377572746629
CIBLE_RAPPEL = 0.7223564248422037


def _evaluer(table):
    def fn(i, table=table):
        return table[i].tolist()
    return fn


def bilan_vers_scores(y, bilan):
    n = len(y)
    pred = np.full(n, -1, dtype=np.int64)
    modes = {"nominal": 0, "degrade": 0, "abandon": 0}
    for b in bilan:
        modes[b["mode"]] = modes.get(b["mode"], 0) + 1
        if b["mode"] == "abandon":
            continue
        pred[b["idc"]] = CLASSES.index(b["classe"])
    emis = pred >= 0
    corrects = int(((pred == y) & emis).sum())
    attaque = y > 0
    vp = int((attaque & emis & (pred > 0)).sum())
    fn = int((attaque & ~(emis & (pred > 0))).sum())
    return {
        "exactitude_toutes": corrects / n,
        "rappel_toutes": vp / (vp + fn) if vp + fn else 0.0,
        "exactitude_emises": corrects / int(emis.sum()) if emis.any() else 0.0,
        "emises": int(emis.sum()),
        "abandons": int((~emis).sum()),
        "nominal": modes.get("nominal", 0),
        "degrade": modes.get("degrade", 0),
    }


def _run(y, p_rg, p_ia, **kw):
    sim = executer(
        Monde(n=len(y), debit=1, capacite=kw.pop("capacite", 200), graine=0, **{
            k: kw.pop(k) for k in ("taux_panne", "taux_reprise", "delai_garde") if k in kw
        }),
        evaluer_regles=_evaluer(p_rg),
        evaluer_ia=_evaluer(p_ia),
        latence_ia=kw.pop("latence_ia", 0),
        tracer=False,
    )
    if sim.decision.rejets:
        raise RuntimeError(f"rejets inattendus : {sim.decision.rejets}")
    return bilan_vers_scores(y, sim.decision.bilan)


def campagne(y=None, p_rg=None, p_ia=None):
    if y is None:
        y, p_rg, p_ia = charger()
    fusion = 0.35 * p_ia + 0.65 * p_rg
    pred_f = fusion.argmax(1)
    pred_r = p_rg.argmax(1)
    attaque = y > 0

    def ref(pred):
        vp = int((attaque & (pred > 0)).sum())
        fn = int((attaque & (pred == 0)).sum())
        return {
            "exactitude_toutes": float((pred == y).mean()),
            "rappel_toutes": vp / (vp + fn) if vp + fn else 0.0,
        }

    panne = []
    for p, reprise in ((0.0, 0.2), (0.05, 0.2), (0.1, 0.2), (0.2, 0.2), (0.5, 0.2), (1.0, 0.0)):
        s = _run(y, p_rg, p_ia, taux_panne=p, taux_reprise=reprise, delai_garde=3)
        s["taux_panne"] = p
        s["taux_reprise"] = reprise
        panne.append(s)

    delai = []
    for d in (1, 3, 5, 10):
        s = _run(y, p_rg, p_ia, taux_panne=0.0, taux_reprise=0.2, delai_garde=d,
                 latence_ia=5, capacite=1)
        s["delai_garde"] = d
        s["latence_ia"] = 5
        delai.append(s)

    return {
        "n": int(len(y)),
        "jeu": "KDDTest+",
        "cible_fusion": {"exactitude_toutes": CIBLE_EXACT, "rappel_toutes": CIBLE_RAPPEL},
        "reference_argmax": {"fusion": ref(pred_f), "regles": ref(pred_r)},
        "panne": panne,
        "delai_latence_ia_5": delai,
    }


def _fmt(x):
    return f"{x:.4f}".replace(".", ",")


def afficher(res):
    print(f"KDDTest+  n={res['n']}")
    rf = res["reference_argmax"]["fusion"]
    rr = res["reference_argmax"]["regles"]
    print(f"  argmax fusion  exact={_fmt(rf['exactitude_toutes'])}  rappel={_fmt(rf['rappel_toutes'])}")
    print(f"  argmax regles  exact={_fmt(rr['exactitude_toutes'])}  rappel={_fmt(rr['rappel_toutes'])}")
    print("panne  reprise  exact_toutes  rappel_toutes  exact_emises  abandons  nominal  degrade")
    for s in res["panne"]:
        print(f"  {s['taux_panne']:<5}  {s['taux_reprise']:<6}  {_fmt(s['exactitude_toutes']):>13}  "
              f"{_fmt(s['rappel_toutes']):>13}  {_fmt(s['exactitude_emises']):>12}  "
              f"{s['abandons']:8d}  {s['nominal']:7d}  {s['degrade']:7d}")
    print("delai  latence_ia=5, capacite=1, panne=0")
    for s in res["delai_latence_ia_5"]:
        print(f"  {s['delai_garde']:<5}  exact={_fmt(s['exactitude_toutes'])}  "
              f"rappel={_fmt(s['rappel_toutes'])}  abandons={s['abandons']}  "
              f"nominal={s['nominal']}  degrade={s['degrade']}")


def main():
    res = campagne()
    afficher(res)
    out = artifact("resultats_devs.json")
    out.write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
