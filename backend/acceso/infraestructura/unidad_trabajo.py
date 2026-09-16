"""
Unit of Work sobre Django: una transacción por caso de uso. Todo lo que se escribe
dentro (incluido el outbox) se confirma o se deshace junto.
"""
from __future__ import annotations

from django.db import transaction

from ..aplicacion.puertos import Cifrador
from . import repositorios as r


class UnidadDeTrabajoDjango:
    def __init__(self, cifrador: Cifrador):
        self._cifrador = cifrador
        self._atomic = None

    def __enter__(self) -> "UnidadDeTrabajoDjango":
        self._atomic = transaction.atomic()
        self._atomic.__enter__()
        self.organizaciones = r.OrganizacionesDjango()
        self.politicas = r.PoliticasDjango()
        self.permisos = r.PermisosDjango()
        self.roles = r.RolesDjango()
        self.usuarios = r.UsuariosDjango(self._cifrador)
        self.credenciales = r.CredencialesDjango()
        self.grupos = r.GruposDjango()
        self.dispositivos = r.DispositivosDjango()
        self.sesiones = r.SesionesDjango()
        self.intentos = r.IntentosDjango()
        self.autorizaciones = r.AutorizacionesDjango()
        self.outbox = r.OutboxDjango()
        self.auditoria = r.AuditoriaExpediente()
        return self

    def __exit__(self, tipo, valor, traza) -> None:
        # transaction.atomic hace commit si no hay excepción y rollback si la hay.
        self._atomic.__exit__(tipo, valor, traza)
        self._atomic = None


class FabricaUoWDjango:
    def __init__(self, cifrador: Cifrador):
        self._cifrador = cifrador

    def __call__(self) -> UnidadDeTrabajoDjango:
        return UnidadDeTrabajoDjango(self._cifrador)
