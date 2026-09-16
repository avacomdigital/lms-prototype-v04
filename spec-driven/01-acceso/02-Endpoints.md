# 02 · Módulo de acceso y usuarios · Endpoints (APIViews)

| Campo | Valor |
|---|---|
| Prefijo | `/api/acceso/` (incluido desde `avacom_lms/urls.py`) |
| Estilo | `APIView` de DRF, JSON, sin `ModelSerializer` hacia el dominio: las vistas traducen HTTP ↔ casos de uso |
| Autenticación | `Authorization: Bearer <JWT>`; la clase `AutenticacionJwt` resuelve la sesión y construye un `Principal` |
| Autorización | Cada vista declara `permiso` y calcula el `objetivo`; la decisión la toma `PoliticaAutorizacion` (dominio), nunca la vista |
| Modelo | [01 · Modelado de datos](01-modelado-datos.md) |
| Estado | Implementado en `backend/acceso/interfaces/` con pruebas en `backend/acceso/tests/` |

---

## 0 · Convenciones

### 0.1 · Respuestas de error

Todas las rutas devuelven errores con la misma forma:

```json
{ "detail": "Texto legible para el docente", "codigo": "credenciales_invalidas" }
```

| HTTP | `codigo` | Cuándo |
|---|---|---|
| 400 | `datos_invalidos`, `secreto_debil`, `identificador_duplicado`, `politica_invalida` | Validación de entrada o de reglas de dominio |
| 401 | `sesion_requerida`, `sesion_invalida`, `sesion_expirada`, `sesion_revocada`, `credenciales_invalidas` | Sin token, token inválido o login fallido. Se envía `WWW-Authenticate: Bearer` |
| 403 | `sin_permiso`, `debe_cambiar_credencial`, `sesion_temporal_limitada` | El actor **no tiene el permiso en absoluto** (o una regla transversal lo frena). Incluye `permiso`, `alcance_requerido` y `alcance_concedido` |
| 404 | `no_encontrado` | Recurso inexistente, o el actor **tiene el permiso pero no alcanza a ese objetivo** (un docente sobre un estudiante de otro grupo). No se revela existencia. Otra organización siempre es 404 |
| 409 | `conflicto`, `ya_instalado`, `autorizacion_usada` | Estado incompatible |
| 423 | `usuario_bloqueado` | Bloqueo automático o manual. Incluye `reintentar_en_seg` cuando es automático |

### 0.2 · Fechas

Todas en **milisegundos desde época** (bigint), como el resto del backend.

### 0.3 · El `Principal`

Lo que la vista recibe en `request.user` después de autenticar:

```python
Principal(usuario_id, organizacion_id, rol_codigo, menu, nivel, sesion_id, clase_sesion, evaluacion_ref, debe_cambiar_credencial, dispositivo_id)
```

Reglas transversales aplicadas por `PoliticaAutorizacion` antes de cualquier permiso:

- `debe_cambiar_credencial = true` → sólo se permiten `credential.change_own` y `session.revoke_own` (403 `debe_cambiar_credencial`).
- `clase_sesion = TEMPORAL` → sólo `student.exam.attempt`, `student.progress.read`, `student.progress.write`, `content.read`, `results.read`, `session.revoke_own`, todos `SELF` (403 `sesion_temporal_limitada`).
- El resto se decide con rol + permisos adicionales + alcance (§5.3 del modelado).

---

## 1 · Rutas sin sesión

### 1.1 · `GET /api/acceso/configuracion/`

Lo que la tableta necesita para pintar la pantalla de acceso. **Sin PII.**

