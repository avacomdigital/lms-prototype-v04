"""Instalación, login, bloqueo, identidad, cierre y revocación de sesiones."""
from __future__ import annotations

from acceso import models as m

from .base import BaseAcceso


class InstalacionYConfiguracionTests(BaseAcceso):
    def test_la_instalacion_es_unica(self):
        r = self.api.post("/api/acceso/instalacion/", {
            "organizacion": {"codigo": "OTRA", "nombre": "Otra"},
            "administrador": {"nombres": "X", "dni": "1", "password": "Otra.Clave.2026!"}}, format="json")
        self.assertEqual(r.status_code, 409)
        self.assertEqual(r.json()["codigo"], "ya_instalado")

    def test_configuracion_publica_sin_pii(self):
        r = self.api.get("/api/acceso/configuracion/")
        self.assertEqual(r.status_code, 200)
        datos = r.json()
        self.assertTrue(datos["instalado"])
        self.assertEqual(datos["organizacion"]["locale"], "es-CO")
        self.assertEqual(datos["perfiles"]["student"], {"tipo_identificador": "CODIGO_ESTUDIANTIL", "tipo_secreto": "PIN",
                                                         "longitud_minima": 6, "permite_acceso_temporal": True})
        self.assertEqual(datos["perfiles"]["teacher"]["tipo_secreto"], "PASSWORD")
        self.assertEqual(datos["duracion_sesion_min"], 240)
        self.assertTrue(datos["claves_derivadas"])  # el prototipo deriva de SECRET_KEY y lo dice

    def test_health_informa_del_modulo(self):
        r = self.api.get("/health/")
        self.assertEqual(r.json()["acceso"]["instalado"], True)

    def test_la_pii_no_esta_en_claro_en_la_base(self):
        persona = m.Persona.objects.get(usuario_id=self.estudiante_id)
        self.assertNotIn("Juan", persona.nombres_cifrado)
        ident = m.IdentificadorUsuario.objects.get(usuario_id=self.estudiante_id, tipo="CODIGO_ESTUDIANTIL")
        self.assertNotIn(self.ESTUDIANTE_CODIGO, ident.valor_cifrado)
        self.assertEqual(len(ident.valor_hmac), 64)
        credencial = m.Credencial.objects.get(usuario_id=self.estudiante_id, activa=True)
        self.assertTrue(credencial.hash.startswith("$argon2id$"))


