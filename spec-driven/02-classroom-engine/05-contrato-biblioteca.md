# 05 · Classroom Engine · Contrato con la API de Contenido v2 de AVACOM Biblioteca

| Campo | Valor |
|---|---|
| Módulo | MOD-007 · Classroom Engine · fuente de cursos `biblioteca` |
| Estado | **Implementado contra el documento «Mapeo de campos · API de Contenido v2»** (equipo de Biblioteca, comprobado por ellos contra la API real el 17-09-2026). La API **no está instalada en este equipo**: todo se verificó con un host de pruebas que la imita (§7). Los puntos que el mapeo no fija están en §8 como supuestos, y hay que cerrarlos contra `contracts/openapi.v2.json` |
| Sustituye a | La propuesta de [06 · Contrato exigido a la biblioteca](../06-contrato-biblioteca.md) en lo que toca al aula (`/v1/cursos`, `/v1/curso/{ref}`, `evaluacion`, `comprobar`). El contrato 1 sigue vigente para `/api/biblioteca/*` y el flujo de intentos del expediente |
| Cierra | Q-44 (cómo publica la biblioteca el curso 1.0), Q-45 (cómo se piden los medios), parte de Q-48 (quién califica las preguntas del manifiesto) de [01 · Modelo de datos](01-modelo-de-datos.md) §12 |
| Documentos hermanos | [01 · Modelo de datos y API](01-modelo-de-datos.md) · [03 · Journey](03-journey-clase-de-hoy.md) · [04 · Frontend](04-frontend-classroom-engine.md) · [00 · Línea base del contrato 1](../00-linea-base-conexion-biblioteca.md) |

---

## 0 · Resumen

1. **La API v2 entrega el curso que el LMS ya sabía leer, recortado.** Es el esquema 1.0 (`lessons → objects → questions`, `media`) **sin ninguna clave de corrección** y sin `teacherNotes` para el alumno. El normalizador de [01](01-modelo-de-datos.md) §2 no cambió: la vista de aula es la misma con `fuente=biblioteca` que con `fuente=ejemplo`.
2. **Un cliente nuevo y único**, `backend/biblioteca/contenido_v2.py`: `link.json` releído en cada petición, `Authorization: Bearer <token>`, un 401 reintenta **una** vez tras releer, la ausencia de `link.json` es «sin contenido» (503 con sugerencia), y `POST /v2/evaluate` viaja **siempre con `version`**.
3. **La fuente `biblioteca` del aula habla v2** (`FuenteBiblioteca`): pide el curso con `mode=class` y `profile=teacher|student` según el rol, baja los medios en paso a través y califica por `/v2/evaluate` y `/v2/evaluate/batch`.
4. **El aula ahora califica sin guardar**: `POST /api/aula/cursos/{curso_ref}/evaluar/` valida la forma de `response` contra la pregunta tal como la vio el alumno (ids, nunca posiciones), reenvía con la versión y devuelve el veredicto traducido (`puntaje` decimal o nulo, `correcta` booleana o nula, `requiere_correccion_manual`). Persistir el intento sigue siendo de MOD-010 (Q-48, Q-49).
5. **Nada se guarda del curso** (artículo 14): ni catálogo, ni títulos como clave, ni posiciones de opción, ni `token`, ni URL de medios. Lo único que el expediente conserva del contenido son `courseId` + `version` y los `lessonId`/`objectId`/`questionId`/`optionId`, tal como pide el mapeo §2.
6. **OPS elige la fuente y Student no.** OPS pide `biblioteca` por defecto y, si no está encendida, ofrece «Usar el curso de ejemplo» con un toque; la tableta no manda `fuente`: sigue la clase del profesor y el backend resuelve.

---

## 1 · Transporte

```
Tableta / OPS ──HTTP LAN :8000──► backend del LMS ──loopback 127.0.0.1:{apiPort}──► API de Contenido v2
                                   (contenido_v2.py)   Authorization: Bearer {token}
```

