#!/usr/bin/env python3
"""
Zones protégées — ADR-05.

Problème résolu
---------------
L'énoncé impose deux choses contradictoires en apparence : le GAML ne doit
pas être écrit à la main, et le code métier doit être complété. La frontière
retenue est la zone protégée : le générateur écrit la structure, le
développeur écrit le corps métier, et une régénération ne détruit rien.

Mécanique
---------
    // @user-begin(identifiant)
    // À COMPLÉTER — intention
    <contenu écrit par le développeur>
    // @user-end(identifiant)

Avant d'écrire, le générateur relit le fichier cible, extrait le contenu de
chaque zone et le réinjecte dans la sortie.

Deux garde-fous, parce que ce mécanisme perd du travail quand il échoue
-----------------------------------------------------------------------
1. Une zone présente dans le fichier existant mais ABSENTE du modèle
   signalerait que du code métier va disparaître. Le générateur refuse alors
   d'écrire, sauf --forcer. C'est le seul cas où le générateur s'arrête.

2. Le fichier précédent est sauvegardé en .bak avant écriture. Un mécanisme
   qui ne peut pas se tromper n'existe pas ; un mécanisme dont l'erreur est
   irréversible est un défaut de conception.
"""
import os
import re
import shutil
import textwrap

DEBUT = re.compile(r"^\s*//\s*@user-begin\(([^)]+)\)\s*$")
FIN = re.compile(r"^\s*//\s*@user-end\(([^)]+)\)\s*$")
LIGNE_INTENTION = re.compile(r"^\s*//\s*À COMPLÉTER —")


def extraire(chemin):
    """
    Lit les zones d'un fichier généré précédemment.
    Retourne {identifiant: contenu}. Fichier absent -> {}.
    """
    if not os.path.exists(chemin):
        return {}
    zones, courant, tampon = {}, None, []
    with open(chemin, encoding="utf-8") as f:
        for num, ligne in enumerate(f, 1):
            d = DEBUT.match(ligne)
            if d:
                if courant is not None:
                    raise ValueError(
                        f"{chemin}:{num} — zone '{d.group(1)}' ouverte alors que "
                        f"'{courant}' n'est pas fermée. Marqueurs imbriqués.")
                courant, tampon = d.group(1), []
                continue
            f_ = FIN.match(ligne)
            if f_:
                if courant is None:
                    raise ValueError(f"{chemin}:{num} — @user-end sans @user-begin.")
                if f_.group(1) != courant:
                    raise ValueError(
                        f"{chemin}:{num} — @user-end({f_.group(1)}) ferme "
                        f"@user-begin({courant}).")
                # Le contenu est DÉSINDENTÉ à la lecture et ré-indenté à
                # l'écriture. Sans cela, le gabarit préfixe l'indentation
                # devant un contenu qui la porte déjà : chaque régénération
                # décale le bloc d'un niveau supplémentaire. Défaut invisible
                # à la première génération, détecté par le test d'idempotence
                # Z4 de verifier_cycle.py.
                corps = [l for l in tampon if not LIGNE_INTENTION.match(l)]
                zones[courant] = textwrap.dedent(
                    "\n".join(corps)).strip("\n")
                courant = None
                continue
            if courant is not None:
                tampon.append(ligne.rstrip("\n"))
    if courant is not None:
        raise ValueError(f"{chemin} — zone '{courant}' jamais fermée.")
    return zones


def zones_du_modele(racine):
    """Identifiants de toutes les ZoneProtegee présentes dans le modèle PSM."""
    trouves = set()

    def parcourir(n):
        if n.classe == "ZoneProtegee":
            trouves.add(n.get("identifiant"))
        for enfants in n.enfants.values():
            for e in enfants:
                parcourir(e)

    parcourir(racine)
    return trouves


def controler_pertes(existantes, attendues):
    """
    Zones présentes dans le fichier mais absentes du modèle : leur contenu
    serait perdu. Retourne la liste des identifiants concernés, en ignorant
    celles dont le contenu est vide ou réduit au marqueur par défaut.
    """
    perdues = []
    for ident, contenu in existantes.items():
        if ident in attendues:
            continue
        utile = [l for l in contenu.splitlines()
                 if l.strip() and not l.strip().startswith("// à compléter")
                 and not l.strip().startswith("// généré")]
        if utile:
            perdues.append(ident)
    return perdues


def ecrire(chemin, contenu):
    """Écrit en sauvegardant la version précédente."""
    os.makedirs(os.path.dirname(chemin), exist_ok=True)
    if os.path.exists(chemin):
        shutil.copy2(chemin, chemin + ".bak")
    with open(chemin, "w", encoding="utf-8") as f:
        f.write(contenu)


def statistiques(zones):
    """Combien de zones sont réellement complétées."""
    remplies = 0
    for contenu in zones.values():
        utile = [l for l in contenu.splitlines()
                 if l.strip() and not l.strip().startswith("//")]
        if utile:
            remplies += 1
    return remplies, len(zones)
