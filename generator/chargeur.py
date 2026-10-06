#!/usr/bin/env python3
"""
Chargement du métamodèle et de l'instance PSM.

Deux implémentations, une seule interface
------------------------------------------
  BACKEND "pyecore" : chargement par PyEcore. C'est la voie de référence —
                      l'outil est celui qu'emploie la communauté EMF, et
                      c'est lui qui valide réellement la conformité.

  BACKEND "stdlib"  : chargement par xml.etree, sans dépendance.

Pourquoi les deux. Le repli n'est pas là par méfiance envers PyEcore mais
parce que la génération doit rester exécutable sur une machine où il n'est
pas installé — c'est le cas de l'environnement où ce projet a été développé.
Une chaîne IDM qui ne se régénère que sur le poste de son auteur n'est pas
reproductible, et la reproductibilité est une exigence du projet (ENF5).

Les deux backends produisent le MÊME graphe de Noeud. Le test
`comparer_backends()` le vérifie quand PyEcore est disponible : sans cette
comparaison, l'équivalence serait une affirmation.
"""
import os
import tempfile
import xml.etree.ElementTree as ET

from lxml import etree as lxml_etree

XSI_TYPE = "{http://www.w3.org/2001/XMLSchema-instance}type"

try:
    import pyecore.resources  # noqa: F401
    PYECORE_DISPONIBLE = True
except ImportError:
    PYECORE_DISPONIBLE = False


# ==========================================================================
class Noeud:
    """Élément de modèle, indépendant du backend."""

    __slots__ = ("classe", "attrs", "enfants")

    def __init__(self, classe):
        self.classe = classe
        self.attrs = {}
        self.enfants = {}          # feature -> [Noeud]

    def __getattr__(self, nom):
        if nom in self.attrs:
            return self.attrs[nom]
        if nom in self.enfants:
            return self.enfants[nom]
        return None

    def get(self, nom, defaut=None):
        return self.attrs.get(nom, defaut)

    def liste(self, feature):
        return self.enfants.get(feature, [])

    def __repr__(self):
        return f"<{self.classe} {self.attrs.get('nom', '')}>"


# ==========================================================================
class Metamodele:
    """
    Ce que le générateur a besoin de savoir du .ecore :
      - le type de chaque feature (pour distinguer containment et attribut)
      - la traduction des littéraux d'énumération vers la syntaxe GAML
        (GamlType.LIST -> 'list', ArchitectureKind.WEIGHTED_TASKS -> 'weighted_tasks')

    Cette dernière correspondance vient du métamodèle et non d'un dictionnaire
    codé dans le générateur : la syntaxe concrète est une propriété du PSM.
    """

    def __init__(self, chemin):
        racine = ET.parse(chemin).getroot()
        self.classes, self.enums, self.litteraux, parents = {}, {}, {}, {}
        for c in racine.findall("eClassifiers"):
            nom, kind = c.get("name"), c.get(XSI_TYPE)
            if kind == "ecore:EEnum":
                self.enums[nom] = [l.get("name") for l in c.findall("eLiterals")]
                for l in c.findall("eLiterals"):
                    self.litteraux[(nom, l.get("name"))] = \
                        l.get("literal", l.get("name"))
            elif kind == "ecore:EClass":
                self.classes[nom] = {f.get("name"): f
                                     for f in c.findall("eStructuralFeatures")}
                parents[nom] = [s[3:] for s in c.get("eSuperTypes", "").split()]

        def aplatir(n, vus=None):
            vus = vus or set()
            if n in vus or n not in self.classes:
                return {}
            vus.add(n)
            r = dict(self.classes[n])
            for p in parents.get(n, []):
                r.update(aplatir(p, vus))
            return r

        self.features = {n: aplatir(n) for n in self.classes}

    def type_feature(self, classe, feature):
        f = self.features.get(classe, {}).get(feature)
        return f.get("eType", "").replace("#//", "") if f is not None else None

    def est_containment(self, classe, feature):
        f = self.features.get(classe, {}).get(feature)
        return f is not None and f.get("containment") == "true"

    def gaml(self, enum, litteral):
        """Syntaxe concrète GAML d'un littéral d'énumération."""
        return self.litteraux.get((enum, litteral), litteral)

    def est_multiple(self, classe, feature):
        f = self.features.get(classe, {}).get(feature)
        return f is not None and f.get("upperBound") == "-1"

    def defaut(self, classe, feature):
        """
        Valeur par défaut DÉCLARÉE dans le .ecore, ou None.

        Point de sémantique qui a produit 105 écarts entre les deux backends.

        PyEcore matérialise une valeur pour toute feature non renseignée : la
        valeur déclarée s'il y en a une, sinon le PREMIER littéral pour un
        EEnum. Le chargeur stdlib, lui, ne voyait que ce qui figurait dans le
        XMI et renvoyait None.

        Ce n'était pas une divergence cosmétique. `Affectation.declaration` et
        `Attribute.typeElement` sont des GamlType sans valeur déclarée : côté
        PyEcore ils valaient donc 'int'. Générer avec ce backend aurait émis
        `int x <- ...` devant CHAQUE affectation et `list<int>` devant chaque
        liste — un GAML différent selon le lecteur du modèle, ce qui ruine la
        propriété que la chaîne revendique.

        Règle retenue, appliquée identiquement aux deux backends :
          - attribut présent dans le XMI            -> sa valeur
          - absent mais defaultValueLiteral déclaré -> cette valeur
          - absent sans valeur déclarée             -> None (non renseigné)

        Le premier littéral d'un EEnum n'est pas une valeur par défaut : c'est
        un accident d'ordre de déclaration.
        """
        f = self.features.get(classe, {}).get(feature)
        if f is None:
            return None
        d = f.get("defaultValueLiteral")
        if d is None:
            return None
        t = f.get("eType", "").replace("#//", "")
        return self.gaml(t, d) if t in self.enums else d

    def appliquer_defauts(self, noeud):
        """Complète un Noeud avec les valeurs par défaut déclarées."""
        for nom in self.features.get(noeud.classe, {}):
            if nom in noeud.attrs or nom in noeud.enfants:
                continue
            d = self.defaut(noeud.classe, nom)
            if d is not None:
                noeud.attrs[nom] = d
        return noeud