| Regla del mapeo | Cómo se cumple | Dónde |
|---|---|---|
| `link.json` se relee en cada petición | `leer_enlace()` abre el archivo en cada `_pedir()`; nada se guarda en memoria | `contenido_v2.leer_enlace` |
| `apiPort` y `token` cambian en cada arranque: **no guardar** | No hay variable de módulo con el puerto ni el token; sólo la ruta del archivo | — |
| Un `401` reintenta **una** vez tras releer `link.json` | `_pedir(reintentar=True)` → al primer 401 vuelve a leer y repite con `reintentar=False`; el segundo 401 sube como `BibliotecaError(401, codigo="unauthorized")` → **502 `fuente_error`** | `contenido_v2._pedir` |
| La ausencia de `link.json` produce «sin contenido», no un error | `BibliotecaNoDisponible` → `FuenteNoDisponible` → **503** `{disponible: false, detail: "…sin contenido.", sugerencia}` | `fuente_biblioteca._traducir` |
| Sólo loopback, sin proxy, tiempo de espera corto | `ProxyHandler({})`, `127.0.0.1`, `AVACOM_CONTENIDO_TIEMPO_ESPERA_SEG` (3 s) | como en el contrato 1 |
| Ruta de `link.json` | `%ProgramData%\AVACOM\contenido\link.json`; se fuerza con `AVACOM_CONTENIDO_ENLACE_V2` (setting o variable de entorno) para el host de pruebas | `settings.py` |

Claves de `link.json` aceptadas: `apiPort` (también `port`), `token`, `pid`/`processId` (opcional), `apiVersion` (opcional). Se admiten en camelCase, minúsculas o PascalCase.

---

## 2 · Rutas que consume el aula

| Ruta de la API v2 | Quién la llama | Para qué | Caso de uso del aula |
|---|---|---|---|
| `GET /v2/health` | `contenido_v2.estado()` | ¿Hay contenido? `installedCourses` es la **señal de cambio** (huella `v2-…`) | `EstadoFuente` → `GET /api/aula/fuente/` |
| `GET /v2/courses` | `FuenteBiblioteca.cursos()` | La lista de cursos instalados. Si trae fichas (sin `lessons`), se baja cada curso completo (la lista de una escuela es corta) | `ConsultarCursos` → `GET /api/aula/cursos/` |
| `GET /v2/courses/{courseId}?mode=class&profile=teacher\|student` | `FuenteBiblioteca.curso()` | El curso recortado. `mode=class` porque el aula es una clase; `profile` según el rol (el docente ve `teacherNotes`) | `ConsultarCurso`, `ConsultarLeccion`, `ConsultarObjeto`, `IniciarSesion`, `DeclararFoco`, `Distribuir` |
| `GET /v2/courses/{courseId}?version=1.1.0` | ídem con `version` | Una **versión archivada**, para reconstruir lo que vio el alumno en un intento viejo | `?version=` en `GET /api/aula/cursos/{ref}/…` |
| `GET /v2/courses/{courseId}/media/{mediaId}[/ruta]` | `FuenteBiblioteca.medio()` | Bytes del medio, con `Range` y `HEAD`, en paso a través (el LMS no abre archivos ni guarda URL) | `AbrirMedio` → `GET /api/aula/cursos/{ref}/medios/{media_ref}/[ruta]` |
| `POST /v2/evaluate` | `FuenteBiblioteca.evaluar()` | Un veredicto. **Siempre con `version`** | `EvaluarRespuesta` → `POST /api/aula/cursos/{ref}/evaluar/` |
| `POST /v2/evaluate/batch` | `FuenteBiblioteca.evaluar_lote()` | Hasta 200 respuestas en `items`; más de 200 el aula responde 400 | ídem con `items` |
| `GET /v2/courses/{courseId}/questions/{questionId}/grading-guide` | `contenido_v2.guia_calificacion()` | Rúbrica y respuesta modelo de una abierta, **sólo para calificar a mano**. Está en el cliente y **no se expone por `/api/aula/`**: es de MOD-011 (revisión docente), no del aula | — |

Lo que el aula **no** pide: nada que cree o modifique contenido (no existe en el contrato), y nada del catálogo plano del contrato 1 (`/v1/catalogo`, `/v1/taxonomia`), que sigue siendo del modo libre «Asignaturas».

### 2.1 · Efecto de `mode=class`

Cada curso, lección y objeto declara en qué modos puede usarse; el modo se manda como parámetro. En `example.json` el examen declara `modes: ["exam"]`, así que con `mode=class` **no viaja al aula**: la lección de evaluación llega sin objetos. El aula ya lo trataba como `fuera_de_alcance` (MOD-010), de modo que no cambia nada de lo que se proyecta; sólo desaparece la tarjeta atenuada «Examen» en P2. Si la API real **valida** el modo en vez de filtrar (supuesto A-6), la tarjeta vuelve sola.

