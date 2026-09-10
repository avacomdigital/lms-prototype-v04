# Spec · Conexión AVACOM LMS ↔ AVACOM Biblioteca

| Campo | Valor |
|---|---|
| Objetivo (`/goal`) | Mostrar los cursos disponibles en AVACOM Biblioteca dentro de AVACOM LMS (OPS Master y Student), reproducir su contenido completo y registrar el progreso de los estudiantes en el LMS |
| Estado | **Implementado y verificado** el 2026-09-09 |
| Alcance | `backend/` (Django REST Framework, nuevo), `src/Avacom.Lms.Core`, `src/Avacom.Lms.Ui`, `src/Avacom.Lms.Ops`, `src/Avacom.Lms.Student`; y una extensión **aditiva** de la API local de AVACOM Biblioteca (`app-biblioteca/src/Avacom.Contenido/Api`) |
| Documentos de partida | `spec-driven/00..06`, `api_calls.md`, `CONTRATO-LMS.txt`, `format.md` y los dos ejemplos de curso |

Este documento sigue el formato spec-driven del proyecto: **constitución → especificación → clarificación → plan → tareas → verificación**. Describe **cómo se hizo** la conexión, no una propuesta.

---

## 1 · Constitución aplicada

Los dos artículos del nuevo prototipo se respetan al pie de la letra:

| Artículo | Cómo se cumple en esta entrega |
|---|---|
| **13 · El expediente es lo único que el LMS posee** | El backend tiene 8 tablas, todas de expediente: `m05_inscripcion`, `m05_progreso_leccion`, `m05_apertura_material`, `m10_intento`, `m10_intento_pregunta`, `m10_intento_respuesta`, `m05_disponibilidad_observada` y `m19_auditoria`. Toda columna `_ref`/`_codigo` es una referencia emitida por la biblioteca; toda columna `_rotulo` es evidencia histórica que no se refresca ni decide nada |
| **14 · La administración del curso pertenece a la biblioteca** | No existe tabla de curso, sección, lección, ítem, pregunta ni opción (prueba `FronteraTests`). Las rutas antiguas de administración (`/api/courses/`, `/api/lessons/`, `/api/course-packages/`, …) responden **409 `administracion_no_permitida`** nombrando al dueño. Ninguna columna puede contener una clave (prueba de esquema) |

Regla que más fácil se rompe y que **no** se rompió: **no se cachea el catálogo**. El LMS pide la estructura en vivo cada vez; lo único que recuerda del contenido son fechas (`m05_disponibilidad_observada`) para poder decir «no disponible desde…» con la biblioteca cerrada.

---

## 2 · Especificación

### 2.1 · Historias cubiertas

| ID | Historia | Cómo se ve |
|---|---|---|
| US-A | Docente y estudiante entran en **Asignaturas** y ven los cursos que ofrece la biblioteca | `AsignaturasPage` en OPS y en Student: los cursos como **hexágonos** (`ProfessorHexTile`, la misma pieza del menú principal) y debajo la **lista completa** con asignatura, nivel, grado, versión, cantidad de materiales y progreso |
| US-B | Al tocar un curso se ve **todo su contenido**: secciones, materiales, láminas, videos, documentos, interactivos, lecciones y evaluaciones | `CursoBibliotecaPage` (una por app) que aloja el control compartido `CourseContentView`: estructura a la izquierda, visor a la derecha |
| US-C | El backend **registra el progreso** del estudiante viendo el curso | Cada apertura de material crea una fila en `m05_apertura_material`; al cerrarla se anota el tiempo; el progreso por sección se recalcula contra la estructura vigente y se guarda de forma **monotónica** en `m05_progreso_leccion` |
| US-D | El estudiante responde una evaluación y obtiene una nota | Intento → respuestas corregidas **en la biblioteca** (`POST /v1/comprobar`) → nota ponderada en `m10_intento`. Las preguntas abiertas quedan `pendiente_correccion` |
| US-E | El docente ve el consolidado por estudiante | Pestaña «Estudiantes y progreso» del curso en OPS: progreso, materiales abiertos, tiempo, última actividad y notas |
| US-F | Sin biblioteca no hay pantalla en blanco | 503 con motivo y sugerencia en contenido; 200 con expediente y aviso en `students/{persona}/courses/`; las pantallas explican «no se pudo comprobar», nunca «desapareció» |

