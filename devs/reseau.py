from __future__ import annotations

import random
from math import inf

from devs.atomique import Atomique, Coordinateur

CLASSES = ("NORMAL", "DOS", "PROBE", "R2L", "U2R")

LIENS = (
    ("capture", "p1", "extraction", "p1"),
    ("extraction", "p2", "decision", "p2"),
    ("decision", "p3", "regles", "p3"),
    ("decision", "p3", "ia", "p3"),
    ("regles", "verdict", "decision", "verdict"),
    ("ia", "verdict", "decision", "verdict"),
    ("ia", "refus", "decision", "refus"),
    ("decision", "p4", "alertes", "p4"),
    ("decision", "p5", "journal", "p5"),
    ("decision", "charge", "capture", "charge"),
)


class Monde:
    def __init__(self, n=1, debit=1, capacite=200, delai_garde=3,
                 poids_ia=0.35, lambda_fp=0.0, seuil_alerte=0.5,
                 taux_panne=0.0, taux_reprise=0.2, alpha=0.99, beta=0.05,
                 graine=0):
        self.n = n
        self.debit = debit
        self.capacite = capacite
        self.delai_garde = delai_garde
        self.poids_ia = poids_ia
        self.lambda_fp = lambda_fp
        self.seuil_alerte = seuil_alerte
        self.taux_panne = taux_panne
        self.taux_reprise = taux_reprise
        self.alpha = alpha
        self.beta = beta
        self.mu = 0.0
        self.rng = random.Random(graine)


def nature(p) -> str:
    if abs(sum(p) - len(p) * min(p)) < 1e-9:
        return "ABSTENTION"
    return "DETECTION"


def utilite(c_ia, c_rg, a_ia, a_rg, degrade, poids, lambda_fp, mu):
    u = []
    for k in range(len(CLASSES)):
        if degrade:
            score = c_ia[k] if a_ia else c_rg[k]
        else:
            score = poids * c_ia[k] + (1.0 - poids) * c_rg[k]
        penalite = 0.0 if k == 0 else lambda_fp * (1.0 - mu)
        u.append(score - penalite)
    return u


def classe_de(u) -> str:
    return CLASSES[max(range(len(u)), key=lambda i: u[i])]


class Capture(Atomique):
    def __init__(self, monde: Monde):
        super().__init__("capture")
        self.monde = monde
        self.reste = monde.n
        self.suiv = 0
        self.charge = 0
        self.lot = []
        self.restant = 0

    def delta_ext(self, e, x):
        if x.get("charge"):
            self.charge = x["charge"][-1]

    def delta_con(self, x):
        self.delta_ext(0, x)
        self.delta_int()

    def sortie(self):
        return {"p1": list(self.lot)} if self.lot else {}

    def delta_int(self):
        if self.lot:
            self.lot = []
            self.restant = 1
            return
        self.lot = []
        while (len(self.lot) < self.monde.debit and self.reste > 0
               and self.charge < self.monde.capacite):
            self.lot.append({"idc": self.suiv})
            self.suiv += 1
            self.reste -= 1
        if self.lot:
            self.restant = 0
        elif self.reste > 0:
            self.restant = 1
        else:
            self.restant = inf


class Extraction(Atomique):
    def __init__(self):
        super().__init__("extraction")
        self.emis = []
        self.restant = inf

    def delta_ext(self, e, x):
        p1 = x.get("p1") or []
        if not p1:
            return
        self.emis = [{"idc": m["idc"]} for m in p1]
        self.restant = 0

    def delta_con(self, x):
        self.delta_ext(0, x)

    def sortie(self):
        return {"p2": list(self.emis)} if self.emis else {}

    def delta_int(self):
        self.emis = []
        self.restant = inf


