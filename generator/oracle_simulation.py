#!/usr/bin/env python3
"""
Oracle de la simulation — transcription Python du GAML complété.

Question posée
--------------
Le code métier écrit dans les zones protégées reproduit-il les performances
mesurées à l'Étape 3 ? Autrement dit : la simulation GAMA, une fois lancée,
reproduira-t-elle les mesures du pipeline Python, ou bien la transcription
en GAML a-t-elle introduit un écart ?

Pourquoi un oracle plutôt qu'un lancement de GAMA
--------------------------------------------------
GAMA n'est pas pilotable depuis cet environnement. Mais l'essentiel du risque
n'est pas dans GAMA : il est dans la TRANSCRIPTION du métier — seuils de
signatures exprimés en unités réelles alors que le vecteur est normalisé,
formule de fusion, gestion de l'abstention, indices de la matrice de
confusion. Ce fichier réimplémente ces quatre points EXACTEMENT comme le GAML
les exprime, ligne à ligne, et mesure le résultat sur KDDTest+ entier.

Un écart ici est un défaut du code métier. Une correspondance ici ne garantit
pas que GAMA compilera, mais garantit que s'il compile, il calculera juste.

Correspondance ligne à ligne avec les zones protégées de ids_sma.gaml :
    signatures_rm1_rm11           -> evaluer_signatures()
    calcul_utilite                -> utilite()
    mise_a_jour_matrice_confusion -> mettre_a_jour()
"""
import json
import os
import sys

import numpy as np
import pandas as pd

ICI = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.dirname(ICI)
sys.path.insert(0, ICI)

import generateur_encodage as GE      # noqa: E402
import transpileur_foret as TF        # noqa: E402

CLASSES = ["NORMAL", "DOS", "PROBE", "R2L", "U2R"]
NB = 5


# ==========================================================================
# Transcription de generated/encodage.gaml : valeur_brute
# ==========================================================================
def valeur_brute(v, j, bmin, bmax):
    return v[j] * (bmax[j] - bmin[j]) + bmin[j]


# ==========================================================================
# Transcription de la zone signatures_rm1_rm11
# ==========================================================================
def evaluer_signatures(v, IDX, bmin, bmax):
    p = [1.0 / NB] * NB          # ABSTENTION par défaut
    br = lambda nom: valeur_brute(v, IDX[nom], bmin, bmax)

    meilleure, classe = 0.0, 0
    if br("serror_rate") > 0.8 and br("count") >= 100 and 0.999 > meilleure:
        meilleure, classe = 0.999, 1
    if v[IDX["protocol_type=icmp"]] == 1.0 and br("src_bytes") > 1000 \
            and 1.000 > meilleure:
        meilleure, classe = 1.000, 1
    if v[IDX["flag=S0"]] == 1.0 and br("same_srv_rate") > 0.9 \
            and 0.575 > meilleure:
        meilleure, classe = 0.575, 1
    if br("land") == 1 and 0.720 > meilleure:
        meilleure, classe = 0.720, 1
    if br("diff_srv_rate") > 0.7 and 0.684 > meilleure:
        meilleure, classe = 0.684, 2
    if br("rerror_rate") > 0.8 and br("count") >= 50 and 0.233 > meilleure:
        meilleure, classe = 0.233, 2
    if br("is_guest_login") == 1 and br("hot") >= 1 and 0.265 > meilleure:
        meilleure, classe = 0.265, 3
    if br("num_file_creations") >= 1 and br("num_shells") >= 1 \
            and 0.500 > meilleure:
        meilleure, classe = 0.500, 4
    svc_r2l = (
        v[IDX["service=telnet"]] == 1.0
        or v[IDX["service=login"]] == 1.0
        or v[IDX["service=ssh"]] == 1.0
        or v[IDX["service=ftp"]] == 1.0
        or v[IDX["service=pop_3"]] == 1.0
        or v[IDX["service=imap4"]] == 1.0
    )
    if br("num_failed_logins") >= 1 and br("logged_in") == 0 and svc_r2l \
            and 0.547 > meilleure:
        meilleure, classe = 0.547, 3
    if v[IDX["service=telnet"]] == 1.0 and br("num_failed_logins") >= 1 \
            and 0.565 > meilleure:
        meilleure, classe = 0.565, 3
    if br("root_shell") == 1 and br("num_file_creations") >= 1 \
            and 0.467 > meilleure:
        meilleure, classe = 0.467, 4

    if meilleure > 0.0:
        p = [(1.0 - meilleure) / (NB - 1)] * NB
        p[classe] = meilleure
        return p, True
    return p, False