```json
{
  "instalado": true,
  "organizacion": { "id": "…", "codigo": "IE-SANJOSE", "nombre": "IE San José", "pais": "CO", "idioma": "es", "locale": "es-CO" },
  "perfiles": {
    "student": { "tipo_identificador": "CODIGO_ESTUDIANTIL", "tipo_secreto": "PIN", "longitud_minima": 6, "permite_acceso_temporal": true },
    "teacher": { "tipo_identificador": "DNI", "tipo_secreto": "PASSWORD", "longitud_minima": 8, "permite_acceso_temporal": false },
    "admin":   { "tipo_identificador": "DNI", "tipo_secreto": "PASSWORD", "longitud_minima": 12, "permite_acceso_temporal": false }
  },
  "duracion_sesion_min": 240,
  "claves_derivadas": false
}
```

`instalado = false` significa que aún no hay organización: el cliente debe ofrecer §1.2. `claves_derivadas = true` avisa de que las claves de cifrado se derivaron de `SECRET_KEY` (Q-35).

### 1.2 · `POST /api/acceso/instalacion/`

Primer arranque. Sólo funciona **mientras no exista ninguna organización** (409 `ya_instalado` después). Crea organización, políticas sembradas y el primer administrador. Caso de uso `InstalarNodo`.

```json
{
  "organizacion": { "codigo": "IE-SANJOSE", "nombre": "IE San José", "pais": "CO", "idioma": "es", "locale": "es-CO", "zona_horaria": "America/Bogota" },
  "administrador": { "alias": "Rectoría", "nombres": "Ana", "apellidos": "Pérez", "dni": "1042888795", "password": "Rectoria.2026!" }
}
```

→ `201` `{ "organizacion": {…}, "administrador": { "id": "…", "alias": "Rectoría" } }`. Si `password` se omite, se genera una y se devuelve **una sola vez** en `password_inicial`.

### 1.3 · `POST /api/acceso/dispositivos/`

Registro idempotente de la tableta o del nodo principal (por `identificador`).

```json
{ "identificador": "a8f3…-tablet", "nombre": "tableta-07", "tipo": "TABLETA" }
```

→ `201` la primera vez, `200` después: `{ "id": "…", "nombre": "tableta-07", "tipo": "TABLETA", "activo": true }`.

### 1.4 · `POST /api/acceso/sesiones/` · Autenticar usuario

```json
{ "identificador": "122499", "secreto": "691302", "dispositivo": "a8f3…-tablet" }
```

Reglas: se normaliza el identificador, se busca por HMAC, se comprueba que el **tipo** de identificador está permitido por la política del perfil (o del grupo), se verifica Argon2id, se aplica `PoliticaBloqueo`, se registra `m01_intento_acceso`, se emite el JWT y se crea `m01_sesion`.

→ `200`

```json
{
  "token": "eyJhbGciOiJIUzI1NiIs…",
  "tipo": "Bearer",
  "expira_en": 1789014400000,
  "sesion_id": "…",
  "usuario": { "id": "…", "alias": "Juan P.", "rol": "STUDENT", "menu": "student", "nivel": 1, "debe_cambiar_credencial": false }
}
```

Errores: `401 credenciales_invalidas` (mismo mensaje y mismo tiempo de respuesta para usuario inexistente, tipo no permitido y secreto incorrecto), `423 usuario_bloqueado` con `reintentar_en_seg`.

### 1.5 · `POST /api/acceso/autorizaciones-temporales/canjear/` · Canjear acceso temporal

Opción B (código que el docente le dicta al estudiante):

```json
{ "codigo": "834195", "dispositivo": "a8f3…-tablet" }
```

Opción A (la tableta recibió `grant_id` + `token` del nodo):

```json
{ "grant_id": "…", "token": "b64url-256-bits", "dispositivo": "a8f3…-tablet" }
```

→ `200` misma forma que §1.4 con `usuario.clase_sesion = "TEMPORAL"` y `evaluacion_ref` si la autorización lo fijó. Errores: `401 credenciales_invalidas` (código incorrecto, caducado, ya usado, otra tableta); al tercer fallo la autorización queda revocada y el docente ve `revocada_en`.

---

## 2 · Identidad propia

### 2.1 · `GET /api/acceso/yo/`

