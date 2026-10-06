#!/usr/bin/env python3
"""
Générateur PSM -> GAML.

    python3 generer.py [--backend auto|pyecore|stdlib] [--forcer] [--verifier]

Chaîne complète :

    psm/gaml-psm.ecore  ──┐
                             ├─> chargeur.py ─> graphe de Noeud ─┐
    psm/psm-ids-complet.xmi ┘                                 │
                                                                 ├─> Jinja2 ─> ids_sma.gaml
    ml/artifacts/foret_export.json ─> transpileur_foret.py ─> table CSV ─┘
                                                    └─> cascade INLINE

Le générateur ne contient aucune connaissance du métier ni de la syntaxe
GAML : le métier est dans le modèle, la syntaxe est dans les gabarits. Ce
fichier n'orchestre que le passage de l'un à l'autre.
"""
import argparse
import datetime
import os
import sys
import textwrap
import unicodedata

ICI = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.dirname(ICI)
ECORE = os.path.join(RACINE, "psm", "gaml-psm.ecore")
XMI = os.path.join(RACINE, "psm", "psm-ids-complet.xmi")
SORTIE = os.path.join(RACINE, "gama", "models", "ids_sma.gaml")
CSV = os.path.join(RACINE, "gama", "models", "generated", "foret_table.csv")
DEMO = os.path.join(RACINE, "gama", "models", "generated", "foret_demo.gaml")
ENCODAGE = os.path.join(RACINE, "gama", "models", "generated", "encodage.gaml")
MARQUEUR_MAINTENU = "Note GAMA 2025 : les imports de sous-modeles"


def _garder_monolithe_maintenu(forcer: bool):
    """Refuse d'écraser ids_sma.gaml maintenu à la main sauf --forcer."""
    if forcer or not os.path.isfile(SORTIE):
        return None
    try:
        tete = open(SORTIE, encoding="utf-8").read(800)
    except OSError:
        return None
    if MARQUEUR_MAINTENU not in tete:
        return None
    print()
    print("ARRÊT — ids_sma.gaml est maintenu à la main (monolithe GAMA 2025).")
    print(f"  {os.path.relpath(SORTIE, RACINE)}")
    print("  La régénération Jinja écraserait les correctifs hors zones @user-*.")
    print("  Pour forcer : python generer.py --forcer")
    return 2


# --------------------------------------------------------------------------
# Filtres Jinja2
# --------------------------------------------------------------------------
def sansdiese(v):
    """'#AgentCapture' -> 'AgentCapture'. Les références sont sérialisées par nom."""
    return v[1:] if isinstance(v, str) and v.startswith("#") else v


def envelopper(texte, n=0, largeur=96):
    """
    Replie un commentaire long en lignes de commentaire GAML alignées.

    La première ligne est rendue par le gabarit (qui a déjà écrit l'indentation
    et le '// '), les suivantes sont préfixées ici. Faire porter l'alignement
    par le filtre plutôt que par `indent` évite le décalage de trois caractères
    dû à la longueur du marqueur de commentaire.
    """
    if not texte:
        return ""
    p = "    " * n
    lignes = textwrap.wrap(str(texte), width=max(40, largeur - 4 * n))
    return ("\n" + p + "// ").join(lignes)


def en_ascii(texte):
    """
    Replie tout caractere non-ASCII vers son equivalent ASCII.

    Motif : Eclipse — donc GAMA, donc l'editeur Xtext — lit les fichiers avec
    l'encodage par defaut de la plateforme, qui vaut CP1252 sur Windows et non
    UTF-8. Un fichier genere en UTF-8 contenant des accents y est relu comme
    une suite d'octets invalides. Selon les cas, cela produit du charabia dans
    les commentaires ou une erreur de l'analyseur.

    Plutot que de parier sur la configuration d'encodage du poste, le code
    genere est ASCII pur. C'est une contrainte sans cout : GAML n'a pas besoin
    d'accents, et un fichier genere n'est pas un document.

    Les zones protegees sont repliees elles aussi. L'operation est idempotente
    — replier un texte deja ASCII ne le change pas — donc le test Z4 tient.
    """
    decompose = unicodedata.normalize("NFD", texte)
    sans_diacritiques = "".join(c for c in decompose
                                if unicodedata.category(c) != "Mn")
    substitutions = {
        "\u2014": "-", "\u2013": "-", "\u2019": "'", "\u2018": "'",
        "\u201c": '"', "\u201d": '"', "\u2026": "...", "\u00a0": " ",
        "\u00ab": '"', "\u00bb": '"', "\u2192": "->", "\u2264": "<=",
        "\u2265": ">=", "\u00d7": "x", "\u03bc": "mu", "\u03c4": "tau",
        "\u03bb": "lambda", "\u03b1": "alpha", "\u03b2": "beta",
        "\u00b0": "deg", "\u20ac": "EUR",
    }
    for k, v in substitutions.items():
        sans_diacritiques = sans_diacritiques.replace(k, v)
    # Tout residu non-ASCII est remplace par '?' plutot que supprime : un
    # caractere perdu silencieusement serait plus difficile a reperer qu'un
    # point d'interrogation visible dans un commentaire.
    return sans_diacritiques.encode("ascii", "replace").decode("ascii")


