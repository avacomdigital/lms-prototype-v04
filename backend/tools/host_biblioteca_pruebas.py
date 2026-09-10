"""
Host de pruebas que imita a AVACOM Biblioteca en loopback.

Implementa el contrato 1 (salud, catalogo, cursos, curso, taxonomia, elemento,
mostrar) y las capacidades opcionales (medio, leccion, evaluacion, comprobar,
voz) sobre un catálogo en memoria. Escribe una nota de enlace en la ruta que se
le indique, para que el backend lo encuentre con AVACOM_CONTENIDO_ENLACE.

Uso en pruebas:

    host = HostBibliotecaPruebas(ruta_enlace)
    host.iniciar()
    ...
    host.detener()

Uso a mano (para probar el LMS sin la biblioteca real):

    python -m tools.host_biblioteca_pruebas %TEMP%\\enlace-pruebas.json
    set AVACOM_CONTENIDO_ENLACE=%TEMP%\\enlace-pruebas.json
"""
from __future__ import annotations

import json
import os
import secrets
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlparse

CONTRATO = 1

# Bytes «cifrados» de mentira: un PNG diminuto y un texto que hace de video.
PNG_1x1 = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000d4944415478da63f8ffff3f0300"
    "0501fe0d8d3d0e0000000049454e44ae426082"
)


