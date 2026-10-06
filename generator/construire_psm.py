#!/usr/bin/env python3
"""
Construction de l'instance PSM complète — application des règles T-1 à T-11.

Pourquoi un script plutôt qu'un fichier XMI saisi à la main
------------------------------------------------------------
Le PSM complet compte plus de 400 éléments. Le saisir à la main serait
long, illisible et surtout non reproductible : une correction du PIM
imposerait une reprise manuelle intégrale, ce qui est précisément le
travail que l'IDM prétend supprimer.

Ce script EST la transformation PIM -> PSM. Chaque fonction construire_*
implémente les règles T-1 à T-11 documentées en psm/05-PSM.md §4. La
traçabilité est portée dans le modèle lui-même par les attributs
`classePim`, `butPim` et `contratPim`.

Limite à énoncer honnêtement : le PIM n'existe pas ici sous forme de modèle
formel (c'est un document et des diagrammes PlantUML). Cette transformation
est donc écrite d'après le PIM, non calculée depuis lui. Une chaîne
entièrement outillée aurait un PIM Ecore et une transformation M2M — hors
d'atteinte en trois semaines, et sans valeur pédagogique supplémentaire.

Sortie : psm/psm-ids-complet.xmi
"""
import os
import xml.etree.ElementTree as ET

ICI = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.dirname(ICI)
SORTIE = os.path.join(RACINE, "psm", "psm-ids-complet.xmi")

NS_PSM = "http://ids-sma-idm.org/psm/gaml/1.0"
NS_XSI = "http://www.w3.org/2001/XMLSchema-instance"
NS_XMI = "http://www.omg.org/XMI"


# ==========================================================================
# Fabriques d'éléments — une par concept du métamodèle
# ==========================================================================
def el(parent, tag, type_=None, identifiable=False, **attrs):
    e = ET.SubElement(parent, tag)
    if type_:
        e.set(f"{{{NS_XSI}}}type", f"gamlpsm:{type_}")
    for k, v in attrs.items():
        if v is None:
            continue
        e.set(k, str(v))
    if identifiable and attrs.get("nom"):
        # xmi:id — obligatoire pour que les références '#nom' se résolvent.
        #
        # Le modèle sérialise ses références inter-objets par nom ('#ACTIF',
        # '#AgentCapture'), forme lisible et stable choisie à l'Étape 4 contre
        # le chemin indexé ('//@especes.3/@etats.1'), qui devient faux dès
        # qu'un élément est inséré en amont.
        #
        # Mais cette forme n'est valide en XMI que si la cible porte un
        # xmi:id du même nom. Sans lui, EMF et PyEcore retirent le '#',
        # cherchent l'identifiant dans leur registre et échouent —
        # « KeyError: 'AgentCapture' ». Le chargeur stdlib, lui, résolvait par
        # le nom et ne voyait rien : le modèle était valide pour un seul des
        # deux lecteurs, ce qui est la définition d'un format non standard.
        e.set(f"{{{NS_XMI}}}id", str(attrs["nom"]))
    return e


def attribut(parent, nom, type_, init=None, **kw):
    return el(parent, "attributs", nom=nom, type=type_, initialisation=init, **kw)


def parametre(parent, nom, type_, init, libelle, mini, maxi, categorie):
    return el(parent, "attributs", nom=nom, type=type_, initialisation=init,
              estParametre="true", libelle=libelle, minimum=mini,
              maximum=maxi, categorie=categorie)


def aff(parent, cible, expression, declaration=None, type_element=None,
        commentaire=None, balise="corps"):
    return el(parent, balise, "Affectation", cible=cible, expression=expression,
              declaration=declaration, typeElement=type_element,
              commentaire=commentaire)


def si(parent, condition, balise="corps", commentaire=None):
    return el(parent, balise, "Conditionnelle", condition=condition,
              commentaire=commentaire)


def boucle(parent, variable=None, collection=None, tantque=None, balise="corps"):
    return el(parent, balise, "Boucle", variable=variable, collection=collection,
              conditionTantQue=tantque)


def fipa(parent, genre, performatif, contenus, contrat, destinataires=None,
         message=None, balise="corps"):
    return el(parent, balise, "CommunicationFipa", genre=genre,
              performatif=performatif, protocole="PROTOCOLE_IDS",
              destinataires=destinataires, contenus=contenus,
              messageSource=message, contratPim=contrat)


def zone(parent, identifiant, intention, defaut="// à compléter", balise="corps"):
    return el(parent, balise, "ZoneProtegee", identifiant=identifiant,
              intention=intention, contenuParDefaut=defaut)


def appel(parent, nom, resultat=None, type_resultat=None, type_element=None,
          balise="corps", **args):
    a = el(parent, balise, "AppelAction", nom=nom, resultatDans=resultat,
           typeResultat=type_resultat, typeElement=type_element)
    for k, v in args.items():
        el(a, "arguments", nom=k, expression=v)
    return a


