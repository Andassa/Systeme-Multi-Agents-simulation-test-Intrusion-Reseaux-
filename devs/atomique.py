"""DEVS parallèle, temps entier.

Un pas de temps est un cycle. Les sorties d'un micro-pas sont livrées
dans le même instant aux autres atomes ; `restant == 0` enchaîne un
micro-pas sans faire avancer l'horloge. C'est le délai de transport nul
des couplages DEVS : la durée est dans `ta`, pas dans le lien.
"""
from __future__ import annotations

from math import inf


class Atomique:
    def __init__(self, nom: str):
        self.nom = nom
        self.restant = inf
        self.t = 0

    def ecouler(self, dt: int) -> None:
        if self.restant != inf:
            self.restant -= dt

    def sortie(self) -> dict:
        return {}

    def delta_int(self) -> None:
        self.restant = inf

    def delta_ext(self, e: int, x: dict) -> None:
        pass

    def delta_con(self, x: dict) -> None:
        self.delta_int()
        self.delta_ext(0, x)


class Coordinateur:
    def __init__(self, composants: dict, liens: list, limite_micro: int = 64):
        self.composants = composants
        self.liens = liens
        self.limite_micro = limite_micro
        self.t = 0
        self.trace = []

    def jusqua(self, horizon: int) -> int:
        self._micros()
        while self.t < horizon:
            attente = [a.restant for a in self.composants.values() if a.restant != inf]
            if not attente:
                break
            dt = min(attente)
            if dt < 0:
                raise RuntimeError(f"restant négatif à t={self.t}")
            if self.t + dt > horizon:
                break
            self.t += dt
            for a in self.composants.values():
                a.t = self.t
                a.ecouler(dt)
            self._micros()
        return self.t

    def _micros(self) -> None:
        for micro in range(self.limite_micro):
            imminents = [n for n, a in self.composants.items() if a.restant == 0]
            if not imminents:
                return
            boites = {n: {} for n in self.composants}
            for n in imminents:
                for port, msgs in (self.composants[n].sortie() or {}).items():
                    if not msgs:
                        continue
                    if port != "charge":
                        for m in msgs:
                            self.trace.append((self.t, micro, n, port, m))
                    for src, p_out, dst, p_in in self.liens:
                        if src == n and p_out == port:
                            boites[dst].setdefault(p_in, []).extend(msgs)
            for n, a in self.composants.items():
                x = boites[n]
                imminent = a.restant == 0
                if not imminent and not x:
                    continue
                a.t = self.t
                if imminent and x:
                    a.delta_con(x)
                elif imminent:
                    a.delta_int()
                else:
                    a.delta_ext(0, x)
        raise RuntimeError(f"plus de {self.limite_micro} micro-pas à t={self.t}")
