"""Regla de desacoplamiento: dominio y aplicación no conocen el framework."""
from __future__ import annotations

import re
from pathlib import Path

from django.test import SimpleTestCase

PROHIBIDOS = ("django", "rest_framework", "pydantic", "sqlalchemy", "fastapi")
RAIZ = Path(__file__).resolve().parent.parent


class ArquitecturaTests(SimpleTestCase):
    def test_dominio_y_aplicacion_no_importan_frameworks(self):
        patron = re.compile(r"^\s*(?:from|import)\s+([\w\.]+)", re.MULTILINE)
        violaciones = []
        for carpeta in ("dominio", "aplicacion"):
            for archivo in (RAIZ / carpeta).rglob("*.py"):
                for modulo in patron.findall(archivo.read_text(encoding="utf-8")):
                    raiz = modulo.split(".")[0]
                    if raiz in PROHIBIDOS:
                        violaciones.append(f"{archivo.relative_to(RAIZ)} importa {modulo}")
        self.assertEqual(violaciones, [])

    def test_las_vistas_no_tocan_el_orm(self):
        texto = (RAIZ / "interfaces" / "views.py").read_text(encoding="utf-8")
        self.assertNotIn("from .. import models", texto)
        self.assertNotIn("from ..models", texto)
        self.assertNotIn(".objects.", texto)