def retour(parent, expression=None, balise="corps"):
    return el(parent, balise, "Retour", expression=expression)


def ecrire(parent, expression, balise="corps", commentaire=None):
    return el(parent, balise, "Ecriture", expression=expression,
              commentaire=commentaire)


# ==========================================================================
# T-1 / T-2 / T-3 : projection des trois classes d'agent du PIM
# ==========================================================================
ARCHITECTURE = {
    "AgentReactif": "REFLEX",
    "AgentBaseModele": "FSM",
    "AgentBaseButs": "WEIGHTED_TASKS",
}


def espece(racine, nom, classe_pim, **kw):
    """Applique T-1/T-2/T-3 : la classe PIM détermine l'architecture GAML."""
    base = classe_pim.split("::")[0]
    return el(racine, "especes", identifiable=True, nom=nom,
              architecture=ARCHITECTURE[base], skills="FIPA",
              classePim=classe_pim, **kw)


# ==========================================================================
# SECTION GLOBALE
# ==========================================================================
def construire_global(racine):
    g = el(racine, "sectionGlobale")

    # -- constantes de protocole ------------------------------------------
    attribut(g, "PROTOCOLE_IDS", "STRING", "'no-protocol'",
             commentaire="RÉSOLU à l'Étape 6. 'no-protocol' est la seule valeur "
                         "explicitement documentée avec 'fipa-propose' en 2025-06. "
                         "Elle laisse le modélisateur maître de la séquence — et "
                         "lui impose d'émettre end_conversation, sans quoi les "
                         "conversations s'accumulent indéfiniment dans la liste "
                         "'conversations' de chaque agent.")
    attribut(g, "CLASSES", "LIST", "['NORMAL','DOS','PROBE','R2L','U2R']",
             typeElement="STRING")
    attribut(g, "NB_CLASSES", "INT", "5")
    attribut(g, "NB_FEATURES", "INT", "122")

    # -- paramètres exposés à l'expérience (EF9) ---------------------------
    parametre(g, "poids_ia", "FLOAT", "0.35", "Poids de la source IA",
              "0.0", "1.0", "Fusion")
    parametre(g, "lambda_fp", "FLOAT", "0.0", "Pénalité de faux positif",
              "0.0", "1.0", "Fusion")
    parametre(g, "delai_garde", "INT", "3", "Délai de garde tau (cycles)",
              "1", "20", "Fusion")
    parametre(g, "seuil_alerte", "FLOAT", "0.5", "Seuil de gravité d'alerte",
              "0.0", "1.0", "Alertes")
    parametre(g, "debit_capture", "INT", "10",
              "Connexions lues par cycle", "1", "100", "Capture")
    parametre(g, "capacite_file", "INT", "200",
              "Capacité des files d'entrée (EF11)", "1", "500", "Capture")
    parametre(g, "taux_panne", "FLOAT", "0.0",
              "p_f — probabilité de panne par cycle", "0.0", "0.5", "Pannes")
    parametre(g, "taux_reprise", "FLOAT", "0.20",
              "p_r — probabilité de reprise par cycle", "0.0", "1.0", "Pannes")
    parametre(g, "alpha_menace", "FLOAT", "0.99",
              "Décroissance du niveau de menace", "0.0", "1.0", "Menace")
    parametre(g, "beta_menace", "FLOAT", "0.05",
              "Incrément par détection", "0.0", "1.0", "Menace")

    # -- état de l'environnement partagé (EF8) -----------------------------
    attribut(g, "niveau_menace", "FLOAT", "0.0")
    attribut(g, "matrice_confusion", "LIST", "list_with(25, 0)",
             typeElement="INT",
             commentaire="ADR-07 : la simulation calcule ses propres métriques "
                         "à partir de la vérité terrain portée par le dataset. "
                         "Indice = 5 * classe_reelle + classe_predite.")
    attribut(g, "nb_decisions", "INT", "0")
    attribut(g, "nb_degradees", "INT", "0")
    attribut(g, "nb_abandons", "INT", "0")
    attribut(g, "nb_rejets_file", "INT", "0")
    attribut(g, "exactitude_courante", "FLOAT", "0.0")
    attribut(g, "rappel_courant", "FLOAT", "0.0")
    attribut(g, "taux_fp_courant", "FLOAT", "0.0")

    # -- ressources chargées ----------------------------------------------
    attribut(g, "fichier_foret", "FILE",
             "csv_file('generated/foret_table.csv', ',', true)")
    attribut(g, "table_foret", "MATRIX", "matrix(fichier_foret)")
    attribut(g, "racines_foret", "LIST", "[]", typeElement="INT",
             commentaire="Rempli à l'init par le générateur — un indice par arbre.")
    attribut(g, "fichier_donnees", "FILE",
             "csv_file('data/KDDTest+.txt', ',', false)")
    # csv_file = matrice [colonne, ligne] ; row_at pour obtenir une connexion.
    attribut(g, "donnees_nslkdd", "MATRIX", "matrix(fichier_donnees)")
    attribut(g, "shape", "GEOMETRY", "rectangle(100, 80)")

    a_lire = el(g, "actions", nom="lire_connexion", typeRetour="LIST")
    el(a_lire, "parametres", nom="idc", type="INT")
    retour(a_lire, "list(donnees_nslkdd row_at idc)")

    # -- initialisation ----------------------------------------------------
    # La zone protégée « init_racines_foret » a été supprimée à l'Étape 6.
    # Elle demandait au développeur de recopier une valeur que le générateur
    # connaît déjà : une zone protégée dont le contenu est dérivable d'un
    # artefact existant est une invitation à l'erreur de recopie, pas une
    # frontière de conception.
    aff(g, "racines_foret", "RACINES_FORET", balise="initialisation",
        commentaire="Généré dans generated/encodage.gaml depuis le transpileur.")
    for nom, pim in ESPECES:
        el(g, "initialisation", "Creation", espece="#" + nom, nombre="1")
    el(g, "initialisation", "Ecriture",
       expression="'IDS-SMA initialisé — ' + string(NB_FEATURES) + ' variables, '"
                  " + string(NB_CLASSES) + ' classes, ' + string(donnees_nslkdd.rows)"
                  " + ' connexions x ' + string(donnees_nslkdd.columns) + ' champs'")
    return g


