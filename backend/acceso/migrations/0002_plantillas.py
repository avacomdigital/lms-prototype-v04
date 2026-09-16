"""
Siembra plug-and-play: catálogo de permisos y los tres roles de sistema
(STUDENT, TEACHER, ADMIN) con sus alcances. Idempotente. La organización, sus
políticas y el primer administrador se crean con `acceso_instalar` o con
POST /api/acceso/instalacion/, no aquí.
"""
import time
import uuid

from django.db import migrations

from acceso.dominio import plantillas


def sembrar(apps, schema_editor):
    Permiso = apps.get_model("acceso", "Permiso")
    Rol = apps.get_model("acceso", "Rol")
    RolPermiso = apps.get_model("acceso", "RolPermiso")
    ahora = int(time.time() * 1000)
    for codigo, modulo, descripcion, maximo, _sensible in plantillas.PERMISOS:
        Permiso.objects.update_or_create(codigo=codigo, defaults={
            "modulo": modulo, "descripcion": descripcion, "alcance_maximo": maximo.value})
    for codigo, (nombre, menu, nivel, permisos) in plantillas.ROLES_SISTEMA.items():
        rol = Rol.objects.filter(codigo=codigo, organizacion__isnull=True).first()
        if rol is None:
            rol = Rol.objects.create(id=str(uuid.uuid4()), organizacion=None, codigo=codigo, nombre=nombre,
                                     menu_principal=menu.value, nivel=nivel, es_sistema=True, creado_en=ahora)
        RolPermiso.objects.filter(rol=rol).delete()
        RolPermiso.objects.bulk_create([
            RolPermiso(rol=rol, permiso_id=permiso, alcance=alcance.value) for permiso, alcance in permisos.items()])


def retirar(apps, schema_editor):
    Rol = apps.get_model("acceso", "Rol")
    Rol.objects.filter(es_sistema=True, usuarios__isnull=True).delete()


class Migration(migrations.Migration):
    dependencies = [("acceso", "0001_initial")]
    operations = [migrations.RunPython(sembrar, retirar)]
