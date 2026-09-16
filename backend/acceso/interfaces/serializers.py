"""
Serializers de entrada: validan la FORMA del JSON (tipos, campos obligatorios,
longitudes). Las reglas de negocio (fortaleza, alcances, jerarquía) viven en el
dominio y no se repiten aquí. No hay ModelSerializer: el ORM no sale de la
infraestructura.
"""
from __future__ import annotations

from rest_framework import serializers


class OrganizacionEntrada(serializers.Serializer):
    codigo = serializers.CharField(max_length=32)
    nombre = serializers.CharField(max_length=200)
    pais = serializers.CharField(max_length=2, required=False, default="CO")
    idioma = serializers.CharField(max_length=8, required=False, default="es")
    locale = serializers.CharField(max_length=16, required=False, allow_blank=True, default="")
    zona_horaria = serializers.CharField(max_length=64, required=False, default="America/Bogota")


class AdministradorEntrada(serializers.Serializer):
    alias = serializers.CharField(max_length=64, required=False, default="Administración")
    nombres = serializers.CharField(max_length=120)
    apellidos = serializers.CharField(max_length=120, required=False, allow_blank=True, default="")
    dni = serializers.CharField(max_length=64)
    password = serializers.CharField(max_length=128, required=False, allow_blank=True, default="", trim_whitespace=False)


class InstalacionEntrada(serializers.Serializer):
    organizacion = OrganizacionEntrada()
    administrador = AdministradorEntrada()


class DispositivoEntrada(serializers.Serializer):
    identificador = serializers.CharField(max_length=128)
    nombre = serializers.CharField(max_length=64)
    tipo = serializers.ChoiceField(choices=["TABLETA", "MASTER"], required=False, default="TABLETA")


class DispositivoCambios(serializers.Serializer):
    nombre = serializers.CharField(max_length=64, required=False)
    activo = serializers.BooleanField(required=False)


class LoginEntrada(serializers.Serializer):
    identificador = serializers.CharField(max_length=128)
    secreto = serializers.CharField(max_length=128, trim_whitespace=False)
    dispositivo = serializers.CharField(max_length=128, required=False, allow_blank=True, default="")


class CanjeEntrada(serializers.Serializer):
    codigo = serializers.CharField(max_length=16, required=False, allow_blank=True, default="")
    grant_id = serializers.CharField(max_length=36, required=False, allow_blank=True, default="")
    token = serializers.CharField(max_length=128, required=False, allow_blank=True, default="")
    dispositivo = serializers.CharField(max_length=128, required=False, allow_blank=True, default="")

    def validate(self, datos):
        if not datos.get("codigo") and not (datos.get("grant_id") and datos.get("token")):
            raise serializers.ValidationError("Envíe un código, o bien grant_id y token.")
        return datos


class CambioCredencialEntrada(serializers.Serializer):
    secreto_actual = serializers.CharField(max_length=128, trim_whitespace=False)
    secreto_nuevo = serializers.CharField(max_length=128, trim_whitespace=False)


class PersonaEntrada(serializers.Serializer):
    nombres = serializers.CharField(max_length=120, required=False)
    apellidos = serializers.CharField(max_length=120, required=False, allow_blank=True)
    pais = serializers.CharField(max_length=2, required=False)
    fecha_nacimiento = serializers.CharField(max_length=10, required=False, allow_blank=True, allow_null=True)
    telefono = serializers.CharField(max_length=32, required=False, allow_blank=True, allow_null=True)


class IdentificadorEntrada(serializers.Serializer):
    tipo = serializers.ChoiceField(choices=["DNI", "CODIGO_ESTUDIANTIL", "EMAIL"])
    valor = serializers.CharField(max_length=128)
    es_login = serializers.BooleanField(required=False, default=True)


class UsuarioEntrada(serializers.Serializer):
    rol = serializers.CharField(max_length=32)
    alias = serializers.CharField(max_length=64)
    idioma = serializers.CharField(max_length=8, required=False, allow_blank=True, default="")
    persona = PersonaEntrada()
    identificadores = IdentificadorEntrada(many=True, min_length=1)
    secreto = serializers.CharField(max_length=128, required=False, allow_blank=True, default="", trim_whitespace=False)
    secreto_definitivo = serializers.BooleanField(required=False, default=False)
    grupo_id = serializers.CharField(max_length=36, required=False, allow_blank=True, default="")


