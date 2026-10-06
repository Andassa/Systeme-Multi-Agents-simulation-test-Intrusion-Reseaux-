#!/usr/bin/env python3
"""
Garde-fou léger : fige le contrat de validation sans relancer GAMA.

    python tests/test_baseline.py

Échoue si la cible ML dérive ou si le modèle GAML perd un
invariant critique (file Decision, P3 plat, zones métier).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CIBLE_EXACT = 0.8102377572746629
CIBLE_RAPPEL = 0.7223564248422037
TOL = 1e-3


def ok(msg: str) -> None:
    print(f"  OK    {msg}")


def fail(msg: str) -> None:
    print(f"  ECHEC {msg}")
    raise SystemExit(1)


def test_fusion_cible() -> None:
    path = ROOT / "ml" / "artifacts" / "resultats_fusion.json"
    if not path.exists():
        fail(f"absent : {path.relative_to(ROOT)}")
    data = json.loads(path.read_text(encoding="utf-8"))
    exact = float(data["fusion"]["exactitude_5_classes"])
    rappel = float(data["fusion"]["rappel"])
    if abs(exact - CIBLE_EXACT) > TOL:
        fail(f"exactitude fusion={exact}, attendu ~{CIBLE_EXACT}")
    if abs(rappel - CIBLE_RAPPEL) > TOL:
        fail(f"rappel fusion={rappel}, hors tolérance")
    if float(data["meta"]["poids_ia"]) != 0.35:
        fail("meta.poids_ia doit être 0.35")
    ok(f"fusion exact={exact:.4f} rappel={rappel:.4f}")


def test_artefacts_gama() -> None:
    requis = [
        "gama/models/ids_sma.gaml",
        "gama/models/generated/foret_table.csv",
        "gama/models/generated/encodage.gaml",
        "gama/models/data/KDDTest+.txt",
    ]
    for rel in requis:
        if not (ROOT / rel).exists():
            fail(f"absent : {rel}")
    ok(f"{len(requis)} artefacts GAMA présents")


def test_modules_ml() -> None:
    ml = ROOT / "ml"
    for rel in (
        "constants.py",
        "data_paths.py",
        "metrics.py",
        "foret.py",
        "regles.py",
        "evaluer_fusion.py",
        "preprocessing.py",
        "export_foret.py",
    ):
        if not (ml / rel).exists():
            fail(f"module ml absent : {rel}")
    # Import sans numpy lourd : constants + paths seulement
    import importlib.util

    def load(name: str, path: Path):
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(mod)
        return mod

    cst = load("ml_constants", ml / "constants.py")
    if cst.CLASSES != ["NORMAL", "DOS", "PROBE", "R2L", "U2R"]:
        fail("CLASSES dérivées")
    if cst.label_to_class("neptune") != 1:
        fail("label_to_class(neptune)")
    paths = load("ml_paths", ml / "data_paths.py")
    if not paths.artifact("resultats_fusion.json").exists():
        fail("artifact resultats_fusion.json")
    ok("modules ml (constants, paths, fichiers)")


def test_invariants_gaml() -> None:
    main = (ROOT / "gama/models/ids_sma.gaml").read_text(encoding="utf-8")

    for jeton in (
        "file_idc",
        "requete_envoyee",
        "trancher",
        "@user-begin(calcul_utilite)",
        "@user-begin(mise_a_jour_matrice_confusion)",
        "@user-begin(signatures_rm1_rm11)",
        "service=telnet",
        "num_failed_logins",
        "poids_ia <- 0.35",
        "'P3', idc, 'regles'",
        "'P3', int(c[1]), 'ia'",
        "species AgentVue",
        "charge_decision",
        "enregistrer_prediction",
        'import "generated/encodage.gaml"',
    ):
        if jeton not in main:
            fail(f"invariant manquant : {jeton}")
    if 'import "species/' in main:
        fail("imports species/ interdits (monolithe requis sous GAMA 2025)")
    ok("invariants GAML (file, P3 plat, zones, monolithe)")


def main() -> int:
    print("tests/test_baseline — contrat de validation")
    print("-" * 60)
    test_fusion_cible()
    test_artefacts_gama()
    test_modules_ml()
    test_invariants_gaml()
    print("-" * 60)
    print("Baseline OK — exactitude cible ~0.810 préservée.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
