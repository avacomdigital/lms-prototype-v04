"""Clases de permiso DRF. Sólo comprueban que hay sesión: la autorización real la decide la política del dominio."""
from __future__ import annotations

from django.conf import settings
from rest_framework.permissions import BasePermission

from ..dominio.entidades import Principal


def principal_de(request) -> Principal | None:
    usuario = getattr(request, "user", None)
    return usuario if isinstance(usuario, Principal) else None


class SesionRequerida(BasePermission):
    message = {"detail": "Hace falta iniciar sesión.", "codigo": "sesion_requerida"}

    def has_permission(self, request, view) -> bool:
        return principal_de(request) is not None


class SesionSiSeExige(BasePermission):
    """Para las rutas del expediente y la biblioteca: exige sesión sólo con AVACOM_LMS_EXIGIR_SESION=1 (Q-34)."""

    message = SesionRequerida.message

    def has_permission(self, request, view) -> bool:
        if not getattr(settings, "AVACOM_LMS_EXIGIR_SESION", False):
            return True
        return principal_de(request) is not None
