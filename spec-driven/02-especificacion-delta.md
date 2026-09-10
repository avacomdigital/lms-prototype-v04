# 02 · Especificación · delta respecto de la línea base

| Campo | Valor |
|---|---|
| Especificación normativa | Fase 2 del prompt [`docs/prompts/prompt-backend-spec-driven.md`](../prompts/prompt-backend-spec-driven.md) |
| Este documento | La traducción de esa especificación a un antes/después trazable, para que ningún requisito se pierda en el camino |

La Fase 2 del prompt contiene la especificación completa —problema, frontera, actores, US-01..US-14, RF-001..RF-045, CA-01..CA-15, fuera de alcance y medidas de éxito— en el formato que consume `/speckit.specify`. No se duplica aquí.

---

## 1 · Qué se queda, qué se va, qué se resuelve en vivo

| Capacidad de la línea base | Destino | Nota |
|---|---|---|
| Marcos curriculares, cursos, versiones, secciones, lecciones, ítems, recursos, actividades | **AVACOM Biblioteca** | Desaparecen del esquema de OPS |
| Activación, reversión e inmutabilidad de versiones | **AVACOM Biblioteca** | OPS observa la versión vigente para poder fechar el expediente |
| Inspección, importación e instalación de paquetes (SCORM 1.2/2004, cmi5, nativo, AVACOM-Contenido) | **AVACOM Biblioteca** | Se elimina `exams.packages` y `exams.package_install` de OPS |
| Inventario y verificación de presencia por equipo (`m05_curso_host`) | **AVACOM Biblioteca** | OPS pregunta; conserva sólo memoria de la última revisión |
| Asociación de material a una lección (`m05_unidad_material`) | **AVACOM Biblioteca** | La composición del curso es del dueño del curso |
| Preguntas y opciones del quiz | **AVACOM Biblioteca** | OPS las pide sin clave y no las almacena |
| Estructura mostrada al estudiante | **Resuelta en vivo** | Por referencia de curso, en cada consulta |
| Disponibilidad de un curso en el aula | **Resuelta en vivo** | Con memoria de la última revisión para poder degradar |
| Inscripción | **AVACOM OPS** | Reescrita contra referencia de curso |
| Progreso por lección lógica y promedio del curso | **AVACOM OPS** | Reescrito contra referencia de curso |
| Intentos, respuestas, veredictos y notas | **AVACOM OPS** | Reescritos contra referencias de evaluación y pregunta |
| Reparto de preguntas por persona | **AVACOM OPS** | Es reparto, no composición |
| Reparto de aula y su cierre | **AVACOM OPS** | Es estado de la clase en curso |
| Auditoría | **AVACOM OPS** | Gana el evento de rechazo de administración |
| Presencia y eventos en vivo | **AVACOM OPS** | Sin cambios de diseño |

## 2 · Trazabilidad de los requisitos anteriores

| Antes | Ahora | Estado |
|---|---|---|
| RF-001..RF-008 (catálogo académico, jerarquía, versión activa, ítems, recursos) | RF-001..RF-008 nuevos (frontera de administración) | **Reemplazados**. Su contenido anterior se traslada |
| RF-009..RF-016 (expediente y progreso) | RF-009..RF-016 | **Conservados**, reescritos contra referencias |
| RF-017..RF-025 (quiz) | RF-017..RF-025 | **Conservados** con corrección delegada; el almacenamiento de preguntas se traslada |
| RF-026..RF-034 (presencia por host) | RF-026..RF-034 nuevos (disponibilidad y aula) | **Reemplazados** por consulta en vivo más memoria de revisión |
| RF-035..RF-041 (paquetes) | — | **Trasladados** íntegros |
| RF-042..RF-054 (integración) | RF-035..RF-040 | **Conservados y condensados**; la parte de material por lección se traslada |
| RF-055..RF-057 (diagnóstico, auditoría, sin Internet) | RF-043..RF-045 | **Conservados** |
| — | RF-041..RF-042 | **Nuevos**: continuidad y migración del expediente |

## 3 · Historias nuevas y su motivo

| Historia | Por qué existe |
|---|---|
| US-07 · Administración rechazada en el sitio equivocado | La frontera tiene que ser del backend, no de la disciplina del cliente. Sin rechazo explícito, el primer script que llame a la ruta antigua reintroduce la doble verdad |
| US-13 · Expediente legible sin biblioteca | Es la prueba de que el expediente no depende del contenido. Con la biblioteca cerrada, el estudiante debe seguir viendo notas y progreso |
| US-14 · Migración sin pérdida | El expediente existente apunta hoy a filas físicas que van a desaparecer. Es el riesgo principal del cambio |

## 4 · Lo que cambia para el estudiante y para el docente

| Actor | Antes | Ahora |
|---|---|---|
| Docente | Crea el curso, arma secciones y lecciones, importa paquetes, controla presencia y disponibilidad desde OPS Master | Administra el curso en AVACOM Biblioteca. En OPS Master inscribe, acompaña la clase, reparte material y consulta resultados |
| Estudiante | Ve la estructura guardada por OPS | Ve la estructura vigente que publica la biblioteca; su expediente es el mismo y sobrevive a cambios |
| Técnico | Diagnostica presencia física en el inventario del LMS | Diagnostica disponibilidad consultada, con distinción explícita entre «no disponible» y «no se pudo comprobar» |

## 5 · Ambigüedades detectadas y no resueltas aquí

Se envían a la Fase 3 ([03-clarificacion.md](03-clarificacion.md)) y bloquean el plan: el contrato de curso y estructura que la biblioteca debe publicar (Q-19), la referencia estable de curso (Q-20), el destino de los cursos ya creados en OPS y su expediente (Q-21), el cálculo de nota sin claves (Q-22) y el impacto en el frontend (Q-23).
