# 04 · Plan técnico del nuevo prototipo

| Campo | Valor |
|---|---|
| Estado | Propuesta. Depende de Q-19 a Q-23 |
| Plataforma | Sin cambios: Python 3.12, Django 5.2.3, DRF 3.16.1 con `APIView`, Channels 4.3.1, Daphne 4.2.1, SQLite, ASGI en `0.0.0.0:8000` |
| Bloque normativo | Fase 4 del prompt [`docs/prompts/prompt-backend-spec-driven.md`](../prompts/prompt-backend-spec-driven.md) |

---

## 1 · Componentes

```
                         ┌──────────────────────── AVACOM OPS · backend ─────────────────────────┐
Tableta / Master  ──────►│  views            expediente + consultas del estudiante y del docente │
      HTTP :8000         │  rechazos         rutas retiradas de administración → error explicativo│
                         │  estructura       resolución EN VIVO del árbol del curso (no escribe)  │
                         │  intentos         intento, reparto de preguntas, respuesta, nota       │
                         │  progress         upsert monotónico y promedio sobre estructura vigente│
                         │  disponibilidad   revisión de oferta + memoria de la última revisión   │
                         │  biblioteca       ÚNICO cliente hacia AVACOM Biblioteca                │
                         │  consumers        eventos de aula en vivo                              │
                         └───────────────────────────────┬───────────────────────────────────────┘
                                                         │ loopback, puerto efímero, X-Avacom-Ficha
                                                         ▼
                                            AVACOM Biblioteca · dueña del curso
```

| Módulo | Origen | Cambio |
|---|---|---|
| `exams.biblioteca` | `exams.contenido` | **Se conserva íntegro** y se amplía con las rutas de curso y estructura. Su descubrimiento de puerto y ficha, tiempo de espera, degradación y detección de cambio ya es correcto |
| `exams.estructura` | nuevo | Resuelve y proyecta el árbol del curso. No escribe nunca |
| `exams.disponibilidad` | `exams.reconciliacion` | Conserva la regla de oro —no escribir sin oferta válida— y pierde el saneamiento de banderas propias |
| `exams.intentos` | parte de `exams.views` | Se separa como servicio de dominio con límites transaccionales |
| `exams.progress` | igual | Reescrito contra referencias |
| `exams.rechazos` | nuevo | Las rutas retiradas responden con el error de RF-003 en lugar de desaparecer sin aviso |
| `exams.catalog`, `exams.package_install`, `exams.packages`, `exams.hosts` | — | **Se eliminan.** Su contenido se traslada a AVACOM Biblioteca |
| `exams.views_contenido` | — | Se reparte entre `estructura`, `disponibilidad` y las vistas de aula |

---

## 2 · Modelo de datos objetivo

De 19 entidades a **8 aprobadas** más una condicionada por Q-04/Q-24. Toda columna terminada en `_ref` o `_codigo` es una referencia emitida por AVACOM Biblioteca; toda columna terminada en `_rotulo` es evidencia histórica que no se refresca.

### 2.1 · `m05_inscripcion` · Inscripcion

| Columna | Tipo | Nota |
|---|---|---|
| `id` | char(40) | Identificador compacto |
| `curso_ref` | char(200) | Referencia estable del curso en la biblioteca (Q-20) |
| `persona_id` | char(64) | Identificador externo. No hay tabla de personas |
| `curso_rotulo` | char(250) | Título con el que se inscribió. Evidencia histórica |
| `inscrito_en`, `retirado_en` | bigint ms | El retiro de la inscripción es una decisión del docente, no del contenido |
| `creado_en`, `creado_por`, `secuencia` | | Convención del proyecto |

Invariantes: `UNIQUE(curso_ref, persona_id)`; `retirado_en IS NULL OR retirado_en >= inscrito_en`.

### 2.2 · `m05_progreso_leccion` · ProgresoLeccion

Se conserva el nombre de tabla. Cambia `curso_id` (FK) por `curso_ref`.

| Columna | Tipo | Nota |
|---|---|---|
| `curso_ref` | char(200) | Antes FK a `m05_curso` |
| `persona_id` | char(64) | |
| `leccion_codigo` | char(120) | **Identidad lógica**, emitida por la biblioteca. Es lo que hace que el progreso sobreviva al cambio de versión |
| `leccion_rotulo` | char(250) | Antes `leccion_titulo`. Mismo papel: permitir mostrar el historial con la biblioteca cerrada |
| `porcentaje` | decimal(5,2) | |
| `estado` | char(16) | `no_iniciada` / `en_curso` / `completada` |
| `version_observada` | char(32) | Contra qué versión se registró el último avance |
| `iniciado_en`, `actualizado_en`, `completado_en` | bigint ms | |