### 2.2 · Requisitos funcionales verificables

| RF | Requisito | Prueba |
|---|---|---|
| RF-01 | La nota de enlace se lee en **cada** petición, acepta claves PascalCase y minúsculas, y valida `Contrato` | `DescubrimientoTests` |
| RF-02 | Nota ausente, puerto muerto o contrato mayor → **503** con `sugerencia`; `estado()` nunca lanza | `DescubrimientoTests` |
| RF-03 | Los cursos mostrados son **exactamente** los que devuelve `GET /v1/cursos` (con la política de la escuela ya aplicada) | `CursosTests`, verificación manual contra la biblioteca real |
| RF-04 | La estructura se resuelve en vivo con `GET /v1/curso/{ref}` y se anota con el expediente de la persona (`abierto`, `completado`, `progreso`, `estado_intento`) | `CursosTests.test_el_curso_trae_secciones_e_items_anotados` |
| RF-05 | Toda ruta opcional exige su capacidad y responde **501** explicativo con la lista publicada; nunca se simula | `SinCapacidadesTests`, `ComponenteAntiguoTests`, `SinEvaluacionTests` |
| RF-06 | Los bytes de un material pasan a través del backend conservando `Content-Type`, `Content-Length`, `Content-Range` y `Accept-Ranges` | `MedioTests` |
| RF-07 | Ningún payload hacia el estudiante contiene `clave`, `clave_respuesta`, `respuesta`, `correcta`, `es_correcta` ni `solucion` | `test_ninguna_respuesta_del_estudiante_trae_una_clave`, `test_sin_claves_limpia_recursivamente` |
| RF-08 | Abrir un material inscribe a la persona si hacía falta y recalcula la sección; el progreso **nunca disminuye**; 100 % sella con fecha | `AperturasYProgresoTests` |
| RF-09 | Un intento se reanuda si está abierto; responder es idempotente por `(intento, pregunta)`; finalizar es idempotente y produce una sola nota | `IntentosTests.test_flujo_completo_con_correccion_delegada` |
| RF-10 | Sin capacidad `comprobar` no se produce ninguna nota: el intento queda `pendiente_correccion` | `SinComprobarTests` |
| RF-11 | Un curso conocido que deja de ofrecerse se marca con fecha y se audita; si vuelve, se audita la reaparición | `DegradacionTests.test_curso_retirado_se_explica_con_fecha` |
| RF-12 | La auditoría es de sólo escritura | `FronteraTests.test_la_auditoria_es_de_solo_escritura` |

---

## 3 · Clarificación · decisiones tomadas

