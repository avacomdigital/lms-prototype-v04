"""
Value Objects del módulo de acceso. Validan en el constructor y no dependen de nada.

Este archivo, como todo `acceso/dominio`, no importa Django ni DRF: una prueba
de arquitectura lo garantiza (tests/test_arquitectura.py).
"""
from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from enum import Enum


class Alcance(str, Enum):
    """Hasta dónde llega un permiso. Es una regla de negocio, no una tabla."""

    SELF = "SELF"
    ASSIGNED_GROUPS = "ASSIGNED_GROUPS"
    ORGANIZATION = "ORGANIZATION"

    @property
    def orden(self) -> int:
        return {"SELF": 1, "ASSIGNED_GROUPS": 2, "ORGANIZATION": 3}[self.value]

    def cubre(self, requerido: "Alcance") -> bool:
        return self.orden >= requerido.orden

    @classmethod
    def parse(cls, texto: str) -> "Alcance":
        try:
            return cls(str(texto or "").strip().upper())
        except ValueError:
            raise ValueError(f"Alcance desconocido: {texto!r}. Use SELF, ASSIGNED_GROUPS u ORGANIZATION.")


class Menu(str, Enum):
    STUDENT = "student"
    TEACHER = "teacher"
    ADMIN = "admin"


class TipoIdentificador(str, Enum):
    DNI = "DNI"
    CODIGO_ESTUDIANTIL = "CODIGO_ESTUDIANTIL"
    EMAIL = "EMAIL"
    CUALQUIERA = "CUALQUIERA"  # sólo válido en la política


class TipoSecreto(str, Enum):
    PIN = "PIN"
    PASSWORD = "PASSWORD"


class EstadoUsuario(str, Enum):
    ACTIVO = "ACTIVO"
    BLOQUEADO = "BLOQUEADO"
    SUSPENDIDO = "SUSPENDIDO"
    RETIRADO = "RETIRADO"


class PapelGrupo(str, Enum):
    ESTUDIANTE = "ESTUDIANTE"
    DOCENTE = "DOCENTE"


class ClaseSesion(str, Enum):
    NORMAL = "NORMAL"
    TEMPORAL = "TEMPORAL"


class TipoAutorizacion(str, Enum):
    DISPOSITIVO = "DISPOSITIVO"
    CODIGO = "CODIGO"


class TipoDispositivo(str, Enum):
    TABLETA = "TABLETA"
    MASTER = "MASTER"


class ResultadoIntento(str, Enum):
    EXITO = "EXITO"
    FALLO = "FALLO"
    BLOQUEADO = "BLOQUEADO"
    DESBLOQUEO = "DESBLOQUEO"
    TEMPORAL_EXITO = "TEMPORAL_EXITO"
    TEMPORAL_FALLO = "TEMPORAL_FALLO"


def _enum(cls, texto, nombre):
    if isinstance(texto, cls):
        return texto
    try:
        return cls(str(texto or "").strip().upper() if cls is not Menu else str(texto or "").strip().lower())
    except ValueError:
        raise ValueError(f"{nombre} desconocido: {texto!r}.")


@dataclass(frozen=True)
class UserId:
    valor: str

    def __post_init__(self):
        try:
            uuid.UUID(str(self.valor))
        except (ValueError, AttributeError, TypeError):
            raise ValueError("El identificador de usuario debe ser un UUID.")
        object.__setattr__(self, "valor", str(self.valor).lower())

    @classmethod
    def nuevo(cls) -> "UserId":
        return cls(str(uuid.uuid4()))

    def __str__(self) -> str:
        return self.valor


@dataclass(frozen=True)
class CountryCode:
    """ISO 3166-1 alpha-2: `CO`, `MX`, `US`."""

    valor: str

    def __post_init__(self):
        v = str(self.valor or "").strip().upper()
        if not re.fullmatch(r"[A-Z]{2}", v):
            raise ValueError("El país debe ser un código ISO 3166-1 alpha-2 (dos letras, p. ej. CO).")
        object.__setattr__(self, "valor", v)

    def __str__(self) -> str:
        return self.valor


@dataclass(frozen=True)
class LanguageCode:
    """ISO 639-1 (o 639-2 de tres letras): `es`, `en`, `fr`."""

    valor: str

    def __post_init__(self):
        v = str(self.valor or "").strip().lower()
        if not re.fullmatch(r"[a-z]{2,3}", v):
            raise ValueError("El idioma debe ser un código ISO 639 (p. ej. es, en).")
        object.__setattr__(self, "valor", v)

    def __str__(self) -> str:
        return self.valor