Invariantes conservados: `UNIQUE(curso_ref, persona_id, leccion_codigo)`; `0 <= porcentaje <= 100`; `completada` implica `porcentaje = 100` y `completado_en` no nulo.

### 2.3 · `m10_intento` · Intento

| Columna | Tipo | Nota |
|---|---|---|
| `evaluacion_ref` | char(200) | Antes FK a `m10_actividad` |
| `curso_ref`, `leccion_codigo` | | Contexto académico del intento, para poder alimentar el progreso |
| `version_observada` | char(32) | Con qué versión del contenido se rindió |
| `persona_id`, `persona_rotulo`, `dispositivo` | | |
| `pregunta_actual` | int | Lo que alimenta el seguimiento en vivo |
| `estado` | char(16) | `abierto` / `finalizado` / `pendiente_correccion` (Q-22) |
| `puntaje` | decimal(6,2) null | Registro autoritativo de la nota. No se duplica en progreso |
| `iniciado_en`, `finalizado_en` | bigint ms | |

Invariantes: un solo intento `abierto` por `(evaluacion_ref, persona_id, dispositivo)`; `finalizado` implica `finalizado_en` no nulo; `puntaje` sólo con estado `finalizado`.

### 2.4 · `m10_intento_pregunta` · IntentoPregunta

Sustituye `m05_examen_pregunta`. Qué se le preguntó a quién y en qué orden, para poder reconstruir el examen aunque el contenido ya no esté.

Columnas: `intento`, `pregunta_ref`, `elemento_ref`, `version_elemento`, `orden`.
Invariantes: `UNIQUE(intento, pregunta_ref)`; `UNIQUE(intento, orden)`.
**No hay columna para la clave, y no es un olvido** (artículo 14.5).

### 2.5 · `m10_intento_respuesta` · IntentoRespuesta

Sustituye `m10_quiz_respuesta`. La opción elegida ya no es una FK a una tabla de opciones que no existe.

| Columna | Tipo | Nota |
|---|---|---|
| `intento` | FK | |
| `pregunta_ref` | char(200) | |
| `respuesta` | texto/JSON | Lo que el estudiante eligió o escribió, tal como se envió a corregir |
| `acierta` | bool null | **Veredicto** devuelto por la biblioteca. Nulo mientras no se pudo corregir |
| `corregido_en` | bigint ms null | |
| `retroalimentacion_rotulo` | texto null | La que la pregunta ya trae; nunca la clave |

Invariante: `UNIQUE(intento, pregunta_ref)` — es la idempotencia real de la respuesta.

### 2.6 · `m05_reparto_activo` · RepartoActivo

**Sin cambios estructurales.** Ya trabaja sólo con referencias. Se elimina la FK `curso` y se sustituye por `curso_ref` nulable.
Invariantes conservados: un solo reparto abierto por `(host_id, sesion_clase_id, elemento_ref)`; cierre posterior a la apertura.

### 2.7 · `m05_disponibilidad_observada` · DisponibilidadObservada

Reemplaza a la vez `m05_curso_host` y las tres columnas de memoria de `m05_unidad_material`. **Es la única concesión del artículo 14** y su razón de ser es poder explicar una ausencia con la biblioteca cerrada.

| Columna | Tipo | Nota |
|---|---|---|
| `host_id` | char(64) | |
| `referencia` | char(200) | Referencia de curso o de elemento |
| `clase` | char(16) | `curso` o `elemento` |
| `disponible_ultima_revision` | bool | |
| `revisado_en` | bigint ms | |
| `desaparecido_en` | bigint ms null | |

Invariantes: `UNIQUE(host_id, referencia, clase)`; **no disponible obliga a fecha** (`disponible = True OR desaparecido_en IS NOT NULL`).
Lo que esta tabla **no** tiene, y su revisión debe comprobar: título, estructura, tipo de contenido, enunciado, opción o clave.

### 2.8 · `m19_auditoria` · Auditoria

Sin cambios de forma: `actor_id`, `accion`, `objeto_tabla`, `objeto_id`, `valor_anterior`, `valor_nuevo`, momento. Append-only, sin ruta de escritura ni de borrado.
Acciones nuevas: `administracion.rechazada`, `disponibilidad.desaparecio`, `disponibilidad.reaparecio`, `reparto.cerrado_por_retiro`, `migracion.expediente`.

### 2.9 · Condicionada · `m01_identidad_preparatoria`