# ==========================================================================
# LES SEPT AGENTS
# ==========================================================================
ESPECES = [
    ("AgentCapture", "AgentReactif::AgentCapture"),
    ("AgentExtraction", "AgentReactif::AgentExtraction"),
    ("AgentReglesDetection", "AgentReactif::AgentReglesDetection"),
    ("AgentIADetection", "AgentBaseModele::AgentIADetection"),
    ("AgentDecision", "AgentBaseButs::AgentDecision"),
    ("AgentAlertes", "AgentReactif::AgentAlertes"),
    ("AgentJournalisation", "AgentReactif::AgentJournalisation"),
]


def agent_capture(racine):
    s = espece(racine, "AgentCapture", "AgentReactif::AgentCapture")
    attribut(s, "identifiant", "STRING", "'capture'")
    attribut(s, "position", "INT", "0")
    attribut(s, "nb_lues", "INT", "0")

    r = el(s, "reflexes", nom="lire_flux", boiteLue="AUCUNE", ordre="1",
           condition="position < donnees_nslkdd.rows")
    b = boucle(r, variable="i", collection="range(0, debit_capture - 1)")
    si_ = si(b, "position < donnees_nslkdd.rows")
    aff(si_, "idc", "position", declaration="INT", balise="alors",
        commentaire="L'identifiant de connexion EST l'indice de la ligne dans "
                    "le fichier, capturé AVANT incrémentation. La version "
                    "initiale émettait nb_lues, incrémenté juste avant : "
                    "l'AgentJournalisation aurait relu la ligne suivante pour "
                    "récupérer l'étiquette réelle, décalant toute la matrice "
                    "de confusion d'un rang sans produire la moindre erreur.")
    aff(si_, "position", "position + 1", balise="alors")
    aff(si_, "nb_lues", "nb_lues + 1", balise="alors")
    # FIPA aplatit les listes imbriquées dans contents : seul l'idc traverse
    # le bus ; l'Extraction relit via world.lire_connexion (row_at).
    fipa(si_, "START_CONVERSATION", "REQUEST",
         "['P1', idc]", "P1",
         destinataires="list(AgentExtraction)", balise="alors")

    r2 = el(s, "reflexes", nom="traiter_echecs", boiteLue="FAILURES", ordre="2",
            condition="!empty(failures)")
    b2 = boucle(r2, variable="m", collection="copy(failures)")
    aff(b2, "c", "list(m.contents)", declaration="LIST",
        commentaire="C7 : contents lu une seule fois.")
    ecrire(b2, "'[capture] echec de pretraitement : ' + string(c)")
    fipa(b2, "END_CONVERSATION", "INFORM", "['fin']", "P1", message="m")

    # Clôture P1 : Extraction répond par inform ; sans end_conversation les
    # conversations s'accumulent (fuite sur 22 544 connexions).
    r3 = el(s, "reflexes", nom="cloturer_p1", boiteLue="INFORMS", ordre="3",
            condition="!empty(informs)")
    b3 = boucle(r3, variable="m", collection="copy(informs)")
    aff(b3, "c", "list(m.contents)", declaration="LIST")
    fipa(b3, "END_CONVERSATION", "INFORM", "['fin']", "P1", message="m")
    return s


