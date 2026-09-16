"""Adaptadores criptográficos: AES-GCM, HMAC, Argon2id y JWT."""
from __future__ import annotations

import base64
import os
import time

from django.test import SimpleTestCase

from acceso.dominio import errores
from acceso.dominio.valores import DocumentNumber, TipoIdentificador
from acceso.infraestructura.seguridad import AzarSeguro, CifradorAesGcm, Claves, EmisorJwt, HasherArgon2


def claves(explicitas: bool = True) -> Claves:
    if explicitas:
        k = lambda: base64.b64encode(os.urandom(32)).decode()
        return Claves(k(), k(), k(), "base")
    return Claves(None, None, None, "secreto-del-prototipo")


class CifradorTests(SimpleTestCase):
    def test_cifra_y_descifra_con_nonce_distinto_cada_vez(self):
        c = CifradorAesGcm(claves())
        a, b = c.cifrar("Juan", "persona.nombres"), c.cifrar("Juan", "persona.nombres")
        self.assertNotEqual(a, b)
        self.assertTrue(a.startswith("v1:"))
        self.assertEqual(c.descifrar(a, "persona.nombres"), "Juan")

    def test_detecta_manipulacion_y_contexto_equivocado(self):
        c = CifradorAesGcm(claves())
        cifrado = c.cifrar("1042888795", "identificador.valor")
        with self.assertRaises(errores.Conflicto):
            c.descifrar(cifrado, "persona.nombres")
        alterado = cifrado[:-4] + ("AAAA" if not cifrado.endswith("AAAA") else "BBBB")
        with self.assertRaises(errores.Conflicto):
            c.descifrar(alterado, "identificador.valor")

    def test_indice_estable_tras_normalizar(self):
        c = CifradorAesGcm(claves())
        a = DocumentNumber(TipoIdentificador.DNI, "1.042.888-795").normalizado
        b = DocumentNumber(TipoIdentificador.DNI, " 1042888795 ").normalizado
        self.assertEqual(c.indice(a), c.indice(b))
        self.assertNotEqual(c.indice(a), c.indice("1042888796"))
        self.assertEqual(len(c.indice(a)), 64)

    def test_claves_derivadas_se_delatan(self):
        self.assertTrue(CifradorAesGcm(claves(explicitas=False)).claves_derivadas())
        self.assertFalse(CifradorAesGcm(claves()).claves_derivadas())
        with self.assertRaises(ValueError):
            Claves("no-es-base64-de-32-bytes", None, None, "x")


class HasherTests(SimpleTestCase):
    def test_argon2id_verifica_y_no_repite_hash(self):
        h = HasherArgon2(time_cost=1, memory_cost=8192, parallelism=1)
        a, b = h.hash("691302"), h.hash("691302")
        self.assertTrue(a.startswith("$argon2id$"))
        self.assertNotEqual(a, b)
        self.assertTrue(h.verificar(a, "691302"))
        self.assertFalse(h.verificar(a, "691303"))
        self.assertFalse(h.verificar("basura", "691302"))

    def test_rehash_cuando_cambian_los_parametros(self):
        debil, fuerte = HasherArgon2(1, 8192, 1), HasherArgon2(2, 16384, 1)
        hash_debil = debil.hash("x")
        self.assertFalse(debil.necesita_rehash(hash_debil))
        self.assertTrue(fuerte.necesita_rehash(hash_debil))


class JwtTests(SimpleTestCase):
    def test_emite_lee_y_caduca(self):
        emisor = EmisorJwt(claves())
        ahora = int(time.time())
        token = emisor.emitir({"sub": "u1", "jti": "s1", "iat": ahora, "exp": ahora + 60})
        self.assertEqual(emisor.leer(token)["sub"], "u1")
        vencido = emisor.emitir({"sub": "u1", "jti": "s1", "iat": ahora - 120, "exp": ahora - 60})
        with self.assertRaises(errores.SesionExpirada):
            emisor.leer(vencido)
        with self.assertRaises(errores.SesionInvalida):
            EmisorJwt(claves()).leer(token)  # otra clave
        with self.assertRaises(errores.SesionInvalida):
            emisor.leer(emisor.emitir({"sub": "u1", "iat": ahora, "exp": ahora + 60}))  # sin jti


class AzarTests(SimpleTestCase):
    def test_pin_y_contrasena_generados(self):
        azar = AzarSeguro()
        self.assertRegex(azar.pin(6), r"^\d{6}$")
        clave = azar.password(12)
        self.assertEqual(len(clave), 12)
        self.assertTrue(any(c.isupper() for c in clave) and any(not c.isalnum() for c in clave))
        self.assertEqual(len(azar.hash_rapido("x")), 64)
