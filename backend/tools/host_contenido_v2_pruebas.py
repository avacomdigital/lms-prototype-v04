"""
Host de pruebas que imita la **API de Contenido v2** de AVACOM Biblioteca (contrato 2)
en loopback, con la forma comprobada en vivo el 2026-09-21 contra `GET /v2/openapi.json`
(copia en spec-driven/02-classroom-engine/openapi.v2.json):

  GET  /v2/health                                     → {contract: 2, schema, index: ready|rebuilding, installedCourses: n}
  GET  /v2/courses?page&pageSize                      → {items:[CourseSummary], page, pageSize, total}
  GET  /v2/courses/{id}?mode&profile                  → el ESQUEMA: metadatos, lecciones con resúmenes de objeto y medios
  GET  /v2/courses/{id}/lessons/{lid}?mode&profile&seed → la lección completa recortada (+ courseId, version)
  GET  /v2/courses/{id}/objects/{oid}?profile&seed    → un objeto completo (+ courseId, version, lessonId)
  GET  /v2/courses/{id}/questions/{qid}/grading-guide?version
  POST /v2/evaluate · /v2/evaluate/batch (≤ 200)      → veredicto con las claves del manifiesto completo · {results[]}
  POST /v2/media-sessions · DELETE /v2/media-sessions/{id}
  Servidor de medios aparte (mediaPort): /s/{cap}/{mediaId}[/@captions|/@transcript|/@files|/{ruta}] con Range, sin token

Autenticación: cabecera `X-Avacom-Token`; sin ella o con otra, 401 `unauthorized`. Escribe
`link.json` ({contract, apiPort, mediaPort, token, pid, startedAt}) donde se le indique, para
que el backend lo encuentre con AVACOM_CONTENIDO_ENLACE_V2. `rechazar_proximas = n` fuerza n
401 seguidos (para probar el reintento único); `reconstruyendo = True` responde 503
`index_rebuilding`; `desactivados` responde 403 `policy_disabled` y omite el curso de la lista.

Uso a mano, sin la biblioteca real:

    python -m tools.host_contenido_v2_pruebas %TEMP%\\link-pruebas.json
    set AVACOM_CONTENIDO_ENLACE_V2=%TEMP%\\link-pruebas.json
"""
from __future__ import annotations

import copy
import json
import os
import secrets
import sys
import threading
import time
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlparse

# Lo que la API recorta antes de entregar una pregunta (§1 del mapeo).
CLAVES_RECORTADAS = frozenset({
    "answer", "acceptedAnswers", "wrongAnswers", "numericTolerance", "pairs", "wrongPairs", "correctOrder", "wrongOrders",
    "modelAnswer", "rubric", "incorrectExamples", "feedback", "isCorrect",
})
# Lo que el esquema del curso resume de cada objeto (CourseOutline).
CLAVES_RESUMEN_OBJETO = ("id", "type", "title", "modes", "topicRef", "estimatedDurationSec", "mediaId")
MODOS = ("simple", "class", "exam", "review", "free_learning")
LOTE_MAXIMO = 200

PNG_1x1 = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000d4944415478da63f8ffff3f0300"
    "0501fe0d8d3d0e0000000049454e44ae426082"
)


def recortar(valor, *, perfil: str):
    """Quita claves de corrección y, con perfil student, las notas del docente. Recursivo."""
    if isinstance(valor, dict):
        salida = {}
        for k, v in valor.items():
            if k in CLAVES_RECORTADAS or (perfil == "student" and k == "teacherNotes"):
                continue
            salida[k] = recortar(v, perfil=perfil)
        return salida
    if isinstance(valor, list):
        return [recortar(v, perfil=perfil) for v in valor]
    return valor


def _rotacion(semilla: str | None, n: int) -> int:
    """Sin semilla, una posición; con semilla, un desplazamiento derivado de ella. Nunca el orden de origen."""
    if n < 2:
        return 0
    if not semilla:
        return 1
    return 1 + sum(ord(c) for c in semilla) % (n - 1)