```json
{
  "usuario": { "id": "…", "alias": "Prof. Gómez", "rol": "TEACHER", "menu": "teacher", "nivel": 2, "idioma": "es", "estado": "ACTIVO",
               "persona": { "nombres": "Luis", "apellidos": "Gómez" } },
  "permisos": [ { "codigo": "student.progress.read", "alcance": "ASSIGNED_GROUPS", "origen": "rol" },
                { "codigo": "audit.read", "alcance": "ORGANIZATION", "origen": "adicional", "vigente_hasta": 1791000000000 } ],
  "grupos": [ { "id": "…", "codigo": "8A", "nombre": "Octavo A", "periodo": "2026", "papel": "DOCENTE" } ],
  "sesion": { "id": "…", "clase": "NORMAL", "expira_en": 1789014400000, "evaluacion_ref": null, "dispositivo": "master" }
}
```

Es la única fuente que el cliente MAUI usa para decidir qué hexágonos mostrar.

### 2.2 · `PUT /api/acceso/yo/credencial/` · Cambiar credencial propia

```json
{ "secreto_actual": "691302", "secreto_nuevo": "480215" }
```

Valida `PoliticaFortaleza` según la política vigente del usuario, rechaza las últimas 3 credenciales, limpia `debe_cambiar`, **revoca las demás sesiones** (`credencial_cambiada`) y conserva la actual. → `200 { "cambiada": true, "sesiones_revocadas": 1 }`. Permiso `credential.change_own`.

### 2.3 · `DELETE /api/acceso/sesiones/actual/` · Cerrar sesión

→ `204`. Permiso `session.revoke_own`.

---

## 3 · Sesiones

| Ruta | Verbo | Permiso · objetivo | Nota |
|---|---|---|---|
| `/api/acceso/sesiones/?usuario=<id>&activas=1` | GET | `session.read` · el usuario filtrado (o la organización si no hay filtro) | Lista `id, usuario_id, alias, dispositivo, clase, emitida_en, expira_en, ultimo_uso_en, revocada_en` |
| `/api/acceso/sesiones/{id}/` | DELETE | `session.revoke` · dueño de la sesión | Caso de uso `RevocarSesion`. `motivo_revocacion` = `docente` o `administrador` según el nivel del actor. Idempotente: `204` aunque ya estuviera revocada |

---

## 4 · Usuarios

### 4.1 · `GET /api/acceso/usuarios/?grupo=<id>&rol=STUDENT&estado=ACTIVO`

Permiso `user.read`. Con alcance `ASSIGNED_GROUPS` sólo aparecen estudiantes de los grupos del docente; el filtro `grupo` fuera de alcance devuelve `404`. La PII (`persona`) se descifra sólo para quien tiene `user.read` sobre ese usuario.

```json
[ { "id": "…", "alias": "Juan P.", "rol": "STUDENT", "menu": "student", "estado": "ACTIVO",
    "bloqueado_hasta": null, "debe_cambiar_credencial": false, "ultimo_acceso_en": 1788990000000,
    "persona": { "nombres": "Juan", "apellidos": "Pérez" },
    "identificadores": [ { "tipo": "CODIGO_ESTUDIANTIL", "valor": "122499", "es_login": true } ],
    "grupos": [ { "id": "…", "codigo": "8A", "papel": "ESTUDIANTE" } ] } ]
```

### 4.2 · `POST /api/acceso/usuarios/` · Crear usuario

Permiso `user.create`. Un docente (`ASSIGNED_GROUPS`) sólo puede crear estudiantes y **debe** indicar un `grupo_id` propio; el estudiante queda inscrito en él en la misma transacción.

