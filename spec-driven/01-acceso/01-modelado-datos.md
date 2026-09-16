# 01 · Módulo de acceso y usuarios · Modelado de datos

| Campo | Valor |
|---|---|
| Módulo | `acceso` · identidad, credenciales, RBAC con alcance, sesiones JWT y recuperación en el aula |
| Estado | Especificado e implementado en `backend/acceso/` |
| Prefijo de tablas | `m01_` (módulo 01 · identidad y acceso; resuelve la tabla condicionada 2.9 del [plan](../04-plan.md)) |
| Plataforma | Python 3.12 · Django 5.2.3 · DRF 3.16.1 · SQLite · `argon2-cffi` · `cryptography` · `PyJWT` |
| Cliente | .NET MAUI (AVACOM OPS Master en Windows, AVACOM Student en Windows/Android), sin internet, sin teclado en el nodo principal |
| Decisiones que cierra | Q-04 (autenticación mínima) y Q-24 (tabla preparatoria de identidad) |
| Documentos hermanos | [02 · Endpoints](02-Endpoints.md) · [Presentación](../../specs/presentaciones/acceso.html) · [Pantallas MAUI](../../specs/presentaciones/acceso-sugerencias.html) |

---

## 0 · Resumen ejecutivo

El aula AVACOM funciona sin internet. Todo lo que hace falta para **decidir quién es alguien y qué puede hacer** tiene que estar en el SQLite del equipo maestro. Este documento define ese mínimo en tercera forma normal, con estas decisiones:

1. **Un rol por usuario, permisos por rol, alcance por permiso.** El rol decide el menú (`student` / `teacher` / `admin`). El alcance (`SELF`, `ASSIGNED_GROUPS`, `ORGANIZATION`) es una **regla de negocio** que la política de autorización resuelve con la pertenencia a grupos, no una tabla de permisos por contexto.
2. **Plantillas plug-and-play.** Tres roles de sistema (`STUDENT`, `TEACHER`, `ADMIN`) con sus permisos vienen sembrados. Un colegio que no quiera configurar nada usa eso y funciona.
3. **Permisos adicionales sin tabla gigante.** Un profesor que necesita algo más recibe una fila en `m01_usuario_permiso` con permiso, alcance, vigencia y quién lo otorgó. Nada de `course_id`, `student_id`, `device_id` en una tabla de permisos.
4. **Credenciales configurables por colegio.** `m01_politica_credencial` dice, por perfil (`student`/`teacher`/`admin`), con qué identificador se entra (DNI, código estudiantil, email) y qué secreto se usa (PIN de 6 dígitos o contraseña). Un grupo puede sobreescribir la política (los grados superiores pueden usar contraseña).
5. **Argon2id para todo secreto; AES-256-GCM para todo dato personal; HMAC-SHA-256 para poder buscar lo cifrado.** Los secretos no se recuperan nunca; los datos personales sí.
6. **JWT HS256 de 4 horas con sesión registrada.** El token viaja al cliente; la fila `m01_sesion` permite revocarlo y saber desde qué dispositivo entró.
7. **Dos mecanismos de recuperación distintos.** Restablecer la credencial (el profesor asigna un PIN provisional que obliga a cambiarlo) y **acceso temporal a examen** (autorizar la tableta o dar un código de un solo uso que caduca en 5 minutos), ambos sin correo, SMS ni internet.
8. **Arquitectura hexagonal dentro del monolito modular.** Dominio y casos de uso no importan Django. Django ORM, DRF, Argon2, AES y JWT son adaptadores sustituibles.

---

## 1 · Requisitos que gobiernan el modelo

| # | Requisito | Dónde se cumple |
|---|---|---|
| R-01 | Tres tipos de usuario: estudiante (menor de edad, sin correo), profesor, administrador | `m01_rol.menu_principal`; `m01_identificador_usuario` admite entrar sin email |
| R-02 | El colegio configura qué identificador y qué secreto usan sus estudiantes | `m01_politica_credencial` por organización y perfil; `m01_grupo.politica_credencial_id` para excepciones |
| R-03 | Profesor: DNI + contraseña (≥ 8, una mayúscula, un símbolo) | Política sembrada `teacher`: `PASSWORD`, `longitud_minima=8`, `exige_mayuscula`, `exige_simbolo` |
| R-04 | RBAC claro; el menú varía por rol | `m01_rol` → `m01_rol_permiso`; `menu_principal` |
| R-05 | Permisos adicionales para profesores y administradores, sin tabla contextual gigante | `m01_usuario_permiso` con `alcance` + vigencia |
| R-06 | Scopes como regla, no como tabla | Enumeración `SELF` / `ASSIGNED_GROUPS` / `ORGANIZATION` evaluada por `PoliticaAutorizacion` con `m01_miembro_grupo` |
| R-07 | Autorización 100 % offline | Todas las tablas viven en el SQLite local; el JWT se firma y verifica localmente |
| R-08 | JWT con 4 h por defecto | `m01_politica_credencial.duracion_sesion_min = 240`; `m01_sesion.expira_en` |
| R-09 | Recuperación sin email/SMS/internet; emergencia «el examen empieza en 3 minutos» | Caso de uso *Restablecer credencial* y `m01_autorizacion_temporal` (opción A dispositivo, opción B código) |
| R-10 | Hashing por estándar; OWASP Top 10 | Argon2id (OWASP Password Storage), bloqueo por intentos (A07), auditoría (A09), cifrado de PII (A02), autorización centralizada (A01) |
| R-11 | Campos ISO | `pais` ISO 3166-1 alpha-2, `idioma` ISO 639-1, `locale` BCP 47 |
| R-12 | Hexagonal + Use Case + Repository + UoW + Policy + Value Objects + Outbox | §6 y `backend/acceso/` |
| R-13 | Portabilidad DRF/ORM → FastAPI/SQLAlchemy | Ninguna regla en `dominio/` ni `aplicacion/` importa Django |

