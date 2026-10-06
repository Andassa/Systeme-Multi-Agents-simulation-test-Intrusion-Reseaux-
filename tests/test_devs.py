#!/usr/bin/env python3
from __future__ import annotations

import sys
from math import inf
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from devs.reseau import Monde, classe_de, executer, uniforme, utilite


def ok(msg):
    print(f"  OK    {msg}")


def fail(msg):
    print(f"  ECHEC {msg}")
    raise SystemExit(1)


def test_utilite_premiere_classe_en_cas_d_egalite():
    u = utilite([0.5, 0.5, 0, 0, 0], [0.5, 0.5, 0, 0, 0], True, True,
                False, 0.35, 0.0, 0.0)
    if classe_de(u) != "NORMAL":
        fail(f"égalité : {classe_de(u)}")
    ok("argmax garde le premier indice")


def test_nominal():
    sim = executer(Monde(n=1, graine=1))
    b = sim.decision.bilan
    if len(b) != 1 or b[0]["mode"] != "nominal" or b[0]["classe"] != "DOS":
        fail(f"nominal : {b}")
    if b[0]["t"] != 0:
        fail(f"la chaîne à latence 0 tient dans le cycle 0, t={b[0]['t']}")
    if sim.journal.n != 1 or sim.alertes.n != 1:
        fail(f"journal={sim.journal.n} alertes={sim.alertes.n}")
    ok("nominal DOS, journal et alerte dans le cycle 0")


def test_panne():
    sim = executer(Monde(n=3, debit=1, taux_panne=1.0, taux_reprise=0.0, graine=1))
    if any(b["mode"] != "degrade" for b in sim.decision.bilan):
        fail(f"panne : {sim.decision.bilan}")
    if len(sim.decision.bilan) != 3:
        fail(f"attendu 3 dégradés, {sim.decision.bilan}")
    ok("IA en panne : refus immédiat, trois dégradés")


def test_delai_ia_muette():
    sim = executer(Monde(n=1, delai_garde=3), latence_ia=inf)
    b = sim.decision.bilan
    if len(b) != 1 or b[0]["mode"] != "degrade" or b[0]["t"] != 3:
        fail(f"délai : {b}")
    if b[0]["classe"] != "DOS":
        fail(f"dégradé doit garder la classe des règles, {b[0]}")
    ok("IA muette : dégradé à t = delai_garde, classe des règles")


def test_deux_muets_abandon():
    sim = executer(Monde(n=1, delai_garde=3), latence_ia=inf, latence_regles=inf)
    b = sim.decision.bilan
    if len(b) != 1 or b[0]["mode"] != "abandon" or b[0]["t"] != 3:
        fail(f"abandon : {b}")
    if sim.journal.n != 0 or sim.alertes.n != 0:
        fail("l'abandon ne doit rien émettre")
    ok("silence des deux détecteurs : abandon à t=3, pas de P4/P5")


def test_abstention():
    sim = executer(Monde(n=1), evaluer_regles=uniforme, evaluer_ia=uniforme)
    b = sim.decision.bilan
    if len(b) != 1 or b[0]["mode"] != "abandon":
        fail(f"abstention : {b}")
    if sim.journal.n != 0:
        fail("deux abstentions comptent comme un abandon")
    ok("deux distributions uniformes : abandon")


def test_penalite_fp():
    sim = executer(Monde(n=1, lambda_fp=1.0))
    if sim.decision.bilan[0]["classe"] != "NORMAL":
        fail(f"pénalité : {sim.decision.bilan}")
    ok("lambda_fp = 1 fait basculer la fusion vers NORMAL")


def test_file():
    sim = executer(Monde(n=5, debit=5, capacite=1, delai_garde=10), latence_ia=2)
    if sim.decision.rejets != 3:
        fail(f"rejets={sim.decision.rejets}, attendu 3 (1 active + 1 en file)")
    if len(sim.decision.bilan) != 2:
        fail(f"servies : {sim.decision.bilan}")
    if sim.decision.bilan[0]["t"] != 2 or sim.decision.bilan[1]["t"] != 4:
        fail(f"dates : {sim.decision.bilan}")
    ok("capacité 1, latence IA 2 : 3 rejets, services à t=2 et t=4")


def test_conflit_deux_verdicts_a_lecheance():
    sim = executer(Monde(n=1, delai_garde=3), latence_ia=3, latence_regles=3)
    b = sim.decision.bilan
    if len(b) != 1 or b[0]["mode"] != "nominal" or b[0]["t"] != 3:
        fail(f"conflit : {b}")
    ok("réponses pile à l'échéance : nominal, pas dégradé")


def main():
    test_utilite_premiere_classe_en_cas_d_egalite()
    test_nominal()
    test_panne()
    test_delai_ia_muette()
    test_deux_muets_abandon()
    test_abstention()
    test_penalite_fp()
    test_file()
    test_conflit_deux_verdicts_a_lecheance()
    print("devs ok")


if __name__ == "__main__":
    main()
