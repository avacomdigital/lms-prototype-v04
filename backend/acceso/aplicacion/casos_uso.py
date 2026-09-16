"""
Casos de uso del módulo de acceso (Use Case Pattern).

Cada operación importante es una clase con `ejecutar(...)`. Recibe los puertos por
el contenedor, abre una Unidad de Trabajo, aplica las políticas del dominio y
devuelve diccionarios planos (DTO) que la capa HTTP serializa tal cual.

Nada de este archivo importa Django, DRF, Pydantic, SQLAlchemy ni FastAPI.
"""
from __future__ import annotations

import hmac
import uuid
from dataclasses import dataclass
from typing import Any, Iterable

from ..dominio import errores, plantillas
from ..dominio.entidades import (
    AutorizacionTemporal,
    Credencial,
    Dispositivo,
    EventoSalida,
    Grupo,
    Identificador,
    IntentoAcceso,
    MiembroGrupo,
    Organizacion,
    Permiso,
    Persona,
    PoliticaCredencial,
    Principal,
    Rol,
    RolPermiso,
    Sesion,
    Usuario,
    UsuarioPermiso,
)
from ..dominio.politicas import (
    ContextoActor,
    ObjetivoGrupo,
    ObjetivoOrganizacion,
    ObjetivoUsuario,
    PoliticaAutorizacion,
    PoliticaBloqueo,
    PoliticaFortaleza,
    SinObjetivo,
    politica_aplicable,
)
from ..dominio.valores import (
    Alcance,
    ClaseSesion,
    CountryCode,
    DocumentNumber,
    EstadoUsuario,
    LanguageCode,
    LocaleCode,
    Menu,
    PapelGrupo,
    PermissionCode,
    ResultadoIntento,
    TipoAutorizacion,
    TipoDispositivo,
    TipoIdentificador,
    TipoSecreto,
    UserId,
)
from .puertos import Azar, Cifrador, EmisorTokens, FabricaUoW, Hasher, Reloj, UnidadDeTrabajo

MINUTO_MS = 60_000
DIA_MS = 24 * 60 * MINUTO_MS


@dataclass
class Servicios:
    """Los puertos que necesitan los casos de uso. Los arma `infraestructura/contenedor.py`."""

    uow: FabricaUoW
    hasher: Hasher
    cifrador: Cifrador
    tokens: EmisorTokens
    reloj: Reloj
    azar: Azar


def _nuevo_id() -> str:
    return str(uuid.uuid4())


def _texto(valor, nombre: str, maximo: int, obligatorio: bool = True) -> str:
    t = str(valor or "").strip()
    if not t and obligatorio:
        raise errores.DatosInvalidos(f"Falta {nombre}.")
    if len(t) > maximo:
        raise errores.DatosInvalidos(f"{nombre} supera los {maximo} caracteres.")
    return t


def _enum(cls, valor, nombre: str):
    if isinstance(valor, cls):
        return valor
    try:
        texto = str(valor or "").strip()
        return cls(texto.lower() if cls is Menu else texto.upper())
    except ValueError:
        raise errores.DatosInvalidos(f"{nombre} desconocido: {valor!r}.")


# ================================================================== soporte


