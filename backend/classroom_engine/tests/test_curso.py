"""
El endpoint de prueba del curso «Ciencias naturales» (manifiesto de ejemplo) y la
misma vista servida por la biblioteca (host de pruebas con el manifiesto).
"""
from __future__ import annotations

import json
import os
import tempfile

from django.conf import settings
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from tools.host_biblioteca_pruebas import HostBibliotecaPruebas

from ..dominio import catalogos, curso as cur

CURSO = "avacom.co.lower-secondary.6.science.states-of-matter"


def manifiesto() -> dict:
    with open(settings.AVACOM_AULA_CURSO_EJEMPLO, encoding="utf-8") as f:
        return json.load(f)


class CursoDeEjemploTests(TestCase):
    def setUp(self):
        self.api = APIClient()

    def test_el_endpoint_de_prueba_entrega_ciencias_naturales(self):
        r = self.api.get("/api/aula/pruebas/curso/")
        self.assertEqual(r.status_code, 200)
        v = r.json()
        self.assertEqual(v["fuente"], "ejemplo")
        self.assertEqual(v["curso_ref"], CURSO)
        self.assertEqual(v["titulo"], "Estados de la materia y sus cambios")
        self.assertEqual(v["version"], "1.0.0")
        self.assertEqual(v["idioma"], "es-CO")
        self.assertEqual(v["clasificacion"]["pais"], "CO")
        self.assertEqual(v["clasificacion"]["asignatura"], {"codigo": "science", "nombre": "Ciencias naturales"})
        self.assertEqual(v["clasificacion"]["nivel"]["codigo"], "lower_secondary")
        self.assertEqual(v["clasificacion"]["grado"]["nombre"], "Sexto")
        self.assertEqual(v["resumen"]["lecciones"], 3)
        self.assertEqual(v["resumen"]["objetos"], 8)
        self.assertEqual(v["resumen"]["objetos_por_tipo"], {"lecture": 2, "explanation": 1, "simulation_lab": 2, "activity": 2, "exam": 1})
        self.assertEqual(v["resumen"]["preguntas"], 9)   # las del examen no viajan al aula
        self.assertEqual(v["resumen"]["fuera_de_alcance"], [{"objeto_ref": "l3-exam", "tipo": "exam", "modulo": "MOD-010"}])
        self.assertEqual(v["portada"]["media_ref"], "img-cover-matter")
        self.assertIn("/medios/img-cover-matter/", v["portada_url"])

    def test_los_objetos_llevan_su_componente_maui(self):
        v = self.api.get("/api/aula/pruebas/curso/").json()
        l1 = v["lecciones"][0]
        self.assertEqual(l1["leccion_ref"], "l1-three-states")
        self.assertEqual([o["componente"] for o in l1["objetos"]], ["presentacion", "lectura", "laboratorio_web", "actividad"])
        self.assertEqual([o["tipo"] for o in l1["objetos"]], ["lecture", "explanation", "simulation_lab", "activity"])
        self.assertEqual(l1["temas"][0]["subtemas"][0], {"tema_ref": "st-solid", "titulo": "Sólido"})

    def test_la_presentacion_trae_laminas_bloques_y_tramos(self):
        v = self.api.get("/api/aula/pruebas/curso/").json()
        lecture = v["lecciones"][0]["objetos"][0]
        self.assertEqual(lecture["total_unidades"], 3)
        s1, s2, s3 = lecture["laminas"]
        self.assertEqual((s1["unidad_ref"], s1["indice"], s1["duracion_seg"]), ("l1-lecture-s1", 1, 240))
        self.assertEqual([b["componente"] for b in s1["bloques"]], ["titulo", "texto"])
        texto = s1["bloques"][1]
        self.assertEqual(texto["estilo"], "definition")
        self.assertEqual(texto["tramos"][0], {"texto": "Materia", "negrita": True})
        self.assertFalse(texto["tramos"][1]["negrita"])
        imagen, lista = s2["bloques"]
        self.assertEqual(imagen["componente"], "imagen")
        self.assertEqual(imagen["url"], f"/api/aula/cursos/{CURSO}/medios/img-particles/?fuente=ejemplo")
        self.assertEqual(imagen["texto_alternativo"][:15], "Tres recipiente")
        self.assertEqual((lista["componente"], lista["ordenada"], len(lista["items"])), ("lista", False, 3))
        self.assertEqual(lista["items_tramos"][0][0], {"texto": "Sólido:", "negrita": True})
        video = s3["bloques"][0]
        self.assertEqual((video["componente"], video["desde_seg"], video["hasta_seg"], video["autoplay"]), ("video", 0, 60, False))
        self.assertEqual(video["duracion_seg"], 150.0)
        self.assertTrue(video["subtitulos_url"].endswith("/medios/vid-changes/subtitulos?fuente=ejemplo"))

    def test_la_lectura_trae_paginas_con_audio_y_pdf_por_rango(self):
        v = self.api.get("/api/aula/pruebas/curso/").json()
        lectura = v["lecciones"][0]["objetos"][1]
        self.assertEqual(lectura["componente"], "lectura")
        self.assertEqual(len(lectura["paginas"]), 2)
        audio = lectura["paginas"][0]["bloques"][0]
        self.assertEqual((audio["componente"], audio["duracion_seg"]), ("audio", 25.5))
        self.assertTrue(audio["transcripcion_url"].endswith("/medios/aud-summary/transcripcion?fuente=ejemplo"))
        pdf = lectura["paginas"][1]["bloques"][1]
        self.assertEqual((pdf["componente"], pdf["desde_pagina"], pdf["hasta_pagina"], pdf["paginas"]), ("pdf", 1, 3, 3))
        self.assertTrue(pdf["url_pagina_inicial"].endswith("#page=1"))

    def test_el_laboratorio_es_una_webview_con_parametros_de_lanzamiento(self):
        v = self.api.get("/api/aula/pruebas/curso/").json()
        phet = v["lecciones"][0]["objetos"][2]
        self.assertEqual(phet["componente"], "laboratorio_web")
        self.assertEqual(phet["simulacion"]["componente"], "webview")
        self.assertEqual(phet["simulacion"]["simulacion"]["proveedor"], "phet")
        self.assertIn("block_network", phet["simulacion"]["simulacion"]["ajustes"])
        self.assertEqual(phet["simulacion"]["simulacion"]["destinos"], ["screen", "tablet"])
        self.assertTrue(phet["url_lanzamiento"].endswith("/medios/sim-phet-states/states-of-matter-basics_es.html?fuente=ejemplo"))
        self.assertEqual(phet["simulacion"]["licencia"]["tipo"], "cc-by-4.0")
        curva = v["lecciones"][1]["objetos"][1]
        self.assertEqual(curva["parametros_lanzamiento"], {"startTemp": -10, "altitudeMeters": 0})
        self.assertIn("index.html?fuente=ejemplo&startTemp=-10&altitudeMeters=0", curva["url_lanzamiento"])
        self.assertEqual(curva["simulacion"]["simulacion"]["ancho_diseno"], 1280)
        self.assertEqual(len(curva["pasos"]), 3)

    def test_la_actividad_trae_las_seis_clases_de_pregunta_sin_ninguna_clave(self):
        r = self.api.get("/api/aula/pruebas/curso/")
        v = r.json()
        actividad = v["lecciones"][0]["objetos"][3]
        self.assertEqual(actividad["componente"], "actividad")
        self.assertEqual(actividad["ajustes"], {"retroalimentacion": "immediate", "intentos_permitidos": 2,
                                                "barajar_preguntas": False, "barajar_opciones": True})
        self.assertEqual([p["componente"] for p in actividad["preguntas"]],
                         ["opcion_multiple", "verdadero_falso", "completar", "relacionar", "ordenar", "abierta"])
        self.assertEqual(actividad["puntos_totales"], 13)
        mc, tf, fb, ma, ord_, ab = actividad["preguntas"]
        self.assertEqual([o["opcion_ref"] for o in mc["opciones"]], ["a", "b", "c"])
        self.assertFalse(mc["permite_varias"])
        self.assertEqual([o["opcion_ref"] for o in tf["opciones"]], ["true", "false"])
        self.assertEqual(fb["espacios"][0], {"espacio_ref": "b1", "modo_entrada": "select", "opciones": ["propio", "variable"]})
        self.assertEqual(len(ma["izquierda"]), 3)
        self.assertEqual(len(ma["derecha"]), 4)
        self.assertEqual([e["ref"] for e in ord_["elementos"]], ["o-gas", "o-solid", "o-liquid"])
        self.assertEqual((ab["formato_respuesta"], ab["longitud_maxima"]), ("text", 600))
        # Ninguna clave de corrección, ni en camelCase ni en español, en ningún nivel del payload.
        self.assertIsNone(cur.contiene_clave(v))
        texto = r.content.decode("utf-8")
        for prohibida in ("isCorrect", "acceptedAnswers", "modelAnswer", "correctOrder", '"pairs"', '"rubric"', '"answer"', '"feedback"'):
            self.assertNotIn(prohibida, texto)

    def test_el_examen_se_muestra_pero_no_se_ejecuta_en_el_aula(self):
        v = self.api.get("/api/aula/pruebas/curso/").json()
        examen = v["lecciones"][2]["objetos"][0]
        self.assertEqual((examen["componente"], examen["fuera_de_alcance"], examen["modulo"]), ("examen", True, "MOD-010"))
        self.assertEqual(examen["preguntas"], [])
        self.assertEqual(examen["total_preguntas_banco"], 12)
        self.assertEqual(examen["ajustes"]["seleccion"]["cantidad_preguntas"], 4)
        self.assertEqual(examen["ajustes"]["aprobacion_pct"], 60)

    def test_las_notas_del_docente_solo_salen_con_rol_docente(self):
        estudiante = self.api.get("/api/aula/pruebas/curso/").json()
        self.assertNotIn("notas_docente", json.dumps(estudiante))
        docente = self.api.get("/api/aula/pruebas/curso/?rol=docente").json()
        self.assertEqual(docente["rol"], "docente")
        self.assertIn("Curso de cuatro sesiones", docente["notas_docente"]["summary"])
        self.assertIn("timing", docente["lecciones"][0]["notas_docente"])
        self.assertIn("tips", docente["lecciones"][0]["objetos"][0]["notas_docente"])
        self.assertIn("tips", docente["lecciones"][0]["objetos"][0]["laminas"][1]["notas_docente"])
        self.assertIsNone(cur.contiene_clave(docente))   # tampoco el docente recibe claves desde el aula

    def test_la_lista_agrupa_por_asignatura_para_el_panel(self):
        r = self.api.get("/api/aula/cursos/?fuente=ejemplo")
        self.assertEqual(r.status_code, 200)
        datos = r.json()
        self.assertEqual(len(datos["asignaturas"]), 1)
        self.assertEqual(datos["asignaturas"][0]["nombre"], "Ciencias naturales")
        self.assertEqual(datos["asignaturas"][0]["codigo"], "science")
        ficha = datos["asignaturas"][0]["cursos"][0]
        self.assertEqual((ficha["curso_ref"], ficha["lecciones"], ficha["objetos"], ficha["medios"]), (CURSO, 3, 8, 8))
        self.assertEqual(self.api.get("/api/aula/pruebas/cursos/").json()["cursos"][0]["titulo"], ficha["titulo"])

    def test_leccion_y_objeto_sueltos_y_referencias_inexistentes(self):
        r = self.api.get(f"/api/aula/cursos/{CURSO}/lecciones/l2-changes-of-state/?fuente=ejemplo")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["leccion"]["titulo"], "Cambios de estado")
        self.assertEqual(r.json()["curso"]["clasificacion"]["asignatura"]["nombre"], "Ciencias naturales")
        r = self.api.get(f"/api/aula/cursos/{CURSO}/objetos/l2-activity/?fuente=ejemplo")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["objeto"]["componente"], "actividad")
        self.assertEqual(r.json()["leccion"]["leccion_ref"], "l2-changes-of-state")
        self.assertNotIn("objetos", r.json()["leccion"])
        r = self.api.get(f"/api/aula/cursos/{CURSO}/objetos/no-existe/?fuente=ejemplo")
        self.assertEqual((r.status_code, r.json()["codigo"]), (404, "referencia_no_encontrada"))
        r = self.api.get("/api/aula/cursos/otro-curso/?fuente=ejemplo")
        self.assertEqual((r.status_code, r.json()["codigo"]), (404, "curso_no_encontrado"))

    def test_la_fuente_se_resuelve_sola_para_la_referencia_del_ejemplo(self):
        # Sin `?fuente=`: la referencia es la del manifiesto de ejemplo → se sirve aunque la biblioteca no esté.
        r = self.api.get(f"/api/aula/cursos/{CURSO}/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["fuente"], "ejemplo")
        r = self.api.get(f"/api/aula/cursos/{CURSO}/medios/img-particles/")
        self.assertEqual(r.status_code, 200)

    def test_fuente_desconocida_y_biblioteca_ausente(self):
        r = self.api.get("/api/aula/cursos/?fuente=nube")
        self.assertEqual((r.status_code, r.json()["codigo"]), (400, "datos_invalidos"))
        with override_settings(AVACOM_CONTENIDO_ENLACE=os.path.join(tempfile.gettempdir(), "no-existe-enlace.json")):
            r = self.api.get("/api/aula/cursos/?fuente=biblioteca")
        self.assertEqual(r.status_code, 503)
        self.assertFalse(r.json()["disponible"])
        self.assertIn("sugerencia", r.json())

    # ------------------------------------------------------------------- medios
    def test_los_medios_de_ejemplo_son_bytes_validos_de_su_tipo(self):
        base = f"/api/aula/cursos/{CURSO}/medios"
        r = self.api.get(f"{base}/img-particles/?fuente=ejemplo")
        self.assertEqual((r.status_code, r["Content-Type"]), (200, "image/png"))
        self.assertEqual(r.content[:8], b"\x89PNG\r\n\x1a\n")
        self.assertEqual(r["X-Avacom-Marcador"], "ejemplo")
        r = self.api.head(f"{base}/img-particles/?fuente=ejemplo")
        self.assertEqual((r.status_code, r["Content-Type"], r.content), (200, "image/png", b""))
        r = self.api.get(f"{base}/img-particles/?fuente=ejemplo", HTTP_RANGE="bytes=0-9")
        self.assertEqual((r.status_code, len(r.content)), (206, 10))
        self.assertTrue(r["Content-Range"].startswith("bytes 0-9/"))
        r = self.api.get(f"{base}/aud-summary/?fuente=ejemplo")
        self.assertEqual((r.status_code, r["Content-Type"], r.content[:4]), (200, "audio/wav", b"RIFF"))
        r = self.api.get(f"{base}/pdf-lab-guide/?fuente=ejemplo")
        self.assertEqual((r.status_code, r["Content-Type"], r.content[:5]), (200, "application/pdf", b"%PDF-"))
        self.assertIn(b"/Count 3", r.content)
        r = self.api.get(f"{base}/sim-phet-states/states-of-matter-basics_es.html?fuente=ejemplo")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r["Content-Type"].startswith("text/html"))
        self.assertIn("Estados de la materia: básico (PhET)", r.content.decode("utf-8"))
        r = self.api.get(f"{base}/sim-heating-curve/index.html?fuente=ejemplo&startTemp=-10")
        self.assertEqual(r.status_code, 200)
        self.assertIn("scale(", r.content.decode("utf-8"))      # scale_to_fit
        r = self.api.get(f"{base}/vid-changes/subtitulos?fuente=ejemplo")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r["Content-Type"].startswith("text/vtt"))
        self.assertTrue(r.content.startswith(b"WEBVTT"))
        r = self.api.get(f"{base}/aud-summary/transcripcion?fuente=ejemplo")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r["Content-Type"].startswith("text/plain"))

    def test_el_video_de_ejemplo_no_se_simula_y_se_explica(self):
        r = self.api.get(f"/api/aula/cursos/{CURSO}/medios/vid-changes/?fuente=ejemplo")
        self.assertEqual((r.status_code, r.json()["codigo"]), (404, "referencia_no_encontrada"))
        self.assertIn("sugerencia", r.json())
        r = self.api.get(f"/api/aula/cursos/{CURSO}/medios/no-existe/?fuente=ejemplo")
        self.assertEqual(r.status_code, 404)
        r = self.api.get(f"/api/aula/cursos/{CURSO}/medios/sim-phet-states/otro.js?fuente=ejemplo")
        self.assertEqual(r.status_code, 404)