def agent_extraction(racine):
    s = espece(racine, "AgentExtraction", "AgentReactif::AgentExtraction")
    attribut(s, "identifiant", "STRING", "'extraction'")
    attribut(s, "vocabulaires", "MAP", "map([])",
             commentaire="ADR-02 : modalités connues par variable catégorielle, "
                         "issues du train. Une modalité inconnue au test produit "
                         "un vecteur nul sur son bloc one-hot.")
    attribut(s, "bornes_min", "LIST", "[]", typeElement="FLOAT")
    attribut(s, "bornes_max", "LIST", "[]", typeElement="FLOAT")
    attribut(s, "nb_traitees", "INT", "0")
    attribut(s, "nb_modalites_inconnues", "INT", "0")

    # La zone protégée « encodage_one_hot » a été supprimée à l'Étape 6.
    # L'encodage est une DONNÉE issue de l'apprentissage (vocabulaires et
    # bornes établis sur le train), pas une décision de conception. Le saisir
    # à la main ferait courir un risque de divergence silencieuse entre ce que
    # la forêt a appris et ce que la simulation lui présente. L'action est
    # donc générée dans generated/encodage.gaml et vérifiée sur données
    # réelles par verifier_encodage.py.
    r = el(s, "reflexes", nom="traiter_requetes", boiteLue="REQUESTS", ordre="1",
           condition="!empty(requests)")
    b = boucle(r, variable="m", collection="copy(requests)")
    aff(b, "c", "list(m.contents)", declaration="LIST",
        commentaire="C7 : lecture unique.")
    aff(b, "idc", "int(c[1])", declaration="INT")
    appel(b, "world.lire_connexion", resultat="brut", type_resultat="LIST",
          idc="idc")
    # GAMA 2025+ : actions du global importé → préfixe world. (discussion #821)
    appel(b, "world.encoder_connexion", resultat="v", type_resultat="LIST",
          type_element="FLOAT", brut="brut")
    aff(b, "nb_traitees", "nb_traitees + 1")
    # Vecteur dans une map : une list<float> nue dans contents est aplatie par FIPA.
    fipa(b, "REPLY", "INFORM", "['P1', idc, ['v'::v]]", "P1", message="m")
    fipa(b, "START_CONVERSATION", "INFORM", "['P2', idc, ['v'::v]]", "P2",
         destinataires="list(AgentDecision)")
    return s


def agent_regles(racine):
    s = espece(racine, "AgentReglesDetection",
               "AgentReactif::AgentReglesDetection")
    attribut(s, "identifiant", "STRING", "'regles'")
    attribut(s, "nb_regles", "INT", "11")
    attribut(s, "nb_declenchements", "INT", "0")
    attribut(s, "nb_abstentions", "INT", "0")

    a = el(s, "actions", nom="evaluer_signatures", typeRetour="LIST",
           typeElement="FLOAT")
    el(a, "parametres", nom="v", type="LIST", typeElement="FLOAT")
    aff(a, "p", "list_with(NB_CLASSES, 1.0 / NB_CLASSES)", declaration="LIST",
        type_element="FLOAT",
        commentaire="PIM §3.1 — ABSTENTION par défaut : distribution uniforme, "
                    "entropie maximale. Surtout PAS 'NORMAL avec confiance 1'. "
                    "Cette erreur a coûté 5 points de rappel à l'Étape 3.")
    aff(a, "declenchee", "false", declaration="BOOL")
    zone(a, "signatures_rm1_rm11",
         "Évaluer les 11 signatures RM1 à RM11 du CIM §5.2 sur le vecteur v. "
         "Si une signature se déclenche : declenchee <- true, p[classe] <- confiance, "
         "et p[k] <- (1 - confiance) / (NB_CLASSES - 1) pour les autres. "
         "Si aucune ne se déclenche, LAISSER p uniforme — ne rien affirmer. "
         "Confiances = précisions mesurées sur KDDTrain+ (pas sur le test).")
    si_ = si(a, "declenchee")
    aff(si_, "nb_declenchements", "nb_declenchements + 1", balise="alors")
    aff(si_, "nb_abstentions", "nb_abstentions + 1", balise="sinon")
    retour(a, "p")

    r = el(s, "reflexes", nom="repondre_consultations", boiteLue="QUERIES",
           ordre="1", condition="!empty(queries)")
    b = boucle(r, variable="m", collection="copy(queries)")
    aff(b, "c", "list(m.contents)", declaration="LIST")
    aff(b, "idc", "int(c[1])", declaration="INT")
    appel(b, "evaluer_signatures", resultat="p", type_resultat="LIST",
          type_element="FLOAT", v="list<float>(map(c[2])['v'])")
    aff(b, "nature", "(sum(p) - NB_CLASSES * min(p)) < 1e-9 ? 'ABSTENTION' : 'DETECTION'",
        declaration="STRING",
        commentaire="Distribution uniforme <=> abstention. Test par l'écart "
                    "au minimum plutôt que par un drapeau : la propriété est "
                    "portée par la distribution, pas par une variable annexe.")
    # P3 plat : FIPA aplatirait une list<float> imbriquée dans une map.
    fipa(b, "REPLY", "INFORM",
         "['P3', idc, 'regles', nature, p[0], p[1], p[2], p[3], p[4]]",
         "P3", message="m")
    return s