| ID | Pregunta | Decisión |
|---|---|---|
| C-1 | El contrato 1 de la biblioteca **no expone medios ni preguntas** (`api_calls.md` §11). ¿Cómo se reproduce «todo el contenido» dentro del LMS? | Se **amplió la biblioteca por capacidades**, sin subir el contrato: `medio`, `leccion`, `evaluacion`, `comprobar` y `voz`. Añadir rutas y campos no rompe a quien ya lee; `/v1/salud` las declara y el LMS sólo las usa si están. Con una biblioteca antigua el LMS degrada al catálogo y a «Mostrar en el aula» |
| C-2 | ¿La biblioteca revela alguna vez la clave? | No. `POST /v1/comprobar` compara donde vive la clave y devuelve `{acierta, retroalimentacion}`; la retroalimentación sólo acompaña al acierto, igual que en el visor de la pantalla. `GET /v1/evaluacion` no trae clave ni retroalimentación. Hay pruebas en ambos lados |
| C-3 | ¿Qué es «progreso»? | Todo lo que hace el estudiante: aperturas del visor (qué, cuándo, cuánto tiempo), avance por sección, intentos, respuestas, veredictos y notas |
| C-4 | ¿Cómo se identifica al estudiante sin autenticación (Q-04)? | `persona_id` = slug estable del nombre con el que entra al aula (`Identidad.SlugDe`), `persona_rotulo` = el nombre. El docente no tiene expediente: en OPS no se registra progreso y las evaluaciones se abren como vista previa |
| C-5 | ¿Cómo se calcula el progreso de una sección? | `items completados ÷ items visibles`. Un material se completa al abrirse; una evaluación o actividad, al finalizar un intento. `banco` y `scorm` no se dan en el aula y no cuentan |
| C-6 | ¿Cómo se calcula la nota (Q-22, alternativa A)? | Ponderada por `peso` sobre las preguntas con veredicto. Si queda alguna sin veredicto (abierta o sin capacidad) el intento es `pendiente_correccion` y conserva el puntaje parcial |
| C-7 | ¿Qué pasa con «Crear curso» en OPS? | Deja de ser el destino de «Asignaturas». La página queda en el proyecto como resto del demo, sin ruta desde el menú. El panel dice dónde se administran los cursos |
| C-8 | ¿Qué hacen las tabletas con un PDF? | En Windows el visor lo muestra embebido; en Android se abre con el visor del sistema desde la misma URL del backend |
| C-9 | ¿Hay que reiniciar la biblioteca? | Sí, una vez, para que la instancia en ejecución publique las capacidades nuevas. Se detuvo el proceso, se compiló la app y se relanzó el ejecutable; la API se enciende sola al abrir la pestaña «Contenido AVACOM», que es la primera |
| C-10 | ¿Cómo se califica una pregunta corregible que el estudiante dejó sin responder? | Como error, siempre que la biblioteca publicara `comprobar` al finalizar (si no había corrección posible queda pendiente). Las abiertas y las respondidas sin veredicto quedan `pendiente_correccion`; el intento guarda `pendientes` |
| C-11 | El servidor de desarrollo de Django no lee cuerpos `Transfer-Encoding: chunked` (los envía `PostAsJsonAsync`) | La fachada serializa el JSON a texto y envía `Content-Length`. Sin esto las aperturas y los intentos llegaban vacíos (400) |
| C-12 | ¿Dónde queda un fallo no controlado de las apps en el aula? | En `%LOCALAPPDATA%\AVACOM\lmsallos-{ops|student}.log` (`RegistroDeFallos`, enganchado a AppDomain, TaskScheduler y WinUI) |

---

## 4 · Plan técnico · lo que se construyó

### 4.1 · Topología

```
OPS Master (MAUI, Windows) ─┐  Sesion.Biblioteca → BibliotecaDeContenido (fachada)
Student (MAUI, Win/Android) ─┼── HTTP LAN :8000 ──► backend Django/DRF
                             ┘                        ├─ biblioteca.cliente   ÚNICO cliente → 127.0.0.1:{Puerto} · X-Avacom-Ficha · 3 s
                                                      └─ expediente.*         8 tablas SQLite · auditoría append-only
                                                                 │ loopback
                                                                 ▼
                                                       AVACOM Biblioteca · ApiLocal (+ capacidades)
```

### 4.2 · Backend (`backend/`)

| Módulo | Papel |
|---|---|
| `biblioteca/cliente.py` | Descubrimiento (`ruta_enlace`, `leer_enlace`), vivacidad (`proceso_vivo` con `OpenProcess`, nunca `os.kill` en Windows), transporte único (`_pedir`, sin proxy, 3 s), contrato (`salud`, `cursos`, `curso`, `catalogo`, `taxonomia`, `elemento`, `mostrar`), capacidades (`leccion`, `evaluacion`, `comprobar`, `abrir_medio`, `abrir_voz`) y `estado()` que nunca lanza |
| `biblioteca/views.py` | Rutas hacia arriba con la traducción 503/501/502/404/403; `MedioView` reenvía el flujo con `Range` |
| `expediente/models.py` | Las 8 tablas del expediente con sus invariantes (`UNIQUE`, ausencia con fecha, un solo intento abierto, `completada ⇒ 100 % y fecha`) |
| `expediente/servicios.py` | Inscripción idempotente, apertura + recálculo, upsert monotónico, intentos con corrección delegada, revisión de disponibilidad (sólo con oferta válida) y consolidado docente |
| `expediente/views.py` | Expediente, consolidado, auditoría de sólo lectura y rechazos 409 |
| `tools/host_biblioteca_pruebas.py` | Host que imita el contrato completo; las 31 pruebas del backend corren sin la biblioteca real |

