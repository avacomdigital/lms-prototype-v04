"""Usuarios: creación por alcance, credenciales provisionales, roles, permisos adicionales, grupos y políticas."""
from __future__ import annotations

from acceso import models as m

from .base import BaseAcceso


def estudiante(codigo: str, grupo_id: str | None = None, **extra) -> dict:
    datos = {"rol": "STUDENT", "alias": f"Alumno {codigo}", "persona": {"nombres": "Nombre", "apellidos": "Apellido"},
             "identificadores": [{"tipo": "CODIGO_ESTUDIANTIL", "valor": codigo, "es_login": True}]}
    if grupo_id:
        datos["grupo_id"] = grupo_id
    datos.update(extra)
    return datos


class CrearUsuarioTests(BaseAcceso):
    def test_docente_crea_estudiante_en_su_grupo_y_recibe_pin_generado_una_vez(self):
        r = self.docente.post("/api/acceso/usuarios/", estudiante("130001", self.grupo["id"]), format="json")
        self.assertEqual(r.status_code, 201, r.content)
        datos = r.json()
        self.assertRegex(datos["secreto_inicial"], r"^\d{6}$")
        self.assertTrue(datos["debe_cambiar_credencial"])
        self.assertEqual(datos["grupos"][0]["codigo"], "8A")
        ficha = self.docente.get(f"/api/acceso/usuarios/{datos['id']}/").json()
        self.assertNotIn("secreto_inicial", ficha)
        self.assertEqual(ficha["identificadores"][0]["valor"], "130001")

    def test_docente_no_crea_en_grupo_ajeno_ni_docentes_ni_sin_grupo(self):
        r = self.docente.post("/api/acceso/usuarios/", estudiante("130002", self.otro_grupo["id"]), format="json")
        self.assertEqual(r.status_code, 404)
        r = self.docente.post("/api/acceso/usuarios/", estudiante("130003"), format="json")
        self.assertEqual(r.status_code, 400)
        r = self.docente.post("/api/acceso/usuarios/", {**estudiante("130004", self.grupo["id"]), "rol": "TEACHER",
                                                        "identificadores": [{"tipo": "DNI", "valor": "555"}]}, format="json")
        self.assertEqual((r.status_code, r.json()["codigo"]), (403, "sin_permiso"))

    def test_pin_debil_y_identificador_duplicado(self):
        r = self.docente.post("/api/acceso/usuarios/", estudiante("130005", self.grupo["id"], secreto="123456"), format="json")
        self.assertEqual((r.status_code, r.json()["codigo"]), (400, "secreto_debil"))
        self.assertTrue(r.json()["reglas"])
        r = self.docente.post("/api/acceso/usuarios/", estudiante(self.ESTUDIANTE_CODIGO, self.grupo["id"]), format="json")
        self.assertEqual((r.status_code, r.json()["codigo"]), (400, "identificador_duplicado"))
        self.assertEqual(m.Usuario.objects.filter(alias__startswith="Alumno").count(), 0)

    def test_estudiante_no_crea_usuarios_y_solo_se_lista_a_si_mismo(self):
        est = self.sesion(self.ESTUDIANTE_CODIGO, self.ESTUDIANTE_PIN)
        self.assertEqual(est.post("/api/acceso/usuarios/", estudiante("130006"), format="json").status_code, 403)
        lista = est.get("/api/acceso/usuarios/").json()
        self.assertEqual([u["id"] for u in lista], [self.estudiante_id])
        self.assertEqual(est.get(f"/api/acceso/usuarios/{self.docente_id}/").status_code, 404)

    def test_listados_por_alcance(self):
        self.admin.post("/api/acceso/usuarios/", estudiante("140001", self.otro_grupo["id"]), format="json")
        del_docente = {u["alias"] for u in self.docente.get("/api/acceso/usuarios/").json()}
        self.assertEqual(del_docente, {"Prof. Gómez", "Juan P."})
        del_admin = {u["alias"] for u in self.admin.get("/api/acceso/usuarios/").json()}
        self.assertEqual(del_admin, {"Rectoría", "Prof. Gómez", "Juan P.", "Alumno 140001"})
        self.assertEqual(self.docente.get(f"/api/acceso/usuarios/?grupo={self.otro_grupo['id']}").status_code, 404)
        self.assertEqual(len(self.admin.get("/api/acceso/usuarios/?rol=STUDENT").json()), 2)


