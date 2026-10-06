#!/usr/bin/env python3
"""
Construction du contexte de génération de generated/encodage.gaml.

Ce module traduit ml/artifacts/parametres_encodage.json en littéraux GAML. Il ne
prend aucune décision : il transcrit. Toute décision d'encodage a été prise
à l'Étape 3 et mesurée là-bas.

Point délicat, à ne pas manquer
-------------------------------
preprocessing.py construit le vecteur dans cet ordre : d'abord les 38 colonnes
numériques dans l'ordre du fichier, puis les blocs one-hot de protocol_type,
service et flag. Les indices des indicatrices dépendent donc de la taille des
blocs précédents. Se tromper d'offset donnerait un vecteur syntaxiquement
valide et sémantiquement faux — la forêt lirait « service=http » là où le
modèle a appris « flag=SF ». Le contrôle croisé est fait par
verifier_encodage.py, qui compare l'encodage GAML réimplémenté en Python au
vecteur produit par preprocessing.py sur des lignes réelles.
"""
import json
import os

ICI = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.dirname(ICI)
PARAMS = os.path.join(RACINE, "ml", "artifacts", "parametres_encodage.json")

# Colonnes du fichier NSL-KDD brut (41 champs + label + difficulty)
COLONNES_BRUTES = [
    'duration', 'protocol_type', 'service', 'flag', 'src_bytes', 'dst_bytes',
    'land', 'wrong_fragment', 'urgent', 'hot', 'num_failed_logins',
    'logged_in', 'num_compromised', 'root_shell', 'su_attempted', 'num_root',
    'num_file_creations', 'num_shells', 'num_access_files',
    'num_outbound_cmds', 'is_host_login', 'is_guest_login', 'count',
    'srv_count', 'serror_rate', 'srv_serror_rate', 'rerror_rate',
    'srv_rerror_rate', 'same_srv_rate', 'diff_srv_rate', 'srv_diff_host_rate',
    'dst_host_count', 'dst_host_srv_count', 'dst_host_same_srv_rate',
    'dst_host_diff_srv_rate', 'dst_host_same_src_port_rate',
    'dst_host_srv_diff_host_rate', 'dst_host_serror_rate',
    'dst_host_srv_serror_rate', 'dst_host_rerror_rate',
    'dst_host_srv_rerror_rate', 'label', 'difficulty',
]

DOS = {'back', 'land', 'neptune', 'pod', 'smurf', 'teardrop', 'apache2',
       'udpstorm', 'processtable', 'mailbomb', 'worm'}
PROBE = {'satan', 'ipsweep', 'nmap', 'portsweep', 'mscan', 'saint'}
R2L = {'guess_passwd', 'ftp_write', 'imap', 'phf', 'multihop', 'warezmaster',
       'warezclient', 'spy', 'xlock', 'xsnoop', 'snmpguess', 'snmpgetattack',
       'httptunnel', 'sendmail', 'named'}
U2R = {'buffer_overflow', 'loadmodule', 'rootkit', 'perl', 'sqlattack',
       'xterm', 'ps'}


# Longueur maximale d'une ligne generee.
#
# Motif : l'editeur Xtext de GAMA analyse le fichier ligne par ligne et
# certaines de ses regles de mise en forme se comportent mal sur des lignes de
# plusieurs milliers de caracteres. L'index nomme des 122 composantes tenait
# sur une seule ligne de 2541 caracteres. Rien ne dit que c'etait la cause de
# l'erreur observee, mais c'est une anomalie gratuite dans du code genere :
# elle ne coute rien a supprimer et rend le fichier relisible.
LARGEUR_MAX = 100


def _envelopper(elements, ouvrant, fermant, indent=8):
    """Repartit des elements sur plusieurs lignes sans depasser LARGEUR_MAX."""
    lignes, courante = [], ""
    for i, e in enumerate(elements):
        morceau = e + ("," if i < len(elements) - 1 else "")
        if courante and len(courante) + len(morceau) > LARGEUR_MAX:
            lignes.append(courante)
            courante = morceau
        else:
            courante += morceau
    if courante:
        lignes.append(courante)
    if len(lignes) == 1:
        return ouvrant + lignes[0] + fermant
    saut = "\n" + " " * indent
    return ouvrant + saut + saut.join(lignes) + saut + fermant


