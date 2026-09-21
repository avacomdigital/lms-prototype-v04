"""
Cliente de la **API de Contenido v2** de AVACOM Biblioteca (la que entrega el curso
con el esquema 1.0 recortado, califica respuestas y sirve los medios del paquete).

Convive con `cliente.py` (contrato 1, `enlace.json`, `X-Avacom-Ficha`), que sigue
alimentando `/api/biblioteca/*` y el flujo de intentos del expediente. Este módulo es
el ÚNICO sitio del LMS que habla el v2; MOD-007 lo usa a través de
`classroom_engine.infraestructura.fuente_biblioteca`.

Reglas del documento «Mapeo de campos · API de Contenido v2» que aquí se cumplen:

  - `link.json` se relee EN CADA petición: `apiPort` y `token` cambian en cada
    arranque de la biblioteca y no se guardan entre llamadas.
  - Un 401 reintenta UNA vez tras releer `link.json`; el segundo 401 es error.
  - La ausencia de `link.json` produce «sin contenido» (BibliotecaNoDisponible →
    503 con motivo y sugerencia), no un error.
  - `POST /v2/evaluate` viaja siempre con `version`.
  - Nada se cachea: ni el curso, ni el `token`, ni las URL de medios.

Supuestos por confirmar contra `contracts/openapi.v2.json` (documentados en
spec-driven/02-classroom-engine/05-contrato-biblioteca.md §8):
  A-1  el token viaja como `Authorization: Bearer <token>`;
  A-2  la lista de cursos instalados es `GET /v2/courses`;
  A-3  los bytes de un medio son `GET /v2/courses/{courseId}/media/{mediaId}[/ruta]`;
  A-4  `link.json` vive junto a `enlace.json` (`%ProgramData%\\AVACOM\\contenido\\link.json`);
  A-5  los errores llegan como `{"error": {"code", "message"}}` (se aceptan variantes planas).
"""
from __future__ import annotations

import hashlib
import json
import os
import urllib.error
import urllib.parse
import urllib.request

from django.conf import settings

from .cliente import SUGERENCIA_ABRIR, BibliotecaError, BibliotecaNoDisponible

API = "v2"

# ------------------------------------------------------------------ rutas
RUTA_SALUD = "/v2/health"
RUTA_CURSOS = "/v2/courses"                                                   # A-2
RUTA_CURSO = "/v2/courses/{curso}"
RUTA_GUIA = "/v2/courses/{curso}/questions/{pregunta}/grading-guide"
RUTA_EVALUAR = "/v2/evaluate"
RUTA_EVALUAR_LOTE = "/v2/evaluate/batch"
RUTA_MEDIO = "/v2/courses/{curso}/media/{medio}"                               # A-3

LOTE_MAXIMO = 200          # «hasta 200 respuestas dentro de items»

# Enumeraciones del contrato. Si llega un valor fuera de estas listas, el contrato subió
# de versión: el LMS lo MUESTRA con rótulo genérico, no lo descarta (§9 del mapeo).
MODOS = ("simple", "class", "exam", "review", "free_learning")
PERFILES = ("student", "teacher")
CODIGOS_ERROR = (
    "unauthorized", "not_found", "course_not_found", "lesson_not_found",
    "disabled_by_policy", "index_rebuilding", "invalid_parameter", "invalid_response",
)

SUGERENCIA_SIN_CONTENIDO = SUGERENCIA_ABRIR


# ------------------------------------------------------------ descubrimiento

def ruta_enlace() -> str:
    """Dónde está `link.json`. Se fuerza con AVACOM_CONTENIDO_ENLACE_V2 (setting o
    variable de entorno) para probar contra el host de pruebas sin instalar nada."""
    forzada = getattr(settings, "AVACOM_CONTENIDO_ENLACE_V2", None) or os.environ.get("AVACOM_CONTENIDO_ENLACE_V2")
    if forzada:
        return forzada
    base = os.environ.get("ProgramData") or os.environ.get("PROGRAMDATA") or r"C:\ProgramData"
    return os.path.join(base, "AVACOM", "contenido", "link.json")                # A-4


