#!/usr/bin/env python3
"""
Vérification d'une instance PSM : conformité au métamodèle + contraintes C1..C10.

Deux niveaux de contrôle, à ne pas confondre :

  CONFORMITÉ  — l'instance n'emploie que des classes, attributs et références
                déclarés dans gaml-psm.ecore, et les valeurs d'énumération
                existent. C'est ce qu'EMF vérifie au chargement.

  CONTRAINTES — C1 à C10 (cf. 05-PSM.md §3). Elles décrivent des modèles
                parfaitement conformes mais sémantiquement faux. C1, C7 et C8
                sont les plus importantes : leur violation ne produirait aucune
                erreur, ni à la génération, ni à la compilation, ni à
                l'exécution. Seulement de mauvais résultats.

Usage : python3 verifier_contraintes.py [instance.xmi] [metamodele.ecore]
"""
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict

XSI_TYPE = "{http://www.w3.org/2001/XMLSchema-instance}type"
NS_PSM = "http://ids-sma-idm.org/psm/gaml/1.0"

MAILBOX_PERFORMATIVE = {
    "INFORMS": "INFORM", "QUERIES": "QUERY", "REQUESTS": "REQUEST",
    "REFUSES": "REFUSE", "FAILURES": "FAILURE", "AGREES": "AGREE",
    "PROPOSES": "PROPOSE",
}


# --------------------------------------------------------------------------
# Chargement du métamodèle
# --------------------------------------------------------------------------
def charger_metamodele(chemin):
    racine = ET.parse(chemin).getroot()
    classes, enums, abstraites, parents = {}, {}, set(), {}
    for c in racine.findall("eClassifiers"):
        nom, kind = c.get("name"), c.get(XSI_TYPE)
        if kind == "ecore:EEnum":
            enums[nom] = {l.get("name") for l in c.findall("eLiterals")}
        elif kind == "ecore:EClass":
            classes[nom] = {f.get("name"): f for f in c.findall("eStructuralFeatures")}
            if c.get("abstract") == "true":
                abstraites.add(nom)
            parents[nom] = [s[3:] for s in c.get("eSuperTypes", "").split()]
    # aplatissement de l'héritage
    def toutes(n, vus=None):
        vus = vus or set()
        if n in vus or n not in classes:
            return {}
        vus.add(n)
        r = dict(classes[n])
        for p in parents.get(n, []):
            r.update(toutes(p, vus))
        return r
    return {n: toutes(n) for n in classes}, enums, abstraites, parents


# --------------------------------------------------------------------------
# Parcours de l'instance
# --------------------------------------------------------------------------
def type_element(el, feats_parent, nom_parent, classes):
    """Détermine la classe métamodèle d'un élément d'instance."""
    t = el.get(XSI_TYPE)
    if t:
        return t.split(":")[-1]
    tag = el.tag.split("}")[-1]
    f = feats_parent.get(tag)
    if f is None:
        return None
    return f.get("eType", "").replace("#//", "")


