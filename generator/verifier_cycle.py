#!/usr/bin/env python3
"""
Test de cycle : générer -> compléter à la main -> régénérer.

Pourquoi ce test existe
-----------------------
Le mécanisme de zones protégées (ADR-05) est le seul endroit du projet où
une erreur détruit du travail humain. Une génération unique ne prouve rien :
le défaut apparaît au DEUXIÈME passage, quand le générateur relit ce qu'il a
lui-même écrit.

C'est exactement ce qui s'est produit ici : le commentaire d'intention était
émis à l'intérieur de la zone, donc relu comme du contenu utilisateur, donc
réinjecté — et dupliqué à chaque régénération. Invisible à la première
génération.

Scénario vérifié
----------------
  1. génération initiale
  2. écriture de code métier dans chaque zone protégée
  3. régénération
  4. le code métier est intact
  5. régénération à nouveau
  6. le fichier est IDENTIQUE à celui de l'étape 3 (idempotence)
  7. suppression d'une zone du modèle -> le générateur refuse d'écrire

L'étape 6 est celle qui aurait attrapé le défaut d'intention dupliquée.
"""
import os
import re
import shutil
import subprocess
import sys

ICI = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.dirname(ICI)
GAML = os.path.join(RACINE, "gama", "models", "ids_sma.gaml")

# Marqueur volontairement ASCII PUR. Il contenait un tiret cadratin, replie
# en "-" par le filtre en_ascii() du generateur : le test cherchait donc une
# chaine qui n'existait plus et concluait a la perte du code metier. Le defaut
# etait dans le test, pas dans le generateur — mais un test qui crie au loup
# finit par etre ignore, ce qui est exactement ce qu'il ne faut pas.
MARQUE = "// CODE METIER DE TEST - ne doit jamais disparaitre"


def generer(*extra):
    r = subprocess.run([sys.executable, os.path.join(ICI, "generer.py"), *extra],
                       capture_output=True, text=True, cwd=ICI)
    return r.returncode, r.stdout + r.stderr


def remplir_zones(chemin):
    """Simule le travail du développeur : écrit du code dans chaque zone."""
    with open(chemin, encoding="utf-8") as f:
        lignes = f.readlines()
    sortie, dans_zone, n = [], False, 0
    for l in lignes:
        d = re.match(r"^(\s*)//\s*@user-begin\(([^)]+)\)", l)
        if d:
            sortie.append(l)
            sortie.append(f"{d.group(1)}{MARQUE} [{d.group(2)}]\n")
            sortie.append(f"{d.group(1)}int compteur_{n} <- {n};\n")
            n += 1
            dans_zone = True
            continue
        if re.match(r"^\s*//\s*@user-end\(", l):
            dans_zone = False
            sortie.append(l)
            continue
        if dans_zone:
            continue          # on remplace le contenu par défaut
        sortie.append(l)
    with open(chemin, "w", encoding="utf-8") as f:
        f.writelines(sortie)
    return n


def main():
    # ---- SAUVEGARDE DU CODE MÉTIER RÉEL ---------------------------------
    # Ce test est destructif par nature : il vide le fichier, y écrit du code
    # factice, régénère plusieurs fois. Tant que les zones protégées étaient
    # vides, c'était sans conséquence. Depuis l'Étape 6 elles contiennent le
    # code métier — signatures RM1–RM11, fusion d'utilité, matrice de confusion
    # — et une exécution du test l'effaçait intégralement.
    #
    # Le défaut a été trouvé en constatant que ids_sma.gaml avait perdu 5 Ko
    # après un verifier_tout.py. Un test qui détruit ce qu'il vérifie est pire
    # qu'un test absent : il donne l'illusion du contrôle.
    sauvegarde = None
    if os.path.exists(GAML) and os.path.getsize(GAML) > 0:
        with open(GAML, encoding="utf-8") as f:
            sauvegarde = f.read()

    try:
        code = deroulement()
    finally:
        if sauvegarde is not None:
            with open(GAML, "w", encoding="utf-8") as f:
                f.write(sauvegarde)
    return code


def deroulement(_ignore=None):
    echecs, succes = [], []

    def verifie(ok, code, msg):
        (succes if ok else echecs).append(f"{code} : {msg}")

    # 1 -------------------------------------------------------------------
    # On vide le fichier plutôt que de le supprimer : certains montages
    # (conteneurs, partages réseau) interdisent unlink mais autorisent write.
    os.makedirs(os.path.dirname(GAML), exist_ok=True)
    open(GAML, "w", encoding="utf-8").close()
    rc, _ = generer()
    verifie(rc == 0 and os.path.getsize(GAML) > 0, "Z1",
            "génération initiale depuis un répertoire vide")

    # 2 -------------------------------------------------------------------
    n = remplir_zones(GAML)
    verifie(n > 0, "Z2", f"{n} zones protégées complétées à la main")
    apres_saisie = open(GAML, encoding="utf-8").read()

    # 3 / 4 ---------------------------------------------------------------
    rc, sortie = generer()
    contenu = open(GAML, encoding="utf-8").read()
    conserves = contenu.count(MARQUE)
    verifie(rc == 0 and conserves == n, "Z3",
            f"régénération : {conserves}/{n} blocs de code métier conservés")

    # 5 / 6 : idempotence --------------------------------------------------
    premiere = contenu
    rc, _ = generer()
    seconde = open(GAML, encoding="utf-8").read()

    def sans_horodatage(t):
        return re.sub(r"Généré le\s+:.*", "", t)

    identique = sans_horodatage(premiere) == sans_horodatage(seconde)
    verifie(identique, "Z4",
            "idempotence : deux régénérations successives donnent le même fichier")
    if not identique:
        a = sans_horodatage(premiere).splitlines()
        b = sans_horodatage(seconde).splitlines()
        for i, (x, y) in enumerate(zip(a, b)):
            if x != y:
                echecs.append(f"       première divergence ligne {i + 1} :")
                echecs.append(f"         gén.1 : {x[:90]}")
                echecs.append(f"         gén.2 : {y[:90]}")
                break
        if len(a) != len(b):
            echecs.append(f"       longueurs : {len(a)} vs {len(b)} lignes")

    # 7 : refus d'écrire si une zone du fichier n'est plus au modèle --------
    with open(GAML, encoding="utf-8") as f:
        t = f.read()
    t = t.replace("// @user-begin(calcul_utilite)",
                  "// @user-begin(zone_disparue_du_modele)")
    t = t.replace("// @user-end(calcul_utilite)",
                  "// @user-end(zone_disparue_du_modele)")
    with open(GAML, "w", encoding="utf-8") as f:
        f.write(t)

    rc, sortie = generer()
    verifie(rc == 1 and "ARRÊT" in sortie, "Z5",
            "refus d'écrire quand du code métier n'a plus de zone au modèle")
    verifie("zone_disparue_du_modele" in sortie, "Z6",
            "la zone menacée est nommée dans le message d'arrêt")

    rc, sortie = generer("--forcer")
    verifie(rc == 0, "Z7", "--forcer permet d'écrire malgré l'avertissement")

    # remise en état -------------------------------------------------------
    generer()

    print("Test de cycle génération / complétion / régénération")
    print("-" * 66)
    for s in succes:
        print("  OK    " + s)
    for e in echecs:
        print("  ECHEC " + e)
    print()
    print(f"{len(succes)} réussite(s), {len(echecs)} échec(s).")
    return 1 if echecs else 0


if __name__ == "__main__":
    sys.exit(main())