---

## 2 · Opciones consideradas

### 2.1 · Cómo representar a los tres tipos de usuario

| Opción | Descripción | Ventajas | Inconvenientes | Decisión |
|---|---|---|---|---|
| A · Una tabla por tipo (`estudiante`, `profesor`, `administrador`) | Tres tablas con credenciales y datos propios | Campos específicos sin nulos | Triplica credenciales, sesiones, auditoría y políticas; un profesor que también administra existe dos veces | Rechazada |
| B · Una sola tabla `usuario` con columna `tipo` | Discriminador en la misma fila que el nombre, el DNI y el hash | Sencilla | Mezcla cuenta con persona; el DNI de un estudiante y el correo de un profesor caben en la misma columna nulable; no es 3FN cuando hay más de un identificador | Rechazada |
| **C · `usuario` (cuenta) + `persona` (datos personales) + `identificador_usuario` (1..n) + `rol`** | La cuenta apunta a un rol; la persona guarda PII cifrada; los identificadores son filas | 3FN, PII aislada y cifrable, un usuario puede entrar con DNI o con código, un profesor puede ser administrador cambiando de rol sin duplicarse | Más joins (triviales en SQLite local) | **Elegida** |

### 2.2 · Cómo representar los permisos

| Opción | Descripción | Decisión |
|---|---|---|
| A · Permisos fijos en código por rol | Un `if rol == "TEACHER"` por operación | Rechazada: no permite permisos adicionales ni roles del colegio |
| B · RBAC + tabla `usuario_permiso_contexto` (usuario, permiso, grupo, curso, estudiante, recurso, clase, dispositivo…) | Cada excepción se guarda con todos sus contextos | Rechazada explícitamente: crece sin límite, casi todo nulo, imposible de razonar y de sincronizar |
| **C · RBAC + alcance por permiso + contexto derivado de pertenencia** | `rol_permiso(rol, permiso, alcance)` y `usuario_permiso(usuario, permiso, alcance, vigencia)`. El contexto («¿es mi estudiante?») se **calcula** con `miembro_grupo` | **Elegida**. Dos tablas pequeñas y una política |

### 2.3 · Dónde vive la sesión

| Opción | Decisión |
|---|---|
| JWT sin estado | Rechazada: no se puede revocar la sesión de un estudiante que dejó la tableta abierta |
| Sesión opaca en base de datos, sin JWT | Rechazada: el cliente MAUI y una futura API remota esperan un portador estándar |
| **JWT HS256 + fila `m01_sesion` con `jti`** | **Elegida**. El token es estándar y verificable offline; la fila permite revocar, listar y auditar |

### 2.4 · Cómo guardar el DNI y el nombre

| Opción | Decisión |
|---|---|
| Texto plano | Rechazada: el SQLite viaja en un portátil de colegio; OWASP A02 |
| Sólo hash | Rechazada: hay que mostrar el nombre y verificar el documento |
| **AES-256-GCM (recuperable) + HMAC-SHA-256 (buscable) con claves separadas** | **Elegida**. Cifrado autenticado con nonce por valor; el índice HMAC permite buscar sin descifrar toda la tabla |

---

## 3 · Modelo de datos (3FN)

### 3.0 · Diagrama

```
 m01_organizacion 1───n m01_politica_credencial
        │1                         │0..1
        │                          │
        n                          │
   m01_usuario n───1 m01_rol 1───n m01_rol_permiso n───1 m01_permiso
     │1 │1  │1  │1                                        │1
     │  │   │   └──n m01_usuario_permiso n────────────────┘
     │  │   └──────n m01_identificador_usuario
     │  └──────────1 m01_persona
     ├──────────────n m01_credencial
     ├──────────────n m01_sesion n───0..1 m01_dispositivo n───1 m01_organizacion
     ├──────────────n m01_intento_acceso
     ├──────────────n m01_autorizacion_temporal (usuario, otorgada_por, dispositivo?, sesion?)
     └──────────────n m01_miembro_grupo n───1 m01_grupo n───1 m01_organizacion
                                                   └──0..1 m01_politica_credencial
 m01_evento_salida (outbox, sin FK: agregado_tipo + agregado_id)
```

