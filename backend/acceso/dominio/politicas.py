"""
Policy Pattern: las reglas de autorización, fortaleza de secretos y bloqueo por
intentos viven aquí, separadas de vistas, serializers y ORM. Se prueban con
datos en memoria.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from . import errores, plantillas
from .entidades import Concesion, IntentoAcceso, PoliticaCredencial, Principal, Rol, UsuarioPermiso
from .valores import Alcance, ClaseSesion, Password, Pin, ResultadoIntento, TipoSecreto

# ------------------------------------------------------------------ objetivos


@dataclass(frozen=True)
class ObjetivoUsuario:
    usuario_id: str
    organizacion_id: str
    nivel: int


@dataclass(frozen=True)
class ObjetivoGrupo:
    grupo_id: str
    organizacion_id: str


@dataclass(frozen=True)
class ObjetivoOrganizacion:
    organizacion_id: str


@dataclass(frozen=True)
class SinObjetivo:
    """Operación sin objeto concreto (listar dispositivos, leer catálogos): basta tener el permiso."""


Objetivo = ObjetivoUsuario | ObjetivoGrupo | ObjetivoOrganizacion | SinObjetivo


@dataclass(frozen=True)
class Decision:
    permitido: bool
    permiso: str
    codigo: str = "ok"
    alcance_requerido: Alcance | None = None
    alcance_concedido: Alcance | None = None

    def exigir(self, ocultar_existencia: bool = False) -> "Decision":
        """Lanza el error de dominio correspondiente si la decisión es negativa."""
        if self.permitido:
            return self
        extra = {
            "permiso": self.permiso,
            "alcance_requerido": self.alcance_requerido.value if self.alcance_requerido else None,
            "alcance_concedido": self.alcance_concedido.value if self.alcance_concedido else None,
        }
        if self.codigo == "debe_cambiar_credencial":
            raise errores.DebeCambiarCredencial(**extra)
        if self.codigo == "sesion_temporal_limitada":
            raise errores.SesionTemporalLimitada(**extra)
        # 403 = no puede hacer esta operación en absoluto; 404 = puede, pero no sobre este objetivo
        # (no se revela si existe). Otra organización siempre se oculta.
        if self.codigo == "fuera_de_organizacion" or (ocultar_existencia and self.alcance_concedido is not None):
            raise errores.NoEncontrado(**extra)
        raise errores.SinPermiso(**extra)


@dataclass
class ContextoActor:
    """Todo lo que la política necesita saber del actor; lo carga el caso de uso una sola vez."""

    principal: Principal
    concesiones: dict[str, Concesion]
    grupos_docente: frozenset[str] = field(default_factory=frozenset)  # grupos donde es DOCENTE vigente
    grupos_miembro: frozenset[str] = field(default_factory=frozenset)  # grupos donde es miembro vigente (cualquier papel)


# ---------------------------------------------------------------- autorización


class PoliticaAutorizacion:
    """RBAC + alcance + contexto. Denegar por defecto."""

    @staticmethod
    def concesiones_efectivas(rol: Rol, adicionales: list[UsuarioPermiso], ahora: int) -> dict[str, Concesion]:
        salida: dict[str, Concesion] = {}
        for rp in rol.permisos:
            salida[rp.permiso_codigo] = Concesion(rp.permiso_codigo, rp.alcance, "rol")
        for extra in adicionales:
            if not extra.vigente(ahora):
                continue
            actual = salida.get(extra.permiso_codigo)
            if actual is None or extra.alcance.orden > actual.alcance.orden:
                salida[extra.permiso_codigo] = Concesion(extra.permiso_codigo, extra.alcance, "adicional", extra.vigente_hasta)
        return salida

    @staticmethod
    def alcance_requerido(ctx: ContextoActor, objetivo: Objetivo, grupos_objetivo: frozenset[str]) -> Alcance | None:
        """El alcance mínimo con el que el actor alcanza al objetivo; None si no está en su organización."""
        actor = ctx.principal
        if isinstance(objetivo, SinObjetivo):
            return Alcance.SELF
        if objetivo.organizacion_id != actor.organizacion_id:
            return None
        if isinstance(objetivo, ObjetivoOrganizacion):
            return Alcance.ORGANIZATION
        if isinstance(objetivo, ObjetivoUsuario):
            if objetivo.usuario_id == actor.usuario_id:
                return Alcance.SELF
            if objetivo.nivel == 1 and ctx.grupos_docente & grupos_objetivo:
                return Alcance.ASSIGNED_GROUPS
            return Alcance.ORGANIZATION
        # grupo
        if objetivo.grupo_id in ctx.grupos_docente:
            return Alcance.ASSIGNED_GROUPS
        if objetivo.grupo_id in ctx.grupos_miembro:
            return Alcance.SELF
        return Alcance.ORGANIZATION

    def transversal(self, ctx: ContextoActor, permiso: str) -> Decision | None:
        """Reglas previas a cualquier permiso: credencial provisional y sesión temporal."""
        actor = ctx.principal
        if actor.debe_cambiar_credencial and permiso not in plantillas.PERMISOS_CON_CREDENCIAL_PROVISIONAL:
            return Decision(False, permiso, "debe_cambiar_credencial")
        if actor.clase_sesion is ClaseSesion.TEMPORAL and permiso not in plantillas.PERMISOS_SESION_TEMPORAL:
            return Decision(False, permiso, "sesion_temporal_limitada")
        return None

    def alcance_concedido(self, ctx: ContextoActor, permiso: str) -> Alcance | None:
        """El alcance efectivo con el que el actor tiene el permiso, tras las reglas transversales."""
        if self.transversal(ctx, permiso) is not None:
            return None
        concesion = ctx.concesiones.get(permiso)
        if concesion is None:
            return None
        if ctx.principal.clase_sesion is ClaseSesion.TEMPORAL:
            return Alcance.SELF
        return concesion.alcance

    def decidir(self, ctx: ContextoActor, permiso: str, objetivo: Objetivo,
                grupos_objetivo: frozenset[str] = frozenset()) -> Decision:
        previa = self.transversal(ctx, permiso)
        if previa is not None:
            return previa
        requerido = self.alcance_requerido(ctx, objetivo, grupos_objetivo)
        if requerido is None:
            return Decision(False, permiso, "fuera_de_organizacion")
        concedido = self.alcance_concedido(ctx, permiso)
        if concedido is None:
            return Decision(False, permiso, "sin_permiso", requerido, None)
        if not concedido.cubre(requerido):
            return Decision(False, permiso, "sin_permiso", requerido, concedido)
        if isinstance(objetivo, ObjetivoUsuario) and requerido is not Alcance.SELF:
            # Jerarquía: con alcance de grupos sólo se administran estudiantes; con alcance de
            # organización, nunca a alguien de nivel superior al propio.
            if requerido is Alcance.ASSIGNED_GROUPS and objetivo.nivel != 1:
                return Decision(False, permiso, "sin_permiso", Alcance.ORGANIZATION, concedido)
            if ctx.principal.nivel < objetivo.nivel:
                return Decision(False, permiso, "sin_permiso", requerido, concedido)
        return Decision(True, permiso, "ok", requerido, concedido)

    @staticmethod
    def alcance_otorgable(permiso_maximo: Alcance, alcance_pedido: Alcance, alcance_del_actor: Alcance | None) -> Alcance:
        """Un actor no puede otorgar más alcance del que él mismo tiene ni más que el techo del permiso."""
        if alcance_pedido.orden > permiso_maximo.orden:
            raise errores.DatosInvalidos(
                f"El permiso admite como máximo el alcance {permiso_maximo.value}.")
        if alcance_del_actor is None or alcance_pedido.orden > alcance_del_actor.orden:
            raise errores.SinPermiso("No puede otorgar un alcance mayor del que usted tiene sobre ese permiso.")
        return alcance_pedido


# ------------------------------------------------------------------ fortaleza


class PoliticaFortaleza:
    """Valida un secreto contra la política de credenciales vigente para el usuario."""

    @staticmethod
    def validar(secreto: str, politica: PoliticaCredencial) -> list[str]:
        reglas: list[str] = []
        if politica.tipo_secreto is TipoSecreto.PIN:
            try:
                pin = Pin(secreto)
            except ValueError as error:
                return [str(error)]
            if len(pin.valor) < politica.longitud_minima:
                reglas.append(f"El PIN debe tener al menos {politica.longitud_minima} dígitos.")
            if len(pin.valor) > 8:
                reglas.append("El PIN no puede tener más de 8 dígitos.")
            if pin.es_trivial():
                reglas.append("El PIN es demasiado fácil de adivinar (repetido o en secuencia).")
            return reglas
        try:
            clave = Password(secreto)
        except ValueError as error:
            return [str(error)]
        if len(clave.valor) < politica.longitud_minima:
            reglas.append(f"La contraseña debe tener al menos {politica.longitud_minima} caracteres.")
        if politica.exige_mayuscula and not clave.tiene_mayuscula:
            reglas.append("Debe incluir al menos una letra mayúscula.")
        if politica.exige_minuscula and not clave.tiene_minuscula:
            reglas.append("Debe incluir al menos una letra minúscula.")
        if politica.exige_digito and not clave.tiene_digito:
            reglas.append("Debe incluir al menos un dígito.")
        if politica.exige_simbolo and not clave.tiene_simbolo:
            reglas.append("Debe incluir al menos un símbolo (p. ej. . , ! # $ %).")
        return reglas

    @classmethod
    def exigir(cls, secreto: str, politica: PoliticaCredencial) -> None:
        reglas = cls.validar(secreto, politica)
        if reglas:
            raise errores.SecretoDebil("La clave no cumple la política del colegio.", reglas=reglas)


# -------------------------------------------------------------------- bloqueo


@dataclass(frozen=True)
class EstadoBloqueo:
    bloqueado: bool
    fallos: int
    hasta: int | None = None

    def segundos_restantes(self, ahora: int) -> int:
        if not self.bloqueado or self.hasta is None:
            return 0
        return max(0, (self.hasta - ahora + 999) // 1000)


class PoliticaBloqueo:
    """Bloqueo automático calculado sobre el registro de intentos, sin contador desnormalizado."""

    @staticmethod
    def evaluar(intentos_desc: list[IntentoAcceso], politica: PoliticaCredencial, ahora: int) -> EstadoBloqueo:
        ventana_ms = max(politica.ventana_intentos_min, politica.bloqueo_minutos) * 60_000
        fallos = 0
        ultimo_fallo: int | None = None
        for intento in intentos_desc:  # del más reciente al más antiguo
            if intento.resultado in (ResultadoIntento.EXITO, ResultadoIntento.DESBLOQUEO):
                break
            if intento.momento < ahora - ventana_ms:
                break
            if intento.resultado is ResultadoIntento.FALLO:
                fallos += 1
                if ultimo_fallo is None:
                    ultimo_fallo = intento.momento
        if fallos >= politica.intentos_maximos and ultimo_fallo is not None:
            hasta = ultimo_fallo + politica.bloqueo_minutos * 60_000
            if ahora < hasta:
                return EstadoBloqueo(True, fallos, hasta)
        return EstadoBloqueo(False, fallos, None)


def politica_aplicable(del_perfil: PoliticaCredencial, del_grupo: PoliticaCredencial | None) -> PoliticaCredencial:
    """El grupo puede sobrescribir la política del perfil (grados superiores con contraseña)."""
    return del_grupo or del_perfil