def agent_ia(racine):
    s = espece(racine, "AgentIADetection", "AgentBaseModele::AgentIADetection")
    attribut(s, "identifiant", "STRING", "'ia'")
    attribut(s, "nb_predictions", "INT", "0")
    attribut(s, "nb_refus_panne", "INT", "0")

    # T-2 : la variable d'état de la FSM EST sigma.
    # Les références inter-objets sont sérialisées par nom (#NOM) plutôt que
    # par chemin XMI (//@especes.3/@etats.1). Les deux formes sont résolues par
    # le vérificateur ; la forme par nom est retenue parce qu'un chemin indexé
    # devient faux dès qu'un élément est inséré en amont, ce qui rend toute
    # relecture du modèle dangereuse.
    a = el(s, "actions", nom="predire", typeRetour="LIST", typeElement="FLOAT")
    el(a, "parametres", nom="v", type="LIST", typeElement="FLOAT")
    aff(a, "acc", "list_with(NB_CLASSES, 0.0)", declaration="LIST",
        type_element="FLOAT")
    el(a, "corps", "ParcoursClassifieur", ressource="#foretNSLKDD",
       vecteurEntree="v", distributionSortie="acc",
       commentaire="ADR-03 bis — remplacé à la génération par un parcours de "
                   "table (TABLE) ou une cascade if/else (INLINE).")
    retour(a, "acc")

    # Étape 6 — la lecture des consultations passe des réflexes aux ÉTATS.
    #
    # Motif : la cohabitation d'un `reflex` et de `control: fsm` n'est pas
    # documentée pour 2025-06. Placer la lecture dans le corps des états lève
    # ce doute et améliore le modèle : le comportement en panne n'est plus un
    # `if (state = 'EN_PANNE')` dans un réflexe unique, il EST l'état. La
    # machine à états devient la structure de contrôle plutôt qu'une variable
    # consultée.
    e1 = el(s, "etats", identifiable=True, nom="ACTIF", estInitial="true",
            boiteLue="QUERIES")
    b1 = boucle(e1, variable="m", collection="copy(queries)")
    aff(b1, "c", "list(m.contents)", declaration="LIST")
    aff(b1, "idc", "int(c[1])", declaration="INT")
    appel(b1, "predire", resultat="p", type_resultat="LIST",
          type_element="FLOAT", v="list<float>(map(c[2])['v'])")
    aff(b1, "nb_predictions", "nb_predictions + 1")
    fipa(b1, "REPLY", "INFORM",
         "['P3', idc, 'ia', 'DETECTION', p[0], p[1], p[2], p[3], p[4]]",
         "P3", message="m")
    el(e1, "transitions", cible="#EN_PANNE", condition="flip(taux_panne)",
       evenementPim="e11_panne")

    e2 = el(s, "etats", identifiable=True, nom="EN_PANNE", boiteLue="QUERIES")
    ecrire(e2, "'[ia] panne au cycle ' + string(cycle)", balise="corpsEntree")
    b2 = boucle(e2, variable="m", collection="copy(queries)")
    aff(b2, "c", "list(m.contents)", declaration="LIST",
        commentaire="EF10 : même en panne, l'agent consomme ses messages et "
                    "REFUSE explicitement. Un agent muet laisserait "
                    "l'AgentDecision attendre son délai de garde à chaque "
                    "consultation — la panne coûterait tau cycles au lieu d'un.")
    aff(b2, "idc", "int(c[1])", declaration="INT")
    aff(b2, "nb_refus_panne", "nb_refus_panne + 1")
    fipa(b2, "REPLY", "REFUSE", "['P3', idc, 'agent en panne']", "P3",
         message="m")
    el(e2, "transitions", cible="#ACTIF", condition="flip(taux_reprise)",
       evenementPim="e12_reprise")
    return s