---

## 3 · Identificadores · qué guarda el expediente

La tabla del mapeo §2, con su estado en el LMS:

| Identificador | Estable | ¿Se guarda? | Dónde, hoy |
|---|---|---|---|
| `courseId` | sí | **sí** | `m07_sesion.curso_ref`, `m07_foco.curso_ref`, `m07_distribucion.curso_ref`; `m10_intento.curso_ref` |
| `version` | — | **sí, junto al `courseId`** | `m07_sesion.curso_version`, `m07_foco.curso_version` (la de la vista con la que se inició o proyectó). El veredicto de `/evaluar/` devuelve `version` para que MOD-010 la escriba en el intento |
| `lessonId` | sí | sí | `leccion_ref` en sesión, foco y distribución |
| `objectId` | sí | sí | `objeto_ref` en foco y distribución; `objectId` en cada evaluación |
| `questionId` | sí | sí | `unidad_ref` del foco cuando se proyecta una pregunta; `questionId` en cada evaluación |
| `optionId` | sí | sí (en la respuesta) | `response.selectedOptionIds` valida que sean `id` de la pregunta; **una posición es 400** |
| `mediaId` | sí | sólo si hace falta | `media_ref` del foco cuando se proyecta un medio suelto |
| `topicRef` | sí | recomendado | Viaja en la vista (`tema_ref`); no se guarda todavía (informe por tema es de MOD-012) |
| `translationGroupId` | sí | opcional | Viaja en la vista (`grupo_traduccion`); no se guarda |
| `title`, `subtitle` | **no** | sólo como rótulo histórico | `curso_rotulo`, `leccion_rotulo`, `rotulo` (artículo 13.3). **Nunca son clave** |
| `sessionId` de medios | efímero | **no** | El LMS reenvía bytes; no ve ni guarda sesiones de medios |
| `apiPort`, `token` | efímeros | **no** | `link.json` releído en cada llamada |

---

## 4 · Preguntas · lo que llega y lo que se envía

Las seis clases de pregunta ya estaban en el normalizador ([01](01-modelo-de-datos.md) §2.5). Lo que fija el mapeo y cómo lo aplica el aula:

| Tipo | Llega **sin** | Vista de aula | `response` que exige `/v2/evaluate` | Validación previa del aula (`dominio/respuestas.py`) |
|---|---|---|---|---|
| `multiple_choice` | marca de correcta; opciones **barajadas** | `opciones[{opcion_ref, texto}]`, `permite_varias` | `{"selectedOptionIds": ["a"]}` | lista no vacía de `id` existentes; una sola si `permite_varias` es falso; se eliminan repetidos |
| `true_false` | `answer` | dos opciones fijas `true`/`false` | `{"value": true}` | booleano (o `"true"`/`"false"`) |
| `fill_blanks` | valor esperado de cada hueco | `plantilla` con `{{id}}`, `espacios[{espacio_ref, modo_entrada, opciones}]` | `{"blanks": {"b1": "2", "b2": "5"}}` | cada clave es un hueco de la plantilla; los valores viajan como texto |
| `matching` | `pairs`, `wrongPairs`; `right` trae **distractores** | `izquierda[]`, `derecha[]` (más larga) | `{"pairs": [{"leftId","rightId"}]}` | cada `leftId` está en `izquierda` y cada `rightId` en `derecha` |
| `ordering` | `correctOrder`; `items` **desordenados** | `elementos[]` | `{"order": ["o14","o13","o12"]}` | exactamente los elementos de la pregunta, una vez cada uno |
| `open` | `modelAnswer`, `rubric`, `incorrectExamples` | `formato_respuesta`, `longitud_maxima` | `{"text"}` **o** `{"drawingRef"}` **o** `{"audioRef"}` | exactamente uno de los tres; `text` respeta `longitud_maxima` |
| *desconocido* | — | `componente: no_soportado`, se **muestra** | tal cual | se reenvía sin tocar: conjunto abierto (§9 del mapeo) |

### 4.1 · El veredicto

`POST /api/aula/cursos/{curso_ref}/evaluar/?fuente=biblioteca`

