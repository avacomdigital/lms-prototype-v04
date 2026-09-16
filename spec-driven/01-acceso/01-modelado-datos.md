# 01 · Módulo de acceso y usuarios · Modelado de datos

| Campo | Valor |
|---|---|
| Módulo | `acceso` · **MOD-001 · Identity & Access** del Documento Maestro (DOM-001 · Identidad y Organización) |
| Estado | Especificado e implementado en `backend/acceso/`; alineado con el Maestro según [04 · Lineamientos](04-Lineamientos-Al-Documento-Maestro.md) |
| Prefijo de tablas | `m01_` (CV-01) · 18 tablas |
| Plataforma | Python 3.12 · Django 5.2.3 · DRF 3.16.1 · SQLite · `argon2-cffi` · `cryptography` · `PyJWT` |
| Cliente | .NET MAUI (AVACOM OPS Master en Windows, AVACOM Student en Windows/Android), sin internet, sin teclado en el nodo principal |
| Decisiones que cierra | Q-04 (autenticación mínima) y Q-24 (tabla preparatoria de identidad) |
| Documentos hermanos | [02 · Endpoints](02-Endpoints.md) · [03 · Casos de uso](03-casos-de-uso-backend.md) · [04 · Lineamientos](04-Lineamientos-Al-Documento-Maestro.md) · [Presentación](../../specs/presentaciones/acceso.html) |

---

## 0 · Resumen ejecutivo

El aula AVACOM funciona sin internet. Todo lo que hace falta para **decidir quién es alguien y qué puede hacer** tiene que estar en el SQLite del equipo maestro. Este documento define ese mínimo en tercera forma normal, siguiendo MOD-001 del Documento Maestro:

1. **Una persona, varios roles, un solo rol efectivo por sesión (BR-021).** Los roles se asignan con alcance concreto y vigencia (`m01_usuario_rol`); al entrar se elige con cuál se trabaja. La asignación acota al rol.
2. **Cinco roles de fábrica**: Alumno, Profesor, Administrador, Reportes y Técnico AVACOM, con el catálogo de permisos `identity.*` y **cuatro alcances**: propio (`SELF`), grupo (`ASSIGNED_GROUPS`), nivel educativo (`LEVEL`) e instalación (`ORGANIZATION`). El contexto («¿es mi estudiante?») se **calcula** con la pertenencia a grupos; no hay tabla de permisos por contexto.
3. **Una sola sesión abierta por persona** en toda la instalación, y **cero o una por dispositivo compartido** (INV-011). Abrir en otro aparato cierra la anterior y lo avisa.
4. **Reglamento de acceso por colegio, por perfil y por nivel educativo (BR-023, BR-024)**: con qué identificador se entra (documento, matrícula, clave de instalación, correo), qué secreto se usa (PIN, contraseña o **avatar** para preescolar), bloqueo por intentos, duración e **inactividad** de la sesión.
5. **Identidad en tres capas (DEC-048)**: identificador interno inmutable, identificadores externos con emisor y uno principal, y credenciales que no identifican fuera de la instalación. Nunca existe una persona sin identificador externo (DEC-049).
6. **Argon2id para todo secreto; AES-256-GCM para todo dato personal; HMAC-SHA-256 para poder buscar lo cifrado.**
7. **Recuperación sin correo ni internet**: restablecer la credencial desde el aula, acceso temporal a examen (tableta autorizada o código de un solo uso) y **admisión nominal** de un alumno sin credencial a la mano, con vinculación posterior.
8. **Escaladas temporales (BR-101)** con motivo, caducidad obligatoria y concedente distinto del receptor. **Carga masiva** desde archivo (FUN-003).
9. **Nada se borra (CV-05)**: identificadores se retiran, asignaciones se revocan, cuentas pasan a `RETIRADO` y no vuelven (BR-025). Todo cambio publica un evento `identidad.*.v1` en la cola de salida dentro de la misma transacción.
10. **Arquitectura hexagonal dentro del monolito modular.** Dominio y casos de uso no importan Django; ORM, DRF, Argon2, AES y JWT son adaptadores sustituibles.

---

## 1 · Requisitos que gobiernan el modelo