def agent_decision(racine):
    s = espece(racine, "AgentDecision", "AgentBaseButs::AgentDecision")
    attribut(s, "identifiant", "STRING", "'decision'")
    attribut(s, "etatDecision", "STRING", "'INACTIF'",
             commentaire="T-5 : machine à états du PIM réifiée en attribut. "
                         "GAMA n'admet qu'une valeur pour control:, et "
                         "weighted_tasks porte la sémantique d'agent à base de buts.")
    attribut(s, "verdictsRecus", "LIST", "[]", typeElement="MAP")
    attribut(s, "connexionCourante", "INT", "-1")
    attribut(s, "vecteurCourant", "LIST", "[]", typeElement="FLOAT")
    attribut(s, "cycleDebutConsultation", "INT", "-1")
    attribut(s, "decisionCourante", "MAP", "map([])")
    attribut(s, "nb_refus_recus", "INT", "0")

    # C1 : UN SEUL reflex sur informs, alors que P2 et P3 y aboutissent
    r = el(s, "reflexes", nom="recevoir_informs", boiteLue="INFORMS", ordre="1",
           condition="!empty(informs)")
    b = boucle(r, variable="m", collection="copy(informs)")
    aff(b, "c", "list(m.contents)", declaration="LIST",
        commentaire="C7 : contents lu une seule fois, puis stocké.")
    aff(b, "contrat", "string(c[0])", declaration="STRING",
        commentaire="T-11 : discriminateur de contrat en tête. P2 et les "
                    "réponses à P3 arrivent sur le même performatif INFORM, "
                    "donc dans la même file, que C1 interdit de lire deux fois.")
    c2 = si(b, "contrat = 'P2'")
    aff(c2, "connexionCourante", "int(c[1])", balise="alors")
    aff(c2, "vecteurCourant", "list<float>(map(c[2])['v'])", balise="alors")
    aff(c2, "verdictsRecus", "[]", balise="alors")
    aff(c2, "cycleDebutConsultation", "cycle", balise="alors")
    aff(c2, "nb_refus_recus", "0", balise="alors")
    aff(c2, "etatDecision", "'CONSULTATION'", balise="alors")
    fipa(c2, "END_CONVERSATION", "INFORM", "['fin']", "P2", message="m",
         balise="alors")
    c3 = si(c2, "contrat = 'P3'", balise="sinon")
    # Reconstruction du verdict depuis le format plat P3.
    aff(c3, "verdict",
        "['emetteur'::string(c[2]), 'nature'::string(c[3]), "
        "'distribution'::[float(c[4]), float(c[5]), float(c[6]), "
        "float(c[7]), float(c[8])]]",
        declaration="MAP", balise="alors")
    aff(c3, "verdictsRecus", "verdictsRecus + [verdict]", balise="alors")
    fipa(c3, "END_CONVERSATION", "INFORM", "['fin']", "P3", message="m",
         balise="alors")

    # Étape 6 — les REFUS doivent être lus, sinon la panne coûte tau cycles.
    # L'AgentIADetection répond REFUSE quand il est en panne (EF10). Sans ce
    # comportement, ce refus resterait dans la file `refuses` sans être
    # consommé et l'AgentDecision attendrait l'expiration de son délai de
    # garde à chaque consultation. Le mode dégradé s'enclenche ici, dès le
    # refus reçu, et non tau cycles plus tard.
    r2 = el(s, "reflexes", nom="recevoir_refus", boiteLue="REFUSES", ordre="2",
            condition="!empty(refuses)")
    b2 = boucle(r2, variable="m", collection="copy(refuses)")
    aff(b2, "c", "list(m.contents)", declaration="LIST")
    aff(b2, "nb_refus_recus", "nb_refus_recus + 1")
    fipa(b2, "END_CONVERSATION", "INFORM", "['fin']", "P3", message="m")

    a = el(s, "actions", nom="utilite", typeRetour="LIST", typeElement="FLOAT")
    el(a, "parametres", nom="degrade", type="BOOL")
    aff(a, "u", "list_with(NB_CLASSES, 0.0)", declaration="LIST",
        type_element="FLOAT",
        commentaire="Déclaré HORS de la zone protégée : `return u` se trouve "
                    "lui aussi hors de la zone, et une variable déclarée dans "
                    "la zone n'y serait pas visible.")
    zone(a, "calcul_utilite",
         "Calculer U(k) pour chaque classe k. Mode nominal : "
         "U(k) = poids_ia * c_IA(k) + (1 - poids_ia) * c_R(k) "
         "- lambda_fp * (k != 0 ? 1 : 0) * (1 - niveau_menace). "
         "Mode dégradé : U(k) = c_dispo(k) - lambda_fp * (...) — la confiance de la "
         "source survivante est utilisée TELLE QUELLE, sans division par deux, "
         "sinon le système sous-alerte au moment où il est affaibli. "
         "Retourner la liste des 5 utilités.")
    retour(a, "u")

    # T-5 : les états conditionnent les poids ; sentinelle obligatoire
    T = [
        ("attendre", "0.1", "-",
         "Sentinelle. weighted_tasks exécute la tâche de poids maximal à CHAQUE "
         "pas, y compris quand tous les poids valent 0 — le choix est alors "
         "arbitraire. Sans corps vide de poids minimal, un agent au repos "
         "exécuterait une tâche métier au hasard, sans erreur ni exception."),
        ("consulter", "(etatDecision = 'CONSULTATION' and empty(verdictsRecus) "
                      "and cycle = cycleDebutConsultation) ? 100.0 : 0.0", "G1", None),
        ("fusionner", "(etatDecision = 'CONSULTATION' and length(verdictsRecus) = 2) "
                      "? 90.0 : 0.0", "G2", None),
        ("emettre", "(etatDecision = 'EMISSION') ? 95.0 : 0.0", "G1", None),
        ("fusionner_degrade",
         "(etatDecision = 'CONSULTATION' and length(verdictsRecus) = 1 "
         "and (nb_refus_recus > 0 or cycle - cycleDebutConsultation > delai_garde))"
         " ? 80.0 : 0.0", "G4", None),
        ("abandonner",
         "(etatDecision = 'CONSULTATION' and empty(verdictsRecus) "
         "and cycle - cycleDebutConsultation > delai_garde) ? 70.0 : 0.0", "G3", None),
    ]
    taches = {}
    for nom, poids, but, comm in T:
        t = el(s, "taches", nom=nom, expressionPoids=poids, butPim=but)
        taches[nom] = t
        if comm:
            ecrire(t, "nil", commentaire=comm)

    fipa(taches["consulter"], "START_CONVERSATION", "QUERY",
         "['P3', connexionCourante, ['v'::vecteurCourant]]", "P3",
         destinataires="list(AgentIADetection) + list(AgentReglesDetection)")

    for nom, degrade in (("fusionner", "false"), ("fusionner_degrade", "true")):
        t = taches[nom]
        appel(t, "utilite", resultat="u", type_resultat="LIST",
              type_element="FLOAT", degrade=degrade)
        g = si(t, "(max(u) - min(u)) < 1e-6",
               commentaire="PIM §6 — deux abstentions produisent une distribution "
                           "uniforme, donc un argmax arbitraire. C'est un ABANDON, "
                           "pas une décision. Défaut invisible en test agrégé.")
        aff(g, "etatDecision", "'INACTIF'", balise="alors")
        aff(g, "nb_abandons", "nb_abandons + 1", balise="alors")
        aff(g, "decisionCourante",
            "['classe'::CLASSES[index_of(u, max(u))], 'confiance'::max(u), "
            "'degradee'::" + degrade + "]", balise="sinon")
        aff(g, "etatDecision", "'EMISSION'", balise="sinon")
        if degrade == "true":
            aff(g, "nb_degradees", "nb_degradees + 1", balise="sinon")

    ab = taches["abandonner"]
    aff(ab, "nb_abandons", "nb_abandons + 1")
    aff(ab, "etatDecision", "'INACTIF'")

    em = taches["emettre"]
    aff(em, "niveau_menace",
        "min(1.0, alpha_menace * niveau_menace + beta_menace * "
        "(decisionCourante['classe'] != 'NORMAL' ? 1.0 : 0.0))",
        commentaire="MC : mu(t+1) = min(1, alpha*mu(t) + beta*somme g(classe)).")
    aff(em, "nb_decisions", "nb_decisions + 1")
    aff(em, "classe_emise", "string(decisionCourante['classe'])",
        declaration="STRING",
        commentaire="Contenu plat uniquement : FIPA aplatit les maps imbriquées.")
    aff(em, "confiance_emise", "float(decisionCourante['confiance'])",
        declaration="FLOAT")
    fipa(em, "START_CONVERSATION", "INFORM",
         "['P4', connexionCourante, classe_emise, confiance_emise]", "P4",
         destinataires="list(AgentAlertes)")
    fipa(em, "START_CONVERSATION", "INFORM",
         "['P5', connexionCourante, classe_emise, confiance_emise]", "P5",
         destinataires="list(AgentJournalisation)")
    aff(em, "etatDecision", "'INACTIF'")
    return s