class Base:
    politica = PoliticaAutorizacion()

    def __init__(self, servicios: Servicios):
        self.s = servicios

    # ------------------------------------------------------------ utilidades
    def ahora(self) -> int:
        return self.s.reloj.ahora_ms()

    def organizacion(self, uow: UnidadDeTrabajo) -> Organizacion:
        org = uow.organizaciones.unica()
        if org is None:
            raise errores.Conflicto("El nodo aún no está instalado: falta la organización.", codigo="no_instalado")
        return org

    def evento(self, uow: UnidadDeTrabajo, agregado_tipo: str, agregado_id: str, tipo: str, carga: dict | None = None):
        uow.outbox.publicar(EventoSalida(agregado_tipo, agregado_id, tipo, carga or {}, self.ahora()))

    def auditar(self, uow: UnidadDeTrabajo, actor_id: str, accion: str, tabla: str = "", objeto_id: str = "", nuevo=None):
        uow.auditoria.registrar(actor_id or "", accion, tabla, str(objeto_id or ""), nuevo)

    # -------------------------------------------------------------- políticas
    def politica_de(self, uow: UnidadDeTrabajo, usuario: Usuario, rol: Rol) -> PoliticaCredencial:
        del_perfil = uow.politicas.por_perfil(usuario.organizacion_id, rol.menu_principal)
        if del_perfil is None:
            raise errores.Conflicto(f"La organización no tiene política de credenciales para el perfil {rol.menu_principal.value}.")
        del_grupo = uow.grupos.politica_de_grupo(usuario.id, self.ahora()) if rol.nivel == 1 else None
        return politica_aplicable(del_perfil, del_grupo)

    def rol_de(self, uow: UnidadDeTrabajo, usuario: Usuario) -> Rol:
        rol = uow.roles.por_id(usuario.rol_id)
        if rol is None:
            raise errores.Conflicto("El usuario apunta a un rol que ya no existe.")
        return rol

    # ------------------------------------------------------------ autorización
    def contexto(self, uow: UnidadDeTrabajo, principal: Principal) -> ContextoActor:
        rol = uow.roles.por_id(principal.rol_id)
        if rol is None:
            raise errores.SesionInvalida("El rol de la sesión ya no existe.")
        ahora = self.ahora()
        concesiones = self.politica.concesiones_efectivas(rol, uow.usuarios.permisos_adicionales(principal.usuario_id), ahora)
        return ContextoActor(
            principal=principal,
            concesiones=concesiones,
            grupos_docente=uow.grupos.ids_grupos(principal.usuario_id, PapelGrupo.DOCENTE, ahora),
            grupos_miembro=uow.grupos.ids_grupos(principal.usuario_id, None, ahora),
        )

    def exigir(self, ctx: ContextoActor, permiso: str, objetivo, grupos_objetivo: frozenset[str] = frozenset(),
               ocultar: bool = False):
        return self.politica.decidir(ctx, permiso, objetivo, grupos_objetivo).exigir(ocultar_existencia=ocultar)

    def exigir_alcance(self, ctx: ContextoActor, permiso: str) -> Alcance:
        """El alcance con el que el actor tiene el permiso; lanza el error preciso si no lo tiene."""
        previa = self.politica.transversal(ctx, permiso)
        if previa is not None:
            previa.exigir()
        alcance = self.politica.alcance_concedido(ctx, permiso)
        if alcance is None:
            raise errores.SinPermiso(permiso=permiso)
        return alcance

    def ejecutar_registrando(self, cuerpo):
        """Ejecuta `cuerpo(uow)`; si termina en un error de acceso, CONFIRMA igualmente la transacción
        (el intento fallido y su auditoría deben quedar escritos) y relanza el error después."""
        error: errores.ErrorAcceso | None = None
        with self.s.uow() as uow:
            try:
                return cuerpo(uow)
            except errores.ErrorAcceso as capturado:
                error = capturado
        raise error

    def usuario_objetivo(self, uow: UnidadDeTrabajo, ctx: ContextoActor, usuario_id: str, permiso: str) -> tuple[Usuario, Rol]:
        """Carga al usuario objetivo y exige el permiso sobre él. Fuera de alcance → 404 (no se revela existencia)."""
        usuario = uow.usuarios.por_id(usuario_id)
        if usuario is None:
            raise errores.NoEncontrado("No existe ese usuario.")
        rol = self.rol_de(uow, usuario)
        grupos = uow.grupos.ids_grupos(usuario.id, None, self.ahora())
        self.exigir(ctx, permiso, ObjetivoUsuario(usuario.id, usuario.organizacion_id, rol.nivel), grupos, ocultar=True)
        return usuario, rol

    def grupo_objetivo(self, uow: UnidadDeTrabajo, ctx: ContextoActor, grupo_id: str, permiso: str) -> Grupo:
        grupo = uow.grupos.por_id(grupo_id)
        if grupo is None:
            raise errores.NoEncontrado("No existe ese grupo.")
        self.exigir(ctx, permiso, ObjetivoGrupo(grupo.id, grupo.organizacion_id), ocultar=True)
        return grupo

    # ----------------------------------------------------------------- DTOs
    def dto_usuario(self, uow: UnidadDeTrabajo, usuario: Usuario, rol: Rol | None = None, incluir_pii: bool = True,
                    incluir_grupos: bool = True) -> dict[str, Any]:
        rol = rol or self.rol_de(uow, usuario)
        ahora = self.ahora()
        credencial = uow.credenciales.activa(usuario.id)
        politica = self.politica_de(uow, usuario, rol)
        bloqueo = PoliticaBloqueo.evaluar(
            uow.intentos.recientes(usuario.id, ahora - max(politica.ventana_intentos_min, politica.bloqueo_minutos) * MINUTO_MS),
            politica, ahora)
        salida: dict[str, Any] = {
            "id": usuario.id,
            "alias": usuario.alias,
            "idioma": usuario.idioma,
            "rol": rol.codigo,
            "menu": rol.menu_principal.value,
            "nivel": rol.nivel,
            "estado": usuario.estado.value,
            "bloqueado_hasta": bloqueo.hasta if bloqueo.bloqueado else None,
            "intentos_fallidos": bloqueo.fallos,
            "tiene_credencial": credencial is not None,
            "debe_cambiar_credencial": bool(credencial and (credencial.debe_cambiar or credencial.expirada(ahora))),
            "tipo_secreto": politica.tipo_secreto.value,
            "tipo_identificador": politica.tipo_identificador.value,
            "creado_en": usuario.creado_en,
            "ultimo_acceso_en": usuario.ultimo_acceso_en,
        }
        if incluir_pii:
            persona = uow.usuarios.persona(usuario.id)
            salida["persona"] = self._dto_persona(persona) if persona else None
            salida["identificadores"] = [
                {"tipo": i.tipo.value, "valor": i.valor, "es_login": i.es_login} for i in uow.usuarios.identificadores(usuario.id)
            ]
        if incluir_grupos:
            membresias = uow.grupos.membresias(usuario.id)
            grupos = {g.id: g for g in uow.grupos.listar(usuario.organizacion_id, [m.grupo_id for m in membresias])}
            salida["grupos"] = [
                {"id": m.grupo_id, "codigo": grupos[m.grupo_id].codigo, "nombre": grupos[m.grupo_id].nombre,
                 "periodo": grupos[m.grupo_id].periodo, "papel": m.papel.value}
                for m in membresias if m.grupo_id in grupos
            ]
        return salida

    @staticmethod
    def _dto_persona(persona: Persona) -> dict:
        return {"nombres": persona.nombres, "apellidos": persona.apellidos, "pais": persona.pais,
                "fecha_nacimiento": persona.fecha_nacimiento, "telefono": persona.telefono}

    @staticmethod
    def dto_sesion(sesion: Sesion, alias: str = "", dispositivo: str | None = None) -> dict:
        return {"id": sesion.id, "usuario_id": sesion.usuario_id, "alias": alias, "clase": sesion.clase.value,
                "dispositivo_id": sesion.dispositivo_id, "dispositivo": dispositivo, "emitida_en": sesion.emitida_en,
                "expira_en": sesion.expira_en, "ultimo_uso_en": sesion.ultimo_uso_en, "revocada_en": sesion.revocada_en,
                "motivo_revocacion": sesion.motivo_revocacion, "evaluacion_ref": sesion.evaluacion_ref}

    @staticmethod
    def dto_rol(rol: Rol) -> dict:
        return {"id": rol.id, "codigo": rol.codigo, "nombre": rol.nombre, "menu_principal": rol.menu_principal.value,
                "nivel": rol.nivel, "es_sistema": rol.es_sistema, "organizacion_id": rol.organizacion_id,
                "permisos": [{"codigo": p.permiso_codigo, "alcance": p.alcance.value} for p in rol.permisos]}

    @staticmethod
    def dto_politica(p: PoliticaCredencial) -> dict:
        return {"id": p.id, "perfil": p.perfil.value, "tipo_identificador": p.tipo_identificador.value,
                "tipo_secreto": p.tipo_secreto.value, "longitud_minima": p.longitud_minima,
                "exige_mayuscula": p.exige_mayuscula, "exige_minuscula": p.exige_minuscula,
                "exige_digito": p.exige_digito, "exige_simbolo": p.exige_simbolo,
                "intentos_maximos": p.intentos_maximos, "ventana_intentos_min": p.ventana_intentos_min,
                "bloqueo_minutos": p.bloqueo_minutos, "duracion_sesion_min": p.duracion_sesion_min,
                "vigencia_credencial_dias": p.vigencia_credencial_dias,
                "permite_acceso_temporal": p.permite_acceso_temporal, "actualizado_en": p.actualizado_en}

    @staticmethod
    def dto_grupo(g: Grupo) -> dict:
        return {"id": g.id, "codigo": g.codigo, "nombre": g.nombre, "periodo": g.periodo, "activo": g.activo,
                "politica_credencial_id": g.politica_credencial_id, "creado_en": g.creado_en}

    @staticmethod
    def dto_dispositivo(d: Dispositivo) -> dict:
        return {"id": d.id, "identificador": d.identificador, "nombre": d.nombre, "tipo": d.tipo.value,
                "activo": d.activo, "registrado_en": d.registrado_en, "ultimo_visto_en": d.ultimo_visto_en}

    @staticmethod
    def dto_autorizacion(a: AutorizacionTemporal, alias: str = "", dispositivo: str | None = None) -> dict:
        return {"id": a.id, "usuario_id": a.usuario_id, "alias": alias, "otorgada_por": a.otorgada_por,
                "tipo": a.tipo.value, "dispositivo_id": a.dispositivo_id, "dispositivo": dispositivo,
                "evaluacion_ref": a.evaluacion_ref, "creada_en": a.creada_en, "expira_en": a.expira_en,
                "usada_en": a.usada_en, "revocada_en": a.revocada_en, "sesion_id": a.sesion_id, "motivo": a.motivo}

    # ------------------------------------------------------------ credenciales
    def generar_secreto(self, politica: PoliticaCredencial) -> str:
        for _ in range(50):
            if politica.tipo_secreto is TipoSecreto.PIN:
                candidato = self.s.azar.pin(politica.longitud_minima)
            else:
                candidato = self.s.azar.password(max(politica.longitud_minima, 12))
            if not PoliticaFortaleza.validar(candidato, politica):
                return candidato
        raise errores.Conflicto("No se pudo generar una clave que cumpla la política.")

    def establecer_credencial(self, uow: UnidadDeTrabajo, usuario: Usuario, politica: PoliticaCredencial, secreto: str,
                              creado_por: str | None, debe_cambiar: bool) -> Credencial:
        PoliticaFortaleza.exigir(secreto, politica)
        for anterior in uow.credenciales.historial(usuario.id, plantillas.CREDENCIALES_NO_REUTILIZABLES):
            if self.s.hasher.verificar(anterior.hash, secreto):
                raise errores.SecretoDebil("No puede reutilizar una clave anterior.", reglas=["Elija una clave distinta de las últimas usadas."])
        ahora = self.ahora()
        uow.credenciales.desactivar(usuario.id, ahora)
        credencial = Credencial(
            id=_nuevo_id(), usuario_id=usuario.id, tipo=politica.tipo_secreto, hash=self.s.hasher.hash(secreto),
            activa=True, debe_cambiar=debe_cambiar, creado_en=ahora,
            expira_en=(ahora + politica.vigencia_credencial_dias * DIA_MS) if politica.vigencia_credencial_dias else None,
            creado_por=creado_por,
        )
        uow.credenciales.guardar(credencial)
        return credencial

    # ----------------------------------------------------------------- sesión
    def abrir_sesion(self, uow: UnidadDeTrabajo, usuario: Usuario, rol: Rol, politica: PoliticaCredencial,
                     dispositivo: Dispositivo | None, clase: ClaseSesion, debe_cambiar: bool,
                     evaluacion_ref: str | None = None) -> dict:
        ahora = self.ahora()
        sesion = Sesion(
            id=_nuevo_id(), usuario_id=usuario.id, clase=clase, emitida_en=ahora,
            expira_en=ahora + politica.duracion_sesion_min * MINUTO_MS,
            dispositivo_id=dispositivo.id if dispositivo else None, evaluacion_ref=evaluacion_ref,
        )
        uow.sesiones.guardar(sesion)
        usuario.ultimo_acceso_en = ahora
        usuario.actualizado_en = ahora
        uow.usuarios.guardar(usuario)
        token = self.s.tokens.emitir({
            "iss": "avacom-lms", "sub": usuario.id, "jti": sesion.id, "org": usuario.organizacion_id,
            "rol": rol.codigo, "menu": rol.menu_principal.value, "nivel": rol.nivel,
            "dev": sesion.dispositivo_id, "clase": clase.value, "eval": evaluacion_ref,
            "iat": ahora // 1000, "exp": sesion.expira_en // 1000,
        })
        return {
            "token": token, "tipo": "Bearer", "expira_en": sesion.expira_en, "sesion_id": sesion.id,
            "usuario": {"id": usuario.id, "alias": usuario.alias, "rol": rol.codigo, "menu": rol.menu_principal.value,
                        "nivel": rol.nivel, "debe_cambiar_credencial": debe_cambiar, "clase_sesion": clase.value,
                        "evaluacion_ref": evaluacion_ref},
        }

    def dispositivo_por_identificador(self, uow: UnidadDeTrabajo, organizacion_id: str, identificador: str | None) -> Dispositivo | None:
        if not identificador:
            return None
        dispositivo = uow.dispositivos.por_identificador(organizacion_id, str(identificador).strip())
        if dispositivo and dispositivo.activo:
            dispositivo.ultimo_visto_en = self.ahora()
            uow.dispositivos.guardar(dispositivo)
            return dispositivo
        return None


def asegurar_plantillas(uow: UnidadDeTrabajo, ahora: int) -> None:
    """Siembra el catálogo de permisos y los roles de sistema si faltan (idempotente)."""
    existentes = {p.codigo for p in uow.permisos.listar()}
    for codigo, modulo, descripcion, maximo in plantillas.PERMISOS:
        if codigo not in existentes:
            uow.permisos.guardar(Permiso(codigo, modulo, descripcion, maximo))
    for codigo, (nombre, menu, nivel, permisos) in plantillas.ROLES_SISTEMA.items():
        if uow.roles.por_codigo("", codigo) is None:
            uow.roles.guardar(Rol(
                id=_nuevo_id(), organizacion_id=None, codigo=codigo, nombre=nombre, menu_principal=menu, nivel=nivel,
                es_sistema=True, creado_en=ahora,
                permisos=[RolPermiso(p, a) for p, a in permisos.items()],
            ))


# ============================================================ instalación


class InstalarNodo(Base):
    """Primer arranque: organización, políticas por defecto y primer administrador."""

    def ejecutar(self, organizacion: dict, administrador: dict) -> dict:
        with self.s.uow() as uow:
            if uow.organizaciones.unica() is not None:
                raise errores.YaInstalado()
            ahora = self.ahora()
            asegurar_plantillas(uow, ahora)
            locale = LocaleCode(organizacion.get("locale") or f"{organizacion.get('idioma', 'es')}-{organizacion.get('pais', 'CO')}")
            org = Organizacion(
                id=_nuevo_id(),
                codigo=_texto(organizacion.get("codigo"), "el código de la organización", 32).upper(),
                nombre=_texto(organizacion.get("nombre"), "el nombre de la organización", 200),
                pais=str(CountryCode(organizacion.get("pais") or "CO")),
                idioma=str(LanguageCode(organizacion.get("idioma") or locale.idioma.valor)),
                locale=str(locale),
                zona_horaria=_texto(organizacion.get("zona_horaria") or "America/Bogota", "la zona horaria", 64),
                creado_en=ahora,
            )
            uow.organizaciones.guardar(org)
            for perfil, valores in plantillas.POLITICAS_POR_DEFECTO.items():
                uow.politicas.guardar(PoliticaCredencial(id=_nuevo_id(), organizacion_id=org.id, perfil=perfil,
                                                         creado_en=ahora, actualizado_en=ahora, **valores))
            rol_admin = uow.roles.por_codigo(org.id, "ADMIN")
            datos_admin = {
                "rol": "ADMIN",
                "alias": administrador.get("alias") or "Administración",
                "idioma": org.idioma,
                "persona": {"nombres": administrador.get("nombres", ""), "apellidos": administrador.get("apellidos", ""),
                            "pais": org.pais},
                "identificadores": [{"tipo": "DNI", "valor": administrador.get("dni"), "es_login": True}],
                "secreto": administrador.get("password"),
            }
            creado = CrearUsuario(self.s)._crear(uow, org, rol_admin, datos_admin, creado_por=None,
                                                 provisional=not administrador.get("password"))
            self.auditar(uow, creado["id"], "acceso.instalacion", "m01_organizacion", org.id, {"codigo": org.codigo})
            self.evento(uow, "organizacion", org.id, "acceso.organizacion.instalada", {"codigo": org.codigo})
            salida = {"organizacion": dto_organizacion(org),
                      "administrador": {"id": creado["id"], "alias": creado["alias"]}}
            if "secreto_inicial" in creado:
                salida["password_inicial"] = creado["secreto_inicial"]
            return salida