class Detecteur(Atomique):
    def __init__(self, nom, monde: Monde, evaluer, panne=False, latence=0):
        super().__init__(nom)
        self.monde = monde
        self.evaluer = evaluer
        self.panne = panne
        self.latence = latence
        self.phase = "ACTIF"
        self.boite = []
        self.delai = None
        self.reveil = 0 if panne else inf
        self.emis_v = []
        self.emis_r = []
        self.restant = 0 if panne else inf

    def _armer(self):
        if self.emis_v or self.emis_r:
            self.restant = 0
            return
        opts = []
        if self.panne:
            opts.append(self.reveil)
        if self.delai is not None:
            opts.append(self.delai)
        self.restant = min(opts) if opts else inf

    def ecouler(self, dt):
        if self.panne:
            self.reveil -= dt
        if self.delai is not None:
            self.delai -= dt
            if self.delai <= 0 and self.boite:
                self._repondre()
        self._armer()

    def _repondre(self):
        for q in self.boite:
            if self.phase == "EN_PANNE":
                self.emis_r.append({"idc": q["idc"]})
            else:
                p = list(self.evaluer(q["idc"]))
                self.emis_v.append({
                    "idc": q["idc"],
                    "emetteur": self.nom,
                    "nature": nature(p),
                    "p": p,
                })
        self.boite = []
        self.delai = None

    def _tirer(self):
        if self.phase == "ACTIF":
            if self.monde.rng.random() < self.monde.taux_panne:
                self.phase = "EN_PANNE"
        elif self.monde.rng.random() < self.monde.taux_reprise:
            self.phase = "ACTIF"
        self.reveil = 1

    def delta_ext(self, e, x):
        qs = x.get("p3") or []
        if not qs or self.latence == inf:
            return
        self.boite.extend(qs)
        if self.latence == 0:
            self._repondre()
        elif self.delai is None:
            self.delai = self.latence
        self._armer()

    def delta_int(self):
        self.emis_v = []
        self.emis_r = []
        if self.panne and self.reveil <= 0:
            self._tirer()
        self._armer()

    def delta_con(self, x):
        self.delta_ext(0, x)
        if self.panne and self.reveil <= 0:
            self._tirer()
        self._armer()

    def sortie(self):
        y = {}
        if self.emis_v:
            y["verdict"] = list(self.emis_v)
        if self.emis_r:
            y["refus"] = list(self.emis_r)
        return y


class Decision(Atomique):
    def __init__(self, monde: Monde):
        super().__init__("decision")
        self.monde = monde
        self.phase = "INACTIF"
        self.file = []
        self.courante = None
        self.verdicts = []
        self.refus = 0
        self.emis = []
        self.mode = None
        self.bilan = []
        self.rejets = 0
        self.restant = inf

    def _charge(self) -> int:
        actif = 0 if self.phase == "INACTIF" else 1
        return len(self.file) + actif

    def _offrir(self, msg):
        if self.phase == "INACTIF" and self.courante is None and not self.file:
            self._demarrer(msg["idc"])
        elif len(self.file) < self.monde.capacite:
            self.file.append(msg["idc"])
        else:
            self.rejets += 1

    def _demarrer(self, idc):
        self.courante = idc
        self.verdicts = []
        self.refus = 0
        self.mode = None
        self.phase = "ARMER"
        self.emis = [("p3", {"idc": idc}), ("charge", self._charge())]
        self.restant = 0

    def _prendre(self) -> bool:
        if not self.file:
            return False
        self._demarrer(self.file.pop(0))
        return True

    def _distrib(self):
        c_ia = [0.0] * 5
        c_rg = [0.0] * 5
        a_ia = a_rg = False
        for v in self.verdicts:
            if v["emetteur"] == "ia":
                c_ia, a_ia = v["p"], True
            else:
                c_rg, a_rg = v["p"], True
        return c_ia, c_rg, a_ia, a_rg

    def _trancher(self, degrade: bool):
        if degrade:
            abst = self.verdicts[0]["nature"] == "ABSTENTION"
        else:
            abst = all(v["nature"] == "ABSTENTION" for v in self.verdicts)
        if abst or not self.verdicts:
            self._abandonner()
            return
        c_ia, c_rg, a_ia, a_rg = self._distrib()
        u = utilite(c_ia, c_rg, a_ia, a_rg, degrade, self.monde.poids_ia,
                    self.monde.lambda_fp, self.monde.mu)
        classe = classe_de(u)
        conf = max(u)
        self.classe = classe
        self.confiance = conf
        self.monde.mu = min(1.0, self.monde.alpha * self.monde.mu
                            + self.monde.beta * (0.0 if classe == "NORMAL" else 1.0))
        msg = {"idc": self.courante, "classe": classe, "confiance": conf}
        self.mode = "degrade" if degrade else "nominal"
        self.phase = "TRANCHER"
        self.emis = [("p4", dict(msg)), ("p5", dict(msg)), ("charge", self._charge())]
        self.restant = 0

    def _abandonner(self):
        self.bilan.append({"idc": self.courante, "mode": "abandon", "t": self.t})
        self.courante = None
        self.verdicts = []
        self.refus = 0
        self.phase = "INACTIF"
        if not self._prendre():
            self.phase = "PUBLIE"
            self.emis = [("charge", 0)]
            self.restant = 0

    def _peut_trancher(self):
        if len(self.verdicts) >= 2:
            self._trancher(False)
        elif len(self.verdicts) == 1 and self.refus > 0:
            self._trancher(True)

    def _echeance(self):
        if len(self.verdicts) >= 2:
            self._trancher(False)
        elif len(self.verdicts) == 1:
            self._trancher(True)
        else:
            self._abandonner()

    def _clore(self):
        self.bilan.append({
            "idc": self.courante,
            "mode": self.mode,
            "classe": self.classe,
            "t": self.t,
        })
        self.courante = None
        self.verdicts = []
        self.refus = 0
        self.phase = "INACTIF"
        if not self._prendre():
            self.phase = "PUBLIE"
            self.emis = [("charge", 0)]
            self.restant = 0

    def _ingerer(self, x):
        for m in x.get("p2") or []:
            self._offrir(m)
        self.verdicts.extend(x.get("verdict") or [])
        self.refus += len(x.get("refus") or [])

    def delta_ext(self, e, x):
        self._ingerer(x)
        if self.phase == "ATTENTE":
            self._peut_trancher()

    def delta_int(self):
        self.emis = []
        if self.phase == "ARMER":
            self.phase = "ATTENTE"
            self.restant = self.monde.delai_garde
        elif self.phase == "ATTENTE":
            self._echeance()
        elif self.phase == "TRANCHER":
            self._clore()
        elif self.phase == "PUBLIE":
            self.phase = "INACTIF"
            self.restant = inf
        else:
            self.restant = inf

    def delta_con(self, x):
        self._ingerer(x)
        if self.phase == "ATTENTE":
            self._echeance()
        else:
            self.delta_int()

    def sortie(self):
        ports = {}
        for port, msg in self.emis:
            ports.setdefault(port, []).append(msg)
        return ports