def agent_alertes(racine):
    s = espece(racine, "AgentAlertes", "AgentReactif::AgentAlertes")
    attribut(s, "identifiant", "STRING", "'alertes'")
    attribut(s, "nb_alertes", "INT", "0")

    r = el(s, "reflexes", nom="traiter_decisions", boiteLue="INFORMS", ordre="1",
           condition="!empty(informs)")
    b = boucle(r, variable="m", collection="copy(informs)")
    aff(b, "c", "list(m.contents)", declaration="LIST")
    # P4 plat : ['P4', idc, classe, confiance]
    aff(b, "classe", "string(c[2])", declaration="STRING")
    aff(b, "confiance", "float(c[3])", declaration="FLOAT")
    aff(b, "gravite", "confiance * (1.0 + niveau_menace) / 2.0",
        declaration="FLOAT")
    g = si(b, "classe != 'NORMAL' and gravite >= seuil_alerte")
    aff(g, "nb_alertes", "nb_alertes + 1", balise="alors")
    ecrire(g, "'[ALERTE] connexion ' + string(c[1]) + ' — ' + classe "
              "+ ' (gravite ' + string(gravite with_precision 3) + ')'",
           balise="alors")
    fipa(b, "END_CONVERSATION", "INFORM", "['fin']", "P4", message="m")
    return s