def main(chemin_xmi, chemin_ecore):
    classes, enums, abstraites, _ = charger_metamodele(chemin_ecore)
    racine = ET.parse(chemin_xmi).getroot()

    erreurs, avertissements = [], []
    inventaire = defaultdict(int)
    # chemin XMI -> élément, pour résoudre les références non-containment
    index_chemins = {}
    refs_a_resoudre = []   # (chemin, feature, valeur, classe attendue)
    # (species, mailbox) -> [noms de reflex]      pour C1
    boites = defaultdict(list)
    # species -> [ordres]                          pour C5
    ordres = defaultdict(list)
    zones = []                                     # pour C8, C9
    brutes = []                                    # pour C10

    def visiter(el, nom_classe, chemin, xmi="/", espece_courante=None):
        if nom_classe is None:
            erreurs.append(f"CONFORMITE {chemin} : feature inconnue '{el.tag.split('}')[-1]}'")
            return
        if nom_classe not in classes:
            erreurs.append(f"CONFORMITE {chemin} : classe inconnue '{nom_classe}'")
            return
        if nom_classe in abstraites:
            erreurs.append(f"CONFORMITE {chemin} : classe abstraite '{nom_classe}' instanciée")
            return
        inventaire[nom_classe] += 1
        feats = classes[nom_classe]
        index_chemins[xmi] = nom_classe
        # Résolution des références '#X' selon la sémantique EMF : la cible
        # doit porter un xmi:id valant X. Une version antérieure résolvait par
        # l'attribut `nom`, ce qui validait un modèle que PyEcore refusait
        # ensuite avec « KeyError: 'AgentCapture' ». Un vérificateur plus
        # permissif que la plateforme cible ne vérifie rien : il déplace
        # simplement la découverte du défaut jusqu'à l'exécution.
        ident = el.get("{http://www.omg.org/XMI}id")
        if ident:
            index_chemins["#" + ident] = nom_classe

        # attributs présents
        for k, v in el.attrib.items():
            if k.startswith("{"):
                continue
            f = feats.get(k)
            if f is None:
                erreurs.append(f"CONFORMITE {chemin} : '{nom_classe}.{k}' non déclaré")
                continue
            t = f.get("eType", "").replace("#//", "")
            if t in enums:
                for jeton in v.split():
                    if jeton not in enums[t]:
                        erreurs.append(
                            f"CONFORMITE {chemin} : '{jeton}' hors de l'énumération {t}")
            elif t in classes and f.get("containment") != "true":
                # référence non-containment sérialisée en chemin XMI
                for jeton in v.split():
                    refs_a_resoudre.append((chemin, f"{nom_classe}.{k}", jeton, t))

        # V11 : features obligatoires (lowerBound = 1)
        presents = set(el.attrib) | {e.tag.split("}")[-1] for e in el}
        for nomf, f in feats.items():
            if f.get("lowerBound") != "1":
                continue
            if f.get("upperBound") == "-1":
                continue
            if nomf not in presents:
                erreurs.append(
                    f"V11 {chemin} : '{nom_classe}.{nomf}' est obligatoire "
                    "(lowerBound=1) et absent")

        # collecte pour les contraintes
        if nom_classe == "Species":
            espece_courante = el.get("nom")
        elif nom_classe == "Reflex":
            b = el.get("boiteLue", "AUCUNE")
            if b != "AUCUNE":
                boites[(espece_courante, b)].append(el.get("nom"))
            o = el.get("ordre")
            if o is None:
                erreurs.append(f"C5 {chemin} : Reflex '{el.get('nom')}' sans ordre")
            else:
                ordres[espece_courante].append(int(o))
        elif nom_classe == "ZoneProtegee":
            zones.append((el.get("identifiant"), el.get("intention"), chemin))
        elif nom_classe == "ExpressionBrute":
            brutes.append((el.get("texte"), el.get("justification"), chemin))
        elif nom_classe == "CommunicationFipa":
            genre, src = el.get("genre"), el.get("messageSource")
            if genre == "REPLY" and not src:
                erreurs.append(f"C6 {chemin} : REPLY sans messageSource")
            if genre == "START_CONVERSATION" and src:
                erreurs.append(f"C6 {chemin} : START_CONVERSATION avec messageSource")

        rangs = defaultdict(int)
        for enfant in el:
            tag = enfant.tag.split("}")[-1]
            r = rangs[tag]
            rangs[tag] += 1
            visiter(enfant, type_element(enfant, feats, nom_classe, classes),
                    f"{chemin}/{tag}",
                    ("/" if xmi == "/" else xmi) + f"@{tag}.{r}"
                    if xmi == "/" else f"{xmi}/@{tag}.{r}",
                    espece_courante)

    visiter(racine, "GamlModel", "GamlModel")

    # ---- V12 : résolution des références non-containment -------------------
    for chemin, feature, cible, attendu in refs_a_resoudre:
        reel = index_chemins.get(cible)
        if reel is None:
            erreurs.append(
                f"V12 {chemin} : '{feature}' pointe '{cible}', qui ne désigne "
                "aucun élément du modèle")
        elif reel != attendu and attendu not in ("Species",):
            erreurs.append(
                f"V12 {chemin} : '{feature}' attend un {attendu}, trouve un {reel}")

    # ---- Contraintes structurelles ----------------------------------------
    # C1
    for (sp, b), noms in boites.items():
        if len(noms) > 1:
            erreurs.append(
                f"C1 : espèce '{sp}' a {len(noms)} reflex sur la boîte {b} ({noms}). "
                "Le premier exécuté viderait la liste — panne silencieuse.")
    # C5
    for sp, os in ordres.items():
        if len(os) != len(set(os)):
            erreurs.append(f"C5 : ordres de reflex non distincts dans '{sp}' : {sorted(os)}")
    # C8 / C9
    ids = [z[0] for z in zones]
    for d in {i for i in ids if ids.count(i) > 1}:
        erreurs.append(f"C8 : identifiant de ZoneProtegee dupliqué : '{d}'")
    for i, intention, ch in zones:
        if not intention:
            erreurs.append(f"C9 {ch} : ZoneProtegee '{i}' sans intention")
    # C10
    for texte, just, ch in brutes:
        if not just:
            erreurs.append(f"C10 {ch} : ExpressionBrute sans justification")

    # C2 / C3 / C4 : cohérence architecture / corps
    for sp in racine.findall("especes"):
        arch = sp.get("architecture", "REFLEX")
        etats = sp.findall("etats")
        taches = sp.findall("taches")
        nom = sp.get("nom")
        if (arch == "FSM") != bool(etats):
            erreurs.append(f"C2 : '{nom}' architecture={arch} mais {len(etats)} état(s)")
        if (arch == "WEIGHTED_TASKS") != bool(taches):
            erreurs.append(f"C3 : '{nom}' architecture={arch} mais {len(taches)} tâche(s)")
        if arch == "FSM":
            init = [e for e in etats if e.get("estInitial") == "true"]
            if len(init) != 1:
                erreurs.append(f"C4 : '{nom}' a {len(init)} état initial (attendu : 1)")
        if arch == "WEIGHTED_TASKS":
            poids_const = [t for t in taches
                           if t.get("expressionPoids", "").replace(".", "").isdigit()]
            if not poids_const:
                avertissements.append(
                    f"'{nom}' est en weighted_tasks sans tâche sentinelle à poids constant. "
                    "Quand tous les poids valent 0, GAMA exécute une tâche arbitraire.")

    # ---- Rapport -----------------------------------------------------------
    print(f"Instance     : {chemin_xmi}")
    print(f"Métamodèle   : {chemin_ecore}")
    print()
    print("Inventaire des éléments instanciés :")
    for n, c in sorted(inventaire.items(), key=lambda x: (-x[1], x[0])):
        print(f"    {c:3d}  {n}")
    print()
    print(f"ExpressionBrute : {len(brutes)}  (objectif : < 5)")
    print(f"ZoneProtegee    : {len(zones)}")
    print()

    for a in avertissements:
        print(f"  AVERT {a}")
    for e in erreurs:
        print(f"  ECHEC {e}")
    if not erreurs:
        print("  OK    conformité au métamodèle")
        print("  OK    contraintes C1 à C10")
    print()
    print(f"{len(erreurs)} erreur(s), {len(avertissements)} avertissement(s).")
    return 1 if erreurs else 0


if __name__ == "__main__":
    xmi = sys.argv[1] if len(sys.argv) > 1 else "exemple-psm-minimal.xmi"
    ecore = sys.argv[2] if len(sys.argv) > 2 else "gaml-psm.ecore"
    sys.exit(main(xmi, ecore))