```json
{
  "rol": "STUDENT",
  "alias": "Juan P.",
  "idioma": "es",
  "persona": { "nombres": "Juan", "apellidos": "Pérez", "fecha_nacimiento": "2012-04-09", "pais": "CO" },
  "identificadores": [ { "tipo": "CODIGO_ESTUDIANTIL", "valor": "122499", "es_login": true },
                       { "tipo": "DNI", "valor": "1.020.334.556", "es_login": false } ],
  "secreto": "691302",
  "grupo_id": "…"
}
```

→ `201` con la forma de §4.1 más `secreto_inicial` **sólo si el servidor lo generó** (cuando `secreto` se omite). La credencial nace con `debe_cambiar = true` cuando la estableció otra persona, salvo que quien la crea envíe `"secreto_definitivo": true` junto con un `secreto` explícito (colegios que prefieren PIN fijo asignado por el docente a estudiantes pequeños).

Errores: `400 secreto_debil` (con `reglas` incumplidas), `400 identificador_duplicado`, `403 sin_permiso` (docente intentando crear un docente).

### 4.3 · `GET /api/acceso/usuarios/{id}/` · `PATCH /api/acceso/usuarios/{id}/`

`user.read` / `user.update`. El `PATCH` acepta `alias`, `idioma`, `estado` (`ACTIVO`, `SUSPENDIDO`, `RETIRADO`; `BLOQUEADO` manual sólo con `user.unlock`), `persona` parcial e `identificadores` (reemplazo completo de la lista). Cambiar `estado` a algo distinto de `ACTIVO` revoca las sesiones.

### 4.4 · `PUT /api/acceso/usuarios/{id}/rol/` · Asignar rol

Permiso `user.role.assign` (sólo `ORGANIZATION`). `{ "rol": "TEACHER" }`. El actor no puede asignar un rol de nivel superior al suyo. Revoca las sesiones del usuario (el menú cambia). Caso de uso `AsignarRol`.

### 4.5 · Permisos adicionales

| Ruta | Verbo | Permiso | Cuerpo / respuesta |
|---|---|---|---|
| `/api/acceso/usuarios/{id}/permisos/` | GET | `user.read` | Lista de `m01_usuario_permiso` vigentes y revocados |
| `/api/acceso/usuarios/{id}/permisos/` | POST | `user.permission.grant` | `{ "permiso": "audit.read", "alcance": "ORGANIZATION", "motivo": "Coordinador académico 2026", "vigente_hasta": 1791000000000 }` → `201`. El alcance no puede superar `alcance_maximo` del permiso ni el alcance que el propio actor tiene sobre él |
| `/api/acceso/usuarios/{id}/permisos/{permiso}/` | DELETE | `user.permission.grant` | Sella `revocado_en` → `204` |

### 4.6 · `POST /api/acceso/usuarios/{id}/credencial/restablecer/` · Restablecer credencial

Permiso `credential.reset`. Es la **recuperación real**: el profesor establece un secreto provisional desde el aula.

```json
{ "secreto": "204915" }
```

`secreto` es opcional: si falta, el servidor genera un PIN o contraseña según la política del usuario. → `200 { "secreto_provisional": "204915", "debe_cambiar": true, "sesiones_revocadas": 2 }`. El secreto se devuelve **una sola vez** y no queda en ningún registro. Caso de uso `RestablecerCredencial`.

### 4.7 · `POST /api/acceso/usuarios/{id}/desbloquear/` · Desbloquear usuario

Permiso `user.unlock`. Inserta `DESBLOQUEO` en `m01_intento_acceso` (reinicia la cuenta de fallos) y, si el estado era `BLOQUEADO`, lo pasa a `ACTIVO`. → `200 { "estado": "ACTIVO", "bloqueado_hasta": null }`. Caso de uso `DesbloquearUsuario`.

---

## 5 · Acceso temporal a examen

### 5.1 · `POST /api/acceso/autorizaciones-temporales/` · Otorgar acceso temporal

Permiso `exam.temporary_access.grant` sobre el estudiante. La política del perfil del estudiante debe tener `permite_acceso_temporal`.

Opción A · autorizar la tableta:

```json
{ "usuario_id": "…", "tipo": "DISPOSITIVO", "dispositivo_id": "…", "evaluacion_ref": "co-sec-mat-eval-08", "minutos": 5, "motivo": "Olvidó el PIN antes del parcial" }
```

→ `201`

```json
{ "id": "…", "tipo": "DISPOSITIVO", "expira_en": 1789000300000, "dispositivo": { "id": "…", "nombre": "tableta-07" },
  "entrega": { "grant_id": "…", "token": "b64url-256-bits" } }
```

`entrega` es lo que el nodo principal envía a la tableta (por el canal de aula ya existente); el estudiante no tiene que recordar nada.

Opción B · código para dictar:

```json
{ "usuario_id": "…", "tipo": "CODIGO", "evaluacion_ref": "co-sec-mat-eval-08", "minutos": 5, "motivo": "…" }
```

→ `201 { "id": "…", "tipo": "CODIGO", "expira_en": …, "entrega": { "codigo": "834195" } }`. El código sólo existe en esa respuesta; la base guarda Argon2id.

### 5.2 · `GET /api/acceso/autorizaciones-temporales/?usuario=<id>&vigentes=1`

Permiso `exam.temporary_access.grant`. Lista sin secretos: `id, usuario_id, alias, tipo, dispositivo, evaluacion_ref, creada_en, expira_en, usada_en, revocada_en, sesion_id`.

### 5.3 · `DELETE /api/acceso/autorizaciones-temporales/{id}/`

Revoca la autorización y, si ya produjo una sesión `TEMPORAL`, también la sesión. → `204`.

---

## 6 · Catálogos y configuración

| Ruta | Verbo | Permiso | Nota |
|---|---|---|---|
| `/api/acceso/roles/` | GET | `role.read` | Plantillas de sistema + roles del colegio, cada uno con `permisos: [{codigo, alcance}]` |
| `/api/acceso/roles/` | POST | `role.manage` | `{ "codigo": "COORDINADOR", "nombre": "…", "plantilla": "TEACHER", "menu_principal": "teacher", "nivel": 2, "permisos": [ { "codigo": "audit.read", "alcance": "ORGANIZATION" } ] }` clona la plantilla y aplica los cambios |
| `/api/acceso/permisos/` | GET | `role.read` | Catálogo con `alcance_maximo` |
| `/api/acceso/politicas/` | GET | `policy.manage` | Las tres políticas de la organización |
| `/api/acceso/politicas/{perfil}/` | PUT | `policy.manage` | Cuerpo con las columnas de `m01_politica_credencial`. Caso de uso `ConfigurarPolitica`; valida coherencia (`PIN` ⇒ 4..8 dígitos) |
| `/api/acceso/grupos/` | GET, POST | `group.read` / `group.manage` | `{ "codigo": "8A", "nombre": "Octavo A", "periodo": "2026", "politica_credencial_id": null }` |
| `/api/acceso/grupos/{id}/` | GET, PATCH | `group.read` / `group.manage` | Detalle con `miembros` |
| `/api/acceso/grupos/{id}/miembros/` | POST | `group.member.manage` | `{ "usuario_id": "…", "papel": "ESTUDIANTE" }` → `201`. Un docente sólo añade estudiantes a sus propios grupos |
| `/api/acceso/grupos/{id}/miembros/{usuario_id}/` | DELETE | `group.member.manage` | Sella `hasta` → `204` |
| `/api/acceso/dispositivos/` | GET | `exam.temporary_access.grant` o `device.manage` | Tabletas activas para elegir a cuál autorizar |
| `/api/acceso/dispositivos/{id}/` | PATCH | `device.manage` | `{ "activo": false, "nombre": "…" }` |

---

## 7 · Integración con el resto del backend

