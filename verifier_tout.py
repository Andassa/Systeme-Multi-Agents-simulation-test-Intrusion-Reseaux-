#!/usr/bin/env python3
"""
Vérification complète de la chaîne IDM, depuis la racine du projet.

    python verifier_tout.py

Ce script existe pour répondre à une question précise : après un déplacement
du projet, est-ce que tout fonctionne encore ? Il enchaîne les vérifications
déjà écrites à chaque étape et rend un verdict unique.

Il ne vérifie PAS la compilation GAML — cela demande GAMA, qui n'est pas
pilotable depuis Python. Ce point reste manuel.
"""
import os
import subprocess
import sys

RACINE = os.path.dirname(os.path.abspath(__file__))

ETAPES = [
    ("Baseline — contrat exactitude / invariants GAML",
     ["tests/test_baseline.py"], "."),
    ("Métamodèle Ecore — structure (V1..V10)",
     ["psm/valider_metamodele.py", "gaml-psm.ecore"], "psm"),
    ("Instance minimale — conformité + C1..C10",
     ["psm/verifier_contraintes.py", "exemple-psm-minimal.xmi",
      "gaml-psm.ecore"], "psm"),
    ("Instance complète — conformité + C1..C10",
     ["psm/verifier_contraintes.py", "psm-ids-complet.xmi",
      "gaml-psm.ecore"], "psm"),
    ("Transpilation de la forêt — équivalence numérique",
     ["generator/transpileur_foret.py"], "generator"),
    ("Encodage GAML conforme au modèle entraîné",
     ["generator/verifier_encodage.py"], "generator"),
    ("Référence de fusion (base de règles v3)",
     ["ml/evaluer_fusion.py"], "ml"),
    ("Oracle — le métier GAML reproduit la référence",
     ["generator/oracle_simulation.py"], "generator"),
]

ARTEFACTS = [
    "psm/gaml-psm.ecore",
    "psm/psm-ids-complet.xmi",
    "ml/artifacts/foret_export.json",
    "gama/models/ids_sma.gaml",
    "gama/models/generated/foret_table.csv",
    "gama/models/generated/foret_demo.gaml",
    "gama/models/generated/encodage.gaml",
    "ml/artifacts/resultats_fusion.json",
    "gama/models/data/KDDTest+.txt",
]


def lancer(titre, argv, cwd):
    script = os.path.join(RACINE, argv[0])
    if not os.path.exists(script):
        return False, f"script absent : {argv[0]}", ""
    r = subprocess.run([sys.executable, script] + argv[1:],
                       cwd=os.path.join(RACINE, cwd),
                       capture_output=True, text=True)
    return r.returncode == 0, "", r.stdout + r.stderr


def main():
    print("=" * 74)
    print("VÉRIFICATION DE LA CHAÎNE IDM")
    print(f"racine : {RACINE}")
    print("=" * 74)
    print()

    echecs = 0

    print("Dépendances")
    print("-" * 74)
    for mod in ("jinja2", "numpy", "pandas", "pyecore", "lxml"):
        try:
            __import__(mod)
            print(f"  OK      {mod}")
        except ImportError:
            obligatoire = mod in ("jinja2", "numpy")
            print(f"  {'MANQUE ' if obligatoire else 'absent  '}{mod}"
                  f"{'  (obligatoire)' if obligatoire else '  (optionnel)'}")
            if obligatoire:
                echecs += 1
    print()

    print("Étapes")
    print("-" * 74)
    for titre, argv, cwd in ETAPES:
        ok, err, sortie = lancer(titre, argv, cwd)
        print(f"  {'OK   ' if ok else 'ECHEC'}  {titre}")
        if not ok:
            echecs += 1
            for l in (err or sortie).strip().splitlines()[-12:]:
                print(f"           {l}")
    print()

    print("Artefacts produits")
    print("-" * 74)
    for a in ARTEFACTS:
        p = os.path.join(RACINE, a)
        if os.path.exists(p):
            t = os.path.getsize(p)
            unite = f"{t / 1e6:.2f} Mo" if t > 1e6 else f"{t / 1024:.1f} Ko"
            print(f"  OK      {a:52s} {unite:>10s}")
        else:
            print(f"  ABSENT  {a}")
            echecs += 1
    print()

    print("=" * 74)
    if echecs:
        print(f"{echecs} problème(s). La chaîne n'est pas opérationnelle en l'état.")
    else:
        print("Chaîne IDM opérationnelle depuis cette racine.")
        print()
        print("Reste manuel — non vérifiable depuis Python :")
        print("  - compiler gama/models/ids_sma.gaml dans GAMA 2025.6.4")
        print("  - lancer l'expérience ids_gui")
    print("=" * 74)
    return 1 if echecs else 0


if __name__ == "__main__":
    sys.exit(main())