| # | Requisito | Dónde se cumple |
|---|---|---|
| R-01 | Cinco tipos de usuario (Alumno menor sin correo, Profesor, Administrador, Reportes, Técnico) | `m01_rol.menu_principal`; `m01_identificador_usuario` admite entrar sin email |
| R-02 | El colegio configura identificador y secreto por perfil y por nivel educativo | `m01_politica_credencial` (`perfil`, `nivel_clave`); `m01_grupo.politica_credencial_id` para excepciones por grupo |
| R-03 | Profesor: documento + contraseña (≥ 8, mayúscula, símbolo) | Política sembrada `teacher` |
| R-04 | RBAC claro; el menú varía por rol; varios roles por persona, uno efectivo | `m01_rol`, `m01_rol_permiso`, `m01_usuario_rol`, `m01_sesion.rol_id` |
| R-05 | Permisos adicionales sin tabla contextual gigante | `m01_usuario_permiso` (escalada) con `alcance`, `motivo` y `vigente_hasta` |
| R-06 | Alcances como regla, no como tabla | `SELF` / `ASSIGNED_GROUPS` / `LEVEL` / `ORGANIZATION` evaluados por `PoliticaAutorizacion` con `m01_miembro_grupo` y `m01_usuario_rol` |
| R-07 | Autorización 100 % offline | Todas las tablas en el SQLite local; el JWT se firma y verifica en el nodo |
| R-08 | Sesión de 4 h, inactividad configurable, una sola por persona | `duracion_sesion_min = 240`, `inactividad_min`, `abrir_sesion()` |
| R-09 | Recuperación sin email/SMS/internet | Restablecer credencial, `m01_autorizacion_temporal`, cuentas provisionales |
| R-10 | Hashing por estándar; OWASP Top 10 | Argon2id, bloqueo por intentos, auditoría, cifrado de PII, autorización centralizada |
| R-11 | Campos ISO | `pais` ISO 3166-1 alpha-2, `idioma` ISO 639-1, `locale` BCP 47 |
| R-12 | Hexagonal + Use Case + Repository + UoW + Policy + Value Objects + Outbox | §6 y `backend/acceso/` |
| R-13 | Nomenclatura del Maestro | Permisos `identity.*`, eventos `identidad.*.v1`, tablas `m01_*` |

---

## 2 · Opciones consideradas

### 2.1 · Cómo representar a las personas

| Opción | Ventaja | Inconveniente | Decisión |
|---|---|---|---|
| A · Una tabla por tipo | Campos específicos sin nulos | Triplica credenciales, sesiones y auditoría; una persona con dos papeles existe dos veces | Rechazada |
| B · Una tabla `usuario` con columna `tipo` | Sencilla | Mezcla cuenta con persona; no es 3FN con más de un identificador | Rechazada |
| **C · cuenta + persona (PII cifrada) + identificadores externos (1..n) + asignaciones de rol (1..n)** | 3FN, PII aislada, entra con documento o matrícula, acumula roles sin duplicarse | Más joins (triviales en SQLite local) | **Elegida** (coincide con DEC-048 y `m01_persona_rol`) |

### 2.2 · Cómo representar los permisos

| Opción | Decisión |
|---|---|
| A · Permisos fijos en código por rol | Rechazada: no admite adicionales ni roles del colegio |
| B · RBAC + tabla `usuario_permiso_contexto` (usuario, permiso, grupo, curso, estudiante, recurso, clase, dispositivo…) | Rechazada explícitamente: crece sin límite, casi todo nulo |
| **C · RBAC + alcance por permiso + asignación de rol con alcance + contexto derivado de pertenencia** | **Elegida**. `rol_permiso(rol, permiso, alcance)`, `usuario_rol(usuario, rol, alcance_tipo, alcance_id, vigencia)` y `usuario_permiso` para escaladas |

### 2.3 · Dónde vive la sesión

| Opción | Decisión |
|---|---|
| JWT sin estado | Rechazada: no se puede cerrar la sesión de un estudiante ni imponer la sesión única |
| Sesión opaca sin JWT | Rechazada: el cliente MAUI espera un portador estándar |
| **JWT HS256 + fila `m01_sesion` con `jti` y rol efectivo** | **Elegida**: estándar, verificable offline, revocable, sobrevive al reinicio del nodo (FUN-011) |

### 2.4 · Cómo guardar documento y nombre

| Opción | Decisión |
|---|---|
| Texto plano | Rechazada: el SQLite viaja en un portátil de colegio; datos de menores |
| Sólo hash | Rechazada: hay que mostrar el nombre y verificar el documento |
| **AES-256-GCM (recuperable) + HMAC-SHA-256 (buscable) con claves separadas** | **Elegida** |