@dataclass(frozen=True)
class LocaleCode:
    """BCP 47 / RFC 5646 en su forma idioma[-REGIÓN]: `es-CO`, `en-US`."""

    valor: str

    def __post_init__(self):
        partes = str(self.valor or "").strip().replace("_", "-").split("-")
        if not partes or not re.fullmatch(r"[A-Za-z]{2,3}", partes[0]):
            raise ValueError("El locale debe seguir BCP 47 (p. ej. es-CO).")
        salida = [partes[0].lower()]
        for extra in partes[1:]:
            if re.fullmatch(r"[A-Za-z]{2}", extra):
                salida.append(extra.upper())
            elif re.fullmatch(r"[A-Za-z0-9]{3,8}", extra):
                salida.append(extra)
            else:
                raise ValueError("El locale debe seguir BCP 47 (p. ej. es-CO).")
        object.__setattr__(self, "valor", "-".join(salida))

    @property
    def idioma(self) -> LanguageCode:
        return LanguageCode(self.valor.split("-")[0])

    def __str__(self) -> str:
        return self.valor


@dataclass(frozen=True)
class PermissionCode:
    """`modulo.recurso.accion`, p. ej. `student.progress.read`."""

    valor: str

    def __post_init__(self):
        v = str(self.valor or "").strip().lower()
        if not re.fullmatch(r"[a-z_]+(\.[a-z_]+){1,3}", v):
            raise ValueError(f"Código de permiso inválido: {self.valor!r}.")
        object.__setattr__(self, "valor", v)

    def __str__(self) -> str:
        return self.valor


@dataclass(frozen=True)
class DocumentNumber:
    """Un identificador de persona con su tipo y su forma normalizada (la que se indexa con HMAC)."""

    tipo: TipoIdentificador
    valor: str

    def __post_init__(self):
        tipo = _enum(TipoIdentificador, self.tipo, "Tipo de identificador")
        if tipo is TipoIdentificador.CUALQUIERA:
            raise ValueError("CUALQUIERA sólo se usa en la política, no en un identificador.")
        v = str(self.valor or "").strip()
        if not v:
            raise ValueError("El identificador no puede estar vacío.")
        if tipo is TipoIdentificador.EMAIL:
            if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", v):
                raise ValueError("El correo no tiene un formato válido.")
        elif len(v) > 64:
            raise ValueError("El identificador es demasiado largo.")
        object.__setattr__(self, "tipo", tipo)
        object.__setattr__(self, "valor", v)

    @property
    def normalizado(self) -> str:
        if self.tipo is TipoIdentificador.EMAIL:
            return self.valor.lower().replace(" ", "")
        return re.sub(r"[\s.\-]", "", self.valor).upper()

    @staticmethod
    def normalizar_entrada(texto: str) -> tuple[str, str]:
        """Para el login: devuelve (forma normalizada como documento, forma normalizada como email)."""
        t = str(texto or "").strip()
        return re.sub(r"[\s.\-]", "", t).upper(), t.lower().replace(" ", "")


@dataclass(frozen=True)
class Pin:
    valor: str

    def __post_init__(self):
        v = str(self.valor or "").strip()
        if not v.isdigit():
            raise ValueError("El PIN sólo admite dígitos.")
        object.__setattr__(self, "valor", v)

    def es_trivial(self) -> bool:
        v = self.valor
        if len(set(v)) == 1:
            return True
        asc = all(int(v[i + 1]) - int(v[i]) == 1 for i in range(len(v) - 1))
        desc = all(int(v[i]) - int(v[i + 1]) == 1 for i in range(len(v) - 1))
        if asc or desc:
            return True
        if len(v) % 2 == 0 and v[: len(v) // 2] == v[len(v) // 2:]:
            return True
        return v in {"123123", "112233", "121212", "696969", "159753", "147258"}


@dataclass(frozen=True)
class Password:
    valor: str

    def __post_init__(self):
        v = str(self.valor or "")
        if not v or v != v.strip():
            raise ValueError("La contraseña no puede estar vacía ni empezar o terminar con espacios.")
        if len(v) > 128:
            raise ValueError("La contraseña es demasiado larga.")

    @property
    def tiene_mayuscula(self) -> bool:
        return any(c.isupper() for c in self.valor)

    @property
    def tiene_minuscula(self) -> bool:
        return any(c.islower() for c in self.valor)

    @property
    def tiene_digito(self) -> bool:
        return any(c.isdigit() for c in self.valor)

    @property
    def tiene_simbolo(self) -> bool:
        return any(not c.isalnum() for c in self.valor)
