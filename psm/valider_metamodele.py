#!/usr/bin/env python3
"""
Validation structurelle de gaml-psm.ecore sans dépendance externe.

Pourquoi ce script existe : PyEcore n'est pas installable dans l'environnement
d'exécution utilisé pour la conception (pas d'accès PyPI). Plutôt que de
déclarer le métamodèle « valide » sans preuve, on vérifie ici les propriétés
qu'EMF vérifierait au chargement :

  V1  XML bien formé
  V2  unicité des noms de classifieurs
  V3  toute référence eType interne (#//X) désigne un classifieur existant
  V4  toute référence eType externe pointe le métamodèle Ecore standard
  V5  tout eSuperTypes désigne un classifieur existant et non lui-même
  V6  pas de cycle d'héritage
  V7  unicité des noms de features au sein d'une classe (héritage compris)
  V8  toute EReference containment=true pointe une EClass, jamais un EEnum
  V9  toute classe concrète est atteignable depuis GamlModel par containment
  V10 les littéraux d'un EEnum ont des valeurs distinctes

Usage : python3 valider_metamodele.py [chemin.ecore]
Sortie : code 0 si tout passe, 1 sinon.
"""
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict

XSI = "{http://www.w3.org/2001/XMLSchema-instance}type"
ECORE_NS = "http://www.eclipse.org/emf/2002/Ecore"

echecs = []
succes = []


def verifie(ok, code, message):
    (succes if ok else echecs).append(f"{code} : {message}")