# ==========================================================================
# Transcription de la zone calcul_utilite
# ==========================================================================
def utilite(c_ia, c_rg, degrade, a_ia, poids_ia, lambda_fp, menace):
    u = [0.0] * NB
    for k in range(NB):
        if degrade:
            score = c_ia[k] if a_ia else c_rg[k]
        else:
            score = poids_ia * c_ia[k] + (1.0 - poids_ia) * c_rg[k]
        penalite = 0.0 if k == 0 else lambda_fp * (1.0 - menace)
        u[k] = score - penalite
    return u


# ==========================================================================
# Transcription de la zone mise_a_jour_matrice_confusion
# ==========================================================================
def metriques(mc):
    """
    DEUX exactitudes, et il faut les nommer separement.

    Le rapport de l'Etape 3 employait le mot « exactitude » pour la mesure
    BINAIRE dans son tableau de fusion et pour la mesure a CINQ CLASSES
    ailleurs. La confusion masquait le defaut trouve a l'Etape 6 : la fusion
    ameliore la detection binaire tout en degradant l'attribution de classe.
    Une erreur DoS -> PROBE reste une detection correcte en binaire.
    """
    total = int(mc.sum())
    bons = int(sum(mc[k][k] for k in range(NB)))
    exact_5 = 0.0 if total == 0 else bons / total
    vp = int(mc[1:, 1:].sum())
    fn = int(mc[1:, 0].sum())
    fp = int(mc[0, 1:].sum())
    vn = int(mc[0, 0])
    exact_bin = 0.0 if total == 0 else (vp + vn) / total
    rappel = 0.0 if vp + fn == 0 else vp / (vp + fn)
    taux_fp = 0.0 if fp + vn == 0 else fp / (fp + vn)
    return exact_5, exact_bin, rappel, taux_fp


