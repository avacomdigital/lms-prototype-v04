"""
Composition root de MOD-007: el único sitio que sabe qué adaptador va con qué puerto
y cómo se construyen las URL de los medios que consume el cliente MAUI.
"""
from __future__ import annotations

import time
from urllib.parse import quote

from django.conf import settings

from ..aplicacion.casos_uso import Servicios
from ..dominio.errores import DatosInvalidos
from .fuente_biblioteca import FuenteBiblioteca
from .fuente_ejemplo import ALIAS, FuenteEjemplo
from .repositorios import AutorizacionPrototipo
from .unidad_trabajo import FabricaUoWAula

FUENTES = ("biblioteca", "ejemplo")


class RelojNodo:
    """BR-062: la marca temporal autoritativa la pone el equipo del aula."""

    def ahora_ms(self) -> int:
        return int(time.time() * 1000)


def ruta_ejemplo() -> str:
    return getattr(settings, "AVACOM_AULA_CURSO_EJEMPLO", "") or ""


def fuente_por_defecto() -> str:
    return getattr(settings, "AVACOM_AULA_FUENTE_CURSOS", "biblioteca") or "biblioteca"


def fuente(nombre: str | None, curso_ref: str = ""):
    """La fuente pedida; sin nombre, la configurada. Si no se pidió ninguna y la referencia es la
    del manifiesto de ejemplo, se resuelve sola: así las URL de medios no dependen del parámetro."""
    if nombre:
        if nombre not in FUENTES:
            raise DatosInvalidos(f"Fuente desconocida «{nombre}». Fuentes: {', '.join(FUENTES)}.", fuente=nombre)
        return FuenteEjemplo(ruta_ejemplo()) if nombre == "ejemplo" else FuenteBiblioteca()
    if curso_ref and (curso_ref in ALIAS or _es_el_ejemplo(curso_ref)):
        return FuenteEjemplo(ruta_ejemplo())
    return fuente(fuente_por_defecto())


def _es_el_ejemplo(curso_ref: str) -> bool:
    try:
        return str(FuenteEjemplo(ruta_ejemplo())._leer().get("id", "")) == curso_ref
    except Exception:
        return False


def url_medio(nombre_fuente: str, curso_ref: str, media_ref: str, ruta: str | None) -> str:
    base = f"/api/aula/cursos/{quote(curso_ref, safe='')}/medios/{quote(media_ref, safe='')}/"
    if ruta:
        base += quote(ruta.strip("/"), safe="/")
    return f"{base}?fuente={nombre_fuente}"


def servicios() -> Servicios:
    return Servicios(
        uow=FabricaUoWAula(),
        fuente=fuente,
        reloj=RelojNodo(),
        autorizacion=AutorizacionPrototipo(),
        url_medio=url_medio,
    )
