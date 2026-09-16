# Backend AVACOM LMS · Django REST Framework

Integra **AVACOM Biblioteca** (dueña de los cursos) con **AVACOM OPS Master** y
**AVACOM Student** (clientes MAUI). Este backend **no administra cursos**: los
lee en vivo de la biblioteca por loopback y guarda únicamente el **expediente
del estudiante** (inscripción, aperturas del visor, progreso, intentos y notas).

```
Tableta (Student) ─┐
                   │ HTTP LAN :8000
OPS Master ────────┼──────────────►  este backend (Django/DRF, SQLite)
                   ┘                      │ loopback · puerto efímero · X-Avacom-Ficha
                                          ▼
                                AVACOM Biblioteca · 127.0.0.1:{puerto de enlace.json}
```

## Requisitos

- Python 3.12 (el entorno virtual queda en `backend/.venv`, ignorado por git).
- AVACOM Biblioteca encendida en el mismo equipo, con la pestaña «Contenido AVACOM»
  abierta y la licencia cargada. Si no está, el backend sigue funcionando en
  modo degradado (503 con motivo en las rutas de contenido; el expediente sigue
  legible con 200).

## Instalar y arrancar

```powershell
cd backend
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python manage.py migrate
.venv\Scripts\python manage.py runserver 0.0.0.0:8000
```

`0.0.0.0:8000` es lo que esperan los clientes: OPS Master en `http://127.0.0.1:8000`
y las tabletas en `http://<IP del equipo maestro>:8000`.

## Probar

```powershell
.venv\Scripts\python manage.py test
```

La suite no necesita la biblioteca real: `tools/host_biblioteca_pruebas.py`
imita el contrato en loopback y escribe su propia nota de enlace, que el backend
encuentra por `AVACOM_CONTENIDO_ENLACE`. Para usar el LMS completo sin la
biblioteca instalada:

```powershell
.venv\Scripts\python -m tools.host_biblioteca_pruebas %TEMP%\enlace-pruebas.json
set AVACOM_CONTENIDO_ENLACE=%TEMP%\enlace-pruebas.json
.venv\Scripts\python manage.py runserver 0.0.0.0:8000
```

## Rutas

| Ruta | Verbo | Qué hace |
|---|---|---|
| `/health/` | GET | Estado del backend y de la biblioteca |
| `/api/biblioteca/estado/` | GET | `estado()` de la biblioteca; nunca falla |
| `/api/biblioteca/cursos/?persona=` | GET | Cursos ofrecidos (con progreso de la persona) |
| `/api/biblioteca/cursos/{curso_ref}/?persona=` | GET | Árbol vigente del curso anotado con el expediente |
| `/api/biblioteca/medio/{ref}/[ruta]` | GET, HEAD | Bytes de un material (capacidad `medio`, con `Range`) |
| `/api/biblioteca/leccion/{ref}/` | GET | Pasos de una lección (capacidad `leccion`) |
| `/api/biblioteca/evaluacion/{ref}/` | GET | Preguntas sin clave (capacidad `evaluacion`) |
| `/api/biblioteca/voz/{ref}/[pregunta]/` | GET | Instrucción hablada (capacidad `voz`) |
| `/api/biblioteca/mostrar/` | POST | Proyecta en la pantalla del aula |
| `/api/biblioteca/catalogo/`, `taxonomia/`, `elementos/{ref}/` | GET | Navegación fina |
| `/api/students/{persona}/courses/` | GET | Cursos de la persona con progreso; 200 aunque la biblioteca esté cerrada |
| `/api/students/{persona}/courses/{curso_ref}/progress/` | GET, POST | Progreso por sección (upsert monotónico) |
| `/api/aperturas/`, `/api/aperturas/{id}/cerrar/` | POST | El visor del contenido: qué abrió cada persona y cuánto tiempo |
| `/api/intentos/start|answer|finish/` | POST | Evaluaciones con corrección delegada a la biblioteca |
| `/api/resultados/`, `/api/resultados/{id}/` | GET | Notas |
| `/api/cursos/{curso_ref}/consolidado/` | GET | Consolidado docente por estudiante |
| `/api/inscripciones/` | GET, POST, DELETE lógico | Inscripción |
| `/api/auditoria/` | GET | Sólo lectura |
| `/api/courses/…` y demás rutas de administración | cualquier verbo | **409** `administracion_no_permitida` |
| `/api/acceso/configuracion/` | GET | Qué identificador y qué secreto usa cada perfil (para pintar el login). Sin sesión |
| `/api/acceso/instalacion/` | POST | Primer arranque: organización, políticas y primer administrador. Sólo una vez |
| `/api/acceso/dispositivos/` | POST · GET | Registro idempotente de la tableta · listado (con sesión) |
| `/api/acceso/sesiones/` | POST · GET | Iniciar sesión (JWT de 4 h) · listar sesiones |
| `/api/acceso/sesiones/actual/`, `/api/acceso/sesiones/{id}/` | DELETE | Cerrar la propia · revocar ajena |
| `/api/acceso/yo/`, `/api/acceso/yo/credencial/` | GET · PUT | Identidad, permisos efectivos y menú · cambiar la propia clave |
| `/api/acceso/usuarios/…` | GET, POST, PATCH | Usuarios, rol, permisos adicionales, `credencial/restablecer/`, `desbloquear/` |
| `/api/acceso/autorizaciones-temporales/…` | POST, GET, DELETE · `canjear/` | Acceso temporal a examen (tableta autorizada o código de un solo uso) |
| `/api/acceso/roles/`, `permisos/`, `politicas/`, `grupos/…` | GET, POST, PUT, PATCH | Catálogos y configuración del colegio |