class Puits(Atomique):
    def __init__(self, nom, port, monde: Monde):
        super().__init__(nom)
        self.port = port
        self.monde = monde
        self.n = 0
        self.restant = inf

    def ecouler(self, dt):
        pass

    def delta_ext(self, e, x):
        for m in x.get(self.port) or []:
            if self.port == "p4":
                grav = m["confiance"] * (1.0 + self.monde.mu) / 2.0
                if m["classe"] != "NORMAL" and grav >= self.monde.seuil_alerte:
                    self.n += 1
            else:
                self.n += 1


def dos(_idc):
    return [0.0025, 0.99, 0.0025, 0.0025, 0.0025]


def dos_faible(_idc):
    return [0.01, 0.96, 0.01, 0.01, 0.01]


def uniforme(_idc):
    return [0.2, 0.2, 0.2, 0.2, 0.2]


class Simulation:
    def __init__(self, monde, decision, alertes, journal, coordinateur):
        self.monde = monde
        self.decision = decision
        self.alertes = alertes
        self.journal = journal
        self.coordinateur = coordinateur
        self.trace = coordinateur.trace
        self.t = coordinateur.t


def executer(monde: Monde | None = None, evaluer_regles=dos, evaluer_ia=dos_faible,
             latence_regles=0, latence_ia=0, horizon=None, tracer: bool = True) -> Simulation:
    monde = monde or Monde()
    if horizon is None:
        lats = [v for v in (latence_regles, latence_ia) if v != inf]
        lat = max(lats) if lats else 0
        horizon = monde.n * (lat + 2) + monde.delai_garde + 8
    capture = Capture(monde)
    extraction = Extraction()
    regles = Detecteur("regles", monde, evaluer_regles, latence=latence_regles)
    ia = Detecteur("ia", monde, evaluer_ia, panne=True, latence=latence_ia)
    decision = Decision(monde)
    alertes = Puits("alertes", "p4", monde)
    journal = Puits("journal", "p5", monde)
    comps = {
        "capture": capture,
        "extraction": extraction,
        "regles": regles,
        "ia": ia,
        "decision": decision,
        "alertes": alertes,
        "journal": journal,
    }
    co = Coordinateur(comps, LIENS, tracer=tracer)
    co.jusqua(horizon)
    return Simulation(monde, decision, alertes, journal, co)