Convenciones del proyecto que se conservan: fechas en **bigint milisegundos** (`*_en`), identificadores compactos, columnas `*_cifrado` para AES-GCM y `*_hmac` para índice ciego, ninguna columna de texto plano con PII.

### 3.1 · `m01_organizacion` · Organizacion

El colegio, instituto o universidad. Un nodo de aula suele tener una sola fila, pero la configuración de credenciales y los grupos cuelgan de aquí para que el modelo sirva también a una instalación central.

| Columna | Tipo | Nota |
|---|---|---|
| `id` | char(36) PK | UUID |
| `codigo` | char(32) UNIQUE | Corto, para mostrar en la tableta («IE-SANJOSE») |
| `nombre` | char(200) | No es PII |
| `pais` | char(2) | ISO 3166-1 alpha-2 (`CO`, `MX`) |
| `idioma` | char(8) | ISO 639-1 (`es`) |
| `locale` | char(16) | BCP 47 (`es-CO`) |
| `zona_horaria` | char(64) | IANA (`America/Bogota`) |
| `creado_en` | bigint | |

### 3.2 · `m01_politica_credencial` · PoliticaCredencial

Qué identificador y qué secreto usa cada perfil en ese colegio. Es lo que hace configurable el login del estudiante.

| Columna | Tipo | Nota |
|---|---|---|
| `id` | char(36) PK | |
| `organizacion_id` | FK | |
| `perfil` | char(16) | `student` / `teacher` / `admin` (coincide con `m01_rol.menu_principal`) |
| `tipo_identificador` | char(24) | `DNI` / `CODIGO_ESTUDIANTIL` / `EMAIL` / `CUALQUIERA` |
| `tipo_secreto` | char(16) | `PIN` / `PASSWORD` |
| `longitud_minima` | smallint | 6 para PIN, 8 para contraseña |
| `exige_mayuscula`, `exige_minuscula`, `exige_digito`, `exige_simbolo` | bool | Reglas de fortaleza. Para `PIN` se ignoran salvo `exige_digito` |
| `intentos_maximos` | smallint | 5 por defecto |
| `ventana_intentos_min` | smallint | 15: los fallos cuentan dentro de esta ventana |
| `bloqueo_minutos` | smallint | 15: cuánto dura el bloqueo automático |
| `duracion_sesion_min` | int | **240** por defecto (R-08) |
| `vigencia_credencial_dias` | int null | Null = no caduca |
| `permite_acceso_temporal` | bool | Si el perfil puede recibir autorizaciones temporales (sólo `student` por defecto) |
| `creado_en`, `actualizado_en` | bigint | |

Invariantes: `UNIQUE(organizacion_id, perfil)`; `longitud_minima >= 4`; `tipo_secreto = 'PIN'` implica `longitud_minima BETWEEN 4 AND 8`.

Semilla: `student` → `CODIGO_ESTUDIANTIL` + `PIN` de 6; `teacher` → `DNI` + `PASSWORD` de 8 con mayúscula y símbolo; `admin` → `DNI` + `PASSWORD` de 12 con mayúscula, dígito y símbolo.

### 3.3 · `m01_rol` · Rol

| Columna | Tipo | Nota |
|---|---|---|
| `id` | char(36) PK | |
| `organizacion_id` | FK null | Null = **plantilla de sistema** compartida (plug-and-play). No nulo = rol propio del colegio |
| `codigo` | char(32) | `STUDENT`, `TEACHER`, `ADMIN`, o el que defina el colegio (`COORDINADOR`) |
| `nombre` | char(80) | |
| `menu_principal` | char(16) | `student` / `teacher` / `admin`. **Decide qué menú abre el cliente MAUI** |
| `nivel` | smallint | 1 estudiante, 2 docente, 3 administrador. Un actor nunca administra a alguien de nivel igual o superior salvo con alcance `ORGANIZATION` y nivel ≥ objetivo |
| `es_sistema` | bool | Las plantillas no se editan ni se borran |
| `creado_en` | bigint | |

Invariantes: `UNIQUE(organizacion_id, codigo)` (con nulos tratados como valor único en SQLite mediante índice parcial); `es_sistema` implica `organizacion_id IS NULL`.

### 3.4 · `m01_permiso` · Permiso

Catálogo cerrado y sembrado. Los códigos son `Value Objects` (`PermissionCode`): `modulo.recurso.accion`.

| Columna | Tipo | Nota |
|---|---|---|
| `codigo` | char(64) PK | `student.progress.read` |
| `modulo` | char(24) | `acceso`, `expediente`, `contenido`, `aula` |
| `descripcion` | char(200) | |
| `alcance_maximo` | char(20) | Techo razonable: `credential.change_own` nunca pasa de `SELF` |

Catálogo inicial (§5).

### 3.5 · `m01_rol_permiso` · RolPermiso

