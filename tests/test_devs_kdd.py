#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from devs.mesurer import CIBLE_EXACT, CIBLE_RAPPEL, campagne


def ok(msg):
    print(f"  OK    {msg}")


def fail(msg):
    print(f"  ECHEC {msg}")
    raise SystemExit(1)


def main():
    res = campagne()
    p0 = res["panne"][0]
    if abs(p0["exactitude_toutes"] - CIBLE_EXACT) > 1e-12:
        fail(f"nominal {p0['exactitude_toutes']} != {CIBLE_EXACT}")
    if abs(p0["rappel_toutes"] - CIBLE_RAPPEL) > 1e-12:
        fail(f"rappel {p0['rappel_toutes']} != {CIBLE_RAPPEL}")
    ok("panne 0 = fusion 0,8102 / 0,7224")

    exacts = [s["exactitude_toutes"] for s in res["panne"]]
    if exacts != sorted(exacts, reverse=True):
        fail(f"l'exactitude ne baisse pas avec la panne : {exacts}")
    ok("l'exactitude baisse quand taux_panne augmente")

    d1 = res["delai_latence_ia_5"][0]
    d5 = res["delai_latence_ia_5"][2]
    if not (d1["exactitude_toutes"] < d5["exactitude_toutes"]):
        fail("le délai 1 n'est pas sous le délai 5")
    if abs(d5["exactitude_toutes"] - CIBLE_EXACT) > 1e-12:
        fail("délai >= latence doit retrouver la fusion")
    ok("latence IA 5 : délai 1 sous la fusion, délai 5 égal à la fusion")

    brut = json.loads((ROOT / "ml" / "artifacts" / "resultats_devs.json").read_text(encoding="utf-8"))
    if brut["panne"][0]["exactitude_toutes"] != p0["exactitude_toutes"]:
        fail("resultats_devs.json ne correspond plus à la campagne")
    ok("resultats_devs.json aligné")
    print("devs kdd ok")


if __name__ == "__main__":
    main()