def compter(racine, classe):
    n = [0]

    def p(x):
        if x.classe == classe:
            n[0] += 1
        for L in x.enfants.values():
            for e in L:
                p(e)

    p(racine)
    return n[0]


def collecter(racine, classe):
    out = []

    def p(x):
        if x.classe == classe:
            out.append(x)
        for L in x.enfants.values():
            for e in L:
                p(e)

    p(racine)
    return out


# --------------------------------------------------------------------------
def principal(argv=None):
    ap = argparse.ArgumentParser(description="Génération GAML depuis le PSM")
    ap.add_argument("--backend", default="auto",
                    choices=["auto", "pyecore", "stdlib"])
    ap.add_argument("--forcer", action="store_true",
                    help="écrire même si des zones protégées seraient perdues")
    ap.add_argument("--verifier", action="store_true",
                    help="comparer les deux backends de chargement")
    args = ap.parse_args(argv)

    print("=" * 72)
    print("GÉNÉRATION PSM -> GAML")
    print("=" * 72)

    stop = _garder_monolithe_maintenu(args.forcer)
    if stop is not None:
        return stop

    import jinja2  # noqa: WPS433 — après garde monolithe
    import chargeur
    import transpileur_foret as TF
    import zones_protegees as ZP
    import generateur_encodage as GE

    # --- 1. Chargement du modèle -----------------------------------------
    racine, mm, backend = chargeur.charger(ECORE, XMI, args.backend)
    print(f"[1] modèle chargé      : {racine.get('nom')}  (backend {backend})")
    if backend == "stdlib" and not chargeur.PYECORE_DISPONIBLE:
        print("    PyEcore absent de cet environnement — repli documenté "
              "dans chargeur.py.")

    if args.verifier:
        ecarts = chargeur.comparer_backends(ECORE, XMI)
        if ecarts is None:
            print("    comparaison des backends impossible : PyEcore absent.")
        elif ecarts:
            print(f"    ÉCARTS ENTRE BACKENDS : {len(ecarts)}")
            for e in ecarts[:10]:
                print("       ", e)
            return 1
        else:
            print("    backends stdlib et pyecore : graphes identiques.")

    # --- 2. Transpilation de la forêt ------------------------------------
    foret = TF.charger()
    ressources = {r.get("nom"): r for r in racine.liste("ressources")}
    cascades, racines_table = {}, []

    for nom, r in ressources.items():
        if r.get("strategieGeneration") == "table":
            lignes, racines_table = TF.aplatir(foret)
            TF.ecrire_csv(lignes, foret["classes"], CSV)
            print(f"[2] forêt '{nom}' -> table : {len(lignes)} nœuds, "
                  f"{len(racines_table)} arbres, "
                  f"{os.path.getsize(CSV) / 1e6:.2f} Mo")
        else:
            cascades[nom] = TF.cascade_gaml(
                foret, n_arbres=int(r.get("nbArbres", 3)),
                profondeur_max=int(r.get("profondeurMax", 4)),
                noms_features=foret["features"])
            print(f"[2] forêt '{nom}' -> cascade : "
                  f"{len(cascades[nom].splitlines())} lignes lisibles")

    # --- 3. Zones protégées : relecture avant écriture --------------------
    existantes = ZP.extraire(SORTIE)
    attendues = ZP.zones_du_modele(racine)
    perdues = ZP.controler_pertes(existantes, attendues)
    remplies, total = ZP.statistiques(existantes)
    print(f"[3] zones protégées    : {len(attendues)} au modèle, "
          f"{total} relues, {remplies} complétées")
    if perdues:
        print()
        print("    ARRÊT — ces zones contiennent du code métier absent du modèle :")
        for p in perdues:
            print(f"      - {p}")
        print("    Leur contenu serait perdu. Corrigez le modèle, ou --forcer.")
        if not args.forcer:
            return 1
        print("    --forcer : écriture malgré la perte.")

    # --- 4. Rendu ---------------------------------------------------------
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(os.path.join(ICI, "gabarits")),
        trim_blocks=False, lstrip_blocks=False, keep_trailing_newline=True)
    env.filters["sansdiese"] = sansdiese
    env.filters["envelopper"] = envelopper

    g = racine.liste("sectionGlobale")[0]
    contexte = {
        "m": racine,
        "zones": existantes,
        "ressources": ressources,
        "cascades": cascades,
        "backend": backend,
        "chemin_psm": os.path.relpath(XMI, RACINE).replace("\\", "/"),
        "horodatage": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "parametres_globaux": [a for a in g.liste("attributs")
                               if a.get("estParametre") == "true"],
    }
    # Cible INLINE : fichier séparé, importé par le modèle principal.
    # Deux artefacts distincts issus du même élément ClassifierResource —
    # c'est le point où la double génération devient observable plutôt
    # qu'annoncée.
    prod = next((r for r in ressources.values()
                 if r.get("strategieGeneration") == "table"), None)
    for nom, cascade in cascades.items():
        res = ressources[nom]
        texte_demo = env.get_template("foret_demo.gaml.j2").render(
            res=res, prod=prod, cascade=cascade,
            nb_lignes=len(cascade.splitlines()),
            horodatage=contexte["horodatage"])
        texte_demo = en_ascii(texte_demo)
        ZP.ecrire(DEMO, texte_demo)
        print(f"[4] cible INLINE écrite: {os.path.relpath(DEMO, RACINE)} "
              f"({len(texte_demo.splitlines())} lignes)")

    # Table d'encodage : dérivée de parametres_encodage.json, donc générée.
    # Le vecteur présenté à la forêt en simulation doit être exactement celui
    # qu'elle a vu à l'apprentissage — verifier_encodage.py le contrôle sur
    # données réelles.
    ctx_enc = GE.contexte(racines_table, contexte["horodatage"])
    texte_enc = env.get_template("encodage.gaml.j2").render(**ctx_enc)
    texte_enc = en_ascii(texte_enc)
    ZP.ecrire(ENCODAGE, texte_enc)
    print(f"[4] encodage écrit     : {os.path.relpath(ENCODAGE, RACINE)} "
          f"({len(texte_enc.splitlines())} lignes, "
          f"{ctx_enc['nb_numeriques']} numériques + {ctx_enc['nb_onehot']} indicatrices)")

    texte = env.get_template("modele.gaml.j2").render(**contexte)
    # normalisation : pas plus de deux sauts de ligne consécutifs
    while "\n\n\n" in texte:
        texte = texte.replace("\n\n\n", "\n\n")
    texte = en_ascii(texte)

    ZP.ecrire(SORTIE, texte)

    # --- 5. Rapport -------------------------------------------------------
    nb_lignes = len(texte.splitlines())
    brutes = compter(racine, "ExpressionBrute")
    print(f"[4] GAML écrit         : {os.path.relpath(SORTIE, RACINE)}")
    print(f"    lignes             : {nb_lignes}")
    print(f"    taille             : {len(texte) / 1024:.1f} Ko")
    print()
    print("Indicateurs de qualité du PSM")
    print("-" * 72)
    print(f"  espèces générées         : {len(racine.liste('especes'))}")
    print(f"  réflexes                 : {compter(racine, 'Reflex')}")
    print(f"  tâches (weighted_tasks)  : {compter(racine, 'Task')}")
    print(f"  communications FIPA      : {compter(racine, 'CommunicationFipa')}")
    print(f"  zones protégées          : {compter(racine, 'ZoneProtegee')}")
    print(f"  ExpressionBrute          : {brutes}   (objectif : < 5)")
    if brutes >= 5:
        print("    -> le métamodèle est sous-dimensionné : la chaîne IDM est "
              "contournée en pratique.")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