class NormalizadorTests(TestCase):
    def test_tramos_y_texto_plano(self):
        self.assertEqual(cur.tramos("**Gas:** sin forma"), [{"texto": "Gas:", "negrita": True}, {"texto": " sin forma", "negrita": False}])
        self.assertEqual(cur.tramos("sin marcado"), [{"texto": "sin marcado", "negrita": False}])
        self.assertEqual(cur.tramos(""), [])
        self.assertEqual(cur.texto_plano("a **b** c"), "a b c")

    def test_agrupar_por_asignatura_y_catalogos(self):
        grupos = cur.agrupar_por_asignatura([
            {"clasificacion": {"asignatura": {"codigo": "math", "nombre": "Matemáticas"}}, "curso_ref": "a"},
            {"clasificacion": {"asignatura": {"codigo": "science", "nombre": "Ciencias naturales"}}, "curso_ref": "b"},
            {"clasificacion": {"asignatura": {"codigo": "math", "nombre": "Matemáticas"}}, "curso_ref": "c"},
        ])
        self.assertEqual([g["nombre"] for g in grupos], ["Ciencias naturales", "Matemáticas"])
        self.assertEqual(len(grupos[1]["cursos"]), 2)
        self.assertEqual(set(catalogos.TIPOS_OBJETO), {"lecture", "explanation", "simulation_lab", "activity", "exam"})
        self.assertEqual(set(catalogos.TIPOS_BLOQUE), {"heading", "text", "list", "image", "video", "audio", "pdf"})
        self.assertEqual(len(catalogos.TIPOS_PREGUNTA), 6)

    def test_sin_claves_limpia_camel_y_espanol(self):
        sucio = {"options": [{"id": "a", "isCorrect": True, "feedback": "x"}], "answer": False, "clave_respuesta": "3",
                 "rubric": [], "ok": {"pairs": [], "texto": "se queda"}}
        self.assertEqual(cur.sin_claves(sucio), {"options": [{"id": "a"}], "ok": {"texto": "se queda"}})
        self.assertEqual(cur.contiene_clave(sucio), "isCorrect")

    def test_localizar_y_primer_objeto(self):
        vista = cur.normalizar(manifiesto(), rol="docente", fuente="ejemplo", url_medio=lambda m, r: f"/m/{m}/{r or ''}")
        hallado = cur.localizar(vista, objeto_ref="l1-lecture", unidad_ref="l1-lecture-s2")
        self.assertEqual(hallado["leccion"]["leccion_ref"], "l1-three-states")
        self.assertEqual(hallado["unidad"]["indice"], 2)
        pregunta = cur.localizar(vista, objeto_ref="l1-activity", unidad_ref="l1-act-q3")["unidad"]
        self.assertEqual(pregunta["componente"], "completar")
        self.assertEqual(cur.primer_objeto(vista, "l2-changes-of-state")["objeto"]["objeto_ref"], "l2-lecture")
        self.assertIsNone(cur.primer_objeto(vista, "l3-assessment"))   # el examen no es foco de aula
        with self.assertRaises(cur.ReferenciaNoEncontrada):
            cur.localizar(vista, objeto_ref="l1-lecture", unidad_ref="no-existe")


