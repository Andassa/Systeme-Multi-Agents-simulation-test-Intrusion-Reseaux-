"""Chemins ML — artifacts + localisation des fichiers NSL-KDD."""
from __future__ import annotations

import os
from pathlib import Path

ML_DIR = Path(__file__).resolve().parent
ARTIFACTS = ML_DIR / "artifacts"
ROOT = ML_DIR.parent

ARTIFACTS.mkdir(exist_ok=True)

_DATA_CANDIDATES = (
    ROOT / "data",
    ROOT / "gama" / "models" / "data",
    Path.cwd(),
)


def artifact(name: str) -> Path:
    return ARTIFACTS / name


def find_nslkdd(name: str) -> Path:
    for base in _DATA_CANDIDATES:
        p = base / name
        if p.exists():
            return p
    searched = "\n  ".join(str(b) for b in _DATA_CANDIDATES)
    raise FileNotFoundError(f"{name} introuvable.\n  {searched}")


def as_str(path: Path) -> str:
    """Compat code historique qui attend encore des str."""
    return os.fspath(path)
