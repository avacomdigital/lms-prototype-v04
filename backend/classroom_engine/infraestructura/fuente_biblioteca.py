"""
Fuente de cursos REAL: AVACOM Biblioteca a través de la **API de Contenido v2**
(`biblioteca.contenido_v2`). MOD-007 no abre sockets: reutiliza el descubrimiento de
`link.json`, el token, el reintento único tras 401, el tiempo de espera y la
degradación que viven en ese módulo.

Qué pide y cómo:
  GET /v2/courses                                → la lista de cursos instalados (fichas o cursos completos)
  GET /v2/courses/{courseId}?mode=class&profile= → el curso recortado; `profile=teacher` sólo para el docente
  GET /v2/courses/{courseId}?version=…           → una versión archivada, para reconstruir un intento viejo
  GET /v2/courses/{courseId}/media/{mediaId}[/r] → bytes del medio, en paso a través
  POST /v2/evaluate · /v2/evaluate/batch         → el veredicto, siempre con `version`

Traducción de los códigos de error del contrato a los del aula:
  sin link.json / puerto muerto / sin respuesta  → FuenteNoDisponible (503, estado normal)
  index_rebuilding (503)                         → FuenteNoDisponible con «vuelve a intentarlo»
  course_not_found (404)                         → CursoNoEncontrado
  not_found · lesson_not_found (404)             → ReferenciaNoEncontrada
  disabled_by_policy (403)                       → DesactivadoPorPolitica (404 para el aula)
  invalid_parameter (400)                        → DatosInvalidos
  unauthorized tras el reintento (401)           → FuenteError (502)
  invalid_response y demás                       → FuenteError (502)
"""
from __future__ import annotations

from biblioteca import contenido_v2 as v2
from biblioteca.cliente import BibliotecaError, BibliotecaNoDisponible

from ..aplicacion.puertos import Bytes
from ..dominio.errores import (
    CapacidadAusente,
    CursoNoEncontrado,
    DatosInvalidos,
    DesactivadoPorPolitica,
    FuenteError,
    FuenteNoDisponible,
    ReferenciaNoEncontrada,
)

MODO_AULA = "class"                                   # el aula siempre pide el curso en modo clase
PERFIL_POR_ROL = {"docente": "teacher", "estudiante": "student"}
SUGERENCIA_INDICE = "La biblioteca está reconstruyendo su índice; vuelve a intentarlo en unos segundos."


def _traducir(error: Exception, *, curso_ref: str = "", media_ref: str = "", pregunta_ref: str = "") -> Exception:
    if isinstance(error, BibliotecaNoDisponible):
        return FuenteNoDisponible(error.motivo, sugerencia=error.sugerencia)
    if not isinstance(error, BibliotecaError):
        return error
    codigo, estado, detalle = error.codigo, error.estado, error.detalle
    extra = {"codigo_biblioteca": codigo} if codigo else {}
    if codigo == "index_rebuilding" or estado == 503:
        return FuenteNoDisponible(detalle or "La biblioteca está reconstruyendo su índice.", sugerencia=SUGERENCIA_INDICE, **extra)
    if codigo == "disabled_by_policy" or estado == 403:
        return DesactivadoPorPolitica(detalle, curso_ref=curso_ref, **extra)
    if codigo == "course_not_found":
        return CursoNoEncontrado(detalle, curso_ref=curso_ref, **extra)
    if codigo in ("not_found", "lesson_not_found") or estado == 404:
        if media_ref or pregunta_ref:
            return ReferenciaNoEncontrada(detalle, media_ref=media_ref, pregunta_ref=pregunta_ref, **extra)
        return CursoNoEncontrado(detalle, curso_ref=curso_ref, **extra)
    if codigo == "invalid_parameter" or estado == 400:
        return DatosInvalidos(detalle, **extra)
    if estado == 501:
        return CapacidadAusente(detalle, capacidades=error.capacidades)
    return FuenteError(detalle, estado_biblioteca=estado, **extra)


def _con_id(datos: dict) -> dict:
    if isinstance(datos, dict) and "id" not in datos and datos.get("courseId"):
        datos["id"] = datos["courseId"]
    return datos


class FuenteBiblioteca:
    nombre = "biblioteca"

    def cursos(self) -> list[dict]:
        """`GET /v2/courses`. Si la lista trae fichas (sin `lessons`), se baja cada curso completo:
        la lista de una escuela es corta y así el panel muestra lecciones y portada reales."""
        try:
            fichas = v2.cursos()
        except (BibliotecaNoDisponible, BibliotecaError) as error:
            raise _traducir(error) from error
        salida = []
        for ficha in fichas:
            if "lessons" in ficha:
                salida.append(_con_id(ficha))
                continue
            ref = str(ficha.get("courseId") or ficha.get("id") or "")
            if not ref:
                continue
            try:
                salida.append(self.curso(ref, rol="estudiante"))
            except (CursoNoEncontrado, DesactivadoPorPolitica, ReferenciaNoEncontrada):
                continue      # lo que la política desactivó no se muestra (§7)
        return salida

    def curso(self, curso_ref: str, *, version: str | None = None, rol: str = "estudiante") -> dict:
        try:
            datos = v2.curso(curso_ref, version=version, modo=MODO_AULA, perfil=PERFIL_POR_ROL.get(rol, "student"))
        except (BibliotecaNoDisponible, BibliotecaError) as error:
            raise _traducir(error, curso_ref=curso_ref) from error
        if not isinstance(datos, dict):
            raise FuenteError("La biblioteca no devolvió un curso.", curso_ref=curso_ref)
        return _con_id(datos)

    def medio(self, curso_ref: str, media_ref: str, ruta: str | None, rango: str | None, metodo: str) -> Bytes:
        try:
            respuesta = v2.abrir_medio(curso_ref, media_ref, ruta, rango, metodo)
        except (BibliotecaNoDisponible, BibliotecaError) as error:
            raise _traducir(error, curso_ref=curso_ref, media_ref=media_ref) from error
        return Bytes(respuesta.headers.get("Content-Type") or "application/octet-stream", flujo=respuesta)

    def evaluar(self, curso_ref: str, version: str, objeto_ref: str, pregunta_ref: str, respuesta: dict) -> dict:
        try:
            return v2.evaluar(curso_ref, version, objeto_ref, pregunta_ref, respuesta)
        except (BibliotecaNoDisponible, BibliotecaError) as error:
            raise _traducir(error, curso_ref=curso_ref, pregunta_ref=pregunta_ref) from error

    def evaluar_lote(self, curso_ref: str, version: str, items: list[dict]) -> list[dict]:
        try:
            return v2.evaluar_lote([{"courseId": curso_ref, "version": version, **item} for item in items])
        except (BibliotecaNoDisponible, BibliotecaError) as error:
            raise _traducir(error, curso_ref=curso_ref) from error

    def estado(self) -> dict:
        return v2.estado()