# ==========================================================================
# BACKEND stdlib
# ==========================================================================
def _charger_stdlib(chemin_xmi, mm):
    racine_xml = ET.parse(chemin_xmi).getroot()

    def construire(el, classe):
        n = Noeud(classe)
        for k, v in el.attrib.items():
            if k.startswith("{"):
                continue
            t = mm.type_feature(classe, k)
            if t in mm.enums:
                jetons = [mm.gaml(t, j) for j in v.split()]
                # Une feature à cardinalité multiple donne TOUJOURS une liste,
                # même à un seul élément. La version antérieure renvoyait un
                # scalaire dans ce cas et une liste au-delà, alors que PyEcore
                # renvoie toujours une liste : d'où l'écart « 'fipa' != ['fipa'] ».
                n.attrs[k] = jetons if mm.est_multiple(classe, k) else jetons[0]
            else:
                n.attrs[k] = v
        mm.appliquer_defauts(n)
        for enfant in el:
            tag = enfant.tag.split("}")[-1]
            t = enfant.get(XSI_TYPE)
            cible = t.split(":")[-1] if t else mm.type_feature(classe, tag)
            if cible is None:
                continue
            n.enfants.setdefault(tag, []).append(construire(enfant, cible))
        return n

    return construire(racine_xml, "GamlModel")


# ==========================================================================
# BACKEND pyecore
# ==========================================================================
def _nettoyer_xml_pour_pyecore(chemin):
    """Crée une copie temporaire du XML sans commentaires pour pyecore."""
    chemin_abs = os.path.abspath(chemin)
    parser = lxml_etree.XMLParser(remove_comments=True, resolve_entities=False)
    arbre = lxml_etree.parse(chemin_abs, parser=parser)
    # Le fichier temporaire est créé À CÔTÉ de la source : pyecore résout les
    # références (href, nsURI) relativement à l'emplacement du fichier. Le placer
    # dans os.getcwd() rendait la génération dépendante du répertoire courant.
    fd, chemin_temp = tempfile.mkstemp(suffix=".xml", prefix=".pyecore-clean-",
                                       dir=os.path.dirname(chemin_abs))
    os.close(fd)
    arbre.write(chemin_temp, encoding="utf-8", xml_declaration=True)
    return chemin_temp