def _clave(nota: dict, *nombres):
    """Acepta camelCase, minúsculas y PascalCase: el LMS no se ata a la serialización."""
    for nombre in nombres:
        for candidata in (nombre, nombre.lower(), nombre[:1].upper() + nombre[1:]):
            if candidata in nota:
                return nota[candidata]
    return None


def leer_enlace() -> dict:
    """Lee `link.json` EN CADA llamada. Devuelve {puerto, token, proceso, api}.

    Sin archivo, ilegible o incompleto → BibliotecaNoDisponible: es «sin contenido»,
    el estado normal de un aula con la biblioteca cerrada."""
    ruta = ruta_enlace()
    if not os.path.exists(ruta):
        raise BibliotecaNoDisponible(
            "AVACOM Biblioteca no está encendida en este equipo (no hay link.json): sin contenido.",
            sugerencia=SUGERENCIA_SIN_CONTENIDO,
        )
    try:
        with open(ruta, encoding="utf-8") as archivo:
            nota = json.load(archivo)
    except (OSError, json.JSONDecodeError) as error:
        raise BibliotecaNoDisponible(f"link.json no se pudo leer: {error}") from error
    if not isinstance(nota, dict):
        raise BibliotecaNoDisponible("link.json no tiene la forma esperada.")

    puerto = _clave(nota, "apiPort", "port", "puerto")
    token = _clave(nota, "token")
    proceso = _clave(nota, "pid", "processId", "proceso")
    api = _clave(nota, "apiVersion", "version", "api")
    if isinstance(puerto, str) and puerto.isdigit():
        puerto = int(puerto)
    if not isinstance(puerto, int) or not isinstance(token, str) or not token:
        raise BibliotecaNoDisponible("link.json está incompleto (faltan apiPort o token).")
    return {"puerto": puerto, "token": token, "proceso": proceso if isinstance(proceso, int) else None,
            "api": str(api) if api is not None else None}


# ---------------------------------------------------------------- transporte

# Sin proxy: es loopback y un proxy del sistema desviaría 127.0.0.1 a ningún sitio.
_abridor = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def _tiempo_espera() -> float:
    return float(getattr(settings, "AVACOM_CONTENIDO_TIEMPO_ESPERA_SEG", 3))


def _detalle_de_error(error: urllib.error.HTTPError) -> tuple[str, str]:
    """(codigo, mensaje) del cuerpo de error. Acepta `{"error": {"code", "message"}}`,
    `{"code", "message"}`, `{"error": "code", "detail": "..."}` y texto plano (A-5)."""
    try:
        texto = error.read().decode("utf-8", errors="replace")[:600]
    except OSError:
        texto = ""
    codigo, mensaje = "", ""
    try:
        datos = json.loads(texto) if texto else {}
    except json.JSONDecodeError:
        datos = {}
    if isinstance(datos, dict):
        anidado = datos.get("error")
        if isinstance(anidado, dict):
            codigo = str(anidado.get("code") or anidado.get("codigo") or "")
            mensaje = str(anidado.get("message") or anidado.get("detail") or anidado.get("mensaje") or "")
        else:
            codigo = str(datos.get("code") or datos.get("codigo") or (anidado if isinstance(anidado, str) else "") or "")
            mensaje = str(datos.get("message") or datos.get("detail") or datos.get("motivo") or "")
    if not mensaje:
        mensaje = texto or str(error.reason) or f"HTTP {error.code}"
    if not codigo and error.code == 401:
        codigo = "unauthorized"
    return codigo, mensaje