def main(chemin):
    # V1 -----------------------------------------------------------------
    try:
        arbre = ET.parse(chemin)
    except ET.ParseError as e:
        print(f"V1 ECHEC : XML mal formé — {e}")
        return 1
    racine = arbre.getroot()
    verifie(True, "V1", "XML bien formé")

    classifieurs = racine.findall("eClassifiers")
    noms = [c.get("name") for c in classifieurs]
    par_nom = {c.get("name"): c for c in classifieurs}

    # V2 -----------------------------------------------------------------
    doublons = {n for n in noms if noms.count(n) > 1}
    verifie(not doublons, "V2",
            "noms de classifieurs uniques" if not doublons
            else f"doublons : {sorted(doublons)}")

    # V3 / V4 ------------------------------------------------------------
    ref_internes_ko, ref_externes_ko = [], []
    for c in classifieurs:
        for f in c.findall("eStructuralFeatures"):
            t = f.get("eType", "")
            if t.startswith("#//"):
                cible = t[3:]
                if cible not in par_nom:
                    ref_internes_ko.append(f"{c.get('name')}.{f.get('name')} -> {cible}")
            elif t:
                if ECORE_NS not in t:
                    ref_externes_ko.append(f"{c.get('name')}.{f.get('name')} -> {t}")
    verifie(not ref_internes_ko, "V3",
            "toutes les références eType internes résolvent" if not ref_internes_ko
            else f"non résolues : {ref_internes_ko}")
    verifie(not ref_externes_ko, "V4",
            "toutes les références eType externes visent Ecore" if not ref_externes_ko
            else f"hors Ecore : {ref_externes_ko}")

    # V5 / V6 ------------------------------------------------------------
    parents = {}
    supertypes_ko = []
    for c in classifieurs:
        st = c.get("eSuperTypes", "").split()
        ps = []
        for s in st:
            cible = s[3:] if s.startswith("#//") else s
            if cible not in par_nom:
                supertypes_ko.append(f"{c.get('name')} -> {cible}")
            elif cible == c.get("name"):
                supertypes_ko.append(f"{c.get('name')} hérite de lui-même")
            else:
                ps.append(cible)
        parents[c.get("name")] = ps
    verifie(not supertypes_ko, "V5",
            "tous les eSuperTypes résolvent" if not supertypes_ko
            else str(supertypes_ko))

    cycles = []
    for depart in parents:
        vus, pile = set(), [depart]
        while pile:
            n = pile.pop()
            if n in vus:
                cycles.append(depart)
                break
            vus.add(n)
            pile.extend(parents.get(n, []))
    verifie(not cycles, "V6",
            "aucun cycle d'héritage" if not cycles else f"cycles depuis {cycles}")

    # V7 -----------------------------------------------------------------
    def features(nom, vus=None):
        vus = vus or set()
        if nom in vus:
            return []
        vus.add(nom)
        propres = [f.get("name") for f in par_nom[nom].findall("eStructuralFeatures")]
        for p in parents.get(nom, []):
            propres += features(p, vus)
        return propres

    collisions = []
    for c in classifieurs:
        if c.get(XSI) != "ecore:EClass":
            continue
        fs = features(c.get("name"))
        d = {f for f in fs if fs.count(f) > 1}
        if d:
            collisions.append(f"{c.get('name')} : {sorted(d)}")
    verifie(not collisions, "V7",
            "aucune collision de nom de feature" if not collisions else str(collisions))

    # V8 -----------------------------------------------------------------
    containment_ko = []
    for c in classifieurs:
        for f in c.findall("eStructuralFeatures"):
            if f.get("containment") == "true":
                cible = f.get("eType", "")[3:]
                if par_nom.get(cible) is None or \
                   par_nom[cible].get(XSI) != "ecore:EClass":
                    containment_ko.append(f"{c.get('name')}.{f.get('name')}")
    verifie(not containment_ko, "V8",
            "toute référence containment vise une EClass" if not containment_ko
            else str(containment_ko))

    # V9 -----------------------------------------------------------------
    enfants = defaultdict(set)
    for c in classifieurs:
        for f in c.findall("eStructuralFeatures"):
            if f.get("containment") == "true":
                enfants[c.get("name")].add(f.get("eType", "")[3:])
    # une classe abstraite atteinte rend ses sous-classes atteintes
    sous = defaultdict(set)
    for n, ps in parents.items():
        for p in ps:
            sous[p].add(n)

    atteints, pile = set(), ["GamlModel"]
    while pile:
        n = pile.pop()
        if n in atteints:
            continue
        atteints.add(n)
        pile.extend(enfants.get(n, ()))
        pile.extend(sous.get(n, ()))

    concretes = {c.get("name") for c in classifieurs
                 if c.get(XSI) == "ecore:EClass" and c.get("abstract") != "true"}
    orphelines = concretes - atteints
    verifie(not orphelines, "V9",
            "toute classe concrète est atteignable depuis GamlModel"
            if not orphelines else f"orphelines : {sorted(orphelines)}")

    # V10 ----------------------------------------------------------------
    enums_ko = []
    for c in classifieurs:
        if c.get(XSI) != "ecore:EEnum":
            continue
        vals = [l.get("value") for l in c.findall("eLiterals")]
        if len(vals) != len(set(vals)):
            enums_ko.append(c.get("name"))
    verifie(not enums_ko, "V10",
            "valeurs de littéraux distinctes dans chaque EEnum"
            if not enums_ko else str(enums_ko))

    # Rapport ------------------------------------------------------------
    nb_cls = sum(1 for c in classifieurs if c.get(XSI) == "ecore:EClass")
    nb_abs = sum(1 for c in classifieurs
                 if c.get(XSI) == "ecore:EClass" and c.get("abstract") == "true")
    nb_enum = sum(1 for c in classifieurs if c.get(XSI) == "ecore:EEnum")
    nb_feat = sum(len(c.findall("eStructuralFeatures")) for c in classifieurs)

    print(f"Métamodèle : {chemin}")
    print(f"  nsURI            : {racine.get('nsURI')}")
    print(f"  EClass           : {nb_cls} (dont {nb_abs} abstraites)")
    print(f"  EEnum            : {nb_enum}")
    print(f"  features totales : {nb_feat}")
    print()
    for s in succes:
        print(f"  OK    {s}")
    for e in echecs:
        print(f"  ECHEC {e}")
    print()
    if echecs:
        print(f"{len(echecs)} contrainte(s) violée(s).")
        return 1
    print(f"{len(succes)}/{len(succes)} contraintes satisfaites.")
    return 0


if __name__ == "__main__":
    chemin = sys.argv[1] if len(sys.argv) > 1 else "gaml-psm.ecore"
    sys.exit(main(chemin))
