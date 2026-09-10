"""
Rutas que el backend expone hacia arriba (OPS Master y Student) sobre la biblioteca.

Contrato de degradación (línea base §8):
  - BibliotecaNoDisponible → 503 {disponible:false, detail, sugerencia}
  - BibliotecaError 501   → 501 con el detalle y las `capacidades` publicadas
  - BibliotecaError 404/403/409 → se pasan tal cual (significan algo para el cliente)
  - cualquier otro BibliotecaError → 502 con el detalle
"""
from __future__ import annotations

from django.http import HttpResponse, StreamingHttpResponse
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from expediente import servicios

from . import cliente

CABECERAS_MEDIO = ("Content-Length", "Content-Range", "Accept-Ranges", "Cache-Control")


def respuesta_de_error(error: Exception) -> Response:
    if isinstance(error, cliente.BibliotecaNoDisponible):
        return Response(
            {"disponible": False, "detail": error.motivo, "sugerencia": error.sugerencia},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    if isinstance(error, cliente.BibliotecaError):
        if error.estado == 501:
            return Response({"detail": error.detalle, "capacidades": error.capacidades}, status=501)
        if error.estado in (403, 404, 409):
            return Response({"detail": error.detalle}, status=error.estado)
        return Response({"detail": error.detalle, "estado_biblioteca": error.estado}, status=status.HTTP_502_BAD_GATEWAY)
    raise error


class VistaBiblioteca(APIView):
    """Base: convierte las dos excepciones del cliente en las respuestas del contrato."""

    def handle_exception(self, exc):
        if isinstance(exc, (cliente.BibliotecaNoDisponible, cliente.BibliotecaError)):
            return respuesta_de_error(exc)
        return super().handle_exception(exc)


class EstadoView(VistaBiblioteca):
    def get(self, request):
        return Response(cliente.estado())


class CursosView(VistaBiblioteca):
    """Los cursos ofrecidos por la biblioteca (con la política de la escuela ya
    aplicada). Con `?persona=` añade el progreso de esa persona en cada curso.
    Deja memoria de la última revisión de disponibilidad."""

    def get(self, request):
        datos = cliente.cursos()
        persona = request.query_params.get("persona") or None
        cursos = datos["cursos"]
        servicios.revisar_disponibilidad([c.get("curso_ref", "") for c in cursos])
        salida = []
        for curso in cursos:
            fila = dict(curso)
            fila["disponible"] = True
            fila["progreso"] = float(servicios.promedio_curso(curso.get("curso_ref", ""), persona, None)) if persona else None
            salida.append(fila)
        return Response({
            "disponible": True,
            "huella_catalogo": datos["huella_catalogo"],
            "capacidades": datos["capacidades"],
            "cursos": salida,
        })


class CursoView(VistaBiblioteca):
    """El árbol vigente de un curso, resuelto en vivo, anotado con el expediente de `?persona=`."""

    def get(self, request, curso_ref: str):
        detalle = cliente.curso(curso_ref)
        persona = request.query_params.get("persona") or None
        return Response(servicios.proyectar_curso(detalle, persona))


class CatalogoView(VistaBiblioteca):
    def get(self, request):
        filtros = {k: request.query_params.get(k) for k in ("nivel", "grado", "asignatura", "tipo", "taxonomia_ref")}
        return Response({"elementos": cliente.catalogo(**filtros)})


class TaxonomiaView(VistaBiblioteca):
    def get(self, request):
        return Response({"nodos": cliente.taxonomia(request.query_params.get("padre"))})


class ElementoView(VistaBiblioteca):
    def get(self, request, ref: str):
        return Response(cliente.elemento(ref))


class MostrarView(VistaBiblioteca):
    """Proyecta un material en la pantalla del aula (ventana de la biblioteca)."""

    def post(self, request):
        ref = (request.data or {}).get("elemento_ref")
        if not ref:
            return Response({"detail": "Falta elemento_ref."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            return Response(cliente.mostrar(ref))
        except cliente.BibliotecaError as error:
            if error.estado == 409:
                return Response({"aceptado": False, "motivo": error.detalle}, status=409)
            raise


class LeccionView(VistaBiblioteca):
    def get(self, request, ref: str):
        return Response(cliente.leccion(ref))


class EvaluacionView(VistaBiblioteca):
    """Preguntas sin ningún indicador de corrección (la clave nunca llega al LMS)."""

    def get(self, request, ref: str):
        return Response(cliente.evaluacion(ref))


def _reenviar_flujo(respuesta, metodo: str):
    """Convierte la respuesta cruda de la biblioteca en un StreamingHttpResponse
    que respeta Content-Type, Content-Length y Content-Range (para que el
    reproductor pueda adelantar un video)."""
    tipo = respuesta.headers.get("Content-Type") or "application/octet-stream"
    if metodo == "HEAD":
        respuesta.close()
        salida = HttpResponse(status=respuesta.status, content_type=tipo)
    else:
        def generar():
            try:
                while True:
                    trozo = respuesta.read(64 * 1024)
                    if not trozo:
                        break
                    yield trozo
            finally:
                respuesta.close()

        salida = StreamingHttpResponse(generar(), status=respuesta.status, content_type=tipo)
    for cabecera in CABECERAS_MEDIO:
        valor = respuesta.headers.get(cabecera)
        if valor:
            salida[cabecera] = valor
    salida.setdefault("Cache-Control", "no-store")
    return salida


class MedioView(VistaBiblioteca):
    """Flujo de bytes de un material (capacidad `medio`). Es un paso a través:
    la biblioteca descifra y aplica la política; el LMS no abre archivos."""

    def get(self, request, ref: str, ruta: str | None = None):
        return _reenviar_flujo(cliente.abrir_medio(ref, ruta, request.headers.get("Range"), "GET"), "GET")

    def head(self, request, ref: str, ruta: str | None = None):
        return _reenviar_flujo(cliente.abrir_medio(ref, ruta, request.headers.get("Range"), "HEAD"), "HEAD")


class VozView(VistaBiblioteca):
    """Instrucción hablada de un elemento o de una pregunta (capacidad `voz`)."""

    def get(self, request, ref: str, pregunta_ref: str | None = None):
        return _reenviar_flujo(cliente.abrir_voz(ref, pregunta_ref, request.headers.get("Range"), "GET"), "GET")

    def head(self, request, ref: str, pregunta_ref: str | None = None):
        return _reenviar_flujo(cliente.abrir_voz(ref, pregunta_ref, request.headers.get("Range"), "HEAD"), "HEAD")
