"""
`manage.py acceso_importar`: FUN-003 / CAP-003, carga masiva de usuarios desde un
archivo delimitado, sin red y sin pasar por la interfaz HTTP.

    manage.py acceso_importar padron.csv --actor-dni 1042888795 [--delimitador ";"] [--grupo 8A]

El actor debe ser una persona con el permiso `identity.user.import` (administración).
Usa el mismo caso de uso que POST /api/acceso/usuarios/importar/.
"""
from __future__ import annotations

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from acceso.aplicacion.casos_uso import ImportarUsuarios
from acceso.dominio import errores
from acceso.dominio.entidades import Principal
from acceso.dominio.valores import ClaseSesion, DocumentNumber
from acceso.infraestructura.contenedor import servicios


class Command(BaseCommand):
    help = "Importa usuarios desde un archivo delimitado (rol, alias, nombres, apellidos, tipo_identificador, identificador, grupo, secreto)."

    def add_arguments(self, parser):
        parser.add_argument("archivo")
        parser.add_argument("--actor-dni", required=True, help="Documento de la persona que ejecuta la importación.")
        parser.add_argument("--delimitador", default=",")
        parser.add_argument("--grupo", default="", help="Código de grupo por defecto para las filas sin columna grupo.")

    def handle(self, *args, **opciones):
        ruta = Path(opciones["archivo"])
        if not ruta.exists():
            raise CommandError(f"No existe el archivo {ruta}.")
        s = servicios()
        with s.uow() as uow:
            hmac_doc = s.cifrador.indice(DocumentNumber.normalizar_entrada(opciones["actor_dni"])[0])
            encontrado = uow.usuarios.por_identificador(hmac_doc)
            if encontrado is None:
                raise CommandError("No existe una persona con ese documento.")
            actor, _ = encontrado
            rol = uow.roles.por_id(actor.rol_id)
            grupo_id = None
            if opciones["grupo"]:
                grupo = next((g for g in uow.grupos.listar(actor.organizacion_id) if g.codigo.upper() == opciones["grupo"].upper()), None)
                if grupo is None:
                    raise CommandError(f"No existe el grupo {opciones['grupo']}.")
                grupo_id = grupo.id
        # El comando actúa con la identidad del actor, sin abrir una sesión HTTP.
        principal = Principal(actor.id, actor.organizacion_id, rol.id, rol.codigo, rol.menu_principal, rol.nivel,
                              sesion_id="consola", clase_sesion=ClaseSesion.NORMAL, debe_cambiar_credencial=False)
        try:
            salida = ImportarUsuarios(s).ejecutar(principal, contenido=ruta.read_text(encoding="utf-8-sig"),
                                                  delimitador=opciones["delimitador"], grupo_id=grupo_id)
        except errores.ErrorAcceso as error:
            raise CommandError(f"{error.codigo}: {error.detalle} {error.extra or ''}")
        r = salida["resumen"]
        self.stdout.write(self.style.SUCCESS(f"Importados {r['creados']} de {r['total']} · {r['existentes']} ya existían · {r['rechazadas']} rechazadas."))
        for fila in salida["creados"]:
            if fila.get("secreto_inicial"):
                self.stdout.write(f"  {fila['identificador']} · {fila['alias']} · clave inicial: {fila['secreto_inicial']}")
        for fila in salida["rechazadas"]:
            self.stdout.write(self.style.WARNING(f"  fila {fila['fila']} ({fila['identificador']}): {fila['motivo']}"))
