"""
Pruebas del cliente único y de las rutas hacia arriba, contra el host de pruebas.

No necesitan la biblioteca real: el host escribe su propia nota de enlace y el
backend la encuentra por AVACOM_CONTENIDO_ENLACE.
"""
from __future__ import annotations

import os
import tempfile

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from tools.host_biblioteca_pruebas import HostBibliotecaPruebas

from . import cliente


class ConHostDePruebas(TestCase):
    capacidades: list[str] | None = None

    def setUp(self):
        self.carpeta = tempfile.mkdtemp(prefix="avacom-lms-")
        self.ruta_enlace = os.path.join(self.carpeta, "enlace.json")
        self.host = HostBibliotecaPruebas(self.ruta_enlace, capacidades=self.capacidades).iniciar()
        self._ajuste = override_settings(AVACOM_CONTENIDO_ENLACE=self.ruta_enlace)
        self._ajuste.enable()
        self.api = APIClient()

    def tearDown(self):
        self._ajuste.disable()
        self.host.detener()


class DescubrimientoTests(ConHostDePruebas):
    def test_la_nota_se_lee_en_cada_llamada_y_acepta_ambas_convenciones(self):
        nota = cliente.leer_enlace()
        self.assertEqual(nota["puerto"], self.host.puerto)
        # minúsculas también valen
        with open(self.ruta_enlace, "w", encoding="utf-8") as f:
            f.write('{"contrato":1,"puerto":%d,"ficha":"%s","proceso":%d}' % (self.host.puerto, self.host.ficha, os.getpid()))
        self.assertEqual(cliente.leer_enlace()["ficha"], self.host.ficha)

    def test_sin_nota_es_un_estado_normal_503(self):
        self.host.borrar_enlace()
        r = self.api.get("/api/biblioteca/cursos/")
        self.assertEqual(r.status_code, 503)
        self.assertFalse(r.json()["disponible"])
        self.assertIn("sugerencia", r.json())
        estado = cliente.estado()
        self.assertFalse(estado["disponible"])
        self.assertTrue(estado["motivo"])

    def test_contrato_mayor_pide_actualizar_el_lms(self):
        self.host.escribir_enlace(contrato=cliente.CONTRATO_SOPORTADO + 1)
        r = self.api.get("/api/biblioteca/estado/")
        self.assertFalse(r.json()["disponible"])
        self.assertIn("actualizar", r.json()["motivo"])

    def test_puerto_muerto_es_no_disponible(self):
        puerto = self.host.puerto
        self.host.detener()
        with open(self.ruta_enlace, "w", encoding="utf-8") as f:
            f.write('{"Contrato":1,"Puerto":%d,"Ficha":"abc","Proceso":1}' % puerto)
        r = self.api.get("/api/biblioteca/cursos/")
        self.assertEqual(r.status_code, 503)

    def test_estado_nunca_lanza_y_trae_huella_y_capacidades(self):
        estado = cliente.estado()
        self.assertTrue(estado["disponible"])
        self.assertTrue(estado["huella_catalogo"].startswith("h"))
        self.assertIn("curso", estado["capacidades"])
        self.assertEqual(estado["conteos"]["cursos"], 2)
        self.assertIn(estado["proceso_vivo"], (True, None))

    def test_health_incluye_el_estado_de_la_biblioteca(self):
        r = self.api.get("/health/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["status"], "ok")
        self.assertFalse(r.json()["administra_cursos"])
        self.assertTrue(r.json()["biblioteca"]["disponible"])


class CursosTests(ConHostDePruebas):
    def test_los_cursos_son_los_de_la_biblioteca(self):
        r = self.api.get("/api/biblioteca/cursos/")
        self.assertEqual(r.status_code, 200)
        refs = [c["curso_ref"] for c in r.json()["cursos"]]
        self.assertEqual(refs, ["co-secundaria-8-matematicas", "co-preescolar-transicion-exploracion"])
        self.assertTrue(all(c["disponible"] for c in r.json()["cursos"]))

    def test_el_curso_trae_secciones_e_items_anotados(self):
        r = self.api.get("/api/biblioteca/cursos/co-secundaria-8-matematicas/?persona=ethan")
        self.assertEqual(r.status_code, 200)
        datos = r.json()
        self.assertEqual(len(datos["secciones"]), 3)
        item = datos["secciones"][0]["items"][0]
        for campo in ("orden", "tipo", "elemento_ref", "titulo", "version", "abierto", "completado", "visible"):
            self.assertIn(campo, item)
        self.assertFalse(item["abierto"])
        self.assertEqual(datos["progreso"], 0.0)
        self.assertIn("medio", datos["capacidades"])

    def test_curso_inexistente_404(self):
        self.assertEqual(self.api.get("/api/biblioteca/cursos/no-existe/").status_code, 404)

    def test_mostrar_proyecta_en_el_aula(self):
        r = self.api.post("/api/biblioteca/mostrar/", {"elemento_ref": "co-sec-mat-doc-funcion"}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self.host.mostrados, ["co-sec-mat-doc-funcion"])
        r = self.api.post("/api/biblioteca/mostrar/", {"elemento_ref": "no-existe"}, format="json")
        self.assertEqual(r.status_code, 409)
        self.assertIn("motivo", r.json())


class MedioTests(ConHostDePruebas):
    def test_el_medio_se_reenvia_con_tipo_y_rango(self):
        r = self.api.get("/api/biblioteca/medio/co-pre-exp-img-granja/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r["Content-Type"], "image/png")
        self.assertEqual(b"".join(r.streaming_content)[:8], b"\x89PNG\r\n\x1a\n")

        r = self.api.get("/api/biblioteca/medio/co-sec-mat-video-pendiente/", HTTP_RANGE="bytes=0-9")
        self.assertEqual(r.status_code, 206)
        self.assertEqual(r["Content-Range"], "bytes 0-9/102400")
        self.assertEqual(len(b"".join(r.streaming_content)), 10)

    def test_el_interactivo_sirve_sus_archivos_internos(self):
        r = self.api.get("/api/biblioteca/medio/co-sec-mat-int-grafica/index.html")
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"Explorador", b"".join(r.streaming_content))
        r = self.api.get("/api/biblioteca/medio/co-sec-mat-int-grafica/app.js")
        self.assertEqual(r.status_code, 200)

    def test_leccion_y_evaluacion(self):
        r = self.api.get("/api/biblioteca/leccion/co-sec-mat-lec-funcion/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.json()["pasos"]), 4)
        r = self.api.get("/api/biblioteca/evaluacion/co-sec-mat-eval-funcion/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.json()["preguntas"]), 3)

    def test_ninguna_respuesta_del_estudiante_trae_una_clave(self):
        r = self.api.get("/api/biblioteca/evaluacion/co-sec-mat-eval-funcion/")
        texto = r.content.decode("utf-8").lower()
        for prohibida in ("clave", "es_correcta", '"correcta"', '"respuesta"', "solucion"):
            self.assertNotIn(prohibida, texto)

    def test_sin_claves_limpia_recursivamente(self):
        datos = {"preguntas": [{"ref": "a", "clave": "x", "opciones": [{"texto": "b", "es_correcta": True}]}], "respuesta": "z"}
        limpio = cliente.sin_claves(datos)
        self.assertEqual(limpio, {"preguntas": [{"ref": "a", "opciones": [{"texto": "b"}]}]})


class SinCapacidadesTests(ConHostDePruebas):
    capacidades = ["curso"]

    def test_las_rutas_opcionales_responden_501_explicativo(self):
        for ruta in ("/api/biblioteca/medio/co-pre-exp-img-granja/", "/api/biblioteca/leccion/co-sec-mat-lec-funcion/",
                     "/api/biblioteca/evaluacion/co-sec-mat-eval-funcion/"):
            r = self.api.get(ruta)
            self.assertEqual(r.status_code, 501, ruta)
            self.assertEqual(r.json()["capacidades"], ["curso"])
        # el catálogo plano y los cursos siguen funcionando
        self.assertEqual(self.api.get("/api/biblioteca/cursos/").status_code, 200)


class ComponenteAntiguoTests(ConHostDePruebas):
    capacidades = []

    def test_sin_capacidad_curso_no_se_abre_ningun_curso_pero_el_catalogo_plano_sigue(self):
        self.assertEqual(self.api.get("/api/biblioteca/cursos/").status_code, 501)
        r = self.api.get("/api/biblioteca/catalogo/?tipo=video")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.json()["elementos"]), 1)
