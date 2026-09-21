"""La forma de `response` por tipo de pregunta y la traducción del veredicto (§5 y §6 del mapeo). Dominio puro."""
from __future__ import annotations

from django.test import SimpleTestCase

from ..dominio import respuestas as resp
from ..dominio.errores import DatosInvalidos

MC = {"pregunta_ref": "q1", "tipo": "multiple_choice", "permite_varias": False,
      "opciones": [{"opcion_ref": "a"}, {"opcion_ref": "b"}, {"opcion_ref": "c"}]}
FB = {"pregunta_ref": "q3", "tipo": "fill_blanks", "espacios": [{"espacio_ref": "b1"}, {"espacio_ref": "b2"}]}
MA = {"pregunta_ref": "q4", "tipo": "matching", "izquierda": [{"ref": "l1"}], "derecha": [{"ref": "r1"}, {"ref": "r2"}]}
OR = {"pregunta_ref": "q5", "tipo": "ordering", "elementos": [{"ref": "x"}, {"ref": "y"}]}
AB = {"pregunta_ref": "q6", "tipo": "open", "longitud_maxima": 5}


class FormaDeLaRespuestaTests(SimpleTestCase):
    def test_cada_tipo_admite_solo_su_forma(self):
        self.assertEqual(resp.validar_respuesta(MC, {"selectedOptionIds": ["b", "b"]}), {"selectedOptionIds": ["b"]})
        self.assertEqual(resp.validar_respuesta({**MC, "permite_varias": True}, {"selectedOptionIds": ["a", "c"]}), {"selectedOptionIds": ["a", "c"]})
        self.assertEqual(resp.validar_respuesta({"tipo": "true_false"}, {"value": "true"}), {"value": True})
        self.assertEqual(resp.validar_respuesta(FB, {"blanks": {"b1": 2, "b2": "forma"}}), {"blanks": {"b1": "2", "b2": "forma"}})
        self.assertEqual(resp.validar_respuesta(MA, {"pairs": [{"leftId": "l1", "rightId": "r2"}]}), {"pairs": [{"leftId": "l1", "rightId": "r2"}]})
        self.assertEqual(resp.validar_respuesta(OR, {"order": ["y", "x"]}), {"order": ["y", "x"]})
        self.assertEqual(resp.validar_respuesta(AB, {"drawingRef": "d-1"}), {"drawingRef": "d-1"})

    def test_lo_que_no_cumple_la_forma_es_400(self):
        casos = [
            (MC, {"selectedOptionIds": []}), (MC, {"selectedOptionIds": ["a", "b"]}), (MC, {"selectedOptionIds": ["z"]}),
            (MC, {"selectedIndex": 1}), (MC, {"value": True}), (MC, "a"), (MC, {}),
            ({"tipo": "true_false"}, {"value": "sí"}),
            (FB, {"blanks": {"b9": "x"}}), (FB, {"blanks": []}),
            (MA, {"pairs": [{"leftId": "l1", "rightId": "r9"}]}), (MA, {"pairs": [{"leftId": "l1"}]}),
            (OR, {"order": ["x"]}), (OR, {"order": ["x", "x"]}),
            (AB, {"text": "demasiado largo"}), (AB, {"text": "a", "audioRef": "b"}), (AB, {}),
        ]
        for pregunta, respuesta in casos:
            with self.subTest(tipo=pregunta.get("tipo"), respuesta=respuesta), self.assertRaises(DatosInvalidos):
                resp.validar_respuesta(pregunta, respuesta)

    def test_un_tipo_desconocido_se_reenvia_tal_cual(self):
        """Conjunto abierto (§9): un tipo nuevo no rompe; la biblioteca decide."""
        self.assertEqual(resp.validar_respuesta({"tipo": "hotspot"}, {"x": 1, "y": 2}), {"x": 1, "y": 2})


class VeredictoTests(SimpleTestCase):
    def test_score_y_correct_admiten_nulo_y_decimales(self):
        v = resp.veredicto({"questionId": "q", "score": 1.3333, "maxScore": 2, "correct": False, "requiresManualGrading": False, "feedback": []})
        self.assertEqual((v["puntaje"], v["puntaje_maximo"], v["correcta"], v["pendiente"]), (1.3333, 2.0, False, False))
        v = resp.veredicto({"questionId": "q", "score": 1, "maxScore": 2, "correct": None, "requiresManualGrading": False, "feedback": "una línea"})
        self.assertEqual((v["puntaje"], v["correcta"], v["retroalimentacion"]), (1.0, None, ["una línea"]))

    def test_la_correccion_manual_deja_el_intento_pendiente_sin_nota(self):
        # Aunque llegara un número, con requiresManualGrading no se inventa nota.
        v = resp.veredicto({"questionId": "q6", "score": 4, "maxScore": 4, "correct": None, "requiresManualGrading": True}, "otra")
        self.assertEqual((v["pregunta_ref"], v["puntaje"], v["puntaje_maximo"], v["requiere_correccion_manual"], v["pendiente"]), ("q6", None, 4.0, True, True))
        self.assertEqual(v["retroalimentacion"], [])
        self.assertEqual(resp.veredicto({}, "q9")["pregunta_ref"], "q9")