### 2.5 · Cómo contar los intentos fallidos

| Opción | Decisión |
|---|---|
| Contador `intentos_fallidos` en la credencial (como en el Maestro) | Rechazada: desbloquear borra la evidencia de lo que pasó |
| **Registro de intentos + cálculo** | **Elegida**: el bloqueo se calcula sobre `m01_intento_acceso`; desbloquear inserta una fila `DESBLOQUEO` |

---

## 3 · Modelo de datos (3FN)

### 3.0 · Diagrama

```
 m01_organizacion 1───n m01_politica_credencial (por perfil y, opcionalmente, por nivel educativo)
        │1                         │0..1
        n                          │
   m01_usuario n───1 m01_rol 1───n m01_rol_permiso n───1 m01_permiso
     │1 │1 │1 │1 │1                 │1                       │1
     │  │  │  │  └──n m01_usuario_rol n─┘ (rol + alcance_tipo + alcance_id + vigencia)
     │  │  │  └─────n m01_usuario_permiso (escalada) n──────┘
     │  │  └────────n m01_identificador_usuario (emisor, principal, retirado_en)
     │  └───────────1 m01_persona (cifrada)
     ├──────────────n m01_credencial (PIN · PASSWORD · AVATAR)
     ├──────────────n m01_sesion (rol efectivo, clase, motivo_cierre) n───0..1 m01_dispositivo
     ├──────────────n m01_intento_acceso
     ├──────────────n m01_autorizacion_temporal (usuario, otorgada_por, dispositivo?, sesion?)
     ├──────────────n m01_miembro_grupo n───1 m01_grupo (nivel_clave, politica?) n───1 m01_organizacion
     └──0..1 vinculado_a ─► m01_usuario (admisión nominal)
 m01_evento_salida (outbox, sin FK: agregado_tipo + agregado_id)
```

Convenciones que se conservan: fechas en **bigint milisegundos** (CV-03), claves de texto (CV-02, hoy UUID), columnas `*_cifrado` para AES-GCM y `*_hmac` para índice ciego, ninguna columna de texto plano con PII, **nada se borra** (CV-05).

### 3.1 · `m01_organizacion` · Organizacion

| Columna | Tipo | Nota |
|---|---|---|
| `id` | char(36) PK | UUID |
| `codigo` | char(32) UNIQUE | Corto, para mostrar («IE-SANJOSE»). Es el `emisor` por defecto de los identificadores |
| `nombre` | char(200) | |
| `pais` | char(2) | ISO 3166-1 alpha-2 |
| `idioma` | char(8) | ISO 639-1 |
| `locale` | char(16) | BCP 47 |
| `zona_horaria` | char(64) | IANA |
| `creado_en` | bigint | |

### 3.2 · `m01_politica_credencial` · PoliticaCredencial

El reglamento de acceso (BR-023, BR-024). Una fila **general por perfil** y, opcionalmente, **excepciones por nivel educativo** para el perfil de estudiantes.

| Columna | Tipo | Nota |
|---|---|---|
| `id` | char(36) PK | |
| `organizacion_id` | FK | |
| `perfil` | char(16) | `student` / `teacher` / `admin` / `reports` / `technician` |
| `nivel_clave` | char(24) null | `preescolar` · `primaria` · `secundaria` · `bachillerato` · `preuniversitario`. Null = política general |
| `tipo_identificador` | char(24) | `DNI` / `CODIGO_ESTUDIANTIL` / `CLAVE_INSTALACION` / `EMAIL` / `CUALQUIERA` |
| `tipo_secreto` | char(16) | `PIN` / `PASSWORD` / `AVATAR` |
| `longitud_minima` | smallint | 6 para PIN, 8 para contraseña docente, 12 para administración |
| `exige_mayuscula`, `exige_minuscula`, `exige_digito`, `exige_simbolo` | bool | Sólo aplican a `PASSWORD` |
| `intentos_maximos` | smallint | 5 |
| `ventana_intentos_min` | smallint | 15 |
| `bloqueo_minutos` | smallint | 15 (30 para administración) |
| `duracion_sesion_min` | int | **240** |
| `inactividad_min` | smallint | **20** (30 para estudiantes). FUN-009 |
| `vigencia_credencial_dias` | int null | Null = no caduca |
| `permite_acceso_temporal` | bool | Sólo `student` por defecto |
| `creado_en`, `actualizado_en` | bigint | |