| Columna | Tipo | Nota |
|---|---|---|
| `id` | bigint PK | |
| `rol_id` | FK | |
| `permiso_codigo` | FK | |
| `alcance` | char(20) | `SELF` / `ASSIGNED_GROUPS` / `ORGANIZATION` |

Invariantes: `UNIQUE(rol_id, permiso_codigo)`; `alcance <= permiso.alcance_maximo` (validado por la política).

### 3.6 · `m01_usuario` · Usuario

La **cuenta**. No contiene datos personales.

| Columna | Tipo | Nota |
|---|---|---|
| `id` | char(36) PK | UUID. Es el `persona_id` que el expediente ya usa como identificador externo |
| `organizacion_id` | FK | |
| `rol_id` | FK | **Exactamente un rol.** Decide el menú |
| `estado` | char(16) | `ACTIVO` / `BLOQUEADO` / `SUSPENDIDO` / `RETIRADO`. `BLOQUEADO` es sólo el bloqueo manual; el automático se **calcula** con `m01_intento_acceso` |
| `alias` | char(64) | Apodo visible en el aula («Juan P.») sin PII completa. Lo que muestra la tableta compartida |
| `idioma` | char(8) | ISO 639-1, preferencia de interfaz |
| `creado_en`, `actualizado_en` | bigint | |
| `creado_por` | FK null (usuario) | |
| `ultimo_acceso_en` | bigint null | |

### 3.7 · `m01_persona` · Persona (1:1)

Datos personales, siempre cifrados. Separada de la cuenta para que un volcado de `m01_usuario` no exponga nada.

| Columna | Tipo | Protección |
|---|---|---|
| `usuario_id` | PK, FK | |
| `nombres_cifrado` | text | AES-256-GCM |
| `apellidos_cifrado` | text | AES-256-GCM |
| `fecha_nacimiento_cifrado` | text null | AES-256-GCM (menores de edad: se guarda, no se muestra por defecto) |
| `telefono_cifrado` | text null | AES-256-GCM |
| `telefono_hmac` | char(64) null | HMAC-SHA-256, índice para buscar |
| `pais` | char(2) | ISO 3166-1 alpha-2 |
| `actualizado_en` | bigint | |

### 3.8 · `m01_identificador_usuario` · IdentificadorUsuario

Con qué se identifica una persona. Un estudiante puede tener DNI **y** código estudiantil; cuál sirve para entrar lo decide la política.

| Columna | Tipo | Nota |
|---|---|---|
| `id` | char(36) PK | |
| `usuario_id` | FK | |
| `tipo` | char(24) | `DNI` / `CODIGO_ESTUDIANTIL` / `EMAIL` |
| `valor_cifrado` | text | AES-256-GCM: para mostrarlo |
| `valor_hmac` | char(64) | HMAC-SHA-256 del valor **normalizado**: para buscarlo |
| `es_login` | bool | Si sirve para iniciar sesión |
| `verificado_en` | bigint null | |
| `creado_en` | bigint | |

Invariantes: `UNIQUE(tipo, valor_hmac)`; como mucho un identificador por `(usuario_id, tipo)`.

Normalización antes del HMAC: DNI y código → mayúsculas, sin espacios, puntos ni guiones; email → minúsculas y sin espacios.

### 3.9 · `m01_credencial` · Credencial

| Columna | Tipo | Nota |
|---|---|---|
| `id` | char(36) PK | |
| `usuario_id` | FK | |
| `tipo` | char(16) | `PIN` / `PASSWORD` |
| `hash` | char(255) | Cadena codificada de **Argon2id** (`$argon2id$v=19$m=65536,t=3,p=1$…`): incluye parámetros y sal |
| `activa` | bool | Sólo una activa por usuario |
| `debe_cambiar` | bool | Verdadero cuando la asignó un profesor (restablecimiento) |
| `creado_en` | bigint | |
| `expira_en` | bigint null | Derivado de `vigencia_credencial_dias` en el momento de crearla |
| `sustituida_en` | bigint null | Cuando dejó de estar activa |
| `creado_por` | FK null | Quién la estableció (el propio usuario o un docente/administrador) |

Invariantes: índice único parcial `(usuario_id) WHERE activa`; `activa = false` implica `sustituida_en IS NOT NULL`. El historial permite rechazar la reutilización de las últimas N credenciales.

### 3.10 · `m01_usuario_permiso` · UsuarioPermiso

Permisos **adicionales** a los del rol, con alcance y vigencia. Sustituye a la tabla contextual gigante.

| Columna | Tipo | Nota |
|---|---|---|
| `id` | char(36) PK | |
| `usuario_id` | FK | |
| `permiso_codigo` | FK | |
| `alcance` | char(20) | |
| `otorgado_por` | FK | |
| `motivo` | char(200) | Obligatorio: es lo que se lee en auditoría |
| `vigente_desde`, `vigente_hasta` | bigint / bigint null | |
| `revocado_en` | bigint null | |

