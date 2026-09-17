"""Regla de desacoplamiento: dominio y aplicación no conocen el framework; las vistas no tocan el ORM."""
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
                    if modulo.split(".")[0] in PROHIBIDOS:
                        violaciones.append(f"{archivo.relative_to(RAIZ)} importa {modulo}")
        self.assertEqual(violaciones, [])

    def test_las_vistas_no_tocan_el_orm_ni_la_biblioteca_directamente(self):
        texto = (RAIZ / "interfaces" / "views.py").read_text(encoding="utf-8")
        self.assertNotIn("from .. import models", texto)
        self.assertNotIn("from ..models", texto)
        self.assertNotIn(".objects.", texto)
        self.assertNotIn("cliente_biblioteca.curso(", texto)

    def test_el_esquema_es_solo_de_aula_sin_curso_ni_claves(self):
        """Regla de oro (artículo 14): ninguna tabla de curso, asignatura, lección, objeto, pregunta ni opción."""
        from django.apps import apps

        modelos = apps.get_app_config("classroom_engine").get_models()
        tablas = {m._meta.db_table for m in modelos}
        self.assertTrue(tablas, "la app classroom_engine debe tener tablas m07_*")
        for tabla in tablas:
            self.assertTrue(tabla.startswith("m07_"), tabla)
            for prohibida in ("curso", "asignatura", "leccion", "objeto", "lamina", "bloque", "medio", "pregunta", "opcion", "materia"):
                self.assertNotIn(prohibida, tabla, f"{tabla} parece una tabla de contenido")
        for modelo in modelos:
            for campo in modelo._meta.get_fields():
                for prohibida in ("clave", "correcta", "solucion"):
                    self.assertNotIn(prohibida, campo.name, f"{modelo.__name__}.{campo.name}")