```json
→ {"objeto_ref": "l1-activity", "pregunta_ref": "l1-act-q1", "respuesta": {"selectedOptionIds": ["a"]}}
← {"fuente": "biblioteca", "curso_ref": "avacom.co.…", "version": "1.0.0", "objeto_ref": "l1-activity",
   "pregunta_ref": "l1-act-q1", "puntaje": 1.0, "puntaje_maximo": 1.0, "correcta": true,
   "requiere_correccion_manual": false, "pendiente": false,
   "retroalimentacion": ["Correcto: el aire es una mezcla de gases."]}
```

| Campo del contrato | Campo del aula | Regla |
|---|---|---|
| `score` (número **o nulo**) | `puntaje` | `float` o `null`. Con `requiresManualGrading` es **siempre** `null` aunque llegara un número: no se inventa nota |
| `maxScore` (puede no ser entero) | `puntaje_maximo` | `float` |
| `correct` (booleano **o nulo**) | `correcta` | `null` en abiertas y en crédito parcial (ni bien ni mal) |
| `requiresManualGrading` | `requiere_correccion_manual` | `true` → el intento queda **pendiente** |
| — | `pendiente` | `requiere_correccion_manual` o `puntaje` nulo: lo que MOD-010 debe dejar en `pendiente_correccion` |
| `feedback` (lista, puede venir vacía) | `retroalimentacion` | lista de texto; nunca contiene la clave |

`version`: si el cuerpo no la trae, se usa la del curso instalado; en ambos casos viaja a `/v2/evaluate`. Con `{"version": "…", "items": [{objeto_ref, pregunta_ref, respuesta}…]}` se usa `/v2/evaluate/batch` y la respuesta es `{veredictos[], pendientes}`.

La fuente `ejemplo` responde **501 `capacidad_ausente`**: el manifiesto de ejemplo trae las claves, pero la regla es que la clave se compara sólo donde vive; el aula no simula veredictos. La validación de forma (§4) sí se ejecuta antes, así que una respuesta mal formada es 400 con cualquier fuente.

---

## 5 · Enumeraciones y conjuntos abiertos

Valores del contrato (mapeo §3) frente a los catálogos del aula (`dominio/catalogos.py`):

| Conjunto | Contrato v2 | Aula | Si llega otro valor |
|---|---|---|---|
| Modos | `simple · class · exam · review · free_learning` | `MODOS` (iguales) | se conserva en `modos[]` |
| Tipos de objeto | `lecture · explanation · simulation_lab · activity · exam` | `TIPOS_OBJETO` | `componente: no_soportado`, con `crudo` sin claves: **se muestra** |
| Tipos de pregunta | `multiple_choice · true_false · fill_blanks · matching · ordering · open` | `TIPOS_PREGUNTA` | `componente: no_soportado`; la respuesta se reenvía tal cual |
| Tipos de medio | `image · video · audio · pdf · simulation` | `CLASES_MEDIO` | `componente: no_soportado` |
| Bloques | `heading · text · list · formula · image · video · audio · pdf` | `TIPOS_BLOQUE` **sin `formula`** | `formula` llega como `crudo` (aviso en el cliente). Añadirlo es una fila en `TIPOS_BLOQUE` y un control MAUI |
| Nivel cognitivo | `remember … create` | `nivel_cognitivo`, informativo | se conserva |
| Ajustes de actividad | `feedback: immediate · on_submit · none` | `ajustes.retroalimentacion` | se conserva |
| Ajustes de examen | `selection.strategy`, `timeLimit.policy`, `showResults` | `ajustes` del objeto `exam` | se conserva (MOD-010) |
| Simuladores | `provider`, `technology`, `orientation`, `shims`, `supportsTargets` | `simulacion{proveedor, tecnologia, orientacion, ajustes, destinos}` | se conserva |
| Códigos de error | `unauthorized · not_found · course_not_found · lesson_not_found · disabled_by_policy · index_rebuilding · invalid_parameter · invalid_response` | §6 | `502 fuente_error` con `codigo_biblioteca` |

Regla del contrato que el LMS ya cumplía y que se comprobó de nuevo: **añadir un campo no rompe a nadie**. El normalizador toma los campos por nombre e ignora el resto; ningún deserializador estricto falla ante una propiedad desconocida. Los tipos del LMS no se generaron desde `course.schema.json`: los opcionales son anulables (`None`), no valores por defecto.