Invariantes: `UNIQUE(usuario_id, permiso_codigo) WHERE revocado_en IS NULL`; `vigente_hasta IS NULL OR vigente_hasta > vigente_desde`.

### 3.11 · `m01_grupo` · Grupo

El contexto que da sentido a `ASSIGNED_GROUPS`. Es el grupo de clase («8-A · 2026»), no el curso de la biblioteca.

| Columna | Tipo | Nota |
|---|---|---|
| `id` | char(36) PK | |
| `organizacion_id` | FK | |
| `codigo` | char(32) | |
| `nombre` | char(120) | |
| `periodo` | char(16) | «2026», «2026-1» |
| `politica_credencial_id` | FK null | Sobrescribe la política del perfil (grados superiores con contraseña) |
| `activo` | bool | |
| `creado_en` | bigint | |

Invariante: `UNIQUE(organizacion_id, codigo, periodo)`.

### 3.12 · `m01_miembro_grupo` · MiembroGrupo

| Columna | Tipo | Nota |
|---|---|---|
| `id` | char(36) PK | |
| `grupo_id` | FK | |
| `usuario_id` | FK | |
| `papel` | char(16) | `ESTUDIANTE` / `DOCENTE` |
| `desde` | bigint | |
| `hasta` | bigint null | Null = vigente |

Invariante: `UNIQUE(grupo_id, usuario_id, papel)`. La regla `ASSIGNED_GROUPS` es: *existe un grupo donde el actor es `DOCENTE` vigente y el objetivo es miembro vigente*.

### 3.13 · `m01_dispositivo` · Dispositivo

| Columna | Tipo | Nota |
|---|---|---|
| `id` | char(36) PK | |
| `organizacion_id` | FK | |
| `identificador` | char(128) | Lo que la app MAUI genera una vez y guarda en su almacenamiento seguro |
| `nombre` | char(64) | «tableta-07»; es el `dispositivo` que ya graba el expediente |
| `tipo` | char(16) | `TABLETA` / `MASTER` |
| `activo` | bool | |
| `registrado_en`, `ultimo_visto_en` | bigint | |

Invariante: `UNIQUE(organizacion_id, identificador)`.

### 3.14 · `m01_sesion` · Sesion

| Columna | Tipo | Nota |
|---|---|---|
| `id` | char(36) PK | Es el `jti` del JWT |
| `usuario_id` | FK | |
| `dispositivo_id` | FK null | |
| `clase` | char(16) | `NORMAL` / `TEMPORAL` (nació de una autorización temporal) |
| `emitida_en`, `expira_en` | bigint | `expira_en = emitida_en + duracion_sesion_min` |
| `ultimo_uso_en` | bigint null | |
| `revocada_en` | bigint null | |
| `motivo_revocacion` | char(64) null | `logout`, `docente`, `administrador`, `credencial_cambiada`, `expirada` |

Invariante: `expira_en > emitida_en`; `revocada_en IS NULL OR motivo_revocacion IS NOT NULL`.

### 3.15 · `m01_intento_acceso` · IntentoAcceso

Registro de cada intento de autenticación. De aquí se **calcula** el bloqueo automático (no hay contador desnormalizado en `m01_usuario`).

| Columna | Tipo | Nota |
|---|---|---|
| `id` | bigint PK | |
| `usuario_id` | FK null | Null cuando el identificador no existe |
| `identificador_hmac` | char(64) | Lo que se intentó, ciego |
| `dispositivo_id` | FK null | |
| `resultado` | char(24) | `EXITO` / `FALLO` / `BLOQUEADO` / `DESBLOQUEO` / `TEMPORAL_EXITO` / `TEMPORAL_FALLO` |
| `motivo` | char(64) | `secreto_invalido`, `usuario_inexistente`, `identificador_no_permitido`, `credencial_expirada`… |
| `autorizacion_id` | FK null | Cuando el intento fue canjear una autorización temporal |
| `momento` | bigint | |

Regla de bloqueo: se cuentan los `FALLO` posteriores al último `EXITO` o `DESBLOQUEO` dentro de `ventana_intentos_min`; al llegar a `intentos_maximos` el usuario queda bloqueado hasta `último_fallo + bloqueo_minutos`. *Desbloquear usuario* inserta una fila `DESBLOQUEO`.

### 3.16 · `m01_autorizacion_temporal` · AutorizacionTemporal

La emergencia «el examen empieza en 3 minutos».

| Columna | Tipo | Nota |
|---|---|---|
| `id` | char(36) PK | |
| `usuario_id` | FK | El estudiante |
| `otorgada_por` | FK | El docente |
| `tipo` | char(16) | `DISPOSITIVO` (opción A) / `CODIGO` (opción B) |
| `dispositivo_id` | FK null | Obligatorio en `DISPOSITIVO`: sólo esa tableta puede canjearla |
| `secreto_hash` | char(255) | Opción A: SHA-256 del token aleatorio de 256 bits. Opción B: **Argon2id** del código de 6 dígitos (baja entropía) |
| `evaluacion_ref` | char(200) null | Si se indica, la sesión resultante sólo sirve para esa evaluación |
| `creada_en`, `expira_en` | bigint | 5 minutos por defecto |
| `usada_en` | bigint null | Un solo uso |
| `revocada_en` | bigint null | |
| `sesion_id` | FK null | La sesión `TEMPORAL` que produjo |
| `motivo` | char(200) | Lo que escribió el docente |

