"""
Entidades del dominio de acceso. Son dataclasses planas: el ORM las mapea en
`infraestructura/repositorios.py`, nunca al revés.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .valores import (
    Alcance,
    ClaseSesion,
    EstadoUsuario,
    Menu,
    PapelGrupo,
    ResultadoIntento,
    TipoAutorizacion,
    TipoDispositivo,
    TipoIdentificador,
    TipoSecreto,
)


@dataclass
class Organizacion:
    id: str
    codigo: str
    nombre: str
    pais: str
    idioma: str
    locale: str
    zona_horaria: str
    creado_en: int


@dataclass
class PoliticaCredencial:
    id: str
    organizacion_id: str
    perfil: Menu
    tipo_identificador: TipoIdentificador
    tipo_secreto: TipoSecreto
    longitud_minima: int
    exige_mayuscula: bool
    exige_minuscula: bool
    exige_digito: bool
    exige_simbolo: bool
    intentos_maximos: int
    ventana_intentos_min: int
    bloqueo_minutos: int
    duracion_sesion_min: int
    vigencia_credencial_dias: int | None
    permite_acceso_temporal: bool
    creado_en: int
    actualizado_en: int

    def validar(self) -> None:
        if self.longitud_minima < 4:
            raise ValueError("La longitud mínima no puede ser menor que 4.")
        if self.tipo_secreto is TipoSecreto.PIN and not 4 <= self.longitud_minima <= 8:
            raise ValueError("Un PIN tiene entre 4 y 8 dígitos.")
        if self.tipo_secreto is TipoSecreto.PASSWORD and self.longitud_minima < 8:
            raise ValueError("Una contraseña tiene al menos 8 caracteres.")
        if self.intentos_maximos < 3:
            raise ValueError("Permita al menos 3 intentos antes de bloquear.")
        if self.duracion_sesion_min < 5 or self.duracion_sesion_min > 24 * 60:
            raise ValueError("La sesión dura entre 5 minutos y 24 horas.")
        if self.bloqueo_minutos < 1 or self.ventana_intentos_min < 1:
            raise ValueError("Ventana y bloqueo se expresan en minutos mayores que cero.")

    def admite_identificador(self, tipo: TipoIdentificador) -> bool:
        return self.tipo_identificador is TipoIdentificador.CUALQUIERA or self.tipo_identificador is tipo


@dataclass
class Permiso:
    codigo: str
    modulo: str
    descripcion: str
    alcance_maximo: Alcance


@dataclass
class RolPermiso:
    permiso_codigo: str
    alcance: Alcance


@dataclass
class Rol:
    id: str
    organizacion_id: str | None
    codigo: str
    nombre: str
    menu_principal: Menu
    nivel: int
    es_sistema: bool
    creado_en: int
    permisos: list[RolPermiso] = field(default_factory=list)


@dataclass
class Usuario:
    id: str
    organizacion_id: str
    rol_id: str
    estado: EstadoUsuario
    alias: str
    idioma: str
    creado_en: int
    actualizado_en: int
    creado_por: str | None = None
    ultimo_acceso_en: int | None = None

    @property
    def activo(self) -> bool:
        return self.estado is EstadoUsuario.ACTIVO


@dataclass
class Persona:
    usuario_id: str
    nombres: str
    apellidos: str
    pais: str
    fecha_nacimiento: str | None = None
    telefono: str | None = None
    actualizado_en: int = 0


@dataclass
class Identificador:
    id: str
    usuario_id: str
    tipo: TipoIdentificador
    valor: str
    es_login: bool
    creado_en: int
    verificado_en: int | None = None


@dataclass
class Credencial:
    id: str
    usuario_id: str
    tipo: TipoSecreto
    hash: str
    activa: bool
    debe_cambiar: bool
    creado_en: int
    expira_en: int | None = None
    sustituida_en: int | None = None
    creado_por: str | None = None

    def expirada(self, ahora: int) -> bool:
        return self.expira_en is not None and ahora >= self.expira_en


@dataclass
class UsuarioPermiso:
    id: str
    usuario_id: str
    permiso_codigo: str
    alcance: Alcance
    otorgado_por: str
    motivo: str
    vigente_desde: int
    vigente_hasta: int | None = None
    revocado_en: int | None = None

    def vigente(self, ahora: int) -> bool:
        if self.revocado_en is not None:
            return False
        if ahora < self.vigente_desde:
            return False
        return self.vigente_hasta is None or ahora < self.vigente_hasta


@dataclass
class Grupo:
    id: str
    organizacion_id: str
    codigo: str
    nombre: str
    periodo: str
    activo: bool
    creado_en: int
    politica_credencial_id: str | None = None


@dataclass
class MiembroGrupo:
    id: str
    grupo_id: str
    usuario_id: str
    papel: PapelGrupo
    desde: int
    hasta: int | None = None

    def vigente(self, ahora: int) -> bool:
        return self.hasta is None or ahora < self.hasta


@dataclass
class Dispositivo:
    id: str
    organizacion_id: str
    identificador: str
    nombre: str
    tipo: TipoDispositivo
    activo: bool
    registrado_en: int
    ultimo_visto_en: int


@dataclass
class Sesion:
    id: str
    usuario_id: str
    clase: ClaseSesion
    emitida_en: int
    expira_en: int
    dispositivo_id: str | None = None
    ultimo_uso_en: int | None = None
    revocada_en: int | None = None
    motivo_revocacion: str | None = None
    evaluacion_ref: str | None = None

    def vigente(self, ahora: int) -> bool:
        return self.revocada_en is None and ahora < self.expira_en


@dataclass
class IntentoAcceso:
    identificador_hmac: str
    resultado: ResultadoIntento
    motivo: str
    momento: int
    usuario_id: str | None = None
    dispositivo_id: str | None = None
    autorizacion_id: str | None = None
    id: int | None = None


@dataclass
class AutorizacionTemporal:
    id: str
    usuario_id: str
    otorgada_por: str
    tipo: TipoAutorizacion
    secreto_hash: str
    creada_en: int
    expira_en: int
    motivo: str
    dispositivo_id: str | None = None
    evaluacion_ref: str | None = None
    usada_en: int | None = None
    revocada_en: int | None = None
    sesion_id: str | None = None

    def canjeable(self, ahora: int) -> bool:
        return self.usada_en is None and self.revocada_en is None and ahora < self.expira_en


@dataclass
class EventoSalida:
    agregado_tipo: str
    agregado_id: str
    tipo_evento: str
    carga: dict[str, Any]
    creado_en: int
    id: int | None = None
    publicado_en: int | None = None
    intentos: int = 0


@dataclass(frozen=True)
class Concesion:
    """Un permiso efectivo del actor: el alcance máximo entre el rol y los adicionales."""

    permiso_codigo: str
    alcance: Alcance
    origen: str  # "rol" | "adicional"
    vigente_hasta: int | None = None


@dataclass(frozen=True)
class Principal:
    """Quién actúa. Lo construye la autenticación y lo consumen las políticas y los casos de uso."""

    usuario_id: str
    organizacion_id: str
    rol_id: str
    rol_codigo: str
    menu: Menu
    nivel: int
    sesion_id: str
    clase_sesion: ClaseSesion
    debe_cambiar_credencial: bool
    dispositivo_id: str | None = None
    evaluacion_ref: str | None = None

    # DRF sólo necesita esto para tratar al portador como autenticado.
    is_authenticated = True
    is_anonymous = False