Invariantes: única por `(organizacion, perfil)` sin nivel; única por `(organizacion, perfil, nivel_clave)` con nivel; `PIN` ⇒ 4..8; `AVATAR` sólo para `student`; `5 ≤ inactividad_min ≤ duracion_sesion_min`.

Resolución para una persona: **política de su grupo** → **política de su nivel educativo** → **política de su perfil**.

### 3.3 · `m01_rol` · Rol

| Columna | Tipo | Nota |
|---|---|---|
| `id` | char(36) PK | |
| `organizacion_id` | FK null | Null = **plantilla de sistema** (los cinco roles). No nulo = rol propio del colegio |
| `codigo` | char(32) | `STUDENT`, `TEACHER`, `ADMIN`, `REPORTS`, `TECHNICIAN`, o el que defina el colegio |
| `nombre` | char(80) | |
| `menu_principal` | char(16) | `student` / `teacher` / `admin` / `reports` / `technician`. Decide qué menú abre el cliente |
| `nivel` | smallint | 1 alumno · 2 personal · 3 administración. Nadie administra a alguien de nivel superior |
| `es_sistema` | bool | Las plantillas no se editan ni se borran |
| `creado_en` | bigint | |

### 3.4 · `m01_permiso` · Permiso

Catálogo cerrado y sembrado (28 permisos). Los de este módulo llevan el prefijo `identity.` del Maestro.

| Columna | Tipo | Nota |
|---|---|---|
| `codigo` | char(64) PK | `identity.password.reset`, `student.progress.read`… |
| `modulo` | char(24) | `acceso`, `expediente`, `contenido`, `aula`, `reportes`, `auditoria` |
| `descripcion` | char(200) | |
| `alcance_maximo` | char(20) | Techo: `identity.password.change_own` nunca pasa de `SELF`; `identity.exam_access.grant` nunca pasa de `ASSIGNED_GROUPS` |

Los **sensibles** (exigen asiento de auditoría siempre) se marcan en `plantillas.PERMISOS` y los expone `GET /permisos/`.

### 3.5 · `m01_rol_permiso` · RolPermiso

| Columna | Tipo | Nota |
|---|---|---|
| `rol_id` | FK | |
| `permiso_codigo` | FK | |
| `alcance` | char(20) | `SELF` / `ASSIGNED_GROUPS` / `LEVEL` / `ORGANIZATION` |

Invariante: `UNIQUE(rol_id, permiso_codigo)`; `alcance ≤ permiso.alcance_maximo`.

### 3.6 · `m01_usuario` · Usuario

La **cuenta**. Sin datos personales.

| Columna | Tipo | Nota |
|---|---|---|
| `id` | char(36) PK | Identidad interna estable (BR-020). Es el `persona_id` del expediente |
| `organizacion_id` | FK | |
| `rol_id` | FK | **Rol principal**: el que decide el menú si no se elige otro al entrar |
| `estado` | char(16) | `ACTIVO` / `BLOQUEADO` (manual) / `SUSPENDIDO` / `RETIRADO`. El bloqueo por intentos se calcula |
| `alias` | char(64) | Lo que muestra la tableta compartida («Juan P.») |
| `idioma` | char(8) | ISO 639-1 |
| `provisional` | bool | Admisión nominal: la creó el profesor «por su nombre» y aún no se vinculó |
| `vinculado_a` | FK null (usuario) | Al vincular, apunta a la persona definitiva y la provisional pasa a `RETIRADO` |
| `creado_en`, `actualizado_en`, `creado_por`, `ultimo_acceso_en` | | |

### 3.7 · `m01_persona` · Persona (1:1)

| Columna | Tipo | Protección |
|---|---|---|
| `usuario_id` | PK, FK | |
| `nombres_cifrado`, `apellidos_cifrado` | text | AES-256-GCM |
| `fecha_nacimiento_cifrado` | text null | AES-256-GCM |
| `telefono_cifrado` / `telefono_hmac` | text / char(64) | AES-256-GCM + índice HMAC |
| `pais` | char(2) | ISO 3166-1 alpha-2 |
| `actualizado_en` | bigint | |