def catalogo_por_defecto() -> dict:
    return {
        "cursos": [
            {
                "curso_ref": "co-secundaria-8-matematicas", "titulo": "Matemáticas · Grado 8", "version_vigente": "1",
                "pais": "CO", "nivel": "secundaria", "grado": "8", "asignatura": "Matemáticas", "idioma": "es",
                "lecciones": 1, "elementos": 5, "actualizado_en": 1757000000000,
            },
            {
                "curso_ref": "co-preescolar-transicion-exploracion", "titulo": "Exploración del medio · Transición",
                "version_vigente": "1", "pais": "CO", "nivel": "preescolar", "grado": "transicion",
                "asignatura": "Exploración del medio", "idioma": "es", "lecciones": 1, "elementos": 5,
                "actualizado_en": 1757000000000,
            },
        ],
        "secciones": {
            "co-secundaria-8-matematicas": [
                {
                    "codigo": "co-sec-mat-var-e1", "titulo": "Identifico relaciones entre propiedades de las gráficas",
                    "tipo": "estandar", "orden": 1,
                    "items": [
                        {"orden": 1, "tipo": "evaluacion", "elemento_ref": "co-sec-mat-eval-funcion",
                         "titulo": "Evaluación · Función lineal", "version": "1", "duracion_seg": None},
                        {"orden": 2, "tipo": "leccion", "elemento_ref": "co-sec-mat-lec-funcion",
                         "titulo": "Función lineal y razón de cambio", "version": "1", "duracion_seg": None},
                    ],
                },
                {
                    "codigo": "co-sec-mat-dba-8-05", "titulo": "Función lineal y su representación gráfica",
                    "tipo": "tema", "orden": 2,
                    "items": [
                        {"orden": 1, "tipo": "interactivo", "elemento_ref": "co-sec-mat-int-grafica",
                         "titulo": "Explorador de rectas", "version": "1", "duracion_seg": None},
                        {"orden": 2, "tipo": "documento", "elemento_ref": "co-sec-mat-doc-funcion",
                         "titulo": "La función lineal", "version": "1", "duracion_seg": None},
                    ],
                },
                {
                    "codigo": "co-sec-mat-dba-8-06", "titulo": "Pendiente y razón de cambio", "tipo": "tema", "orden": 3,
                    "items": [
                        {"orden": 1, "tipo": "video", "elemento_ref": "co-sec-mat-video-pendiente",
                         "titulo": "Qué significa la pendiente", "version": "1", "duracion_seg": 420},
                    ],
                },
            ],
            "co-preescolar-transicion-exploracion": [
                {
                    "codigo": "co-pre-exp-seres", "titulo": "Seres vivos de mi entorno", "tipo": "experiencia", "orden": 1,
                    "items": [
                        {"orden": 1, "tipo": "imagen", "elemento_ref": "co-pre-exp-img-granja",
                         "titulo": "Lámina de la granja", "version": "1", "duracion_seg": None},
                        {"orden": 2, "tipo": "imagen", "elemento_ref": "co-pre-exp-img-bosque",
                         "titulo": "Lámina del bosque", "version": "1", "duracion_seg": None},
                    ],
                },
            ],
        },
        "medios": {
            "co-pre-exp-img-granja": ("image/png", PNG_1x1),
            "co-pre-exp-img-bosque": ("image/png", PNG_1x1),
            "co-sec-mat-doc-funcion": ("application/pdf", b"%PDF-1.4\n% documento de prueba\n"),
            "co-sec-mat-video-pendiente": ("video/mp4", bytes(range(256)) * 400),
        },
        "interactivos": {
            "co-sec-mat-int-grafica": {
                "index.html": ("text/html; charset=utf-8", b"<html><body><h1>Explorador</h1><script src='app.js'></script></body></html>"),
                "app.js": ("text/javascript; charset=utf-8", b"console.log('hola')"),
            }
        },
        "lecciones": {
            "co-sec-mat-lec-funcion": {
                "titulo": "Función lineal y razón de cambio",
                "pasos": [
                    {"orden": 1, "elemento_ref": "co-sec-mat-doc-funcion", "titulo": "La función lineal", "tipo": "documento", "nota": "Lectura previa"},
                    {"orden": 2, "elemento_ref": "co-sec-mat-video-pendiente", "titulo": "Qué significa la pendiente", "tipo": "video", "nota": "Explicación"},
                    {"orden": 3, "elemento_ref": "co-sec-mat-int-grafica", "titulo": "Explorador de rectas", "tipo": "interactivo", "nota": "Exploración guiada"},
                    {"orden": 4, "elemento_ref": "co-sec-mat-eval-funcion", "titulo": "Evaluación · Función lineal", "tipo": "evaluacion", "nota": "Evaluación de cierre"},
                ],
            }
        },
        "evaluaciones": {
            "co-sec-mat-eval-funcion": {
                "titulo": "Evaluación · Función lineal", "tipo": "evaluacion", "version": "1",
                "preguntas": [
                    {"ref": "pr-001", "orden": 1, "tipo": "opcion_multiple", "enunciado": "¿Cuál es la pendiente de la recta y = 3x - 5?",
                     "peso": 1, "dificultad": "baja", "corregible": True, "voz": False,
                     "clave_respuesta": "3", "retro": "La pendiente es el número que multiplica a x."},
                    {"ref": "pr-002", "orden": 2, "tipo": "verdadero_falso", "enunciado": "Toda función lineal pasa por el origen",
                     "peso": 1, "dificultad": "media", "corregible": True, "voz": False,
                     "clave_respuesta": "falso", "retro": "Solo pasa por el origen cuando el corte con el eje y es cero"},
                    {"ref": "pr-003", "orden": 3, "tipo": "abierta", "enunciado": "Explica qué representa la pendiente",
                     "peso": 2, "dificultad": "alta", "corregible": False, "voz": False, "clave_respuesta": None, "retro": None},
                ],
            }
        },
    }


