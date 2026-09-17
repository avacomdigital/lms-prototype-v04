"""
Fuente de cursos REAL: AVACOM Biblioteca, a través del cliente único del LMS
(`biblioteca.cliente`). MOD-007 no abre sockets: reutiliza el descubrimiento de la
nota de enlace, la ficha, el tiempo de espera y la degradación que ya existen.

Traduce las dos excepciones del cliente a los errores del dominio del aula:
  BibliotecaNoDisponible → FuenteNoDisponible (503)
  BibliotecaError 501    → CapacidadAusente   (501)
  BibliotecaError 404    → CursoNoEncontrado / ReferenciaNoEncontrada (404)
  otro BibliotecaError   → FuenteError        (502)

Lo que espera de la biblioteca cuando publique el manifiesto (Q-44/Q-45):
  GET /v1/curso/{curso_ref}            → el manifiesto (schemaVersion 1.0) o el árbol del contrato 1
  GET /v1/medio/{media_ref}[/ruta]     → los bytes del medio del paquete
"""
from __future__ import annotations

from biblioteca import cliente

from ..aplicacion.puertos import Bytes
from ..dominio.errores import CapacidadAusente, CursoNoEncontrado, FuenteError, FuenteNoDisponible, ReferenciaNoEncontrada


def _traducir(error: Exception, *, curso_ref: str = "", media_ref: str = "") -> Exception:
    if isinstance(error, cliente.BibliotecaNoDisponible):
        return FuenteNoDisponible(error.motivo, sugerencia=error.sugerencia)
    if isinstance(error, cliente.BibliotecaError):
        if error.estado == 501:
            return CapacidadAusente(error.detalle, capacidades=error.capacidades)
        if error.estado == 404:
            if media_ref:
                return ReferenciaNoEncontrada(error.detalle, media_ref=media_ref)
            return CursoNoEncontrado(error.detalle, curso_ref=curso_ref)
        return FuenteError(error.detalle, estado_biblioteca=error.estado)
    return error


class FuenteBiblioteca:
    nombre = "biblioteca"

    def cursos(self) -> list[dict]:
        try:
            return list(cliente.cursos()["cursos"])
        except (cliente.BibliotecaNoDisponible, cliente.BibliotecaError) as error:
            raise _traducir(error) from error

    def curso(self, curso_ref: str) -> dict:
        try:
            datos = cliente.curso(curso_ref)
        except (cliente.BibliotecaNoDisponible, cliente.BibliotecaError) as error:
            raise _traducir(error, curso_ref=curso_ref) from error
        datos.pop("capacidades", None)   # anotación del cliente, no del curso
        return datos

    def medio(self, curso_ref: str, media_ref: str, ruta: str | None, rango: str | None, metodo: str) -> Bytes:
        try:
            respuesta = cliente.abrir_medio(media_ref, ruta, rango, metodo)
        except (cliente.BibliotecaNoDisponible, cliente.BibliotecaError) as error:
            raise _traducir(error, curso_ref=curso_ref, media_ref=media_ref) from error
        return Bytes(respuesta.headers.get("Content-Type") or "application/octet-stream", flujo=respuesta)