### 3.8 · `m01_identificador_usuario` · IdentificadorUsuario

Identificadores **externos** (DEC-048): lo que vincula a la misma persona entre nodos.

| Columna | Tipo | Nota |
|---|---|---|
| `id` | char(36) PK | |
| `usuario_id` | FK | |
| `tipo` | char(24) | `DNI` (documento nacional) / `CODIGO_ESTUDIANTIL` (matrícula) / `CLAVE_INSTALACION` (la emite el nodo, DEC-049) / `EMAIL` |
| `valor_cifrado` | text | AES-256-GCM |
| `valor_hmac` | char(64) | HMAC-SHA-256 del valor **normalizado** |
| `emisor` | char(64) | Institución o instalación que lo emitió; por defecto el código de la organización |
| `principal` | bool | **Uno por persona**: el que se muestra y el que vincula |
| `es_login` | bool | Si sirve para iniciar sesión |
| `verificado_en`, `creado_en` | bigint | |
| `retirado_en` | bigint null | CV-05: se retira, no se borra |

Invariantes (todos sobre los vigentes): `UNIQUE(tipo, valor_hmac)`; uno por `(usuario, tipo)`; un `principal` por usuario.

### 3.9 · `m01_credencial` · Credencial

| Columna | Tipo | Nota |
|---|---|---|
| `id` | char(36) PK | |
| `usuario_id` | FK | |
| `tipo` | char(16) | `PIN` / `PASSWORD` / `AVATAR` |
| `hash` | char(255) | Cadena **Argon2id** con parámetros y sal |
| `activa` | bool | Sólo una activa por usuario |
| `debe_cambiar` | bool | Provisional: la puso otra persona |
| `creado_en`, `expira_en`, `sustituida_en`, `creado_por` | | |

### 3.10 · `m01_usuario_rol` · UsuarioRol (m01_persona_rol del Maestro)

Asignación de rol con alcance concreto y vigencia. Una persona puede tener varias; en cada sesión trabaja con una (BR-021).

| Columna | Tipo | Nota |
|---|---|---|
| `id` | char(36) PK | |
| `usuario_id` | FK | |
| `rol_id` | FK | |
| `alcance_tipo` | char(20) | `ORGANIZATION` / `LEVEL` / `ASSIGNED_GROUPS`. **Acota** el alcance del rol |
| `alcance_id` | char(36) null | `nivel_clave` o `grupo_id`; nulo con `ORGANIZATION` |
| `desde`, `hasta` | bigint / null | Vigencia (CAP-006: suplente hasta una fecha) |
| `asignado_por` | FK null | |
| `revocado_en` | bigint null | |

Invariantes: una vigente por `(usuario, rol, alcance_tipo, alcance_id)`; `hasta > desde`; alcance distinto de organización exige `alcance_id`.

### 3.11 · `m01_usuario_permiso` · Escalada (m01_escalada del Maestro)

| Columna | Tipo | Nota |
|---|---|---|
| `id` | char(36) PK | |
| `usuario_id` | FK | |
| `permiso_codigo` | FK | |
| `alcance` | char(20) | |
| `otorgado_por` | FK | Debe ser una identidad **distinta** del receptor |
| `motivo` | char(200) | Obligatorio por regla |
| `vigente_desde`, `vigente_hasta` | bigint | **Caducidad obligatoria** (BR-101), tope 24 h |
| `revocado_en` | bigint null | |

### 3.12 · `m01_grupo` · Grupo

| Columna | Tipo | Nota |
|---|---|---|
| `id` | char(36) PK | |
| `organizacion_id` | FK | |
| `codigo`, `nombre`, `periodo` | | |
| `nivel_clave` | char(24) null | Nivel educativo del Maestro: decide la interfaz y las políticas por nivel |
| `politica_credencial_id` | FK null | Excepción de reglamento para el grupo |
| `activo`, `creado_en` | | |

### 3.13 · `m01_miembro_grupo` · MiembroGrupo

`grupo_id`, `usuario_id`, `papel` (`ESTUDIANTE` / `DOCENTE`), `desde`, `hasta`. Es lo que convierte `ASSIGNED_GROUPS` en una consulta: *existe un grupo donde el actor es DOCENTE vigente y el objetivo es miembro vigente*.

### 3.14 · `m01_dispositivo` · Dispositivo