def _charger_pyecore(chemin_xmi, chemin_ecore, mm):
    """
    Chargement par pyecore.

    Cette fonction LÈVE en cas d'échec ; le repli éventuel est décidé par
    charger(), qui le signale. Une version antérieure rattrapait l'exception
    ici et retournait silencieusement le graphe stdlib : `charger()` annonçait
    alors le backend « pyecore » tout en exécutant stdlib, et
    `comparer_backends()` comparait stdlib à lui-même — une comparaison qui
    passe toujours et ne prouve rien. Un repli doit être visible, sans quoi il
    transforme une vérification en formalité.
    """
    from pyecore.resources import ResourceSet, URI

    temporaires = []
    try:
        chemin_ecore_nettoye = _nettoyer_xml_pour_pyecore(chemin_ecore)
        chemin_xmi_nettoye = _nettoyer_xml_pour_pyecore(chemin_xmi)
        temporaires += [chemin_ecore_nettoye, chemin_xmi_nettoye]

        rset = ResourceSet()
        ressource_mm = rset.get_resource(URI(chemin_ecore_nettoye))
        paquet = ressource_mm.contents[0]
        rset.metamodel_registry[paquet.nsURI] = paquet
        ressource = rset.get_resource(URI(chemin_xmi_nettoye))
        racine_ec = ressource.contents[0]

        def construire(obj):
            classe = obj.eClass.name
            n = Noeud(classe)
            for f in obj.eClass.eAllStructuralFeatures():
                v = obj.eGet(f)
                if v is None:
                    continue
                # eIsSet distingue « renseigné dans le XMI » de « valeur par
                # défaut matérialisée par PyEcore ». Sans ce filtre, toute
                # feature absente remontait avec le premier littéral de son
                # énumération — 'int' pour un GamlType — et le générateur
                # produisait un GAML différent de celui du backend stdlib.
                # Les valeurs par défaut légitimes, celles que le .ecore
                # déclare, sont réappliquées ensuite par appliquer_defauts().
                try:
                    if not obj.eIsSet(f) and not getattr(f, "containment", False):
                        continue
                except Exception:
                    pass
                nom_t = f.eType.name if f.eType is not None else ""
                if getattr(f, "containment", False):
                    enfants = list(v) if f.many else [v]
                    n.enfants[f.name] = [construire(e) for e in enfants if e is not None]
                elif nom_t in mm.enums:
                    if f.many:
                        n.attrs[f.name] = [mm.gaml(nom_t, x.name) for x in v]
                    else:
                        n.attrs[f.name] = mm.gaml(nom_t, v.name)
                elif nom_t in mm.classes:
                    cible = list(v) if f.many else [v]
                    noms = [getattr(c, "nom", None) for c in cible if c is not None]
                    if noms:
                        n.attrs[f.name] = "#" + noms[0]
                elif isinstance(v, bool):
                    # PyEcore renvoie un booleen Python ; le XMI porte la
                    # chaine 'true' ou 'false'. Sans cette normalisation,
                    # estParametre et estInitial auraient diverge en 'True'
                    # contre 'true' — et les gabarits, qui comparent a la
                    # chaine minuscule, auraient silencieusement cesse
                    # d'emettre les parametres d'experience et l'etat initial
                    # de la machine a etats.
                    n.attrs[f.name] = "true" if v else "false"
                else:
                    if v != "":
                        n.attrs[f.name] = str(v)
            mm.appliquer_defauts(n)
            return n

        return construire(racine_ec)
    finally:
        # Les copies nettoyées sont supprimées dans tous les cas. Sans ce
        # bloc, chaque exécution laissait un fichier .pyecore-clean-*.xml
        # dans generator/ — douze s'y étaient accumulés.
        for t in temporaires:
            try:
                os.unlink(t)
            except OSError:
                pass