def dto_organizacion(org: Organizacion) -> dict:
    return {"id": org.id, "codigo": org.codigo, "nombre": org.nombre, "pais": org.pais, "idioma": org.idioma,
            "locale": org.locale, "zona_horaria": org.zona_horaria}


class ConsultarConfiguracion(Base):
    """Lo que la tableta necesita para pintar la pantalla de acceso. Sin PII."""

    def ejecutar(self) -> dict:
        with self.s.uow() as uow:
            org = uow.organizaciones.unica()
            if org is None:
                return {"instalado": False, "claves_derivadas": self.s.cifrador.claves_derivadas()}
            perfiles = {}
            duracion = 240
            for p in uow.politicas.por_organizacion(org.id):
                perfiles[p.perfil.value] = {
                    "tipo_identificador": p.tipo_identificador.value, "tipo_secreto": p.tipo_secreto.value,
                    "longitud_minima": p.longitud_minima, "permite_acceso_temporal": p.permite_acceso_temporal,
                }
                if p.perfil is Menu.STUDENT:
                    duracion = p.duracion_sesion_min
            return {"instalado": True, "organizacion": dto_organizacion(org), "perfiles": perfiles,
                    "duracion_sesion_min": duracion, "claves_derivadas": self.s.cifrador.claves_derivadas()}


class RegistrarDispositivo(Base):
    def ejecutar(self, identificador: str, nombre: str, tipo: str = "TABLETA") -> tuple[dict, bool]:
        with self.s.uow() as uow:
            org = self.organizacion(uow)
            identificador = _texto(identificador, "el identificador del dispositivo", 128)
            nombre = _texto(nombre, "el nombre del dispositivo", 64)
            ahora = self.ahora()
            existente = uow.dispositivos.por_identificador(org.id, identificador)
            if existente:
                existente.ultimo_visto_en = ahora
                if nombre and existente.nombre != nombre:
                    existente.nombre = nombre
                uow.dispositivos.guardar(existente)
                return self.dto_dispositivo(existente), False
            dispositivo = Dispositivo(id=_nuevo_id(), organizacion_id=org.id, identificador=identificador, nombre=nombre,
                                      tipo=_enum(TipoDispositivo, tipo, "Tipo de dispositivo"), activo=True,
                                      registrado_en=ahora, ultimo_visto_en=ahora)
            uow.dispositivos.guardar(dispositivo)
            self.evento(uow, "dispositivo", dispositivo.id, "acceso.dispositivo.registrado", {"nombre": nombre})
            return self.dto_dispositivo(dispositivo), True


# ============================================================ autenticación


class AutenticarUsuario(Base):
    """Identificador + secreto → JWT. Mismo error y mismo coste para «no existe» y «clave incorrecta»."""

    _hash_senuelo: str | None = None

    def _senuelo(self) -> str:
        if AutenticarUsuario._hash_senuelo is None:
            AutenticarUsuario._hash_senuelo = self.s.hasher.hash(self.s.azar.token_url(16))
        return AutenticarUsuario._hash_senuelo

    def ejecutar(self, identificador: str, secreto: str, dispositivo: str | None = None) -> dict:
        identificador = str(identificador or "").strip()
        secreto = str(secreto or "")
        if not identificador or not secreto:
            raise errores.DatosInvalidos("Faltan identificador o clave.")
        # Los intentos fallidos deben quedar escritos aunque la respuesta sea un error.
        return self.ejecutar_registrando(lambda uow: self._autenticar(uow, identificador, secreto, dispositivo))

    def _autenticar(self, uow: UnidadDeTrabajo, identificador: str, secreto: str, dispositivo: str | None) -> dict:
        org = uow.organizaciones.unica()
        if org is None:
            raise errores.CredencialesInvalidas()
        ahora = self.ahora()
        como_documento, como_email = DocumentNumber.normalizar_entrada(identificador)
        hmac_doc = self.s.cifrador.indice(como_documento)
        encontrado = uow.usuarios.por_identificador(hmac_doc)
        if encontrado is None and "@" in identificador:
            hmac_doc = self.s.cifrador.indice(como_email)
            encontrado = uow.usuarios.por_identificador(hmac_doc)
        disp = self.dispositivo_por_identificador(uow, org.id, dispositivo)
        disp_id = disp.id if disp else None

        def fallo(usuario_id: str | None, motivo: str, resultado=ResultadoIntento.FALLO):
            uow.intentos.registrar(IntentoAcceso(hmac_doc, resultado, motivo, ahora, usuario_id, disp_id))

        if encontrado is None:
            self.s.hasher.verificar(self._senuelo(), secreto)  # coste parejo
            fallo(None, "usuario_inexistente")
            raise errores.CredencialesInvalidas()

        usuario, ident = encontrado
        if usuario.estado is EstadoUsuario.BLOQUEADO:
            fallo(usuario.id, "bloqueo_manual", ResultadoIntento.BLOQUEADO)
            raise errores.UsuarioBloqueado("Su cuenta está bloqueada. Pida al docente que la desbloquee.", reintentar_en_seg=None)
        if not usuario.activo:
            fallo(usuario.id, f"estado_{usuario.estado.value.lower()}")
            raise errores.CredencialesInvalidas()

        rol = self.rol_de(uow, usuario)
        politica = self.politica_de(uow, usuario, rol)
        if not ident.es_login or not politica.admite_identificador(ident.tipo):
            self.s.hasher.verificar(self._senuelo(), secreto)
            fallo(usuario.id, "identificador_no_permitido")
            raise errores.CredencialesInvalidas()

        ventana = max(politica.ventana_intentos_min, politica.bloqueo_minutos) * MINUTO_MS
        bloqueo = PoliticaBloqueo.evaluar(uow.intentos.recientes(usuario.id, ahora - ventana), politica, ahora)
        if bloqueo.bloqueado:
            fallo(usuario.id, "bloqueo_automatico", ResultadoIntento.BLOQUEADO)
            raise errores.UsuarioBloqueado("Demasiados intentos. Espere o pida al docente que lo desbloquee.",
                                           reintentar_en_seg=bloqueo.segundos_restantes(ahora), bloqueado_hasta=bloqueo.hasta)

        credencial = uow.credenciales.activa(usuario.id)
        if credencial is None or not self.s.hasher.verificar(credencial.hash, secreto):
            if credencial is None:
                self.s.hasher.verificar(self._senuelo(), secreto)
            fallo(usuario.id, "sin_credencial" if credencial is None else "secreto_invalido")
            despues = PoliticaBloqueo.evaluar(uow.intentos.recientes(usuario.id, ahora - ventana), politica, ahora)
            if despues.bloqueado:
                self.auditar(uow, usuario.id, "acceso.usuario.bloqueado", "m01_usuario", usuario.id,
                             {"fallos": despues.fallos, "hasta": despues.hasta})
                self.evento(uow, "usuario", usuario.id, "acceso.usuario.bloqueado", {"hasta": despues.hasta})
                raise errores.UsuarioBloqueado("Demasiados intentos. Espere o pida al docente que lo desbloquee.",
                                               reintentar_en_seg=despues.segundos_restantes(ahora), bloqueado_hasta=despues.hasta)
            restantes = max(0, politica.intentos_maximos - despues.fallos)
            raise errores.CredencialesInvalidas(intentos_restantes=restantes)

        if self.s.hasher.necesita_rehash(credencial.hash):
            credencial.hash = self.s.hasher.hash(secreto)
            uow.credenciales.guardar(credencial)

        debe_cambiar = credencial.debe_cambiar or credencial.expirada(ahora)
        uow.intentos.registrar(IntentoAcceso(hmac_doc, ResultadoIntento.EXITO, "ok", ahora, usuario.id, disp_id))
        salida = self.abrir_sesion(uow, usuario, rol, politica, disp, ClaseSesion.NORMAL, debe_cambiar)
        self.auditar(uow, usuario.id, "acceso.sesion.iniciada", "m01_sesion", salida["sesion_id"],
                     {"dispositivo": disp.nombre if disp else None, "rol": rol.codigo})
        self.evento(uow, "sesion", salida["sesion_id"], "acceso.sesion.iniciada", {"usuario_id": usuario.id})
        return salida


class ResolverPrincipal(Base):
    """Token → Principal. Lo usa el adaptador de autenticación de DRF en cada petición."""

    def ejecutar(self, token: str) -> Principal:
        claims = self.s.tokens.leer(token)
        with self.s.uow() as uow:
            sesion = uow.sesiones.por_id(str(claims.get("jti", "")))
            if sesion is None or sesion.usuario_id != claims.get("sub"):
                raise errores.SesionInvalida()
            ahora = self.ahora()
            if sesion.revocada_en is not None:
                raise errores.SesionRevocada()
            if ahora >= sesion.expira_en:
                raise errores.SesionExpirada()
            usuario = uow.usuarios.por_id(sesion.usuario_id)
            if usuario is None or not usuario.activo:
                raise errores.SesionInvalida("La cuenta ya no está activa.")
            rol = self.rol_de(uow, usuario)
            credencial = uow.credenciales.activa(usuario.id)
            debe_cambiar = bool(credencial and (credencial.debe_cambiar or credencial.expirada(ahora)))
            if sesion.ultimo_uso_en is None or ahora - sesion.ultimo_uso_en > MINUTO_MS:
                sesion.ultimo_uso_en = ahora
                uow.sesiones.guardar(sesion)
            return Principal(
                usuario_id=usuario.id, organizacion_id=usuario.organizacion_id, rol_id=rol.id, rol_codigo=rol.codigo,
                menu=rol.menu_principal, nivel=rol.nivel, sesion_id=sesion.id, clase_sesion=sesion.clase,
                debe_cambiar_credencial=debe_cambiar and sesion.clase is ClaseSesion.NORMAL,
                dispositivo_id=sesion.dispositivo_id, evaluacion_ref=sesion.evaluacion_ref,
            )


