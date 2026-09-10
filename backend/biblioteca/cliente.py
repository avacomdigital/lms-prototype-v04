"""
ÚNICO cliente del LMS hacia AVACOM Biblioteca (componente `avacom-contenido`).

Regla estructural: si aparece otro `urlopen`/`HttpClient` en el LMS apuntando a
127.0.0.1, está mal. El descubrimiento del puerto, la ficha, el tiempo de espera,
la revalidación por capacidades y el manejo de «no hay contenido» se escriben
una sola vez, aquí.

Topología:

    Tableta / OPS Master ──HTTP LAN :8000──► este backend ──loopback, puerto efímero──► Biblioteca
                                                            X-Avacom-Ficha

Tres decisiones que se replican tal cual de la línea base:
  1. El puerto no se fija nunca: se lee de la nota de enlace EN CADA petición.
  2. La nota no se cachea: guardarla en memoria es seguir hablando con un puerto muerto.
  3. La ausencia de la biblioteca no es un error: produce degradación (503), no un 500.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

from django.conf import settings

CONTRATO_SOPORTADO = 1

# Rutas que la biblioteca publica desde el contrato 1 y que NO dependen de
# `capacidades`. Todo lo demás se protege con `_exigir`.
RUTAS_SIN_CAPACIDAD = ("salud", "catalogo", "taxonomia", "elemento", "mostrar")

# Capacidades opcionales y la ruta que habilitan.
CAPACIDAD_CURSO = "curso"            # GET /v1/cursos, GET /v1/curso/{ref}
CAPACIDAD_MEDIO = "medio"            # GET /v1/medio/{ref}[/ruta-interna]
CAPACIDAD_LECCION = "leccion"        # GET /v1/leccion/{ref}
CAPACIDAD_EVALUACION = "evaluacion"  # GET /v1/evaluacion/{ref}
CAPACIDAD_COMPROBAR = "comprobar"    # POST /v1/comprobar
CAPACIDAD_VOZ = "voz"                # GET /v1/voz/{ref}[/pregunta_ref]

SUGERENCIA_ABRIR = (
    "Abre AVACOM Biblioteca en el equipo maestro y entra en la pestaña "
    "«Contenido AVACOM» con la licencia cargada."
)


class BibliotecaNoDisponible(Exception):
    """La biblioteca no está: nota ausente, puerto muerto, sin respuesta a tiempo.

    Es un estado NORMAL del aula. Hacia arriba se traduce en 503 con motivo y
    sugerencia; nunca en una pantalla en blanco.
    """

    def __init__(self, motivo: str, sugerencia: str | None = SUGERENCIA_ABRIR):
        super().__init__(motivo)
        self.motivo = motivo
        self.sugerencia = sugerencia


class BibliotecaError(Exception):
    """La biblioteca contestó, pero con error. Lleva el código HTTP y el detalle."""

    def __init__(self, estado: int, detalle: str, capacidades: list[str] | None = None):
        super().__init__(f"{estado}: {detalle}")
        self.estado = estado
        self.detalle = detalle
        self.capacidades = capacidades or []


# ------------------------------------------------------------ descubrimiento

def ruta_enlace() -> str:
    """Dónde está la nota de enlace. Se puede forzar con AVACOM_CONTENIDO_ENLACE
    (setting de Django o variable de entorno): es lo que permite probar la
    integración con un host de pruebas sin instalar la biblioteca."""
    forzada = getattr(settings, "AVACOM_CONTENIDO_ENLACE", None) or os.environ.get("AVACOM_CONTENIDO_ENLACE")
    if forzada:
        return forzada
    base = os.environ.get("ProgramData") or os.environ.get("PROGRAMDATA") or r"C:\ProgramData"
    return os.path.join(base, "AVACOM", "contenido", "enlace.json")


def _clave(nota: dict, nombre: str):
    """Acepta PascalCase y minúsculas: no se ata el LMS a un detalle de serialización."""
    for candidata in (nombre, nombre.lower(), nombre.capitalize()):
        if candidata in nota:
            return nota[candidata]
    return None


def leer_enlace() -> dict:
    """Lee la nota EN CADA llamada. Devuelve {contrato, puerto, ficha, proceso}.

    Lanza BibliotecaNoDisponible si la nota no existe, no se puede leer, está
    incompleta o declara un contrato que este LMS no entiende.
    """
    ruta = ruta_enlace()
    if not os.path.exists(ruta):
        raise BibliotecaNoDisponible(
            "AVACOM Biblioteca no está encendida en este equipo (no hay nota de enlace)."
        )
    try:
        with open(ruta, encoding="utf-8") as archivo:
            nota = json.load(archivo)
    except (OSError, json.JSONDecodeError) as error:
        raise BibliotecaNoDisponible(f"La nota de enlace no se pudo leer: {error}") from error

    if not isinstance(nota, dict):
        raise BibliotecaNoDisponible("La nota de enlace no tiene la forma esperada.")

    contrato = _clave(nota, "Contrato")
    puerto = _clave(nota, "Puerto")
    ficha = _clave(nota, "Ficha")
    proceso = _clave(nota, "Proceso")
    if not isinstance(contrato, int) or not isinstance(puerto, int) or not isinstance(ficha, str) or not ficha:
        raise BibliotecaNoDisponible("La nota de enlace está incompleta (faltan Contrato, Puerto o Ficha).")
    if contrato > CONTRATO_SOPORTADO:
        raise BibliotecaNoDisponible(
            f"La biblioteca habla el contrato {contrato} y este LMS sólo entiende hasta el "
            f"{CONTRATO_SOPORTADO}: hay que actualizar el LMS.",
            sugerencia="Actualiza AVACOM OPS antes de volver a intentarlo.",
        )
    return {
        "contrato": contrato,
        "puerto": puerto,
        "ficha": ficha,
        "proceso": proceso if isinstance(proceso, int) else None,
    }


def proceso_vivo(pid: int | None):
    """True / False / None (no se sabe). En Windows NO se usa os.kill(pid, 0):
    CPython lo traduce a TerminateProcess y mataría la biblioteca en clase."""
    if not pid:
        return None
    if sys.platform == "win32":
        import ctypes
        from ctypes import wintypes

        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        STILL_ACTIVE = 259
        ERROR_INVALID_PARAMETER = 87
        ERROR_ACCESS_DENIED = 5
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.OpenProcess.restype = wintypes.HANDLE
        handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not handle:
            error = ctypes.get_last_error()
            if error == ERROR_INVALID_PARAMETER:
                return False
            if error == ERROR_ACCESS_DENIED:
                return True
            return None
        try:
            codigo = wintypes.DWORD()
            if not kernel32.GetExitCodeProcess(handle, ctypes.byref(codigo)):
                return None
            return codigo.value == STILL_ACTIVE
        finally:
            kernel32.CloseHandle(handle)
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return None


# ---------------------------------------------------------------- transporte

# Sin proxy: la biblioteca es loopback y un proxy del sistema (registro de
# Windows o variables de entorno) desviaría 127.0.0.1 a ningún sitio.
_abridor = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def _tiempo_espera() -> float:
    return float(getattr(settings, "AVACOM_CONTENIDO_TIEMPO_ESPERA_SEG", 3))


def _pedir(metodo: str, camino: str, consulta: dict | None = None, cuerpo: dict | None = None,
           cabeceras: dict | None = None, crudo: bool = False):
    """La única función que abre un socket hacia la biblioteca.

    Devuelve el JSON decodificado o, con `crudo=True`, la respuesta HTTP abierta
    (quien la pide debe cerrarla). Traduce fallos del transporte a dos
    excepciones: BibliotecaNoDisponible y BibliotecaError(estado, detalle).
    """
    nota = leer_enlace()
    filtros = {k: v for k, v in (consulta or {}).items() if v not in (None, "")}
    url = f"http://127.0.0.1:{nota['puerto']}{camino}"
    if filtros:
        url += "?" + urllib.parse.urlencode(filtros)

    datos = None
    encabezados = {"X-Avacom-Ficha": nota["ficha"], "Accept": "application/json, */*"}
    if cuerpo is not None:
        datos = json.dumps(cuerpo, ensure_ascii=False).encode("utf-8")
        encabezados["Content-Type"] = "application/json; charset=utf-8"
    encabezados.update(cabeceras or {})

    peticion = urllib.request.Request(url, data=datos, headers=encabezados, method=metodo)
    try:
        respuesta = _abridor.open(peticion, timeout=_tiempo_espera())
    except urllib.error.HTTPError as error:
        detalle = _detalle_de_error(error)
        raise BibliotecaError(error.code, detalle) from error
    except urllib.error.URLError as error:
        raise BibliotecaNoDisponible(
            "La nota de enlace apunta a un puerto donde nadie escucha: la biblioteca se cerró."
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
        raise BibliotecaNoDisponible(f"La biblioteca contestó algo que no es JSON ({error}).") from error


def _detalle_de_error(error: urllib.error.HTTPError) -> str:
    try:
        texto = error.read().decode("utf-8", errors="replace")[:400]
    except OSError:
        texto = ""
    try:
        datos = json.loads(texto) if texto else {}
        if isinstance(datos, dict):
            for clave in ("motivo", "error", "detail"):
                if datos.get(clave):
                    return str(datos[clave])
    except json.JSONDecodeError:
        pass
    return texto or str(error.reason) or f"HTTP {error.code}"


def _lista(respuesta, *claves) -> list:
    """La biblioteca a veces contesta lista y a veces objeto envolvente."""
    if isinstance(respuesta, list):
        return respuesta
    if isinstance(respuesta, dict):
        for clave in claves:
            if isinstance(respuesta.get(clave), list):
                return respuesta[clave]
    return []


# ----------------------------------------------------------------- contrato

def salud() -> dict:
    return _pedir("GET", "/v1/salud")


def capacidades(datos_salud: dict | None = None) -> list[str]:
    """Un componente que no declara capacidades equivale a la lista vacía."""
    datos = datos_salud if datos_salud is not None else salud()
    lista = datos.get("capacidades") or []
    return [str(c) for c in lista]


def _exigir(capacidad: str, caps: list[str]) -> None:
    """Una ruta opcional exige su capacidad y responde 501 explicativo; nunca se
    simula un resultado."""
    if capacidad not in caps:
        raise BibliotecaError(
            501,
            f"La biblioteca instalada no publica la capacidad «{capacidad}». "
            f"Capacidades disponibles: {', '.join(caps) or 'ninguna'}.",
            capacidades=caps,
        )


def _ref(valor: str) -> str:
    return urllib.parse.quote(valor, safe="")


def catalogo(**filtros) -> list[dict]:
    return _lista(_pedir("GET", "/v1/catalogo", consulta=filtros), "elementos", "items")


def taxonomia(padre: str | None = None) -> list[dict]:
    return _lista(_pedir("GET", "/v1/taxonomia", consulta={"padre": padre}), "nodos", "items")


def elemento(ref: str) -> dict:
    return _pedir("GET", f"/v1/elemento/{_ref(ref)}")


def mostrar(elemento_ref: str) -> dict:
    """Proyecta un material en la pantalla del aula (la ventana de la biblioteca)."""
    return _pedir("POST", "/v1/mostrar", cuerpo={"elemento_ref": elemento_ref})


def cursos() -> dict:
    """{huella_catalogo, cursos:[...], capacidades} con la política de la escuela ya aplicada."""
    caps = capacidades()
    _exigir(CAPACIDAD_CURSO, caps)
    datos = _pedir("GET", "/v1/cursos")
    return {
        "huella_catalogo": datos.get("huella_catalogo", ""),
        "cursos": _lista(datos, "cursos"),
        "capacidades": caps,
    }


def curso(curso_ref: str) -> dict:
    """El árbol vigente del curso: secciones (nodos de taxonomía) con sus items."""
    caps = capacidades()
    _exigir(CAPACIDAD_CURSO, caps)
    datos = _pedir("GET", f"/v1/curso/{_ref(curso_ref)}")
    datos["capacidades"] = caps
    return datos


def leccion(elemento_ref: str) -> dict:
    caps = capacidades()
    _exigir(CAPACIDAD_LECCION, caps)
    return _pedir("GET", f"/v1/leccion/{_ref(elemento_ref)}")


CLAVES_PROHIBIDAS = frozenset({
    "clave", "clave_respuesta", "respuesta", "respuesta_correcta", "correcta", "es_correcta", "solucion",
})


def sin_claves(valor):
    """Recorre recursivamente un payload y quita cualquier campo que pudiera
    contener una clave de corrección (artículo 6 / CA-08). La biblioteca ya no
    las envía; esto es la segunda línea de defensa."""
    if isinstance(valor, dict):
        return {k: sin_claves(v) for k, v in valor.items() if str(k).lower() not in CLAVES_PROHIBIDAS}
    if isinstance(valor, list):
        return [sin_claves(v) for v in valor]
    return valor


def evaluacion(elemento_ref: str) -> dict:
    """Preguntas de una evaluación o actividad, sin ningún indicador de corrección."""
    caps = capacidades()
    _exigir(CAPACIDAD_EVALUACION, caps)
    datos = _pedir("GET", f"/v1/evaluacion/{_ref(elemento_ref)}")
    return sin_claves(datos)


def comprobar(elemento_ref: str, pregunta_ref: str, respuesta: str) -> dict:
    """La clave se compara donde vive. Devuelve {acierta, retroalimentacion}."""
    caps = capacidades()
    _exigir(CAPACIDAD_COMPROBAR, caps)
    return _pedir(
        "POST",
        "/v1/comprobar",
        cuerpo={"elemento_ref": elemento_ref, "pregunta_ref": pregunta_ref, "respuesta": respuesta},
    )


def abrir_medio(elemento_ref: str, ruta_interna: str | None = None, rango: str | None = None,
                metodo: str = "GET"):
    """Abre el flujo de bytes de un material (capacidad `medio`). Devuelve la
    respuesta HTTP cruda, con Content-Type, Content-Length y Content-Range de la
    biblioteca. Quien la pide la cierra."""
    caps = capacidades()
    _exigir(CAPACIDAD_MEDIO, caps)
    camino = f"/v1/medio/{_ref(elemento_ref)}"
    if ruta_interna:
        camino += "/" + urllib.parse.quote(ruta_interna, safe="/")
    cabeceras = {"Range": rango} if rango else None
    return _pedir(metodo, camino, cabeceras=cabeceras, crudo=True)


def abrir_voz(elemento_ref: str, pregunta_ref: str | None = None, rango: str | None = None,
              metodo: str = "GET"):
    """Instrucción hablada de un elemento o de una pregunta (capacidad `voz`)."""
    caps = capacidades()
    _exigir(CAPACIDAD_VOZ, caps)
    camino = f"/v1/voz/{_ref(elemento_ref)}"
    if pregunta_ref:
        camino += "/" + _ref(pregunta_ref)
    cabeceras = {"Range": rango} if rango else None
    return _pedir(metodo, camino, cabeceras=cabeceras, crudo=True)


# ------------------------------------------------------------------- estado

def _huella_catalogo(datos: dict) -> str:
    """Preferencia: generación → huella → contadores. Es la respuesta a «¿puedo
    preguntar a menudo?»: sí, porque es diminuta."""
    if datos.get("generacion") is not None:
        return f"g{datos['generacion']}"
    if datos.get("huella_catalogo"):
        return f"h{datos['huella_catalogo']}"
    return f"c{datos.get('elementos', 0)}-{datos.get('paquetes', 0)}-{datos.get('politicas', 0)}"


def estado() -> dict:
    """El artículo 9 hecho función: NUNCA lanza. Siempre devuelve un diccionario
    y, si no hay componente, `disponible=False` con el motivo."""
    salida = {
        "disponible": False,
        "motivo": "",
        "sugerencia": None,
        "puerto": None,
        "proceso": None,
        "proceso_vivo": None,
        "componente": "",
        "contrato": None,
        "huella_catalogo": "",
        "huella_derivada": False,
        "capacidades": [],
        "conteos": {"elementos": 0, "paquetes": 0, "politicas": 0, "cursos": 0},
    }
    try:
        nota = leer_enlace()
    except BibliotecaNoDisponible as error:
        salida.update(motivo=error.motivo, sugerencia=error.sugerencia)
        return salida

    salida.update(puerto=nota["puerto"], proceso=nota["proceso"], proceso_vivo=proceso_vivo(nota["proceso"]))
    try:
        datos = salud()
    except BibliotecaNoDisponible as error:
        salida.update(motivo=error.motivo, sugerencia=error.sugerencia)
        return salida
    except BibliotecaError as error:
        salida.update(
            motivo=f"La biblioteca respondió {error.estado}: {error.detalle}",
            sugerencia=SUGERENCIA_ABRIR,
        )
        return salida

    salida.update(
        disponible=True,
        componente=str(datos.get("componente", "")),
        contrato=datos.get("contrato"),
        huella_catalogo=_huella_catalogo(datos),
        huella_derivada=datos.get("generacion") is None and not datos.get("huella_catalogo"),
        capacidades=capacidades(datos),
        conteos={
            "elementos": int(datos.get("elementos", 0) or 0),
            "paquetes": int(datos.get("paquetes", 0) or 0),
            "politicas": int(datos.get("politicas", 0) or 0),
            "cursos": int(datos.get("cursos", 0) or 0),
        },
    )
    return salida