### 4.3 · Biblioteca (extensión aditiva, contrato sigue en 1)

| Pieza | Cambio |
|---|---|
| `Api/IFuenteDeContenido.cs` (nuevo) | Frontera entre la API y el contenido descifrado: abrir medio, archivo interno de un interactivo, preguntas sin clave, corregibles, acertar, pasos de lección, voz |
| `Api/FuenteDeContenido.cs` (nuevo) | Implementación real sobre `ResolutorDeMedios` (política + cifrado) y `GestorDePaquetes`, con cerrojo y caché acotada de interactivos desplegados en memoria |
| `Api/ApiLocal.cs` | Constructor con `fuente` opcional; capacidades declaradas sólo si hay fuente; rutas `GET /v1/medio/{ref}[/ruta]` (bytes con `Range`, `HEAD`), `GET /v1/leccion/{ref}`, `GET /v1/evaluacion/{ref}`, `POST /v1/comprobar`, `GET /v1/voz/{ref}[/pregunta]`; toda ruta pasa por «existe + política» |
| `Paquetes/LecturaDeManifiesto.cs` | `Corregibles(elementoRef)`: referencias con clave, nunca la clave |
| `App/Paquetes/GestorDePaquetes.cs` | Cerrojo: la API atiende en hilos del servidor |
| `App/Paquetes/PuenteConElLms.cs` | Enchufa `FuenteDeContenido(resolutor, gestor.Abrir)` al encender la API |
| `tests/ApiLocalCapacidadesTests.cs` (nuevo) | 20 pruebas: capacidades, rangos, `HEAD`, interactivo, política, lección, evaluación sin clave, comprobar, voz, ficha |

### 4.4 · Clientes MAUI

| Pieza | Papel |
|---|---|
| `Core/Models/BibliotecaModels.cs` | Contratos del backend (`CursoResumen`, `CursoDetalle`, `SeccionCurso`, `ItemCurso`, `IntentoIniciado`, `ConsolidadoCurso`, …) |
| `Core/Services/BibliotecaDeContenido.cs` | Fachada única de los clientes; habla con el backend, nunca con la biblioteca; 503 → lista vacía / `null` con `UltimoMotivo`; huella local con `OlvidarHuella()` |
| `Core/Models/Identidad.cs` | `persona_id` estable a partir del nombre |
| `Ui/Controls/CourseContentView` | El curso completo: secciones e items a la izquierda; visor por tipo a la derecha (`Image` para láminas, `WebView` con reproductor HTML5 para video/audio, `WebView` para PDF e interactivos con recursos relativos, lista de pasos para lecciones, flujo de preguntas con corrección delegada y voz para evaluaciones). Registra aperturas y cierres en modo estudiante; en modo docente ofrece «Mostrar en el aula» |
| `Ops/Pages/AsignaturasPage` | Cursos como hexágonos + lista completa + estado de la biblioteca |
| `Ops/Pages/CursoBibliotecaPage` | Contenido del curso y pestaña «Estudiantes y progreso» (consolidado) |
| `Student/Pages/AsignaturasPage` | Cursos con progreso; expediente legible con la biblioteca cerrada; «Ver curso demo» sólo cuando no hay backend |
| `Student/Pages/CursoBibliotecaPage` | Contenido del curso en modo estudiante, con chip de progreso en vivo |

### 4.5 · Secuencia de integración (la de `api_calls.md`, ejecutada por el backend)