class HostBibliotecaPruebas:
    def __init__(self, ruta_enlace: str, catalogo: dict | None = None, capacidades: list[str] | None = None,
                 contrato: int = CONTRATO):
        self.ruta_enlace = ruta_enlace
        self.catalogo = catalogo or catalogo_por_defecto()
        self.capacidades = list(capacidades) if capacidades is not None else ["curso", "medio", "leccion", "evaluacion", "comprobar", "voz"]
        self.contrato = contrato
        self.ficha = secrets.token_hex(32)
        self.mostrados: list[str] = []
        self.peticiones: list[str] = []
        self._servidor: ThreadingHTTPServer | None = None
        self._hilo: threading.Thread | None = None

    # ------------------------------------------------------------ ciclo de vida
    def iniciar(self) -> "HostBibliotecaPruebas":
        host = self
        servidor = ThreadingHTTPServer(("127.0.0.1", 0), self._manejador())
        servidor.daemon_threads = True
        self._servidor = servidor
        self._hilo = threading.Thread(target=servidor.serve_forever, daemon=True)
        self._hilo.start()
        self.escribir_enlace()
        return host

    @property
    def puerto(self) -> int:
        return self._servidor.server_address[1] if self._servidor else 0

    def escribir_enlace(self, contrato: int | None = None) -> None:
        os.makedirs(os.path.dirname(self.ruta_enlace) or ".", exist_ok=True)
        with open(self.ruta_enlace, "w", encoding="utf-8") as archivo:
            json.dump({"Contrato": contrato if contrato is not None else self.contrato, "Puerto": self.puerto,
                       "Ficha": self.ficha, "Proceso": os.getpid()}, archivo)

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

    # ------------------------------------------------------------- catálogo
    def huella(self) -> str:
        import hashlib

        base = "|".join(sorted(c["curso_ref"] for c in self.catalogo["cursos"]))
        return hashlib.sha256(base.encode()).hexdigest()[:16]

    def _elemento(self, ref: str) -> dict | None:
        for curso_ref, secciones in self.catalogo["secciones"].items():
            for seccion in secciones:
                for item in seccion["items"]:
                    if item["elemento_ref"] == ref:
                        return {**item, "paquete": curso_ref, "taxonomia_ref": seccion["codigo"]}
        return None

    # ------------------------------------------------------------- servidor
    def _manejador(self):
        host = self

        class Manejador(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.0"

            def log_message(self, *args):  # silencio en pruebas
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

            def _bytes(self, tipo: str, datos: bytes) -> None:
                rango = self.headers.get("Range")
                desde, hasta = 0, len(datos) - 1
                parcial = False
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
                if self.headers.get("X-Avacom-Ficha") != host.ficha:
                    self._json(401, {"error": "ficha no valida"})
                    return False
                return True

            def do_HEAD(self):
                self.do_GET()

            def do_GET(self):
                if not self._autorizado():
                    return
                url = urlparse(self.path)
                camino = unquote(url.path)
                consulta = {k: v[0] for k, v in parse_qs(url.query).items()}
                host.peticiones.append(f"GET {camino}")
                partes = [p for p in camino.split("/") if p]

                if camino == "/v1/salud":
                    return self._json(200, {
                        "componente": "avacom-contenido", "contrato": host.contrato,
                        "elementos": sum(len(s["items"]) for ss in host.catalogo["secciones"].values() for s in ss),
                        "paquetes": len(host.catalogo["cursos"]), "politicas": 0,
                        "huella_catalogo": host.huella(), "cursos": len(host.catalogo["cursos"]),
                        "capacidades": host.capacidades,
                    })
                if camino == "/v1/cursos" and "curso" in host.capacidades:
                    return self._json(200, {"huella_catalogo": host.huella(), "cursos": host.catalogo["cursos"]})
                if len(partes) == 3 and partes[1] == "curso" and "curso" in host.capacidades:
                    ref = partes[2]
                    curso = next((c for c in host.catalogo["cursos"] if c["curso_ref"] == ref), None)
                    if not curso:
                        return self._json(404, {"error": "no hay ningun curso con esa referencia"})
                    return self._json(200, {
                        "curso_ref": ref, "titulo": curso["titulo"], "version": curso["version_vigente"],
                        "nivel": curso["nivel"], "grado": curso["grado"], "asignatura": curso["asignatura"],
                        "idioma": curso["idioma"], "huella": host.huella(), "secciones": host.catalogo["secciones"].get(ref, []),
                    })
                if camino == "/v1/catalogo":
                    elementos = []
                    for curso_ref, secciones in host.catalogo["secciones"].items():
                        for seccion in secciones:
                            for item in seccion["items"]:
                                if consulta.get("tipo") and item["tipo"] != consulta["tipo"]:
                                    continue
                                elementos.append({"ref": item["elemento_ref"], "tipo": item["tipo"], "titulo": item["titulo"],
                                                  "taxonomia_ref": seccion["codigo"], "version": item["version"],
                                                  "duracion_seg": item["duracion_seg"], "paquete": curso_ref})
                    return self._json(200, {"elementos": elementos})
                if camino == "/v1/taxonomia":
                    nodos = [{"ref": s["codigo"], "padre": None, "tipo": s["tipo"], "codigo": s["codigo"], "nombre": s["titulo"],
                              "orden": s["orden"], "pais": "CO", "nivel": None}
                             for ss in host.catalogo["secciones"].values() for s in ss]
                    return self._json(200, {"nodos": nodos if not consulta.get("padre") else []})
                if len(partes) == 3 and partes[1] == "elemento":
                    e = host._elemento(partes[2])
                    return self._json(200, {"ref": e["elemento_ref"], **e}) if e else self._json(404, {"error": "no esta en el indice"})
                if len(partes) >= 3 and partes[1] == "medio" and "medio" in host.capacidades:
                    ref = partes[2]
                    interno = "/".join(partes[3:])
                    if ref in host.catalogo["interactivos"]:
                        archivos = host.catalogo["interactivos"][ref]
                        nombre = interno or "index.html"
                        if nombre not in archivos:
                            return self._json(404, {"error": "no existe dentro del interactivo"})
                        return self._bytes(*archivos[nombre])
                    if ref in host.catalogo["medios"]:
                        return self._bytes(*host.catalogo["medios"][ref])
                    return self._json(404, {"error": "no esta en el indice"}) if not host._elemento(ref) else \
                        self._json(409, {"error": "este elemento es estructura, no tiene archivo"})
                if len(partes) == 3 and partes[1] == "leccion" and "leccion" in host.capacidades:
                    leccion = host.catalogo["lecciones"].get(partes[2])
                    if not leccion:
                        return self._json(404, {"error": "no esta en el indice"})
                    return self._json(200, {"elemento_ref": partes[2], **leccion})
                if len(partes) == 3 and partes[1] == "evaluacion" and "evaluacion" in host.capacidades:
                    ev = host.catalogo["evaluaciones"].get(partes[2])
                    if not ev:
                        return self._json(404, {"error": "no esta en el indice"})
                    return self._json(200, {
                        "elemento_ref": partes[2], "titulo": ev["titulo"], "tipo": ev["tipo"], "version": ev["version"],
                        "preguntas": [{k: v for k, v in p.items() if k not in ("clave_respuesta", "retro")} for p in ev["preguntas"]],
                    })
                if len(partes) >= 3 and partes[1] == "voz" and "voz" in host.capacidades:
                    return self._bytes("audio/wav", b"RIFF" + bytes(44))
                return self._json(404, {"error": "no existe ese punto de enlace"})

            def do_POST(self):
                if not self._autorizado():
                    return
                largo = int(self.headers.get("Content-Length") or 0)
                cuerpo = json.loads(self.rfile.read(largo) or b"{}") if largo else {}
                camino = unquote(urlparse(self.path).path)
                host.peticiones.append(f"POST {camino}")
                if camino == "/v1/mostrar":
                    ref = cuerpo.get("elemento_ref")
                    if not ref:
                        return self._json(400, {"error": "falta elemento_ref"})
                    if not host._elemento(ref):
                        return self._json(409, {"aceptado": False, "motivo": "Ese material no esta instalado en este equipo."})
                    host.mostrados.append(ref)
                    return self._json(200, {"aceptado": True})
                if camino == "/v1/comprobar" and "comprobar" in host.capacidades:
                    ev = host.catalogo["evaluaciones"].get(cuerpo.get("elemento_ref", ""))
                    pregunta = next((p for p in (ev or {}).get("preguntas", []) if p["ref"] == cuerpo.get("pregunta_ref")), None)
                    if not pregunta:
                        return self._json(404, {"error": "no existe esa pregunta"})
                    clave = pregunta.get("clave_respuesta")
                    if clave is None:
                        return self._json(409, {"error": "pregunta abierta: la califica el docente"})
                    acierta = str(cuerpo.get("respuesta", "")).strip().lower() == clave.strip().lower()
                    return self._json(200, {"acierta": acierta, "retroalimentacion": pregunta.get("retro") if acierta else None})
                return self._json(404, {"error": "no existe ese punto de enlace"})

        return Manejador


if __name__ == "__main__":
    ruta = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.environ.get("TEMP", "."), "enlace-pruebas.json")
    host = HostBibliotecaPruebas(ruta).iniciar()
    print(f"Host de pruebas escuchando en http://127.0.0.1:{host.puerto} · nota en {ruta}")
    print("set AVACOM_CONTENIDO_ENLACE=" + ruta)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        host.detener()