class ConsultarIdentidad(Base):
    """`GET /yo/`: lo que el cliente usa para pintar el menú."""

    def ejecutar(self, principal: Principal) -> dict:
        with self.s.uow() as uow:
            usuario = uow.usuarios.por_id(principal.usuario_id)
            if usuario is None:
                raise errores.SesionInvalida()
            rol = self.rol_de(uow, usuario)
            ctx = self.contexto(uow, principal)
            sesion = uow.sesiones.por_id(principal.sesion_id)
            dispositivo = uow.dispositivos.por_id(sesion.dispositivo_id) if sesion and sesion.dispositivo_id else None
            permisos = []
            for c in sorted(ctx.concesiones.values(), key=lambda c: c.permiso_codigo):
                alcance = self.politica.alcance_concedido(ctx, c.permiso_codigo)
                if alcance is None:
                    continue
                permisos.append({"codigo": c.permiso_codigo, "alcance": alcance.value, "origen": c.origen,
                                 "vigente_hasta": c.vigente_hasta})
            dto = self.dto_usuario(uow, usuario, rol, incluir_pii=True)
            return {
                "usuario": {k: v for k, v in dto.items() if k not in ("grupos", "identificadores")},
                "identificadores": dto.get("identificadores", []),
                "permisos": permisos,
                "grupos": dto.get("grupos", []),
                "sesion": self.dto_sesion(sesion, usuario.alias, dispositivo.nombre if dispositivo else None) if sesion else None,
            }


class CambiarCredencialPropia(Base):
    def ejecutar(self, principal: Principal, secreto_actual: str, secreto_nuevo: str) -> dict:
        with self.s.uow() as uow:
            ctx = self.contexto(uow, principal)
            self.exigir(ctx, "credential.change_own", ObjetivoUsuario(principal.usuario_id, principal.organizacion_id, principal.nivel))
            usuario = uow.usuarios.por_id(principal.usuario_id)
            rol = self.rol_de(uow, usuario)
            actual = uow.credenciales.activa(usuario.id)
            if actual is None or not self.s.hasher.verificar(actual.hash, str(secreto_actual or "")):
                raise errores.CredencialesInvalidas("La clave actual no es correcta.")
            politica = self.politica_de(uow, usuario, rol)
            self.establecer_credencial(uow, usuario, politica, str(secreto_nuevo or ""), creado_por=usuario.id, debe_cambiar=False)
            revocadas = uow.sesiones.revocar_de_usuario(usuario.id, "credencial_cambiada", self.ahora(), excepto=principal.sesion_id)
            self.auditar(uow, usuario.id, "acceso.credencial.cambiada", "m01_credencial", usuario.id, {"sesiones_revocadas": revocadas})
            self.evento(uow, "credencial", usuario.id, "acceso.credencial.cambiada", {})
            return {"cambiada": True, "sesiones_revocadas": revocadas}


class RevocarSesion(Base):
    def ejecutar(self, principal: Principal, sesion_id: str | None = None) -> dict:
        with self.s.uow() as uow:
            ctx = self.contexto(uow, principal)
            propia = sesion_id is None or sesion_id == principal.sesion_id
            sesion = uow.sesiones.por_id(principal.sesion_id if propia else sesion_id)
            if sesion is None:
                raise errores.NoEncontrado("No existe esa sesión.")
            if propia:
                self.exigir(ctx, "session.revoke_own", ObjetivoUsuario(principal.usuario_id, principal.organizacion_id, principal.nivel))
                motivo = "logout"
            else:
                self.usuario_objetivo(uow, ctx, sesion.usuario_id, "session.revoke")
                motivo = "administrador" if principal.nivel >= 3 else "docente"
            if sesion.revocada_en is None:
                sesion.revocada_en = self.ahora()
                sesion.motivo_revocacion = motivo
                uow.sesiones.guardar(sesion)
                self.auditar(uow, principal.usuario_id, "acceso.sesion.revocada", "m01_sesion", sesion.id, {"motivo": motivo})
                self.evento(uow, "sesion", sesion.id, "acceso.sesion.revocada", {"motivo": motivo})
            return {"id": sesion.id, "revocada_en": sesion.revocada_en, "motivo_revocacion": sesion.motivo_revocacion}


class ListarSesiones(Base):
    def ejecutar(self, principal: Principal, usuario_id: str | None = None, solo_activas: bool = True) -> list[dict]:
        with self.s.uow() as uow:
            ctx = self.contexto(uow, principal)
            ahora = self.ahora()
            if usuario_id:
                usuario, _ = self.usuario_objetivo(uow, ctx, usuario_id, "session.read")
                sesiones = uow.sesiones.listar(principal.organizacion_id, usuario.id, solo_activas, ahora)
            else:
                alcance = self.exigir_alcance(ctx, "session.read")
                permitidos = self._usuarios_en_alcance(uow, ctx, alcance)
                sesiones = uow.sesiones.listar(principal.organizacion_id, None, solo_activas, ahora, permitidos)
            return self._con_alias(uow, sesiones)

    def _usuarios_en_alcance(self, uow, ctx: ContextoActor, alcance: Alcance) -> Iterable[str] | None:
        if alcance is Alcance.ORGANIZATION:
            return None
        if alcance is Alcance.SELF:
            return [ctx.principal.usuario_id]
        ids = {ctx.principal.usuario_id}
        for grupo_id in ctx.grupos_docente:
            ids.update(m.usuario_id for m in uow.grupos.miembros(grupo_id) if m.papel is PapelGrupo.ESTUDIANTE)
        return ids

    def _con_alias(self, uow, sesiones: list[Sesion]) -> list[dict]:
        alias: dict[str, str] = {}
        dispositivos: dict[str, str] = {}
        salida = []
        for s in sesiones:
            if s.usuario_id not in alias:
                u = uow.usuarios.por_id(s.usuario_id)
                alias[s.usuario_id] = u.alias if u else ""
            if s.dispositivo_id and s.dispositivo_id not in dispositivos:
                d = uow.dispositivos.por_id(s.dispositivo_id)
                dispositivos[s.dispositivo_id] = d.nombre if d else ""
            salida.append(self.dto_sesion(s, alias[s.usuario_id], dispositivos.get(s.dispositivo_id) if s.dispositivo_id else None))
        return salida


# ================================================================= usuarios


class CrearUsuario(Base):
    def ejecutar(self, principal: Principal, datos: dict) -> dict:
        with self.s.uow() as uow:
            ctx = self.contexto(uow, principal)
            org = self.organizacion(uow)
            rol = uow.roles.por_codigo(org.id, _texto(datos.get("rol"), "el rol", 32).upper())
            if rol is None:
                raise errores.DatosInvalidos("Ese rol no existe.")
            grupo_id = str(datos.get("grupo_id") or "").strip() or None
            alcance = self.exigir_alcance(ctx, "user.create")
            if alcance is Alcance.ORGANIZATION:
                self.exigir(ctx, "user.create", ObjetivoOrganizacion(org.id))
                if rol.nivel > principal.nivel:
                    raise errores.SinPermiso("No puede crear usuarios de un nivel superior al suyo.", permiso="user.create")
            else:
                # Un docente sólo crea estudiantes y siempre dentro de uno de sus grupos.
                if rol.nivel != 1:
                    raise errores.SinPermiso("Con su alcance sólo puede crear estudiantes.", permiso="user.create",
                                             alcance_requerido=Alcance.ORGANIZATION.value)
                if not grupo_id:
                    raise errores.DatosInvalidos("Indique el grupo en el que queda inscrito el estudiante.")
                self.grupo_objetivo(uow, ctx, grupo_id, "user.create")
            creado = self._crear(uow, org, rol, datos, creado_por=principal.usuario_id, provisional=True)
            if grupo_id:
                grupo = uow.grupos.por_id(grupo_id)
                if grupo is None or grupo.organizacion_id != org.id:
                    raise errores.NoEncontrado("No existe ese grupo.")
                if alcance is Alcance.ORGANIZATION:
                    self.exigir(ctx, "group.member.manage", ObjetivoGrupo(grupo.id, grupo.organizacion_id), ocultar=True)
                uow.grupos.guardar_miembro(MiembroGrupo(_nuevo_id(), grupo.id, creado["id"],
                                                        PapelGrupo.ESTUDIANTE if rol.nivel == 1 else PapelGrupo.DOCENTE, self.ahora()))
                creado = {**creado, "grupos": [{"id": grupo.id, "codigo": grupo.codigo, "nombre": grupo.nombre,
                                                "periodo": grupo.periodo, "papel": "ESTUDIANTE" if rol.nivel == 1 else "DOCENTE"}]}
            return creado

    def _crear(self, uow: UnidadDeTrabajo, org: Organizacion, rol: Rol, datos: dict, creado_por: str | None,
               provisional: bool) -> dict:
        ahora = self.ahora()
        persona_datos = datos.get("persona") or {}
        usuario = Usuario(
            id=str(UserId.nuevo()), organizacion_id=org.id, rol_id=rol.id, estado=EstadoUsuario.ACTIVO,
            alias=_texto(datos.get("alias"), "el alias", 64),
            idioma=str(LanguageCode(datos.get("idioma") or org.idioma)),
            creado_en=ahora, actualizado_en=ahora, creado_por=creado_por,
        )
        identificadores = self._identificadores(uow, usuario.id, datos.get("identificadores") or [], ahora)
        if not any(i.es_login for i in identificadores):
            raise errores.DatosInvalidos("Hace falta al menos un identificador que sirva para iniciar sesión.")
        uow.usuarios.guardar(usuario)
        uow.usuarios.guardar_persona(Persona(
            usuario_id=usuario.id,
            nombres=_texto(persona_datos.get("nombres"), "los nombres", 120),
            apellidos=_texto(persona_datos.get("apellidos"), "los apellidos", 120, obligatorio=False),
            pais=str(CountryCode(persona_datos.get("pais") or org.pais)),
            fecha_nacimiento=_texto(persona_datos.get("fecha_nacimiento"), "la fecha de nacimiento", 10, obligatorio=False) or None,
            telefono=_texto(persona_datos.get("telefono"), "el teléfono", 32, obligatorio=False) or None,
            actualizado_en=ahora,
        ))
        uow.usuarios.reemplazar_identificadores(usuario.id, identificadores)
        politica = self.politica_de(uow, usuario, rol)
        secreto = str(datos.get("secreto") or "")
        generado = False
        if not secreto:
            secreto = self.generar_secreto(politica)
            generado = True
        # Quien crea la cuenta puede marcar el secreto como definitivo (colegios que prefieren
        # PIN asignado por el docente); si no, la primera entrada obliga a cambiarlo.
        debe_cambiar = provisional and not (bool(datos.get("secreto_definitivo")) and not generado)
        self.establecer_credencial(uow, usuario, politica, secreto, creado_por=creado_por, debe_cambiar=debe_cambiar)
        self.auditar(uow, creado_por or usuario.id, "acceso.usuario.creado", "m01_usuario", usuario.id, {"rol": rol.codigo})
        self.evento(uow, "usuario", usuario.id, "acceso.usuario.creado", {"rol": rol.codigo, "organizacion_id": org.id})
        salida = self.dto_usuario(uow, usuario, rol, incluir_pii=True, incluir_grupos=False)
        if generado:
            salida["secreto_inicial"] = secreto
        return salida

    def _identificadores(self, uow: UnidadDeTrabajo, usuario_id: str, lista: list[dict], ahora: int,
                         excepto_usuario: str | None = None) -> list[Identificador]:
        salida: list[Identificador] = []
        tipos: set[TipoIdentificador] = set()
        for item in lista:
            try:
                documento = DocumentNumber(_enum(TipoIdentificador, item.get("tipo"), "Tipo de identificador"), item.get("valor"))
            except ValueError as error:
                raise errores.DatosInvalidos(str(error))
            if documento.tipo in tipos:
                raise errores.DatosInvalidos(f"Sólo puede haber un identificador de tipo {documento.tipo.value}.")
            tipos.add(documento.tipo)
            valor_hmac = self.s.cifrador.indice(documento.normalizado)
            if uow.usuarios.existe_identificador(valor_hmac, excepto_usuario=excepto_usuario or usuario_id):
                raise errores.IdentificadorDuplicado(f"El {documento.tipo.value} ya pertenece a otra persona.")
            salida.append(Identificador(_nuevo_id(), usuario_id, documento.tipo, documento.valor,
                                        bool(item.get("es_login", True)), ahora))
        return salida