# ==========================================================================
def charger(chemin_ecore, chemin_xmi, backend="auto"):
    """
    Retourne (racine, mm, backend_effectif).

    backend : "auto" | "pyecore" | "stdlib"
    """
    mm = Metamodele(chemin_ecore)
    demande_explicite = backend == "pyecore"
    if backend == "auto":
        backend = "pyecore" if PYECORE_DISPONIBLE else "stdlib"
    if backend == "pyecore":
        if not PYECORE_DISPONIBLE:
            raise RuntimeError("PyEcore n'est pas installé (pip install pyecore).")
        try:
            return _charger_pyecore(chemin_xmi, chemin_ecore, mm), mm, "pyecore"
        except Exception as e:
            if demande_explicite:
                # Aucun repli quand PyEcore a été demandé nommément. Un repli
                # silencieux transformerait la commande de vérification en
                # formalité : elle afficherait « génération réussie » sans
                # avoir rien vérifié de ce qu'on lui demandait de vérifier.
                raise RuntimeError(
                    f"PyEcore a échoué : {type(e).__name__}: {e}\n"
                    "  Le backend a été demandé explicitement : aucun repli.\n"
                    "  Diagnostic : lancer\n"
                    "      python ../psm/verifier_contraintes.py "
                    "../psm/psm-ids-complet.xmi ../psm/gaml-psm.ecore\n"
                    "  Une erreur V12 signale une référence '#X' dont la cible "
                    "ne porte pas de xmi:id.") from e
            # En mode auto, le repli est acceptable mais bruyant, et le nom du
            # backend retourné dit la vérité.
            print(f"    AVERTISSEMENT — PyEcore a échoué : "
                  f"{type(e).__name__}: {e}")
            print("    Repli sur le backend stdlib. Le graphe est le même, "
                  "mais la conformité EMF n'est PAS vérifiée.")
            return (_charger_stdlib(chemin_xmi, mm), mm,
                    "stdlib (repli après échec pyecore)")
    return _charger_stdlib(chemin_xmi, mm), mm, "stdlib"


def comparer_backends(chemin_ecore, chemin_xmi):
    """
    Vérifie que les deux backends produisent le même graphe.

    Exécuté par generer.py --verifier quand PyEcore est disponible. Sans ce
    contrôle, l'équivalence annoncée dans l'en-tête de ce module ne serait
    qu'une intention.
    """
    if not PYECORE_DISPONIBLE:
        return None
    a, _, _ = charger(chemin_ecore, chemin_xmi, "stdlib")
    b, _, _ = charger(chemin_ecore, chemin_xmi, "pyecore")

    ecarts = []

    def cmp(x, y, chemin):
        if x.classe != y.classe:
            ecarts.append(f"{chemin} : classe {x.classe} != {y.classe}")
            return
        for k in set(x.attrs) | set(y.attrs):
            vx, vy = x.attrs.get(k), y.attrs.get(k)
            if str(vx) != str(vy):
                ecarts.append(f"{chemin}.{k} : {vx!r} != {vy!r}")
        for f in set(x.enfants) | set(y.enfants):
            lx, ly = x.liste(f), y.liste(f)
            if len(lx) != len(ly):
                ecarts.append(f"{chemin}/{f} : {len(lx)} != {len(ly)} enfants")
                continue
            for i, (ex, ey) in enumerate(zip(lx, ly)):
                cmp(ex, ey, f"{chemin}/{f}[{i}]")

    cmp(a, b, "GamlModel")
    return ecarts


if __name__ == "__main__":
    ICI = os.path.dirname(os.path.abspath(__file__))
    RACINE = os.path.dirname(ICI)
    ec = os.path.join(RACINE, "psm", "gaml-psm.ecore")
    xm = os.path.join(RACINE, "psm", "psm-ids-complet.xmi")

    racine, mm, backend = charger(ec, xm)
    n = [0]

    def compter(x):
        n[0] += 1
        for L in x.enfants.values():
            for e in L:
                compter(e)

    compter(racine)
    print("backend         :", backend,
          "" if PYECORE_DISPONIBLE else "(PyEcore absent de cet environnement)")
    print("modèle          :", racine.get("nom"))
    print("éléments chargés:", n[0])
    print("espèces         :", [s.get("nom") for s in racine.liste("especes")])

    ecarts = comparer_backends(ec, xm)
    if ecarts is None:
        print("comparaison des backends : impossible ici, PyEcore absent")
    elif ecarts:
        print("ECARTS entre backends :", len(ecarts))
        for e in ecarts[:10]:
            print("   ", e)
    else:
        print("comparaison des backends : graphes identiques")