def agent_journal(racine):
    s = espece(racine, "AgentJournalisation",
               "AgentReactif::AgentJournalisation")
    attribut(s, "identifiant", "STRING", "'journal'")
    attribut(s, "nb_entrees", "INT", "0")

    r = el(s, "reflexes", nom="journaliser", boiteLue="INFORMS", ordre="1",
           condition="!empty(informs)")
    b = boucle(r, variable="m", collection="copy(informs)")
    aff(b, "c", "list(m.contents)", declaration="LIST")
    # P5 plat : ['P5', idc, classe, confiance]
    aff(b, "classe_pred", "string(c[2])", declaration="STRING")
    aff(b, "nb_entrees", "nb_entrees + 1")
    zone(b, "mise_a_jour_matrice_confusion",
         "ENF4 : cet agent est le SEUL à accéder à l'étiquette réelle. "
         "Récupérer la classe réelle de la connexion c[1] depuis le dataset, "
         "calculer i = 5 * index(classe_reelle) + index(classe_predite), "
         "puis matrice_confusion[i] <- matrice_confusion[i] + 1. "
         "Recalculer exactitude_courante, rappel_courant et taux_fp_courant.")
    fipa(b, "END_CONVERSATION", "INFORM", "['fin']", "P5", message="m")
    return s


# ==========================================================================
# EXPÉRIENCE
# ==========================================================================
def construire_experience(racine):
    x = el(racine, "experiences", nom="ids_gui", type="GUI", repetitions="1")

    d = el(x, "sorties", "Display", nom="metriques",
           rafraichissement="every(10#cycle)")
    c = el(d, "couches", "ChartLayer", nom="Performance en ligne",
           typeGraphe="SERIES")
    el(c, "series", nom="exactitude", expression="exactitude_courante",
       couleur="#1f77b4")
    el(c, "series", nom="rappel", expression="rappel_courant", couleur="#d62728")
    el(c, "series", nom="taux FP", expression="taux_fp_courant", couleur="#7f7f7f")

    d2 = el(x, "sorties", "Display", nom="menace_et_robustesse",
            rafraichissement="every(1#cycle)")
    c2 = el(d2, "couches", "ChartLayer", nom="Niveau de menace",
            typeGraphe="SERIES")
    el(c2, "series", nom="mu", expression="niveau_menace", couleur="#ff7f0e")
    c3 = el(d2, "couches", "ChartLayer", nom="Décisions par mode",
            typeGraphe="HISTOGRAM")
    el(c3, "series", nom="nominales",
       expression="nb_decisions - nb_degradees", couleur="#2ca02c")
    el(c3, "series", nom="dégradées", expression="nb_degradees", couleur="#ff7f0e")
    el(c3, "series", nom="abandons", expression="nb_abandons", couleur="#d62728")

    for nom, expr in [
        ("decisions", "nb_decisions"),
        ("degradees", "nb_degradees"),
        ("abandons", "nb_abandons"),
        ("alertes", "first(AgentAlertes).nb_alertes"),
        ("abstentions_regles", "first(AgentReglesDetection).nb_abstentions"),
        ("statut_ia", "first(AgentIADetection).state"),
        ("exactitude", "exactitude_courante"),
    ]:
        el(x, "sorties", "Monitor", nom=nom, expression=expr)
    return x


# ==========================================================================
def construire():
    ET.register_namespace("gamlpsm", NS_PSM)
    ET.register_namespace("xsi", NS_XSI)
    ET.register_namespace("xmi", NS_XMI)

    racine = ET.Element(f"{{{NS_PSM}}}GamlModel", {
        f"{{{NS_XMI}}}version": "2.0",
        "nom": "ids_sma",
        "auteur": "Projet IDS-SMA-IDM",
        "description": "IDS multi-agents sur NSL-KDD — modèle PSM complet, "
                       "produit par application des règles T-1 à T-11.",
    })

    el(racine, "imports", chemin="generated/encodage.gaml")
    el(racine, "imports", chemin="generated/foret_demo.gaml")

    construire_global(racine)
    agent_capture(racine)
    agent_extraction(racine)
    agent_regles(racine)
    agent_ia(racine)
    agent_decision(racine)
    agent_alertes(racine)
    agent_journal(racine)

    el(racine, "ressources", identifiable=True, nom="foretNSLKDD",
       cheminSource="../ml/artifacts/foret_export.json", strategieGeneration="TABLE",
       cheminTableGeneree="generated/foret_table.csv", nbArbres="20",
       profondeurMax="12", nbNoeuds="10232", nbCaracteristiques="122",
       nbClasses="5")
    el(racine, "ressources", identifiable=True, nom="foretDemo",
       cheminSource="../ml/artifacts/foret_export.json", strategieGeneration="INLINE",
       nbArbres="3", profondeurMax="4", nbNoeuds="45",
       nbCaracteristiques="122", nbClasses="5")

    construire_experience(racine)
    return racine


if __name__ == "__main__":
    racine = construire()
    ET.indent(racine, space="  ")
    arbre = ET.ElementTree(racine)
    arbre.write(SORTIE, encoding="utf-8", xml_declaration=True)

    n = sum(1 for _ in racine.iter())
    print("Instance PSM écrite :", os.path.relpath(SORTIE, RACINE))
    print("  éléments      :", n)
    print("  espèces       :", len(racine.findall("especes")))
    print("  ressources    :", len(racine.findall("ressources")))
    print("  taille        : %.1f Ko" % (os.path.getsize(SORTIE) / 1024))
