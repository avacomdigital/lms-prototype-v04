"""
`manage.py acceso_instalar`: mismo caso de uso que POST /api/acceso/instalacion/.

    manage.py acceso_instalar --codigo IE-SANJOSE --nombre "IE San José" --pais CO \
        --admin-dni 1042888795 --admin-nombres Ana --admin-apellidos Pérez [--admin-password "Rectoria.2026!"]

Si no se da contraseña, se genera una y se muestra UNA sola vez.
"""
from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from acceso.aplicacion.casos_uso import InstalarNodo
from acceso.dominio import errores
from acceso.infraestructura.contenedor import servicios


class Command(BaseCommand):
    help = "Instala el nodo: organización, políticas por defecto y primer administrador."

    def add_arguments(self, parser):
        parser.add_argument("--codigo", required=True)
        parser.add_argument("--nombre", required=True)
        parser.add_argument("--pais", default="CO")
        parser.add_argument("--idioma", default="es")
        parser.add_argument("--locale", default="")
        parser.add_argument("--zona-horaria", default="America/Bogota")
        parser.add_argument("--admin-dni", required=True)
        parser.add_argument("--admin-nombres", required=True)
        parser.add_argument("--admin-apellidos", default="")
        parser.add_argument("--admin-alias", default="Administración")
        parser.add_argument("--admin-password", default="")

    def handle(self, *args, **opciones):
        try:
            salida = InstalarNodo(servicios()).ejecutar(
                {"codigo": opciones["codigo"], "nombre": opciones["nombre"], "pais": opciones["pais"],
                 "idioma": opciones["idioma"], "locale": opciones["locale"], "zona_horaria": opciones["zona_horaria"]},
                {"dni": opciones["admin_dni"], "nombres": opciones["admin_nombres"], "apellidos": opciones["admin_apellidos"],
                 "alias": opciones["admin_alias"], "password": opciones["admin_password"]},
            )
        except errores.ErrorAcceso as error:
            raise CommandError(f"{error.codigo}: {error.detalle} {error.extra or ''}")
        org = salida["organizacion"]
        self.stdout.write(self.style.SUCCESS(f"Organización {org['codigo']} · {org['nombre']} instalada ({org['locale']})."))
        self.stdout.write(f"Administrador: {salida['administrador']['alias']} · id {salida['administrador']['id']}")
        if "password_inicial" in salida:
            self.stdout.write(self.style.WARNING(f"Contraseña inicial (no se volverá a mostrar): {salida['password_inicial']}"))