`organizacion_id`, `identificador` (lo genera la app y lo guarda en el almacén seguro), `nombre` («tableta-07»), `tipo`, `activo`, `registrado_en`, `ultimo_visto_en`. Contexto, nunca identidad.

### 3.15 · `m01_sesion` · Sesion

| Columna | Tipo | Nota |
|---|---|---|
| `id` | char(36) PK | `jti` del JWT |
| `usuario_id` | FK | |
| `rol_id` | FK null | **Rol efectivo** de la sesión (BR-021) |
| `dispositivo_id` | FK null | Contexto |
| `clase` | char(16) | `NORMAL` / `TEMPORAL` |
| `emitida_en`, `expira_en`, `ultimo_uso_en` | bigint | La inactividad se mide desde `ultimo_uso_en` |
| `revocada_en` | bigint null | |
| `motivo_revocacion` | char(64) null | `persona` · `otro_dispositivo` · `dispositivo_compartido` · `inactividad` · `restauracion` · `profesor` · `administrador` · `credencial_cambiada` · `credencial_restablecida` · `rol_cambiado` · `estado_cuenta` · `dispositivo_baja` |
| `evaluacion_ref` | char(200) null | Sesión temporal limitada a una evaluación |

Reglas: **una sola vigente por persona** y **cero o una por dispositivo** (INV-011), impuestas al abrir; la fila cerrada conserva su motivo.

### 3.16 · `m01_intento_acceso` · IntentoAcceso

`usuario_id?`, `identificador_hmac`, `dispositivo_id?`, `resultado` (`EXITO` · `FALLO` · `BLOQUEADO` · `DESBLOQUEO` · `TEMPORAL_EXITO` · `TEMPORAL_FALLO`), `motivo`, `autorizacion_id?`, `momento`. De aquí se **calcula** el bloqueo (FUN-007).

### 3.17 · `m01_autorizacion_temporal` · AutorizacionTemporal

El pase de emergencia del examen: `tipo` (`DISPOSITIVO` · `CODIGO`), `secreto_hash` (SHA-256 del token de 256 bits, o Argon2id del código de 6 dígitos), `dispositivo_id?`, `evaluacion_ref?`, `expira_en` (5 min), `usada_en`, `revocada_en`, `sesion_id`, `motivo`.

### 3.18 · `m01_evento_salida` · EventoSalida (Transactional Outbox)

`agregado_tipo`, `agregado_id`, `tipo_evento` (`identidad.*.v1`), `carga` (sin PII ni secretos), `creado_en`, `publicado_en`, `intentos`. Se escribe en la **misma transacción** que el hecho (Parte VII del documento de Arquitectura).

---

## 4 · Protección de la información

| Dato | Protección | Motivo |
|---|---|---|
| Contraseña · PIN · avatar · código temporal | **Argon2id** `m=64 MiB, t=3, p=1` | Nunca se recuperan; la baja entropía del PIN y el avatar la compensan el coste y el bloqueo |
| Token de dispositivo (256 bits) | SHA-256 | Alta entropía |
| Documento · matrícula · correo | **AES-256-GCM + HMAC-SHA-256** | Mostrar y buscar |
| Nombres · apellidos · nacimiento · teléfono | **AES-256-GCM** | Recuperar |
| JWT | **HS256** con clave local de 256 bits | Un solo emisor y verificador |

Claves `AVACOM_LMS_CLAVE_DATOS`, `AVACOM_LMS_CLAVE_INDICE`, `AVACOM_LMS_CLAVE_TOKENS` (32 bytes base64). Si faltan, se derivan con HKDF de `SECRET_KEY` y `/health/` lo avisa.

Payload del JWT: `iss`, `sub` (usuario), `jti` (sesión), `org`, `rol` (efectivo), `menu`, `nivel`, `dev`, `clase`, `eval`, `iat`, `exp`. Los **permisos no viajan en el token**: se evalúan contra la base en cada petición.

---

## 5 · Plantillas plug-and-play

### 5.1 · Los cinco roles y sus permisos