Sólo si Q-04 y Q-24 la aprueban: modelo de datos que acerque al módulo de acceso sin implementarlo. No se crea por iniciativa del desarrollo.

### 2.10 · Tablas que se eliminan

`m05_marco_curricular`, `m05_curso`, `m05_curso_version`, `m05_seccion`, `m05_leccion`, `m05_leccion_item`, `m05_recurso_aprendizaje`, `m10_actividad`, `m10_quiz_pregunta`, `m10_quiz_opcion`, `m05_curso_host`, `m05_unidad_material`.

`m05_curso_estudiante`, `m10_quiz_intento` y `m10_quiz_respuesta` no se eliminan: se reescriben como 2.1, 2.3 y 2.5.

---

## 3 · Contratos HTTP objetivo

### 3.1 · Expediente y consultas

| Ruta | Verbo | Nota |
|---|---|---|
| `/health/` | GET | Sin cambios |
| `/api/inscripciones/` | GET, POST | Inscribir a una `curso_ref`. No crea curso |
| `/api/inscripciones/{id}/` | GET, DELETE lógico | El retiro sella fecha; no borra |
| `/api/students/{persona}/courses/` | GET | Cursos de la persona con progreso, disponibilidad y explicación |
| `/api/students/{persona}/courses/{curso_ref}/progress/` | GET, POST | Upsert monotónico |
| `/api/courses/{curso_ref}/estructura/` | GET | **Resuelta en vivo.** Degrada con expediente y aviso |
| `/api/evaluaciones/{evaluacion_ref}/` | GET | Preguntas sin ningún indicador de corrección |
| `/api/intentos/start/` | POST | Crea o reanuda |
| `/api/intentos/progress/` | POST | Publica avance |
| `/api/intentos/answer/` | POST | Idempotente por `(intento, pregunta_ref)`; delega corrección |
| `/api/intentos/finish/` | POST | Idempotente; calcula nota y alimenta progreso |
| `/api/resultados/` · `/api/resultados/{intento}/` | GET | Consolidado y detalle |
| `/api/auditoria/` | GET | Sólo lectura |

### 3.2 · Aula y biblioteca

| Ruta | Verbo |
|---|---|
| `/api/biblioteca/estado/` | GET |
| `/api/biblioteca/oferta/` | GET |
| `/api/biblioteca/revisar/` | GET (informe sin escribir), POST (revisa y audita) |
| `/api/biblioteca/mostrar/` | POST |
| `/api/aula/reparto/` | GET, POST |
| `/api/aula/reparto/{id}/cerrar/` | POST |
| `/api/students/{persona}/reparto/` | GET |

### 3.3 · Rutas retiradas con rechazo explicativo

Todo verbo de escritura sobre `curriculum-frameworks`, `courses`, `course-versions`, `sections`, `lessons`, `lesson-items`, `learning-resources`, `activities`, `quiz-questions`, `quiz-options`, `course-packages`, `course-hosts` y `lecciones/{id}/materiales`.

Respuesta propuesta, a confirmar con Q-18:

```json
{
  "error": "administracion_no_permitida",
  "detail": "Los cursos y su contenido se administran en AVACOM Biblioteca. Este backend registra únicamente el progreso del estudiante.",
  "dueno": "AVACOM Biblioteca",
  "operacion": "POST /api/courses/"
}
```

Código: **409** o **421**, según Q-18. No 404: la ruta existe y su respuesta es informativa a propósito, para que un cliente antiguo reciba una explicación y no un misterio.

### 3.4 · Contrato en vivo

Sin cambios de diseño. `/ws/activities/{ref}/`, donde el identificador pasa a ser `evaluacion_ref`. Cierre `4404` si la evaluación no está en la oferta, `4400` si falta `attempt_id`. Eventos `presence_changed`, `activity_state`, `student_progress`, `attempt_finished`, `pong`; los dos del medio sólo al grupo docente. Endurecer según Q-09.

---

## 4 · Degradación

Es la parte de la línea base que se conserva sin tocar, porque ya es correcta.

| Situación | Respuesta al cliente | Escribe |
|---|---|---|
| Biblioteca ausente o cerrada | 503 con `disponible: false`, motivo y sugerencia | No |
| Capacidad no publicada | 501 con el motivo y la lista de capacidades | No |
| La biblioteca contestó con error | 502 con el detalle | No |
| Consultar expediente sin biblioteca | 200 con progreso, notas y rótulos registrados, más aviso de que el contenido no se puede abrir | No |
| Revisión de disponibilidad sin oferta válida | 503, y la respuesta anterior queda intacta | **Nunca** |

