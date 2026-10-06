"""Chemins du dépôt — source unique pour les scripts Python."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent

DATA = ROOT / "data"
DESIGN = ROOT / "design"
PIM = ROOT / "pim"
PSM = ROOT / "psm"
GENERATOR = ROOT / "generator"
ML = ROOT / "ml"
ML_ARTIFACTS = ML / "artifacts"
GAMA = ROOT / "gama"
GAMA_MODELS = GAMA / "models"
GAMA_GENERATED = GAMA_MODELS / "generated"
GAMA_DATA = GAMA_MODELS / "data"