class ListarUsuarios(Base):
    def ejecutar(self, principal: Principal, grupo_id: str | None = None, rol: str | None = None,
                 estado: str | None = None) -> list[dict]:
        with self.s.uow() as uow:
            ctx = self.contexto(uow, principal)
            alcance = self.exigir_alcance(ctx, "user.read")
            if grupo_id:
                self.grupo_objetivo(uow, ctx, grupo_id, "user.read")
            usuarios = uow.usuarios.listar(principal.organizacion_id, alcance, principal.usuario_id, ctx.grupos_docente,
                                           principal.nivel, grupo_id, (rol or "").upper() or None, (estado or "").upper() or None)
            roles = {r.id: r for r in uow.roles.listar(principal.organizacion_id)}
            return [self.dto_usuario(uow, u, roles.get(u.rol_id), incluir_pii=True) for u in usuarios]


class VerUsuario(Base):
    def ejecutar(self, principal: Principal, usuario_id: str) -> dict:
        with self.s.uow() as uow:
            ctx = self.contexto(uow, principal)
            usuario, rol = self.usuario_objetivo(uow, ctx, usuario_id, "user.read")
            dto = self.dto_usuario(uow, usuario, rol)
            dto["permisos_adicionales"] = [dto_permiso_adicional(p) for p in uow.usuarios.permisos_adicionales(usuario.id)]
            return dto


def dto_permiso_adicional(p: UsuarioPermiso) -> dict:
    return {"id": p.id, "permiso": p.permiso_codigo, "alcance": p.alcance.value, "otorgado_por": p.otorgado_por,
            "motivo": p.motivo, "vigente_desde": p.vigente_desde, "vigente_hasta": p.vigente_hasta, "revocado_en": p.revocado_en}


class ActualizarUsuario(Base):
    ESTADOS_EDITABLES = {EstadoUsuario.ACTIVO, EstadoUsuario.SUSPENDIDO, EstadoUsuario.RETIRADO}

    def ejecutar(self, principal: Principal, usuario_id: str, cambios: dict) -> dict:
        with self.s.uow() as uow:
            ctx = self.contexto(uow, principal)
            usuario, rol = self.usuario_objetivo(uow, ctx, usuario_id, "user.update")
            ahora = self.ahora()
            registro: dict[str, Any] = {}
            if "alias" in cambios:
                usuario.alias = _texto(cambios.get("alias"), "el alias", 64)
                registro["alias"] = usuario.alias
            if "idioma" in cambios:
                usuario.idioma = str(LanguageCode(cambios.get("idioma")))
                registro["idioma"] = usuario.idioma
            if "estado" in cambios:
                nuevo = _enum(EstadoUsuario, cambios.get("estado"), "Estado")
                if nuevo not in self.ESTADOS_EDITABLES:
                    raise errores.DatosInvalidos("El bloqueo manual se gestiona con desbloquear, no con estado.")
                if usuario.id == principal.usuario_id and nuevo is not EstadoUsuario.ACTIVO:
                    raise errores.DatosInvalidos("No puede suspender o retirar su propia cuenta.")
                if nuevo is not usuario.estado:
                    usuario.estado = nuevo
                    registro["estado"] = nuevo.value
                    if nuevo is not EstadoUsuario.ACTIVO:
                        registro["sesiones_revocadas"] = uow.sesiones.revocar_de_usuario(usuario.id, "administrador", ahora)
            if "persona" in cambios and isinstance(cambios["persona"], dict):
                persona = uow.usuarios.persona(usuario.id) or Persona(usuario.id, "", "", self.organizacion(uow).pais)
                p = cambios["persona"]
                if "nombres" in p:
                    persona.nombres = _texto(p.get("nombres"), "los nombres", 120)
                if "apellidos" in p:
                    persona.apellidos = _texto(p.get("apellidos"), "los apellidos", 120, obligatorio=False)
                if "pais" in p:
                    persona.pais = str(CountryCode(p.get("pais")))
                if "fecha_nacimiento" in p:
                    persona.fecha_nacimiento = _texto(p.get("fecha_nacimiento"), "la fecha de nacimiento", 10, obligatorio=False) or None
                if "telefono" in p:
                    persona.telefono = _texto(p.get("telefono"), "el teléfono", 32, obligatorio=False) or None
                persona.actualizado_en = ahora
                uow.usuarios.guardar_persona(persona)
                registro["persona"] = sorted(p.keys())
            if "identificadores" in cambios:
                nuevos = CrearUsuario(self.s)._identificadores(uow, usuario.id, cambios.get("identificadores") or [], ahora)
                if not any(i.es_login for i in nuevos):
                    raise errores.DatosInvalidos("Hace falta al menos un identificador que sirva para iniciar sesión.")
                uow.usuarios.reemplazar_identificadores(usuario.id, nuevos)
                registro["identificadores"] = [i.tipo.value for i in nuevos]
            usuario.actualizado_en = ahora
            uow.usuarios.guardar(usuario)
            if registro:
                self.auditar(uow, principal.usuario_id, "acceso.usuario.actualizado", "m01_usuario", usuario.id, registro)
                self.evento(uow, "usuario", usuario.id, "acceso.usuario.actualizado", {"campos": sorted(registro.keys())})
            return self.dto_usuario(uow, usuario, rol)


class AsignarRol(Base):
    def ejecutar(self, principal: Principal, usuario_id: str, rol_codigo: str) -> dict:
        with self.s.uow() as uow:
            ctx = self.contexto(uow, principal)
            usuario, rol_actual = self.usuario_objetivo(uow, ctx, usuario_id, "user.role.assign")
            nuevo = uow.roles.por_codigo(usuario.organizacion_id, _texto(rol_codigo, "el rol", 32).upper())
            if nuevo is None:
                raise errores.DatosInvalidos("Ese rol no existe.")
            if nuevo.nivel > principal.nivel:
                raise errores.SinPermiso("No puede asignar un rol de nivel superior al suyo.", permiso="user.role.assign")
            if usuario.id == principal.usuario_id and nuevo.nivel < rol_actual.nivel:
                raise errores.DatosInvalidos("No puede rebajar su propio rol.")
            if nuevo.id != usuario.rol_id:
                ahora = self.ahora()
                usuario.rol_id = nuevo.id
                usuario.actualizado_en = ahora
                uow.usuarios.guardar(usuario)
                if uow.politicas.por_perfil(usuario.organizacion_id, nuevo.menu_principal) is None:
                    raise errores.Conflicto("No hay política de credenciales para el perfil del nuevo rol.")
                revocadas = uow.sesiones.revocar_de_usuario(usuario.id, "rol_cambiado", ahora)
                self.auditar(uow, principal.usuario_id, "acceso.rol.asignado", "m01_usuario", usuario.id,
                             {"de": rol_actual.codigo, "a": nuevo.codigo, "sesiones_revocadas": revocadas})
                self.evento(uow, "usuario", usuario.id, "acceso.rol.asignado", {"rol": nuevo.codigo})
            return self.dto_usuario(uow, usuario, nuevo)