class UsuarioCambios(serializers.Serializer):
    alias = serializers.CharField(max_length=64, required=False)
    idioma = serializers.CharField(max_length=8, required=False)
    estado = serializers.ChoiceField(choices=["ACTIVO", "SUSPENDIDO", "RETIRADO"], required=False)
    persona = PersonaEntrada(required=False)
    identificadores = IdentificadorEntrada(many=True, required=False)


class RolAsignacion(serializers.Serializer):
    rol = serializers.CharField(max_length=32)


class PermisoAdicionalEntrada(serializers.Serializer):
    permiso = serializers.CharField(max_length=64)
    alcance = serializers.ChoiceField(choices=["SELF", "ASSIGNED_GROUPS", "ORGANIZATION"])
    motivo = serializers.CharField(max_length=200)
    vigente_hasta = serializers.IntegerField(required=False, allow_null=True, default=None)


class RestablecerEntrada(serializers.Serializer):
    secreto = serializers.CharField(max_length=128, required=False, allow_blank=True, default="", trim_whitespace=False)


class AutorizacionEntrada(serializers.Serializer):
    usuario_id = serializers.CharField(max_length=36)
    tipo = serializers.ChoiceField(choices=["DISPOSITIVO", "CODIGO"])
    dispositivo_id = serializers.CharField(max_length=36, required=False, allow_blank=True, default="")
    evaluacion_ref = serializers.CharField(max_length=200, required=False, allow_blank=True, default="")
    minutos = serializers.IntegerField(required=False, min_value=1, max_value=30, default=5)
    motivo = serializers.CharField(max_length=200, required=False, allow_blank=True, default="")


class PermisoRolEntrada(serializers.Serializer):
    codigo = serializers.CharField(max_length=64)
    alcance = serializers.CharField(max_length=20, required=False, allow_blank=True, allow_null=True, default=None)


class RolEntrada(serializers.Serializer):
    codigo = serializers.CharField(max_length=32)
    nombre = serializers.CharField(max_length=80)
    plantilla = serializers.CharField(max_length=32, required=False, default="TEACHER")
    menu_principal = serializers.ChoiceField(choices=["student", "teacher", "admin"], required=False)
    nivel = serializers.IntegerField(required=False, min_value=1, max_value=3)
    permisos = PermisoRolEntrada(many=True, required=False, default=list)


class PoliticaCambios(serializers.Serializer):
    tipo_identificador = serializers.ChoiceField(choices=["DNI", "CODIGO_ESTUDIANTIL", "EMAIL", "CUALQUIERA"], required=False)
    tipo_secreto = serializers.ChoiceField(choices=["PIN", "PASSWORD"], required=False)
    longitud_minima = serializers.IntegerField(required=False, min_value=4, max_value=64)
    exige_mayuscula = serializers.BooleanField(required=False)
    exige_minuscula = serializers.BooleanField(required=False)
    exige_digito = serializers.BooleanField(required=False)
    exige_simbolo = serializers.BooleanField(required=False)
    intentos_maximos = serializers.IntegerField(required=False, min_value=3, max_value=20)
    ventana_intentos_min = serializers.IntegerField(required=False, min_value=1, max_value=1440)
    bloqueo_minutos = serializers.IntegerField(required=False, min_value=1, max_value=1440)
    duracion_sesion_min = serializers.IntegerField(required=False, min_value=5, max_value=1440)
    vigencia_credencial_dias = serializers.IntegerField(required=False, allow_null=True, min_value=0)
    permite_acceso_temporal = serializers.BooleanField(required=False)


class GrupoEntrada(serializers.Serializer):
    codigo = serializers.CharField(max_length=32)
    nombre = serializers.CharField(max_length=120)
    periodo = serializers.CharField(max_length=16)
    politica_credencial_id = serializers.CharField(max_length=36, required=False, allow_blank=True, allow_null=True, default=None)


class GrupoCambios(serializers.Serializer):
    nombre = serializers.CharField(max_length=120, required=False)
    activo = serializers.BooleanField(required=False)
    politica_credencial_id = serializers.CharField(max_length=36, required=False, allow_blank=True, allow_null=True)


class MiembroEntrada(serializers.Serializer):
    usuario_id = serializers.CharField(max_length=36)
    papel = serializers.ChoiceField(choices=["ESTUDIANTE", "DOCENTE"], required=False, default="ESTUDIANTE")
