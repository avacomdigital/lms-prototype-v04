"""
Adaptadores criptográficos y de tiempo/azar. Implementan los puertos Hasher,
Cifrador, EmisorTokens, Reloj y Azar.

- Argon2id (argon2-cffi) para PIN, contraseñas y códigos temporales.
- AES-256-GCM (cryptography) para datos personales recuperables.
- HMAC-SHA-256 como índice ciego para poder buscar lo cifrado.
- JWT HS256 (PyJWT) con clave local de 256 bits.
Las tres claves salen del entorno; si faltan, se derivan con HKDF de SECRET_KEY y
`claves_derivadas()` lo delata para que /health/ lo avise.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
import string
import time

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from ..dominio import errores

VERSION_CLAVE = "v1"


# ------------------------------------------------------------------- claves


def _decodificar_clave(texto: str | None) -> bytes | None:
    if not texto:
        return None
    try:
        crudo = base64.b64decode(texto, validate=True)
    except Exception:
        crudo = None
    if crudo is None or len(crudo) != 32:
        raise ValueError("Las claves del módulo de acceso deben ser 32 bytes en base64.")
    return crudo


def derivar(secreto_base: str, etiqueta: str) -> bytes:
    return HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=etiqueta.encode("utf-8")).derive(
        secreto_base.encode("utf-8"))


class Claves:
    """Resuelve las tres claves: explícitas del entorno o derivadas de SECRET_KEY."""

    def __init__(self, datos: str | None, indice: str | None, tokens: str | None, secreto_base: str):
        self.derivadas = False
        self.datos = _decodificar_clave(datos)
        self.indice = _decodificar_clave(indice)
        self.tokens = _decodificar_clave(tokens)
        if self.datos is None:
            self.datos, self.derivadas = derivar(secreto_base, "avacom-lms/acceso/datos"), True
        if self.indice is None:
            self.indice, self.derivadas = derivar(secreto_base, "avacom-lms/acceso/indice"), True
        if self.tokens is None:
            self.tokens, self.derivadas = derivar(secreto_base, "avacom-lms/acceso/tokens"), True


# ------------------------------------------------------------------- hasher


class HasherArgon2:
    """Argon2id. Parámetros por encima del mínimo OWASP (m=19 MiB, t=2, p=1)."""

    def __init__(self, time_cost: int = 3, memory_cost: int = 65536, parallelism: int = 1):
        self._ph = PasswordHasher(time_cost=time_cost, memory_cost=memory_cost, parallelism=parallelism,
                                  hash_len=32, salt_len=16)

    def hash(self, secreto: str) -> str:
        return self._ph.hash(secreto)

    def verificar(self, hash_guardado: str, secreto: str) -> bool:
        try:
            return self._ph.verify(hash_guardado, secreto)
        except (VerifyMismatchError, VerificationError, InvalidHashError):
            return False

    def necesita_rehash(self, hash_guardado: str) -> bool:
        try:
            return self._ph.check_needs_rehash(hash_guardado)
        except InvalidHashError:
            return True


# ----------------------------------------------------------------- cifrador


class CifradorAesGcm:
    """AES-256-GCM con nonce de 96 bits por valor y AAD = contexto (columna). HMAC-SHA-256 para índice."""

    def __init__(self, claves: Claves):
        self._aes = AESGCM(claves.datos)
        self._indice = claves.indice
        self._derivadas = claves.derivadas

    def cifrar(self, texto: str, contexto: str) -> str:
        nonce = os.urandom(12)
        cifrado = self._aes.encrypt(nonce, texto.encode("utf-8"), contexto.encode("utf-8"))
        return f"{VERSION_CLAVE}:{base64.urlsafe_b64encode(nonce + cifrado).decode('ascii')}"

    def descifrar(self, cifrado: str, contexto: str) -> str:
        if not cifrado:
            return ""
        try:
            version, cuerpo = cifrado.split(":", 1)
            if version != VERSION_CLAVE:
                raise ValueError(version)
            crudo = base64.urlsafe_b64decode(cuerpo)
            return self._aes.decrypt(crudo[:12], crudo[12:], contexto.encode("utf-8")).decode("utf-8")
        except (ValueError, InvalidTag):
            raise errores.Conflicto("No se pudo descifrar un dato: la clave cambió o el registro fue alterado.",
                                    codigo="dato_ilegible")

    def indice(self, texto_normalizado: str) -> str:
        return hmac.new(self._indice, texto_normalizado.encode("utf-8"), hashlib.sha256).hexdigest()

    def claves_derivadas(self) -> bool:
        return self._derivadas


# ------------------------------------------------------------------- tokens


class EmisorJwt:
    def __init__(self, claves: Claves, emisor: str = "avacom-lms"):
        self._clave = claves.tokens
        self._emisor = emisor

    def emitir(self, claims: dict) -> str:
        return jwt.encode({**claims, "iss": self._emisor}, self._clave, algorithm="HS256")

    def leer(self, token: str) -> dict:
        try:
            return jwt.decode(token, self._clave, algorithms=["HS256"], issuer=self._emisor,
                              options={"require": ["exp", "iat", "sub", "jti"]})
        except jwt.ExpiredSignatureError:
            raise errores.SesionExpirada()
        except jwt.InvalidTokenError:
            raise errores.SesionInvalida()


# -------------------------------------------------------------- reloj y azar


class RelojSistema:
    def ahora_ms(self) -> int:
        return int(time.time() * 1000)


class AzarSeguro:
    _SIMBOLOS = ".,!#$%&*+-=?@_"

    def token_url(self, octetos: int = 32) -> str:
        return secrets.token_urlsafe(octetos)

    def pin(self, digitos: int) -> str:
        return "".join(secrets.choice(string.digits) for _ in range(digitos))

    def password(self, longitud: int) -> str:
        alfabeto = string.ascii_letters + string.digits + self._SIMBOLOS
        base = [secrets.choice(string.ascii_uppercase), secrets.choice(string.ascii_lowercase),
                secrets.choice(string.digits), secrets.choice(self._SIMBOLOS)]
        base += [secrets.choice(alfabeto) for _ in range(max(0, longitud - len(base)))]
        secrets.SystemRandom().shuffle(base)
        return "".join(base)

    def hash_rapido(self, texto: str) -> str:
        return hashlib.sha256(texto.encode("utf-8")).hexdigest()