class OtorgarPermiso(Base):
    def ejecutar(self, principal: Principal, usuario_id: str, permiso: str, alcance: str, motivo: str,
                 vigente_hasta: int | None = None) -> dict:
        with self.s.uow() as uow:
            ctx = self.contexto(uow, principal)
            usuario, _ = self.usuario_objetivo(uow, ctx, usuario_id, "user.permission.grant")
            codigo = str(PermissionCode(permiso))
            definicion = uow.permisos.obtener(codigo)
            if definicion is None:
                raise errores.DatosInvalidos("Ese permiso no existe en el catálogo.")
            pedido = Alcance.parse(alcance)
            self.politica.alcance_otorgable(definicion.alcance_maximo, pedido, self.politica.alcance_concedido(ctx, codigo))
            ahora = self.ahora()
            if vigente_hasta is not None and int(vigente_hasta) <= ahora:
                raise errores.DatosInvalidos("La vigencia debe estar en el futuro.")
            for existente in uow.usuarios.permisos_adicionales(usuario.id):
                if existente.permiso_codigo == codigo and existente.revocado_en is None:
                    existente.revocado_en = ahora
                    uow.usuarios.guardar_permiso_adicional(existente)
            concesion = UsuarioPermiso(_nuevo_id(), usuario.id, codigo, pedido, principal.usuario_id,
                                       _texto(motivo, "el motivo", 200), ahora, int(vigente_hasta) if vigente_hasta else None)
            uow.usuarios.guardar_permiso_adicional(concesion)
            self.auditar(uow, principal.usuario_id, "acceso.permiso.otorgado", "m01_usuario_permiso", concesion.id,
                         {"usuario_id": usuario.id, "permiso": codigo, "alcance": pedido.value, "motivo": concesion.motivo})
            self.evento(uow, "usuario", usuario.id, "acceso.permiso.otorgado", {"permiso": codigo, "alcance": pedido.value})
            return dto_permiso_adicional(concesion)


class RevocarPermiso(Base):
    def ejecutar(self, principal: Principal, usuario_id: str, permiso: str) -> bool:
        with self.s.uow() as uow:
            ctx = self.contexto(uow, principal)
            usuario, _ = self.usuario_objetivo(uow, ctx, usuario_id, "user.permission.grant")
            codigo = str(PermissionCode(permiso))
            ahora = self.ahora()
            hubo = False
            for existente in uow.usuarios.permisos_adicionales(usuario.id):
                if existente.permiso_codigo == codigo and existente.revocado_en is None:
                    existente.revocado_en = ahora
                    uow.usuarios.guardar_permiso_adicional(existente)
                    hubo = True
            if hubo:
                self.auditar(uow, principal.usuario_id, "acceso.permiso.revocado", "m01_usuario_permiso", usuario.id, {"permiso": codigo})
                self.evento(uow, "usuario", usuario.id, "acceso.permiso.revocado", {"permiso": codigo})
            return hubo


class RestablecerCredencial(Base):
    """La recuperación real: el docente establece un secreto provisional desde el aula."""

    def ejecutar(self, principal: Principal, usuario_id: str, secreto: str | None = None) -> dict:
        with self.s.uow() as uow:
            ctx = self.contexto(uow, principal)
            usuario, rol = self.usuario_objetivo(uow, ctx, usuario_id, "credential.reset")
            politica = self.politica_de(uow, usuario, rol)
            provisional = str(secreto or "") or self.generar_secreto(politica)
            self.establecer_credencial(uow, usuario, politica, provisional, creado_por=principal.usuario_id, debe_cambiar=True)
            ahora = self.ahora()
            revocadas = uow.sesiones.revocar_de_usuario(usuario.id, "credencial_restablecida", ahora)
            uow.intentos.registrar(IntentoAcceso("", ResultadoIntento.DESBLOQUEO, "credencial_restablecida", ahora, usuario.id))
            self.auditar(uow, principal.usuario_id, "acceso.credencial.restablecida", "m01_credencial", usuario.id,
                         {"sesiones_revocadas": revocadas, "tipo": politica.tipo_secreto.value})
            self.evento(uow, "credencial", usuario.id, "acceso.credencial.restablecida", {})
            return {"secreto_provisional": provisional, "tipo_secreto": politica.tipo_secreto.value,
                    "debe_cambiar": True, "sesiones_revocadas": revocadas}


class DesbloquearUsuario(Base):
    def ejecutar(self, principal: Principal, usuario_id: str) -> dict:
        with self.s.uow() as uow:
            ctx = self.contexto(uow, principal)
            usuario, rol = self.usuario_objetivo(uow, ctx, usuario_id, "user.unlock")
            ahora = self.ahora()
            uow.intentos.registrar(IntentoAcceso("", ResultadoIntento.DESBLOQUEO, "docente", ahora, usuario.id))
            if usuario.estado is EstadoUsuario.BLOQUEADO:
                usuario.estado = EstadoUsuario.ACTIVO
                usuario.actualizado_en = ahora
                uow.usuarios.guardar(usuario)
            self.auditar(uow, principal.usuario_id, "acceso.usuario.desbloqueado", "m01_usuario", usuario.id)
            self.evento(uow, "usuario", usuario.id, "acceso.usuario.desbloqueado", {})
            return {"id": usuario.id, "estado": usuario.estado.value, "bloqueado_hasta": None}


# ========================================================== acceso temporal


class OtorgarAccesoTemporal(Base):
    def ejecutar(self, principal: Principal, usuario_id: str, tipo: str, motivo: str, dispositivo_id: str | None = None,
                 evaluacion_ref: str | None = None, minutos: int | None = None) -> dict:
        with self.s.uow() as uow:
            ctx = self.contexto(uow, principal)
            usuario, rol = self.usuario_objetivo(uow, ctx, usuario_id, "exam.temporary_access.grant")
            politica = self.politica_de(uow, usuario, rol)
            if not politica.permite_acceso_temporal:
                raise errores.DatosInvalidos("La política de este perfil no admite acceso temporal.")
            if not usuario.activo:
                raise errores.Conflicto("El usuario no está activo.")
            clase = _enum(TipoAutorizacion, tipo, "Tipo de autorización")
            ahora = self.ahora()
            minutos = int(minutos or plantillas.MINUTOS_ACCESO_TEMPORAL)
            if not 1 <= minutos <= 30:
                raise errores.DatosInvalidos("La autorización dura entre 1 y 30 minutos.")
            dispositivo = None
            entrega: dict[str, Any]
            if clase is TipoAutorizacion.DISPOSITIVO:
                dispositivo = uow.dispositivos.por_id(str(dispositivo_id or ""))
                if dispositivo is None or dispositivo.organizacion_id != principal.organizacion_id or not dispositivo.activo:
                    raise errores.DatosInvalidos("Elija una tableta activa del aula.")
                token = self.s.azar.token_url(32)
                secreto_hash = self.s.azar.hash_rapido(token)
            else:
                token = self.s.azar.pin(6)
                secreto_hash = self.s.hasher.hash(token)
            autorizacion = AutorizacionTemporal(
                id=_nuevo_id(), usuario_id=usuario.id, otorgada_por=principal.usuario_id, tipo=clase,
                secreto_hash=secreto_hash, creada_en=ahora, expira_en=ahora + minutos * MINUTO_MS,
                motivo=_texto(motivo, "el motivo", 200, obligatorio=False) or "Acceso temporal a examen",
                dispositivo_id=dispositivo.id if dispositivo else None,
                evaluacion_ref=_texto(evaluacion_ref, "la evaluación", 200, obligatorio=False) or None,
            )
            uow.autorizaciones.guardar(autorizacion)
            entrega = {"grant_id": autorizacion.id, "token": token} if clase is TipoAutorizacion.DISPOSITIVO else {"codigo": token}
            self.auditar(uow, principal.usuario_id, "acceso.acceso_temporal.otorgado", "m01_autorizacion_temporal", autorizacion.id,
                         {"usuario_id": usuario.id, "tipo": clase.value, "evaluacion_ref": autorizacion.evaluacion_ref,
                          "dispositivo": dispositivo.nombre if dispositivo else None})
            self.evento(uow, "autorizacion_temporal", autorizacion.id, "acceso.acceso_temporal.otorgado",
                        {"usuario_id": usuario.id, "tipo": clase.value})
            dto = self.dto_autorizacion(autorizacion, usuario.alias, dispositivo.nombre if dispositivo else None)
            dto["entrega"] = entrega
            return dto


class CanjearAccesoTemporal(Base):
    def ejecutar(self, dispositivo: str | None, codigo: str | None = None, grant_id: str | None = None,
                 token: str | None = None) -> dict:
        return self.ejecutar_registrando(lambda uow: self._canjear(uow, dispositivo, codigo, grant_id, token))

    def _canjear(self, uow: UnidadDeTrabajo, dispositivo: str | None, codigo: str | None, grant_id: str | None,
                 token: str | None) -> dict:
        org = uow.organizaciones.unica()
        if org is None:
            raise errores.CredencialesInvalidas()
        ahora = self.ahora()
        disp = self.dispositivo_por_identificador(uow, org.id, dispositivo)
        autorizacion: AutorizacionTemporal | None = None
        if grant_id:
            candidata = uow.autorizaciones.por_id(str(grant_id))
            if candidata and candidata.tipo is TipoAutorizacion.DISPOSITIVO and candidata.canjeable(ahora) \
                    and disp is not None and candidata.dispositivo_id == disp.id \
                    and hmac.compare_digest(self.s.azar.hash_rapido(str(token or "")), candidata.secreto_hash):
                autorizacion = candidata
            elif candidata is not None:
                self._fallo(uow, candidata, disp, ahora)
                raise errores.CredencialesInvalidas("La autorización no es válida para esta tableta.")
        elif codigo:
            for candidata in uow.autorizaciones.canjeables_por_codigo(org.id, ahora):
                if self.s.hasher.verificar(candidata.secreto_hash, str(codigo).replace(" ", "")):
                    autorizacion = candidata
                    break
        if autorizacion is None:
            uow.intentos.registrar(IntentoAcceso("", ResultadoIntento.TEMPORAL_FALLO, "autorizacion_invalida", ahora,
                                                 None, disp.id if disp else None))
            raise errores.CredencialesInvalidas("El código no es válido o ya caducó.")
        usuario = uow.usuarios.por_id(autorizacion.usuario_id)
        if usuario is None or not usuario.activo:
            raise errores.CredencialesInvalidas()
        rol = self.rol_de(uow, usuario)
        politica = self.politica_de(uow, usuario, rol)
        salida = self.abrir_sesion(uow, usuario, rol, politica, disp, ClaseSesion.TEMPORAL, False, autorizacion.evaluacion_ref)
        autorizacion.usada_en = ahora
        autorizacion.sesion_id = salida["sesion_id"]
        uow.autorizaciones.guardar(autorizacion)
        uow.intentos.registrar(IntentoAcceso("", ResultadoIntento.TEMPORAL_EXITO, "ok", ahora, usuario.id,
                                             disp.id if disp else None, autorizacion.id))
        self.auditar(uow, usuario.id, "acceso.acceso_temporal.canjeado", "m01_autorizacion_temporal", autorizacion.id,
                     {"sesion_id": salida["sesion_id"], "dispositivo": disp.nombre if disp else None})
        self.evento(uow, "autorizacion_temporal", autorizacion.id, "acceso.acceso_temporal.canjeado", {"usuario_id": usuario.id})
        return salida

    def _fallo(self, uow: UnidadDeTrabajo, autorizacion: AutorizacionTemporal, disp: Dispositivo | None, ahora: int) -> None:
        uow.intentos.registrar(IntentoAcceso("", ResultadoIntento.TEMPORAL_FALLO, "autorizacion_invalida", ahora,
                                             autorizacion.usuario_id, disp.id if disp else None, autorizacion.id))
        if uow.intentos.fallos_de_autorizacion(autorizacion.id) >= plantillas.FALLOS_MAXIMOS_ACCESO_TEMPORAL \
                and autorizacion.revocada_en is None:
            autorizacion.revocada_en = ahora
            uow.autorizaciones.guardar(autorizacion)
            self.auditar(uow, autorizacion.usuario_id, "acceso.acceso_temporal.revocado", "m01_autorizacion_temporal",
                         autorizacion.id, {"motivo": "fallos"})