Regla que hay que hacer explícita en el código: **«no se pudo comprobar» no es «no está»**. Una referencia sin oferta consultable se responde con la última revisión conocida y su fecha, jamás marcándola ausente.

---

## 5 · Migración del expediente, en tres pasos separados

Cada paso es una migración distinta con su propia verificación. **Nunca se combinan.**

### Paso 1 · Añadir y poblar referencias

- Añadir `curso_ref`, `evaluacion_ref`, `pregunta_ref`, `leccion_codigo` y las columnas `_rotulo` donde falten, nulables.
- Poblarlas desde las tablas actuales: `curso_ref` desde la identidad que Q-20 defina; `leccion_codigo` desde `m05_leccion.codigo`, que ya existe; `evaluacion_ref` desde `m10_actividad`; `pregunta_ref` desde `m10_quiz_pregunta`; los rótulos desde los títulos vigentes en ese momento.
- Copiar la opción elegida de cada respuesta a la nueva columna `respuesta` y su corrección a `acierta`.

### Paso 2 · Verificar cobertura

- Contar filas de inscripción, progreso, intento y respuesta antes y después. Deben coincidir exactamente.
- Listar toda fila cuya referencia no se pudo resolver. Se **conserva marcada como irresoluble** y se reporta; no se elimina ni se adivina (RF-042).
- Emitir el informe. **Si hay una sola fila irresoluble sin decisión registrada, el paso 3 no se ejecuta.**

### Paso 3 · Eliminar tablas de curso y estructura

- Retirar las doce tablas de §2.10 y sus modelos, serializers, vistas y rutas.
- Instalar la prueba de esquema que falla si alguna vuelve.

Reversibilidad: los pasos 1 y 2 son reversibles. El paso 3 no lo es sin restaurar una copia, así que exige respaldo verificado y la decisión de Q-21 registrada.

---

## 6 · Estrategia de pruebas

| Prueba | Qué protege |
|---|---|
| Esquema sin tablas de curso | Artículo 14.1 · CA-01 |
| Ningún módulo importa un modelo de curso | Artículo 14.1, en el código y no sólo en la base |
| Rechazo por verbo y ruta retirados | Artículo 14.2 · CA-02 |
| Estructura en vivo refleja el cambio hecho en la biblioteca | Artículo 14.3 · CA-03 |
| Inspección recursiva de todo payload del estudiante buscando `es_correcta`, `correcta`, `clave` y variantes | Artículo 6 · CA-08 |
| Revisión de esquema que impide una columna capaz de contener una clave | Artículo 14.5 |
| Retirar → consultar → reponer con recuentos exactos | CA-04, CA-05 |
| Cambio de versión que conserva y que elimina un código lógico | CA-06 |
| Progreso atrasado que no reduce, y 100% que sella | CA-09 |
| Finalización repetida con una sola nota | CA-10 |
| Sin capacidad de corrección no hay nota | CA-11 |
| Oferta ausente no escribe; respuesta distingue no disponible de no comprobable | CA-13 |
| Reparto idempotente, cierre por retiro, visibilidad del estudiante | CA-14 |
| Migración desde una base de la versión anterior con informe | CA-15 |
| Escenario integral sin Internet y con biblioteca apagada | CA-07, CA-13 |

La suite de integración de referencia es [`backend/exams/tests/test_contenido.py`](../../backend/exams/tests/test_contenido.py): usa `AVACOM_CONTENIDO_ENLACE` y un host de pruebas, y por eso no necesita la biblioteca real. Ese patrón se conserva.

---

## 7 · Riesgos

| Riesgo | Mitigación |
|---|---|
| La biblioteca no publica a tiempo el contrato de estructura (Q-19) | No empezar el paso 3. El prototipo actual queda intacto en su rama |
| El expediente existente no se puede referenciar (Q-20, Q-21) | El paso 2 bloquea el 3. Filas irresolubles se conservan y se reportan |
| Sin capacidad de corrección no hay notas nuevas (Q-22) | Estado `pendiente_correccion` explícito en el intento, en lugar de una nota inventada |
| El OPS Master queda con pantallas huérfanas (Q-23) | Tareas de frontend separadas y explícitas, liberadas en un orden que no rompa la aplicación instalada |
| Latencia por resolver la estructura en cada consulta | Es loopback y el catálogo del aula es pequeño. Si aparece un problema medido, se resuelve con la señal de cambio de la biblioteca, no con una copia local |
| Tentación de cachear el catálogo | Está prohibido por el artículo 14.3 y por la razón que ya conoce la línea base: acaba ofreciendo material que la escuela desactivó |