class LoginTests(BaseAcceso):
    def test_estudiante_entra_con_codigo_y_pin_y_ve_su_menu(self):
        r = self.login(self.ESTUDIANTE_CODIGO, self.ESTUDIANTE_PIN, self.TABLETA)
        self.assertEqual(r.status_code, 200)
        datos = r.json()
        self.assertEqual(datos["tipo"], "Bearer")
        self.assertEqual(datos["usuario"]["menu"], "student")
        self.assertFalse(datos["usuario"]["debe_cambiar_credencial"])
        self.assertAlmostEqual(datos["expira_en"] - m.Sesion.objects.get(id=datos["sesion_id"]).emitida_en, 240 * 60_000, delta=5)
        yo = self.con_token(datos["token"]).get("/api/acceso/yo/").json()
        self.assertEqual(yo["usuario"]["rol"], "STUDENT")
        self.assertEqual(yo["usuario"]["persona"]["nombres"], "Juan")
        self.assertEqual(yo["sesion"]["dispositivo"], "tableta-07")
        self.assertIn({"codigo": "student.exam.attempt", "alcance": "SELF", "origen": "rol", "vigente_hasta": None}, yo["permisos"])
        self.assertEqual(yo["grupos"][0]["codigo"], "8A")

    def test_docente_entra_con_dni_con_puntos_y_admin_ve_permisos_de_organizacion(self):
        self.assertEqual(self.login("80123456", self.DOCENTE_PASS).status_code, 200)
        yo = self.admin.get("/api/acceso/yo/").json()
        self.assertEqual(yo["usuario"]["menu"], "admin")
        self.assertIn({"codigo": "policy.manage", "alcance": "ORGANIZATION", "origen": "rol", "vigente_hasta": None}, yo["permisos"])

    def test_credenciales_invalidas_no_revelan_nada(self):
        mal = self.login(self.ESTUDIANTE_CODIGO, "000001")
        inexistente = self.login("999999", "000001")
        self.assertEqual((mal.status_code, inexistente.status_code), (401, 401))
        self.assertEqual(mal.json()["codigo"], inexistente.json()["codigo"])
        self.assertEqual(mal.json()["intentos_restantes"], 4)
        self.assertEqual(mal["WWW-Authenticate"], "Bearer")

    def test_el_identificador_no_permitido_por_la_politica_no_entra(self):
        # El estudiante tiene DNI registrado pero la política del perfil exige código y su DNI no es de login.
        self.assertEqual(self.login("1020334556", self.ESTUDIANTE_PIN).status_code, 401)

    def test_cinco_fallos_bloquean_y_el_docente_desbloquea(self):
        for _ in range(4):
            self.assertEqual(self.login(self.ESTUDIANTE_CODIGO, "000001").status_code, 401)
        r = self.login(self.ESTUDIANTE_CODIGO, "000001")
        self.assertEqual(r.status_code, 423)
        self.assertEqual(r.json()["codigo"], "usuario_bloqueado")
        self.assertGreater(r.json()["reintentar_en_seg"], 800)
        # con la clave correcta también está bloqueado
        self.assertEqual(self.login(self.ESTUDIANTE_CODIGO, self.ESTUDIANTE_PIN).status_code, 423)
        ficha = self.docente.get(f"/api/acceso/usuarios/{self.estudiante_id}/").json()
        self.assertIsNotNone(ficha["bloqueado_hasta"])
        r = self.docente.post(f"/api/acceso/usuarios/{self.estudiante_id}/desbloquear/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self.login(self.ESTUDIANTE_CODIGO, self.ESTUDIANTE_PIN).status_code, 200)
        self.assertTrue(m.IntentoAcceso.objects.filter(usuario_id=self.estudiante_id, resultado="DESBLOQUEO").exists())

    def test_sin_token_o_con_token_roto(self):
        r = self.api.get("/api/acceso/yo/")
        self.assertEqual((r.status_code, r.json()["codigo"]), (401, "sesion_requerida"))
        r = self.con_token("eyJ.basura.xx").get("/api/acceso/yo/")
        self.assertEqual((r.status_code, r.json()["codigo"]), (401, "sesion_invalida"))


class SesionesTests(BaseAcceso):
    def test_logout_revoca_la_sesion_actual(self):
        estudiante = self.sesion(self.ESTUDIANTE_CODIGO, self.ESTUDIANTE_PIN)
        self.assertEqual(estudiante.delete("/api/acceso/sesiones/actual/").status_code, 204)
        r = estudiante.get("/api/acceso/yo/")
        self.assertEqual((r.status_code, r.json()["codigo"]), (401, "sesion_revocada"))

    def test_docente_lista_y_revoca_sesiones_de_sus_estudiantes(self):
        estudiante = self.sesion(self.ESTUDIANTE_CODIGO, self.ESTUDIANTE_PIN, self.TABLETA)
        sesiones = self.docente.get(f"/api/acceso/sesiones/?usuario={self.estudiante_id}").json()
        self.assertEqual(len(sesiones), 1)
        self.assertEqual(sesiones[0]["dispositivo"], "tableta-07")
        self.assertEqual(self.docente.delete(f"/api/acceso/sesiones/{sesiones[0]['id']}/").status_code, 204)
        self.assertEqual(estudiante.get("/api/acceso/yo/").status_code, 401)
        self.assertEqual(m.Sesion.objects.get(id=sesiones[0]["id"]).motivo_revocacion, "docente")
        # el docente no ve las sesiones del administrador
        r = self.docente.get(f"/api/acceso/sesiones/?usuario={self.admin_id}")
        self.assertEqual(r.status_code, 404)

    def test_estudiante_no_revoca_sesiones_ajenas(self):
        estudiante = self.sesion(self.ESTUDIANTE_CODIGO, self.ESTUDIANTE_PIN)
        docente_sesion = self.admin.get(f"/api/acceso/sesiones/?usuario={self.docente_id}").json()[0]["id"]
        # no tiene el permiso en absoluto → 403 (tenerlo pero sin alcance sobre el objetivo sería 404)
        self.assertEqual(estudiante.delete(f"/api/acceso/sesiones/{docente_sesion}/").status_code, 403)
        self.assertIsNone(m.Sesion.objects.get(id=docente_sesion).revocada_en)

    def test_sesion_expirada(self):
        r = self.login(self.ESTUDIANTE_CODIGO, self.ESTUDIANTE_PIN).json()
        m.Sesion.objects.filter(id=r["sesion_id"]).update(emitida_en=0, expira_en=1)
        yo = self.con_token(r["token"]).get("/api/acceso/yo/")
        self.assertEqual((yo.status_code, yo.json()["codigo"]), (401, "sesion_expirada"))
