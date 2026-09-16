"""
Alineación de datos con MOD-001 · Identity & Access del Documento Maestro.

1. Renombra los permisos del módulo al espacio `identity.*` conservando roles y
   escaladas que los referencian.
2. Añade los permisos nuevos y los roles de sistema REPORTS y TECHNICIAN.
3. Crea las políticas de credencial de los perfiles nuevos en las organizaciones
   que ya existan.
4. Convierte el rol único de cada usuario en su primera asignación de rol con
   alcance de organización (m01_usuario_rol) y fija el rol efectivo de las
   sesiones abiertas.
5. Marca como principal el identificador de acceso de cada persona y le pone
   como emisor el código de su organización (DEC-048).
Idempotente: se puede volver a ejecutar sin duplicar nada.
"""
import time
import uuid

from django.db import migrations

from acceso.dominio import plantillas


def _ahora():
    return int(time.time() * 1000)


def renombrar_permisos(apps, schema_editor):
    Permiso = apps.get_model("acceso", "Permiso")
    RolPermiso = apps.get_model("acceso", "RolPermiso")
    UsuarioPermiso = apps.get_model("acceso", "UsuarioPermiso")
    for viejo, nuevo in plantillas.RENOMBRES_PERMISOS.items():
        definicion = plantillas.PERMISOS_POR_CODIGO[nuevo]
        Permiso.objects.update_or_create(codigo=nuevo, defaults={
            "modulo": definicion[1], "descripcion": definicion[2], "alcance_maximo": definicion[3].value})
        RolPermiso.objects.filter(permiso_id=viejo).update(permiso_id=nuevo)
        UsuarioPermiso.objects.filter(permiso_id=viejo).update(permiso_id=nuevo)
        Permiso.objects.filter(codigo=viejo).delete()


def sembrar_catalogo_y_roles(apps, schema_editor):
    Permiso = apps.get_model("acceso", "Permiso")
    Rol = apps.get_model("acceso", "Rol")
    RolPermiso = apps.get_model("acceso", "RolPermiso")
    ahora = _ahora()
    for codigo, modulo, descripcion, maximo, _sensible in plantillas.PERMISOS:
        Permiso.objects.update_or_create(codigo=codigo, defaults={
            "modulo": modulo, "descripcion": descripcion, "alcance_maximo": maximo.value})
    for codigo, (nombre, menu, nivel, permisos) in plantillas.ROLES_SISTEMA.items():
        rol = Rol.objects.filter(codigo=codigo, organizacion__isnull=True).first()
        if rol is None:
            rol = Rol.objects.create(id=str(uuid.uuid4()), organizacion=None, codigo=codigo, nombre=nombre,
                                     menu_principal=menu.value, nivel=nivel, es_sistema=True, creado_en=ahora)
        else:
            rol.nombre = nombre
            rol.save(update_fields=["nombre"])
        RolPermiso.objects.filter(rol=rol).delete()
        RolPermiso.objects.bulk_create([
            RolPermiso(rol=rol, permiso_id=permiso, alcance=alcance.value) for permiso, alcance in permisos.items()])


def politicas_perfiles_nuevos(apps, schema_editor):
    Organizacion = apps.get_model("acceso", "Organizacion")
    Politica = apps.get_model("acceso", "PoliticaCredencial")
    ahora = _ahora()
    for org in Organizacion.objects.all():
        for perfil, valores in plantillas.POLITICAS_POR_DEFECTO.items():
            if Politica.objects.filter(organizacion=org, perfil=perfil.value, nivel_clave__isnull=True).exists():
                continue
            datos = {k: (v.value if hasattr(v, "value") else v) for k, v in valores.items()}
            Politica.objects.create(id=str(uuid.uuid4()), organizacion=org, perfil=perfil.value, creado_en=ahora,
                                    actualizado_en=ahora, **datos)


def asignaciones_iniciales(apps, schema_editor):
    Usuario = apps.get_model("acceso", "Usuario")
    UsuarioRol = apps.get_model("acceso", "UsuarioRol")
    Sesion = apps.get_model("acceso", "Sesion")
    Identificador = apps.get_model("acceso", "IdentificadorUsuario")
    ahora = _ahora()
    for usuario in Usuario.objects.select_related("organizacion").all():
        if not UsuarioRol.objects.filter(usuario=usuario, rol_id=usuario.rol_id, revocado_en__isnull=True).exists():
            UsuarioRol.objects.create(id=str(uuid.uuid4()), usuario=usuario, rol_id=usuario.rol_id,
                                      alcance_tipo="ORGANIZATION", alcance_id=None, desde=usuario.creado_en or ahora)
        Sesion.objects.filter(usuario=usuario, rol__isnull=True).update(rol_id=usuario.rol_id)
        Identificador.objects.filter(usuario=usuario, emisor="").update(emisor=usuario.organizacion.codigo)
        if not Identificador.objects.filter(usuario=usuario, principal=True, retirado_en__isnull=True).exists():
            primero = Identificador.objects.filter(usuario=usuario, retirado_en__isnull=True).order_by("-es_login", "creado_en").first()
            if primero:
                primero.principal = True
                primero.save(update_fields=["principal"])


def nada(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [("acceso", "0003_alineacion_mod001")]
    operations = [
        migrations.RunPython(renombrar_permisos, nada),
        migrations.RunPython(sembrar_catalogo_y_roles, nada),
        migrations.RunPython(politicas_perfiles_nuevos, nada),
        migrations.RunPython(asignaciones_iniciales, nada),
    ]