def barajar_preguntas(preguntas: list[dict], semilla: str | None) -> None:
    """Las opciones, parejas y elementos llegan en otro orden en cada llamada (rotados), para que una
    prueba que guarde posiciones en vez de `id` falle."""
    for pregunta in preguntas:
        for clave in ("options", "right", "items"):
            lista = pregunta.get(clave)
            if isinstance(lista, list) and len(lista) > 1:
                k = _rotacion(semilla, len(lista))
                pregunta[clave] = lista[k:] + lista[:k]


def filtrar_modo(objetos: list[dict], modo: str | None) -> list[dict]:
    if not modo:
        return objetos
    return [o for o in objetos if not o.get("modes") or modo in o["modes"]]


def resumen_objeto(o: dict) -> dict:
    salida = {k: o[k] for k in CLAVES_RESUMEN_OBJETO if k in o}
    if o.get("type") == "lecture":
        salida["pageCount"] = len(o.get("slides") or [])
    elif o.get("type") == "explanation":
        salida["pageCount"] = len(o.get("pages") or [])
    elif o.get("type") in ("activity", "exam"):
        salida["questionCount"] = len(o.get("questions") or [])
    return salida


def resumen_medio(m: dict) -> dict:
    salida = {k: v for k, v in m.items() if k not in ("path", "captionsPath", "transcriptPath")}
    salida["hasCaptions"] = bool(m.get("captionsPath"))
    salida["hasTranscript"] = bool(m.get("transcriptPath"))
    return salida


def ficha(m: dict) -> dict:
    """CourseSummary."""
    return {"courseId": m.get("id"), "version": m.get("version"), "title": m.get("title"), "subtitle": m.get("subtitle"),
            "language": m.get("language"), "translationGroupId": m.get("translationGroupId"), "classification": m.get("classification"),
            "estimatedDurationMin": m.get("estimatedDurationMin"), "modes": m.get("modes"),
            "curriculumRefs": [{"framework": r.get("framework"), "code": r.get("code")} for r in m.get("curriculumRefs") or []],
            "lessonCount": len(m.get("lessons") or []), "coverMediaId": m.get("coverMediaId"), "updatedAt": "2026-09-18T16:21:50Z"}


# ------------------------------------------------------------------ calificar

def _decimal(x) -> float:
    return round(float(x), 4)


def calificar(pregunta: dict, respuesta: dict) -> dict:
    """El veredicto con las claves del manifiesto completo. Devuelve la forma del contrato (EvaluationResult)."""
    tipo = pregunta.get("type")
    puntos = float(pregunta.get("points") or 1)
    parcial = bool(pregunta.get("partialCredit"))
    retro_general = pregunta.get("feedback") or {}
    base = {"questionId": pregunta["id"], "maxScore": puntos, "requiresManualGrading": False, "feedback": []}

    def cerrar(fraccion: float, extra: list[str] | None = None) -> dict:
        fraccion = max(0.0, min(1.0, fraccion))
        if not parcial and fraccion < 1.0:
            fraccion = 0.0
        acierto = fraccion >= 1.0
        retro = list(extra or [])
        if acierto and retro_general.get("correct"):
            retro.append(retro_general["correct"])
        if not acierto and retro_general.get("incorrect"):
            retro.append(retro_general["incorrect"])
        return {**base, "score": _decimal(puntos * fraccion), "correct": True if acierto else (None if 0 < fraccion < 1 else False),
                "feedback": retro}

    if tipo == "multiple_choice":
        elegidas = respuesta.get("selectedOptionIds")
        if not isinstance(elegidas, list):
            raise ValueError("Response must contain an array 'selectedOptionIds'.")
        opciones = {o["id"]: o for o in pregunta.get("options") or []}
        if any(e not in opciones for e in elegidas):
            raise ValueError("Unknown option id.")
        correctas = {k for k, o in opciones.items() if o.get("isCorrect")}
        aciertos = len(correctas & set(elegidas))
        fallos = len(set(elegidas) - correctas)
        extra = [opciones[e]["feedback"] for e in elegidas if e not in correctas and opciones[e].get("feedback")]
        return cerrar((aciertos - fallos) / max(1, len(correctas)), extra)
    if tipo == "true_false":
        valor = respuesta.get("value")
        if not isinstance(valor, bool):
            raise ValueError("Response must contain a boolean 'value'.")
        return cerrar(1.0 if valor == pregunta.get("answer") else 0.0)
    if tipo == "fill_blanks":
        huecos = respuesta.get("blanks")
        if not isinstance(huecos, dict):
            raise ValueError("Response must contain an object 'blanks'.")
        blancos = pregunta.get("blanks") or []
        aciertos, extra = 0, []
        for b in blancos:
            dado = str(huecos.get(b["id"], "")).strip().lower()
            if dado in {str(a).strip().lower() for a in (b.get("acceptedAnswers") or [])}:
                aciertos += 1
            else:
                extra.extend(w["feedback"] for w in (b.get("wrongAnswers") or []) if str(w.get("value", "")).lower() == dado and w.get("feedback"))
        return cerrar(aciertos / max(1, len(blancos)), extra)
    if tipo == "matching":
        parejas = respuesta.get("pairs")
        if not isinstance(parejas, list):
            raise ValueError("Response must contain an array 'pairs'.")
        esperadas = {(p["leftId"], p["rightId"]) for p in pregunta.get("pairs") or []}
        dadas = {(p.get("leftId"), p.get("rightId")) for p in parejas if isinstance(p, dict)}
        return cerrar(len(esperadas & dadas) / max(1, len(esperadas)))
    if tipo == "ordering":
        orden = respuesta.get("order")
        if not isinstance(orden, list):
            raise ValueError("Response must contain an array 'order'.")
        extra = [w["feedback"] for w in (pregunta.get("wrongOrders") or []) if w.get("order") == orden and w.get("feedback")]
        return cerrar(1.0 if orden == pregunta.get("correctOrder") else 0.0, extra)
    if tipo == "open":
        if not any(respuesta.get(k) for k in ("text", "drawingRef", "audioRef")):
            raise ValueError("Response must contain text, drawingRef or audioRef.")
        return {**base, "score": None, "correct": None, "requiresManualGrading": True, "feedback": []}
    raise LookupError("question_not_found")