El módulo de acceso está especificado en [`spec-driven/01-acceso/`](../spec-driven/01-acceso/01-modelado-datos.md)
(modelo de datos) y [`02-Endpoints.md`](../spec-driven/01-acceso/02-Endpoints.md) (contrato). Vive en `acceso/`
con arquitectura hexagonal: `dominio/` y `aplicacion/` no importan Django; `infraestructura/` e `interfaces/`
son los adaptadores (ORM, Argon2id, AES-GCM, JWT, DRF).

## Instalar el nodo (módulo de acceso)

Tras `migrate`, el catálogo de permisos y los roles `STUDENT`, `TEACHER` y `ADMIN` ya están sembrados.
La organización y el primer administrador se crean una sola vez, desde la API (`POST /api/acceso/instalacion/`)
o con el comando:

```powershell
.venv\Scripts\python manage.py acceso_instalar --codigo IE-SANJOSE --nombre "IE San José" --pais CO --admin-dni 1042888795 --admin-nombres Ana --admin-apellidos Pérez
```

Si no se pasa `--admin-password`, se genera una y se muestra **una sola vez**.

Códigos de degradación: **503** biblioteca ausente (con `sugerencia`), **501**
capacidad no publicada (con `capacidades`), **502** la biblioteca contestó con
error, **404/403** referencia inexistente o desactivada por la escuela.

## Variables de entorno

| Variable | Para qué |
|---|---|
| `AVACOM_CONTENIDO_ENLACE` | Ruta forzada de la nota de enlace (pruebas / host de pruebas) |
| `AVACOM_CONTENIDO_TIEMPO_ESPERA_SEG` | Tiempo de espera hacia la biblioteca (3 s por defecto) |
| `AVACOM_LMS_DB` | Ruta del SQLite (por defecto `backend/db.sqlite3`) |
| `AVACOM_LMS_DEBUG` | `1` por defecto en el prototipo |
| `AVACOM_LMS_CLAVE_DATOS` | Clave AES-256-GCM para los datos personales (32 bytes en base64) |
| `AVACOM_LMS_CLAVE_INDICE` | Clave HMAC-SHA-256 del índice ciego (búsqueda de DNI/código/correo) |
| `AVACOM_LMS_CLAVE_TOKENS` | Clave HS256 de los JWT |
| `AVACOM_LMS_EXIGIR_SESION` | `0` por defecto. Con `1`, expediente y biblioteca exigen sesión (Q-34) |

Si faltan las tres claves, el prototipo las deriva de `SECRET_KEY` con HKDF y `/health/` responde
`"acceso": {"claves_derivadas": true}`. En una instalación distribuida deben venir en `backend.env`.