class ListarAutorizaciones(Base):
    def ejecutar(self, principal: Principal, usuario_id: str | None = None, solo_vigentes: bool = False) -> list[dict]:
        with self.s.uow() as uow:
            ctx = self.contexto(uow, principal)
            ahora = self.ahora()
            if usuario_id:
                usuario, _ = self.usuario_objetivo(uow, ctx, usuario_id, "exam.temporary_access.grant")
                filas = uow.autorizaciones.listar(principal.organizacion_id, usuario.id, solo_vigentes, ahora)
            else:
                alcance = self.exigir_alcance(ctx, "exam.temporary_access.grant")
                permitidos = ListarSesiones(self.s)._usuarios_en_alcance(uow, ctx, alcance)
                filas = uow.autorizaciones.listar(principal.organizacion_id, None, solo_vigentes, ahora, permitidos)
            salida = []
            for a in filas:
                u = uow.usuarios.por_id(a.usuario_id)
                d = uow.dispositivos.por_id(a.dispositivo_id) if a.dispositivo_id else None
                salida.append(self.dto_autorizacion(a, u.alias if u else "", d.nombre if d else None))
            return salida


class RevocarAccesoTemporal(Base):
    def ejecutar(self, principal: Principal, autorizacion_id: str) -> None:
        with self.s.uow() as uow:
            ctx = self.contexto(uow, principal)
            autorizacion = uow.autorizaciones.por_id(autorizacion_id)
            if autorizacion is None:
                raise errores.NoEncontrado("No existe esa autorización.")
            self.usuario_objetivo(uow, ctx, autorizacion.usuario_id, "exam.temporary_access.grant")
            ahora = self.ahora()
            if autorizacion.revocada_en is None:
                autorizacion.revocada_en = ahora
                uow.autorizaciones.guardar(autorizacion)
            if autorizacion.sesion_id:
                sesion = uow.sesiones.por_id(autorizacion.sesion_id)
                if sesion and sesion.revocada_en is None:
                    sesion.revocada_en = ahora
                    sesion.motivo_revocacion = "docente"
                    uow.sesiones.guardar(sesion)
            self.auditar(uow, principal.usuario_id, "acceso.acceso_temporal.revocado", "m01_autorizacion_temporal",
                         autorizacion.id, {"motivo": "docente"})
            self.evento(uow, "autorizacion_temporal", autorizacion.id, "acceso.acceso_temporal.revocado", {})


# ================================================================ catálogos


class ListarRoles(Base):
    def ejecutar(self, principal: Principal) -> list[dict]:
        with self.s.uow() as uow:
            ctx = self.contexto(uow, principal)
            self.exigir(ctx, "role.read", SinObjetivo())
            return [self.dto_rol(r) for r in uow.roles.listar(principal.organizacion_id)]


class ListarPermisos(Base):
    def ejecutar(self, principal: Principal) -> list[dict]:
        with self.s.uow() as uow:
            ctx = self.contexto(uow, principal)
            self.exigir(ctx, "role.read", SinObjetivo())
            return [{"codigo": p.codigo, "modulo": p.modulo, "descripcion": p.descripcion, "alcance_maximo": p.alcance_maximo.value}
                    for p in uow.permisos.listar()]


class CrearRol(Base):
    def ejecutar(self, principal: Principal, datos: dict) -> dict:
        with self.s.uow() as uow:
            ctx = self.contexto(uow, principal)
            self.exigir(ctx, "role.manage", ObjetivoOrganizacion(principal.organizacion_id))
            codigo = _texto(datos.get("codigo"), "el código del rol", 32).upper()
            if uow.roles.por_codigo(principal.organizacion_id, codigo) is not None:
                raise errores.Conflicto("Ya existe un rol con ese código.")
            plantilla = uow.roles.por_codigo(principal.organizacion_id, str(datos.get("plantilla") or "TEACHER").upper())
            if plantilla is None:
                raise errores.DatosInvalidos("La plantilla indicada no existe.")
            menu = _enum(Menu, datos.get("menu_principal") or plantilla.menu_principal.value, "Menú")
            nivel = int(datos.get("nivel") or plantilla.nivel)
            if nivel > principal.nivel or nivel < 1:
                raise errores.SinPermiso("No puede crear un rol de nivel superior al suyo.", permiso="role.manage")
            permisos = {p.permiso_codigo: p.alcance for p in plantilla.permisos}
            for item in datos.get("permisos") or []:
                pc = str(PermissionCode(item.get("codigo")))
                definicion = uow.permisos.obtener(pc)
                if definicion is None:
                    raise errores.DatosInvalidos(f"El permiso {pc} no existe.")
                alcance = item.get("alcance")
                if alcance in (None, "", "NONE"):
                    permisos.pop(pc, None)
                    continue
                # Un administrador (nivel 3) puede conceder hasta el techo del permiso; los demás, hasta lo que tienen.
                del_actor = definicion.alcance_maximo if principal.nivel >= 3 else self.politica.alcance_concedido(ctx, pc)
                permisos[pc] = self.politica.alcance_otorgable(definicion.alcance_maximo, Alcance.parse(alcance), del_actor)
            rol = Rol(id=_nuevo_id(), organizacion_id=principal.organizacion_id, codigo=codigo,
                      nombre=_texto(datos.get("nombre"), "el nombre del rol", 80), menu_principal=menu, nivel=nivel,
                      es_sistema=False, creado_en=self.ahora(), permisos=[RolPermiso(p, a) for p, a in permisos.items()])
            uow.roles.guardar(rol)
            self.auditar(uow, principal.usuario_id, "acceso.rol.creado", "m01_rol", rol.id, {"codigo": codigo, "plantilla": plantilla.codigo})
            self.evento(uow, "rol", rol.id, "acceso.rol.creado", {"codigo": codigo})
            return self.dto_rol(rol)


class ListarPoliticas(Base):
    def ejecutar(self, principal: Principal) -> list[dict]:
        with self.s.uow() as uow:
            ctx = self.contexto(uow, principal)
            self.exigir(ctx, "policy.manage", ObjetivoOrganizacion(principal.organizacion_id))
            return [self.dto_politica(p) for p in uow.politicas.por_organizacion(principal.organizacion_id)]


class ConfigurarPolitica(Base):
    CAMPOS_BOOL = ("exige_mayuscula", "exige_minuscula", "exige_digito", "exige_simbolo", "permite_acceso_temporal")
    CAMPOS_INT = ("longitud_minima", "intentos_maximos", "ventana_intentos_min", "bloqueo_minutos", "duracion_sesion_min")

    def ejecutar(self, principal: Principal, perfil: str, cambios: dict) -> dict:
        with self.s.uow() as uow:
            ctx = self.contexto(uow, principal)
            self.exigir(ctx, "policy.manage", ObjetivoOrganizacion(principal.organizacion_id))
            menu = _enum(Menu, perfil, "Perfil")
            politica = uow.politicas.por_perfil(principal.organizacion_id, menu)
            if politica is None:
                raise errores.NoEncontrado("No hay política para ese perfil.")
            if "tipo_identificador" in cambios:
                politica.tipo_identificador = _enum(TipoIdentificador, cambios["tipo_identificador"], "Tipo de identificador")
            if "tipo_secreto" in cambios:
                politica.tipo_secreto = _enum(TipoSecreto, cambios["tipo_secreto"], "Tipo de secreto")
            for campo in self.CAMPOS_BOOL:
                if campo in cambios:
                    setattr(politica, campo, bool(cambios[campo]))
            for campo in self.CAMPOS_INT:
                if campo in cambios:
                    try:
                        setattr(politica, campo, int(cambios[campo]))
                    except (TypeError, ValueError):
                        raise errores.DatosInvalidos(f"{campo} debe ser un entero.")
            if "vigencia_credencial_dias" in cambios:
                v = cambios["vigencia_credencial_dias"]
                politica.vigencia_credencial_dias = int(v) if v not in (None, "", 0, "0") else None
            try:
                politica.validar()
            except ValueError as error:
                raise errores.PoliticaInvalida(str(error))
            politica.actualizado_en = self.ahora()
            uow.politicas.guardar(politica)
            self.auditar(uow, principal.usuario_id, "acceso.politica.configurada", "m01_politica_credencial", politica.id,
                         {"perfil": menu.value, "campos": sorted(cambios.keys())})
            self.evento(uow, "politica", politica.id, "acceso.politica.configurada", {"perfil": menu.value})
            return self.dto_politica(politica)