| Permiso | STUDENT | TEACHER | ADMIN | REPORTS | TECHNICIAN |
|---|---|---|---|---|---|
| `student.progress.read` · `results.read` | SELF | ASSIGNED_GROUPS | ORGANIZATION | ORGANIZATION | — |
| `student.progress.write` · `student.exam.attempt` | SELF | — | — | — | — |
| `reports.student.view` | — | ASSIGNED_GROUPS | ORGANIZATION | ORGANIZATION | — |
| `content.read` | SELF | ORGANIZATION | ORGANIZATION | ORGANIZATION | — |
| `content.project` | — | ASSIGNED_GROUPS | ASSIGNED_GROUPS | — | — |
| `identity.user.read` | SELF | ASSIGNED_GROUPS | ORGANIZATION | ORGANIZATION | — |
| `identity.user.create` · `identity.user.update` · `identity.user.unlock` · `identity.password.reset` | — | ASSIGNED_GROUPS | ORGANIZATION | — | — |
| `identity.user.import` · `identity.role.assign` · `identity.escalation.grant` · `identity.role.manage` · `identity.policy.manage` · `identity.group.manage` · `audit.read` | — | — | ORGANIZATION | — | — |
| `identity.exam_access.grant` | — | ASSIGNED_GROUPS | ASSIGNED_GROUPS | — | — |
| `identity.session.read` | SELF | ASSIGNED_GROUPS | ORGANIZATION | SELF | ORGANIZATION |
| `identity.session.revoke` | — | ASSIGNED_GROUPS | ORGANIZATION | — | — |
| `identity.group.read` | SELF | ASSIGNED_GROUPS | ORGANIZATION | ORGANIZATION | — |
| `identity.group.member.manage` | — | ASSIGNED_GROUPS | ORGANIZATION | — | — |
| `identity.role.read` | — | ORGANIZATION | ORGANIZATION | ORGANIZATION | ORGANIZATION |
| `identity.device.manage` | — | — | ORGANIZATION | — | ORGANIZATION |
| `identity.password.change_own` · `identity.session.revoke_own` | SELF | SELF | SELF | SELF | SELF |

### 5.2 · Evaluación de una decisión (Policy Pattern)

```
decidir(actor, permiso, objetivo):
    rol_efectivo = el de la sesión (BR-021)
    concesiones = rol_permiso[rol_efectivo] ∪ escaladas vigentes
    alcance = min(concesiones[permiso], alcance de la asignación del rol)   # ausencia → DENEGADO
    grupos del actor = donde es DOCENTE ∪ los que abre la asignación (un grupo, o todos los de un nivel)
    ORGANIZATION → misma organización y actor.nivel ≥ objetivo.nivel
    LEVEL / ASSIGNED_GROUPS → objetivo es estudiante y comparte alguno de esos grupos
    SELF → objetivo == actor
    Fuera de alcance → 403 acceso denegado, nunca «no existe»
```

Reglas transversales previas: credencial provisional ⇒ sólo `identity.password.change_own`; sesión `TEMPORAL` ⇒ sólo rendir la evaluación.

---

## 6 · Arquitectura del módulo

```
DRF (interfaces/views.py, serializers.py, autenticacion.py, urls.py)
      ↓
Casos de uso (aplicacion/casos_uso.py)            ← Use Case Pattern (39 casos)
      ↓
Dominio (dominio/entidades.py, valores.py, politicas.py, errores.py, plantillas.py)
      ↓
Puertos (aplicacion/puertos.py)
      ↓
Adaptadores (infraestructura/repositorios.py, unidad_trabajo.py, seguridad.py, contenedor.py)
      ↓
Django ORM (models.py) → SQLite
```

Regla verificable: una prueba recorre `dominio/` y `aplicacion/` y falla si algún archivo importa `django`, `rest_framework`, `pydantic`, `sqlalchemy` o `fastapi`.

---

## 7 · Relación con el expediente y con los demás módulos del Maestro

- `m01_usuario.id` **es** el `persona_id` del expediente. `vinculado_a` permite reasignar lo que hizo una cuenta provisional.
- Grupos (MOD-002) y dispositivos (MOD-009) viven hoy dentro de `acceso`; cuando existan esos módulos, se replicarán desde su dueño.
- La orden de limpiar el contenedor de la tableta (MOD-009) se deriva de `identidad.sesion.cerrada.v1` con motivo `otro_dispositivo` o `dispositivo_compartido`.
- La exigencia de sesión en el expediente sigue preparada y no activada (`AVACOM_LMS_EXIGIR_SESION=0`, Q-34).

---

## 8 · Preguntas abiertas

Ver la sección 10 de [04 · Lineamientos](04-Lineamientos-Al-Documento-Maestro.md): Q-34 a Q-43.