---

## 6 · Errores · del contrato al aula

| API v2 | Estado | Código del aula | HTTP del aula | Qué ve el cliente |
|---|---|---|---|---|
| sin `link.json`, puerto muerto, sin respuesta a tiempo | — | `fuente_no_disponible` | **503** `{disponible: false, detail, sugerencia}` | «Biblioteca apagada · tocar para usar el ejemplo» |
| `index_rebuilding` | 503 | `fuente_no_disponible` + `codigo_biblioteca` | 503 con `sugerencia: "…vuelve a intentarlo en unos segundos"` | igual, con «Reintentar» |
| `course_not_found` | 404 | `curso_no_encontrado` | 404 | sin inventar título |
| `not_found`, `lesson_not_found` | 404 | `referencia_no_encontrada` (medio, pregunta) · `curso_no_encontrado` (curso) | 404 | |
| `disabled_by_policy` | 403 | `desactivado_por_politica` | **404** | lo que la política desactivó **no se muestra ni se guarda**; en la lista se omite |
| `invalid_parameter` | 400 | `datos_invalidos` | 400 | |
| `unauthorized` tras el reintento | 401 | `fuente_error` + `codigo_biblioteca: unauthorized` | **502** | |
| `invalid_response` y cualquier otro | * | `fuente_error` + `estado_biblioteca` | 502 | |

Todos llevan `codigo_biblioteca` cuando la API mandó código, para que el soporte pueda cruzar con los registros de la biblioteca.

---

## 7 · Cómo se probó sin la biblioteca

`backend/tools/host_contenido_v2_pruebas.py` imita la API v2 en loopback a partir del **manifiesto completo** (`example.json`, que sí trae las claves): recorta lo que el contrato recorta (§1 del mapeo), quita `teacherNotes` con `profile=student`, filtra por `mode`, **rota las opciones** una posición en cada respuesta (una prueba que guardara posiciones fallaría), sirve versiones archivadas con `?version=`, califica con crédito parcial decimal y deja las abiertas con `score: null` y `requiresManualGrading: true`. Escribe `link.json` con `apiPort`, `token` y `pid`, y puede forzar 401 seguidos (`rechazar_proximas`), 503 `index_rebuilding` (`reconstruyendo`) y 403 `disabled_by_policy` (`desactivados`).

A mano, con el backend en marcha:

```
cd backend
.venv\Scripts\python -m tools.host_contenido_v2_pruebas %TEMP%\link-pruebas.json
set AVACOM_CONTENIDO_ENLACE_V2=%TEMP%\link-pruebas.json
.venv\Scripts\python manage.py runserver 0.0.0.0:8000
```

Con eso, OPS con la fuente `biblioteca` muestra «Biblioteca conectada» y el curso «Ciencias naturales» servido por la API v2 de mentira.

| Suite | Pruebas | Qué comprueba |
|---|---|---|
| `classroom_engine.tests.test_curso · ConLaApiDeContenidoV2Tests` (13) | misma vista que el ejemplo (con `mode=class` y `profile` por rol); opciones barajadas identificadas por `id`; la lista baja cada curso completo; `?version=` archivada y `course_not_found`; **401 reintenta una sola vez** y el segundo es 502; códigos de error traducidos (desactivado, reconstruyendo); estado de la fuente con cursos instalados y huella; medios en paso a través con `Range`; evaluar opción múltiple por `id` **siempre con `version`**; los demás tipos y el crédito parcial decimal; abierta pendiente sin nota; lote con la versión indicada y límite de 200 |
| `classroom_engine.tests.test_curso · CursoDeEjemploTests` (+2) | sin `link.json` → 503 «sin contenido» y `GET /api/aula/fuente/`; la fuente de ejemplo no califica (501) pero valida la forma (400) |
| `classroom_engine.tests.test_respuestas` (5) | la forma de `response` por tipo (17 casos inválidos), tipo desconocido reenviado, `score`/`correct` nulos y decimales, corrección manual sin nota |
| `Avacom.Lms.Core.Tests · AulaApiTests` (+1) | sin fuente el parámetro no viaja; con fuente se añade a la consulta |

Totales: **58** pruebas del aula, **176** del backend, **15** del núcleo MAUI.

### 7.1 · Lista de verificación del mapeo (§8), con veredicto