class CredencialTests(BaseAcceso):
    def test_restablecer_devuelve_secreto_una_vez_y_obliga_a_cambiarlo(self):
        abierta = self.sesion(self.ESTUDIANTE_CODIGO, self.ESTUDIANTE_PIN)
        r = self.docente.post(f"/api/acceso/usuarios/{self.estudiante_id}/credencial/restablecer/", {}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        provisional = r.json()["secreto_provisional"]
        self.assertRegex(provisional, r"^\d{6}$")
        self.assertEqual(r.json()["sesiones_revocadas"], 1)
        self.assertEqual(abierta.get("/api/acceso/yo/").status_code, 401)
        self.assertEqual(self.login(self.ESTUDIANTE_CODIGO, self.ESTUDIANTE_PIN).status_code, 401)

        entrada = self.login(self.ESTUDIANTE_CODIGO, provisional)
        self.assertTrue(entrada.json()["usuario"]["debe_cambiar_credencial"])
        est = self.con_token(entrada.json()["token"])
        r = est.get("/api/acceso/usuarios/")
        self.assertEqual((r.status_code, r.json()["codigo"]), (403, "debe_cambiar_credencial"))
        r = est.put("/api/acceso/yo/credencial/", {"secreto_actual": provisional, "secreto_nuevo": "480215"}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(est.get("/api/acceso/yo/").status_code, 200)
        self.assertEqual(self.login(self.ESTUDIANTE_CODIGO, "480215").status_code, 200)

    def test_no_se_reutiliza_una_credencial_anterior(self):
        est = self.sesion(self.ESTUDIANTE_CODIGO, self.ESTUDIANTE_PIN)
        r = est.put("/api/acceso/yo/credencial/", {"secreto_actual": self.ESTUDIANTE_PIN, "secreto_nuevo": self.ESTUDIANTE_PIN}, format="json")
        self.assertEqual((r.status_code, r.json()["codigo"]), (400, "secreto_debil"))
        r = est.put("/api/acceso/yo/credencial/", {"secreto_actual": "mal", "secreto_nuevo": "480215"}, format="json")
        self.assertEqual(r.status_code, 401)

    def test_el_docente_no_restablece_al_administrador(self):
        r = self.docente.post(f"/api/acceso/usuarios/{self.admin_id}/credencial/restablecer/", {}, format="json")
        self.assertEqual(r.status_code, 404)

    def test_politica_de_grupo_sobrescribe_la_del_perfil(self):
        politicas = {p["perfil"]: p for p in self.admin.get("/api/acceso/politicas/").json()}
        r = self.admin.patch(f"/api/acceso/grupos/{self.grupo['id']}/", {"politica_credencial_id": politicas["teacher"]["id"]}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        ficha = self.docente.get(f"/api/acceso/usuarios/{self.estudiante_id}/").json()
        self.assertEqual(ficha["tipo_secreto"], "PASSWORD")
        r = self.docente.post(f"/api/acceso/usuarios/{self.estudiante_id}/credencial/restablecer/", {"secreto": "480215"}, format="json")
        self.assertEqual((r.status_code, r.json()["codigo"]), (400, "secreto_debil"))
        # y el estudiante ya sólo entra por DNI (política docente) → su código deja de servir
        self.assertEqual(self.login(self.ESTUDIANTE_CODIGO, self.ESTUDIANTE_PIN).status_code, 401)

    def test_configurar_politica_valida_coherencia(self):
        r = self.admin.put("/api/acceso/politicas/student/", {"tipo_secreto": "PIN", "longitud_minima": 12}, format="json")
        self.assertEqual((r.status_code, r.json()["codigo"]), (400, "politica_invalida"))
        r = self.admin.put("/api/acceso/politicas/student/", {"tipo_identificador": "CUALQUIERA", "duracion_sesion_min": 120}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        # ahora el estudiante puede entrar con su DNI (marcado como no-login → sigue sin servir) o con el código
        self.assertEqual(self.login(self.ESTUDIANTE_CODIGO, self.ESTUDIANTE_PIN).status_code, 200)
        self.assertEqual(self.docente.put("/api/acceso/politicas/student/", {"longitud_minima": 4}, format="json").status_code, 403)


class RolesYPermisosTests(BaseAcceso):
    def test_admin_asigna_rol_y_revoca_sesiones(self):
        est = self.sesion(self.ESTUDIANTE_CODIGO, self.ESTUDIANTE_PIN)
        r = self.admin.put(f"/api/acceso/usuarios/{self.estudiante_id}/rol/", {"rol": "TEACHER"}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.json()["menu"], "teacher")
        self.assertEqual(est.get("/api/acceso/yo/").status_code, 401)
        # el docente no tiene user.role.assign en absoluto → 403
        self.assertEqual(self.docente.put(f"/api/acceso/usuarios/{self.estudiante_id}/rol/", {"rol": "ADMIN"}, format="json").status_code, 403)

    def test_permiso_adicional_con_vigencia_y_revocacion(self):
        r = self.admin.post(f"/api/acceso/usuarios/{self.docente_id}/permisos/",
                            {"permiso": "audit.read", "alcance": "ORGANIZATION", "motivo": "Coordinador académico 2026"}, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        permisos = {p["codigo"]: p for p in self.docente.get("/api/acceso/yo/").json()["permisos"]}
        self.assertEqual(permisos["audit.read"]["origen"], "adicional")
        self.assertEqual(permisos["audit.read"]["alcance"], "ORGANIZATION")
        self.assertEqual(self.admin.delete(f"/api/acceso/usuarios/{self.docente_id}/permisos/audit.read/").status_code, 204)
        self.assertNotIn("audit.read", {p["codigo"] for p in self.docente.get("/api/acceso/yo/").json()["permisos"]})

    def test_el_docente_no_otorga_permisos_y_el_techo_se_respeta(self):
        r = self.docente.post(f"/api/acceso/usuarios/{self.estudiante_id}/permisos/",
                              {"permiso": "audit.read", "alcance": "SELF", "motivo": "x"}, format="json")
        self.assertEqual(r.status_code, 403)
        r = self.admin.post(f"/api/acceso/usuarios/{self.docente_id}/permisos/",
                            {"permiso": "credential.change_own", "alcance": "ORGANIZATION", "motivo": "x"}, format="json")
        self.assertEqual((r.status_code, r.json()["codigo"]), (400, "datos_invalidos"))

    def test_rol_del_colegio_clonado_de_plantilla(self):
        r = self.admin.post("/api/acceso/roles/", {
            "codigo": "COORDINADOR", "nombre": "Coordinador", "plantilla": "TEACHER",
            "permisos": [{"codigo": "audit.read", "alcance": "ORGANIZATION"}, {"codigo": "content.project", "alcance": None}],
        }, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        permisos = {p["codigo"]: p["alcance"] for p in r.json()["permisos"]}
        self.assertEqual(permisos["audit.read"], "ORGANIZATION")
        self.assertNotIn("content.project", permisos)
        self.assertEqual(permisos["credential.reset"], "ASSIGNED_GROUPS")
        codigos = {rol["codigo"] for rol in self.docente.get("/api/acceso/roles/").json()}
        self.assertEqual(codigos, {"STUDENT", "TEACHER", "ADMIN", "COORDINADOR"})
        self.assertEqual(self.docente.post("/api/acceso/roles/", {"codigo": "X", "nombre": "X"}, format="json").status_code, 403)


class GruposTests(BaseAcceso):
    def test_docente_ve_sus_grupos_y_gestiona_solo_estudiantes(self):
        grupos = self.docente.get("/api/acceso/grupos/").json()
        self.assertEqual([g["codigo"] for g in grupos], ["8A"])
        self.assertEqual(grupos[0]["papel"], "DOCENTE")
        detalle = self.docente.get(f"/api/acceso/grupos/{self.grupo['id']}/").json()
        self.assertEqual({(x["alias"], x["papel"]) for x in detalle["miembros"]}, {("Prof. Gómez", "DOCENTE"), ("Juan P.", "ESTUDIANTE")})
        r = self.docente.post(f"/api/acceso/grupos/{self.grupo['id']}/miembros/", {"usuario_id": self.admin_id, "papel": "DOCENTE"}, format="json")
        self.assertEqual(r.status_code, 403)
        self.assertEqual(self.docente.get(f"/api/acceso/grupos/{self.otro_grupo['id']}/").status_code, 404)
        self.assertEqual(self.docente.delete(f"/api/acceso/grupos/{self.grupo['id']}/miembros/{self.estudiante_id}/").status_code, 204)
        self.assertEqual(self.docente.get(f"/api/acceso/usuarios/{self.estudiante_id}/").status_code, 404)

    def test_estudiante_ve_su_grupo_pero_no_lo_administra(self):
        est = self.sesion(self.ESTUDIANTE_CODIGO, self.ESTUDIANTE_PIN)
        self.assertEqual([g["codigo"] for g in est.get("/api/acceso/grupos/").json()], ["8A"])
        self.assertEqual(est.post("/api/acceso/grupos/", {"codigo": "X", "nombre": "X", "periodo": "2026"}, format="json").status_code, 403)

    def test_suspender_revoca_y_bloquea_la_entrada(self):
        est = self.sesion(self.ESTUDIANTE_CODIGO, self.ESTUDIANTE_PIN)
        r = self.docente.patch(f"/api/acceso/usuarios/{self.estudiante_id}/", {"estado": "SUSPENDIDO"}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(est.get("/api/acceso/yo/").status_code, 401)
        self.assertEqual(self.login(self.ESTUDIANTE_CODIGO, self.ESTUDIANTE_PIN).status_code, 401)