Invariantes: `UNIQUE(sesion_id)`; `tipo = 'DISPOSITIVO'` implica `dispositivo_id IS NOT NULL`; `usada_en IS NULL OR sesion_id IS NOT NULL`. Los canjes fallidos van a `m01_intento_acceso` con `autorizacion_id`; al tercer fallo la autorización se revoca.

### 3.17 · `m01_evento_salida` · EventoSalida (Transactional Outbox)

| Columna | Tipo | Nota |
|---|---|---|
| `id` | bigint PK | |
| `agregado_tipo` | char(32) | `usuario`, `sesion`, `credencial`, `autorizacion_temporal`, `grupo` |
| `agregado_id` | char(36) | |
| `tipo_evento` | char(64) | `acceso.usuario.creado`, `acceso.sesion.revocada`… |
| `carga` | JSON | **Sólo identificadores y códigos**; nunca PII ni secretos |
| `creado_en` | bigint | |
| `publicado_en` | bigint null | Lo marca el publicador cuando haya con quién sincronizar |
| `intentos` | smallint | |

Se escribe **en la misma transacción** que el cambio (Unit of Work). La auditoría de seguridad legible por el docente se registra en la tabla existente `m19_auditoria` a través del puerto `RegistroAuditoria`.

---

## 4 · Protección de la información

| Dato | Protección | Motivo | Implementación |
|---|---|---|---|
| Contraseña | **Argon2id** `m=64 MiB, t=3, p=1` | Nunca se recupera | `argon2-cffi` `PasswordHasher`; `check_needs_rehash` al entrar |
| PIN estudiante | **Argon2id** (mismos parámetros) | Es una credencial de baja entropía: el coste de cómputo y el bloqueo por intentos son su defensa | ídem |
| Código temporal de 6 dígitos | **Argon2id** | Baja entropía, vida de 5 min, un solo uso, 3 fallos | ídem |
| Token de dispositivo (256 bits) | SHA-256 | Alta entropía: el hash rápido basta y no frena el canje | `hashlib` |
| DNI / código estudiantil / email | **AES-256-GCM + HMAC-SHA-256** | Hay que mostrar y buscar | `cryptography` `AESGCM`; nonce de 96 bits por valor; AAD = nombre de la columna |
| Nombres, apellidos, fecha de nacimiento, teléfono | **AES-256-GCM** (+ HMAC para teléfono) | Hay que recuperarlos | ídem |
| JWT | **HS256** con clave local de 256 bits | Un solo emisor y verificador (el nodo); sin PKI en el aula | `PyJWT` |

Claves: `AVACOM_LMS_CLAVE_DATOS` (AES), `AVACOM_LMS_CLAVE_INDICE` (HMAC) y `AVACOM_LMS_CLAVE_TOKENS` (JWT), en base64 de 32 bytes, entregadas por el instalador en `backend.env`. Si faltan, el prototipo las **deriva con HKDF-SHA256** de `SECRET_KEY` con etiquetas distintas y lo advierte en `/health/`. Cada valor cifrado lleva prefijo de versión de clave (`v1:`) para poder rotar.

Formato del JWT (payload):

```json
{
  "iss": "avacom-lms", "sub": "<usuario_id>", "jti": "<sesion_id>",
  "org": "<organizacion_id>", "rol": "TEACHER", "menu": "teacher", "nivel": 2,
  "dev": "<dispositivo_id|null>", "clase": "NORMAL",
  "eval": null, "iat": 1789000000, "exp": 1789014400
}
```

Los **permisos no viajan en el token**: se evalúan contra la base local en cada petición, de modo que revocar un permiso o una sesión tiene efecto inmediato y el token sigue siendo pequeño. El cliente pide `GET /api/acceso/yo/` para pintar el menú.

Controles OWASP Top 10 que cubre el modelo: **A01** (autorización centralizada en `PoliticaAutorizacion`, denegar por defecto), **A02** (Argon2id, AES-GCM, claves separadas), **A04** (límites de intentos, vigencia, un solo uso), **A05** (`DEBUG=0` en distribución, políticas sembradas seguras), **A07** (bloqueo progresivo, sesiones revocables, obligación de cambiar la credencial provisional, prohibición de PIN triviales), **A09** (intentos y acciones en auditoría append-only).

---

## 5 · Plantillas plug-and-play

### 5.1 · Catálogo de permisos