| | Estado |
|---|---|
| Las tablas del expediente guardan `courseId` **y** `version` | ✅ `m07_sesion`, `m07_foco`; `m10_intento` guarda `curso_ref` y recibe `version` en el veredicto (falta la columna: Q-48) |
| Guardan `lessonId`, `objectId`, `questionId`, no títulos | ✅ `*_ref`; los títulos sólo como `*_rotulo` |
| La respuesta de una opción guarda su `id`, no su índice | ✅ `selectedOptionIds` validado contra los `id` de la pregunta; un índice es 400 |
| `score` y `correct` admiten nulo | ✅ `puntaje`, `correcta` → `None` |
| `score` y `points` admiten decimales | ✅ `float`; `puntos_totales` de la actividad se suma como decimal |
| `requiresManualGrading: true` deja el intento pendiente, sin nota | ✅ `puntaje: null`, `pendiente: true` aunque llegue un número |
| Los tipos se generaron desde `openapi.v2.json`, no desde `course.schema.json` | ✅ (no hay tipos generados: el normalizador lee por nombre y todo opcional es anulable) |
| Un tipo de objeto o de pregunta desconocido **se muestra**, no se descarta | ✅ `componente: no_soportado` + `crudo` |
| `/v2/evaluate` se llama con `version` | ✅ obligatorio en el cliente (`ValueError` sin ella) y siempre puesto por el caso de uso |
| No hay ninguna tabla que replique el catálogo | ✅ `test_el_esquema_es_solo_de_aula_sin_curso_ni_claves` |
| `link.json` se relee en cada petición | ✅ |
| Un `401` reintenta **una** vez tras releer `link.json` | ✅ probado |
| La ausencia de `link.json` produce «sin contenido», no un error | ✅ 503 con `disponible: false` y sugerencia |

---

## 8 · Supuestos por confirmar contra `openapi.v2.json`

El mapeo describe campos e identificadores; no fija todo el transporte. Estos puntos se implementaron con la opción más habitual y están concentrados en constantes de `contenido_v2.py` para cambiarlos en un sitio:

| # | Supuesto | Dónde cambia | Si es distinto |
|---|---|---|---|
| A-1 | El `token` viaja como `Authorization: Bearer <token>` | `_pedir()` | Cambiar la cabecera; el host de pruebas se ajusta igual |
| A-2 | La lista de cursos instalados es `GET /v2/courses` (`{courses: […]}` o lista); si no existiera, `installedCourses` de `/v2/health` sirve de lista | `RUTA_CURSOS`, `cursos()` | Una ruta |
| A-3 | Los bytes de un medio son `GET /v2/courses/{courseId}/media/{mediaId}[/ruta]`, con `Range`; si la API responde con una **URL temporal** (redirección), el cliente la sigue dentro del loopback y no la guarda | `RUTA_MEDIO`, `abrir_medio()` | Una ruta; si hiciera falta abrir una «sesión de medios» explícita, se añade en `abrir_medio()` y nada más cambia (el `sessionId` sigue sin guardarse) |
| A-4 | `link.json` vive en `%ProgramData%\AVACOM\contenido\link.json` | `ruta_enlace()` / `AVACOM_CONTENIDO_ENLACE_V2` | Una ruta; ya es configurable |
| A-5 | Los errores llegan como `{"error": {"code", "message"}}`; se aceptan también `{code, message}`, `{error: "code", detail}` y texto plano | `_detalle_de_error()` | Nada, salvo una forma no prevista |
| A-6 | `?mode=class` **filtra** los objetos que no admiten ese modo (así lo hace el host de pruebas) | `MODO_AULA` | Si sólo valida, la tarjeta «Examen» atenuada vuelve a P2 sin tocar código |
| A-7 | El curso completo trae `id` (esquema 1.0); si llegara sólo `courseId`, se copia a `id` | `_con_id()` | Nada |
| A-8 | `installedCourses` en `/v2/health` es una lista de `{courseId, version, title}` (o de `courseId`); un entero se trata como conteo | `cursos_instalados()` | Nada |

Ninguno de ellos afecta a lo que el aula guarda ni al contrato `/api/aula/` que consumen OPS y Student.

---

## 9 · Lo que cambió en el código