class HostContenidoV2Pruebas:
    def __init__(self, ruta_enlace: str, manifiestos: dict[str, dict], archivados: dict[tuple[str, str], dict] | None = None,
                 medios: dict[str, tuple[str, bytes]] | None = None, desactivados: set[str] | None = None):
        self.ruta_enlace = ruta_enlace
        self.manifiestos = dict(manifiestos)                    # courseId → manifiesto COMPLETO (con claves) de la versión instalada
        self.archivados = dict(archivados or {})                # (courseId, version) → manifiesto archivado (sólo evaluate y grading-guide)
        self.medios = dict(medios or {})                        # mediaId, "mediaId/@captions", "mediaId/@transcript" o "mediaId/ruta" → (tipo, bytes)
        self.desactivados = set(desactivados or ())
        self.token = secrets.token_urlsafe(32)
        self.reconstruyendo = False
        self.rechazar_proximas = 0
        self.peticiones: list[str] = []
        self.consultas: list[dict] = []
        self.cuerpos: list[dict] = []
        self.sesiones: dict[str, dict] = {}                     # capacidad → {id, courseId, mediaIds, expira}
        self._api: ThreadingHTTPServer | None = None
        self._medios: ThreadingHTTPServer | None = None

    # ------------------------------------------------------------ ciclo de vida
    def iniciar(self) -> "HostContenidoV2Pruebas":
        self._api = ThreadingHTTPServer(("127.0.0.1", 0), self._manejador_api())
        self._medios = ThreadingHTTPServer(("127.0.0.1", 0), self._manejador_medios())
        for servidor in (self._api, self._medios):
            servidor.daemon_threads = True
            threading.Thread(target=servidor.serve_forever, daemon=True).start()
        self.escribir_enlace()
        return self

    @property
    def puerto(self) -> int:
        return self._api.server_address[1] if self._api else 0

    @property
    def puerto_medios(self) -> int:
        return self._medios.server_address[1] if self._medios else 0

    def escribir_enlace(self) -> None:
        os.makedirs(os.path.dirname(self.ruta_enlace) or ".", exist_ok=True)
        with open(self.ruta_enlace, "w", encoding="utf-8") as archivo:
            json.dump({"contract": 2, "apiPort": self.puerto, "mediaPort": self.puerto_medios, "token": self.token,
                       "pid": os.getpid(), "startedAt": datetime.now(timezone.utc).isoformat()}, archivo)

    def rotar_token(self) -> None:
        """La biblioteca se reinició: token nuevo en link.json."""
        self.token = secrets.token_urlsafe(32)
        self.escribir_enlace()

    def borrar_enlace(self) -> None:
        try:
            os.remove(self.ruta_enlace)
        except OSError:
            pass

    def detener(self) -> None:
        for servidor in (self._api, self._medios):
            if servidor:
                servidor.shutdown()
                servidor.server_close()
        self._api = self._medios = None
        self.borrar_enlace()

    # ----------------------------------------------------------------- datos
    def _curso(self, ref: str, version: str | None) -> dict | None:
        if version and version != str(self.manifiestos.get(ref, {}).get("version", "")):
            return self.archivados.get((ref, version))
        return self.manifiestos.get(ref)

    @staticmethod
    def _leccion(curso: dict, leccion_ref: str) -> dict | None:
        return next((l for l in curso.get("lessons") or [] if str(l.get("id")) == leccion_ref), None)

    @staticmethod
    def _objeto(curso: dict, objeto_ref: str) -> tuple[dict, dict] | None:
        for l in curso.get("lessons") or []:
            for o in l.get("objects") or []:
                if str(o.get("id")) == objeto_ref:
                    return l, o
        return None

    @staticmethod
    def _pregunta(curso: dict, objeto_ref: str, pregunta_ref: str) -> dict | None:
        hallado = HostContenidoV2Pruebas._objeto(curso, objeto_ref)
        if not hallado:
            return None
        return next((q for q in hallado[1].get("questions") or [] if str(q.get("id")) == pregunta_ref), None)

    def _esquema(self, curso: dict, modo: str | None, perfil: str) -> dict:
        salida = {k: v for k, v in curso.items() if k not in ("id", "lessons", "media", "teacherNotes")}
        salida = {"courseId": curso.get("id"), **salida}
        if perfil != "student" and curso.get("teacherNotes") is not None:
            salida["teacherNotes"] = curso["teacherNotes"]
        salida["lessons"] = [
            {**{k: v for k, v in l.items() if k not in ("objects", "teacherNotes")},
             "objects": [resumen_objeto(o) for o in filtrar_modo(l.get("objects") or [], modo)]}
            for l in curso.get("lessons") or []
        ]
        salida["media"] = [resumen_medio(m) for m in curso.get("media") or []]
        return salida

    def _abrir_sesion(self, curso: dict, media_ids: list[str] | None, leccion_ref: str | None, ttl: int) -> dict:
        medios = {str(m.get("id")): m for m in curso.get("media") or []}
        if media_ids is not None:
            pedidos = [m for m in media_ids if m in medios]
        elif leccion_ref:
            leccion = self._leccion(curso, leccion_ref)
            if leccion is None:
                raise LookupError("lesson_not_found")
            texto = json.dumps(leccion)
            pedidos = [m for m in medios if f'"{m}"' in texto]
        else:
            pedidos = list(medios)
        cap = secrets.token_urlsafe(16)
        sesion_id = "ms_" + secrets.token_hex(8)
        base = f"http://127.0.0.1:{self.puerto_medios}/s/{cap}/"
        self.sesiones[cap] = {"id": sesion_id, "courseId": curso.get("id"), "mediaIds": set(pedidos),
                              "expira": time.time() + ttl}
        urls, extras = {}, {}
        for m in pedidos:
            medio = medios[m]
            urls[m] = f"{base}{m}/{medio['entry']}" if medio.get("kind") == "simulation" and medio.get("entry") else f"{base}{m}"
            extra = {}
            if medio.get("kind") == "simulation":
                extra["files"] = f"{base}{m}/@files"
            if medio.get("captionsPath"):
                extra["captions"] = f"{base}{m}/@captions"
            if medio.get("transcriptPath"):
                extra["transcript"] = f"{base}{m}/@transcript"
            if extra:
                extras[m] = extra
        expira = (datetime.now(timezone.utc) + timedelta(seconds=ttl)).isoformat()
        return {"sessionId": sesion_id, "baseUrl": base, "expiresAt": expira, "urls": urls, "extras": extras}

    # -------------------------------------------------------------- servidores
    def _manejador_api(self):
        host = self

        class Manejador(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.0"

            def log_message(self, *args):
                pass

            def _json(self, codigo: int, datos) -> None:
                cuerpo = json.dumps(datos, ensure_ascii=False).encode("utf-8")
                self.send_response(codigo)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(cuerpo)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                if self.command != "HEAD":
                    self.wfile.write(cuerpo)

            def _error(self, estado: int, codigo: str, mensaje: str) -> None:
                self._json(estado, {"error": {"code": codigo, "message": mensaje, "details": {}}})

            def _autorizado(self) -> bool:
                if host.rechazar_proximas > 0:
                    host.rechazar_proximas -= 1
                    self._error(401, "unauthorized", "Missing or invalid X-Avacom-Token")
                    return False
                if self.headers.get("X-Avacom-Token") != host.token:
                    self._error(401, "unauthorized", "Missing or invalid X-Avacom-Token")
                    return False
                return True

            def _entrada(self):
                url = urlparse(self.path)
                camino = unquote(url.path)
                consulta = {k: v[0] for k, v in parse_qs(url.query).items()}
                host.peticiones.append(f"{self.command} {camino}")
                host.consultas.append(consulta)
                return camino, consulta, [p for p in camino.split("/") if p]

            def _perfil_modo(self, consulta):
                perfil = consulta.get("profile") or "student"
                modo = consulta.get("mode")
                if perfil not in ("student", "teacher"):
                    self._error(400, "invalid_parameter", "profile must be student or teacher")
                    return None
                if modo and modo not in MODOS:
                    self._error(400, "invalid_parameter", "mode must be simple, class, exam, review or free_learning")
                    return None
                return perfil, modo

            def do_HEAD(self):
                self.do_GET()

            def do_GET(self):
                camino, consulta, partes = self._entrada()
                if not self._autorizado():
                    return
                if camino == "/v2/health":
                    return self._json(200, {"contract": 2, "schema": "1.0", "index": "rebuilding" if host.reconstruyendo else "ready",
                                            "installedCourses": len(host.manifiestos)})
                if host.reconstruyendo:
                    return self._error(503, "index_rebuilding", "Index is rebuilding")

                if camino == "/v2/courses":
                    fichas = [ficha(m) for ref, m in host.manifiestos.items() if ref not in host.desactivados]
                    pagina, tamano = int(consulta.get("page") or 1), int(consulta.get("pageSize") or 20)
                    inicio = (pagina - 1) * tamano
                    return self._json(200, {"items": fichas[inicio:inicio + tamano], "page": pagina, "pageSize": tamano, "total": len(fichas)})

                if len(partes) >= 3 and partes[0] == "v2" and partes[1] == "courses":
                    ref = partes[2]
                    curso = host.manifiestos.get(ref)
                    if len(partes) == 3:
                        pm = self._perfil_modo(consulta)
                        if pm is None:
                            return None
                        if ref in host.desactivados:
                            return self._error(403, "policy_disabled", "Disabled by school policy")
                        if curso is None:
                            return self._error(404, "course_not_found", "Course not installed")
                        return self._json(200, host._esquema(curso, pm[1], pm[0]))
                    if curso is None:
                        return self._error(404, "course_not_found", "Course not installed")
                    if ref in host.desactivados:
                        return self._error(403, "policy_disabled", "Disabled by school policy")
                    if len(partes) == 5 and partes[3] == "lessons":
                        pm = self._perfil_modo(consulta)
                        if pm is None:
                            return None
                        leccion = host._leccion(curso, partes[4])
                        if leccion is None:
                            return self._error(404, "lesson_not_found", "Lesson not found")
                        salida = recortar(copy.deepcopy(leccion), perfil=pm[0])
                        salida["objects"] = filtrar_modo(salida.get("objects") or [], pm[1])
                        for o in salida["objects"]:
                            barajar_preguntas(o.get("questions") or [], consulta.get("seed"))
                        return self._json(200, {**salida, "courseId": ref, "version": curso.get("version")})
                    if len(partes) == 5 and partes[3] == "objects":
                        pm = self._perfil_modo(consulta)
                        if pm is None:
                            return None
                        hallado = host._objeto(curso, partes[4])
                        if hallado is None:
                            return self._error(404, "object_not_found", "Object not found")
                        salida = recortar(copy.deepcopy(hallado[1]), perfil=pm[0])
                        barajar_preguntas(salida.get("questions") or [], consulta.get("seed"))
                        return self._json(200, {**salida, "courseId": ref, "version": curso.get("version"), "lessonId": hallado[0].get("id")})
                    if len(partes) == 6 and partes[3] == "questions" and partes[5] == "grading-guide":
                        version = consulta.get("version")
                        fuente = host._curso(ref, version)
                        if fuente is None:
                            return self._error(404, "version_not_available", f"Version {version} is not available")
                        pregunta = None
                        for l in fuente.get("lessons") or []:
                            for o in l.get("objects") or []:
                                pregunta = pregunta or next((q for q in o.get("questions") or [] if str(q.get("id")) == partes[4]), None)
                        if not pregunta:
                            return self._error(404, "question_not_found", "Question not found")
                        return self._json(200, {"courseId": ref, "version": fuente.get("version"), "questionId": pregunta["id"],
                                                "prompt": pregunta.get("prompt"), "points": pregunta.get("points"),
                                                "responseFormat": pregunta.get("responseFormat"), "modelAnswer": pregunta.get("modelAnswer"),
                                                "rubric": pregunta.get("rubric") or [], "incorrectExamples": pregunta.get("incorrectExamples") or []})
                return self._error(404, "not_found", "Unknown endpoint")

            def do_POST(self):
                camino, _, _ = self._entrada()
                if not self._autorizado():
                    return
                largo = int(self.headers.get("Content-Length") or 0)
                cuerpo = json.loads(self.rfile.read(largo) or b"{}") if largo else {}
                host.cuerpos.append(cuerpo)
                if host.reconstruyendo:
                    return self._error(503, "index_rebuilding", "Index is rebuilding")

                if camino == "/v2/evaluate":
                    try:
                        return self._json(200, self._evaluar(cuerpo))
                    except LookupError as e:
                        return self._error(404, str(e), str(e).replace("_", " "))
                    except ValueError as e:
                        return self._error(422, "invalid_response", str(e))
                if camino == "/v2/evaluate/batch":
                    items = cuerpo.get("items")
                    if not isinstance(items, list) or len(items) > LOTE_MAXIMO:
                        return self._error(400, "invalid_parameter", f"items must be an array of at most {LOTE_MAXIMO}")
                    try:
                        return self._json(200, {"results": [self._evaluar(i) for i in items]})
                    except LookupError as e:
                        return self._error(404, str(e), str(e).replace("_", " "))
                    except ValueError as e:
                        return self._error(422, "invalid_response", str(e))
                if camino == "/v2/media-sessions":
                    ref = str(cuerpo.get("courseId") or "")
                    curso = host.manifiestos.get(ref)
                    if curso is None:
                        return self._error(404, "course_not_found", "Course not installed")
                    ttl = int(cuerpo.get("ttlSec") or 14400)
                    if not 1 <= ttl <= 28800:
                        return self._error(400, "invalid_parameter", "ttlSec out of range")
                    try:
                        return self._json(200, host._abrir_sesion(curso, cuerpo.get("mediaIds"), cuerpo.get("lessonId"), ttl))
                    except LookupError as e:
                        return self._error(404, str(e), "Lesson not found")
                return self._error(404, "not_found", "Unknown endpoint")

            def do_DELETE(self):
                camino, _, partes = self._entrada()
                if not self._autorizado():
                    return
                if len(partes) == 3 and partes[1] == "media-sessions":
                    for cap, s in list(host.sesiones.items()):
                        if s["id"] == partes[2]:
                            del host.sesiones[cap]
                            self.send_response(204)
                            self.end_headers()
                            return
                    return self._error(404, "media_session_not_found", "Not found")
                return self._error(404, "not_found", "Unknown endpoint")

            def _evaluar(self, cuerpo: dict) -> dict:
                ref = str(cuerpo.get("courseId") or "")
                version = cuerpo.get("version")
                if ref not in host.manifiestos:
                    raise LookupError("course_not_found")
                curso = host._curso(ref, version)
                if curso is None:
                    raise LookupError("version_not_available")
                hallado = host._objeto(curso, str(cuerpo.get("objectId") or ""))
                if hallado is None:
                    raise LookupError("object_not_found")
                pregunta = host._pregunta(curso, str(cuerpo.get("objectId") or ""), str(cuerpo.get("questionId") or ""))
                if pregunta is None:
                    raise LookupError("question_not_found")
                respuesta = cuerpo.get("response")
                if not isinstance(respuesta, dict):
                    raise ValueError("response must be an object")
                return calificar(pregunta, respuesta)

        return Manejador

    def _manejador_medios(self):
        host = self

        class Medios(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.0"

            def log_message(self, *args):
                pass

            def _error(self, estado: int, codigo: str) -> None:
                cuerpo = json.dumps({"error": {"code": codigo, "message": "Not found", "details": {}}}).encode()
                self.send_response(estado)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(cuerpo)))
                self.end_headers()
                if self.command != "HEAD":
                    self.wfile.write(cuerpo)

            def _bytes(self, tipo: str, datos: bytes) -> None:
                rango = self.headers.get("Range")
                desde, hasta, parcial = 0, len(datos) - 1, False
                if rango and rango.startswith("bytes="):
                    a, _, b = rango[6:].partition("-")
                    if a == "" and b:
                        desde = max(0, len(datos) - int(b))
                    else:
                        desde = int(a or 0)
                        hasta = int(b) if b else len(datos) - 1
                    parcial = True
                    if desde >= len(datos):
                        self.send_response(416)
                        self.send_header("Content-Range", f"bytes */{len(datos)}")
                        self.end_headers()
                        return
                trozo = datos[desde:hasta + 1]
                self.send_response(206 if parcial else 200)
                self.send_header("Content-Type", tipo)
                self.send_header("Content-Length", str(len(trozo)))
                self.send_header("Accept-Ranges", "bytes")
                self.send_header("Cache-Control", "no-store")
                if parcial:
                    self.send_header("Content-Range", f"bytes {desde}-{hasta}/{len(datos)}")
                self.end_headers()
                if self.command != "HEAD":
                    self.wfile.write(trozo)

            def do_HEAD(self):
                self.do_GET()

            def do_GET(self):
                camino = unquote(urlparse(self.path).path)
                host.peticiones.append(f"MEDIA GET {camino}")
                partes = [p for p in camino.split("/") if p]
                if len(partes) < 3 or partes[0] != "s":
                    return self._error(404, "media_session_not_found")
                sesion = host.sesiones.get(partes[1])
                if sesion is None or sesion["expira"] < time.time():
                    return self._error(404, "media_session_not_found")
                media_id = partes[2]
                if media_id not in sesion["mediaIds"]:
                    return self._error(404, "media_session_not_found")
                resto = "/".join(partes[3:])
                if resto == "@files":
                    curso = host.manifiestos.get(sesion["courseId"]) or {}
                    medio = next((m for m in curso.get("media") or [] if str(m.get("id")) == media_id), {})
                    archivos = sorted(k.split("/", 1)[1] for k in host.medios if k.startswith(media_id + "/") and not k.startswith(media_id + "/@"))
                    cuerpo = json.dumps({"mediaId": media_id, "entry": medio.get("entry"), "files": archivos}).encode()
                    return self._bytes("application/json; charset=utf-8", cuerpo)
                clave = f"{media_id}/{resto}" if resto else media_id
                medio = host.medios.get(clave)
                if medio is None:
                    return self._error(404, "media_session_not_found")
                return self._bytes(*medio)

        return Medios


if __name__ == "__main__":
    ruta = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.environ.get("TEMP", "."), "link-pruebas.json")
    ejemplo = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(__file__), "..", "..", "spec-driven", "02-classroom-engine", "example.json")
    with open(ejemplo, encoding="utf-8") as f:
        manifiesto = json.load(f)
    medios = {m["id"]: ("image/png", PNG_1x1) for m in manifiesto.get("media", []) if m.get("kind") == "image"}
    host = HostContenidoV2Pruebas(ruta, {manifiesto["id"]: manifiesto}, medios=medios).iniciar()
    print(f"API de Contenido v2 de pruebas en http://127.0.0.1:{host.puerto} (medios en {host.puerto_medios}) · link.json en {ruta}")
    print("set AVACOM_CONTENIDO_ENLACE_V2=" + ruta)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        host.detener()