```
leer enlace.json ── no existe ──▶ 503 «sin contenido» · el expediente sigue con 200
      │
      ▼
Contrato == 1 ── no ──▶ 503 «hay que actualizar el LMS»
      │
      ▼
GET /v1/salud ──▶ huella_catalogo + capacidades (se exige "curso" antes de /v1/cursos)
      │
      ▼
GET /v1/cursos ──▶ /api/biblioteca/cursos/ ──▶ hexágonos y lista de Asignaturas
      │
      ▼
GET /v1/curso/{ref} ──▶ /api/biblioteca/cursos/{ref}/?persona= ──▶ secciones e items anotados
      │
      ▼
GET /v1/medio|leccion|evaluacion · POST /v1/comprobar ──▶ visor del LMS ──▶ aperturas, progreso, intentos, notas
```

---

## 5 · Tareas ejecutadas

| ID | Tarea | Tipo | Verificación |
|---|---|---|---|
| T1 | Proyecto Django + DRF, ajustes, `AVACOM_CONTENIDO_ENLACE` | conserva | `manage.py check` limpio |
| T2 | Cliente único `biblioteca/cliente.py` | conserva línea base | `DescubrimientoTests` |
| T3 | Modelo del expediente (8 tablas) y migración `0001_initial` | corrige | `makemigrations --check` limpio; `FronteraTests` |
| T4 | Servicios: apertura, progreso monotónico, intentos, disponibilidad, consolidado | corrige | `AperturasYProgresoTests`, `IntentosTests`, `DegradacionTests` |
| T5 | Vistas hacia arriba + degradación + rechazos 409 | corrige | `CursosTests`, `MedioTests`, `FronteraTests` |
| T6 | Host de pruebas del contrato | prueba | 32 pruebas verdes sin biblioteca |
| T7 | Biblioteca: `IFuenteDeContenido`, `FuenteDeContenido`, `ApiLocal` con capacidades, `Corregibles`, cerrojo, puente | traslada | 71 pruebas verdes (`dotnet test tests/Avacom.Contenido.Tests`) |
| T8 | Reinicio de la biblioteca en ejecución con la API extendida | corrige | `/v1/salud` declara `curso, medio, leccion, evaluacion, comprobar, voz` |
| T9 | Core: modelos, fachada, identidad | conserva | Compila; usado por ambas apps |
| T10 | Ui: `CourseContentView` | corrige | Compila; reproduce lámina, video, PDF, interactivo, lección y evaluación |
| T11 | OPS: `AsignaturasPage`, `CursoBibliotecaPage`, rutas, menú | corrige | Compila para Windows |
| T12 | Student: `AsignaturasPage`, `CursoBibliotecaPage`, rutas, menú | corrige | Compila para Windows |
| T13 | Documentación: este spec, `backend/README.md`, README raíz, `docs/architecture.md` | conserva | — |

---

## 6 · Verificación

### 6.1 · Automática

| Suite | Resultado |
|---|---|
| Backend (`backend/.venv/Scripts/python manage.py test`) | 32 pruebas en verde |
| Biblioteca (`dotnet test tests/Avacom.Contenido.Tests`) | 71 pruebas en verde (51 previas + 20 nuevas) |
| Compilación OPS y Student (`net10.0-windows10.0.19041.0`) | En verde |

### 6.2 · Visual, con las apps compiladas y la biblioteca real

Se recorrieron ambas apps con el backend en `127.0.0.1:8000` y la biblioteca extendida:

| Pantalla | Resultado observado |
|---|---|
| Student · Conexión | «Conectado al aula correctamente» (`/health/`) |
| Student · Asignaturas | Hexágono «Matemáticas · Grado 8» + lista con progreso; chip «1 curso(s) disponibles» |
| Student · Curso | 3 secciones (`estandar`, `tema`, `tema`) con sus 5 materiales; visor a la derecha |
| Student · PDF / video / interactivo | El PDF se pinta con el visor embebido, el video se reproduce en flujo descifrado, el «Explorador de rectas» funciona con sus controles |
| Student · Progreso | Al abrir el PDF: sección 50 %, curso 17 %, item «Completado» (`POST /api/aperturas/` 201, `cerrar` 200) |
| Student · Evaluación | 8 preguntas reales; «3» → «✓ Correcto» corregido en la biblioteca; Finalizar → nota registrada, sección 50 %, curso 33 % |
| OPS · Asignaturas | Chip «Biblioteca conectada · 1 curso(s) · curso, medio, leccion, evaluacion, comprobar, voz», hexágono y lista con `curso_ref` |
| OPS · Curso (vista docente) | Mismo contenido, botón «Mostrar en el aula», sin registro de progreso |
| OPS · Estudiantes y progreso | Consolidado: 1 estudiante, 33 % promedio, 1 material abierto, 1 evaluación cerrada, fila de Ethan Martínez con nota |