| Capa | Archivo | Cambio |
|---|---|---|
| Biblioteca (cliente) | `backend/biblioteca/contenido_v2.py` | **Nuevo.** `leer_enlace`, `_pedir` (Bearer, 401 → releer y reintentar una vez), `salud`, `cursos_instalados`, `huella`, `cursos`, `curso(version, modo, perfil)`, `guia_calificacion`, `evaluar`, `evaluar_lote` (troceo a 200), `abrir_medio`, `estado` |
| Biblioteca (cliente) | `backend/biblioteca/cliente.py` | `BibliotecaError.codigo` (código del contrato v2; vacío en el contrato 1) |
| Aula · dominio | `classroom_engine/dominio/respuestas.py` | **Nuevo.** `validar_respuesta(pregunta, respuesta)` por tipo y `veredicto(bruto)` |
| Aula · dominio | `classroom_engine/dominio/errores.py` | `DesactivadoPorPolitica` (404 `desactivado_por_politica`) |
| Aula · puertos | `classroom_engine/aplicacion/puertos.py` | `FuenteDeCursos.curso(ref, *, version, rol)`, `evaluar`, `evaluar_lote`, `estado` |
| Aula · casos de uso | `classroom_engine/aplicacion/casos_uso.py` | `_vista(…, version)`; `ConsultarCurso/Leccion/Objeto` con `version`; **`EstadoFuente`**, **`EvaluarRespuesta`** |
| Aula · infraestructura | `classroom_engine/infraestructura/fuente_biblioteca.py` | Reescrito sobre `contenido_v2`: `mode=class`, `profile` por rol, traducción de códigos, lista que baja cada curso |
| Aula · infraestructura | `classroom_engine/infraestructura/fuente_ejemplo.py` | Misma firma; `version` distinta → 404; `evaluar` → 501; `estado` |
| Aula · HTTP | `classroom_engine/interfaces/views.py`, `urls.py` | `GET fuente/`, `?version=` en curso/lección/objeto, `POST cursos/{ref}/evaluar/` |
| Configuración | `backend/avacom_lms/settings.py` | `AVACOM_CONTENIDO_ENLACE_V2` |
| Pruebas | `backend/tools/host_contenido_v2_pruebas.py` | **Nuevo** host que imita la API v2 |
| Pruebas | `classroom_engine/tests/test_curso.py`, `test_respuestas.py` | Suite v2 (sustituye a la del host del contrato 1 para el aula), respuestas |
| MAUI · núcleo | `Avacom.Lms.Core/Services/AulaApi.cs` | `Fuente` anulable: sin fuente el parámetro no viaja |
| MAUI · OPS | `Sesion.cs`, `Pages/ClaseHoyPage.xaml.cs` | `FuenteAula` en `Preferences` (por defecto `biblioteca`); alerta ámbar «Biblioteca no está encendida» con **«Usar el curso de ejemplo»**; el chip de fuente alterna al tocarlo |
| MAUI · Student | `Sesion.cs` | Sin `FuenteAula`: la tableta no elige fuente |

---

## 10 · Lo que queda fuera y dónde sigue

| Qué | Dueño | Nota |
|---|---|---|
| Guardar el intento, la respuesta y el veredicto (`m10_intento`, `m10_intento_respuesta`) con `version`, `score` decimal/nulo y estado `pendiente_correccion` | MOD-010 (Q-48, Q-49) | El aula ya devuelve todo lo necesario en `/evaluar/`; el flujo de intentos del expediente sigue con el contrato 1 (`/v1/comprobar`) hasta que se migre |
| Calificar a mano una abierta con `grading-guide` | MOD-011 | El cliente ya la pide; falta la pantalla del docente y la ruta, fuera del aula |
| Responder la actividad desde la tableta (S2) | Frontend MOD-007 | La vista previa puede pasar a enviar `POST /evaluar/` con la forma de §4 cuando MOD-010 guarde el intento |
| Bloque `formula` | Normalizador + MAUI | Hoy llega como `crudo`; añadirlo cuando haya un curso que lo use |
| Caché en memoria de minutos invalidada por `installedCourses` | — | **No se implementa**: el artículo 14 prefiere preguntar siempre; `huella` queda disponible si algún día hace falta |
| Confirmar A-1 … A-8 | Equipo de Biblioteca + LMS | Contra `contracts/openapi.v2.json`, `docs/INTEGRACION-LMS.md` y `samples/lms-client/`, que no llegaron con el mapeo |