def _pedir(metodo: str, camino: str, consulta: dict | None = None, cuerpo: dict | None = None,
           cabeceras: dict | None = None, crudo: bool = False, reintentar: bool = True):
    """La única función que abre un socket hacia la API v2.

    Devuelve el JSON decodificado o, con `crudo=True`, la respuesta HTTP abierta (quien
    la pide la cierra). Traduce el transporte a BibliotecaNoDisponible y los HTTP de
    error a BibliotecaError(estado, detalle, codigo=<código del contrato>)."""
    nota = leer_enlace()
    filtros = {k: v for k, v in (consulta or {}).items() if v not in (None, "")}
    url = f"http://127.0.0.1:{nota['puerto']}{camino}"
    if filtros:
        url += "?" + urllib.parse.urlencode(filtros)

    datos = None
    encabezados = {"Authorization": f"Bearer {nota['token']}", "Accept": "application/json, */*"}   # A-1
    if cuerpo is not None:
        datos = json.dumps(cuerpo, ensure_ascii=False).encode("utf-8")
        encabezados["Content-Type"] = "application/json; charset=utf-8"
    encabezados.update(cabeceras or {})

    peticion = urllib.request.Request(url, data=datos, headers=encabezados, method=metodo)
    try:
        respuesta = _abridor.open(peticion, timeout=_tiempo_espera())
    except urllib.error.HTTPError as error:
        codigo, detalle = _detalle_de_error(error)
        if error.code == 401 and reintentar:
            # El token cambió (la biblioteca se reinició): releer link.json y reintentar UNA vez.
            return _pedir(metodo, camino, consulta, cuerpo, cabeceras, crudo, reintentar=False)
        raise BibliotecaError(error.code, detalle, codigo=codigo or _codigo_por_estado(error.code)) from error
    except urllib.error.URLError as error:
        raise BibliotecaNoDisponible(
            "link.json apunta a un puerto donde nadie escucha: la biblioteca se cerró."
        ) from error
    except (TimeoutError, ConnectionError, OSError) as error:
        raise BibliotecaNoDisponible(f"La biblioteca no contestó a tiempo ({error}).") from error

    if crudo:
        return respuesta
    try:
        with respuesta:
            texto = respuesta.read().decode("utf-8")
            return json.loads(texto) if texto.strip() else {}
    except (json.JSONDecodeError, UnicodeDecodeError, OSError) as error:
        raise BibliotecaError(502, f"La biblioteca contestó algo que no es JSON ({error}).", codigo="invalid_response") from error


def _codigo_por_estado(estado: int) -> str:
    return {401: "unauthorized", 404: "not_found", 400: "invalid_parameter", 503: "index_rebuilding"}.get(estado, "")


def _ref(valor: str) -> str:
    return urllib.parse.quote(str(valor), safe="")


def _lista(respuesta, *claves) -> list:
    if isinstance(respuesta, list):
        return respuesta
    if isinstance(respuesta, dict):
        for clave in claves:
            if isinstance(respuesta.get(clave), list):
                return respuesta[clave]
    return []


# ------------------------------------------------------------------ contrato

def salud() -> dict:
    """`GET /v2/health`. Trae `installedCourses`, la señal de cambio del catálogo."""
    return _pedir("GET", RUTA_SALUD)


def cursos_instalados(datos_salud: dict | None = None) -> list[dict]:
    datos = datos_salud if datos_salud is not None else salud()
    instalados = datos.get("installedCourses")
    if isinstance(instalados, int):
        return []
    salida = []
    for c in instalados or []:
        if isinstance(c, dict):
            salida.append({"curso_ref": str(c.get("courseId") or c.get("id") or ""), "version": str(c.get("version") or ""),
                           "titulo": c.get("title")})
        elif isinstance(c, str):
            salida.append({"curso_ref": c, "version": "", "titulo": None})
    return salida


def huella(datos_salud: dict) -> str:
    """Resumen de `installedCourses`: cambia cuando cambia lo instalado. Es lo único que
    tendría sentido comparar si algún día hubiera una caché en memoria (no la hay)."""
    base = "|".join(sorted(f"{c['curso_ref']}@{c['version']}" for c in cursos_instalados(datos_salud)))
    return "v2-" + hashlib.sha256(base.encode("utf-8")).hexdigest()[:16] if base else "v2-vacio"


def cursos() -> list[dict]:
    """Los cursos instalados y ofrecidos a este equipo (A-2). Cada entrada puede ser el
    curso completo o una ficha `{courseId, version, title…}`; quien la consume decide si
    baja el curso completo."""
    return [c for c in _lista(_pedir("GET", RUTA_CURSOS), "courses", "items", "installedCourses") if isinstance(c, dict)]


def curso(curso_ref: str, *, version: str | None = None, modo: str | None = None, perfil: str | None = None) -> dict:
    """`GET /v2/courses/{courseId}?version=&mode=&profile=`: el curso recortado (sin claves).

    `version` pide una versión archivada (reconstruir un intento viejo); sin ella, la
    instalada. `mode` filtra por modo de uso; `profile=student` recorta `teacherNotes`."""
    datos = _pedir("GET", RUTA_CURSO.format(curso=_ref(curso_ref)), consulta={"version": version, "mode": modo, "profile": perfil})
    if isinstance(datos, dict) and "id" not in datos and datos.get("courseId"):
        datos["id"] = datos["courseId"]
    return datos