# =================================================================== grupos


class ListarGrupos(Base):
    def ejecutar(self, principal: Principal) -> list[dict]:
        with self.s.uow() as uow:
            ctx = self.contexto(uow, principal)
            alcance = self.exigir_alcance(ctx, "group.read")
            if alcance is Alcance.ORGANIZATION:
                grupos = uow.grupos.listar(principal.organizacion_id)
            elif alcance is Alcance.ASSIGNED_GROUPS:
                grupos = uow.grupos.listar(principal.organizacion_id, ctx.grupos_docente | ctx.grupos_miembro)
            else:
                grupos = uow.grupos.listar(principal.organizacion_id, ctx.grupos_miembro)
            salida = []
            for g in grupos:
                dto = self.dto_grupo(g)
                dto["papel"] = "DOCENTE" if g.id in ctx.grupos_docente else ("MIEMBRO" if g.id in ctx.grupos_miembro else None)
                dto["miembros"] = len(uow.grupos.miembros(g.id))
                salida.append(dto)
            return salida


class VerGrupo(Base):
    def ejecutar(self, principal: Principal, grupo_id: str) -> dict:
        with self.s.uow() as uow:
            ctx = self.contexto(uow, principal)
            grupo = self.grupo_objetivo(uow, ctx, grupo_id, "group.read")
            dto = self.dto_grupo(grupo)
            miembros = []
            puede_ver_usuarios = self.politica.alcance_concedido(ctx, "user.read")
            for m in uow.grupos.miembros(grupo.id):
                u = uow.usuarios.por_id(m.usuario_id)
                if u is None:
                    continue
                fila = {"usuario_id": u.id, "alias": u.alias, "papel": m.papel.value, "desde": m.desde, "estado": u.estado.value}
                if puede_ver_usuarios is not None and (puede_ver_usuarios is not Alcance.SELF or u.id == principal.usuario_id):
                    fila["rol"] = self.rol_de(uow, u).codigo
                miembros.append(fila)
            dto["miembros"] = miembros
            return dto


class CrearGrupo(Base):
    def ejecutar(self, principal: Principal, datos: dict) -> dict:
        with self.s.uow() as uow:
            ctx = self.contexto(uow, principal)
            self.exigir(ctx, "group.manage", ObjetivoOrganizacion(principal.organizacion_id))
            politica_id = str(datos.get("politica_credencial_id") or "").strip() or None
            if politica_id:
                politica = uow.politicas.por_id(politica_id)
                if politica is None or politica.organizacion_id != principal.organizacion_id:
                    raise errores.DatosInvalidos("La política indicada no existe.")
            grupo = Grupo(id=_nuevo_id(), organizacion_id=principal.organizacion_id,
                          codigo=_texto(datos.get("codigo"), "el código del grupo", 32),
                          nombre=_texto(datos.get("nombre"), "el nombre del grupo", 120),
                          periodo=_texto(datos.get("periodo"), "el periodo", 16), activo=True, creado_en=self.ahora(),
                          politica_credencial_id=politica_id)
            for existente in uow.grupos.listar(principal.organizacion_id):
                if existente.codigo == grupo.codigo and existente.periodo == grupo.periodo:
                    raise errores.Conflicto("Ya existe un grupo con ese código en ese periodo.")
            uow.grupos.guardar(grupo)
            self.auditar(uow, principal.usuario_id, "acceso.grupo.creado", "m01_grupo", grupo.id, {"codigo": grupo.codigo})
            self.evento(uow, "grupo", grupo.id, "acceso.grupo.creado", {"codigo": grupo.codigo})
            return self.dto_grupo(grupo)


class ActualizarGrupo(Base):
    def ejecutar(self, principal: Principal, grupo_id: str, cambios: dict) -> dict:
        with self.s.uow() as uow:
            ctx = self.contexto(uow, principal)
            grupo = self.grupo_objetivo(uow, ctx, grupo_id, "group.manage")
            if "nombre" in cambios:
                grupo.nombre = _texto(cambios.get("nombre"), "el nombre del grupo", 120)
            if "activo" in cambios:
                grupo.activo = bool(cambios["activo"])
            if "politica_credencial_id" in cambios:
                pid = str(cambios.get("politica_credencial_id") or "").strip() or None
                if pid and (uow.politicas.por_id(pid) is None or uow.politicas.por_id(pid).organizacion_id != grupo.organizacion_id):
                    raise errores.DatosInvalidos("La política indicada no existe.")
                grupo.politica_credencial_id = pid
            uow.grupos.guardar(grupo)
            self.auditar(uow, principal.usuario_id, "acceso.grupo.actualizado", "m01_grupo", grupo.id, {"campos": sorted(cambios.keys())})
            return self.dto_grupo(grupo)


class AgregarMiembro(Base):
    def ejecutar(self, principal: Principal, grupo_id: str, usuario_id: str, papel: str = "ESTUDIANTE") -> dict:
        with self.s.uow() as uow:
            ctx = self.contexto(uow, principal)
            grupo = self.grupo_objetivo(uow, ctx, grupo_id, "group.member.manage")
            usuario = uow.usuarios.por_id(str(usuario_id or ""))
            if usuario is None or usuario.organizacion_id != grupo.organizacion_id:
                raise errores.NoEncontrado("No existe ese usuario.")
            rol = self.rol_de(uow, usuario)
            rol_papel = _enum(PapelGrupo, papel, "Papel")
            alcance = self.politica.alcance_concedido(ctx, "group.member.manage")
            if alcance is not Alcance.ORGANIZATION and (rol.nivel != 1 or rol_papel is not PapelGrupo.ESTUDIANTE):
                raise errores.SinPermiso("Con su alcance sólo puede añadir estudiantes.", permiso="group.member.manage")
            if rol_papel is PapelGrupo.DOCENTE and rol.nivel < 2:
                raise errores.DatosInvalidos("Un estudiante no puede ser docente de un grupo.")
            ahora = self.ahora()
            for m in uow.grupos.miembros(grupo.id):
                if m.usuario_id == usuario.id and m.papel is rol_papel:
                    return {"grupo_id": grupo.id, "usuario_id": usuario.id, "papel": rol_papel.value, "desde": m.desde, "ya_estaba": True}
            miembro = MiembroGrupo(_nuevo_id(), grupo.id, usuario.id, rol_papel, ahora)
            uow.grupos.guardar_miembro(miembro)
            self.auditar(uow, principal.usuario_id, "acceso.grupo.miembro_agregado", "m01_miembro_grupo", miembro.id,
                         {"grupo_id": grupo.id, "usuario_id": usuario.id, "papel": rol_papel.value})
            self.evento(uow, "grupo", grupo.id, "acceso.grupo.miembro_agregado", {"usuario_id": usuario.id, "papel": rol_papel.value})
            return {"grupo_id": grupo.id, "usuario_id": usuario.id, "papel": rol_papel.value, "desde": ahora, "ya_estaba": False}


class RetirarMiembro(Base):
    def ejecutar(self, principal: Principal, grupo_id: str, usuario_id: str) -> bool:
        with self.s.uow() as uow:
            ctx = self.contexto(uow, principal)
            grupo = self.grupo_objetivo(uow, ctx, grupo_id, "group.member.manage")
            ahora = self.ahora()
            alcance = self.politica.alcance_concedido(ctx, "group.member.manage")
            hubo = False
            for m in uow.grupos.miembros(grupo.id):
                if m.usuario_id != usuario_id:
                    continue
                if alcance is not Alcance.ORGANIZATION and m.papel is not PapelGrupo.ESTUDIANTE:
                    raise errores.SinPermiso("Con su alcance sólo puede retirar estudiantes.", permiso="group.member.manage")
                m.hasta = ahora
                uow.grupos.guardar_miembro(m)
                hubo = True
            if hubo:
                self.auditar(uow, principal.usuario_id, "acceso.grupo.miembro_retirado", "m01_miembro_grupo", grupo.id, {"usuario_id": usuario_id})
                self.evento(uow, "grupo", grupo.id, "acceso.grupo.miembro_retirado", {"usuario_id": usuario_id})
            return hubo


# ============================================================ dispositivos


class ListarDispositivos(Base):
    def ejecutar(self, principal: Principal, solo_activos: bool = True) -> list[dict]:
        with self.s.uow() as uow:
            ctx = self.contexto(uow, principal)
            previa = self.politica.transversal(ctx, "device.manage")
            if previa is not None:
                previa.exigir()
            if self.politica.alcance_concedido(ctx, "exam.temporary_access.grant") is None \
                    and self.politica.alcance_concedido(ctx, "device.manage") is None:
                raise errores.SinPermiso(permiso="device.manage")
            return [self.dto_dispositivo(d) for d in uow.dispositivos.listar(principal.organizacion_id, solo_activos)]


class ActualizarDispositivo(Base):
    def ejecutar(self, principal: Principal, dispositivo_id: str, cambios: dict) -> dict:
        with self.s.uow() as uow:
            ctx = self.contexto(uow, principal)
            self.exigir(ctx, "device.manage", ObjetivoOrganizacion(principal.organizacion_id))
            dispositivo = uow.dispositivos.por_id(dispositivo_id)
            if dispositivo is None or dispositivo.organizacion_id != principal.organizacion_id:
                raise errores.NoEncontrado("No existe ese dispositivo.")
            if "nombre" in cambios:
                dispositivo.nombre = _texto(cambios.get("nombre"), "el nombre del dispositivo", 64)
            if "activo" in cambios:
                dispositivo.activo = bool(cambios["activo"])
                if not dispositivo.activo:
                    for s in uow.sesiones.listar(principal.organizacion_id, None, True, self.ahora()):
                        if s.dispositivo_id == dispositivo.id:
                            s.revocada_en = self.ahora()
                            s.motivo_revocacion = "dispositivo_baja"
                            uow.sesiones.guardar(s)
            uow.dispositivos.guardar(dispositivo)
            self.auditar(uow, principal.usuario_id, "acceso.dispositivo.actualizado", "m01_dispositivo", dispositivo.id,
                         {"campos": sorted(cambios.keys())})
            return self.dto_dispositivo(dispositivo)
