"""
Plantillas plug-and-play: catálogo de permisos, roles de sistema y políticas
por defecto. Un colegio que no configure nada funciona con esto.
"""
from __future__ import annotations

from .valores import Alcance, Menu, TipoIdentificador, TipoSecreto

S, G, O = Alcance.SELF, Alcance.ASSIGNED_GROUPS, Alcance.ORGANIZATION

# (codigo, modulo, descripcion, alcance_maximo)
PERMISOS: list[tuple[str, str, str, Alcance]] = [
    ("student.progress.read", "expediente", "Ver progreso y notas", O),
    ("student.progress.write", "expediente", "Registrar aperturas y avance", S),
    ("student.exam.attempt", "expediente", "Rendir evaluaciones", S),
    ("results.read", "expediente", "Ver resultados", O),
    ("content.read", "contenido", "Ver cursos de la biblioteca", O),
    ("content.project", "aula", "Proyectar en la pantalla del aula", G),
    ("user.read", "acceso", "Ver usuarios", O),
    ("user.create", "acceso", "Crear usuarios", O),
    ("user.update", "acceso", "Editar datos y estado de usuarios", O),
    ("user.role.assign", "acceso", "Asignar rol", O),
    ("user.permission.grant", "acceso", "Otorgar permisos adicionales", O),
    ("user.unlock", "acceso", "Desbloquear usuarios", O),
    ("credential.reset", "acceso", "Restablecer la credencial de otra persona", O),
    ("credential.change_own", "acceso", "Cambiar la propia credencial", S),
    ("exam.temporary_access.grant", "acceso", "Autorizar acceso temporal a examen", G),
    ("session.read", "acceso", "Ver sesiones", O),
    ("session.revoke", "acceso", "Revocar sesiones ajenas", O),
    ("session.revoke_own", "acceso", "Cerrar la propia sesión", S),
    ("group.read", "acceso", "Ver grupos", O),
    ("group.manage", "acceso", "Crear y editar grupos", O),
    ("group.member.manage", "acceso", "Añadir y quitar miembros de grupos", O),
    ("role.read", "acceso", "Ver roles y permisos", O),
    ("role.manage", "acceso", "Crear roles del colegio", O),
    ("policy.manage", "acceso", "Configurar la política de credenciales", O),
    ("device.manage", "acceso", "Registrar y dar de baja dispositivos", O),
    ("audit.read", "acceso", "Leer auditoría", O),
]

PERMISOS_POR_CODIGO = {p[0]: p for p in PERMISOS}

# codigo -> (nombre, menu, nivel, {permiso: alcance})
ROLES_SISTEMA: dict[str, tuple[str, Menu, int, dict[str, Alcance]]] = {
    "STUDENT": ("Estudiante", Menu.STUDENT, 1, {
        "student.progress.read": S, "student.progress.write": S, "student.exam.attempt": S,
        "results.read": S, "content.read": S, "user.read": S, "credential.change_own": S,
        "session.read": S, "session.revoke_own": S, "group.read": S,
    }),
    "TEACHER": ("Docente", Menu.TEACHER, 2, {
        "student.progress.read": G, "results.read": G, "content.read": O, "content.project": G,
        "user.read": G, "user.create": G, "user.update": G, "user.unlock": G, "credential.reset": G,
        "credential.change_own": S, "exam.temporary_access.grant": G, "session.read": G,
        "session.revoke": G, "session.revoke_own": S, "group.read": G, "group.member.manage": G,
        "role.read": O,
    }),
    "ADMIN": ("Administrador", Menu.ADMIN, 3, {
        **{codigo: (O if maximo is O else maximo) for codigo, _, _, maximo in PERMISOS
           if codigo not in ("student.progress.write", "student.exam.attempt")},
    }),
}

# perfil -> columnas de la política por defecto
POLITICAS_POR_DEFECTO: dict[Menu, dict] = {
    Menu.STUDENT: dict(tipo_identificador=TipoIdentificador.CODIGO_ESTUDIANTIL, tipo_secreto=TipoSecreto.PIN,
                       longitud_minima=6, exige_mayuscula=False, exige_minuscula=False, exige_digito=True,
                       exige_simbolo=False, intentos_maximos=5, ventana_intentos_min=15, bloqueo_minutos=15,
                       duracion_sesion_min=240, vigencia_credencial_dias=None, permite_acceso_temporal=True),
    Menu.TEACHER: dict(tipo_identificador=TipoIdentificador.DNI, tipo_secreto=TipoSecreto.PASSWORD,
                       longitud_minima=8, exige_mayuscula=True, exige_minuscula=False, exige_digito=False,
                       exige_simbolo=True, intentos_maximos=5, ventana_intentos_min=15, bloqueo_minutos=15,
                       duracion_sesion_min=240, vigencia_credencial_dias=None, permite_acceso_temporal=False),
    Menu.ADMIN: dict(tipo_identificador=TipoIdentificador.DNI, tipo_secreto=TipoSecreto.PASSWORD,
                     longitud_minima=12, exige_mayuscula=True, exige_minuscula=True, exige_digito=True,
                     exige_simbolo=True, intentos_maximos=5, ventana_intentos_min=15, bloqueo_minutos=30,
                     duracion_sesion_min=240, vigencia_credencial_dias=None, permite_acceso_temporal=False),
}

# Lo único que puede hacer una sesión nacida de una autorización temporal.
PERMISOS_SESION_TEMPORAL = frozenset({
    "student.exam.attempt", "student.progress.read", "student.progress.write",
    "content.read", "results.read", "session.revoke_own",
})

# Lo único que puede hacer quien aún tiene una credencial provisional.
PERMISOS_CON_CREDENCIAL_PROVISIONAL = frozenset({"credential.change_own", "session.revoke_own"})

MINUTOS_ACCESO_TEMPORAL = 5
FALLOS_MAXIMOS_ACCESO_TEMPORAL = 3
CREDENCIALES_NO_REUTILIZABLES = 3
