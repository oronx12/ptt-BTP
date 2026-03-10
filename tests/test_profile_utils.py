# tests/test_profile_utils.py
"""Tests unitaires pour la logique géométrique de profile_utils."""
import sys
from pathlib import Path

# Ajouter le répertoire core au path pour l'import
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "core"))

from profile_utils import Z_surf, recalc_layers


PARAMS_BASE = {
    "Z0": 100.0,
    "s": 0.025,
    "s_acc": 0.032,
    "x_ch": 6.5,
    "X0": 0.0,
}


class TestZSurf:
    def test_axe_central(self):
        """Z à x=0 doit être Z0."""
        assert Z_surf(0, PARAMS_BASE) == PARAMS_BASE["Z0"]

    def test_pente_chaussee(self):
        """Avant x_ch, pente = s."""
        z3 = Z_surf(3.0, PARAMS_BASE)
        assert abs(z3 - (PARAMS_BASE["Z0"] - PARAMS_BASE["s"] * 3.0)) < 1e-9

    def test_pente_accotement(self):
        """Après x_ch, pente = s_acc."""
        x = 8.0
        z_ch = PARAMS_BASE["Z0"] - PARAMS_BASE["s"] * PARAMS_BASE["x_ch"]
        expected = z_ch - PARAMS_BASE["s_acc"] * (x - PARAMS_BASE["x_ch"])
        assert abs(Z_surf(x, PARAMS_BASE) - expected) < 1e-9

    def test_continuite_au_point_charniere(self):
        """Pas de discontinuité en x_ch."""
        x_ch = PARAMS_BASE["x_ch"]
        assert abs(Z_surf(x_ch, PARAMS_BASE) - Z_surf(x_ch + 1e-10, PARAMS_BASE)) < 1e-6


class TestRecalcLayers:
    def test_nb_layers(self):
        """Nombre de records = nombre de layers."""
        layers = [{"name": "Roulement", "t": 0.06}, {"name": "Base", "t": 0.20}]
        recs = recalc_layers(PARAMS_BASE, layers)
        assert len(recs) == 2

    def test_epaisseur(self):
        """L'épaisseur stockée doit correspondre à 't'."""
        layers = [{"name": "Roulement", "t": 0.06}]
        recs = recalc_layers(PARAMS_BASE, layers)
        assert recs[0]["thickness"] == 0.06

    def test_layers_vides(self):
        """Aucun layer → liste vide."""
        assert recalc_layers(PARAMS_BASE, []) == []
