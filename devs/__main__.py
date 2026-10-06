"""Scénarios du réseau DEVS. Ne lance pas GAMA.

    python -m devs
"""
from math import inf

from devs.reseau import Monde, executer, uniforme


def ligne(ev):
    t, micro, src, port, msg = ev
    idc = msg.get("idc", "")
    extra = msg.get("nature") or msg.get("classe") or ""
    qui = msg.get("emetteur") or ""
    return f"t={t} m={micro} {src}.{port} idc={idc} {qui} {extra}".rstrip()


def montrer(titre, sim, detail=False):
    modes = {}
    for b in sim.decision.bilan:
        modes[b["mode"]] = modes.get(b["mode"], 0) + 1
    print(titre)
    print(f"  issues={len(sim.decision.bilan)} {modes} rejets={sim.decision.rejets} "
          f"journal={sim.journal.n} alertes={sim.alertes.n} mu={sim.monde.mu:.3f}")
    if detail:
        for ev in sim.trace:
            print(" ", ligne(ev))
    else:
        for b in sim.decision.bilan:
            classe = b.get("classe", "")
            print(f"  t={b['t']} idc={b['idc']} {b['mode']} {classe}".rstrip())


def main():
    montrer("nominal, 1 connexion", executer(Monde(n=1)), detail=True)
    print()
    montrer("panne certaine, 4 connexions",
            executer(Monde(n=4, debit=1, taux_panne=1.0, taux_reprise=0.0)))
    print()
    montrer("IA muette, regles repondent, delai 3",
            executer(Monde(n=1, delai_garde=3), latence_ia=inf))
    print()
    montrer("les deux muets",
            executer(Monde(n=1, delai_garde=3), latence_ia=inf, latence_regles=inf,
                     evaluer_regles=uniforme, evaluer_ia=uniforme))
    print()
    montrer("service de 2 cycles, debit 3, capacite 1",
            executer(Monde(n=3, debit=3, capacite=1, delai_garde=10), latence_ia=2))


if __name__ == "__main__":
    main()