class ConLaBibliotecaTests(TestCase):
    """La misma vista de aula cuando el curso lo entrega AVACOM Biblioteca (host de pruebas con el manifiesto)."""

    def setUp(self):
        self.carpeta = tempfile.mkdtemp(prefix="avacom-aula-")
        self.ruta_enlace = os.path.join(self.carpeta, "enlace.json")
        self.manifiesto = manifiesto()
        self.host = HostBibliotecaPruebas(self.ruta_enlace, manifiestos={self.manifiesto["id"]: self.manifiesto}).iniciar()
        self._ajuste = override_settings(AVACOM_CONTENIDO_ENLACE=self.ruta_enlace)
        self._ajuste.enable()
        self.api = APIClient()

    def tearDown(self):
        self._ajuste.disable()
        self.host.detener()

    def test_el_manifiesto_servido_por_la_biblioteca_produce_la_misma_vista(self):
        biblioteca = self.api.get(f"/api/aula/cursos/{CURSO}/?fuente=biblioteca&rol=docente").json()
        ejemplo = self.api.get(f"/api/aula/cursos/{CURSO}/?fuente=ejemplo&rol=docente").json()
        self.assertEqual(biblioteca["fuente"], "biblioteca")
        self.assertEqual(biblioteca["titulo"], ejemplo["titulo"])
        self.assertEqual(biblioteca["resumen"], ejemplo["resumen"])
        self.assertEqual(len(biblioteca["lecciones"]), 3)
        # Sólo cambia la fuente en las URL de los medios.
        self.assertEqual(biblioteca["lecciones"][0]["objetos"][0]["laminas"][1]["bloques"][0]["url"],
                         f"/api/aula/cursos/{CURSO}/medios/img-particles/?fuente=biblioteca")
        self.assertIsNone(cur.contiene_clave(biblioteca))

    def test_la_lista_mezcla_manifiestos_y_arbol_del_contrato_1(self):
        datos = self.api.get("/api/aula/cursos/?fuente=biblioteca").json()
        nombres = [a["nombre"] for a in datos["asignaturas"]]
        self.assertIn("Ciencias naturales", nombres)
        self.assertIn("Matemáticas", nombres)
        self.assertIn("Exploración del medio", nombres)

    def test_el_arbol_del_contrato_1_se_normaliza_con_la_misma_forma(self):
        v = self.api.get("/api/aula/cursos/co-secundaria-8-matematicas/?fuente=biblioteca").json()
        self.assertEqual(v["esquema"], "contrato-1")
        self.assertEqual(v["clasificacion"]["asignatura"]["nombre"], "Matemáticas")
        self.assertEqual(len(v["lecciones"]), 3)
        tipos = {o["tipo_contrato1"]: o for l in v["lecciones"] for o in l["objetos"]}
        self.assertEqual((tipos["evaluacion"]["componente"], tipos["evaluacion"]["fuera_de_alcance"]), ("examen", True))
        self.assertEqual(tipos["leccion"]["componente"], "lectura")
        self.assertEqual(tipos["leccion"]["detalle_url"], "/api/biblioteca/leccion/co-sec-mat-lec-funcion/")
        self.assertEqual(tipos["interactivo"]["url_lanzamiento"], "/api/biblioteca/medio/co-sec-mat-int-grafica/index.html")
        self.assertEqual(tipos["video"]["medio"]["url"], "/api/biblioteca/medio/co-sec-mat-video-pendiente/")
        self.assertIsNone(cur.contiene_clave(v))

    def test_los_medios_pasan_a_traves_de_la_biblioteca(self):
        r = self.api.get("/api/aula/cursos/co-preescolar-transicion-exploracion/medios/co-pre-exp-img-granja/?fuente=biblioteca")
        self.assertEqual((r.status_code, r["Content-Type"]), (200, "image/png"))
        self.assertEqual(b"".join(r.streaming_content)[:8], b"\x89PNG\r\n\x1a\n")
        r = self.api.get("/api/aula/cursos/co-secundaria-8-matematicas/medios/co-sec-mat-video-pendiente/?fuente=biblioteca",
                         HTTP_RANGE="bytes=0-9")
        self.assertEqual(r.status_code, 206)
        self.assertEqual(r["Content-Range"], "bytes 0-9/102400")
        r = self.api.get("/api/aula/cursos/co-secundaria-8-matematicas/medios/no-existe/?fuente=biblioteca")
        self.assertEqual(r.status_code, 404)