| Elemento | Cambio |
|---|---|
| `REST_FRAMEWORK.DEFAULT_AUTHENTICATION_CLASSES` | Se añade `acceso.interfaces.autenticacion.AutenticacionJwt`. Sin cabecera devuelve `None` (anónimo), así que las rutas del expediente **no cambian de comportamiento** |
| `AVACOM_LMS_EXIGIR_SESION` | `0` por defecto. Con `1`, las vistas del expediente y de la biblioteca exigen `Principal` (Q-34). Preparado en `acceso.interfaces.permisos.SesionSiSeExige` |
| `/health/` | Añade `"acceso": { "instalado": true, "claves_derivadas": false }` |
| `m19_auditoria` | Recibe acciones `acceso.sesion.iniciada`, `acceso.sesion.fallida`, `acceso.usuario.bloqueado`, `acceso.usuario.desbloqueado`, `acceso.credencial.restablecida`, `acceso.credencial.cambiada`, `acceso.rol.asignado`, `acceso.permiso.otorgado`, `acceso.permiso.revocado`, `acceso.acceso_temporal.otorgado`, `acceso.acceso_temporal.canjeado`, `acceso.acceso_temporal.revocado`, `acceso.sesion.revocada`, `acceso.usuario.creado`, `acceso.instalacion` |
| `requirements.txt` | `argon2-cffi`, `cryptography`, `PyJWT`; el instalador copia las mismas versiones a `requirements-runtime.txt` |
| Comando | `manage.py acceso_instalar --codigo IE-SANJOSE --nombre "IE San José" --pais CO --admin-dni … [--admin-password …]` ejecuta el mismo caso de uso que §1.2 |

---

## 8 · Trazabilidad casos de uso ↔ rutas

| Caso de uso | Ruta |
|---|---|
| `InstalarNodo` | §1.2 y el comando |
| `RegistrarDispositivo` | §1.3 |
| `AutenticarUsuario` | §1.4 |
| `CanjearAccesoTemporal` | §1.5 |
| `ConsultarIdentidad` | §2.1 |
| `CambiarCredencialPropia` | §2.2 |
| `RevocarSesion` | §2.3, §3, §5.3 |
| `CrearUsuario` | §4.2 |
| `ActualizarUsuario` | §4.3 |
| `AsignarRol` | §4.4 |
| `OtorgarPermiso` / `RevocarPermiso` | §4.5 |
| `RestablecerCredencial` | §4.6 |
| `DesbloquearUsuario` | §4.7 |
| `OtorgarAccesoTemporal` / `RevocarAccesoTemporal` | §5.1, §5.3 |
| `CrearRol` | §6 roles POST |
| `ConfigurarPolitica` | §6 políticas PUT |
| `CrearGrupo` / `AgregarMiembro` / `RetirarMiembro` | §6 grupos |

---

## 9 · Pruebas que acompañan al contrato

| Prueba | Qué comprueba |
|---|---|
| `test_arquitectura` | Ningún archivo de `dominio/` ni `aplicacion/` importa Django, DRF, Pydantic, SQLAlchemy o FastAPI |
| `test_politicas` | Decisiones RBAC + alcance con datos en memoria; PIN triviales rechazados; contraseña docente sin símbolo rechazada |
| `test_seguridad` | AES-GCM cifra/descifra y detecta manipulación; HMAC estable tras normalizar; Argon2id verifica y rehash; JWT caduca |
| `test_api_sesiones` | Instalación única, login por código+PIN, login docente por DNI+contraseña, bloqueo tras 5 fallos y `423`, `yo`, logout, revocación por docente |
| `test_api_usuarios` | Docente crea estudiante en su grupo y no en otro; no crea docentes; restablecer devuelve secreto una vez y obliga a cambiar; desbloquear |
| `test_api_temporal` | Opción A y B: canje, un solo uso, caducidad, tercer fallo revoca, sesión `TEMPORAL` limitada |
| `test_outbox` | Crear usuario deja `m01_evento_salida` en la misma transacción; un fallo posterior no deja ni usuario ni evento |