| Código | Módulo | Alcance máximo | Descripción |
|---|---|---|---|
| `student.progress.read` | expediente | ORGANIZATION | Ver progreso y notas |
| `student.progress.write` | expediente | SELF | Registrar aperturas y avance |
| `student.exam.attempt` | expediente | SELF | Rendir evaluaciones |
| `results.read` | expediente | ORGANIZATION | Ver resultados |
| `content.read` | contenido | ORGANIZATION | Ver cursos de la biblioteca |
| `content.project` | aula | ASSIGNED_GROUPS | Proyectar en la pantalla del aula |
| `user.read` | acceso | ORGANIZATION | Ver usuarios |
| `user.create` | acceso | ORGANIZATION | Crear usuarios |
| `user.update` | acceso | ORGANIZATION | Editar datos y estado |
| `user.role.assign` | acceso | ORGANIZATION | Asignar rol |
| `user.permission.grant` | acceso | ORGANIZATION | Otorgar permisos adicionales |
| `user.unlock` | acceso | ORGANIZATION | Desbloquear |
| `credential.reset` | acceso | ORGANIZATION | Restablecer credencial ajena |
| `credential.change_own` | acceso | SELF | Cambiar la propia |
| `exam.temporary_access.grant` | acceso | ASSIGNED_GROUPS | Autorizar acceso temporal a examen |
| `session.read` | acceso | ORGANIZATION | Ver sesiones |
| `session.revoke` | acceso | ORGANIZATION | Revocar sesiones ajenas |
| `session.revoke_own` | acceso | SELF | Cerrar la propia |
| `group.read` | acceso | ORGANIZATION | Ver grupos |
| `group.manage` | acceso | ORGANIZATION | Crear y editar grupos |
| `group.member.manage` | acceso | ORGANIZATION | Añadir y quitar miembros |
| `role.read` | acceso | ORGANIZATION | Ver roles y permisos |
| `role.manage` | acceso | ORGANIZATION | Crear roles del colegio |
| `policy.manage` | acceso | ORGANIZATION | Configurar la política de credenciales |
| `device.manage` | acceso | ORGANIZATION | Registrar y dar de baja dispositivos |
| `audit.read` | acceso | ORGANIZATION | Leer auditoría |

### 5.2 · Roles de sistema

| Permiso | STUDENT | TEACHER | ADMIN |
|---|---|---|---|
| `student.progress.read` | SELF | ASSIGNED_GROUPS | ORGANIZATION |
| `student.progress.write` | SELF | — | — |
| `student.exam.attempt` | SELF | — | — |
| `results.read` | SELF | ASSIGNED_GROUPS | ORGANIZATION |
| `content.read` | SELF | ORGANIZATION | ORGANIZATION |
| `content.project` | — | ASSIGNED_GROUPS | ASSIGNED_GROUPS |
| `user.read` | SELF | ASSIGNED_GROUPS | ORGANIZATION |
| `user.create` | — | ASSIGNED_GROUPS (sólo estudiantes) | ORGANIZATION |
| `user.update` | — | ASSIGNED_GROUPS | ORGANIZATION |
| `user.role.assign` | — | — | ORGANIZATION |
| `user.permission.grant` | — | — | ORGANIZATION |
| `user.unlock` | — | ASSIGNED_GROUPS | ORGANIZATION |
| `credential.reset` | — | ASSIGNED_GROUPS | ORGANIZATION |
| `credential.change_own` | SELF | SELF | SELF |
| `exam.temporary_access.grant` | — | ASSIGNED_GROUPS | ASSIGNED_GROUPS |
| `session.read` | SELF | ASSIGNED_GROUPS | ORGANIZATION |
| `session.revoke` | — | ASSIGNED_GROUPS | ORGANIZATION |
| `session.revoke_own` | SELF | SELF | SELF |
| `group.read` | SELF | ASSIGNED_GROUPS | ORGANIZATION |
| `group.manage` | — | — | ORGANIZATION |
| `group.member.manage` | — | ASSIGNED_GROUPS | ORGANIZATION |
| `role.read` | — | ORGANIZATION | ORGANIZATION |
| `role.manage`, `policy.manage`, `device.manage`, `audit.read` | — | — | ORGANIZATION |

El colegio puede clonar una plantilla en un rol propio (`organizacion_id` no nulo) y ajustar alcances; las plantillas no se tocan.

### 5.3 · Evaluación de una decisión (Policy Pattern)

```
decidir(actor, permiso, objetivo):
    concesiones = rol_permiso[actor.rol] ∪ usuario_permiso[actor, vigentes]
    alcance = max(concesiones[permiso])            # ausencia → DENEGADO
    si alcance == ORGANIZATION:
        permitir si actor.org == objetivo.org y actor.nivel >= objetivo.nivel
    si alcance == ASSIGNED_GROUPS:
        permitir si objetivo.nivel == 1 (estudiante)
                 y ∃ grupo: actor DOCENTE vigente ∧ objetivo miembro vigente
    si alcance == SELF:
        permitir si actor.id == objetivo.id
```

El objetivo puede ser un usuario, un grupo (se evalúa la pertenencia del actor como docente) o «la organización» (operaciones sin objetivo concreto, como listar roles). La política es una clase pura de `dominio/` con pruebas unitarias sin base de datos.