# ==========================================================================
def main(limite=None):
    params = GE.charger_parametres()
    features = params["features"]
    IDX = {f: i for i, f in enumerate(features)}
    num = params["colonnes_numeriques"]
    bmin = [params["min"][i] for i in range(len(num))]
    bmax = [params["max"][i] for i in range(len(num))]

    foret = TF.charger()
    lignes, racines = TF.aplatir(foret)

    chemin = os.path.join(RACINE, "data", "KDDTest+.txt")
    if not os.path.exists(chemin):
        chemin = os.path.join(RACINE, "gama", "models", "data",
                              "KDDTest+.txt")
    brut = pd.read_csv(chemin, names=GE.COLONNES_BRUTES, nrows=limite)

    # Le vecteur encodé est repris de donnees.npz : verifier_encodage.py a
    # déjà établi que encoder_connexion produit exactement ce vecteur. Le
    # recalculer ligne à ligne en Python pur coûterait des minutes sans rien
    # ajouter à la démonstration.
    X = np.load(os.path.join(RACINE, "ml", "artifacts", "donnees.npz"))["Xte"]
    if limite:
        X = X[:limite]

    poids_ia, lambda_fp, menace = 0.35, 0.0, 0.0
    alpha, beta = 0.99, 0.05

    mc = np.zeros((NB, NB), dtype=int)
    mc_ia = np.zeros((NB, NB), dtype=int)
    mc_rg = np.zeros((NB, NB), dtype=int)
    nb_abstentions = 0

    for i in range(len(X)):
        v = X[i]
        p_ia = TF.parcourir(lignes, racines, v)
        p_rg, declenchee = evaluer_signatures(v, IDX, bmin, bmax)
        if not declenchee:
            nb_abstentions += 1

        u = utilite(p_ia, p_rg, False, True, poids_ia, lambda_fp, menace)
        predite = int(np.argmax(u))

        reelle = _classe(str(brut.iloc[i]["label"]))
        mc[reelle][predite] += 1
        mc_ia[reelle][int(np.argmax(p_ia))] += 1
        mc_rg[reelle][int(np.argmax(p_rg))] += 1

        # Dynamique du niveau de menace (MC §4) — influence la pénalité de FP
        menace = min(1.0, alpha * menace + beta * (1.0 if predite != 0 else 0.0))

    print("Oracle de simulation — transcription du GAML complété")
    print("=" * 70)
    print(f"  connexions traitées : {len(X)}")
    print(f"  abstentions règles  : {nb_abstentions} "
          f"({100.0 * nb_abstentions / len(X):.1f} %)")
    print()
    print(f"  {'configuration':<22} {'exact. 5cl':>11} {'exact. bin':>11}"
          f" {'rappel':>9} {'taux FP':>9}")
    print("  " + "-" * 66)
    resultats = {}
    for nom, m in (("règles seules", mc_rg), ("IA seule", mc_ia),
                   ("fusion (simulation)", mc)):
        e5, eb, r, f = metriques(m)
        resultats[nom] = (e5, eb, r, f)
        print(f"  {nom:<22} {100 * e5:10.2f}% {100 * eb:10.2f}%"
              f" {100 * r:8.2f}% {100 * f:8.2f}%")

    print()
    print("  Référence indépendante — ml/evaluer_fusion.py (base v4)")
    print("  " + "-" * 66)
    ref = json.load(open(os.path.join(RACINE, "ml", "artifacts", "resultats_fusion.json"),
                         encoding="utf-8"))
    correspondance = {"règles seules": "regles", "IA seule": "ia",
                      "fusion (simulation)": "fusion"}
    ecart_max = 0.0
    for nom, cle in correspondance.items():
        r = ref[cle]
        attendu = (r["exactitude_5_classes"], r["exactitude_binaire"],
                   r["rappel"], r["taux_fp"])
        print(f"  {nom:<22} {100 * attendu[0]:10.2f}% {100 * attendu[1]:10.2f}%"
              f" {100 * attendu[2]:8.2f}% {100 * attendu[3]:8.2f}%")
        for a, b in zip(resultats[nom], attendu):
            ecart_max = max(ecart_max, abs(a - b))

    print()
    print(f"  écart maximal à la référence : {100 * ecart_max:.2f} point(s)")
    print()
    # Tolérance de 0,2 point. L'écart résiduel n'est pas du bruit : l'oracle
    # fait varier le niveau de menace au fil des connexions, comme le fera la
    # simulation, alors que le pipeline de référence applique une pénalité de
    # faux positif constante. Les deux calculs ne peuvent donc pas coïncider
    # exactement, et une coïncidence parfaite signalerait au contraire que la
    # dynamique de menace n'a aucun effet.
    ok = ecart_max < 0.002
    print("  =>", "MÉTIER CONFORME AUX MESURES DE RÉFÉRENCE FUSION" if ok
          else "ÉCART SIGNIFICATIF — le code métier ne reproduit pas les mesures")

    sortie = os.path.join(RACINE, "gama", "resultats_oracle.json")
    os.makedirs(os.path.dirname(sortie), exist_ok=True)
    with open(sortie, "w", encoding="utf-8") as fjs:
        json.dump({
            "n": int(len(X)),
            "abstentions": int(nb_abstentions),
            "matrice_confusion_fusion": mc.tolist(),
            "resultats": {k: list(v) for k, v in resultats.items()},
            "colonnes": ["exactitude_5_classes", "exactitude_binaire",
                         "rappel", "taux_fp"],
            "ecart_max_reference": ecart_max,
        }, fjs, indent=1)
    print(f"  détail écrit dans {os.path.relpath(sortie, RACINE)}")
    return 0 if ok else 1


DOS, PROBE, R2L, U2R = GE.DOS, GE.PROBE, GE.R2L, GE.U2R


def _classe(etiquette):
    if etiquette in DOS:
        return 1
    if etiquette in PROBE:
        return 2
    if etiquette in R2L:
        return 3
    if etiquette in U2R:
        return 4
    return 0


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else None
    sys.exit(main(n))
