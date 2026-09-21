"""
Host de pruebas que imita la **API de Contenido v2** de AVACOM Biblioteca en loopback,
tal como la describe «Mapeo de campos · API de Contenido v2»:

  GET  /v2/health                                         → {status, apiVersion, installedCourses[]}
  GET  /v2/courses                                        → {courses:[fichas]}
  GET  /v2/courses/{courseId}?version=&mode=&profile=     → el curso RECORTADO (sin claves; sin teacherNotes con profile=student)
  GET  /v2/courses/{courseId}/questions/{qid}/grading-guide
  POST /v2/evaluate · POST /v2/evaluate/batch (≤ 200)     → veredicto calculado con las claves del manifiesto completo
  GET  /v2/courses/{courseId}/media/{mediaId}[/ruta]      → bytes, con Range

Autenticación: `Authorization: Bearer <token>`; sin él o con otro, 401 `unauthorized`.
Escribe `link.json` ({apiPort, token, pid}) donde se le indique, para que el backend lo
encuentre con AVACOM_CONTENIDO_ENLACE_V2. `rechazar_proximas = n` fuerza n respuestas 401
seguidas (para probar el reintento único); `reconstruyendo = True` responde 503
`index_rebuilding`; `desactivados` responde 403 `disabled_by_policy`.

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
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlparse

# Lo que la API recorta antes de entregar una pregunta (§1 del mapeo).
CLAVES_RECORTADAS = frozenset({
    "answer", "acceptedAnswers", "wrongAnswers", "numericTolerance", "pairs", "wrongPairs", "correctOrder", "wrongOrders",
    "modelAnswer", "rubric", "incorrectExamples", "feedback", "isCorrect",
})
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


def barajar(curso: dict) -> dict:
    """Las opciones, parejas y elementos llegan en otro orden en cada llamada: aquí, rotados
    una posición, para que una prueba que guarde posiciones en vez de `id` falle."""
    for leccion in curso.get("lessons") or []:
        for objeto in leccion.get("objects") or []:
            for pregunta in objeto.get("questions") or []:
                for clave in ("options", "right", "items"):
                    lista = pregunta.get(clave)
                    if isinstance(lista, list) and len(lista) > 1:
                        pregunta[clave] = lista[1:] + lista[:1]
    return curso


def filtrar_modo(curso: dict, modo: str | None) -> dict:
    if not modo:
        return curso
    for leccion in curso.get("lessons") or []:
        leccion["objects"] = [o for o in (leccion.get("objects") or []) if not o.get("modes") or modo in o["modes"]]
    return curso


# ------------------------------------------------------------------ calificar

def _decimal(x) -> float:
    return round(float(x), 4)


def calificar(pregunta: dict, respuesta: dict) -> dict:
    """El veredicto con las claves del manifiesto completo. Devuelve la forma del contrato."""
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
            raise ValueError("selectedOptionIds")
        opciones = {o["id"]: o for o in pregunta.get("options") or []}
        if any(e not in opciones for e in elegidas):
            raise ValueError("selectedOptionIds desconocidas")
        correctas = {k for k, o in opciones.items() if o.get("isCorrect")}
        aciertos = len(correctas & set(elegidas))
        fallos = len(set(elegidas) - correctas)
        extra = [opciones[e]["feedback"] for e in elegidas if e not in correctas and opciones[e].get("feedback")]
        return cerrar((aciertos - fallos) / max(1, len(correctas)), extra)
    if tipo == "true_false":
        valor = respuesta.get("value")
        if not isinstance(valor, bool):
            raise ValueError("value")
        return cerrar(1.0 if valor == pregunta.get("answer") else 0.0)
    if tipo == "fill_blanks":
        huecos = respuesta.get("blanks")
        if not isinstance(huecos, dict):
            raise ValueError("blanks")
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
            raise ValueError("pairs")
        esperadas = {(p["leftId"], p["rightId"]) for p in pregunta.get("pairs") or []}
        dadas = {(p.get("leftId"), p.get("rightId")) for p in parejas if isinstance(p, dict)}
        return cerrar(len(esperadas & dadas) / max(1, len(esperadas)))
    if tipo == "ordering":
        orden = respuesta.get("order")
        if not isinstance(orden, list):
            raise ValueError("order")
        extra = [w["feedback"] for w in (pregunta.get("wrongOrders") or []) if w.get("order") == orden and w.get("feedback")]
        return cerrar(1.0 if orden == pregunta.get("correctOrder") else 0.0, extra)
    if tipo == "open":
        if not any(respuesta.get(k) for k in ("text", "drawingRef", "audioRef")):
            raise ValueError("text|drawingRef|audioRef")
        return {**base, "score": None, "correct": None, "requiresManualGrading": True, "feedback": []}
    raise LookupError(tipo)


class HostContenidoV2Pruebas:
    def __init__(self, ruta_enlace: str, manifiestos: dict[str, dict], archivados: dict[tuple[str, str], dict] | None = None,
                 medios: dict[str, tuple[str, bytes]] | None = None, desactivados: set[str] | None = None):
        self.ruta_enlace = ruta_enlace
        self.manifiestos = dict(manifiestos)                    # courseId → manifiesto COMPLETO (con claves) de la versión instalada
        self.archivados = dict(archivados or {})                # (courseId, version) → manifiesto de una versión archivada
        self.medios = dict(medios or {})                        # mediaId o "mediaId/ruta" → (Content-Type, bytes)
        self.desactivados = set(desactivados or ())
        self.token = secrets.token_urlsafe(32)
        self.reconstruyendo = False
        self.rechazar_proximas = 0
        self.peticiones: list[str] = []
        self.consultas: list[dict] = []
        self.cuerpos: list[dict] = []
        self._servidor: ThreadingHTTPServer | None = None

    # ------------------------------------------------------------ ciclo de vida
    def iniciar(self) -> "HostContenidoV2Pruebas":
        servidor = ThreadingHTTPServer(("127.0.0.1", 0), self._manejador())
        servidor.daemon_threads = True
        self._servidor = servidor
        threading.Thread(target=servidor.serve_forever, daemon=True).start()
        self.escribir_enlace()
        return self

    @property
    def puerto(self) -> int:
        return self._servidor.server_address[1] if self._servidor else 0

    def escribir_enlace(self) -> None:
        os.makedirs(os.path.dirname(self.ruta_enlace) or ".", exist_ok=True)
        with open(self.ruta_enlace, "w", encoding="utf-8") as archivo:
            json.dump({"apiVersion": "v2", "apiPort": self.puerto, "token": self.token, "pid": os.getpid()}, archivo)

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
        if self._servidor:
            self._servidor.shutdown()
            self._servidor.server_close()
            self._servidor = None
        self.borrar_enlace()

    # ----------------------------------------------------------------- datos
    def _curso(self, ref: str, version: str | None) -> dict | None:
        if version and version != str(self.manifiestos.get(ref, {}).get("version", "")):
            return self.archivados.get((ref, version))
        return self.manifiestos.get(ref)

    @staticmethod
    def _ficha(m: dict) -> dict:
        c = m.get("classification") or {}
        return {"courseId": m.get("id"), "version": m.get("version"), "title": m.get("title"), "subtitle": m.get("subtitle"),
                "language": m.get("language"), "subject": (c.get("subject") or {}).get("name"), "lessonCount": len(m.get("lessons") or [])}

    @staticmethod
    def _pregunta(curso: dict, objeto_ref: str, pregunta_ref: str) -> dict | None:
        for l in curso.get("lessons") or []:
            for o in l.get("objects") or []:
                if str(o.get("id")) == objeto_ref:
                    for q in o.get("questions") or []:
                        if str(q.get("id")) == pregunta_ref:
                            return q
        return None

    # -------------------------------------------------------------- servidor
    def _manejador(self):
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
                self._json(estado, {"error": {"code": codigo, "message": mensaje}})

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

            def _autorizado(self) -> bool:
                if host.rechazar_proximas > 0:
                    host.rechazar_proximas -= 1
                    self._error(401, "unauthorized", "token caducado")
                    return False
                if self.headers.get("Authorization") != f"Bearer {host.token}":
                    self._error(401, "unauthorized", "token no valido")
                    return False
                return True

            def _entrada(self):
                url = urlparse(self.path)
                camino = unquote(url.path)
                consulta = {k: v[0] for k, v in parse_qs(url.query).items()}
                host.peticiones.append(f"{self.command} {camino}")
                host.consultas.append(consulta)
                return camino, consulta, [p for p in camino.split("/") if p]

            def do_HEAD(self):
                self.do_GET()

            def do_GET(self):
                camino, consulta, partes = self._entrada()
                if not self._autorizado():
                    return
                if host.reconstruyendo:
                    return self._error(503, "index_rebuilding", "el indice se esta reconstruyendo")

                if camino == "/v2/health":
                    return self._json(200, {"status": "ok", "apiVersion": "2", "indexRebuilding": False,
                                            "installedCourses": [{"courseId": m.get("id"), "version": m.get("version"), "title": m.get("title")}
                                                                 for ref, m in host.manifiestos.items() if ref not in host.desactivados]})
                if camino == "/v2/courses":
                    return self._json(200, {"courses": [host._ficha(m) for ref, m in host.manifiestos.items() if ref not in host.desactivados]})
                if len(partes) >= 3 and partes[0] == "v2" and partes[1] == "courses":
                    ref = partes[2]
                    if ref in host.desactivados:
                        return self._error(403, "disabled_by_policy", "la politica del colegio desactivo este curso")
                    if len(partes) == 3:
                        modo, perfil = consulta.get("mode"), consulta.get("profile") or "student"
                        if modo and modo not in ("simple", "class", "exam", "review", "free_learning"):
                            return self._error(400, "invalid_parameter", f"mode «{modo}» no existe")
                        curso = host._curso(ref, consulta.get("version"))
                        if curso is None:
                            return self._error(404, "course_not_found", "no hay ningun curso con esa referencia y version")
                        return self._json(200, barajar(filtrar_modo(recortar(copy.deepcopy(curso), perfil=perfil), modo)))
                    if len(partes) == 6 and partes[3] == "questions" and partes[5] == "grading-guide":
                        curso = host._curso(ref, consulta.get("version"))
                        pregunta = None
                        for l in (curso or {}).get("lessons") or []:
                            for o in l.get("objects") or []:
                                pregunta = pregunta or next((q for q in o.get("questions") or [] if str(q.get("id")) == partes[4]), None)
                        if not pregunta:
                            return self._error(404, "not_found", "no existe esa pregunta")
                        return self._json(200, {"questionId": pregunta["id"], "type": pregunta.get("type"), "modelAnswer": pregunta.get("modelAnswer"),
                                                "rubric": pregunta.get("rubric") or [], "incorrectExamples": pregunta.get("incorrectExamples") or []})
                    if len(partes) >= 5 and partes[3] == "media":
                        if ref not in host.manifiestos:
                            return self._error(404, "course_not_found", "no hay ningun curso con esa referencia")
                        clave = partes[4] + ("/" + "/".join(partes[5:]) if len(partes) > 5 else "")
                        medio = host.medios.get(clave)
                        if medio is None:
                            return self._error(404, "not_found", "ese medio no esta en el paquete")
                        return self._bytes(*medio)
                return self._error(404, "not_found", "no existe ese punto de enlace")

            def do_POST(self):
                camino, _, _ = self._entrada()
                if not self._autorizado():
                    return
                largo = int(self.headers.get("Content-Length") or 0)
                cuerpo = json.loads(self.rfile.read(largo) or b"{}") if largo else {}
                host.cuerpos.append(cuerpo)
                if host.reconstruyendo:
                    return self._error(503, "index_rebuilding", "el indice se esta reconstruyendo")

                if camino == "/v2/evaluate":
                    try:
                        return self._json(200, self._evaluar(cuerpo))
                    except LookupError as e:
                        return self._error(404, "not_found", str(e))
                    except ValueError as e:
                        return self._error(400, "invalid_parameter", f"response mal formada: {e}")
                if camino == "/v2/evaluate/batch":
                    items = cuerpo.get("items")
                    if not isinstance(items, list) or len(items) > LOTE_MAXIMO:
                        return self._error(400, "invalid_parameter", f"items debe ser una lista de hasta {LOTE_MAXIMO}")
                    try:
                        return self._json(200, {"items": [self._evaluar(i) for i in items]})
                    except LookupError as e:
                        return self._error(404, "not_found", str(e))
                    except ValueError as e:
                        return self._error(400, "invalid_parameter", f"response mal formada: {e}")
                return self._error(404, "not_found", "no existe ese punto de enlace")

            def _evaluar(self, cuerpo: dict) -> dict:
                ref = str(cuerpo.get("courseId") or "")
                curso = host._curso(ref, cuerpo.get("version"))
                if curso is None:
                    raise LookupError("course_not_found")
                pregunta = host._pregunta(curso, str(cuerpo.get("objectId") or ""), str(cuerpo.get("questionId") or ""))
                if pregunta is None:
                    raise LookupError("no existe esa pregunta en ese objeto")
                respuesta = cuerpo.get("response")
                if not isinstance(respuesta, dict):
                    raise ValueError("response")
                return calificar(pregunta, respuesta)

        return Manejador


if __name__ == "__main__":
    ruta = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.environ.get("TEMP", "."), "link-pruebas.json")
    ejemplo = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(__file__), "..", "..", "spec-driven", "02-classroom-engine", "example.json")
    with open(ejemplo, encoding="utf-8") as f:
        manifiesto = json.load(f)
    medios = {m["id"]: ("image/png", PNG_1x1) for m in manifiesto.get("media", []) if m.get("kind") == "image"}
    host = HostContenidoV2Pruebas(ruta, {manifiesto["id"]: manifiesto}, medios=medios).iniciar()
    print(f"API de Contenido v2 de pruebas en http://127.0.0.1:{host.puerto} · link.json en {ruta}")
    print("set AVACOM_CONTENIDO_ENLACE_V2=" + ruta)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        host.detener()