Fallos encontrados y corregidos durante esta verificación: `Resources[...]` de página en vez de `Application.Current.Resources` (KeyNotFound → cierre de la app), POST troceado sin `Content-Length` (C-11) y una carrera de navegación del `WebView` al reemplazar el origen (PDF en blanco).

### 6.3 · Contra la biblioteca real

Con la biblioteca encendida en el equipo (`enlace.json` en `%ProgramData%\AVACOM\contenido`):

- `GET /api/biblioteca/estado/` → `disponible: true`, contrato 1, huella `h…`, capacidades declaradas.
- `GET /api/biblioteca/cursos/` → `co-secundaria-8-matematicas · Matemáticas · Grado 8` (el único paquete instalado hoy en esa instancia).
- `GET /api/biblioteca/cursos/co-secundaria-8-matematicas/` → 3 secciones (`estandar` + 2 `tema`) con evaluación, lección, interactivo, documento y video.
- `GET /api/biblioteca/medio/co-sec-mat-doc-funcion/` con `Range` → 206 con `Content-Range`.

> **Nota sobre «Exploración del medio».** El paquete `avacom-co-preescolar-transicion-exploracion-v1` existe en `trabajo/pub/`, pero **no está instalado** en la instancia de la biblioteca que corre en este equipo (`paquetes: 1`). El LMS lo mostrará en cuanto el administrador lo instale desde la biblioteca (Administración → Instalar paquetes): no hay nada que cambiar en el LMS, que es exactamente el punto de la frontera.

### 6.4 · Cómo probar de punta a punta

1. Biblioteca abierta en «Contenido AVACOM» con licencia.
2. Backend: `cd backend; .venv\Scripts\python manage.py runserver 0.0.0.0:8000`.
3. OPS: `dotnet run --project src/Avacom.Lms.Ops -f net10.0-windows10.0.19041.0` → Iniciar → hexágono **Asignaturas** → tocar un curso → abrir un material → «Mostrar en el aula» proyecta en la biblioteca; pestaña **Estudiantes y progreso** muestra el consolidado.
4. Student: `dotnet run --project src/Avacom.Lms.Student -f net10.0-windows10.0.19041.0` → nombre + `http://127.0.0.1:8000` → **Asignaturas** → curso → abrir láminas/video/PDF/interactivo (se registran aperturas) → evaluación → Comprobar → Finalizar (se registra la nota).
5. Cerrar la biblioteca: OPS y Student siguen mostrando el expediente con aviso; nada queda en blanco.

---

## 7 · Deudas y límites conocidos

- **Sin autenticación** (Q-04): la identidad es el nombre. La frontera de escritura real es la del backend (409 en administración).
- **Vista previa docente de evaluaciones** crea intentos a nombre de `docente-vista-previa`; no aparecen en el consolidado porque ese id no se inscribe como estudiante… salvo que se finalicen. Es un atajo de prototipo.
- **Progreso dentro de un video o PDF** no se mide: una apertura cuenta como material visto. El campo `progreso_pct` de la apertura queda listo para cuando el visor lo reporte.
- **PDF en Android** se abre fuera del LMS (visor del sistema).
- **Preguntas abiertas** quedan `pendiente_correccion`; no hay pantalla de calificación con rúbrica todavía.
- **Concurrencia en la biblioteca**: la API y la interfaz comparten la conexión del manifiesto; se serializó lo que la API toca, pero el visor de la propia biblioteca sigue sin cerrojo (riesgo preexistente y remoto).
- La `generacion` monótona propuesta en `06-contrato-biblioteca.md` no existe: se usa `huella_catalogo` (decisión de la biblioteca, ver `CONTRATO-LMS.txt`).