def _liste_gaml(valeurs, precision=6):
    if not valeurs:
        return "[]"
    if isinstance(valeurs[0], float):
        elems = [f"{v:.{precision}f}" for v in valeurs]
    elif isinstance(valeurs[0], str):
        elems = [f"'{v}'" for v in valeurs]
    else:
        elems = [str(int(v)) for v in valeurs]
    return _envelopper(elems, "[", "]")


def _map_gaml(d):
    return _envelopper([f"'{k}'::{v}" for k, v in d.items()], "map([", "])")


def charger_parametres(chemin=PARAMS):
    with open(chemin, encoding="utf-8") as f:
        return json.load(f)


def contexte(racines_foret, horodatage, chemin=PARAMS):
    p = charger_parametres(chemin)
    features = p["features"]
    num = p["colonnes_numeriques"]
    vocab = p["vocabulaires"]

    # Indice, dans la ligne BRUTE, de chaque colonne numérique. L'ordre du
    # vecteur encodé suit l'ordre de p["colonnes_numeriques"], qui est celui
    # de preprocessing.py.
    colonnes_num = [COLONNES_BRUTES.index(c) for c in num]

    # Position de départ de chaque bloc one-hot dans le vecteur encodé.
    # features est la liste ordonnée produite par preprocessing.py : on y
    # RETROUVE les indices plutôt que de les recalculer, ce qui supprime toute
    # possibilité de décalage.
    vocabulaires, categorielles = {}, {}
    for nom in vocab:
        table = {}
        for modalite in vocab[nom]:
            cle = f"{nom}={modalite}"
            table[modalite] = features.index(cle)
        vocabulaires[nom] = _map_gaml(table)
        categorielles[nom] = {"colonne": COLONNES_BRUTES.index(nom)}

    etiquettes = {
        "DOS": _liste_gaml(sorted(DOS)),
        "PROBE": _liste_gaml(sorted(PROBE)),
        "R2L": _liste_gaml(sorted(R2L)),
        "U2R": _liste_gaml(sorted(U2R)),
    }

    return {
        "nb_features": len(features),
        "nb_numeriques": len(num),
        "nb_onehot": len(features) - len(num),
        "nb_arbres": len(racines_foret),
        "racines": _liste_gaml(racines_foret),
        "bornes_min": _liste_gaml([p["min"][i] for i in range(len(num))]),
        "bornes_max": _liste_gaml([p["max"][i] for i in range(len(num))]),
        "colonnes_num": _liste_gaml(colonnes_num),
        "vocabulaires": vocabulaires,
        "categorielles": categorielles,
        "index_features": _map_gaml({f: i for i, f in enumerate(features)}),
        "colonne_label": COLONNES_BRUTES.index("label"),
        "etiquettes": etiquettes,
        "indices": {c: i for i, c in enumerate(p["classes"])},
        "horodatage": horodatage,
    }


# ==========================================================================
# Réimplémentation Python de encoder_connexion, pour vérification croisée
# ==========================================================================
def encoder_python(ligne_brute, ctx, params):
    """
    Transcription en Python de l'action GAML générée. Sert d'oracle :
    verifier_encodage.py compare son résultat à celui de preprocessing.py.
    Sans cette comparaison, la correction des offsets one-hot ne serait
    qu'une intention.
    """
    features = params["features"]
    num = params["colonnes_numeriques"]
    v = [0.0] * len(features)

    colonnes_num = [COLONNES_BRUTES.index(c) for c in num]
    for j, c in enumerate(colonnes_num):
        x = float(ligne_brute[c])
        mn, mx = params["min"][j], params["max"][j]
        etendue = mx - mn
        xn = 0.0 if etendue == 0 else (x - mn) / etendue
        v[j] = min(1.0, max(0.0, xn))

    inconnues = 0
    for nom in params["vocabulaires"]:
        modalite = str(ligne_brute[COLONNES_BRUTES.index(nom)])
        cle = f"{nom}={modalite}"
        if cle in features:
            v[features.index(cle)] = 1.0
        else:
            inconnues += 1
    return v, inconnues