def guia_calificacion(curso_ref: str, pregunta_ref: str) -> dict:
    """`GET …/questions/{questionId}/grading-guide`: rúbrica y respuesta modelo de una
    pregunta abierta. Sólo para calificar A MANO (MOD-011): el aula no la expone."""
    return _pedir("GET", RUTA_GUIA.format(curso=_ref(curso_ref), pregunta=_ref(pregunta_ref)))


def evaluar(curso_ref: str, version: str, objeto_ref: str, pregunta_ref: str, respuesta: dict) -> dict:
    """`POST /v2/evaluate`. La clave se compara donde vive; aquí sólo vuelve el veredicto.
    `version` se manda SIEMPRE para que un intento se califique con las claves con las que se hizo."""
    if not version:
        raise ValueError("evaluar() exige la versión del curso (regla del contrato: mándenla siempre).")
    return _pedir("POST", RUTA_EVALUAR, cuerpo={
        "courseId": curso_ref, "version": version, "objectId": objeto_ref, "questionId": pregunta_ref, "response": respuesta,
    })


def evaluar_lote(items: list[dict]) -> list[dict]:
    """`POST /v2/evaluate/batch` con hasta 200 respuestas por llamada; más de 200 se trocean."""
    salida: list[dict] = []
    for inicio in range(0, len(items), LOTE_MAXIMO):
        trozo = items[inicio:inicio + LOTE_MAXIMO]
        for item in trozo:
            if not item.get("version"):
                raise ValueError("Cada respuesta del lote exige la versión del curso.")
        datos = _pedir("POST", RUTA_EVALUAR_LOTE, cuerpo={"items": trozo})
        salida.extend(x for x in _lista(datos, "items", "results", "evaluations") if isinstance(x, dict))
    return salida


def abrir_medio(curso_ref: str, media_ref: str, ruta_interna: str | None = None, rango: str | None = None, metodo: str = "GET"):
    """Bytes de un medio del paquete (A-3), en paso a través: respuesta HTTP cruda con
    Content-Type, Content-Length y Content-Range. Quien la pide la cierra. Si la biblioteca
    responde con una URL temporal (redirección), urllib la sigue dentro del loopback."""
    camino = RUTA_MEDIO.format(curso=_ref(curso_ref), medio=_ref(media_ref))
    if ruta_interna:
        camino += "/" + urllib.parse.quote(ruta_interna.strip("/"), safe="/")
    cabeceras = {"Range": rango} if rango else None
    return _pedir(metodo, camino, cabeceras=cabeceras, crudo=True)


# -------------------------------------------------------------------- estado

def estado() -> dict:
    """NUNCA lanza. `disponible=False` con motivo y sugerencia cuando no hay contenido."""
    salida = {
        "api": API, "disponible": False, "motivo": "", "sugerencia": None, "puerto": None, "proceso": None,
        "huella": "", "cursos_instalados": [], "reconstruyendo_indice": False,
    }
    try:
        nota = leer_enlace()
    except BibliotecaNoDisponible as error:
        salida.update(motivo=error.motivo, sugerencia=error.sugerencia)
        return salida
    salida.update(puerto=nota["puerto"], proceso=nota["proceso"])
    try:
        datos = salud()
    except BibliotecaNoDisponible as error:
        salida.update(motivo=error.motivo, sugerencia=error.sugerencia)
        return salida
    except BibliotecaError as error:
        if error.codigo == "index_rebuilding" or error.estado == 503:
            salida.update(reconstruyendo_indice=True, motivo="La biblioteca está reconstruyendo su índice.",
                          sugerencia="Vuelve a intentarlo en unos segundos.")
        else:
            salida.update(motivo=f"La biblioteca respondió {error.estado}: {error.detalle}", sugerencia=SUGERENCIA_ABRIR)
        return salida
    salida.update(disponible=True, huella=huella(datos), cursos_instalados=cursos_instalados(datos),
                  reconstruyendo_indice=bool(datos.get("indexRebuilding")))
    return salida