---

## 6 · Arquitectura del módulo (`backend/acceso/`)

```
DRF (interfaces/views.py, serializers.py, autenticacion.py, urls.py)
      ↓
Casos de uso (aplicacion/casos_uso.py)            ← Use Case Pattern
      ↓
Dominio (dominio/entidades.py, valores.py, politicas.py, errores.py, plantillas.py)
      ↓
Puertos (aplicacion/puertos.py)                    ← Repository, UnitOfWork, Hasher, Cifrador, EmisorTokens, Reloj, Azar, Auditoría
      ↓
Adaptadores (infraestructura/repositorios.py, unidad_trabajo.py, seguridad.py, contenedor.py)
      ↓
Django ORM (models.py) → SQLite
```

| Patrón | Dónde | Regla |
|---|---|---|
| Use Case | `aplicacion/casos_uso.py`: `CrearUsuario`, `AutenticarUsuario`, `AsignarRol`, `OtorgarPermiso`, `RestablecerCredencial`, `CambiarCredencialPropia`, `DesbloquearUsuario`, `OtorgarAccesoTemporal`, `CanjearAccesoTemporal`, `RevocarSesion`, `ConsultarIdentidad`, `CrearGrupo`, `AgregarMiembro`, `RegistrarDispositivo`, `ConfigurarPolitica` | Uno por operación; reciben un `Comando`, devuelven un `Resultado`, abren un UoW |
| Repository | `aplicacion/puertos.py` (Protocol) ↔ `infraestructura/repositorios.py` (Django ORM) | Ni dominio ni casos de uso importan `django` |
| Unit of Work | `infraestructura/unidad_trabajo.py` | `transaction.atomic()`; los eventos del outbox se insertan antes del commit |
| Policy | `dominio/politicas.py`: `PoliticaAutorizacion`, `PoliticaFortaleza`, `PoliticaBloqueo` | Sin ORM, sin DRF; se prueban con datos en memoria |
| Value Objects | `dominio/valores.py`: `UserId`, `CountryCode`, `LanguageCode`, `LocaleCode`, `PermissionCode`, `DocumentNumber`, `Alcance`, `Pin`, `Password` | Validan en el constructor |
| Transactional Outbox | `m01_evento_salida` vía `UoW.publicar()` | Misma transacción que el cambio |
| Composition root | `infraestructura/contenedor.py` | El único sitio que sabe qué adaptador va con qué puerto |

Regla de desacoplamiento verificable: una prueba recorre `acceso/dominio` y `acceso/aplicacion` y falla si algún archivo importa `django`, `rest_framework`, `pydantic`, `sqlalchemy` o `fastapi`.

Portabilidad: cambiar a FastAPI + SQLAlchemy significa escribir otro `interfaces/` y otro `infraestructura/repositorios.py` + `unidad_trabajo.py`; `dominio/`, `aplicacion/` y las pruebas de política no cambian.

---

## 7 · Relación con el expediente

- `m01_usuario.id` **es** el `persona_id` que hoy graban `m05_inscripcion`, `m05_progreso_leccion`, `m10_intento`… No se añade FK física desde el expediente (módulos separados del monolito), pero el identificador es el mismo y el `alias` sustituye al `persona_rotulo` que hoy escribe el cliente.
- `m01_dispositivo.nombre` es el `dispositivo` que ya se registra en aperturas e intentos.
- Los artículos 13 y 14 de la [constitución](../01-constitucion.md) no se tocan: ninguna tabla de este módulo describe contenido; `m01_autorizacion_temporal.evaluacion_ref` es una referencia emitida por la biblioteca, como las demás `*_ref`.
- La exigencia de sesión en las rutas del expediente queda **preparada, no activada** (`AVACOM_LMS_EXIGIR_SESION=0` por defecto) para no romper a los clientes MAUI ya distribuidos. Activarla es la decisión Q-34.

---

## 8 · Preguntas abiertas

| # | Pregunta | Propuesta |
|---|---|---|
| Q-34 | ¿Cuándo se exige sesión en `/api/students/…`, `/api/aperturas/`, `/api/intentos/…`? | Cuando OPS y Student incorporen la pantalla de acceso (ver [acceso-sugerencias.html](../../specs/presentaciones/acceso-sugerencias.html)) |
| Q-35 | ¿El instalador genera las tres claves en `backend.env`? | Sí, con `RandomNumberGenerator` de .NET en el asistente; hasta entonces HKDF de `SECRET_KEY` con aviso en `/health/` |
| Q-36 | ¿Sincronización con una sede central? | El outbox ya deja los eventos; el publicador se define con el contrato de la sede |
| Q-37 | ¿Roles adicionales simultáneos (profesor que también administra)? | Hoy: cambiar el rol o dar permisos adicionales con `ORGANIZATION`. Si hace falta, `m01_usuario_rol` es una tabla de enlace trivial que no rompe nada |
